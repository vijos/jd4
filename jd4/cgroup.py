import asyncio
from itertools import chain
from os import access, geteuid, kill, makedirs, path, rmdir, W_OK
from signal import SIGKILL
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK, SOL_SOCKET, SO_PEERCRED
from subprocess import call
from sys import __stdin__
from tempfile import mkdtemp
from time import sleep

from jd4.log import logger
from jd4.util import read_text_file, write_text_file

CPUACCT_CGROUP_ROOT = '/sys/fs/cgroup/cpuacct/jd4'
MEMORY_CGROUP_ROOT = '/sys/fs/cgroup/memory/jd4'
PIDS_CGROUP_ROOT = '/sys/fs/cgroup/pids/jd4'

def try_init_cgroup():
    euid = geteuid()
    if euid == 0:
        logger.warning('Running as root')
    cgroups_to_init = list()
    if not (path.isdir(CPUACCT_CGROUP_ROOT) and access(CPUACCT_CGROUP_ROOT, W_OK)):
        cgroups_to_init.append(CPUACCT_CGROUP_ROOT)
    if not (path.isdir(MEMORY_CGROUP_ROOT) and access(MEMORY_CGROUP_ROOT, W_OK)):
        cgroups_to_init.append(MEMORY_CGROUP_ROOT)
    if not (path.isdir(PIDS_CGROUP_ROOT) and access(PIDS_CGROUP_ROOT, W_OK)):
        cgroups_to_init.append(PIDS_CGROUP_ROOT)
    if cgroups_to_init:
        if euid == 0:
            logger.info('Initializing cgroup: %s', ', '.join(cgroups_to_init))
            for cgroup_to_init in cgroups_to_init:
                makedirs(cgroup_to_init, exist_ok=True)
        elif __stdin__.isatty():
            logger.info('Initializing cgroup: %s', ', '.join(cgroups_to_init))
            call(['sudo', 'sh', '-c', 'mkdir -p "{1}" && chown -R "{0}" "{1}"'.format(
                euid, '" "'.join(cgroups_to_init))])
        else:
            logger.error('Cgroup not initialized')

class CGroup:
    def __init__(self, socket_path):
        self.cpuacct_cgroup_dir = mkdtemp(prefix='', dir=CPUACCT_CGROUP_ROOT)
        self.memory_cgroup_dir = mkdtemp(prefix='', dir=MEMORY_CGROUP_ROOT)
        self.pids_cgroup_dir = mkdtemp(prefix='', dir=PIDS_CGROUP_ROOT)
        self.sock = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK)
        self.sock.bind(socket_path)
        self.sock.listen()

    def close(self):
        rmdir(self.cpuacct_cgroup_dir)
        rmdir(self.memory_cgroup_dir)
        rmdir(self.pids_cgroup_dir)

    async def accept_one(self):
        loop = asyncio.get_event_loop()
        accept_sock, _ = await loop.sock_accept(self.sock)
        pid = accept_sock.getsockopt(SOL_SOCKET, SO_PEERCRED)
        write_text_file(path.join(self.cpuacct_cgroup_dir, 'tasks'), str(pid))
        write_text_file(path.join(self.memory_cgroup_dir, 'tasks'), str(pid))
        write_text_file(path.join(self.pids_cgroup_dir, 'tasks'), str(pid))
        accept_sock.close()

    @property
    def procs(self):
        return set(chain(
            map(int, read_text_file(path.join(self.cpuacct_cgroup_dir, 'cgroup.procs')).splitlines()),
            map(int, read_text_file(path.join(self.memory_cgroup_dir, 'cgroup.procs')).splitlines()),
            map(int, read_text_file(path.join(self.pids_cgroup_dir, 'cgroup.procs')).splitlines())))

    def kill(self):
        procs = self.procs
        if procs:
            for pid in procs:
                try:
                    kill(pid, SIGKILL)
                except ProcessLookupError:
                    pass
            return True
        else:
            return False

    @property
    def cpu_usage_ns(self):
        return int(read_text_file(path.join(self.cpuacct_cgroup_dir, 'cpuacct.usage')))

    @property
    def memory_limit_bytes(self):
        return int(read_text_file(path.join(self.memory_cgroup_dir, 'memory.limit_in_bytes')))

    @memory_limit_bytes.setter
    def memory_limit_bytes(self, value):
        write_text_file(path.join(self.memory_cgroup_dir, 'memory.limit_in_bytes'), str(value))

    @property
    def memory_usage_bytes(self):
        return int(read_text_file(path.join(self.memory_cgroup_dir, 'memory.max_usage_in_bytes')))

    @property
    def pids_max(self):
        return int(read_text_file(path.join(self.pids_cgroup_dir, 'pids.max')))

    @pids_max.setter
    def pids_max(self, value):
        write_text_file(path.join(self.pids_cgroup_dir, 'pids.max'), str(value))

def enter_cgroup(socket_path):
    with socket(AF_UNIX, SOCK_STREAM) as sock:
        sock.connect(socket_path)
        sock.recv(1)
