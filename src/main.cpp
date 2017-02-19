#include "compiler.h"

void Execute(Box<Executable> executable) {
    for (int i = 0; i < 10; ++i) {
        executable->Execute();
    }
}

int main(int argc, char *argv[]) {
    Box<Compiler> c = CreateSandboxedCompiler(
        "/usr/bin/gcc", {"gcc", "-static", "-o", "/out/foo", "foo.c"},
        "foo.c", "foo", {"foo"});
    Box<Compiler> java = CreateSandboxedCompiler(
        "/usr/bin/javac", {"javac", "-d", "out", "Program.java"},
        "Program.java", "/usr/bin/java", {"java", "Program"});
    Box<Compiler> python = CreateSandboxedInterpreter(
        "foo.py", "/usr/bin/python", {"python", "foo.py"});
    Execute(c->Compile(R"(#include <stdio.h>
int main(void) {
    printf("It works!\n");
})"));
    Execute(java->Compile(R"(class Program {
        public static void main(String[] args) {
            System.out.println("It works!");
        }
    })"));
    Execute(python->Compile("print 'It works!'"));
}
