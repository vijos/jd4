#ifndef JD4_PROCESS_H
#define JD4_PROCESS_H

#include <sys/mount.h>
#include <unistd.h>
#include <boost/asio.hpp>
#include <utility>
#include "shim.h"
#include "util.h"

template<typename Callback>
Process Fork(Callback callback) {
    pid_t pid = fork();
    CHECK_UNIX(pid);
    if (pid == 0) {
        callback();
        exit(0);
    }
    return Process(pid);
}

template<typename Callback>
Process Fork(EventLoop &loop, Callback callback) {
    loop.notify_fork(EventLoop::fork_prepare);
    Process process = Fork([&loop, callback = std::move(callback)]() {
        loop.notify_fork(EventLoop::fork_child);
        callback();
    });
    loop.notify_fork(EventLoop::fork_parent);
    return process;
}

inline int WaitForExit(const Process &process) {
    return boost::process::wait_for_exit(process);
}

#endif //JD4_PROCESS_H
