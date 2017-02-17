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
#  include <boost/process/win32_child.hpp> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 

bp::win32_child *test_it() 
{ 
    PROCESS_INFORMATION pi; 
    bpd::file_handle fh; 
    return new bp::win32_child(pi, fh, fh, fh); 
} 

#endif 
