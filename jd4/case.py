import csv
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import TextIOWrapper
from itertools import islice
from os import mkfifo, path
from shutil import copyfileobj
from zipfile import ZipFile

from jd4.compile import Compiler
from jd4.sandbox import create_sandbox

class LegacyCase:
    def __init__(self, open_input, open_output, time_sec, mem_kb, score):
        self.open_input = open_input
        self.open_output = open_output
        self.time_sec = time_sec
        self.mem_kb = mem_kb
        self.score = score

    def judge(self, sandbox, package, executor):
        executable = package.install(sandbox)
        mkfifo(path.join(sandbox.io_dir, 'stdin'))
        mkfifo(path.join(sandbox.io_dir, 'stdout'))
        mkfifo(path.join(sandbox.io_dir, 'stderr'))
        executor.submit(lambda: copyfileobj(
            self.open_input(), open(path.join(sandbox.io_dir, 'stdin'), 'wb')))
        # TODO: stream judge
        executor.submit(lambda: print(open(path.join(sandbox.io_dir, 'stdout'), 'rb').read()))
        executor.submit(lambda: print(open(path.join(sandbox.io_dir, 'stderr'), 'rb').read()))
        executable.execute(sandbox, stdin_file='/io/stdin',
                           stdout_file='/io/stdout', stderr_file='/io/stderr')

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
    package = gcc.build(sandbox, b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")
    for case in read_legacy_cases('examples/P1000.zip'):
        case.judge(sandbox, package, executor)
