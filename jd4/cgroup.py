from asyncio import get_event_loop, shield, sleep, wait_for, TimeoutError
from itertools import chain
from os import access, cpu_count, geteuid, getpid, kill, makedirs, path, rmdir, W_OK
from signal import SIGKILL
from socket import socket, AF_UNIX, SOCK_STREAM, SOL_SOCKET, SO_PEERCRED
from subprocess import call
from sys import __stdin__
from tempfile import mkdtemp

from jd4.log import logger
from jd4.util import read_text_file, write_text_file

CGROUP2_ROOT = '/sys/fs/cgroup/jd4'
CGROUP2_DAEMON_ROOT = path.join(CGROUP2_ROOT, 'daemon')
WAIT_JITTER_NS = 5000000

def try_init_cgroup():
    euid = geteuid()
    if not (path.isdir(CGROUP2_ROOT) and access(CGROUP2_ROOT, W_OK)):
        cgroup2_subtree_control = path.join(CGROUP2_ROOT, 'cgroup.subtree_control')
        if euid == 0:
            logger.info('Initializing cgroup: %s', CGROUP2_ROOT)
            write_text_file('/sys/fs/cgroup/cgroup.subtree_control', '+cpu +memory +pids')
            makedirs(CGROUP2_ROOT, exist_ok=True)
            write_text_file(cgroup2_subtree_control, '+cpu +memory +pids')
            makedirs(CGROUP2_DAEMON_ROOT, exist_ok=True)
        elif __stdin__.isatty():
            logger.info('Initializing cgroup: %s', CGROUP2_ROOT)
            call(['sudo', 'sh', '-c',
                  '''echo "+cpu +memory +pids" > "/sys/fs/cgroup/cgroup.subtree_control" &&
                     mkdir -p "{1}" &&
                     chown -R "{0}" "{1}" &&
                     echo "+cpu +memory +pids" > "{2}" &&
                     mkdir -p "{3}" &&
                     chown -R "{0}" "{3}"'''.format(
                euid, CGROUP2_ROOT, cgroup2_subtree_control, CGROUP2_DAEMON_ROOT)])
        else:
            logger.error('Cgroup not initialized')

    # Put myself into the cgroup that I can write.
    pid = getpid()
    cgroup2_daemon_procs = path.join(CGROUP2_DAEMON_ROOT, 'cgroup.procs')
    if euid == 0:
        logger.info('Entering cgroup: %s', CGROUP2_DAEMON_ROOT)
        write_text_file(cgroup2_daemon_procs, str(pid))
    elif __stdin__.isatty():
        logger.info('Entering cgroup: %s', CGROUP2_DAEMON_ROOT)
        call(['sudo', 'sh', '-c', 'echo "{0}" > "{1}"'.format(pid, cgroup2_daemon_procs)])
    else:
        logger.error('Cgroup not entered')

class CGroup:
    def __init__(self):
        self.cgroup2_dir = mkdtemp(prefix='', dir=CGROUP2_ROOT)

    def close(self):
        rmdir(self.cgroup2_dir)

    async def accept(self, sock):
        loop = get_event_loop()
        accept_sock, _ = await loop.sock_accept(sock)
        pid = accept_sock.getsockopt(SOL_SOCKET, SO_PEERCRED)
        write_text_file(path.join(self.cgroup2_dir, 'cgroup.procs'), str(pid))
        accept_sock.close()

    @property
    def procs(self):
        return set(map(int,
                       read_text_file(path.join(self.cgroup2_dir, 'cgroup.procs')).splitlines()))

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
        return 1000 * int(read_text_file(path.join(self.cgroup2_dir, 'cpu.stat'))
                          .splitlines()[0].split()[1])

    @property
    def memory_limit_bytes(self):
        return int(read_text_file(path.join(self.cgroup2_dir, 'memory.max')))

    @memory_limit_bytes.setter
    def memory_limit_bytes(self, value):
        write_text_file(path.join(self.cgroup2_dir, 'memory.max'), str(value))

    @property
    def memory_usage_bytes(self):
        return int(read_text_file(path.join(self.cgroup2_dir, 'memory.peak')))

    @property
    def pids_max(self):
        return int(read_text_file(path.join(self.cgroup2_dir, 'pids.max')))

    @pids_max.setter
    def pids_max(self, value):
        write_text_file(path.join(self.cgroup2_dir, 'pids.max'), str(value))

def enter_cgroup(socket_path):
    with socket(AF_UNIX, SOCK_STREAM) as sock:
        sock.connect(socket_path)
        sock.recv(1)

def _get_idle():
    return float(read_text_file('/proc/uptime').split()[1])

async def wait_cgroup(sock, execute_task, cpu_limit_ns, idle_limit_ns,
                      memory_limit_bytes, process_limit):
    cgroup = CGroup()
    try:
        cgroup.memory_limit_bytes = memory_limit_bytes
        cgroup.pids_max = process_limit
        await cgroup.accept(sock)
        start_idle = _get_idle()

        while True:
            cpu_usage_ns = cgroup.cpu_usage_ns
            cpu_remain_ns = cpu_limit_ns - cpu_usage_ns
            if cpu_remain_ns <= 0:
                return cpu_usage_ns, cgroup.memory_usage_bytes
            idle_usage_ns = int((_get_idle() - start_idle) / cpu_count() * 1e9)
            idle_remain_ns = idle_limit_ns - idle_usage_ns
            if idle_remain_ns <= 0:
                return idle_usage_ns, cgroup.memory_usage_bytes
            try:
                await wait_for(shield(execute_task),
                               (min(cpu_remain_ns, idle_remain_ns) + WAIT_JITTER_NS) / 1e9)
                return cgroup.cpu_usage_ns, cgroup.memory_usage_bytes
            except TimeoutError:
                pass
    except Exception as e:
        logger.error(e)
    finally:
        while cgroup.kill():
            await sleep(.001)
        cgroup.close()
