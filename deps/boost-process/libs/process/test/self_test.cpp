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
#  include <unistd.h> 
#elif defined(BOOST_WINDOWS_API) 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include <boost/process/self.hpp> 
#include <boost/process/environment.hpp> 
#include <boost/test/unit_test.hpp> 

namespace bp = ::boost::process; 
namespace but = ::boost::unit_test; 

class launcher 
{ 
public: 
    bp::self &operator()(bp::self::id_type id) 
    { 
        return bp::self::get_instance(); 
    } 
}; 

static void test_id() 
{ 
    bp::self &p = bp::self::get_instance(); 

#if defined(BOOST_POSIX_API) 
    BOOST_REQUIRE(p.get_id() == ::getpid()); 
#elif defined(BOOST_WINDOWS_API) 
    BOOST_REQUIRE(p.get_id() == ::GetCurrentProcessId()); 
#endif 
} 

static void test_get_environment() 
{ 
    bp::self &p = bp::self::get_instance(); 

    bp::environment env1 = p.get_environment(); 
    BOOST_CHECK(env1.find("THIS_SHOULD_NOT_BE_DEFINED") == env1.end()); 

#if defined(BOOST_POSIX_API) 
    BOOST_REQUIRE(::setenv("THIS_SHOULD_BE_DEFINED", "some-value", 1) == 0); 
#elif defined(BOOST_WINDOWS_API) 
    BOOST_REQUIRE(::SetEnvironmentVariableA("THIS_SHOULD_BE_DEFINED", "some-value") != 0); 
#endif 

    bp::environment env2 = p.get_environment(); 
    bp::environment::const_iterator it = env2.find("THIS_SHOULD_BE_DEFINED"); 
    BOOST_CHECK(it != env2.end()); 
    BOOST_CHECK_EQUAL(it->second, "some-value"); 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("self test suite"); 

    test->add(BOOST_TEST_CASE(&test_id)); 
    test->add(BOOST_TEST_CASE(&test_get_environment)); 

    return test; 
} 
