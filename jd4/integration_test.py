from asyncio import get_event_loop
from functools import wraps
from os import path
from unittest import TestCase, main

from jd4.case import read_cases
from jd4.cgroup import try_init_cgroup
from jd4.log import logger
from jd4.pool import pool_build, pool_judge
from jd4.status import STATUS_ACCEPTED

def _wrap(method):
    loop = get_event_loop()
    @wraps(method)
    def wrapped(*args, **kwargs):
        return loop.run_until_complete(method(*args, **kwargs))
    return wrapped

class APlusBTest(TestCase):
    """Run A+B problem on every languages."""
    @classmethod
    def setUpClass(cls):
        try_init_cgroup()
        cls.cases = list(read_cases(path.join(path.dirname(__file__),
                                              'testdata/aplusb.tar.gz')))

    @_wrap
    async def do_lang(self, lang, code):
        logger.info('Testing language "%s"', lang)
        package, message, time_usage_ns, memory_usage_bytes = \
            await pool_build(lang, code)
        self.assertIsNotNone(package, 'Compile failed: ' + message)
        logger.info('Compiled successfully in %d ms time, %d kb memory',
                    time_usage_ns // 1000000, memory_usage_bytes // 1024)
        if message:
            logger.warning('Compiler output is not empty: %s', message)
        for case in self.cases:
            status, score, time_usage_ns, memory_usage_bytes, stderr = \
                await pool_judge(package, case)
            self.assertEqual(status, STATUS_ACCEPTED)
            self.assertEqual(score, 10)
            self.assertEqual(stderr, b'')
            logger.info('Accepted: %d ms time, %d kb memory',
                        time_usage_ns // 1000000, memory_usage_bytes // 1024)

    def test_c(self):
        self.do_lang('c', """#include <stdio.h>
int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\\n", a + b);
}""")

    def test_cc(self):
        self.do_lang('cc', """#include <iostream>
int main(void) {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << std::endl;
}""")

    def test_java(self):
            self.do_lang('java', """import java.io.IOException;
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
        self.do_lang('pas', """var a,b:longint;
begin
    readln(a,b);
    writeln(a+b);
end.""")

    def test_php(self):
        self.do_lang('php', """<?php
$stdin = fopen('php://stdin', 'r');
list($a, $b) = fscanf($stdin, "%d%d");
echo $a + $b . "\\n";
""")

    def test_py(self):
        self.do_lang('py', 'print sum(map(int, raw_input().split()))')

    def test_py3(self):
        self.do_lang('py3', 'print(sum(map(int, input().split())))')

    def test_rs(self):
        self.do_lang('rs', """fn main() {
    let mut line = String::new();
    std::io::stdin().read_line(&mut line).unwrap();
    let numbers: Vec<i32> =
        line.trim_right().split(' ').map(|s| s.parse().unwrap()).collect();
    let sum: i32 = numbers.iter().sum();
    println!("{}", sum);
}""")

    def test_hs(self):
        self.do_lang('hs', 'main = print . sum . map read . words =<< getLine')

    def test_js(self):
        self.do_lang('js', """const [a, b] = readline().split(' ').map(n => parseInt(n, 10));
print((a + b).toString());""")

    def test_go(self):
        self.do_lang('go', """package main
import "fmt"
func main() {
    var a, b int
    fmt.Scanf("%d%d", &a, &b)
    fmt.Printf("%d\\n", a + b)
}
""")

    def test_ruby(self):
        self.do_lang('rb', """a, b = gets.split(" ").map {|x| x.to_i}
puts(a + b)""")

if __name__ == '__main__':
    main()
