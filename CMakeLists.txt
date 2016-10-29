cmake_minimum_required (VERSION 3.0)

project (jd4)

add_subdirectory (deps/gflags)
add_subdirectory (deps/glog)

add_executable (jd4 main.cc)
target_link_libraries (jd4 gflags glog)
