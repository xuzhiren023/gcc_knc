"""Build the Sprint 9 C++ card check (S9-03 to S9-05): libstdc++, libsupc++ and libatomic on KNC.

usage: python tests/acceptance/s9_cxx/build.py OUTDIR [--cxx G++ --libdir DIR]

Without --cxx, everything is built by the donor GCC 5.1.1 (fixture validation; tz is skipped).
With --cxx (the GCC 16 g++ driver, plus any arguments after it, e.g. "--cxx xg++ -B dir/") and
--libdir (where its libstdc++.so.6, libgcc_s.so.1 and libatomic.so.1 are), every program is built by
it, and the cross-DSO check is built three ways: GCC 16 main and library, GCC 16 main with a donor
library, and a donor main with a GCC 16 library. Writes OUTDIR/runs.txt, one card job per line:
"program file,file,... expected-line" (files staged beside the program; "-" for none). Each program
is also built with -DBREAK, which must print FAIL.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[2] / ".work/_shared"
TC = SHARED / "toolchain"
DONOR = [(TC / "cross/bin/k1om-mpss-linux-g++.exe").as_posix()]
# Staged name -> donor file (the Cygwin symlinks do not copy).
DONOR_LIBS = {"libstdc++.so.6": TC / "sysroot/usr/lib64/libstdc++.so.6.0.21",
              "libgcc_s.so.1": TC / "sysroot/lib64/libgcc_s.so.1",
              "libatomic.so.1": TC / "cross/k1om-mpss-linux/lib64/libatomic.so.1.1.0"}
CHECKS = {"hello": 6, "eh": 7, "rtti": 8, "thread": 6, "atomic16": 3, "xdso": 5, "tz": 4}
STATIC = ("hello", "eh", "rtti")

parser = argparse.ArgumentParser()
parser.add_argument("out", type=Path)
parser.add_argument("--cxx", nargs="+")
parser.add_argument("--libdir", type=Path)
args = parser.parse_args()
if bool(args.cxx) != bool(args.libdir):
    sys.exit("--cxx and --libdir go together")
OUT = args.out.resolve()
OUT.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PATH=str(TC / "cygwin/bin") + os.pathsep + os.environ["PATH"])
NEW = args.cxx or DONOR
LIBS = {n: (args.libdir / n).resolve() for n in DONOR_LIBS} if args.libdir else DONOR_LIBS
tag = "new" if args.cxx else "donor"


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], env=env, capture_output=True, text=True)
    if r.returncode:
        sys.exit("FAILED: %s\n%s" % (" ".join(str(c) for c in cmd), r.stderr))


def flags(name):
    std = "-std=gnu++20" if name == "tz" else "-std=gnu++14"
    return [std, "-O2", "-pthread", "-I" + HERE.as_posix()]


def libs_for(libs):
    for name, path in libs.items():
        shutil.copyfile(path, OUT / name)
    return ",".join(sorted(libs))


def expect(name, broken):
    n = CHECKS[name]
    if broken:
        return "S9-CXX %s FAIL checks=%d failures=1" % (name, n)
    return "S9-CXX %s PASS checks=%d failures=0" % (name, n)


runs = []
for name in CHECKS:
    if name == "xdso" or (name == "tz" and not args.cxx):
        continue
    extra = ["-latomic"] if name == "atomic16" else []
    for broken in (False, True):
        b = ["-DBREAK"] if broken else []
        suffix = "-break" if broken else ""
        prog = "claude-s9cxx-%s-%s-shared%s.mic" % (tag, name, suffix)
        run([*NEW, *flags(name), *b, HERE / (name + ".cc"), "-Wl,-rpath,$ORIGIN", *extra, "-o", OUT / prog])
        runs.append("%s %s %s" % (prog, libs_for(LIBS), expect(name, broken)))
        if name in STATIC and not broken:
            # The k1om sysroot has no static glibc, so "static" means libstdc++ and libgcc linked in.
            prog = "claude-s9cxx-%s-%s-static.mic" % (tag, name)
            run([*NEW, *flags(name), HERE / (name + ".cc"), "-static-libstdc++", "-static-libgcc", "-o", OUT / prog])
            runs.append("%s - %s" % (prog, expect(name, False)))

# Cross-DSO pairs: (main compiler, library compiler).
pairs = [(tag, NEW, tag, NEW)]
if args.cxx:
    pairs += [("new", NEW, "donor", DONOR), ("donor", DONOR, "new", NEW)]
for mtag, mcc, ltag, lcc in pairs:
    lib = "libclaude-s9x-%s.so" % ltag
    run([*lcc, *flags("xdso"), "-fPIC", "-shared", "-Wl,-soname," + lib, HERE / "xlib.cc", "-o", OUT / lib])
    for broken in (False, True):
        b = ["-DBREAK"] if broken else []
        prog = "claude-s9cxx-xdso-%s-%s%s.mic" % (mtag, ltag, "-break" if broken else "")
        run([*mcc, *flags("xdso"), *b, HERE / "xmain.cc", OUT / lib, "-Wl,-rpath,$ORIGIN", "-o", OUT / prog])
        # The newer libstdc++ must be the one loaded when either half is GCC 16.
        runs.append("%s %s,%s %s" % (prog, lib, libs_for(LIBS), expect("xdso", broken)))
(OUT / "runs.txt").write_text("\n".join(runs) + "\n", encoding="utf8")
print("\n".join(runs))
