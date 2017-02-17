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

    STARTUPINFOA si; 
    ::ZeroMemory(&si, sizeof(si)); 
    si.cb = sizeof(si); 
    si.dwFlags |= STARTF_USEPOSITION | STARTF_USESIZE; 
    si.dwX = 0; 
    si.dwY = 0; 
    si.dwXSize = 640; 
    si.dwYSize = 480; 

    bp::win32_context ctx; 
    ctx.startupinfo = &si; 
    ctx.environment = bp::self::get_environment(); 

    return bp::win32_launch(exec, args, ctx); 
} 

int main() 
{ 
    try 
    { 
        bp::win32_child c = start_child(); 
    } 
    catch (boost::filesystem::filesystem_error &ex) 
    { 
        std::cout << ex.what() << std::endl; 
    } 
} 
#endif 
