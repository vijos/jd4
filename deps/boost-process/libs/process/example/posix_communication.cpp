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
#include <unistd.h> 

namespace bp = ::boost::process; 

bp::posix_child start_child() 
{ 
    std::string exec = bp::find_executable_in_path("dbus-daemon"); 

    std::vector<std::string> args; 
    args.push_back("dbus-daemon"); 
    args.push_back("--fork"); 
    args.push_back("--session"); 
    args.push_back("--print-address=3"); 
    args.push_back("--print-pid=4"); 

    bp::posix_context ctx; 
    ctx.output_behavior.insert(bp::behavior_map::value_type(STDOUT_FILENO, bp::inherit_stream())); 
    ctx.output_behavior.insert(bp::behavior_map::value_type(STDERR_FILENO, bp::inherit_stream())); 
    ctx.output_behavior.insert(bp::behavior_map::value_type(3, bp::capture_stream())); 
    ctx.output_behavior.insert(bp::behavior_map::value_type(4, bp::capture_stream())); 

    return bp::posix_launch(exec, args, ctx); 
} 

int main() 
{ 
    try 
    { 
        bp::posix_child c = start_child(); 

        std::string address; 
        pid_t pid; 
        c.get_output(3) >> address; 
        c.get_output(4) >> pid; 

        bp::status s = c.wait(); 
        if (s.exited()) 
        { 
            if (s.exit_status() == EXIT_SUCCESS) 
            { 
                std::cout << "D-BUS daemon's address is: " << address << std::endl; 
                std::cout << "D-BUS daemon's PID is: " << pid << std::endl; 
            } 
            else 
                std::cout << "D-BUS daemon returned error condition: " << s.exit_status() << std::endl; 
        } 
        else 
            std::cout << "D-BUS daemon terminated abnormally" << std::endl; 

        return s.exited() ? s.exit_status() : EXIT_FAILURE; 
    } 
    catch (boost::filesystem::filesystem_error &ex) 
    { 
        std::cout << ex.what() << std::endl; 
        return EXIT_FAILURE; 
    } 
} 
#endif 
