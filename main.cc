#include <gflags/gflags.h>
#include <glog/logging.h>
#include <boost/asio.hpp>

int main(int argc, char *argv[]) {
  google::InitGoogleLogging(argv[0]);
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  boost::asio::io_service io_service;
}
