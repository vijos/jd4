import pyximport; pyximport.install()

from asyncio import gather, get_event_loop
from fcntl import fcntl, F_GETFL, F_SETFL
from os import mkfifo, path, O_NONBLOCK
from socket import socket, AF_UNIX, SOCK_STREAM, SOCK_NONBLOCK

from jd4.case import CaseBase, MAX_STDERR_SIZE, CHUNK_SIZE
from jd4.cgroup import try_init_cgroup, wait_cgroup
from jd4.compile import Compiler
from jd4.status import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                       STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED, \
                       STATUS_SYSTEM_ERROR
from jd4.log import logger
from jd4.sandbox import create_sandboxes
from jd4.util import read_pipe

JUDGE_TIME_MS = 1000
JUDGE_MEM_KB = 262144
JUDGE_PROCESS_LIMIT = 32

def copy_pipeobj(src, target):
    while True:
        buf = src.read(CHUNK_SIZE)
        if buf == b'':
            break
        if buf:
            target.write(buf)
            target.flush()

def copy_pipe(src, target):
    try:
        with open(target, 'wb') as target_file, \
             open(src, 'rb') as src_file:
            fd = src_file.fileno()
            flag = fcntl(fd, F_GETFL)
            fcntl(fd, F_SETFL, flag | O_NONBLOCK)
            copy_pipeobj(src_file, target_file)
    except BrokenPipeError:
        pass

class SpjCaseBase(CaseBase):
    def __init__(self, time_limit_ns, memory_limit_bytes, process_limit, score):
        self.time_limit_ns = time_limit_ns
        self.memory_limit_bytes = memory_limit_bytes
        self.process_limit = process_limit
        self.score = score

    async def judge(self, judge_sandbox, user_sandbox, judge_package, user_package):
        loop = get_event_loop()
        judge_exe = await judge_package.install(judge_sandbox)
        user_exe = await user_package.install(user_sandbox)
        judge_stdin_file = path.join(judge_sandbox.in_dir, 'stdin')
        mkfifo(judge_stdin_file)
        judge_stdout_file = path.join(judge_sandbox.in_dir, 'stdout')
        mkfifo(judge_stdout_file)
        # TODO(twd2): performance improve
        user_stdin_file = path.join(user_sandbox.in_dir, 'stdin')
        mkfifo(user_stdin_file)
        user_stdout_file = path.join(user_sandbox.in_dir, 'stdout')
        mkfifo(user_stdout_file)
        judge_err_file = path.join(judge_sandbox.in_dir, 'stderr')
        mkfifo(judge_err_file)
        user_err_file = path.join(user_sandbox.in_dir, 'stderr')
        mkfifo(user_err_file)
        with socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as judge_cgroup_sock, \
             socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK) as user_cgroup_sock:
            judge_cgroup_sock.bind(path.join(judge_sandbox.in_dir, 'cgroup'))
            judge_cgroup_sock.listen()
            user_cgroup_sock.bind(path.join(user_sandbox.in_dir, 'cgroup'))
            user_cgroup_sock.listen()
            judge_exe_task = loop.create_task(judge_exe.execute(
                judge_sandbox,
                stdin_file='/in/stdin',
                stdout_file='/in/stdout',
                stderr_file='/in/stderr',
                cgroup_file='/in/cgroup'))
            user_exe_task = loop.create_task(user_exe.execute(
                user_sandbox,
                stdin_file='/in/stdin',
                stdout_file='/in/stdout',
                stderr_file='/in/stderr',
                cgroup_file='/in/cgroup'))
            others_task = gather(
                loop.run_in_executor(None, copy_pipe, user_stdout_file, judge_stdin_file),
                loop.run_in_executor(None, copy_pipe, judge_stdout_file, user_stdin_file),
                read_pipe(judge_err_file, MAX_STDERR_SIZE),
                read_pipe(user_err_file, MAX_STDERR_SIZE),
                wait_cgroup(judge_cgroup_sock,
                            judge_exe_task,
                            JUDGE_TIME_MS * 1000000,
                            JUDGE_MEM_KB * 1024,
                            JUDGE_PROCESS_LIMIT),
                wait_cgroup(user_cgroup_sock,
                            user_exe_task,
                            self.time_limit_ns,
                            self.memory_limit_bytes,
                            self.process_limit))
            judge_exe_status = await judge_exe_task
            user_exe_status = await user_exe_task
            _, __, judge_err, user_err, (judge_time_usage_ns, judge_memory_usage_bytes), \
                (user_time_usage_ns, user_memory_usage_bytes) = await others_task
        if judge_memory_usage_bytes >= JUDGE_TIME_MS * 1000000 or \
           judge_time_usage_ns >= JUDGE_MEM_KB * 1024:
           status = STATUS_SYSTEM_ERROR # TODO(twd2): judge error
           score = 0
        elif user_memory_usage_bytes >= self.memory_limit_bytes:
            status = STATUS_MEMORY_LIMIT_EXCEEDED
            score = 0
        elif user_time_usage_ns >= self.time_limit_ns:
            status = STATUS_TIME_LIMIT_EXCEEDED
            score = 0
        elif user_exe_status:
            status = STATUS_RUNTIME_ERROR
            score = 0
        else:
            score = min(judge_exe_status, self.score) # TODO(twd2)
            status = STATUS_ACCEPTED if score >= self.score else STATUS_WRONG_ANSWER
        return status, score, user_time_usage_ns, user_memory_usage_bytes, user_err

if __name__ == '__main__':
    async def main():
        try_init_cgroup()
        sandbox1, sandbox2 = await create_sandboxes(2)
        gcc = Compiler('/usr/bin/gcc', ['gcc', '-std=c99', '-o', '/out/foo', '/in/foo.c'],
                       'foo.c', 'foo', ['foo'])
        print('Building judge')
        await gcc.prepare(sandbox1, b"""#include <stdio.h>
#include <stdlib.h>
int main(void) {
    int a, b, c, i = 10;
    int score = 0;
    while (i--)
    {
        a = rand() % 32767;
        b = rand() % 32767;
        printf("%d %d\\n", a, b);
        fflush(stdout);
        scanf("%d", &c);
        if (a + b == c)
        {
            score += 1;
        }
    }
    return score;
}""")
        judge_package, _ = await gcc.build(sandbox1)
        print('Building user')
        await gcc.prepare(sandbox2, b"""#include <stdio.h>
int main(void) {
    int a, b, i = 10;
    while (i--)
    {
        scanf("%d%d", &a, &b);
        printf("%d\\n", a + b + (int)(a > 16384));
        fflush(stdout);
    }
}""")
        user_package, _ = await gcc.build(sandbox2)
        print('Judging')
        for i in range(10):
            logger.info(await SpjCaseBase(1000000000, 262144 * 1024, 1, 10) \
                                  .judge(sandbox1, sandbox2, judge_package, user_package))

    get_event_loop().run_until_complete(main())
