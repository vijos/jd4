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

#include "child_base_test.hpp" 
#include <boost/process/child.hpp> 
#include <boost/test/unit_test.hpp> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

class launcher 
{ 
public: 
    bp::child operator()(bp::child::id_type id) 
    { 
        bpd::file_handle fhinvalid; 
        return bp::child(id, fhinvalid, fhinvalid, fhinvalid); 
    } 

    bp::child operator()(bp::child::id_type id, bpd::file_handle fhstdin, 
        bpd::file_handle fhstdout, bpd::file_handle fhstderr) 
    { 
        return bp::child(id, fhstdin, fhstdout, fhstderr); 
    } 
}; 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("child test suite"); 

    add_tests_child_base<bp::child, launcher>(test); 

    return test; 
} 
