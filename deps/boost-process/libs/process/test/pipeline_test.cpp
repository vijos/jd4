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

#include "launch_base_test.hpp" 
#include <boost/process/child.hpp> 
#include <boost/process/self.hpp> 
#include <boost/process/pistream.hpp> 
#include <boost/process/postream.hpp> 
#include <boost/process/context.hpp> 
#include <boost/process/stream_behavior.hpp> 
#include <boost/process/operations.hpp> 
#include <boost/filesystem/operations.hpp> 
#include <boost/test/unit_test.hpp> 
#include <vector> 
#include <string> 
#include <cstdlib> 

namespace bfs = ::boost::filesystem; 
namespace bp = ::boost::process; 
namespace but = ::boost::unit_test; 

class children_to_child 
{ 
public: 
    children_to_child(bp::children cs) 
      : cs_(cs)
    {
    }

    bp::postream &get_stdin() const 
    { 
        return cs_.front().get_stdin(); 
    } 

    bp::pistream &get_stdout() const 
    { 
        return cs_.back().get_stdout(); 
    } 

    bp::pistream &get_stderr() const 
    { 
        return cs_.back().get_stderr(); 
    } 

    const bp::status wait() 
    { 
        return wait_children(cs_); 
    } 

private: 
    bp::children cs_; 
}; 

class launcher 
{ 
public: 
    children_to_child operator()(const std::vector<std::string> args, 
               bp::context ctx, 
               bp::stream_behavior bstdin = bp::close_stream(), 
               bp::stream_behavior bstdout = bp::close_stream(), 
               bp::stream_behavior bstderr = bp::close_stream(), 
               bool usein = false) 
        const 
    { 
        std::vector<std::string> dummy; 
        dummy.push_back("helpers"); 
        dummy.push_back("stdin-to-stdout"); 

        if (ctx.environment.empty()) 
            ctx.environment = bp::self::get_environment(); 

        bp::context ctx1(ctx); 
        ctx1.stdin_behavior = bstdin; 

        bp::context ctx2(ctx); 
        ctx2.stdout_behavior = bstdout; 
        ctx2.stderr_behavior = bstderr; 

        std::vector<bp::pipeline_entry> entries; 

        if (usein) 
        { 
            entries.push_back(bp::pipeline_entry(get_helpers_path(), 
                                                 args, ctx1)); 
            entries.push_back(bp::pipeline_entry(get_helpers_path(), 
                                                 dummy, ctx2)); 
        } 
        else 
        { 
            entries.push_back(bp::pipeline_entry(get_helpers_path(), 
                                                 dummy, ctx1)); 
            entries.push_back(bp::pipeline_entry(get_helpers_path(), 
                                                 args, ctx2)); 
        } 
        return launch_pipeline(entries); 
    } 
}; 

static void test_exit(const std::string &middle, int value) 
{ 
    std::vector<std::string> args1; 
    args1.push_back("helpers"); 
    args1.push_back("exit-success"); 

    std::vector<std::string> args2; 
    args2.push_back("helpers"); 
    args2.push_back(middle); 

    std::vector<std::string> args3; 
    args3.push_back("helpers"); 
    args3.push_back("exit-success"); 

    bp::context ctx; 
    ctx.environment = bp::self::get_environment(); 

    std::vector<bp::pipeline_entry> entries; 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args1, ctx)); 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args2, ctx)); 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args3, ctx)); 
    bp::children cs = bp::launch_pipeline(entries); 

    BOOST_REQUIRE(cs.size() == 3); 

    const bp::status s = bp::wait_children(cs); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), value); 
} 

static void test_exit_failure() 
{ 
    test_exit("exit-failure", EXIT_FAILURE); 
} 

static void test_exit_success() 
{ 
    test_exit("exit-success", EXIT_SUCCESS); 
} 

static void test_simple() 
{ 
    std::vector<std::string> args1; 
    args1.push_back("helpers"); 
    args1.push_back("prefix"); 
    args1.push_back("proc1-"); 

    std::vector<std::string> args2; 
    args2.push_back("helpers"); 
    args2.push_back("prefix"); 
    args2.push_back("proc2-"); 

    bp::context ctxin; 
    ctxin.stdin_behavior = bp::capture_stream(); 
    ctxin.environment = bp::self::get_environment(); 

    bp::context ctxout; 
    ctxout.stdout_behavior = bp::capture_stream(); 
    ctxout.environment = bp::self::get_environment(); 

    std::vector<bp::pipeline_entry> entries; 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args1, ctxin)); 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args2, ctxout)); 
    bp::children cs = bp::launch_pipeline(entries); 

    BOOST_REQUIRE(cs.size() == 2); 

    cs[0].get_stdin() << "message" << std::endl; 
    cs[0].get_stdin().close(); 

    std::string word; 
    cs[1].get_stdout() >> word; 
    BOOST_CHECK_EQUAL(word, "proc2-proc1-message"); 

    const bp::status s = bp::wait_children(cs); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_SUCCESS); 
} 

static void test_merge_first() 
{ 
    std::vector<std::string> args1; 
    args1.push_back("helpers"); 
    args1.push_back("echo-stdout-stderr"); 
    args1.push_back("message"); 

    std::vector<std::string> args2; 
    args2.push_back("helpers"); 
    args2.push_back("prefix"); 
    args2.push_back("second:"); 

    bp::context ctxin; 
    ctxin.stderr_behavior = bp::redirect_stream_to_stdout(); 
    ctxin.environment = bp::self::get_environment(); 

    bp::context ctxout; 
    ctxout.stdout_behavior = bp::capture_stream(); 
    ctxout.environment = bp::self::get_environment(); 

    std::vector<bp::pipeline_entry> entries; 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args1, ctxin)); 
    entries.push_back(bp::pipeline_entry(get_helpers_path(), args2, ctxout)); 
    bp::children cs = bp::launch_pipeline(entries); 

    BOOST_REQUIRE(cs.size() == 2); 

    std::string line; 
    portable_getline(cs[1].get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "second:stdout message"); 
    portable_getline(cs[1].get_stdout(), line); 
    BOOST_CHECK_EQUAL(line, "second:stderr message"); 

    const bp::status s = bp::wait_children(cs); 
    BOOST_REQUIRE(s.exited()); 
    BOOST_CHECK_EQUAL(s.exit_status(), EXIT_SUCCESS); 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    bfs::initial_path(); 

    but::test_suite *test = BOOST_TEST_SUITE("pipeline test suite"); 

    add_tests_launch_base<launcher, bp::context, children_to_child>(test); 

    test->add(BOOST_TEST_CASE(&test_exit_success), 0, 10); 
    test->add(BOOST_TEST_CASE(&test_exit_failure), 0, 10); 
    test->add(BOOST_TEST_CASE(&test_simple), 0, 10); 
    test->add(BOOST_TEST_CASE(&test_merge_first), 0, 10); 

    return test; 
} 
