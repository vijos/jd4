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
#  include "child_base_test.hpp" 
#  include <boost/process/posix_child.hpp> 
#  include <boost/process/stream_behavior.hpp> 
#  include <boost/process/detail/posix_ops.hpp> 
#  include <boost/process/detail/file_handle.hpp> 
#  include <unistd.h> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
#endif 

#include <boost/test/unit_test.hpp> 

namespace but = ::boost::unit_test; 

#if defined(BOOST_POSIX_API) 
namespace boost { 
namespace process { 

class posix_launcher 
{ 
public: 
    bp::posix_child operator()(bp::posix_child::id_type id) 
    { 
        bpd::info_map infoin, infoout; 

        return bp::posix_child(id, infoin, infoout); 
    } 

    bp::posix_child operator()(bp::posix_child::id_type id, bpd::file_handle fhstdin, 
               bpd::file_handle fhstdout, bpd::file_handle fhstderr) 
    { 
        bpd::info_map infoin, infoout; 
        bp::stream_behavior withpipe = bp::capture_stream(); 

        if (fhstdin.valid()) 
        { 
            bpd::stream_info si(withpipe, false); 
            si.pipe_->rend().close(); 
            si.pipe_->wend() = fhstdin; 
            infoin.insert(bpd::info_map::value_type(STDIN_FILENO, si)); 
        } 

        if (fhstdout.valid()) 
        { 
            bpd::stream_info si(withpipe, true); 
            si.pipe_->wend().close(); 
            si.pipe_->rend() = fhstdout; 
            infoout.insert(bpd::info_map::value_type(STDOUT_FILENO, si)); 
        } 

        if (fhstderr.valid()) 
        { 
            bpd::stream_info si(withpipe, true); 
            si.pipe_->wend().close(); 
            si.pipe_->rend() = fhstderr; 
            infoout.insert(bpd::info_map::value_type(STDERR_FILENO, si)); 
        } 

        return bp::posix_child(id, infoin, infoout); 
    } 
}; 

} 
} 
#endif 

#if !defined(BOOST_POSIX_API) 
static void test_dummy() 
{ 
} 
#endif 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("posix_child test suite"); 

#if defined(BOOST_POSIX_API) 
    add_tests_child_base<bp::posix_child, bp::posix_launcher>(test); 
#else 
    test->add(BOOST_TEST_CASE(&test_dummy)); 
#endif 

    return test; 
} 
