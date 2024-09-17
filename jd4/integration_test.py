from asyncio import get_event_loop
from os import path
from unittest import TestCase, main

from jd4.case import read_cases, APlusBCase
from jd4.cgroup import try_init_cgroup
from jd4.compile import build
from jd4.log import logger
from jd4.pool import init as init_pool
from jd4.status import STATUS_ACCEPTED, STATUS_WRONG_ANSWER, STATUS_RUNTIME_ERROR, \
                       STATUS_TIME_LIMIT_EXCEEDED, STATUS_MEMORY_LIMIT_EXCEEDED

def run(coro):
    return get_event_loop().run_until_complete(coro)

class LanguageTest(TestCase):
    """Run A+B problem on every languages."""
    @classmethod
    def setUpClass(cls):
        cls.cases = list(read_cases(open(path.join(
            path.dirname(__file__), 'testdata/aplusb.zip'), 'rb')))

    def do_lang(self, lang, code):
        package, message, time_usage_ns, memory_usage_bytes = \
            run(build(lang, code))
        self.assertIsNotNone(package, 'Compile failed: ' + message)
        logger.info('Compiled successfully in %d ms time, %d kb memory',
                    time_usage_ns // 1000000, memory_usage_bytes // 1024)
        if message:
            logger.warning('Compiler output is not empty: %s', message)
        for case in self.cases:
            status, score, time_usage_ns, memory_usage_bytes, stderr = \
                run(case.judge(package))
            self.assertEqual(status, STATUS_ACCEPTED)
            self.assertEqual(score, 10)
            self.assertEqual(stderr, b'')
            logger.info('Accepted: %d ms time, %d kb memory',
                        time_usage_ns // 1000000, memory_usage_bytes // 1024)

    def test_c(self):
        self.do_lang('c', b"""#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")

    def test_cc(self):
        self.do_lang('cc', b"""#include <iostream>
int main(void) {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << std::endl;
}""")

    def test_java(self):
        self.do_lang('java', b"""import java.io.IOException;
import java.util.Scanner;
public class Main {
    public static void main(String[] args) throws IOException {
        Scanner sc = new Scanner(System.in);
        int a = sc.nextInt();
        int b = sc.nextInt();
        System.out.println(a + b);
    }
}""")

    def test_pas(self):
        self.do_lang('pas', b"""var a,b:longint;
begin
    readln(a,b);
    writeln(a+b);
end.""")

    def test_php(self):
        self.do_lang('php', b"""<?php
$stdin = fopen('php://stdin', 'r');
list($a, $b) = fscanf($stdin, "%d%d");
echo $a + $b . "\\n";
""")

    def test_py(self):
        self.do_lang('py', b'print(sum(map(int, input().split())))')

    def test_py3(self):
        self.do_lang('py3', b'print(sum(map(int, input().split())))')

    def test_rs(self):
        self.do_lang('rs', b"""fn main() {
    let mut line = String::new();
    std::io::stdin().read_line(&mut line).unwrap();
    let numbers: Vec<i32> =
        line.trim_end().split(' ').map(|s| s.parse().unwrap()).collect();
    let sum: i32 = numbers.iter().sum();
    println!("{}", sum);
}""")

    def test_hs(self):
        self.do_lang('hs', b'main = print . sum . map read . words =<< getLine')

    def test_js(self):
        self.do_lang('js', b"""const [a, b] = readline().split(' ').map(n => parseInt(n, 10));
print((a + b).toString());""")

    def test_go(self):
        self.do_lang('go', b"""package main
import "fmt"
func main() {
    var a, b int
    fmt.Scanf("%d%d", &a, &b)
    fmt.Printf("%d\\n", a + b)
}
""")

    def test_rb(self):
        self.do_lang('rb', b"""a, b = gets.split.map(&:to_i)
puts(a + b)""")

    def test_cs(self):
        self.do_lang('cs', b"""using System;
using System.Linq;
class Program {
    public static void Main(string[] args) {
        Console.WriteLine(Console.ReadLine().Split().Select(int.Parse).Sum());
    }
}""")

    def test_jl(self):
        self.do_lang('jl', b'println(sum(parse(Int, x) for x in split(readline())))')

class StatusTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = APlusBCase(1, 2, 200000000, 33554432, 10)

    def do_status(self, expected_status, expected_score, code):
        package, message, time_usage_ns, memory_usage_bytes = \
            run(build('c', code))
        self.assertIsNotNone(package, 'Compile failed: ' + message)
        if message:
            logger.warning('Compiler output is not empty: %s', message)
        status, score, time_usage_ns, memory_usage_bytes, stderr = \
            run(self.case.judge(package))
        self.assertEqual(status, expected_status)
        self.assertEqual(score, expected_score)

    def test_accepted(self):
        self.do_status(STATUS_ACCEPTED, 10, b"""#include <stdio.h>
int main(void) { puts("3"); }""")

    def test_wrong_answer(self):
        self.do_status(STATUS_WRONG_ANSWER, 0, b'int main(void) {}')

    def test_time_limit_exceeded(self):
        self.do_status(STATUS_TIME_LIMIT_EXCEEDED, 0,
                       b'int main(void) { while (1); }')

    def test_memory_limit_exceeded(self):
        self.do_status(STATUS_MEMORY_LIMIT_EXCEEDED, 0, b"""#include <string.h>
char a[40000000];
int main(void) {
    memset(a, 0, sizeof(a));
}""")

    def test_runtime_error(self):
        self.do_status(STATUS_RUNTIME_ERROR, 0, b'int main(void) { return 1; }')

class CustomJudgeTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = list(read_cases(open(path.join(
            path.dirname(__file__), 'testdata/decompose-sum.zip'), 'rb')))

    def do_status(self, expected_status, expected_score, code):
        package, message, time_usage_ns, memory_usage_bytes = \
            run(build('c', code))
        self.assertIsNotNone(package, 'Compile failed: ' + message)
        logger.info('Compiled successfully in %d ms time, %d kb memory',
                    time_usage_ns // 1000000, memory_usage_bytes // 1024)
        if message:
            logger.warning('Compiler output is not empty: %s', message)
        total_status = STATUS_ACCEPTED
        total_score = 0
        for case in self.cases:
            status, score, time_usage_ns, memory_usage_bytes, stderr = \
                run(case.judge(package))
            total_status = max(total_status, status)
            total_score += score
            self.assertEqual(status, STATUS_ACCEPTED)
            self.assertEqual(score, 25)
            self.assertEqual(stderr, b'')
            logger.info('Accepted: %d ms time, %d kb memory',
                        time_usage_ns // 1000000, memory_usage_bytes // 1024)
        self.assertEqual(total_status, expected_status)
        self.assertEqual(total_score, expected_score)

    def test_accepted(self):
        self.do_status(STATUS_ACCEPTED, 100, b"""#include <stdio.h>
int main(void) {
    int sum;
    scanf("%d", &sum);
    printf("%d %d\\n", 42, sum - 42);
}""")

try_init_cgroup()
init_pool()

if __name__ == '__main__':
    main()
