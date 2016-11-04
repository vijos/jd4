#include "process_runner.h"

#include <sys/wait.h>
#include <glog/logging.h>
#include <boost/bind.hpp>
#include <boost/format.hpp>
#include <fstream>

namespace {

int64_t GetNanosecondsPerTick() {
  long ticks_per_second = sysconf(_SC_CLK_TCK);
  CHECK_GT(ticks_per_second, 0);
  return std::nano::den / (std::nano::num * ticks_per_second);
}

}

namespace jd4 {

ProcessContext::ProcessContext(boost::asio::io_service& io_service,
                               pid_t pid,
                               const ProcessOptions& options)
    : pid_(pid),
      options_(options),
      timer_(io_service),
      nanoseconds_per_tick_(GetNanosecondsPerTick()) {
  if (options_.flags.test(ProcessOptions::LIMIT_IDLE_TIME) ||
      options_.flags.test(ProcessOptions::LIMIT_CPU_TIME)) {
    StartTimer();
  }
}

void ProcessContext::StartTimer() {
  std::chrono::nanoseconds duration = std::chrono::nanoseconds::max();
  if (options_.flags.test(ProcessOptions::LIMIT_IDLE_TIME)) {
    // TODO(iceboy): Limit idle time (/proc/stat).
  }
  if (options_.flags.test(ProcessOptions::LIMIT_CPU_TIME)) {
    std::ifstream stream((boost::format("/proc/%d/stat") % pid_).str());
    std::string content{std::istreambuf_iterator<char>(stream),
                        std::istreambuf_iterator<char>()};
    CHECK(stream.good());
    size_t pos = content.rfind(") ");
    CHECK_NE(pos, std::string::npos);
    unsigned long user_time, system_time;
    CHECK_EQ(sscanf(&content[pos + 2],
                    "%*c %*d %*d %*d %*d %*d %*u %*u %*u %*u %*u %lu %lu",
                    &user_time, &system_time), 2);
    std::chrono::nanoseconds cpu_time_elapsed(
        nanoseconds_per_tick_ * (user_time + system_time));
    if (cpu_time_elapsed >= options_.cpu_time_limit) {
      CHECK_EQ(kill(pid_, SIGKILL), 0);
      return;
    }
    duration = min(duration, options_.cpu_time_limit - cpu_time_elapsed);
  }
  static const std::chrono::nanoseconds jitter = std::chrono::milliseconds(10);
  timer_.expires_from_now(duration + jitter);
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
  while (!waitid(P_ALL, 0, &info, WNOHANG | WEXITED)) {
    auto child_context_iter = child_contexts_.find(info.si_pid);
    child_contexts_.erase(child_context_iter);
    LOG(INFO) << "PID " << info.si_pid << " exited.";
  }
  CHECK_EQ(errno, ECHILD);
  StartSignalWait();
}

}
