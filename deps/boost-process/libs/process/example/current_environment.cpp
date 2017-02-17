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
#include <string> 
#include <vector> 
#include <iostream> 

namespace bp = ::boost::process; 

bp::child start_child(bp::context ctx) 
{ 
#if defined(BOOST_POSIX_API) 
    return bp::launch(std::string("env"), std::vector<std::string>(), ctx); 
#elif defined(BOOST_WINDOWS_API) 
    return bp::launch_shell("set", ctx); 
#else 
#  error "Unsupported platform." 
#endif 
} 

int main() 
{ 
    bp::context ctx; 
    ctx.stdout_behavior = bp::capture_stream(); 
    ctx.environment = bp::self::get_environment(); 

    bp::child c = start_child(ctx); 

    bp::pistream &is = c.get_stdout(); 
    std::string line; 
    while (std::getline(is, line)) 
        std::cout << line << std::endl; 
} 
