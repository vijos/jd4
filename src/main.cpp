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
        ChildContext context;
        context.input_behavior.emplace(STDIN_FILENO, INHERIT_STREAM);
        context.output_behavior.emplace(STDOUT_FILENO, INHERIT_STREAM);
        context.output_behavior.emplace(STDERR_FILENO, INHERIT_STREAM);
        LaunchChild("/bin/bash", {"bunny"}, context).wait();
    }));
    wait(NULL);
    loop.run();
}
