import csv
import re
from asyncio import gather, get_event_loop
from functools import partial
from io import BytesIO, TextIOWrapper
from itertools import islice
from os import link, mkfifo, path
from ruamel import yaml
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK
from threading import RLock
from zipfile import ZipFile, BadZipFile

from jd4._compare import compare_stream
from jd4.cgroup import wait_cgroup
from jd4.compile import build
from jd4.error import FormatError
from jd4.pool import get_sandbox, put_sandbox
from jd4.status import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, \
                       STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED, \
                       STATUS_RUNTIME_ERROR, STATUS_SYSTEM_ERROR
from jd4.util import read_pipe, parse_memory_bytes, parse_time_ns

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 8192
DEFAULT_TIME_NS = 1000000000
DEFAULT_MEMORY_BYTES = 268435456
PROCESS_LIMIT = 64

class CaseBase:
    def __init__(self, time_limit_ns, memory_limit_bytes, process_limit, score):
        self.time_limit_ns = time_limit_ns
        self.memory_limit_bytes = memory_limit_bytes
        self.process_limit = process_limit
        self.score = score

    async def judge(self, package):
        loop = get_event_loop()
        sandbox, = await get_sandbox(1)
        try:
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
                    loop.run_in_executor(None, self.do_input, stdin_file),
                    loop.run_in_executor(None, self.do_output, stdout_file),
                    read_pipe(stderr_file, MAX_STDERR_SIZE),
                    wait_cgroup(cgroup_sock,
                                execute_task,
                                self.time_limit_ns,
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
        finally:
            put_sandbox(sandbox)

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

    def do_input(self, input_file):
        try:
            with open(input_file, 'wb') as dst, self.open_input() as src:
                dos2unix(src, dst)
        except BrokenPipeError:
            pass

    def do_output(self, output_file):
        with open(output_file, 'rb') as out, self.open_output() as ans:
            return compare_stream(ans, out)

class CustomJudgeCase:
    def __init__(self, open_input, time_ns, memory_bytes, open_judge, judge_lang):
        self.open_input = open_input
        self.time_ns = time_ns
        self.memory_bytes = memory_bytes
        self.open_judge = open_judge
        self.judge_lang = judge_lang

    async def judge(self, user_package):
        loop = get_event_loop()
        judge_package, message, _, _ = await build(
            self.judge_lang,
            await loop.run_in_executor(None, lambda: self.open_judge().read()))
        if not judge_package:
            return STATUS_SYSTEM_ERROR, 0, 0, 0, message
        user_sandbox, judge_sandbox = await get_sandbox(2)
        try:
            async def prepare_user_sandbox():
                await user_sandbox.reset()
                return await user_package.install(user_sandbox)

            async def prepare_judge_sandbox():
                await judge_sandbox.reset()
                return await judge_package.install(judge_sandbox)

            user_executable, judge_executable = \
                await gather(prepare_user_sandbox(), prepare_judge_sandbox())
            user_stdin_file = path.join(user_sandbox.in_dir, 'stdin')
            mkfifo(user_stdin_file)
            user_stdout_file = path.join(user_sandbox.in_dir, 'stdout')
            mkfifo(user_stdout_file)
            judge_stdin_file = path.join(judge_sandbox.in_dir, 'stdin')
            link(user_stdout_file, judge_stdin_file)
            user_stderr_file = path.join(user_sandbox.in_dir, 'stderr')
            mkfifo(user_stderr_file)
            judge_stdout_file = path.join(judge_sandbox.in_dir, 'stdout')
            mkfifo(judge_stdout_file)
            judge_stderr_file = path.join(judge_sandbox.in_dir, 'stderr')
            mkfifo(judge_stderr_file)
            judge_extra_file = path.join(judge_sandbox.in_dir, 'extra')
            mkfifo(judge_extra_file)
            with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as user_cgroup_sock, \
                 socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as judge_cgroup_sock:
                user_cgroup_sock.bind(path.join(user_sandbox.in_dir, 'cgroup'))
                judge_cgroup_sock.bind(path.join(judge_sandbox.in_dir, 'cgroup'))
                user_cgroup_sock.listen()
                judge_cgroup_sock.listen()
                user_execute_task = loop.create_task(user_executable.execute(
                    user_sandbox,
                    stdin_file='/in/stdin',
                    stdout_file='/in/stdout',
                    stderr_file='/in/stderr',
                    cgroup_file='/in/cgroup'))
                judge_execute_task = loop.create_task(judge_executable.execute(
                    judge_sandbox,
                    stdin_file='/in/stdin',
                    stdout_file='/in/stdout',
                    stderr_file='/in/stderr',
                    extra_file='/in/extra',
                    cgroup_file='/in/cgroup'))
                others_task = gather(
                    loop.run_in_executor(None, self.do_input, user_stdin_file),
                    loop.run_in_executor(None, self.do_input, judge_extra_file),
                    read_pipe(user_stderr_file, MAX_STDERR_SIZE),
                    read_pipe(judge_stdout_file, MAX_STDERR_SIZE),
                    read_pipe(judge_stderr_file, MAX_STDERR_SIZE),
                    wait_cgroup(user_cgroup_sock,
                                user_execute_task,
                                self.time_ns,
                                self.time_ns,
                                self.memory_bytes,
                                PROCESS_LIMIT),
                    wait_cgroup(judge_cgroup_sock,
                                judge_execute_task,
                                DEFAULT_TIME_NS,
                                self.time_ns + DEFAULT_TIME_NS,
                                DEFAULT_MEMORY_BYTES,
                                PROCESS_LIMIT))
                user_execute_status, judge_execute_status = await gather(
                    user_execute_task, judge_execute_task)
                _, _, user_stderr, judge_stdout, judge_stderr, \
                (user_time_usage_ns, user_memory_usage_bytes), \
                (judge_time_usage_ns, judge_memory_usage_bytes) = \
                    await others_task
            if (judge_execute_status or
                judge_memory_usage_bytes >= DEFAULT_MEMORY_BYTES or
                judge_time_usage_ns >= DEFAULT_TIME_NS):
                status = STATUS_SYSTEM_ERROR
                score = 0
            elif user_memory_usage_bytes >= self.memory_bytes:
                status = STATUS_MEMORY_LIMIT_EXCEEDED
                score = 0
            elif user_time_usage_ns >= self.time_ns:
                status = STATUS_TIME_LIMIT_EXCEEDED
                score = 0
            elif user_execute_status:
                status = STATUS_RUNTIME_ERROR
                score = 0
            else:
                try:
                    status, score = map(int, judge_stdout.split())
                except SystemError:
                    status = STATUS_SYSTEM_ERROR
                    score = 0
            return status, score, user_time_usage_ns, user_memory_usage_bytes, user_stderr
        finally:
            put_sandbox(user_sandbox, judge_sandbox)

    def do_input(self, input_file):
        try:
            with open(input_file, 'wb') as dst, self.open_input() as src:
                dos2unix(src, dst)
        except BrokenPipeError:
            pass

class APlusBCase(CaseBase):
    def __init__(self, a, b, time_limit_ns, memory_limit_bytes, score):
        super().__init__(time_limit_ns, memory_limit_bytes, PROCESS_LIMIT, score)
        self.a = a
        self.b = b

    def do_input(self, input_file):
        try:
            with open(input_file, 'w') as file:
                file.write('{} {}\n'.format(self.a, self.b))
        except BrokenPipeError:
            pass

    def do_output(self, output_file):
        with open(output_file, 'rb') as file:
            return compare_stream(BytesIO(str(self.a + self.b).encode()), file)

def read_legacy_cases(config, open):
    num_cases = int(config.readline())
    for line in islice(csv.reader(config, delimiter='|'), num_cases):
        input, output, time_str, score_str = line[:4]
        try:
            memory_bytes = int(float(line[4]) * 1024)
        except (IndexError, ValueError):
            memory_bytes = DEFAULT_MEMORY_BYTES
        yield DefaultCase(partial(open, path.join('input', input)),
                          partial(open, path.join('output', output)),
                          int(float(time_str) * 1000000000),
                          memory_bytes,
                          int(score_str))

def read_yaml_cases(config, open):
    for case in yaml.safe_load(config)['cases']:
        if 'judge' not in case:
            yield DefaultCase(partial(open, case['input']),
                              partial(open, case['output']),
                              parse_time_ns(case['time']),
                              parse_memory_bytes(case['memory']),
                              int(case['score']))
        else:
            yield CustomJudgeCase(partial(open, case['input']),
                                  parse_time_ns(case['time']),
                                  parse_memory_bytes(case['memory']),
                                  partial(open, case['judge']),
                                  path.splitext(case['judge'])[1][1:])

def read_cases(file):
    zip_file = ZipFile(file)
    canonical_dict = dict((name.lower(), name)
                          for name in zip_file.namelist())

    def open(name):
        try:
            return zip_file.open(canonical_dict[name.lower()])
        except KeyError:
            raise FileNotFoundError(name) from None
    try:
        config = TextIOWrapper(open('config.ini'),
                               encoding='utf-8', errors='replace')
        return read_legacy_cases(config, open)
    except FileNotFoundError:
        pass
    try:
        config = open('config.yaml')
        return read_yaml_cases(config, open)
    except FileNotFoundError:
        pass
    raise FormatError('config file not found')
