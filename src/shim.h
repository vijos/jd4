#ifndef JD4_SHIM_H
#define JD4_SHIM_H

#include <stdlib.h>
#include <boost/asio.hpp>
#include <boost/filesystem.hpp>
#include <boost/log/trivial.hpp>
#include <boost/process.hpp>
#include <boost/utility/string_ref.hpp>
#include <string>
#include <unordered_map>
#include <utility>

extern "C" int pivot_root(const char *new_root, const char *put_old);

#define LOG(severity) BOOST_LOG_TRIVIAL(severity)

#define _STRINGIZE(x) _STRINGIZE2(x)
#define _STRINGIZE2(x) #x

#define CHECK(condition) \
    do { \
        if (!(condition)) { \
            LOG(fatal) << "check failed: " #condition \
                " on " __FILE__ ":" _STRINGIZE(__LINE__); \
            abort(); \
        } \
    } while (0)

#define CHECK_UNIX(ret) \
    do { \
        if (ret < 0) { \
            LOG(fatal) << "check failed: " #ret " with errno " << errno \
                       << " on " __FILE__ ":" _STRINGIZE(__LINE__); \
            abort(); \
        } \
    } while (0)

// Base.
template <typename Key, typename Value>
using HashMap = std::unordered_map<Key, Value>;

template <typename First, typename Second>
using Pair = std::pair<First, Second>;

using Path = boost::filesystem::path;
using String = std::string;
using StringView = boost::string_ref;

template <typename Element>
using Vector = std::vector<Element>;

// I/O
const auto INHERIT_STREAM = boost::process::inherit_stream();

using Child = boost::process::posix_child;
using ChildContext = boost::process::posix_context;
using EventLoop = boost::asio::io_service;

inline Child LaunchChild(const String &exe, const Vector<String> &args, const ChildContext &ctx) {
    return boost::process::posix_launch(exe, args, ctx);
};

using StreamBehavior = boost::process::stream_behavior;

#endif //JD4_SHIM_H
