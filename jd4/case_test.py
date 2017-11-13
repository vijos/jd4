from os import path
from unittest import main, TestCase

from jd4.case import read_legacy_cases

class CaseTest(TestCase):
    def test_legacy_case(self):
        count = 0
        for case in read_legacy_cases(path.join(path.dirname(__file__),
                                                'testdata/1000.zip')):
            self.assertEqual(case.time_limit_ns, 1000000000)
            self.assertEqual(case.memory_limit_bytes, 16777216)
            self.assertEqual(case.score, 10)
            self.assertEqual(sum(map(int, case.open_input().read().split())),
                             int(case.open_output().read()))
            count += 1
        self.assertEqual(count, 10)

if __name__ == '__main__':
    main()
