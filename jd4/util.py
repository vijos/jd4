import re
from asyncio import get_event_loop, StreamReader, StreamReaderProtocol
from os import fdopen, listdir, open as os_open, path, remove, waitpid, \
               O_RDONLY, O_NONBLOCK, WEXITSTATUS, WIFSIGNALED, WNOHANG, WTERMSIG
from shutil import rmtree

from jd4.error import FormatError

TIME_RE = re.compile(r'([0-9]+(?:\.[0-9]*)?)([mun]?)s?')
TIME_UNITS = {'': 1000000000, 'm': 1000000, 'u': 1000, 'n': 1}
MEMORY_RE = re.compile(r'([0-9]+(?:\.[0-9]*)?)([kmg]?)b?')
MEMORY_UNITS = {'': 1, 'k': 1024, 'm': 1048576, 'g': 1073741824}

def remove_under(*dirnames):
    for dirname in dirnames:
        for name in listdir(dirname):
            full_path = path.join(dirname, name)
            if path.isdir(full_path):
                rmtree(full_path)
            else:
                remove(full_path)

def wait_and_reap_zombies(pid):
    _, status = waitpid(pid, 0)
    try:
        while True:
            waitpid(-1, WNOHANG)
    except ChildProcessError:
        pass
    if WIFSIGNALED(status):
        return -WTERMSIG(status)
    return WEXITSTATUS(status)

def read_text_file(file):
    with open(file) as f:
        return f.read()

def write_binary_file(file, data):
    with open(file, 'wb') as f:
        f.write(data)

def write_text_file(file, text):
    with open(file, 'w') as f:
        f.write(text)

async def read_pipe(file, size):
    loop = get_event_loop()
    reader = StreamReader()
    protocol = StreamReaderProtocol(reader)
    transport, _ = await loop.connect_read_pipe(
        lambda: protocol, fdopen(os_open(file, O_RDONLY | O_NONBLOCK)))
    chunks = list()
    while size > 0:
        chunk = await reader.read(size)
        if not chunk:
            break
        chunks.append(chunk)
        size -= len(chunk)
    transport.close()
    return b''.join(chunks)

def parse_time_ns(time_str):
    match = TIME_RE.fullmatch(time_str)
    if not match:
        raise FormatError(time_str, 'error parsing time')
    return int(float(match.group(1)) * TIME_UNITS[match.group(2)])

def parse_memory_bytes(memory_str):
    match = MEMORY_RE.fullmatch(memory_str)
    if not match:
        raise FormatError(memory_str, 'error parsing memory')
    return int(float(match.group(1)) * MEMORY_UNITS[match.group(2)])
