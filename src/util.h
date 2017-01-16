#ifndef JD4_UTIL_H
#define JD4_UTIL_H

#include <unistd.h>
#include <boost/asio.hpp>

template<typename Callback>
pid_t Fork(Callback &&callback) {
    pid_t pid = fork();
    if (pid == 0) {
        callback();
        exit(0);
    }
    return pid;
}

template<typename Callback>
pid_t Fork(Callback &&callback, boost::asio::io_service &io_service) {
    io_service.notify_fork(boost::asio::io_service::fork_prepare);
    pid_t pid = Fork([&io_service, &callback]() {
        io_service.notify_fork(boost::asio::io_service::fork_child);
        callback();
    });
    if (pid > 0) {
        io_service.notify_fork(boost::asio::io_service::fork_parent);
    }
    return pid;
}

#endif //JD4_UTIL_H
