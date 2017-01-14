#ifndef JD4_SHIM_H
#define JD4_SHIM_H

#include <boost/log/trivial.hpp>
#include <boost/utility/string_ref.hpp>

typedef boost::string_ref StringView;

#define LOG(severity) BOOST_LOG_TRIVIAL(severity)

#endif //JD4_SHIM_H
