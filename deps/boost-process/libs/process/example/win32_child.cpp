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
#if defined(BOOST_WINDOWS_API) 
#include <string> 
#include <vector> 
#include <iostream> 
#include <windows.h> 

namespace bp = ::boost::process; 

bp::win32_child start_child() 
{ 
    std::string exec = bp::find_executable_in_path("notepad"); 

    std::vector<std::string> args; 
    args.push_back(bp::executable_to_progname(exec)); 

    bp::win32_context ctx; 
    ctx.environment = bp::self::get_environment(); 

    return bp::win32_launch(exec, args, ctx); 
} 

int main() 
{ 
    try 
    { 
        bp::win32_child c = start_child(); 

        std::cout << "Process handle            : 0x" 
            << c.get_handle() << std::endl; 
        std::cout << "Process identifier        : " 
            << c.get_id() << std::endl; 
        std::cout << "Primary thread handle     : 0x" 
            << c.get_primary_thread_handle() << std::endl; 
        std::cout << "Primary thread identifier : " 
            << c.get_primary_thread_id() << std::endl; 
    } 
    catch (boost::filesystem::filesystem_error &ex) 
    { 
        std::cout << ex.what() << std::endl; 
    } 
} 
#endif 
