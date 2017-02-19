#include "compiler.h"
#include "process.h"

int main(int argc, char *argv[]) {
    Box<Compiler> c_compiler = CreateCompiler(
        "/usr/bin/gcc", {"gcc", "-static", "-o", "/out/foo.out", "foo.c"},
        "foo.c", "foo.out", {"foo"});
    Box<Compiler> java_compiler = CreateCompiler(
        "/usr/bin/javac", {"javac", "-d", "out", "Program.java"},
        "Program.java", "/usr/bin/java", {"java", "Program"});
    {
        Box<Package> package = c_compiler->Compile(R"(#include <stdio.h>
int main(void) {
    printf("It works!\n");
})");
        package->Install("/tmp");
        WaitForExit(package->Execute("/tmp"));
    }
    {
        Box<Package> package = java_compiler->Compile(R"(class Program {
        public static void main(String[] args) {
            System.out.println("It works!");
        }
    })");
        package->Install("/tmp");
        WaitForExit(package->Execute("/tmp"));
    }
}
