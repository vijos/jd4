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

void PrepareSandbox(const Path &sandbox_dir, const Vector<Pair<Path, Path>> &mount_points);
void CompleteSandbox();

inline void Sandbox(const Path &sandbox_dir, const Vector<Pair<Path, Path>> &mount_points) {
    PrepareSandbox(sandbox_dir, mount_points);
    CompleteSandbox();
}

inline Process Execute(const Path &path, const Vector<String> &args, const Vector<String> &envs, const Path &work_dir) {
    using namespace boost::process::initializers;
    return boost::process::execute(run_exe(path), set_args(args), set_env(envs), start_in_dir(work_dir.string()));
}

inline int WaitForExit(const Process &process) {
    return boost::process::wait_for_exit(process);
}

#endif //JD4_PROCESS_H
