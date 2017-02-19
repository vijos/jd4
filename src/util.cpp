#include <sys/mount.h>
#include "util.h"

void WriteFile(const Path &file, StringView content) {
    OFStream sink(file, Ios::binary);
    sink.write(content.data(), content.size());
}

Path CreateTempPath(const Path &model, int num_attempts) {
    Path path;
    do {
        CHECK(num_attempts--);
        path = TempPath() / RandomPath(model);
    } while (!MakeDir(path));
    return path;
}

void CopyFiles(const Path &from_dir, const Path &to_dir) {
    for (DirIterator iter(from_dir); iter != DirIterator(); ++iter) {
        Path path = iter->path().filename();
        switch (iter->status().type()) {
        case FileType::regular_file:
            Copy(from_dir / path, to_dir / path, CopyOption::overwrite_if_exists);
            break;
        case FileType::directory_file:
            CopyFiles(from_dir / path, to_dir / path);
            break;
        default:
            LOG(warning) << "File " << iter->path()
                         << " has special type " << iter->status().type();
        }
    }
}

void UnshareAll() {
    CHECK_UNIX(unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
                       CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET));
}

void MountTmpfs(const Path &dir) {
    CHECK_UNIX(mount("tmpfs", dir.c_str(), "tmpfs", 0, NULL));
}

void MakeBindMount(const Path &from, const Path &to, bool read_only) {
    CHECK(MakeDir(to));
    CHECK_UNIX(mount(from.c_str(), to.c_str(), NULL, MS_BIND, NULL));
    if (read_only) {
        CHECK_UNIX(mount(from.c_str(), to.c_str(), NULL, MS_BIND | MS_REMOUNT | MS_RDONLY, NULL));
    }
}

void PivotRoot(const Path &new_root, const Path &old_root) {
    ChangeDir(new_root);
    CHECK(MakeDir(new_root / old_root));
    CHECK_UNIX(pivot_root(".", old_root.c_str()));
}

void MakeProcMount(const Path &dir) {
    CHECK(MakeDir(dir));
    CHECK_UNIX(mount("procx", dir.c_str(), "proc", 0, NULL));
}

void RemoveMount(const Path &dir) {
    CHECK_UNIX(umount2(dir.c_str(), MNT_DETACH));
    Remove(dir);
}

void Exec(const Path &path, const Vector<String> &args, const Vector<String> &envs) {
    Vector<const char *> arg_ptrs;
    arg_ptrs.reserve(args.size() + 1);
    for (const String &arg : args) {
        arg_ptrs.push_back(arg.c_str());
    }
    arg_ptrs.push_back(nullptr);
    Vector<const char *> env_ptrs;
    env_ptrs.reserve(envs.size() + 1);
    for (const String &env : envs) {
        env_ptrs.push_back(env.c_str());
    }
    env_ptrs.push_back(nullptr);
    execve(path.c_str(), const_cast<char **>(arg_ptrs.data()), const_cast<char **>(env_ptrs.data()));
}
