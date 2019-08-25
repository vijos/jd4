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
    cdef int both_spaced = 1
    cdef int a, b
    cdef str cache_a = "", cache_b = ""
    while True:
        a = ra.read()
        b = rb.read()
        if (a == 13 or a == 10 or a == 32 or a == 9):
            cache_a = ""
        else:
            cache_a = cache_a + chr(a)
        if (b == 13 or b == 10 or b == 32 or a == 9):
            cache_b = ""
        else:
            cache_b = cache_b + chr(b)
        while a != b:
            if (a == 13 or
                (both_spaced and (a == 32 or a == 9)) or
                ((b == -1 or b == 10) and (a == 32 or a == 10))):
                a = ra.read()
            elif (b == 13 or
                  (both_spaced and (b == 32 or b == 9)) or
                  ((a == -1 or a == 10) and (b == 32 or b == 10))):
                b = rb.read()
            else:
                a = ra.read()
                while (a != 13 and a != 10 and a != 32 and a != 9):
                    cache_a = cache_a + chr(a)
                    a=ra.read()
                b = rb.read()
                while (b != 13 and b != 10 and a != 32 and b != 9):
                    cache_b = cache_b + chr(b)
                    b = rb.read()
                return "Read " + cache_b + ", expect " + cache_a
        if a == -1:
            return ""
        both_spaced = (a == 32 or a == 9)
