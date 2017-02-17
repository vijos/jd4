#include "process.h"

#include <sys/mount.h>

void Sandbox(const Path &sandbox_root, const Vector<Pair<Path, Path>> &mount_points) {
    CHECK_UNIX(unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
                       CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET));

    // Prepare root directory.
    CHECK_UNIX(mount("tmpfs", sandbox_root.c_str(), "tmpfs", 0, NULL));
    for (const auto &pair : mount_points) {
        const Path &olddir = pair.first;
        const Path &newdir = sandbox_root / pair.second;
        CHECK_UNIX(mkdir(newdir.c_str(), 0755));
        CHECK_UNIX(mount(olddir.c_str(), newdir.c_str(), NULL, MS_BIND | MS_RDONLY, NULL));
    }

    // Change the root and detach the old one.
    CHECK_UNIX(chdir(sandbox_root.c_str()));
    CHECK_UNIX(mkdir("old_root", 0755));
    CHECK_UNIX(pivot_root(".", "old_root"));
    CHECK_UNIX(umount2("old_root", MNT_DETACH));
    CHECK_UNIX(rmdir("old_root"));
}
