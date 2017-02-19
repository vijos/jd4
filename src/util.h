#ifndef JD4_UTIL_H
#define JD4_UTIL_H

#include "shim.h"

void WriteFile(const Path &file, StringView content);

Path CreateTempPath(const Path &model, int num_attempts);

inline Path CreateTempPath(const Path &model) {
    return CreateTempPath(model, /*num_attempts=*/4);
}

void CopyFiles(const Path &from_dir, const Path &to_dir);

void UnshareAll();

void MountTmpfs(const Path &dir);

void MakeBindMount(const Path &from, const Path &to, bool read_only);

void PivotRoot(const Path &new_root, const Path &old_root);

void MakeProcMount(const Path &to);

void RemoveMount(const Path &dir);

void Exec(const Path &path, const Vector<String> &args, const Vector<String> &envs);

#endif //JD4_UTIL_H
