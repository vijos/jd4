#ifndef JD4_SANDBOX_H
#define JD4_SANDBOX_H

#include <boost/asio.hpp>
#include <string>

class Sandbox {
public:
    explicit Sandbox(boost::asio::io_service &io_service,
                     std::string sandbox_root);
    void Start();

private:
    void HandleSandboxProcess();
    void HandleInitProcess();

    boost::asio::io_service &io_service;
    const std::string sandbox_root;
};

#endif //JD4_SANDBOX_H
