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

namespace bp = ::boost::process; 

int main() 
{ 
    std::string exec = "bjam"; 

    std::vector<std::string> args; 
    args.push_back("bjam"); 
    args.push_back("--version"); 

    bp::context ctx; 
    ctx.stdout_behavior = bp::silence_stream(); 

    bp::child c = bp::launch(exec, args, ctx); 
} 
