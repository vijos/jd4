# cython: c_string_type=str, c_string_encoding=ascii

from os import chdir, getegid, geteuid, makedirs, mkdir, mknod, path, \
               readlink, rmdir, setresgid, setresuid, symlink
from socket import sethostname

from jd4._sandbox cimport mount, umount2, unshare, \
    CLONE_NEWNS, CLONE_NEWUTS, CLONE_NEWIPC, \
    CLONE_NEWUSER, CLONE_NEWPID, CLONE_NEWNET, \
    MS_BIND, MS_REMOUNT, MS_RDONLY, MS_NOSUID
from jd4.util import write_text_file

cdef bind_mount(const char* src, const char* target,
                bint make_dir, bint make_node, bint bind, bint rebind_ro):
    if make_dir:
        makedirs(target)
    if make_node:
        mknod(target)
    if bind:
        mount(src, target, '', MS_BIND | MS_NOSUID, NULL)
    if rebind_ro:
        mount(src, target, '', MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID, NULL)

cdef bind_or_link(src, target):
    if path.islink(src):
        symlink(readlink(src), target)
    elif path.isdir(src):
        bind_mount(src, target, True, False, True, True)

def create_namespace():
    host_euid = geteuid()
    host_egid = getegid()
    unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
            CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET)
    write_text_file('/proc/self/uid_map', '1000 {} 1'.format(host_euid))
    try:
        write_text_file('/proc/self/setgroups', 'deny')
    except FileNotFoundError:
        pass
    write_text_file('/proc/self/gid_map', '1000 {} 1'.format(host_egid))
    setresuid(1000, 1000, 1000)
    setresgid(1000, 1000, 1000)
    sethostname('icebox')

def enter_namespace(root_dir, in_dir, out_dir):
    mount('root', root_dir, 'tmpfs', MS_NOSUID, NULL)
    chdir(root_dir)
    mkdir('proc')
    mount('proc', 'proc', 'proc', MS_NOSUID, NULL)
    mkdir('dev')
    bind_mount('/dev/null', 'dev/null', False, True, True, False)
    bind_mount('/dev/urandom', 'dev/urandom', False, True, True, False)
    mkdir('.cache')
    mount('.cache', '.cache', 'tmpfs', MS_NOSUID, 'size=16m,nr_inodes=4k')
    mkdir('tmp')
    mount('tmp', 'tmp', 'tmpfs', MS_NOSUID, 'size=16m,nr_inodes=4k')
    bind_or_link('/bin', 'bin')
    bind_or_link('/etc/alternatives', 'etc/alternatives')
    bind_or_link('/etc/java-17-openjdk', 'etc/java-17-openjdk')
    bind_or_link('/etc/mono', 'etc/mono')
    bind_or_link('/lib', 'lib')
    bind_or_link('/lib64', 'lib64')
    bind_or_link('/usr/bin', 'usr/bin')
    bind_or_link('/usr/include', 'usr/include')
    bind_or_link('/usr/lib', 'usr/lib')
    bind_or_link('/usr/lib64', 'usr/lib64')
    bind_or_link('/usr/libexec', 'usr/libexec')
    bind_or_link('/usr/share', 'usr/share')
    bind_or_link('/var/lib/ghc', 'var/lib/ghc')
    bind_mount(in_dir, 'in', True, False, True, True)
    bind_mount(out_dir, 'out', True, False, True, False)
    write_text_file('etc/fpc.cfg', '''
        -Sgic
        -Fu/usr/lib/$fpctarget-gnu/fpc/$fpcversion/units/$fpctarget
        -Fu/usr/lib/$fpctarget-gnu/fpc/$fpcversion/units/$fpctarget/*
        -Fu/usr/lib/$fpctarget-gnu/fpc/$fpcversion/units/$fpctarget/rtl
    ''')
    write_text_file('etc/passwd', 'icebox:x:1000:1000:icebox:/:/bin/bash\n')
    mkdir('old_root')
    pivot_root('.', 'old_root')
    umount2('old_root', MNT_DETACH)
    rmdir('old_root')
    bind_mount('/', '/', False, False, False, True)
