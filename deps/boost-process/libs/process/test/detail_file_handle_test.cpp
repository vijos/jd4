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
#  include <cstdlib> 
#  include <cstring> 
#  include <unistd.h> 
#elif defined(BOOST_WINDOWS_API) 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include <boost/process/detail/file_handle.hpp> 
#include <boost/test/unit_test.hpp> 
#include <iostream> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

static bpd::file_handle::handle_type get_test_handle() 
{ 
#if defined(BOOST_POSIX_API) 
    return STDOUT_FILENO; 
#elif defined(BOOST_WINDOWS_API) 
    HANDLE htest = ::GetStdHandle(STD_OUTPUT_HANDLE); 
    BOOST_REQUIRE(htest != INVALID_HANDLE_VALUE); 
    return htest; 
#endif 
} 

static void test_construct() 
{ 
    bpd::file_handle fh1; 
    BOOST_CHECK(!fh1.valid()); 

    bpd::file_handle fh2(get_test_handle()); 
    BOOST_CHECK(fh2.valid()); 
    fh2.release(); 
} 

static void test_copy() 
{ 
    bpd::file_handle fh1; 
    bpd::file_handle fh2(get_test_handle()); 

    bpd::file_handle fh3(fh2); 
    BOOST_REQUIRE(!fh2.valid()); 
    BOOST_REQUIRE(fh3.valid()); 

    fh1 = fh3; 
    BOOST_REQUIRE(!fh3.valid()); 
    BOOST_REQUIRE(fh1.valid()); 

    fh1.release(); 
} 

static void test_get() 
{ 
    bpd::file_handle fh1(get_test_handle()); 
    BOOST_REQUIRE_EQUAL(fh1.get(), get_test_handle()); 
} 

#if defined(BOOST_POSIX_API) 
static void test_posix_dup() 
{ 
    int pfd[2]; 

    BOOST_REQUIRE(::pipe(pfd) != -1); 
    bpd::file_handle rend(pfd[0]); 
    bpd::file_handle wend(pfd[1]); 

    BOOST_REQUIRE(rend.get() != 10); 
    BOOST_REQUIRE(wend.get() != 10); 
    bpd::file_handle fh1 = bpd::file_handle::posix_dup(wend.get(), 10); 
    BOOST_REQUIRE_EQUAL(fh1.get(), 10); 

    BOOST_REQUIRE(::write(wend.get(), "test-posix-dup", 14) != -1); 
    char buf1[15]; 
    BOOST_REQUIRE_EQUAL(::read(rend.get(), buf1, sizeof(buf1)), 14); 
    buf1[14] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf1, "test-posix-dup") == 0); 

    BOOST_REQUIRE(::write(fh1.get(), "test-posix-dup", 14) != -1); 
    char buf2[15]; 
    BOOST_REQUIRE_EQUAL(::read(rend.get(), buf2, sizeof(buf2)), 14); 
    buf2[14] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf2, "test-posix-dup") == 0); 
} 

static void test_posix_remap() 
{ 
    int pfd[2]; 

    BOOST_REQUIRE(::pipe(pfd) != -1); 
    bpd::file_handle rend(pfd[0]); 
    bpd::file_handle wend(pfd[1]); 

    BOOST_REQUIRE(rend.get() != 10); 
    BOOST_REQUIRE(wend.get() != 10); 
    wend.posix_remap(10); 
    BOOST_REQUIRE_EQUAL(wend.get(), 10); 
    BOOST_REQUIRE(::write(wend.get(), "test-posix-remap", 16) != -1); 

    char buf[17]; 
    BOOST_REQUIRE_EQUAL(::read(rend.get(), buf, sizeof(buf)), 16); 
    buf[16] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf, "test-posix-remap") == 0); 
} 
#endif 

