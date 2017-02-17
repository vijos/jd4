#ifndef JD4_SHIM_H
#define JD4_SHIM_H

#include <stdlib.h>
#include <boost/filesystem.hpp>
#include <boost/log/trivial.hpp>
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

template <typename Key, typename Value>
using HashMap = std::unordered_map<Key, Value>;

template <typename First, typename Second>
using Pair = std::pair<First, Second>;

using Path = boost::filesystem::path;

using String = std::string;
using StringView = boost::string_ref;

template <typename Element>
using Vector = std::vector<Element>;

#endif //JD4_SHIM_H
