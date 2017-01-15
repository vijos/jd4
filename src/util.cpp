#include "util.h"

#include <fstream>

bool WriteFile(const char *path, StringView data) {
    std::ofstream file(path);
    file << data;
    file.close();
    return file.good();
}
