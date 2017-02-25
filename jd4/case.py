import csv
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import TextIOWrapper
from itertools import islice, zip_longest
from os import mkfifo, path
from shutil import copyfileobj
from zipfile import ZipFile

from jd4.compile import Compiler
from jd4.judge import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR
from jd4.sandbox import create_sandbox

CHUNK_SIZE = 32768
MAX_STDERR_SIZE = 32768

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

class LegacyCase:
    def __init__(self, open_input, open_output, time_sec, mem_kb, score):
        self.open_input = open_input
        self.open_output = open_output
        self.time_sec = time_sec
        self.mem_kb = mem_kb
        self.score = score

    def judge(self, sandbox, package, executor):
        executable = package.install(sandbox)
        stdin_file = path.join(sandbox.io_dir, 'stdin')
        mkfifo(stdin_file)
        stdin_future = executor.submit(lambda: copyfileobj(
            self.open_input(), open(stdin_file, 'wb'), CHUNK_SIZE))
        stdout_file = path.join(sandbox.io_dir, 'stdout')
        mkfifo(stdout_file)
        stdout_future = executor.submit(lambda: compare_file(
            self.open_output(), open(stdout_file, 'rb')))
        stderr_file = path.join(sandbox.io_dir, 'stderr')
        mkfifo(stderr_file)
        stderr_future = executor.submit(
            lambda: open(stderr_file, 'rb').read(MAX_STDERR_SIZE))
        if executable.execute(sandbox,
                              stdin_file='/io/stdin',
                              stdout_file='/io/stdout',
                              stderr_file='/io/stderr'):
            return STATUS_RUNTIME_ERROR
        stdin_future.result()
        if not stdout_future.result():
            return STATUS_WRONG_ANSWER
        stderr_future.result()
        return STATUS_ACCEPTED

def read_legacy_cases(file):
    zip = ZipFile(file)
    config_raw = zip.open('Config.ini')
    config = TextIOWrapper(config_raw)
    num_cases = int(config.readline())
    cases = list()
    for input, output, time_sec_str, score_str, mem_kb_str in \
        islice(csv.reader(config, delimiter='|'), num_cases):
        open_input = partial(zip.open, path.join('Input', input))
        open_output = partial(zip.open, path.join('Output', output))
        cases.append(LegacyCase(open_input, open_output,
                                int(time_sec_str), int(mem_kb_str), int(score_str)))
    return cases

if __name__ == '__main__':
    executor = ThreadPoolExecutor()
    sandbox = create_sandbox()
    gcc = Compiler('/usr/bin/gcc', ['gcc', '-o', '/io/foo', 'foo.c'],
                   'foo.c', 'foo', ['foo'])
    _, package = gcc.build(sandbox, b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")
    for case in read_legacy_cases('examples/P1000.zip'):
        print(case.judge(sandbox, package, executor))
