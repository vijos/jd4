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
#  include <stdlib.h> 
#elif defined(BOOST_WINDOWS_API) 
#  include <windows.h> 
#else 
#  error "Unsupported platform." 
#endif 

#include <boost/filesystem/operations.hpp> 
#include <boost/process/detail/systembuf.hpp> 
#include <iostream> 
#include <string> 
#include <cstdlib> 

namespace bfs = ::boost::filesystem; 
namespace bpd = ::boost::process::detail; 

static int h_echo_quoted(int, char*[]); 
static int h_echo_stdout(int, char*[]); 
static int h_echo_stderr(int, char*[]); 
static int h_echo_stdout_stderr(int, char*[]); 
static int h_exit_failure(int, char*[]); 
static int h_exit_success(int, char*[]); 
static int h_is_closed_stdin(int, char*[]); 
static int h_is_closed_stdout(int, char*[]); 
static int h_is_closed_stderr(int, char*[]); 
static int h_loop(int, char*[]); 
static int h_prefix(int, char*[]); 
static int h_pwd(int, char*[]); 
static int h_query_env(int, char*[]); 
static int h_stdin_to_stdout(int, char*[]); 

#if defined(BOOST_POSIX_API) 
static int h_posix_echo_one(int, char*[]); 
static int h_posix_echo_two(int, char*[]); 
#elif defined(BOOST_WINDOWS_API) 
static int h_win32_print_startupinfo(int, char*[]); 
#endif 

struct helper 
{ 
    const char *name; 
    int (*entry)(int, char*[]); 
    int min_argc; 
    const char *syntax; 
} helpers[] = { 
    { "echo-quoted", h_echo_quoted, 2, "word" }, 
    { "echo-stdout", h_echo_stdout, 2, "message" }, 
    { "echo-stderr", h_echo_stderr, 2, "message" }, 
    { "echo-stdout-stderr", h_echo_stdout_stderr, 2, "message" }, 
    { "exit-failure", h_exit_failure, 1, "" }, 
    { "exit-success", h_exit_success, 1, "" }, 
    { "is-closed-stdin", h_is_closed_stdin, 1, "" }, 
    { "is-closed-stdout", h_is_closed_stdout, 1, "" }, 
    { "is-closed-stderr", h_is_closed_stderr, 1, "" }, 
    { "loop", h_loop, 1, "" }, 
    { "prefix", h_prefix, 2, "string" }, 
    { "pwd", h_pwd, 1, "" }, 
    { "query-env", h_query_env, 2, "variable" }, 
    { "stdin-to-stdout", h_stdin_to_stdout, 1, "" }, 

#if defined(BOOST_POSIX_API) 
    { "posix-echo-one", h_posix_echo_one, 3, "desc message" }, 
    { "posix-echo-two", h_posix_echo_two, 4, "desc1 desc2 message" }, 
#elif defined(BOOST_WINDOWS_API) 
    { "win32-print-startupinfo", h_win32_print_startupinfo, 1, "" }, 
#endif 

    { NULL, NULL } 
}; 

static int h_echo_quoted(int argc, char *argv[]) 
{ 
    std::cout << ">>>" << argv[1] << "<<<" << std::endl; 
    return EXIT_SUCCESS; 
} 

static int h_echo_stdout(int argc, char *argv[]) 
{ 
    std::cout << argv[1] << std::endl; 
    return EXIT_SUCCESS; 
} 

static int h_echo_stderr(int argc, char *argv[]) 
{ 
    std::cerr << argv[1] << std::endl; 
    return EXIT_SUCCESS; 
} 

static int h_echo_stdout_stderr(int argc, char *argv[]) 
{ 
    std::cout << "stdout " << argv[1] << std::endl; 
    std::cout.flush(); 
    std::cerr << "stderr " << argv[1] << std::endl; 
    std::cerr.flush(); 
    return EXIT_SUCCESS; 
} 

static int h_exit_failure(int argc, char *argv[]) 
{ 
    return EXIT_FAILURE; 
} 

static int h_exit_success(int argc, char *argv[]) 
{ 
    return EXIT_SUCCESS; 
} 

static int h_is_closed_stdin(int argc, char *argv[]) 
{ 
    std::string word; 
    std::cin >> word; 
    return std::cin.eof() ? EXIT_SUCCESS : EXIT_FAILURE; 
} 

