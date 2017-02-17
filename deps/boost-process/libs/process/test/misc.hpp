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
#  if defined(__CYGWIN__) 
#    undef BOOST_POSIX_API 
#    define BOOST_CYGWIN_PATH 
#  endif 
#endif 

#include <boost/filesystem/operations.hpp> 
#include <boost/filesystem/path.hpp> 
#include <boost/test/unit_test.hpp> 
#include <string> 
#include <istream> 

enum bp_api_type { 
    posix_api, 
    win32_api 
} 
#if defined(BOOST_POSIX_API) 
bp_api_type = posix_api; 
#elif defined(BOOST_WINDOWS_API) 
bp_api_type = win32_api; 
#else 
#  error "Unsupported platform." 
#endif 

inline std::string get_helpers_path() 
{ 
    boost::filesystem::path hp = boost::filesystem::initial_path(); 

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32) 
    hp /= "../../../bin.v2/libs/process/test/msvc-9.0/debug/link-static/helpers.exe"; 
#elif defined(sun) || defined(__sun) 
#  if defined(__GNUG__) 
    hp /= "../../../bin.v2/libs/process/test/gcc-3.4.6/debug/link-static/helpers"; 
#  elif defined(__SUNPRO_CC) 
    hp /= "../../../bin.v2/libs/process/test/sun/debug/link-static/stdlib-sun-stlport/helpers"; 
#  endif 
#elif defined(__CYGWIN__) 
    hp /= "../../../bin.v2/libs/process/test/gcc-3.4.4/debug/link-static/helpers.exe"; 
#elif defined(__APPLE__) 
    hp /= "../../../bin.v2/libs/process/test/darwin/debug/link-static/helpers"; 
#endif 

    BOOST_REQUIRE_MESSAGE(boost::filesystem::exists(hp), hp.string() + " not found"); 

    return hp.string(); 
} 

inline std::istream &portable_getline(std::istream &is, std::string &str) 
{ 
    std::getline(is, str); 
    std::string::size_type pos = str.rfind('\r'); 
    if (pos != std::string::npos) 
        str.erase(pos); 
    return is; 
} 
