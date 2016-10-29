cmake_minimum_required (VERSION 3.0)

project (jd4)

add_subdirectory (deps/gflags)
add_subdirectory (deps/glog)
find_package (Boost COMPONENTS system thread)

add_executable (jd4 src/main.cc src/process_runner.cc)
target_link_libraries (jd4 gflags glog ${Boost_LIBRARIES})
