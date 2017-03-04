import csv
from asyncio import gather, get_event_loop, StreamReader, StreamReaderProtocol
from functools import partial
from io import TextIOWrapper
from itertools import islice, zip_longest
from os import fdopen, mkfifo, open as os_open, path, O_RDONLY, O_NONBLOCK
from shutil import copyfileobj
from zipfile import ZipFile

from jd4.cgroup import CGroup
from jd4.compile import Compiler
from jd4.judge import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                      STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED
from jd4.sandbox import create_sandbox

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 8192

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
    await loop.connect_read_pipe(lambda: protocol, fdopen(os_open(file, O_RDONLY | O_NONBLOCK)))
    return await reader.read(size)

class LegacyCase:
    def __init__(self, open_input, open_output, cpu_limit_ns, memory_limit_bytes, score):
        self.open_input = open_input
        self.open_output = open_output
        self.cpu_limit_ns = cpu_limit_ns
        self.memory_limit_bytes = memory_limit_bytes
        self.score = score

    async def judge(self, sandbox, package):
        loop = get_event_loop()
        executable = await package.install(sandbox)
        stdin_file = path.join(sandbox.io_dir, 'stdin')
        mkfifo(stdin_file)
        stdout_file = path.join(sandbox.io_dir, 'stdout')
        mkfifo(stdout_file)
        stderr_file = path.join(sandbox.io_dir, 'stderr')
        mkfifo(stderr_file)
        cgroup = CGroup()
        cgroup.memory_limit_bytes = self.memory_limit_bytes

        _, correct, stderr, _, execute_status = await gather(
            loop.run_in_executor(None, lambda: copyfileobj(self.open_input(), open(stdin_file, 'wb'), CHUNK_SIZE)),
            loop.run_in_executor(None, lambda: compare_file(self.open_output(), open(stdout_file, 'rb'))),
            read_pipe(stderr_file, MAX_STDERR_SIZE),
            cgroup.accept(path.join(sandbox.io_dir, 'cgroup')),
            executable.execute(sandbox,
                               stdin_file='/io/stdin',
                               stdout_file='/io/stdout',
                               stderr_file='/io/stderr',
                               cgroup_file='/io/cgroup'))
        cpu_usage_ns = cgroup.cpu_usage_ns
        memory_usage_bytes = cgroup.memory_usage_bytes
        if memory_usage_bytes >= self.memory_limit_bytes:
            status = STATUS_MEMORY_LIMIT_EXCEEDED
        elif cpu_usage_ns >= self.cpu_limit_ns:
            status = STATUS_TIME_LIMIT_EXCEEDED
        elif execute_status:
            status = STATUS_RUNTIME_ERROR
        elif not correct:
            status = STATUS_WRONG_ANSWER
        else:
            status = STATUS_ACCEPTED
        return status, cpu_usage_ns, memory_usage_bytes, stderr

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
                         int(float(mem_kb_str) * 1024),
                         float(score_str))

if __name__ == '__main__':
    async def main():
        sandbox = await create_sandbox()
        gcc = Compiler('/usr/bin/gcc', ['gcc', '-std=c99', '-o', '/io/foo', 'foo.c'],
                       'foo.c', 'foo', ['foo'])
        _, package = await gcc.build(sandbox, b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")
        for case in read_legacy_cases('examples/P1000.zip'):
            print(await case.judge(sandbox, package))

    get_event_loop().run_until_complete(main())
