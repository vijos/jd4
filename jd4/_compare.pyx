"""Comparing two streams with loose whitespace and newline rules.

This is written in cython for performance reasons. A simple test showed that
using cython here can achieve 50x+ performance over python.

We have to use magic numbers here because cython doesn't support constants:

CHUNK_SIZE = 32768
EOF = -1
CR = 13
LF = 10
TAB = 9
SPACE = 32
"""
cdef class StreamReader:
    cdef stream
    cdef bytes buffer
    cdef const char* begin
    cdef const char* end

    def __init__(self, stream):
        self.stream = stream
        self.begin = NULL
        self.end = NULL

    cdef int read(self):
        if self.begin == self.end:
            self.buffer = self.stream.read(32768)
            if not self.buffer:
                return -1
            self.begin = self.buffer
            self.end = self.begin + len(self.buffer)
        cdef int result = self.begin[0]
        self.begin += 1
        return result

def compare_stream(fa, fb):
    cdef StreamReader ra = StreamReader(fa)
    cdef StreamReader rb = StreamReader(fb)
    cdef int allow_space = 1
    cdef int allow_newline = 1
    cdef int a
    cdef int b

    while True:
        a = ra.read()
        b = rb.read()
        while a != b and not ((a == 32 or a == 9) and (b == 32 or b == 9)):
            if ((a == 32 or a == 9) and (allow_space or b == 10 or b == -1) or
                (a == 10 and (allow_newline or b == -1)) or
                a == 13):
                a = ra.read()
            elif ((b == 32 or b == 9) and (allow_space or a == 10 or a == -1) or
                  (b == 10 and (allow_newline or a == -1)) or
                  b == 13):
                b = rb.read()
            else:
                return False
        if a == -1:
            return True
        allow_newline = (a == 10)
        allow_space = (allow_newline or a == 32 or a == 9)
