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
#include <boost/process/self.hpp> 
#include <boost/process/context.hpp> 
#include <boost/process/operations.hpp> 
#include <boost/test/unit_test.hpp> 
#include <string> 
#include <vector> 
#include <cstdlib> 

namespace bp = ::boost::process; 

namespace status_base_test { 

static bp::child launch_helper(const std::string &name) 
{ 
    std::vector<std::string> args; 
    args.push_back("helpers"); 
    args.push_back(name); 
    bp::context ctx; 
    ctx.environment = bp::self::get_environment(); 
    return bp::launch(get_helpers_path(), args, ctx); 
} 

template <class Exit_Status> 
void test_exit_failure() 
{ 
    const Exit_Status s = launch_helper("exit-failure").wait(); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_FAILURE); 
} 

template <class Exit_Status> 
void test_exit_success() 
{ 
    const Exit_Status s = launch_helper("exit-success").wait(); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_SUCCESS); 
} 

} 

template <class Exit_Status> 
void add_tests_status_base(boost::unit_test::test_suite *ts) 
{ 
    using namespace status_base_test; 

    ts->add(BOOST_TEST_CASE(&(test_exit_success<Exit_Status>)), 0, 10); 
    ts->add(BOOST_TEST_CASE(&(test_exit_failure<Exit_Status>)), 0, 10); 
} 
