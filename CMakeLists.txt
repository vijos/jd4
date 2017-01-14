cmake_minimum_required(VERSION 2.8.12)

project(jd4)

SET(Boost_USE_STATIC_LIBS ON)
find_package(Boost COMPONENTS log system)

add_executable(jd4 src/main.cc)
target_link_libraries(jd4 ${Boost_LIBRARIES} pthread)
