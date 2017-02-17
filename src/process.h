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
pid_t Fork(EventLoop &loop, Callback callback) {
    loop.notify_fork(EventLoop::fork_prepare);
    pid_t pid = Fork([&loop, callback = std::move(callback)]() {
        loop.notify_fork(EventLoop::fork_child);
        callback();
    });
    if (pid > 0) {
        loop.notify_fork(EventLoop::fork_parent);
    }
    return pid;
}

void Sandbox(const Path& sandbox_root,
             const Vector<Pair<String, String>> &mount_points);

#endif //JD4_PROCESS_H
