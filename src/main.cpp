#include <sys/wait.h>
#include "process.h"

int main(int argc, char *argv[]) {
    EventLoop loop;
    CHECK_UNIX(Fork(loop, []() {
        Sandbox("/tmp", {
            {"/bin", "/bin"},
            {"/lib", "/lib"},
            {"/lib64", "/lib64"},
            {"/usr", "/usr"},
        });
        Process process = Execute("/bin/bash", {"bunny"});
        WaitForExit(process);
    }));

    wait(NULL);
    loop.run();
}
