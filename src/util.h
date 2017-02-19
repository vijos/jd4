#ifndef JD4_UTIL_H
#define JD4_UTIL_H

#include "shim.h"

void WriteFile(const Path &file, StringView content);

Path CreateTempPath(const Path &model, int num_attempts);

inline Path CreateTempPath(const Path &model) {
    return CreateTempPath(model, /*num_attempts=*/4);
}

void CopyFiles(const Path &from_dir, const Path &to_dir);

#endif //JD4_UTIL_H
