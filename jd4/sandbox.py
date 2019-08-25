import pickle
from asyncio import gather, get_event_loop, open_connection
from os import close as os_close, chdir, dup2, execve, fork, mkdir, \
               open as os_open, path, set_inheritable, spawnve, waitpid, \
               O_RDONLY, O_WRONLY, P_WAIT
from pty import STDIN_FILENO, STDOUT_FILENO, STDERR_FILENO
from shutil import rmtree
from socket import socketpair
from struct import pack, unpack
from sys import exit
from tempfile import mkdtemp

from jd4._sandbox import create_namespace, enter_namespace
from jd4.cgroup import enter_cgroup
from jd4.log import logger
from jd4.util import remove_under, wait_and_reap_zombies

EXTRA_FILENO = 3
SPAWN_ENV = {'PATH': '/usr/bin:/bin', 'HOME': '/'}

SANDBOX_BACKDOOR = 1
SANDBOX_RESET_CHILD = 2
SANDBOX_COMPILE = 3
SANDBOX_EXECUTE = 4

class Sandbox:
    def __init__(self, pid, sandbox_dir, in_dir, out_dir, reader, writer):
        self.pid = pid
        self.sandbox_dir = sandbox_dir
        self.in_dir = in_dir
        self.out_dir = out_dir
        self.reader = reader
        self.writer = writer

    def __del__(self):
        self.writer.write_eof()
        waitpid(self.pid, 0)
        rmtree(self.sandbox_dir)

    async def reset(self):
        loop = get_event_loop()
        await gather(loop.run_in_executor(None, remove_under, self.in_dir, self.out_dir),
                     self.call(SANDBOX_RESET_CHILD))

    async def call(self, command, *args):
        pickle.dump((command, *args), self.writer)
        length, = unpack('I', await self.reader.read(4))
        ret, err = pickle.loads(await self.reader.read(length))
        if err:
            raise err
        return ret

    async def backdoor(self):
        return await self.call(SANDBOX_BACKDOOR)

def _handle_backdoor():
    return spawnve(P_WAIT, '/bin/bash', ['bunny'], SPAWN_ENV)

def _handle_reset_child():
    remove_under('/tmp')

def _handle_compile(compiler_file, compiler_args, output_file, cgroup_file):
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
        execve(compiler_file, compiler_args, SPAWN_ENV)
    return wait_and_reap_zombies(pid)


def _handle_execute(execute_file,
                    execute_args,
                    stdin_file,
                    stdout_file,
                    stderr_file,
                    extra_file,
                    cgroup_file):
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
        if extra_file:
            fd = os_open(extra_file, O_RDONLY)
            if fd == EXTRA_FILENO:
                set_inheritable(fd, True)
            else:
                dup2(fd, EXTRA_FILENO)
                os_close(fd)
        if cgroup_file:
            enter_cgroup(cgroup_file)
        execve(execute_file, execute_args, SPAWN_ENV)
    return wait_and_reap_zombies(pid)

_HANDLERS = {
    SANDBOX_BACKDOOR: _handle_backdoor,
    SANDBOX_RESET_CHILD: _handle_reset_child,
    SANDBOX_COMPILE: _handle_compile,
    SANDBOX_EXECUTE: _handle_execute,
}

def _handle_child(child_socket, root_dir, in_dir, out_dir):
    create_namespace()
    pid = fork()
    if pid != 0:
        child_socket.close()
        waitpid(pid, 0)
        return exit()

    enter_namespace(root_dir, in_dir, out_dir)
    socket_file = child_socket.makefile('rwb')
    while True:
        try:
            command, *args = pickle.load(socket_file)
        except EOFError:
            return exit()
        try:
            ret, err = _HANDLERS[command](*args), None
        except Exception as e:
            ret, err = None, e
        data = pickle.dumps((ret, err))
        socket_file.write(pack('I', len(data)))
        socket_file.write(data)
        socket_file.flush()

def create_sandboxes(n):
    parent_sockets = list()
    sandbox_params = list()
    for i in range(n):
        sandbox_dir = mkdtemp(prefix='jd4.sandbox.')
        root_dir = path.join(sandbox_dir, 'root')
        mkdir(root_dir)
        in_dir = path.join(sandbox_dir, 'in')
        mkdir(in_dir)
        out_dir = path.join(sandbox_dir, 'out')
        mkdir(out_dir)
        parent_socket, child_socket = socketpair()
        parent_sockets.append(parent_socket)

        pid = fork()
        if pid == 0:
            for parent_socket in parent_sockets:
                parent_socket.close()
            _handle_child(child_socket, root_dir, in_dir, out_dir)
        child_socket.close()
        sandbox_params.append((pid, sandbox_dir, in_dir, out_dir, parent_socket))

    async def helper(pid, sandbox_dir, in_dir, out_dir, parent_socket):
        reader, writer = await open_connection(sock=parent_socket)
        return Sandbox(pid, sandbox_dir, in_dir, out_dir, reader, writer)

    return gather(*[helper(*sp) for sp in sandbox_params])

if __name__ == '__main__':
    sandboxes_task = create_sandboxes(1)

    async def main():
        sandbox, = await sandboxes_task
        logger.info('sandbox_dir: %s', sandbox.sandbox_dir)
        logger.info('return value: %d', await sandbox.backdoor())

    get_event_loop().run_until_complete(main())
