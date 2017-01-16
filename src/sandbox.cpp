#include "sandbox.h"

#include <linux/sched.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include "shim.h"
#include "util.h"

namespace {

void CreateAndBindDir(const char *olddir, const char *newdir) {
    CHECK_UNIX(mkdir(newdir, 0755));
    CHECK_UNIX(mount(olddir, newdir, NULL, MS_BIND, NULL));
    CHECK_UNIX(
        mount(olddir, newdir, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY, NULL));
}

}

Sandbox::Sandbox(boost::asio::io_service &io_service,
                 std::string sandbox_root)
    : io_service(io_service),
      sandbox_root(std::move(sandbox_root)) {}

void Sandbox::Start() {
    pid_t pid = Fork([this]() { HandleSandboxProcess(); }, io_service);
    CHECK(pid > 0);
    // TODO: how to wait/kill all process in the pid namespace?
    wait(NULL);
}

void Sandbox::HandleSandboxProcess() {
    CHECK_UNIX(
        unshare(CLONE_NEWNS | CLONE_NEWCGROUP | CLONE_NEWUTS | CLONE_NEWIPC |
                CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET));

    // Prepare root directory.
    CHECK_UNIX(mount("tmpfs", sandbox_root.c_str(), "tmpfs", 0, NULL));
    CHECK_UNIX(chdir(sandbox_root.c_str()));
    CreateAndBindDir("/bin", "bin");
    CreateAndBindDir("/lib", "lib");
    CreateAndBindDir("/lib64", "lib64");
    CreateAndBindDir("/usr", "usr");

    // Change the root and unmount the old one.
    CHECK_UNIX(mkdir("old-root", 0755));
    CHECK_UNIX(pivot_root(".", "old-root"));
    CHECK_UNIX(umount2("old-root", MNT_DETACH));
    CHECK_UNIX(rmdir("old-root"));

    Fork([this]() { HandleInitProcess(); });
    // TODO: how to wait/kill all process in the pid namespace?
    wait(NULL);
}

void Sandbox::HandleInitProcess() {
    CHECK(getpid() == 1);
    execl("/bin/bash", "bash", NULL) == 0;
}
