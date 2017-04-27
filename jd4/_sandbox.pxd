cdef extern from "sched.h":
    cdef enum:
        CLONE_NEWNS
        CLONE_NEWUTS
        CLONE_NEWIPC
        CLONE_NEWUSER
        CLONE_NEWPID
        CLONE_NEWNET

    int unshare(int flags)

cdef extern from "sys/mount.h":
    cdef enum:
        MS_BIND
        MS_REMOUNT
        MS_RDONLY
        MS_NOSUID
        MNT_DETACH

    int mount(const char* source, const char* target,
              const char* filesystemtype, unsigned long mountflags,
              const void* data)
    int umount2(const char* target, int flags)

cdef extern int pivot_root(const char* new_root, const char* put_old)
