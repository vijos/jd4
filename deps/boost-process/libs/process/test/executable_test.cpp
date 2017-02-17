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
#  include <stdlib.h> 
#  if defined(__CYGWIN__) 
#    undef BOOST_POSIX_API 
#    define BOOST_CYGWIN_PATH 
#  endif 
#elif defined(BOOST_WINDOWS_API) 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include "misc.hpp" 
#include <boost/process/operations.hpp> 
#include <boost/test/unit_test.hpp> 
#include <string> 
#include <stdexcept> 

namespace bfs = ::boost::filesystem; 
namespace bp = ::boost::process; 
namespace but = ::boost::unit_test; 

static void test_find_default() 
{ 
    std::string helpersname = bfs::path(get_helpers_path()).leaf(); 

    BOOST_CHECK_THROW(bp::find_executable_in_path(helpersname), 
        boost::filesystem::filesystem_error); 
} 

static void test_find_env() 
{ 
    bfs::path orig = get_helpers_path(); 
    std::string helpersdir = orig.branch_path().string(); 
    std::string helpersname = orig.leaf(); 

#if defined(BOOST_POSIX_API) 
    std::string oldpath = ::getenv("PATH"); 
    try 
    { 
        ::setenv("PATH", helpersdir.c_str(), 1); 
        bfs::path found = bp::find_executable_in_path(helpersname); 
        BOOST_CHECK(bfs::equivalent(orig, found)); 
        ::setenv("PATH", oldpath.c_str(), 1); 
    } 
    catch (...) 
    { 
        ::setenv("PATH", oldpath.c_str(), 1); 
    } 
#elif defined(BOOST_WINDOWS_API) 
    char oldpath[MAX_PATH]; 
    BOOST_REQUIRE(::GetEnvironmentVariableA("PATH", oldpath, MAX_PATH) != 0); 
    try 
    { 
        BOOST_REQUIRE(::SetEnvironmentVariableA("PATH", 
            helpersdir.c_str()) != 0); 
        bfs::path found = bp::find_executable_in_path(helpersname); 
        BOOST_CHECK(bfs::equivalent(orig, found)); 
        BOOST_REQUIRE(::SetEnvironmentVariable("PATH", oldpath) != 0); 
    } 
    catch (...) 
    { 
        BOOST_REQUIRE(::SetEnvironmentVariable("PATH", oldpath) != 0); 
    } 
#endif 
} 

static void test_find_param() 
{ 
    bfs::path orig = get_helpers_path(); 
    std::string helpersdir = orig.branch_path().string(); 
    std::string helpersname = orig.leaf(); 

    bfs::path found = bp::find_executable_in_path(helpersname, helpersdir); 
    BOOST_CHECK(bfs::equivalent(orig, found)); 
} 

static void test_progname() 
{ 
    BOOST_CHECK_EQUAL(bp::executable_to_progname("foo"), "foo"); 
    BOOST_CHECK_EQUAL(bp::executable_to_progname("/foo"), "foo"); 
    BOOST_CHECK_EQUAL(bp::executable_to_progname("/foo/bar"), "bar"); 
    BOOST_CHECK_EQUAL(bp::executable_to_progname("///foo///bar"), "bar"); 
    BOOST_CHECK_EQUAL(bp::executable_to_progname("/foo/bar/baz"), "baz"); 

    if (bp_api_type == win32_api) 
    { 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.exe"), "f"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.com"), "f"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.bat"), "f"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.bar"), "f.bar"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.bar.exe"), "f.bar"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.bar.com"), "f.bar"); 
        BOOST_CHECK_EQUAL(bp::executable_to_progname("f.bar.bat"), "f.bar"); 
    } 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    bfs::initial_path(); 

    but::test_suite *test = BOOST_TEST_SUITE("executable test suite"); 

    test->add(BOOST_TEST_CASE(&test_find_default)); 
    test->add(BOOST_TEST_CASE(&test_find_env)); 
    test->add(BOOST_TEST_CASE(&test_find_param)); 
    test->add(BOOST_TEST_CASE(&test_progname)); 

    return test; 
} 
