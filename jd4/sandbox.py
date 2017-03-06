import cloudpickle
from asyncio import get_event_loop, open_connection
from butter.clone import unshare, CLONE_NEWNS, CLONE_NEWUTS, CLONE_NEWIPC, CLONE_NEWUSER, CLONE_NEWPID, CLONE_NEWNET
from butter.system import mount, pivot_root, umount, MS_BIND, MS_NOSUID, MS_RDONLY, MS_REMOUNT
from os import chdir, fork, getegid, geteuid, listdir, makedirs, mkdir, path, remove, rmdir, setresgid, setresuid, spawnve, waitpid, P_WAIT, O_NONBLOCK
from shutil import rmtree
from socket import sethostname, socketpair
from struct import pack, unpack
from sys import exit
from tempfile import mkdtemp

from jd4.util import write_text_file

MNT_DETACH = 2

def bind_mount(src, target, *, ignore_missing=True, makedir=True, rdonly=True):
    if ignore_missing and not path.isdir(src):
        return
    if makedir:
        makedirs(target)
    mount(src, target, '', MS_BIND | MS_NOSUID)
    if rdonly:
        mount(src, target, '', MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID)

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
        await loop.run_in_executor(None, remove_under, self.in_dir, self.out_dir)

    async def marshal(self, func):
        cloudpickle.dump(func, self.writer)
        length, = unpack('I', await self.reader.read(4))
        ret, err = cloudpickle.loads(await self.reader.read(length))
        if err:
            raise err
        return ret

    async def backdoor(self):
        return await self.marshal(lambda: spawnve(
            P_WAIT, '/bin/bash', ['bunny'], {'PATH': '/usr/bin:/bin'}))

async def create_sandbox(*, fork_twice=True, mount_proc=True):
    sandbox_dir = mkdtemp(prefix='jd4.sandbox.')
    root_dir = path.join(sandbox_dir, 'root')
    mkdir(root_dir)
    in_dir = path.join(sandbox_dir, 'in')
    mkdir(in_dir)
    out_dir = path.join(sandbox_dir, 'out')
    mkdir(out_dir)
    parent_socket, child_socket = socketpair()

    # Fork child and unshare.
    pid = fork()
    if pid != 0:
        child_socket.close()
        reader, writer = await open_connection(sock=parent_socket)
        return Sandbox(pid, sandbox_dir, in_dir, out_dir, reader, writer)
    parent_socket.close()
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
    if fork_twice:
        pid = fork()
        if pid != 0:
            child_socket.close()
            waitpid(pid, 0)
            exit()

    # Prepare sandbox filesystem.
    mount('tmpfs', root_dir, 'tmpfs', MS_NOSUID)
    if mount_proc:
        proc_dir = path.join(root_dir, 'proc')
        mkdir(proc_dir)
        mount('proc', proc_dir, 'proc', MS_NOSUID)
    bind_mount('/bin', path.join(root_dir, 'bin'))
    bind_mount('/etc/alternatives', path.join(root_dir, 'etc/alternatives'))
    bind_mount('/lib', path.join(root_dir, 'lib'))
    bind_mount('/lib64', path.join(root_dir, 'lib64'))
    bind_mount('/usr/bin', path.join(root_dir, 'usr/bin'))
    bind_mount('/usr/include', path.join(root_dir, 'usr/include'))
    bind_mount('/usr/lib', path.join(root_dir, 'usr/lib'))
    bind_mount('/usr/lib64', path.join(root_dir, 'usr/lib64'))
    bind_mount('/usr/libexec', path.join(root_dir, 'usr/libexec'))
    bind_mount(in_dir, path.join(root_dir, 'in'))
    bind_mount(out_dir, path.join(root_dir, 'out'), rdonly=False)
    chdir(root_dir)
    mkdir('old_root')
    pivot_root('.', 'old_root')
    umount('old_root', MNT_DETACH)
    rmdir('old_root')
    write_text_file('/etc/passwd', 'icebox:x:1000:1000:icebox:/:/bin/bash\n')
    bind_mount('/', '/', makedir=False)

    # Execute pickles.
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

if __name__ == '__main__':
    async def main():
        sandbox = await create_sandbox()
        print('sandbox_dir: {}'.format(sandbox.sandbox_dir))
        print('return value: {}'.format(await sandbox.backdoor()))

    get_event_loop().run_until_complete(main())
