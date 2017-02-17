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

#include <boost/process/process.hpp> 

namespace bp = ::boost::process; 

bp::process *test_it() 
{ 
    bp::process::id_type id = static_cast<bp::process::id_type>(0); 
    return new bp::process(id); 
} 
