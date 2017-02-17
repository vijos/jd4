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

#if defined(BOOST_WINDOWS_API) 
#  include <boost/process/win32_context.hpp> 

namespace bp = ::boost::process; 

bp::win32_context *test_it() 
{ 
    return new bp::win32_context(); 
} 

#endif 
