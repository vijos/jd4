import asyncio
from os import access, geteuid, kill, makedirs, path, rmdir, W_OK
from signal import SIGKILL
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK, SOL_SOCKET, SO_PEERCRED
from subprocess import call
from sys import __stdin__
from tempfile import mkdtemp
from time import sleep

from jd4.logging import logger

CPUACCT_CGROUP_ROOT = '/sys/fs/cgroup/cpuacct/jd4'
MEMORY_CGROUP_ROOT = '/sys/fs/cgroup/memory/jd4'

def try_init_cgroup():
    if not (path.isdir(CPUACCT_CGROUP_ROOT) and access(CPUACCT_CGROUP_ROOT, W_OK) and
            path.isdir(MEMORY_CGROUP_ROOT) and access(MEMORY_CGROUP_ROOT, W_OK)):
        euid = geteuid()
        if euid == 0:
            logger.warning('Running as root')
            logger.info('Initializing cgroup')
            makedirs(CPUACCT_CGROUP_ROOT, exist_ok=True)
            makedirs(MEMORY_CGROUP_ROOT, exist_ok=True)
        elif __stdin__.isatty():
            logger.info('Initializing cgroup')
            call(['sudo', 'sh', '-c', 'mkdir -p "{1}" "{2}" && chown -R "{0}" "{1}" "{2}"'.format(
                euid, CPUACCT_CGROUP_ROOT, MEMORY_CGROUP_ROOT)])
        else:
            logger.error('CGroup not initialized')

class CGroup(object):
    def __init__(self, socket_path):
        self.cpuacct_cgroup_dir = mkdtemp(prefix='', dir=CPUACCT_CGROUP_ROOT)
        self.memory_cgroup_dir = mkdtemp(prefix='', dir=MEMORY_CGROUP_ROOT)
        self.sock = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK)
        self.sock.bind(socket_path)
        self.sock.listen()

    def __del__(self):
        while self.kill():
            sleep(.001)
        rmdir(self.cpuacct_cgroup_dir)
        rmdir(self.memory_cgroup_dir)

    async def accept_one(self):
        loop = asyncio.get_event_loop()
        accept_sock, _ = await loop.sock_accept(self.sock)
        pid = accept_sock.getsockopt(SOL_SOCKET, SO_PEERCRED)
        with open(path.join(self.cpuacct_cgroup_dir, 'tasks'), 'w') as f:
            f.write(str(pid))
        with open(path.join(self.memory_cgroup_dir, 'tasks'), 'w') as f:
            f.write(str(pid))
        accept_sock.close()

    @property
    def pids(self):
        result = set()
        with open(path.join(self.cpuacct_cgroup_dir, 'cgroup.procs')) as procs:
            for pid in procs:
                result.add(int(pid))
        with open(path.join(self.memory_cgroup_dir, 'cgroup.procs')) as procs:
            for pid in procs:
                result.add(int(pid))
        return result

    def kill(self):
        pids = self.pids
        if pids:
            for pid in pids:
                kill(pid, SIGKILL)
            return True
        else:
            return False

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

def enter_cgroup(socket_path):
    with socket(AF_UNIX, SOCK_STREAM) as sock:
        sock.connect(socket_path)
        sock.recv(1)
