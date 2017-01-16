#include <boost/asio.hpp>
#include "sandbox.h"

int main(int argc, char *argv[]) {
    boost::asio::io_service io_service;
    Sandbox(io_service, "/tmp");
    io_service.run();
}
