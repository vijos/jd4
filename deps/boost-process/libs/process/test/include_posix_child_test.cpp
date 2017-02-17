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
#  include <boost/process/posix_child.hpp> 

namespace bp = ::boost::process; 
namespace bpd = ::boost::process::detail; 

bp::posix_child *test_it() 
{ 
    bp::posix_child::id_type id = static_cast<bp::posix_child::id_type>(0); 
    bpd::info_map info; 
    return new bp::posix_child(id, info, info); 
} 

#endif 
