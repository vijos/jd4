import asyncio
from os import kill, path, rmdir
from signal import SIGKILL
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK, SOL_SOCKET, SO_PEERCRED
from tempfile import mkdtemp
from time import sleep

CPUACCT_CGROUP_ROOT = '/sys/fs/cgroup/cpuacct/jd4'
MEMORY_CGROUP_ROOT = '/sys/fs/cgroup/memory/jd4'

def kill_cgroup(cgroup_dir):
    killed = False
    with open(path.join(cgroup_dir, 'cgroup.procs')) as procs:
        for pid in procs:
            kill(int(pid), SIGKILL)
            killed = True
    return killed

def delete_cgroup(cgroup_dir):
    while kill_cgroup(cgroup_dir):
        sleep(.001)
    rmdir(cgroup_dir)

class CGroup(object):
    def __init__(self, socket_path, cpuacct_cgroup_dir, memory_cgroup_dir):
        self.socket_path = socket_path
        self.cpuacct_cgroup_dir = cpuacct_cgroup_dir
        self.memory_cgroup_dir = memory_cgroup_dir

    def __del__(self):
        delete_cgroup(self.cpuacct_cgroup_dir)
        delete_cgroup(self.memory_cgroup_dir)

    def listen(self):
        self.sock = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK)
        self.sock.bind(self.socket_path)
        self.sock.listen()

    async def accept_one(self):
        loop = asyncio.get_event_loop()
        accept_sock, _ = await loop.sock_accept(self.sock)
        pid = accept_sock.getsockopt(SOL_SOCKET, SO_PEERCRED)
        with open(path.join(self.cpuacct_cgroup_dir, 'tasks'), 'w') as f:
            f.write(str(pid))
        with open(path.join(self.memory_cgroup_dir, 'tasks'), 'w') as f:
            f.write(str(pid))

    @property
    def cpu_usage_ns(self):
        with open(path.join(self.cpuacct_cgroup_dir, 'cpuacct.usage')) as f:
            return int(f.read())

    @property
    def memory_limit_bytes(self):
        with open(path.join(self.memory_cgroup_dir, 'memory.limit_in_bytes')) as f:
            return int(f.read())

    @memory_limit_bytes.setter
    def memory_limit_bytes(self, value):
        with open(path.join(self.memory_cgroup_dir, 'memory.limit_in_bytes'), 'w') as f:
            f.write(str(int(value)))

    @property
    def memory_usage_bytes(self):
        with open(path.join(self.memory_cgroup_dir, 'memory.max_usage_in_bytes')) as f:
            return int(f.read())

def create_cgroup(socket_path):
    # TODO(iceboy): Initialize cgroup if interactive and necessary.
    cpuacct_cgroup_dir = mkdtemp(prefix='', dir=CPUACCT_CGROUP_ROOT)
    memory_cgroup_dir = mkdtemp(prefix='', dir=MEMORY_CGROUP_ROOT)
    return CGroup(socket_path, cpuacct_cgroup_dir, memory_cgroup_dir)

def enter_cgroup(socket_path):
    with socket(AF_UNIX, SOCK_STREAM) as sock:
        sock.connect(socket_path)
        sock.recv(1)
