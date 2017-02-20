from butter.clone import unshare, CLONE_NEWNS, CLONE_NEWUTS, CLONE_NEWIPC, CLONE_NEWUSER, CLONE_NEWPID, CLONE_NEWNET
from butter.system import mount, pivot_root, umount, MS_BIND, MS_RDONLY, MS_REMOUNT
from collections import namedtuple
from itertools import chain
from os import chdir, execve, fork, getpid, mkdir, path, rmdir, waitpid
from shutil import rmtree
from sys import exit
from tempfile import mkdtemp

MNT_DETACH = 2

MountPoint = namedtuple('MountPoint', ['src', 'target', 'rdonly'])

DEFAULT_MOUNT_POINTS = [
    MountPoint('/bin', '/bin', True),
    MountPoint('/etc', '/etc', True),
    MountPoint('/lib', '/lib', True),
    MountPoint('/lib64', '/lib64', True),
    MountPoint('/usr', '/usr', True),
]

DEFAULT_ENV = {'PATH': '/usr/bin:/bin'}

SELF_PID = getpid()

def bind_mount(src, target, *, makedir=True, rdonly=True):
    if makedir:
        mkdir(target)
    mount(src, target, '', MS_BIND)
    if rdonly:
        mount(src, target, '', MS_BIND | MS_REMOUNT | MS_RDONLY)

def sandbox(extra_mount_points, callback, *, fork_twice=True, mount_proc=True):
    root = mkdtemp(prefix='jd4.sandbox.')
    pid = fork()
    if pid != 0:
        try:
            waitpid(pid, 0)
        finally:
            rmtree(root)
        return
    unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
            CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET)
    if fork_twice:
        pid = fork()
        if pid != 0:
            waitpid(pid, 0)
            exit()
    mount('tmpfs', root, 'tmpfs')
    if mount_proc:
        mkdir(path.join(root, 'proc'))
        mount('proc', path.join(root, 'proc'), 'proc')
    for mount_point in chain(DEFAULT_MOUNT_POINTS, extra_mount_points):
        bind_mount(mount_point.src, root + path.sep + mount_point.target, rdonly=mount_point.rdonly)
    chdir(root)
    mkdir('old_root')
    pivot_root('.', 'old_root')
    umount('old_root', MNT_DETACH)
    rmdir('old_root')
    callback()
    exit()

class SandboxedExecutable:
    def __init__(self, execute_dir, execute_file, execute_args):
        self.execute_dir = execute_dir
        self.execute_file = execute_file
        self.execute_args = execute_args

    def __del__(self):
        if getpid() == SELF_PID:
            rmtree(self.execute_dir)

    def execute(self):
        sandbox([MountPoint(self.execute_dir, '/in', True)], self.do_execute)

    def do_execute(self):
        chdir('in')
        execve(self.execute_file, self.execute_args, DEFAULT_ENV)

class SandboxedCompiler:
    def __init__(self, compiler_file, compiler_args, code_file, execute_file, execute_args):
        self.compiler_file = compiler_file
        self.compiler_args = compiler_args
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def compile(self, code):
        execute_dir = mkdtemp(prefix='jd4.execute.')
        sandbox([MountPoint(execute_dir, '/out', False)], lambda: self.do_compile(code))
        return SandboxedExecutable(execute_dir, self.execute_file, self.execute_args)

    def do_compile(self, code):
        with open(self.code_file, 'wb') as f:
            f.write(code)
        execve(self.compiler_file, self.compiler_args, DEFAULT_ENV)

class SandboxedInterpreter:
    def __init__(self, code_file, execute_file, execute_args):
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def compile(self, code):
        execute_dir = mkdtemp(prefix='jd4.execute.')
        with open(path.join(execute_dir, self.code_file), 'wb') as f:
            f.write(code)
        return SandboxedExecutable(execute_dir, self.execute_file, self.execute_args)

if __name__ == '__main__':
    gcc = SandboxedCompiler('/usr/bin/gcc', ['gcc', '-o', '/out/foo', 'foo.c'],
                            'foo.c', 'foo', ['foo'])
    javac = SandboxedCompiler('/usr/bin/javac', ['javac', '-d', 'out', 'Program.java'],
                              'Program.java', '/usr/bin/java', ['java', 'Program'])
    python = SandboxedInterpreter('foo.py', '/usr/bin/python', ['python', 'foo.py'])
    exe = gcc.compile(b"""#include <stdio.h>
int main(void) {
    printf("hello c\\n");
}""")
    for i in range(10):
        exe.execute()
    exe = javac.compile(b"""class Program {
    public static void main(String[] args) {
        System.out.println("hello java");
    }
}""")
    for i in range(10):
        exe.execute()
    exe = python.compile(b"print 'hello python'\n")
    for i in range(10):
        exe.execute()
