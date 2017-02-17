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

#include <boost/process/postream.hpp> 
#include <boost/process/detail/pipe.hpp> 
#include <boost/process/detail/systembuf.hpp> 
#include <boost/test/unit_test.hpp> 
#include <istream> 
#include <string> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 
namespace but = ::boost::unit_test; 

static void test_it() 
{ 
    bpd::pipe p; 
    bpd::systembuf rbuf(p.rend().get()); 
    std::istream rend(&rbuf); 
    bp::postream wend(p.wend()); 

    // This assumes that the pipe's buffer is big enough to accept 
    // the data written without blocking! 
    wend << "1Test 1message" << std::endl; 
    std::string tmp; 
    rend >> tmp; 
    BOOST_CHECK_EQUAL(tmp, "1Test"); 
    rend >> tmp; 
    BOOST_CHECK_EQUAL(tmp, "1message"); 
} 

but::test_suite *init_unit_test_suite(int argc, char *argv[]) 
{ 
    but::test_suite *test = BOOST_TEST_SUITE("postream test suite"); 

    test->add(BOOST_TEST_CASE(&test_it)); 

    return test; 
} 
