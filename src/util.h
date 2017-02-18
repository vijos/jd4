#ifndef JD4_UTIL_H
#define JD4_UTIL_H

#include "shim.h"

Path CreateTempPath(const Path &model, int num_attempts);

inline Path CreateTempPath(const Path &model) {
    return CreateTempPath(model, /*num_attempts=*/4);
}

#endif //JD4_UTIL_H
