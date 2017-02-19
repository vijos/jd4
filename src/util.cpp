#include "util.h"

void WriteFile(const Path &file, StringView content) {
    OFStream sink(file, Ios::binary);
    sink.write(content.data(), content.size());
}

Path CreateTempPath(const Path &model, int num_attempts) {
    Path path;
    do {
        CHECK(num_attempts--);
        path = TempPath() / RandomPath(model);
    } while (!MakeDir(path));
    return path;
}

void CopyFiles(const Path &from_dir, const Path &to_dir) {
    for (DirIterator iter(from_dir); iter != DirIterator(); ++iter) {
        Path path = iter->path().filename();
        switch (iter->status().type()) {
        case FileType::regular_file:
            Copy(from_dir / path, to_dir / path, CopyOption::overwrite_if_exists);
            break;
        case FileType::directory_file:
            CopyFiles(from_dir / path, to_dir / path);
            break;
        default:
            LOG(warning) << "File " << iter->path()
                         << " has special type " << iter->status().type();
        }
    }
}
