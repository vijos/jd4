#ifndef JD4_COMPILER_H
#define JD4_COMPILER_H

#include "shim.h"

class Executable {
public:
    virtual ~Executable() = default;
    virtual void Execute() const = 0;

    Executable() = default;
    Executable(const Executable &) = delete;
    Executable &operator=(const Executable &) = delete;
};

class Compiler {
public:
    virtual ~Compiler() = default;
    virtual Box<Executable> Compile(StringView code) const = 0;

    Compiler() = default;
    Compiler(const Compiler &) = delete;
    Compiler &operator=(const Compiler &) = delete;
};

Box<Compiler> CreateSandboxedCompiler(const Path &compiler_file,
                                      const Vector<String> &compiler_args,
                                      const Path &code_file,
                                      const Path &execute_file,
                                      const Vector<String> &execute_args);

Box<Compiler> CreateSandboxedInterpreter(const Path &code_file,
                                         const Path &execute_file,
                                         const Vector<String> &execute_args);

#endif //JD4_COMPILER_H
