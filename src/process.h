#ifndef JD4_PROCESS_H
#define JD4_PROCESS_H

#include <unistd.h>
#include <boost/asio.hpp>
#include <utility>
#include "shim.h"

template<typename Callback>
pid_t Fork(Callback callback) {
    pid_t pid = fork();
    if (pid == 0) {
        callback();
        exit(0);
    }
    return pid;
}

template<typename Callback>
pid_t Fork(boost::asio::io_service &io_service, Callback callback) {
    io_service.notify_fork(boost::asio::io_service::fork_prepare);
    pid_t pid = Fork([&io_service, callback = std::move(callback)]() {
        io_service.notify_fork(boost::asio::io_service::fork_child);
        callback();
    });
    if (pid > 0) {
        io_service.notify_fork(boost::asio::io_service::fork_parent);
    }
    return pid;
}

void Sandbox(const Path& sandbox_root,
             const Vector<Pair<String, String>> &mount_points);

#endif //JD4_PROCESS_H
