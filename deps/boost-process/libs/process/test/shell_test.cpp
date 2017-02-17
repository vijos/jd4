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

#include "misc.hpp" 
#include <boost/process/child.hpp> 
#include <boost/process/context.hpp> 
#include <boost/process/stream_behavior.hpp> 
#include <boost/process/operations.hpp> 
#include <boost/process/pistream.hpp> 
#include <boost/process/status.hpp> 
#include <boost/test/unit_test.hpp> 
#include <string> 
#include <cstdlib> 

namespace bp = ::boost::process; 
namespace but = ::boost::unit_test; 

static void test_shell_execution() 
{ 
    std::string command; 
    if (bp_api_type == posix_api) 
        command = "echo test | sed 's,^,LINE-,'"; 
    else if (bp_api_type == win32_api) 
        command = "if foo==foo echo LINE-test"; 
    else 
        BOOST_REQUIRE(false); 

    bp::context ctx; 
    ctx.stdout_behavior = bp::capture_stream(); 
    // Julio: Without the following line, bash returns an exit status of 4, 
    // which makes the test fail...  Why?  I don't know. 
    ctx.stderr_behavior = bp::redirect_stream_to_stdout(); 
    bp::child c = bp::launch_shell(command, ctx); 

    bp::pistream &is = c.get_stdout(); 
    std::string word; 
    is >> word; 
    BOOST_CHECK_EQUAL(word, "LINE-test"); 

    const bp::status s = c.wait(); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_SUCCESS); 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("shell test suite"); 

    test->add(BOOST_TEST_CASE(&test_shell_execution)); 

    return test; 
} 
