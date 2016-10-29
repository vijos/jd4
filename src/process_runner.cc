#include "process_runner.h"

#include <sys/wait.h>
#include <glog/logging.h>
#include <boost/bind.hpp>

namespace jd4 {

ProcessRunner::ProcessRunner(boost::asio::io_service& io_service)
    : io_service_(io_service),
      signal_set_(io_service, SIGCHLD) {
  start_signal_wait();
}

void ProcessRunner::run(boost::string_view path) {
  io_service_.notify_fork(boost::asio::io_service::fork_prepare);
  pid_t child_pid = fork();
  if (!child_pid) {
    io_service_.notify_fork(boost::asio::io_service::fork_child);
    LOG(FATAL) << "Child process not implemented.";
  }
  CHECK_GT(child_pid, 0);
  io_service_.notify_fork(boost::asio::io_service::fork_parent);
  child_contexts_.emplace(child_pid, ChildContext {
      .start_time = boost::posix_time::microsec_clock::universal_time(),
  });
}

void ProcessRunner::start_signal_wait() {
  signal_set_.async_wait(boost::bind(&ProcessRunner::handle_signal_wait, this));
}

void ProcessRunner::handle_signal_wait() {
  siginfo_t info;
  while (!waitid(P_ALL, 0, &info, WEXITED | WNOHANG)) {
    auto child_context_iter = child_contexts_.find(info.si_pid);
    child_contexts_.erase(child_context_iter);
    LOG(INFO) << "PID " << info.si_pid << " exited.";
  }
  CHECK_EQ(errno, ECHILD);
  start_signal_wait();
}

}
