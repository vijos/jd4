import csv
from asyncio import gather, get_event_loop, sleep, wait_for, Event, StreamReader, StreamReaderProtocol, TimeoutError
from functools import partial
from io import TextIOWrapper
from itertools import islice, zip_longest
from os import cpu_count, fdopen, mkfifo, open as os_open, path, O_RDONLY, O_NONBLOCK
from shutil import copyfileobj
from zipfile import ZipFile

from jd4.cgroup import CGroup, try_init_cgroup
from jd4.compile import Compiler
from jd4.judge import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                      STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED
from jd4.log import logger
from jd4.sandbox import create_sandbox
from jd4.util import read_text_file

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 8192
WAIT_JITTER_NS = 5000000
PROCESS_LIMIT = 32

def chunk_and_strip_lines(f):
    prev = b''
    cur = f.readline(CHUNK_SIZE).lstrip()
    while cur:
        if prev and prev[-1] in b'\r\n':
            prev, cur = prev.rstrip(), cur.lstrip()
        if prev: yield prev
        prev, cur = cur, f.readline(CHUNK_SIZE)
    if prev: prev = prev.rstrip()
    if prev: yield prev

def compare_file(fa, fb):
    a = chunk_and_strip_lines(fa)
    b = chunk_and_strip_lines(fb)
    return all(x == y for x, y in zip_longest(a, b))

async def read_pipe(file, size):
    loop = get_event_loop()
    reader = StreamReader()
    protocol = StreamReaderProtocol(reader)
    transport, _ = await loop.connect_read_pipe(
        lambda: protocol, fdopen(os_open(file, O_RDONLY | O_NONBLOCK)))
    data = await reader.read(size)
    transport.close()
    return data

def get_idle():
    return float(read_text_file('/proc/uptime').split()[1])

async def accept_and_limit(cgroup, time_limit_ns, memory_limit_bytes, process_limit):
    loop = get_event_loop()
    cgroup.memory_limit_bytes = memory_limit_bytes
    cgroup.pids_max = process_limit
    await cgroup.accept_one()
    start_idle = get_idle()
    exit_event = Event()

    async def limit_task():
        while True:
            cpu_usage_ns = cgroup.cpu_usage_ns
            idle_usage_ns = int((get_idle() - start_idle) / cpu_count() * 1e9)
            time_usage_ns = max(cpu_usage_ns, idle_usage_ns)
            time_remain_ns = time_limit_ns - time_usage_ns
            if time_remain_ns <= 0:
                break
            try:
                await wait_for(exit_event.wait(), (time_remain_ns + WAIT_JITTER_NS) / 1e9)
                break
            except TimeoutError:
                pass
        while cgroup.kill():
            await sleep(.001)
        if time_usage_ns < time_limit_ns:
            time_usage_ns = cpu_usage_ns
        return time_usage_ns, cgroup.memory_usage_bytes

    return exit_event, loop.create_task(limit_task())

class LegacyCase:
    def __init__(self, open_input, open_output, time_limit_ns, memory_limit_bytes, score):
        self.open_input = open_input
        self.open_output = open_output
        self.time_limit_ns = time_limit_ns
        self.memory_limit_bytes = memory_limit_bytes
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
        cgroup = CGroup(path.join(sandbox.in_dir, 'cgroup'))
        _, correct, stderr, execute_status, (exit_event, usage_future) = await gather(
            loop.run_in_executor(None, lambda: copyfileobj(self.open_input(), open(stdin_file, 'wb'), CHUNK_SIZE)),
            loop.run_in_executor(None, lambda: compare_file(self.open_output(), open(stdout_file, 'rb'))),
            read_pipe(stderr_file, MAX_STDERR_SIZE),
            executable.execute(sandbox,
                               stdin_file='/in/stdin',
                               stdout_file='/in/stdout',
                               stderr_file='/in/stderr',
                               cgroup_file='/in/cgroup'),
            accept_and_limit(cgroup, self.time_limit_ns, self.memory_limit_bytes, PROCESS_LIMIT))
        exit_event.set()
        time_usage_ns, memory_usage_bytes = await usage_future
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

def read_legacy_cases(file):
    zip_file = ZipFile(file)
    config = TextIOWrapper(zip_file.open('Config.ini'))
    num_cases = int(config.readline())
    for input, output, time_sec_str, score_str, mem_kb_str in \
        islice(csv.reader(config, delimiter='|'), num_cases):
        open_input = partial(zip_file.open, path.join('Input', input))
        open_output = partial(zip_file.open, path.join('Output', output))
        yield LegacyCase(open_input, open_output,
                         int(float(time_sec_str) * 1e9),
                         int(mem_kb_str) * 1024,
                         int(score_str))

if __name__ == '__main__':
    async def main():
        try_init_cgroup()
        sandbox = await create_sandbox()
        gcc = Compiler('/usr/bin/gcc', ['gcc', '-std=c99', '-o', '/out/foo', '/in/foo.c'],
                       'foo.c', 'foo', ['foo'])
        _, package = await gcc.build(sandbox, b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")
        for case in read_legacy_cases('examples/P1000.zip'):
            logger.info(await case.judge(sandbox, package))

    get_event_loop().run_until_complete(main())
