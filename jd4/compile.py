from jd4.sandbox import create_sandbox

from os import chdir, mkdir, path, spawnve, P_WAIT
from shutil import copytree, rmtree
from tempfile import mkdtemp

SPAWN_ENV = {'PATH': '/usr/bin:/bin'}

class CompileError(Exception):
    pass

class UserRuntimeError(Exception):
    pass

class Executable:
    def __init__(self, execute_file, execute_args):
        self.execute_file = execute_file
        self.execute_args = execute_args

    def execute(self, sandbox):
        sandbox.marshal(self.do_execute)

    def do_execute(self):
        chdir('/io/package')
        # TODO(iceboy): Time/memory limit.
        # TODO(iceboy): Input/output.
        # TODO(iceboy): Measure time and memory usage.
        # TODO(iceboy): dropcaps, setuid?
        if spawnve(P_WAIT, self.execute_file, self.execute_args, SPAWN_ENV) != 0:
            raise UserRuntimeError

class Package:
    def __init__(self, package_dir, execute_file, execute_args):
        self.package_dir = package_dir
        self.execute_file = execute_file
        self.execute_args = execute_args

    def __del__(self):
        rmtree(self.package_dir)

    def install(self, sandbox):
        sandbox.reset()
        copytree(path.join(self.package_dir, 'package'), path.join(sandbox.io_dir, 'package'))
        return Executable(self.execute_file, self.execute_args)

class Compiler:
    def __init__(self, compiler_file, compiler_args, code_file, execute_file, execute_args):
        self.compiler_file = compiler_file
        self.compiler_args = compiler_args
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def build(self, sandbox, code):
        sandbox.reset()
        sandbox.marshal(lambda: self.do_build(code))
        package_dir = mkdtemp(prefix='jd4.package.')
        copytree(sandbox.io_dir, path.join(package_dir, 'package'))
        return Package(package_dir, self.execute_file, self.execute_args)

    def do_build(self, code):
        chdir('/')
        with open(self.code_file, 'wb') as f:
            f.write(code)
        # TODO(iceboy): Time/memory limit.
        # TODO(iceboy): Read compiler output.
        # TODO(iceboy): dropcaps, setuid?
        if spawnve(P_WAIT, self.compiler_file, self.compiler_args, SPAWN_ENV) != 0:
            raise CompileError

class Interpreter:
    def __init__(self, code_file, execute_file, execute_args):
        self.code_file = code_file
        self.execute_file = execute_file
        self.execute_args = execute_args

    def build(self, _sandbox, code):
        package_dir = mkdtemp(prefix='jd4.package.')
        mkdir(path.join(package_dir, 'package'))
        with open(path.join(package_dir, 'package', self.code_file), 'wb') as f:
            f.write(code)
        return Package(package_dir, self.execute_file, self.execute_args)

if __name__ == '__main__':
    sandbox = create_sandbox()
    gcc = Compiler('/usr/bin/gcc', ['gcc', '-o', '/io/foo', 'foo.c'],
                   'foo.c', 'foo', ['foo'])
    javac = Compiler('/usr/bin/javac', ['javac', '-d', 'io', 'Program.java'],
                     'Program.java', '/usr/bin/java', ['java', 'Program'])
    python = Interpreter('foo.py', '/usr/bin/python', ['python', 'foo.py'])
    package = gcc.build(sandbox, b"""#include <stdio.h>
int main(void) {
    printf("hello c\\n");
}""")
    for i in range(10):
        package.install(sandbox).execute(sandbox)
    package = javac.build(sandbox, b"""class Program {
    public static void main(String[] args) {
        System.out.println("hello java");
    }
}""")
    for i in range(10):
        package.install(sandbox).execute(sandbox)
    package = python.build(sandbox, b"print 'hello python'\n")
    for i in range(10):
        package.install(sandbox).execute(sandbox)
