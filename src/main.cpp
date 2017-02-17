#include <sys/wait.h>
#include <boost/asio.hpp>
#include "process.h"

int main(int argc, char *argv[]) {
    boost::asio::io_service io_service;
    Fork(io_service, []() {
        Sandbox("/tmp", {
            {"/bin", "/bin"},
            {"/lib", "/lib"},
            {"/lib64", "/lib64"},
            {"/usr", "/usr"},
        });
        Fork([]() {
            CHECK(getpid() == 1);
            execl("/bin/bash", "bash", NULL);
        });
        wait(NULL);
    });
    wait(NULL);
    io_service.run();
}
