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

#include <boost/process/detail/systembuf.hpp> 

namespace bpd = ::boost::process::detail; 

bpd::systembuf *test_it() 
{ 
    bpd::systembuf::handle_type h = static_cast<bpd::systembuf::handle_type>(0); 
    return new bpd::systembuf(h); 
} 
