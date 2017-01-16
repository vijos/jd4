cmake_minimum_required(VERSION 2.8.12)

project(jd4)

set(CMAKE_CXX_STANDARD 11)
set(Boost_USE_STATIC_LIBS ON)
find_package(Boost COMPONENTS log system)

add_executable(jd4 src/main.cpp src/sandbox.cpp)
target_link_libraries(jd4 ${Boost_LIBRARIES} pthread)
