import cloudpickle
from asyncio import gather, get_event_loop, open_connection
from os import fork, listdir, mkdir, path, remove, spawnve, waitpid, P_WAIT
from shutil import rmtree
from socket import socketpair
from struct import pack, unpack
from sys import exit
from tempfile import mkdtemp

from jd4._sandbox import create_namespace, enter_namespace
from jd4.log import logger

MNT_DETACH = 2

def remove_under(*dirnames):
    for dirname in dirnames:
        for name in listdir(dirname):
            full_path = path.join(dirname, name)
            if path.isdir(full_path):
                rmtree(full_path)
            else:
                remove(full_path)

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
                     self.marshal(lambda: remove_under('/tmp')))

    async def marshal(self, func):
        cloudpickle.dump(func, self.writer)
        length, = unpack('I', await self.reader.read(4))
        ret, err = cloudpickle.loads(await self.reader.read(length))
        if err:
            raise err
        return ret

    async def backdoor(self):
        return await self.marshal(lambda: spawnve(
            P_WAIT, '/bin/bash', ['bunny'], {'PATH': '/usr/bin:/bin', 'HOME': '/'}))

def _handle_child(child_socket, root_dir, in_dir, out_dir):
    create_namespace()
    pid = fork()
    if pid != 0:
        child_socket.close()
        waitpid(pid, 0)
        exit()
    enter_namespace(root_dir, in_dir, out_dir)

    socket_file = child_socket.makefile('rwb')
    while True:
        try:
            func = cloudpickle.load(socket_file)
        except EOFError:
            exit()
        try:
            ret, err = func(), None
        except Exception as e:
            ret, err = None, e
        data = cloudpickle.dumps((ret, err))
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

async def create_sandbox():
    sandbox, = await create_sandboxes(1)
    return sandbox

if __name__ == '__main__':
    async def main():
        sandbox = await create_sandbox()
        logger.info('sandbox_dir: %s', sandbox.sandbox_dir)
        logger.info('return value: %d', await sandbox.backdoor())

    get_event_loop().run_until_complete(main())
