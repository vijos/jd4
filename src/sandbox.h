#ifndef JD4_SANDBOX_H
#define JD4_SANDBOX_H

#include <boost/asio.hpp>

class Sandbox {
public:
    explicit Sandbox(boost::asio::io_service &io_service);
    void StartInitProcess();

private:
    void HandleInitProcess();

    boost::asio::io_service &io_service;
    int real_euid;
    int real_egid;
};

#endif //JD4_SANDBOX_H
