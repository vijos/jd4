from asyncio import get_event_loop
from os import close as os_close, chdir, dup2, execve, fork, mkdir, open as os_open, path, waitpid, \
               O_RDONLY, O_WRONLY, WNOHANG, WIFSIGNALED, WTERMSIG, WEXITSTATUS
from pty import STDIN_FILENO, STDOUT_FILENO, STDERR_FILENO
from shutil import copytree, rmtree
from tempfile import mkdtemp

from jd4.cgroup import enter_cgroup
from jd4.sandbox import create_sandbox
from jd4.util import write_binary_file

SPAWN_ENV = {'PATH': '/usr/bin:/bin'}

def wait_and_reap_zombies(pid):
    _, status = waitpid(pid, 0)
    try:
        while True:
            waitpid(-1, WNOHANG)
    except ChildProcessError:
        pass
    if WIFSIGNALED(status):
        return -WTERMSIG(status)
    return WEXITSTATUS(status)

class Executable:
    def __init__(self, execute_file, execute_args):
        self.execute_file = execute_file
        self.execute_args = execute_args

    async def execute(self, sandbox, *,
                      stdin_file=None, stdout_file=None, stderr_file=None, cgroup_file=None):
        return await sandbox.marshal(lambda: self.do_execute(
            stdin_file, stdout_file, stderr_file, cgroup_file))

    def do_execute(self, stdin_file, stdout_file, stderr_file, cgroup_file):
        pid = fork()
        if not pid:
            chdir('/in/package')
            if stdin_file:
                fd = os_open(stdin_file, O_RDONLY)
                dup2(fd, STDIN_FILENO)
                os_close(fd)
            if stdout_file:
                fd = os_open(stdout_file, O_WRONLY)
                dup2(fd, STDOUT_FILENO)
                os_close(fd)
            if stderr_file:
                fd = os_open(stderr_file, O_WRONLY)
                dup2(fd, STDERR_FILENO)
                os_close(fd)
            if cgroup_file:
                enter_cgroup(cgroup_file)
            execve(self.execute_file, self.execute_args, SPAWN_ENV)
        return wait_and_reap_zombies(pid)

class Package:
    def __init__(self, package_dir, execute_file, execute_args):
        self.package_dir = package_dir
        self.execute_file = execute_file
        self.execute_args = execute_args

    def __del__(self):
        rmtree(self.package_dir)

    async def install(self, sandbox):
        loop = get_event_loop()
        await sandbox.reset()
        await loop.run_in_executor(None,
                                   copytree,
                                   path.join(self.package_dir, 'package'),
                                   path.join(sandbox.in_dir, 'package'))
        return Executable(self.execute_file, self.execute_args)

class Compiler:
    def __init__(self, compiler_file, compiler_args, code_file, execute_file, execute_args):
        self.compiler_file = compiler_file
        self.compiler_args = compiler_args
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    async def prepare(self, sandbox, code):
        loop = get_event_loop()
        await sandbox.reset()
        await loop.run_in_executor(None, write_binary_file, path.join(sandbox.in_dir, self.code_file), code)

    async def build(self, sandbox, *, output_file=None, cgroup_file=None):
        loop = get_event_loop()
        status = await sandbox.marshal(lambda: self.do_build(output_file, cgroup_file))
        if status:
            return None, status
        package_dir = mkdtemp(prefix='jd4.package.')
        await loop.run_in_executor(None,
                                   copytree,
                                   sandbox.out_dir,
                                   path.join(package_dir, 'package'))
        return Package(package_dir, self.execute_file, self.execute_args), 0

    def do_build(self, output_file, cgroup_file):
        pid = fork()
        if not pid:
            chdir('/out')
            os_close(STDIN_FILENO)
            if output_file:
                fd = os_open(output_file, O_WRONLY)
                dup2(fd, STDOUT_FILENO)
                dup2(fd, STDERR_FILENO)
                os_close(fd)
            if cgroup_file:
                enter_cgroup(cgroup_file)
            execve(self.compiler_file, self.compiler_args, SPAWN_ENV)
        return wait_and_reap_zombies(pid)

class Interpreter:
    def __init__(self, code_file, execute_file, execute_args):
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def build(self, code):
        package_dir = mkdtemp(prefix='jd4.package.')
        mkdir(path.join(package_dir, 'package'))
        write_binary_file(path.join(package_dir, 'package', self.code_file), code)
        return Package(package_dir, self.execute_file, self.execute_args)

if __name__ == '__main__':
    async def main():
        sandbox = await create_sandbox()
        fpc = Compiler('/usr/bin/fpc', ['fpc', '-o/out/foo', '/in/foo.pas'],
                       'foo.pas', 'foo', ['foo'])
        gcc = Compiler('/usr/bin/gcc', ['gcc', '-std=c99', '-o', '/out/foo', '/in/foo.c'],
                       'foo.c', 'foo', ['foo'])
        gxx = Compiler('/usr/bin/g++', ['g++', '-std=c++11', '-o', '/out/foo', '/in/foo.cc'],
                       'foo.cc', 'foo', ['foo'])
        javac = Compiler('/usr/bin/javac', ['javac', '-d', '/out', '/in/Main.java'],
                         'Main.java', '/usr/bin/java', ['java', 'Main'])
        python = Interpreter('foo.py', '/usr/bin/python', ['python', 'foo.py'])
        await fpc.prepare(sandbox, b"""begin
    writeln('hello pascal');
end.""")
        package, _ = await fpc.build(sandbox)
        for i in range(10):
            executable = await package.install(sandbox)
            await executable.execute(sandbox)
        await gcc.prepare(sandbox, b"""#include <stdio.h>
int main(void) {
    printf("hello c\\n");
}""")
        package, _ = await gcc.build(sandbox)
        for i in range(10):
            executable = await package.install(sandbox)
            await executable.execute(sandbox)
        await gxx.prepare(sandbox, b"""#include <iostream>
int main() {
    std::cout << "hello cxx\\n";
}""")
        package, _ = await gxx.build(sandbox)
        for i in range(10):
            executable = await package.install(sandbox)
            await executable.execute(sandbox)
        await javac.prepare(sandbox, b"""class Main {
    public static void main(String[] args) {
        System.out.println("hello java");
    }
}""")
        package, _ = await javac.build(sandbox)
        for i in range(10):
            executable = await package.install(sandbox)
            await executable.execute(sandbox)
        package = python.build(b"print 'hello python'\n")
        for i in range(10):
            executable = await package.install(sandbox)
            await executable.execute(sandbox)

    get_event_loop().run_until_complete(main())
