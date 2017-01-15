#include "sandbox.h"

#include <linux/sched.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <boost/format.hpp>
#include "shim.h"
#include "util.h"

Sandbox::Sandbox(boost::asio::io_service &io_service)
    : io_service(io_service)
{}

void Sandbox::StartInitProcess() {
    io_service.notify_fork(boost::asio::io_service::fork_prepare);
    pid_t unshare_pid = fork();
    if (!unshare_pid) {
        io_service.notify_fork(boost::asio::io_service::fork_child);
        real_euid = geteuid();
        real_egid = getegid();
        CHECK(unshare(CLONE_NEWNS | CLONE_NEWCGROUP | CLONE_NEWUTS | CLONE_NEWIPC |
                      CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET) == 0);
        pid_t init_pid = fork();
        LOG(info) << init_pid;
        if (!init_pid) {
            HandleInitProcess();
            exit(0);
        }
        wait(NULL);
        exit(0);
    }
    CHECK(unshare_pid > 0);
    io_service.notify_fork(boost::asio::io_service::fork_parent);
    // TODO: how to wait/kill all process in the pid namespace?
    wait(NULL);
}

void Sandbox::HandleInitProcess() {
    CHECK(WriteFile("/proc/self/setgroups", "deny"));
    CHECK(WriteFile("/proc/self/uid_map", (boost::format("0 %d 1") % real_euid).str()));
    CHECK(WriteFile("/proc/self/gid_map", (boost::format("0 %d 1") % real_egid).str()));

    CHECK(mount("none", "/", NULL, MS_REC | MS_PRIVATE, NULL) == 0);
    CHECK(mount("proc", "/proc", "proc", MS_NOSUID | MS_NOEXEC | MS_NODEV, NULL) == 0);

    execl("/bin/bash", "bash", NULL);
}
