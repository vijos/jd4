#include "compiler.h"

int main(int argc, char *argv[]) {
    GccCompile(R"(#include <stdio.h>

int main(void) {
    int a, b;
    scanf("%d%d", &a, &b);
    printf("%d\n", a + b);
})");
}
