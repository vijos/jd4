#include "process_runner.h"

#include <sys/wait.h>
#include <glog/logging.h>
#include <boost/bind.hpp>

namespace jd4 {

ProcessContext::ProcessContext(boost::asio::io_service& io_service,
                               pid_t pid,
                               const ProcessOptions& options)
    : pid_(pid),
      options_(options),
      timer_(io_service) {
  if (options_.flags.test(ProcessOptions::LIMIT_IDLE_TIME) ||
      options_.flags.test(ProcessOptions::LIMIT_CPU_TIME)) {
    StartTimer();
  }
}

void ProcessContext::StartTimer() {
  std::chrono::nanoseconds wait_duration = std::chrono::nanoseconds::max();
  if (options_.flags.test(ProcessOptions::LIMIT_IDLE_TIME)) {
    // TODO(iceboy): Limit idle time (/proc/stat).
  }
  if (options_.flags.test(ProcessOptions::LIMIT_CPU_TIME)) {
    // TODO(iceboy): Limit CPU time.
  }
  timer_.expires_from_now(wait_duration);
  timer_.async_wait(boost::bind(&ProcessContext::HandleTimer, this, _1));
}

void ProcessContext::HandleTimer(const boost::system::error_code& error_code) {
  if (error_code == boost::asio::error::operation_aborted) {
    return;
  }
  CHECK(!error_code) << error_code.message();
  StartTimer();
}

ProcessRunner::ProcessRunner(boost::asio::io_service& io_service)
    : io_service_(io_service),
      signal_set_(io_service, SIGCHLD) {
  StartSignalWait();
}

void ProcessRunner::Run(boost::string_view path,
                        const ProcessOptions& options) {
  io_service_.notify_fork(boost::asio::io_service::fork_prepare);
  pid_t child_pid = fork();
  if (!child_pid) {
    io_service_.notify_fork(boost::asio::io_service::fork_child);
    if (options.flags.test(ProcessOptions::REDIRECT_STDIN)) {
      CHECK_EQ(dup2(options.stdin_fd, STDIN_FILENO), STDIN_FILENO);
    }
    if (options.flags.test(ProcessOptions::REDIRECT_STDOUT)) {
      CHECK_EQ(dup2(options.stdout_fd, STDOUT_FILENO), STDOUT_FILENO);
    }
    if (options.flags.test(ProcessOptions::REDIRECT_STDERR)) {
      CHECK_EQ(dup2(options.stderr_fd, STDERR_FILENO), STDERR_FILENO);
    }
    LOG(FATAL) << "Child process not implemented.";
  }
  CHECK_GT(child_pid, 0);
  io_service_.notify_fork(boost::asio::io_service::fork_parent);
  child_contexts_.emplace(
      std::piecewise_construct,
      std::forward_as_tuple(child_pid),
      std::forward_as_tuple(io_service_, child_pid, options));
}

void ProcessRunner::StartSignalWait() {
  signal_set_.async_wait(boost::bind(&ProcessRunner::HandleSignalWait, this));
}

void ProcessRunner::HandleSignalWait() {
  siginfo_t info;
  while (!waitid(P_ALL, 0, &info, WEXITED | WNOHANG)) {
    auto child_context_iter = child_contexts_.find(info.si_pid);
    child_contexts_.erase(child_context_iter);
    LOG(INFO) << "PID " << info.si_pid << " exited.";
  }
  CHECK_EQ(errno, ECHILD);
  StartSignalWait();
}

}
