import csv
import re
import tarfile
from asyncio import gather, get_event_loop
from functools import partial
from io import BytesIO, IOBase, TextIOWrapper
from itertools import islice
from os import mkfifo, path
from ruamel import yaml
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK
from threading import RLock
from zipfile import ZipFile, BadZipFile

from jd4._compare import compare_stream
from jd4.cgroup import wait_cgroup
from jd4.status import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                       STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED
from jd4.util import read_pipe

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 8192
DEFAULT_TIME_MS = 1000
DEFAULT_MEM_KB = 262144
PROCESS_LIMIT = 64

class CaseBase:
    def __init__(self, time_limit_ns, memory_limit_bytes, process_limit, score):
        self.time_limit_ns = time_limit_ns
        self.memory_limit_bytes = memory_limit_bytes
        self.process_limit = process_limit
        self.score = score

    async def judge(self, sandbox, package):
        loop = get_event_loop()
        executable = await package.install(sandbox)
        stdin_file = path.join(sandbox.in_dir, 'stdin')
        mkfifo(stdin_file)
        stdout_file = path.join(sandbox.in_dir, 'stdout')
        mkfifo(stdout_file)
        stderr_file = path.join(sandbox.in_dir, 'stderr')
        mkfifo(stderr_file)
        with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as cgroup_sock:
            cgroup_sock.bind(path.join(sandbox.in_dir, 'cgroup'))
            cgroup_sock.listen()
            execute_task = loop.create_task(executable.execute(
                sandbox,
                stdin_file='/in/stdin',
                stdout_file='/in/stdout',
                stderr_file='/in/stderr',
                cgroup_file='/in/cgroup'))
            others_task = gather(
                loop.run_in_executor(None, self.do_stdin, stdin_file),
                loop.run_in_executor(None, self.do_stdout, stdout_file),
                read_pipe(stderr_file, MAX_STDERR_SIZE),
                wait_cgroup(cgroup_sock,
                            execute_task,
                            self.time_limit_ns,
                            self.memory_limit_bytes,
                            self.process_limit))
            execute_status = await execute_task
            _, correct, stderr, (time_usage_ns, memory_usage_bytes) = \
                await others_task
        if memory_usage_bytes >= self.memory_limit_bytes:
            status = STATUS_MEMORY_LIMIT_EXCEEDED
            score = 0
        elif time_usage_ns >= self.time_limit_ns:
            status = STATUS_TIME_LIMIT_EXCEEDED
            score = 0
        elif execute_status:
            status = STATUS_RUNTIME_ERROR
            score = 0
        elif not correct:
            status = STATUS_WRONG_ANSWER
            score = 0
        else:
            status = STATUS_ACCEPTED
            score = self.score
        return status, score, time_usage_ns, memory_usage_bytes, stderr

def dos2unix(src, dst):
    while True:
        buf = src.read(CHUNK_SIZE)
        if not buf:
            break
        buf = buf.replace(b'\r', b'')
        dst.write(buf)

class DefaultCase(CaseBase):
    def __init__(self, open_input, open_output, time_ns, memory_bytes, score):
        super().__init__(time_ns, memory_bytes, PROCESS_LIMIT, score)
        self.open_input = open_input
        self.open_output = open_output

    def do_stdin(self, stdin_file):
        try:
            with self.open_input() as src, open(stdin_file, 'wb') as dst:
                dos2unix(src, dst)
        except BrokenPipeError:
            pass

    def do_stdout(self, stdout_file):
        with self.open_output() as ans, open(stdout_file, 'rb') as out:
            return compare_stream(ans, out)

class APlusBCase(CaseBase):
    def __init__(self, a, b, time_limit_ns, memory_limit_bytes, score):
        super().__init__(time_limit_ns, memory_limit_bytes, PROCESS_LIMIT, score)
        self.a = a
        self.b = b

    def do_stdin(self, stdin_file):
        try:
            with open(stdin_file, 'w') as file:
                file.write('{} {}\n'.format(self.a, self.b))
        except BrokenPipeError:
            pass

    def do_stdout(self, stdout_file):
        with open(stdout_file, 'rb') as file:
            return compare_stream(BytesIO(str(self.a + self.b).encode()), file)

class FormatError(Exception):
    pass

def read_legacy_cases(config, open):
    num_cases = int(config.readline())
    for line in islice(csv.reader(config, delimiter='|'), num_cases):
        input, output, time_str, score_str = line[:4]
        try:
            memory_kb = float(line[4])
        except (IndexError, ValueError):
            memory_kb = DEFAULT_MEM_KB
        yield DefaultCase(partial(open, path.join('input', input)),
                          partial(open, path.join('output', output)),
                          int(float(time_str) * 1000000000),
                          int(memory_kb * 1024),
                          int(score_str))

TIME_RE = re.compile(r'([0-9]+(?:\.[0-9]*)?)([mun]?)s?')
TIME_UNITS = {'': 1000000000, 'm': 1000000, 'u': 1000, 'n': 1}
MEMORY_RE = re.compile(r'([0-9]+(?:\.[0-9]*)?)([kmg]?)b?')
MEMORY_UNITS = {'': 1, 'k': 1024, 'm': 1048576, 'g': 1073741824}

def read_yaml_cases(config, open):
    for case in yaml.safe_load(config)['cases']:
        time = TIME_RE.fullmatch(case['time'])
        if not time:
            raise FormatError(case['time'], 'error parsing time')
        memory = MEMORY_RE.fullmatch(case['memory'])
        if not memory:
            raise FormatError(case['memory'], 'error parsing memory')
        yield DefaultCase(
            partial(open, case['input']),
            partial(open, case['output']),
            int(float(time.group(1)) * TIME_UNITS[time.group(2)]),
            int(float(memory.group(1)) * MEMORY_UNITS[memory.group(2)]),
            int(case['score']))

def try_open_zip(file):
    try:
        zip_file = ZipFile(file)
    except BadZipFile:
        return None
    canonical_dict = dict((name.lower(), name)
                          for name in zip_file.namelist())
    def open(name):
        try:
            return zip_file.open(canonical_dict[name.lower()])
        except KeyError:
            raise FileNotFoundError(name) from None
    return open

def try_open_tar(file):
    try:
        tar_file = tarfile.open(fileobj=file)
    except tarfile.TarError:
        return None
    lock = RLock()
    def open(name):
        try:
            with lock:
                file = tar_file.extractfile(name)
        except KeyError:
            raise FileNotFoundError(name) from None
        unlocked_read = file.read
        def locked_read(n=-1):
            with lock:
                return unlocked_read(n)
        file.read = locked_read
        return file
    return open

def read_cases(file):
    open = try_open_zip(file)
    if not open:
        file.seek(0)
        open = try_open_tar(file)
        if not open:
            raise FormatError(file, 'not a zip file or tar file')
    try:
        config = TextIOWrapper(open('config.ini'), encoding='utf-8')
        return read_legacy_cases(config, open)
    except FileNotFoundError:
        pass
    try:
        config = open('config.yaml')
        return read_yaml_cases(config, open)
    except FileNotFoundError:
        pass
    raise FormatError('config file not found')
