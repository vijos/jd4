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

#include <boost/process.hpp> 
#if defined(BOOST_POSIX_API) 
#include <string> 
#include <vector> 
#include <iostream> 
#include <cstdlib> 

namespace bp = ::boost::process; 

bp::child start_child(std::string exec) 
{ 
    std::vector<std::string> args; 

    bp::context ctx; 
    ctx.stdin_behavior = bp::inherit_stream(); 
    ctx.stdout_behavior = bp::inherit_stream(); 
    ctx.stderr_behavior = bp::inherit_stream(); 

    return bp::launch(exec, args, ctx); 
} 

int main(int argc, char *argv[]) 
{ 
    if (argc < 2) 
    { 
        std::cerr << "Please provide a program name" << std::endl; 
        return EXIT_FAILURE; 
    } 

    bp::child c = start_child(argv[1]); 

    bp::posix_status s = c.wait(); 
    if (s.exited()) 
        std::cout << "Program returned exit code " << s.exit_status() << std::endl; 
    else if (s.signaled()) 
    { 
        std::cout << "Program received signal " << s.term_signal() << std::endl; 
        if (s.dumped_core()) 
            std::cout << "Program also dumped core" << std::endl; 
    } 
    else if (s.stopped()) 
        std::cout << "Program stopped by signal " << s.stop_signal() << std::endl; 
    else 
        std::cout << "Unknown termination reason" << std::endl; 

    return s.exited() ? s.exit_status() : EXIT_FAILURE; 
} 
#endif 
