#include "process.h"
#include "util.h"

void GccCompile(StringView code) {
    Path sandbox_dir = CreateTempPath("jd4.sandbox.%%%%%%%%%%%%%%%%");
    Path code_dir = CreateTempPath("jd4.compile.gcc.%%%%%%%%%%%%%%%%");
    {
        OFStream code_sink(code_dir / "foo.c", Ios::binary);
        code_sink.write(code.data(), code.size());
    }

    CHECK_UNIX(Fork([&sandbox_dir, &code_dir]() {
        Sandbox(sandbox_dir, {
            {"/bin", "/bin"},
            {"/lib", "/lib"},
            {"/lib64", "/lib64"},
            {"/usr", "/usr"},
            {code_dir, "/code"},
        });
        WaitForExit(Execute("/usr/bin/gcc",
                            {"gcc", "-static", "-o/code/foo.out", "/code/foo.c"},
                            {"PATH=/usr/bin:/bin"}));
    }));
    wait(NULL);

    // TODO(iceboy): This is just for fun.
    CHECK_UNIX(Fork([&sandbox_dir, &code_dir]() {
        Sandbox(sandbox_dir, {
            {code_dir, "/bin"},
        });
        WaitForExit(Execute("/bin/foo.out", {}, {}));
    }));
    wait(NULL);

    RemoveAll(code_dir);
    RemoveAll(sandbox_dir);
}
