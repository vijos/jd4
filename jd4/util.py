from asyncio import get_event_loop, StreamReader, StreamReaderProtocol
from os import fdopen, open as os_open, O_RDONLY, O_NONBLOCK

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
    data = await reader.read(size)
    transport.close()
    return data
