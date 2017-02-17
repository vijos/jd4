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
#if defined(BOOST_WINDOWS_API) 
#  include "launch_base_test.hpp" 
#  include <boost/process/child.hpp> 
#  include <boost/process/self.hpp> 
#  include <boost/process/status.hpp> 
#  include <boost/process/win32_child.hpp> 
#  include <boost/process/win32_context.hpp> 
#  include <boost/process/win32_operations.hpp> 
#  include <boost/process/stream_behavior.hpp> 
#  include <vector> 
#  include <string> 
#  include <sstream> 
#  include <cstdlib> 
#  include <windows.h> 

namespace bp = ::boost::process; 
#endif 

#include <boost/filesystem/operations.hpp> 
#include <boost/test/unit_test.hpp> 

namespace bfs = ::boost::filesystem; 
namespace but = ::boost::unit_test; 

#if defined(BOOST_WINDOWS_API) 
class launcher 
{ 
public: 
    bp::win32_child operator()(const std::vector<std::string> args, 
               bp::win32_context ctx, 
               bp::stream_behavior bstdin = bp::close_stream(), 
               bp::stream_behavior bstdout = bp::close_stream(), 
               bp::stream_behavior bstderr = bp::close_stream(), 
               bool usein = false) 
        const 
    { 
        ctx.stdin_behavior = bstdin; 
        ctx.stdout_behavior = bstdout; 
        ctx.stderr_behavior = bstderr; 
        if (ctx.environment.empty()) 
            ctx.environment = bp::self::get_environment(); 
        return bp::win32_launch(get_helpers_path(), args, ctx); 
    } 
}; 

template <class Child> 
static void test_startupinfo() 
{ 
    std::vector<std::string> args; 
    args.push_back("helpers"); 
    args.push_back("win32-print-startupinfo"); 

    std::string line; 
    std::ostringstream flags; 

    bp::win32_context ctx1; 
    ctx1.stdout_behavior = bp::capture_stream(); 
    ctx1.environment = bp::self::get_environment(); 
    flags << STARTF_USESTDHANDLES; 
    Child c1 = bp::win32_launch(get_helpers_path(), args, ctx1); 
    portable_getline(c1.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwFlags = " + flags.str()); 
    flags.str(""); 
    portable_getline(c1.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwX = 0"); 
    portable_getline(c1.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwY = 0"); 
    portable_getline(c1.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwXSize = 0"); 
    portable_getline(c1.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwYSize = 0"); 
    const bp::status s1 = c1.wait(); 
    BOOST_REQUIRE(s1.exited()); 
    BOOST_CHECK_EQUAL(s1.exit_status(), EXIT_SUCCESS); 

    STARTUPINFO si; 
    ::ZeroMemory(&si, sizeof(si)); 
    si.cb = sizeof(si); 
    si.dwFlags = STARTF_USEPOSITION | STARTF_USESIZE; 
    si.dwX = 100; 
    si.dwY = 200; 
    si.dwXSize = 300; 
    si.dwYSize = 400; 
    bp::win32_context ctx2; 
    ctx2.startupinfo = &si; 
    ctx2.stdout_behavior = bp::capture_stream(); 
    ctx2.environment = bp::self::get_environment(); 
    flags << (STARTF_USESTDHANDLES | STARTF_USEPOSITION | STARTF_USESIZE); 
    Child c2 = bp::win32_launch(get_helpers_path(), args, ctx2); 
    portable_getline(c2.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwFlags = " + flags.str()); 
    flags.str(""); 
    portable_getline(c2.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwX = 100"); 
    portable_getline(c2.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwY = 200"); 
    portable_getline(c2.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwXSize = 300"); 
    portable_getline(c2.get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "dwYSize = 400"); 
    const bp::status s2 = c2.wait(); 
    BOOST_REQUIRE(s2.exited()); 
    BOOST_CHECK_EQUAL(s2.exit_status(), EXIT_SUCCESS); 
} 
#endif 

#if !defined(BOOST_WINDOWS_API) 
static void test_dummy() 
{ 
} 
#endif 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    bfs::initial_path(); 

    but::test_suite *test = BOOST_TEST_SUITE("win32_launch test suite"); 

#if defined(BOOST_WINDOWS_API) 
    add_tests_launch_base<launcher, bp::win32_context, bp::child>(test); 
    add_tests_launch_base<launcher, bp::win32_context, bp::win32_child>(test); 
    test->add(BOOST_TEST_CASE(&(test_startupinfo<bp::child>))); 
    test->add(BOOST_TEST_CASE(&(test_startupinfo<bp::win32_child>))); 
#else 
    test->add(BOOST_TEST_CASE(&test_dummy)); 
#endif 

    return test; 
} 
