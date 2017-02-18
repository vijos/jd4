#include "process.h"

#include <sys/mount.h>

void Sandbox(const Path &sandbox_dir, const Vector<Pair<Path, Path>> &mount_points) {
    CHECK_UNIX(unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
                       CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET));

    // Prepare root directory.
    CHECK_UNIX(mount("tmpfs", sandbox_dir.c_str(), "tmpfs", 0, NULL));
    for (const auto &pair : mount_points) {
        const Path &old_dir = pair.first;
        const Path &new_dir = sandbox_dir / pair.second;
        CHECK(MakeDir(new_dir));
        CHECK_UNIX(mount(old_dir.c_str(), new_dir.c_str(), NULL, MS_BIND | MS_RDONLY, NULL));
    }

    // Change the root and detach the old one.
    ChangeDir(sandbox_dir);
    CHECK(MakeDir("old_root"));
    CHECK_UNIX(pivot_root(".", "old_root"));
    CHECK_UNIX(umount2("old_root", MNT_DETACH));
    Remove("old_root");
}
