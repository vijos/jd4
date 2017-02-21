import cloudpickle
from butter.clone import unshare, CLONE_NEWNS, CLONE_NEWUTS, CLONE_NEWIPC, CLONE_NEWUSER, CLONE_NEWPID, CLONE_NEWNET
from butter.system import mount, pivot_root, umount, MS_BIND, MS_RDONLY, MS_REMOUNT
from os import chdir, close, fdopen, fork, listdir, mkdir, path, pipe, remove, rmdir, spawnve, waitpid, P_WAIT
from shutil import rmtree
from sys import exit
from tempfile import mkdtemp

MNT_DETACH = 2

def bind_mount(src, target, *, makedir=True, rdonly=True):
    if makedir:
        mkdir(target)
    mount(src, target, '', MS_BIND)
    if rdonly:
        mount(src, target, '', MS_BIND | MS_REMOUNT | MS_RDONLY)

class Sandbox:
    def __init__(self, pid, sandbox_dir, io_dir, request_writer, response_reader):
        self.pid = pid
        self.sandbox_dir = sandbox_dir
        self.io_dir = io_dir
        self.request_writer = request_writer
        self.response_reader = response_reader

    def __del__(self):
        self.request_writer.close()
        waitpid(self.pid, 0)
        rmtree(self.sandbox_dir)

    def reset(self):
        for name in listdir(self.io_dir):
            full_path = path.join(self.io_dir, name)
            if path.isdir(full_path):
                rmtree(full_path)
            else:
                remove(full_path)

    def marshal(self, func):
        cloudpickle.dump(func, self.request_writer)
        self.request_writer.flush()
        ret, err = cloudpickle.load(self.response_reader)
        if err:
            raise err
        return ret

    def backdoor(self):
        return self.marshal(lambda: spawnve(
            P_WAIT, '/bin/bash', ['bunny'], {'PATH': '/usr/bin:/bin'}))

    @staticmethod
    def create(*, fork_twice=True, mount_proc=True):
        sandbox_dir = mkdtemp(prefix='jd4.sandbox.')
        root_dir = path.join(sandbox_dir, 'root')
        mkdir(root_dir)
        io_dir = path.join(sandbox_dir, 'io')
        mkdir(io_dir)
        request_pipe_r, request_pipe_w = pipe()
        response_pipe_r, response_pipe_w = pipe()

        # Fork child and unshare.
        pid = fork()
        if pid != 0:
            close(request_pipe_r)
            close(response_pipe_w)
            request_writer = fdopen(request_pipe_w, 'wb')
            response_reader = fdopen(response_pipe_r, 'rb')
            return Sandbox(pid, sandbox_dir, io_dir, request_writer, response_reader)
        close(request_pipe_w)
        close(response_pipe_r)
        unshare(CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC |
                CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET)
        if fork_twice:
            pid = fork()
            if pid != 0:
                close(request_pipe_r)
                close(response_pipe_w)
                waitpid(pid, 0)
                exit()
        request_reader = fdopen(request_pipe_r, 'rb')
        response_writer = fdopen(response_pipe_w, 'wb')

        # Prepare sandbox filesystem.
        mount('tmpfs', root_dir, 'tmpfs')
        if mount_proc:
            proc_dir = path.join(root_dir, 'proc')
            mkdir(proc_dir)
            mount('proc', proc_dir, 'proc')
        bind_mount('/bin', path.join(root_dir, 'bin'))
        bind_mount('/etc', path.join(root_dir, 'etc'))
        bind_mount('/lib', path.join(root_dir, 'lib'))
        bind_mount('/lib64', path.join(root_dir, 'lib64'))
        bind_mount('/usr', path.join(root_dir, 'usr'))
        bind_mount(io_dir, path.join(root_dir, 'io'), rdonly=False)
        chdir(root_dir)
        mkdir('old_root')
        pivot_root('.', 'old_root')
        umount('old_root', MNT_DETACH)
        rmdir('old_root')

        # Execute pickles.
        while True:
            try:
                func = cloudpickle.load(request_reader)
            except EOFError:
                exit()
            try:
                ret, err = func(), None
            except Exception as e:
                ret, err = None, e
            cloudpickle.dump((ret, err), response_writer)
            response_writer.flush()

if __name__ == '__main__':
    sb = Sandbox.create()
    print('io_dir: {}'.format(sb.io_dir))
    print('return value: {}'.format(sb.backdoor()))
