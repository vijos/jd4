#include "util.h"

Path CreateTempPath(const Path &model, int num_attempts) {
    Path path;
    do {
        CHECK(num_attempts--);
        path = TempPath() / RandomPath(model);
    } while (!MakeDir(path));
    return path;
}
