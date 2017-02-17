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

#include "process_base_test.hpp" 
#include <boost/process/process.hpp> 
#include <boost/test/unit_test.hpp> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

class launcher 
{ 
public: 
    bp::process operator()(bp::process::id_type id) 
    { 
        return bp::process(id); 
    } 
}; 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("process test suite"); 

    add_tests_process_base<bp::process, launcher>(test); 

    return test; 
} 
