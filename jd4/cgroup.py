from os import kill, path, rmdir
from signal import SIGKILL
from socket import socket, AF_UNIX, SOCK_STREAM, SOL_SOCKET, SO_PEERCRED
from tempfile import mkdtemp
from time import sleep

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
    def __init__(self, socket_path, memory_cgroup_dir):
        self.socket_path = socket_path
        self.memory_cgroup_dir = memory_cgroup_dir

    def __del__(self):
        delete_cgroup(self.memory_cgroup_dir)

    def start(self, executor):
        self.sock = socket(AF_UNIX, SOCK_STREAM)
        executor.submit(self.do_start)

    def do_start(self):
        self.sock.bind(self.socket_path)
        self.sock.listen()
        accept_sock, _ = self.sock.accept()
        self.sock.close()
        pid = accept_sock.getsockopt(SOL_SOCKET, SO_PEERCRED)
        with open(path.join(self.memory_cgroup_dir, 'tasks'), 'w') as tasks:
            tasks.write(str(pid))
        accept_sock.close()

    @property
    def memory_usage_bytes(self):
        with open(path.join(self.memory_cgroup_dir, 'memory.max_usage_in_bytes')) as max_usage_in_bytes:
            return int(max_usage_in_bytes.read())

def create_cgroup(socket_path, memory_limit_bytes, executor):
    # TODO(iceboy): Initialize cgroup if interactive and necessary.
    memory_cgroup_dir = mkdtemp(prefix='', dir=MEMORY_CGROUP_ROOT)
    if memory_limit_bytes:
        with open(path.join(memory_cgroup_dir, 'memory.limit_in_bytes'), 'w') as limit_in_bytes:
            limit_in_bytes.write(str(memory_limit_bytes))
    cgroup = CGroup(socket_path, memory_cgroup_dir)
    cgroup.start(executor)
    return cgroup

def enter_cgroup(socket_path):
    sock = socket(AF_UNIX, SOCK_STREAM)
    sock.connect(socket_path)
    sock.recv(1)
    sock.close()
