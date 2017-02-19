#include "compiler.h"

#include "process.h"

namespace {

void PrepareSandboxDir(const Path &dir) {
    MountTmpfs(dir);
    MakeBindMount("/bin", dir / "bin", true);
    MakeBindMount("/etc", dir / "etc", true);
    MakeBindMount("/lib", dir / "lib", true);
    MakeBindMount("/lib64", dir / "lib64", true);
    MakeBindMount("/usr", dir / "usr", true);
}

} //namespace

class SandboxedExecutable : public Executable {
public:
    explicit SandboxedExecutable(const Path &dir, const Path &file, const Vector<String> &args)
        : dir(dir), file(file), args(args)
    {}

    ~SandboxedExecutable() override {
        RemoveAll(dir);
    }

    void Execute() const override {
        Path sandbox_dir = CreateTempPath("jd4.sandbox.%%%%%%%%%%%%%%%%");
        WaitForExit(Fork([this, &sandbox_dir] {
            UnshareAll();
            PrepareSandboxDir(sandbox_dir);
            MakeBindMount(dir, sandbox_dir / "in", false);
            PivotRoot(sandbox_dir, "old_root");
            WaitForExit(Fork([this]() {
                MakeProcMount("/proc");
                RemoveMount("old_root");
                ChangeDir("/in");
                Exec(AbsolutePath(file, "/in"), args, {"PATH=/usr/bin:/bin"});
            }));
        }));
        RemoveAll(sandbox_dir);
    }

private:
    Path dir;
    Path file;
    Vector<String> args;

    SandboxedExecutable(const SandboxedExecutable &) = delete;
    SandboxedExecutable &operator=(const SandboxedExecutable &) = delete;
};

class SandboxedCompiler : public Compiler {
public:
    explicit SandboxedCompiler(const Path &compiler_file,
                               const Vector<String> &compiler_args,
                               const Path &code_file,
                               const Path &execute_file,
                               const Vector<String> &execute_args)
        : compiler_file(compiler_file),
          compiler_args(compiler_args),
          code_file(code_file),
          execute_file(execute_file),
          execute_args(execute_args)
    {}

    Box<Executable> Compile(StringView code) const override {
        Path sandbox_dir = CreateTempPath("jd4.sandbox.%%%%%%%%%%%%%%%%");
        Path output_dir = CreateTempPath("jd4.compiler.%%%%%%%%%%%%%%%%");
        WaitForExit(Fork([this, code, &sandbox_dir, &output_dir] {
            UnshareAll();
            PrepareSandboxDir(sandbox_dir);
            WriteFile(sandbox_dir / code_file, code);
            MakeBindMount(output_dir, sandbox_dir / "out", false);
            PivotRoot(sandbox_dir, "old_root");
            WaitForExit(Fork([this]() {
                MakeProcMount("/proc");
                RemoveMount("old_root");
                Exec(compiler_file, compiler_args, {"PATH=/usr/bin:/bin"});
            }));
        }));
        RemoveAll(sandbox_dir);
        return Box<Executable>(new SandboxedExecutable(output_dir, execute_file, execute_args));
    }

private:
    Path compiler_file;
    Vector<String> compiler_args;
    Path code_file;
    Path execute_file;
    Vector<String> execute_args;
};

class SandboxedInterpreter : public Compiler {
public:
    SandboxedInterpreter(const Path &code_file,
                         const Path &execute_file,
                         const Vector<String> &execute_args)
        : code_file(code_file),
          execute_file(execute_file),
          execute_args(execute_args)
    {}

    Box<Executable> Compile(StringView code) const override {
        Path output_dir = CreateTempPath("jd4.compiler.%%%%%%%%%%%%%%%%");
        WriteFile(AbsolutePath(code_file, output_dir), code);
        return Box<Executable>(new SandboxedExecutable(output_dir, execute_file, execute_args));
    }

private:
    Path code_file;
    Path execute_file;
    Vector<String> execute_args;
};

Box<Compiler> CreateSandboxedCompiler(const Path &compiler_file,
                                      const Vector<String> &compiler_args,
                                      const Path &code_file,
                                      const Path &execute_file,
                                      const Vector<String> &execute_args) {
    return Box<Compiler>(new SandboxedCompiler(compiler_file,
                                               compiler_args,
                                               code_file,
                                               execute_file,
                                               execute_args));
}

Box<Compiler> CreateSandboxedInterpreter(const Path &code_file,
                                         const Path &execute_file,
                                         const Vector<String> &execute_args) {
    return Box<Compiler>(new SandboxedInterpreter(code_file, execute_file, execute_args));
}
