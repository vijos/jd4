#include <unistd.h>
#include <boost/asio.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/utility/string_view.hpp>
#include <unordered_map>

namespace jd4 {

class ProcessRunner {
 public:
  explicit ProcessRunner(boost::asio::io_service& io_service);
  void Run(boost::string_view path);

 private:
  void StartSignalWait();
  void HandleSignalWait();

 private:
  struct ChildContext {
    boost::posix_time::ptime start_time;
  };

 private:
  boost::asio::io_service& io_service_;
  boost::asio::signal_set signal_set_;
  std::unordered_map<pid_t, ChildContext> child_contexts_;
};

}
