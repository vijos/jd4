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
#  include <boost/process/detail/posix_ops.hpp> 
#  include <stdlib.h> 
#elif defined(BOOST_WINDOWS_API) 
#  include <boost/process/detail/win32_ops.hpp> 
#  include <boost/shared_array.hpp> 
#  include <cstring> 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include <boost/process/environment.hpp> 
#include <boost/process/self.hpp> 
#include <boost/test/unit_test.hpp> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

static void test_current() 
{ 
    bp::environment env1 = bp::self::get_environment(); 
    BOOST_CHECK(env1.find("THIS_SHOULD_NOT_BE_DEFINED") == env1.end()); 

#if defined(BOOST_POSIX_API) 
    BOOST_REQUIRE(::setenv("THIS_SHOULD_BE_DEFINED", "some-value", 1) == 0); 
#elif defined(BOOST_WINDOWS_API) 
    BOOST_REQUIRE(::SetEnvironmentVariable("THIS_SHOULD_BE_DEFINED", 
        "some-value") != 0); 
#endif 

    bp::environment env2 = bp::self::get_environment(); 
    bp::environment::const_iterator it = 
        env2.find("THIS_SHOULD_BE_DEFINED"); 
    BOOST_CHECK(it != env2.end()); 
    BOOST_CHECK_EQUAL(it->second, "some-value"); 
} 

#if defined(BOOST_POSIX_API) 
static void test_envp() 
{ 
    bp::environment env; 
    env.insert(bp::environment::value_type("VAR1", "value1")); 
    env.insert(bp::environment::value_type("VAR2", "value2")); 
    env.insert(bp::environment::value_type("VAR3", "value3")); 

    char **ep = bpd::environment_to_envp(env); 

    BOOST_REQUIRE(ep[0] != NULL); 
    BOOST_REQUIRE_EQUAL(std::string(ep[0]), "VAR1=value1"); 
    delete[] ep[0]; 

    BOOST_REQUIRE(ep[1] != NULL); 
    BOOST_REQUIRE_EQUAL(std::string(ep[1]), "VAR2=value2"); 
    delete[] ep[1]; 

    BOOST_REQUIRE(ep[2] != NULL); 
    BOOST_REQUIRE_EQUAL(std::string(ep[2]), "VAR3=value3"); 
    delete[] ep[2]; 

    BOOST_REQUIRE(ep[3] == NULL); 
    delete[] ep; 
} 

static void test_envp_unsorted() 
{ 
    bp::environment env; 
    env.insert(bp::environment::value_type("VAR2", "value2")); 
    env.insert(bp::environment::value_type("VAR1", "value1")); 

    char **ep = bpd::environment_to_envp(env); 

    BOOST_REQUIRE(ep[0] != NULL); 
    BOOST_REQUIRE_EQUAL(std::string(ep[0]), "VAR1=value1"); 
    delete[] ep[0]; 

    BOOST_REQUIRE(ep[1] != NULL); 
    BOOST_REQUIRE_EQUAL(std::string(ep[1]), "VAR2=value2"); 
    delete[] ep[1]; 

    BOOST_REQUIRE(ep[2] == NULL); 
    delete[] ep; 
} 
#endif 

#if defined(BOOST_WINDOWS_API) 
static void test_strings() 
{ 
    bp::environment env; 
    env.insert(bp::environment::value_type("VAR1", "value1")); 
    env.insert(bp::environment::value_type("VAR2", "value2")); 
    env.insert(bp::environment::value_type("VAR3", "value3")); 

    boost::shared_array<char> strs = 
        bpd::environment_to_win32_strings(env); 
    BOOST_REQUIRE(strs.get() != NULL); 

    char *expected = "VAR1=value1\0VAR2=value2\0VAR3=value3\0\0"; 
    BOOST_REQUIRE(std::memcmp(strs.get(), expected, 37) == 0); 
} 

static void test_strings_unsorted() 
{ 
    bp::environment env; 
    env.insert(bp::environment::value_type("VAR2", "value2")); 
    env.insert(bp::environment::value_type("VAR1", "value1")); 

    boost::shared_array<char> strs = 
        bpd::environment_to_win32_strings(env); 
    BOOST_REQUIRE(strs.get() != NULL); 

    char *expected = "VAR1=value1\0VAR2=value2\0\0"; 
    BOOST_REQUIRE(std::memcmp(strs.get(), expected, 25) == 0); 
} 
#endif 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("environment test suite"); 

    test->add(BOOST_TEST_CASE(&test_current)); 
#if defined(BOOST_POSIX_API) 
    test->add(BOOST_TEST_CASE(&test_envp)); 
    test->add(BOOST_TEST_CASE(&test_envp_unsorted)); 
#elif defined(BOOST_WINDOWS_API) 
    test->add(BOOST_TEST_CASE(&test_strings)); 
    test->add(BOOST_TEST_CASE(&test_strings_unsorted)); 
#endif 

    return test; 
} 
