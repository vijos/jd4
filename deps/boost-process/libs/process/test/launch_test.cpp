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
#include <boost/process/context.hpp> 
#include <boost/process/stream_behavior.hpp> 
#include <boost/process/operations.hpp> 
#include <boost/filesystem/operations.hpp> 
#include <boost/test/unit_test.hpp> 
#include <vector> 
#include <string> 

namespace bfs = ::boost::filesystem; 
namespace bp = ::boost::process; 
namespace but = ::boost::unit_test; 

class launcher 
{ 
public: 
    bp::child operator()(const std::vector<std::string> args, 
               bp::context ctx, 
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

        return bp::launch(get_helpers_path(), args, ctx); 
    } 
}; 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    bfs::initial_path(); 

    but::test_suite *test = BOOST_TEST_SUITE("launch test suite"); 

    add_tests_launch_base<launcher, bp::context, bp::child>(test); 

    return test; 
} 
