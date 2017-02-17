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
#include <fstream> 
#include <cstdlib> 

namespace bp = ::boost::process; 

bp::children start_children() 
{ 
    bp::context ctxin; 
    ctxin.stdin_behavior = bp::capture_stream(); 

    bp::context ctxout; 
    ctxout.stdout_behavior = bp::inherit_stream(); 
    ctxout.stderr_behavior = bp::redirect_stream_to_stdout(); 

    std::string exec1 = bp::find_executable_in_path("cut"); 
    std::vector<std::string> args1; 
    args1.push_back("cut"); 
    args1.push_back("-d "); 
    args1.push_back("-f2-5"); 

    std::string exec2 = bp::find_executable_in_path("sed"); 
    std::vector<std::string> args2; 
    args2.push_back("sed"); 
    args2.push_back("s,^,line: >>>,"); 

    std::string exec3 = bp::find_executable_in_path("sed"); 
    std::vector<std::string> args3; 
    args3.push_back("sed"); 
    args3.push_back("s,$,<<<,"); 

    std::vector<bp::pipeline_entry> entries; 
    entries.push_back(bp::pipeline_entry(exec1, args1, ctxin)); 
    entries.push_back(bp::pipeline_entry(exec2, args2, ctxout)); 
    entries.push_back(bp::pipeline_entry(exec3, args3, ctxout)); 

    return bp::launch_pipeline(entries); 
} 

int main(int argc, char *argv[]) 
{ 
    try 
    { 
        if (argc < 2) 
        { 
            std::cerr << "Please specify a file name" << std::endl; 
            return EXIT_FAILURE; 
        } 

        std::ifstream file(argv[1]); 
        if (!file) 
        { 
            std::cerr << "Cannot open file" << std::endl; 
            return EXIT_FAILURE; 
        } 

        bp::children cs = start_children(); 

        bp::postream &os = cs.front().get_stdin(); 
        std::string line; 
        while (std::getline(file, line)) 
            os << line << std::endl; 
        os.close(); 

        bp::status s = bp::wait_children(cs); 

        return s.exited() ? s.exit_status() : EXIT_FAILURE; 
    } 
    catch (boost::filesystem::filesystem_error &ex) 
    { 
        std::cout << ex.what() << std::endl; 
        return EXIT_FAILURE; 
    } 
} 
