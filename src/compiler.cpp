#include "compiler.h"

#include "process.h"

class CompiledPackage : public Package {
public:
    explicit CompiledPackage(const Path &package_dir,
                             const Path &execute_file,
                             const Vector<String> &args)
        : package_dir(package_dir),
          execute_file(execute_file),
          args(args)
    {}

    ~CompiledPackage() override {
        RemoveAll(package_dir);
    }

    void Install(const Path &install_dir) const override {
        CopyFiles(package_dir, install_dir);
    }

    Process Execute(const Path &install_dir) const override {
        return ::Execute(AbsolutePath(execute_file, install_dir), args, {}, install_dir);
    }

private:
    Path package_dir;
    Path execute_file;
    Vector<String> args;

    CompiledPackage(const CompiledPackage &) = delete;
    CompiledPackage &operator=(const CompiledPackage &) = delete;
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

    Box<Package> Compile(StringView code) const override {
        Path compiler_canonical = CanonicalPath(compiler_file);
        Path sandbox_dir = CreateTempPath("jd4.sandbox.%%%%%%%%%%%%%%%%");
        Path output_dir = CreateTempPath("jd4.compiler.%%%%%%%%%%%%%%%%");
        WaitForExit(Fork([this, code, &compiler_canonical, &sandbox_dir, &output_dir] {
            PrepareSandbox(sandbox_dir, {
                {"/bin", "/bin"},
                {"/lib", "/lib"},
                {"/lib64", "/lib64"},
                {"/usr", "/usr"},
                {output_dir, "/out"},
            });
            WriteFile(code_file, code);
            WaitForExit(Fork([this, &compiler_canonical]() {
                CHECK(MakeDir("proc"));
                CHECK_UNIX(mount("/proc", "/proc", "proc", 0, NULL));
                CompleteSandbox();
                WaitForExit(Execute(compiler_canonical, compiler_args, {"PATH=/usr/bin:/bin"}, "/"));
            }));
        }));
        RemoveAll(sandbox_dir);
        return Box<Package>(new CompiledPackage(output_dir, execute_file, execute_args));
    }

private:
    Path compiler_file;
    Vector<String> compiler_args;
    Path code_file;
    Path execute_file;
    Vector<String> execute_args;
};

class Interpreter : public Compiler {
public:
    Interpreter(const Path &code_file,
                const Path &execute_file,
                const Vector<String> &execute_args)
        : code_file(code_file),
          execute_file(execute_file),
          execute_args(execute_args)
    {}

    Box<Package> Compile(StringView code) const override {
        Path output_dir = CreateTempPath("jd4.compiler.%%%%%%%%%%%%%%%%");
        WriteFile(AbsolutePath(code_file, output_dir), code);
        return Box<Package>(new CompiledPackage(output_dir, execute_file, execute_args));
    }

private:
    Path code_file;
    Path execute_file;
    Vector<String> execute_args;
};

Box<Compiler> CreateCompiler(const Path &compiler_file,
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

Box<Compiler> CreateInterpreter(const Path &code_file,
                                const Path &execute_file,
                                const Vector<String> &execute_args) {
    return Box<Compiler>(new Interpreter(code_file, execute_file, execute_args));
}
