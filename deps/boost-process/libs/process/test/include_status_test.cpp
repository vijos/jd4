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

#include <boost/process/status.hpp> 

namespace bp = ::boost::process; 

namespace boost { 
namespace process { 

class child 
{ 
public: 
    static bp::status *test_it() 
    { 
        return new bp::status(0); 
    } 
}; 

} 
} 

bp::status *test_it() 
{ 
    return bp::child::test_it(); 
} 