static int h_is_closed_stdout(int argc, char *argv[]) 
{ 
    std::cout << "foo" << std::endl; 
    return std::cout.bad() ? EXIT_SUCCESS : EXIT_FAILURE; 
} 

static int h_is_closed_stderr(int argc, char *argv[]) 
{ 
    std::cerr << "foo" << std::endl; 
    return std::cerr.bad() ? EXIT_SUCCESS : EXIT_FAILURE; 
} 

static int h_loop(int argc, char *argv[]) 
{ 
    for (;;) 
        ; 

    return EXIT_SUCCESS; 
} 

static int h_prefix(int argc, char *argv[]) 
{ 
    std::string line; 
    while (std::getline(std::cin, line)) 
        std::cout << argv[1] << line << std::endl; 

    return EXIT_SUCCESS; 
} 

static int h_pwd(int argc, char *argv[]) 
{ 
    std::cout << bfs::current_path().string() << std::endl; 
    return EXIT_SUCCESS; 
} 

static int h_query_env(int argc, char *argv[]) 
{ 
#if defined(BOOST_WINDOWS_API) 
    char buf[1024]; 
    DWORD res = ::GetEnvironmentVariableA(argv[1], buf, sizeof(buf)); 
    if (res == 0) 
        std::cout << "undefined" << std::endl; 
    else 
    { 
        std::cout << "defined" << std::endl; 
        std::cout << "'" << buf << "'" << std::endl; 
    } 
#else 
    const char *value = ::getenv(argv[1]); 
    if (value == NULL) 
        std::cout << "undefined" << std::endl; 
    else 
    { 
        std::cout << "defined" << std::endl; 
        std::cout << "'" << value << "'" << std::endl; 
    } 
#endif 

    return EXIT_SUCCESS; 
} 

static int h_stdin_to_stdout(int argc, char *argv[]) 
{ 
    char ch; 
    while (std::cin >> ch) 
        std::cout << ch; 

    return EXIT_SUCCESS; 
} 

#if defined(BOOST_POSIX_API) 
static int h_posix_echo_one(int argc, char *argv[]) 
{ 
    int desc = ::atoi(argv[1]); 

    bpd::systembuf buf(desc); 
    std::ostream os(&buf); 
    os << argv[2] << std::endl; 

    return EXIT_SUCCESS; 
} 

static int h_posix_echo_two(int argc, char *argv[]) 
{ 
    int desc1 = ::atoi(argv[1]); 
    int desc2 = ::atoi(argv[2]); 

    bpd::systembuf buf1(desc1); 
    std::ostream os1(&buf1); 
    os1 << argv[1] << " " << argv[3] << std::endl; 
    os1.flush(); 

    bpd::systembuf buf2(desc2); 
    std::ostream os2(&buf2); 
    os2 << argv[2] << " " << argv[3] << std::endl; 
    os2.flush(); 

    return EXIT_SUCCESS; 
} 
#endif 

#if defined(BOOST_WINDOWS_API) 
static int h_win32_print_startupinfo(int argc, char *argv[]) 
{ 
    STARTUPINFO si; 
    ::GetStartupInfo(&si); 
    std::cout << "dwFlags = " << si.dwFlags << std::endl; 
    std::cout << "dwX = " << si.dwX << std::endl; 
    std::cout << "dwY = " << si.dwY << std::endl; 
    std::cout << "dwXSize = " << si.dwXSize << std::endl; 
    std::cout << "dwYSize = " << si.dwYSize << std::endl; 

    return EXIT_SUCCESS; 
} 
#endif 

int main(int argc, char *argv[]) 
{ 
    if (argc < 2) 
    { 
        std::cerr << "helpers: Missing command" << std::endl; 
        return 128; 
    } 

    std::string command(argv[1]); 
    --argc; 
    ++argv; 

    struct helper *h = helpers; 
    while (h->name != NULL) 
    { 
        if (command == h->name) 
        { 
            int res; 
            if (argc < h->min_argc) 
            { 
                std::cerr << "helpers: Command syntax: `" << command << " " 
                    << h->syntax << "'" << std::endl; 
                res = 128; 
            } 
            else 
                res = (*h->entry)(argc, argv); 
            return res; 
        } 
        ++h; 
    } 

    std::cerr << "helpers: Invalid command `" << command << "'" 
        << std::endl; 
    return 128; 
} 
