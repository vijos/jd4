#include <unistd.h>
#include <boost/asio.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/utility/string_view.hpp>
#include <bitset>
#include <chrono>
#include <unordered_map>

namespace jd4 {

struct ProcessOptions {
  enum Flags {
    REDIRECT_STDIN,
    REDIRECT_STDOUT,
    REDIRECT_STDERR,
    LIMIT_IDLE_TIME,
    LIMIT_CPU_TIME,
    LIMIT_MEMORY,
    FLAGS_MAX,
  };

  std::bitset<FLAGS_MAX> flags;
  int stdin_fd;
  int stdout_fd;
  int stderr_fd;
  std::chrono::nanoseconds idle_time_limit;
  std::chrono::nanoseconds cpu_time_limit;
  std::size_t memory_limit;
};

class ProcessContext {
 public:
  explicit ProcessContext(boost::asio::io_service& io_service,
                          pid_t pid,
                          const ProcessOptions& options);

 private:
  void StartTimer();
  void HandleTimer(const boost::system::error_code& error_code);

 private:
  const pid_t pid_;
  const ProcessOptions options_;
  boost::asio::steady_timer timer_;
};

class ProcessRunner {
 public:
  explicit ProcessRunner(boost::asio::io_service& io_service);
  void Run(boost::string_view path) { Run(path, ProcessOptions()); }
  void Run(boost::string_view path, const ProcessOptions& options);

 private:
  void StartSignalWait();
  void HandleSignalWait();

 private:
  boost::asio::io_service& io_service_;
  boost::asio::signal_set signal_set_;
  std::unordered_map<pid_t, ProcessContext> child_contexts_;
};

}