#if defined(BOOST_WINDOWS_API) 
static void test_win32_dup() 
{ 
    HANDLE in, out; 
    SECURITY_ATTRIBUTES sa; 
    ZeroMemory(&sa, sizeof(sa)); 
    sa.nLength = sizeof(sa); 
    sa.lpSecurityDescriptor = NULL; 
    sa.bInheritHandle = FALSE; 
    BOOST_REQUIRE(::CreatePipe(&in, &out, &sa, 0) != 0); 
    bpd::file_handle rend(in); 
    bpd::file_handle wend(out); 

    DWORD flags, rcnt; 
    char buf[15]; 

    bpd::file_handle out2 = bpd::file_handle::win32_dup(wend.get(), false); 
    BOOST_REQUIRE(::GetHandleInformation(out2.get(), &flags) != 0); 
    BOOST_REQUIRE(!(flags & HANDLE_FLAG_INHERIT)); 

    bpd::file_handle out3 = bpd::file_handle::win32_dup(wend.get(), true); 
    BOOST_REQUIRE(::GetHandleInformation(out3.get(), &flags) != 0); 
    BOOST_REQUIRE(flags & HANDLE_FLAG_INHERIT); 

    BOOST_REQUIRE(::WriteFile(wend.get(), "test-win32-dup", 14, &rcnt, 
        NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    BOOST_REQUIRE(::ReadFile(rend.get(), buf, sizeof(buf), &rcnt, NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    buf[14] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf, "test-win32-dup") == 0); 

    BOOST_REQUIRE(::WriteFile(out2.get(), "test-win32-dup", 14, &rcnt, 
        NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    BOOST_REQUIRE(::ReadFile(rend.get(), buf, sizeof(buf), &rcnt, NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    buf[14] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf, "test-win32-dup") == 0); 

    BOOST_REQUIRE(::WriteFile(out3.get(), "test-win32-dup", 14, &rcnt, 
        NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    BOOST_REQUIRE(::ReadFile(rend.get(), buf, sizeof(buf), &rcnt, NULL) != 0); 
    BOOST_REQUIRE_EQUAL(rcnt, 14); 
    buf[14] = '\0'; 
    BOOST_REQUIRE(std::strcmp(buf, "test-win32-dup") == 0); 
} 

static void test_win32_set_inheritable() 
{ 
    HANDLE in, out; 
    SECURITY_ATTRIBUTES sa; 
    ZeroMemory(&sa, sizeof(sa)); 
    sa.nLength = sizeof(sa); 
    sa.lpSecurityDescriptor = NULL; 
    sa.bInheritHandle = FALSE; 
    BOOST_REQUIRE(::CreatePipe(&in, &out, &sa, 0) != 0); 
    bpd::file_handle rend(in); 
    bpd::file_handle wend(out); 

    DWORD flags; 

    bpd::file_handle out2 = bpd::file_handle::win32_dup(wend.get(), false); 
    BOOST_REQUIRE(::GetHandleInformation(out2.get(), &flags) != 0); 
    BOOST_REQUIRE(!(flags & HANDLE_FLAG_INHERIT)); 

    bpd::file_handle out3 = bpd::file_handle::win32_dup(wend.get(), true); 
    BOOST_REQUIRE(::GetHandleInformation(out3.get(), &flags) != 0); 
    BOOST_REQUIRE(flags & HANDLE_FLAG_INHERIT); 
} 
#endif 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("detail::file_handle test suite"); 

    test->add(BOOST_TEST_CASE(&test_construct)); 
    test->add(BOOST_TEST_CASE(&test_copy)); 
    test->add(BOOST_TEST_CASE(&test_get)); 

#if defined(BOOST_POSIX_API) 
    test->add(BOOST_TEST_CASE(&test_posix_dup)); 
    test->add(BOOST_TEST_CASE(&test_posix_remap)); 
#elif defined(BOOST_WINDOWS_API) 
    test->add(BOOST_TEST_CASE(&test_win32_dup)); 
    test->add(BOOST_TEST_CASE(&test_win32_set_inheritable)); 
#endif 

    return test; 
} 
