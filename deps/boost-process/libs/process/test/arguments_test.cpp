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
#  include <utility> 
#  include <cstddef> 
#elif defined(BOOST_WINDOWS_API) 
#  include <boost/process/detail/win32_ops.hpp> 
#  include <cstring> 
#else 
#  error "Unsupported platform." 
#endif 

#include "misc.hpp" 
#include <boost/filesystem/operations.hpp> 
#include <boost/process/child.hpp> 
#include <boost/process/context.hpp> 
#include <boost/process/self.hpp> 
#include <boost/process/operations.hpp> 
#include <boost/process/status.hpp> 
#include <boost/test/unit_test.hpp> 
#include <string> 
#include <vector> 
#include <cstdlib> 

namespace bfs = ::boost::filesystem; 
namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

static std::string get_argument(const std::string &word) 
{ 
    std::vector<std::string> args; 
    args.push_back("helpers"); 
    args.push_back("echo-quoted"); 
    args.push_back(word); 

    bp::context ctx; 
    ctx.stdout_behavior = bp::capture_stream(); 
    ctx.environment = bp::self::get_environment(); 

    bp::child c = bp::launch(get_helpers_path(), args, ctx); 
    bp::pistream &is = c.get_stdout(); 

    std::string result; 
    portable_getline(is, result); 

    const bp::status s = c.wait(); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_SUCCESS); 

    return result; 
} 

static void test_quoting() 
{ 
    BOOST_CHECK_EQUAL(get_argument("foo"), ">>>foo<<<"); 
    BOOST_CHECK_EQUAL(get_argument("foo "), ">>>foo <<<"); 
    BOOST_CHECK_EQUAL(get_argument(" foo"), ">>> foo<<<"); 
    BOOST_CHECK_EQUAL(get_argument("foo bar"), ">>>foo bar<<<"); 

    BOOST_CHECK_EQUAL(get_argument("foo\"bar"), ">>>foo\"bar<<<"); 
    BOOST_CHECK_EQUAL(get_argument("foo\"bar\""), ">>>foo\"bar\"<<<"); 
    BOOST_CHECK_EQUAL(get_argument("\"foo\"bar"), ">>>\"foo\"bar<<<"); 
    BOOST_CHECK_EQUAL(get_argument("\"foo bar\""), ">>>\"foo bar\"<<<"); 

    BOOST_CHECK_EQUAL(get_argument("*"), ">>>*<<<"); 
    BOOST_CHECK_EQUAL(get_argument("?*"), ">>>?*<<<"); 
    BOOST_CHECK_EQUAL(get_argument("[a-z]*"), ">>>[a-z]*<<<"); 
} 

#if defined(BOOST_POSIX_API) 
static void test_collection_to_posix_argv() 
{ 
    std::vector<std::string> args; 
    args.push_back("program"); 
    args.push_back("arg1"); 
    args.push_back("arg2"); 
    args.push_back("arg3"); 

    std::pair<std::size_t, char**> p = bpd::collection_to_posix_argv(args); 
    std::size_t argc = p.first; 
    char **argv = p.second; 

    BOOST_REQUIRE_EQUAL(argc, static_cast<std::size_t>(4)); 

    BOOST_REQUIRE(std::strcmp(argv[0], "program") == 0); 
    BOOST_REQUIRE(std::strcmp(argv[1], "arg1") == 0); 
    BOOST_REQUIRE(std::strcmp(argv[2], "arg2") == 0); 
    BOOST_REQUIRE(std::strcmp(argv[3], "arg3") == 0); 
    BOOST_REQUIRE(argv[4] == NULL); 

    delete[] argv[0]; 
    delete[] argv[1]; 
    delete[] argv[2]; 
    delete[] argv[3]; 
    delete[] argv; 
} 
#endif 

#if defined(BOOST_WINDOWS_API) 
static void test_collection_to_win32_cmdline() 
{ 
    std::vector<std::string> args; 
    args.push_back("program"); 
    args.push_back("arg1"); 
    args.push_back("arg2"); 
    args.push_back("arg3"); 

    boost::shared_array<char> cmdline = 
        bpd::collection_to_win32_cmdline(args); 
    BOOST_REQUIRE(std::strcmp(cmdline.get(), 
        "program arg1 arg2 arg3") == 0); 
} 
#endif 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    bfs::initial_path(); 

    but::test_suite* test = BOOST_TEST_SUITE("arguments test suite"); 

    test->add(BOOST_TEST_CASE(&test_quoting)); 

#if defined(BOOST_POSIX_API) 
    test->add(BOOST_TEST_CASE(&test_collection_to_posix_argv)); 
#elif defined(BOOST_WINDOWS_API) 
    test->add(BOOST_TEST_CASE(&test_collection_to_win32_cmdline)); 
#endif 

    return test; 
} 
