// 
// Boost.Process 
// ~~~~~~~~~~~~~ 
// 
// Copyright (c) 2006, 2007 Julio M. Merino Vidal 
// Copyright (c) 2008 Boris Schaeling 
// 
// Distributed under the Boost Software License, Version 1.0. (See accompanying 
// file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt) 
// 

#include <boost/process/config.hpp> 

#if defined(BOOST_POSIX_API) 
#  include <sys/stat.h> 
#  include <fcntl.h> 
#  include <unistd.h> 
#elif defined(BOOST_WINDOWS_API) 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include <boost/process/detail/systembuf.hpp> 
#include <boost/test/unit_test.hpp> 
#include <istream> 
#include <ostream> 
#include <fstream> 
#include <cstddef> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

static void check_data(std::istream &is, std::size_t length) 
{ 
    char ch = 'A', chr; 
    std::size_t cnt = 0; 
    while (is >> chr) 
    { 
        BOOST_CHECK(ch == chr); 
        if (ch == 'Z') 
            ch = 'A'; 
        else 
            ++ch; 
        ++cnt; 
    } 
    BOOST_CHECK(cnt == length); 
} 

static void write_data(std::ostream &os, std::size_t length) 
{ 
    char ch = 'A'; 
    for (std::size_t i = 0; i < length; ++i) 
    { 
        os << ch; 
        if (ch == 'Z') 
            ch = 'A'; 
        else 
            ++ch; 
    } 
    os.flush(); 
} 

static void remove_file(const std::string &name) 
{ 
#if defined(BOOST_WINDOWS_API) 
    ::DeleteFileA(name.c_str()); 
#else 
    ::unlink(name.c_str()); 
#endif 
} 

static void test_read(std::size_t length, std::size_t bufsize) 
{ 
    std::ofstream f("test_read.txt"); 
    write_data(f, length); 
    f.close(); 

#if defined(BOOST_WINDOWS_API) 
    HANDLE hfile = ::CreateFileA("test_read.txt", 
        GENERIC_READ, 0, NULL, OPEN_EXISTING, 
        FILE_ATTRIBUTE_NORMAL, NULL); 
    BOOST_REQUIRE(hfile != INVALID_HANDLE_VALUE); 
    bpd::systembuf sb(hfile, bufsize); 
    std::istream is(&sb); 
    check_data(is, length); 
    ::CloseHandle(hfile); 
#else 
    int fd = ::open("test_read.txt", O_RDONLY); 
    BOOST_CHECK(fd != -1); 
    bpd::systembuf sb(fd, bufsize); 
    std::istream is(&sb); 
    check_data(is, length); 
    ::close(fd); 
#endif 
    remove_file("test_read.txt"); 
} 

static void test_short_read() 
{ 
    test_read(64, 1024); 
} 

static void test_long_read() 
{ 
    test_read(64 * 1024, 1024); 
} 

static void test_write(std::size_t length, std::size_t bufsize) 
{ 
#if defined(BOOST_WINDOWS_API) 
    HANDLE hfile = ::CreateFileA("test_write.txt", 
        GENERIC_WRITE, 0, NULL, CREATE_NEW, 
        FILE_ATTRIBUTE_NORMAL, NULL); 
    BOOST_REQUIRE(hfile != INVALID_HANDLE_VALUE); 
    bpd::systembuf sb(hfile, bufsize); 
    std::ostream os(&sb); 
    write_data(os, length); 
    ::CloseHandle(hfile); 
#else 
    int fd = ::open("test_write.txt", O_WRONLY | O_CREAT | O_TRUNC, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH); 
    BOOST_CHECK(fd != -1); 
    bpd::systembuf sb(fd, bufsize); 
    std::ostream os(&sb); 
    write_data(os, length); 
    ::close(fd); 
#endif 

    std::ifstream is("test_write.txt"); 
    check_data(is, length); 
    is.close(); 
    remove_file("test_write.txt"); 
} 

static void test_short_write() 
{ 
    test_write(64, 1024); 
} 

static void test_long_write() 
{ 
    test_write(64 * 1024, 1024); 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("detail::systembuf test suite"); 

    test->add(BOOST_TEST_CASE(&test_short_read)); 
    test->add(BOOST_TEST_CASE(&test_long_read)); 
    test->add(BOOST_TEST_CASE(&test_short_write)); 
    test->add(BOOST_TEST_CASE(&test_long_write)); 

    return test; 
} 
