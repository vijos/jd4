import csv
from io import TextIOWrapper
from itertools import islice
from os import path
from zipfile import ZipFile

class LegacyCase:
    def __init__(self, open_input, open_output, time_sec, mem_kb, score):
        self.open_input = open_input
        self.open_output = open_output
        self.time_sec = time_sec
        self.mem_kb = mem_kb
        self.score = score

    def judge(self, executable, sandbox):
        # TODO
        executable.execute(sandbox)

def read_legacy_cases(file):
    zip = ZipFile(file)
    config_raw = zip.open('Config.ini')
    config = TextIOWrapper(config_raw)
    num_cases = int(config.readline())
    cases = list()
    for input, output, time_sec_str, score_str, mem_kb_str in \
        islice(csv.reader(config, delimiter='|'), num_cases):
        open_input = lambda: zip.open(path.join('Input', input))
        open_output = lambda: zip.open(path.join('Output', output))
        cases.append(LegacyCase(open_input, open_output,
                                int(time_sec_str), int(mem_kb_str), int(score_str)))
    return cases
