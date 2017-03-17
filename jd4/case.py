import pyximport; pyximport.install()

import csv
from asyncio import gather, get_event_loop, sleep, TimeoutError
from functools import partial
from io import BytesIO, TextIOWrapper
from itertools import islice
from os import mkfifo, path
from random import randint
from shutil import copyfileobj
from zipfile import ZipFile

from jd4._compare import compare_stream
from jd4.cgroup import CGroup, try_init_cgroup, accept_and_limit, \
                       PROCESS_LIMIT, DEFAULT_TIME_MS, DEFAULT_MEM_KB
from jd4.compile import Compiler
from jd4.status import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                       STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED
from jd4.log import logger
from jd4.sandbox import create_sandbox
from jd4.util import read_pipe, read_text_file

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 8192

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
        cgroup = CGroup(path.join(sandbox.in_dir, 'cgroup'))
        try:
            _, correct, stderr, (exit_event, usage_future), execute_status = await gather(
                loop.run_in_executor(None, self.do_stdin, stdin_file),
                loop.run_in_executor(None, self.do_stdout, stdout_file),
                read_pipe(stderr_file, MAX_STDERR_SIZE),
                accept_and_limit(cgroup, self.time_limit_ns, self.memory_limit_bytes, self.process_limit),
                executable.execute(sandbox,
                                   stdin_file='/in/stdin',
                                   stdout_file='/in/stdout',
                                   stderr_file='/in/stderr',
                                   cgroup_file='/in/cgroup'))
            exit_event.set()
            time_usage_ns, memory_usage_bytes = await usage_future
        finally:
            cgroup.close()
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

class LegacyCase(CaseBase):
    def __init__(self, open_input, open_output, time_sec, mem_kb, score):
        super().__init__(int(time_sec * 1e9), int(mem_kb * 1024), PROCESS_LIMIT, score)
        self.open_input = open_input
        self.open_output = open_output

    def do_stdin(self, stdin_file):
        try:
            with self.open_input() as src, open(stdin_file, 'wb') as dst:
                copyfileobj(src, dst, CHUNK_SIZE)
        except BrokenPipeError:
            pass

    def do_stdout(self, stdout_file):
        with self.open_output() as ans, open(stdout_file, 'rb') as out:
            return compare_stream(ans, out)

class APlusBCase(CaseBase):
    def __init__(self, a, b):
        super().__init__(DEFAULT_TIME_MS * 1000000, DEFAULT_MEM_KB * 1024, PROCESS_LIMIT, 10)
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

def read_legacy_cases(file):
    zip_file = ZipFile(file)
    canonical_dict = dict((name.lower(), name) for name in zip_file.namelist())
    config = TextIOWrapper(zip_file.open(canonical_dict['config.ini']),
                           encoding='utf-8', errors='replace')
    num_cases = int(config.readline())
    for line in islice(csv.reader(config, delimiter='|'), num_cases):
        input, output, time_sec_str, score_str = line[:4]
        try:
            mem_kb = float(line[4])
        except (IndexError, ValueError):
            mem_kb = DEFAULT_MEM_KB
        open_input = partial(zip_file.open, canonical_dict[path.join('input', input.lower())])
        open_output = partial(zip_file.open, canonical_dict[path.join('output', output.lower())])
        yield LegacyCase(open_input, open_output, float(time_sec_str), mem_kb, int(score_str))

if __name__ == '__main__':
    async def main():
        try_init_cgroup()
        sandbox = await create_sandbox()
        gcc = Compiler('/usr/bin/gcc', ['gcc', '-std=c99', '-o', '/out/foo', '/in/foo.c'],
                       'foo.c', 'foo', ['foo'])
        await gcc.prepare(sandbox, b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")
        package, _ = await gcc.build(sandbox)
        for case in read_legacy_cases('examples/1000.zip'):
            logger.info(await case.judge(sandbox, package))
        for i in range(10):
            logger.info(await APlusBCase(randint(0, 32767),
                                         randint(0, 32767)).judge(sandbox, package))

    get_event_loop().run_until_complete(main())
