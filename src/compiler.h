#ifndef JD4_COMPILER_H
#define JD4_COMPILER_H

#include "shim.h"

class Package {
public:
    virtual ~Package() = default;
    virtual void Install(const Path &install_dir) const = 0;
    virtual Process Execute(const Path &install_dir) const = 0;

    Package() = default;
    Package(const Package &) = delete;
    Package &operator=(const Package &) = delete;
};

class Compiler {
public:
    virtual ~Compiler() = default;
    virtual Box<Package> Compile(StringView code) const = 0;

    Compiler() = default;
    Compiler(const Compiler &) = delete;
    Compiler &operator=(const Compiler &) = delete;
};

Box<Compiler> CreateCompiler(const Path &compiler_file,
                             const Vector<String> &compiler_args,
                             const Path &code_file,
                             const Path &execute_file,
                             const Vector<String> &execute_args);

Box<Compiler> CreateInterpreter(const Path &code_file,
                                const Path &execute_file,
                                const Vector<String> &execute_args);

#endif //JD4_COMPILER_H
