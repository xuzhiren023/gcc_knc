"""Build the Sprint 9 OpenMP card check (S9-06, rerun by S9-10 and S9-11): six C and two Fortran
programs plus the runtime probe, against libgomp shared and static.

usage: python tests/acceptance/s9_omp/build.py OUTDIR --cc GCC... --fc GFORTRAN... --libdir DIR
       python tests/acceptance/s9_omp/build.py OUTDIR --host

--cc and --fc take the GCC 16 drivers and any arguments after them (e.g. "--cc xgcc -B dir/");
--libdir holds the k1om libgomp.so.1, libgomp.a, libgfortran.so.5, libquadmath.so.0 and
libgcc_s.so.1 (and the omp_lib module is found by --fc). Writes OUTDIR/runs.txt, one card job per
line: "program file,file,... expected-line" (files staged beside the program; "-" for none). Run
each job at 60x1 and 60x4 (OMP_NUM_THREADS=60 and 240) with OMP_DISPLAY_ENV=verbose; the expected
line is the same at both. Each program is also built with -DBREAK, which must print FAIL.

--host builds the eight programs with the Cygwin GCC in the shared toolchain and runs them here,
which checks the fixtures themselves (the runtime probe is card-only).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[2] / ".work/_shared"
CYGWIN = SHARED / "toolchain/cygwin/bin"
PROGRAMS = {"for": 3, "reduction": 4, "critical": 4, "single": 4, "tasks": 3, "locks": 4,
            "do": 3, "sections": 3}
CARD_ONLY = {"runtime": 3}
LIBS = ("libgomp.so.1", "libgfortran.so.5", "libquadmath.so.0", "libgcc_s.so.1")

parser = argparse.ArgumentParser()
parser.add_argument("out", type=Path)
parser.add_argument("--cc", nargs="+")
parser.add_argument("--fc", nargs="+")
parser.add_argument("--libdir", type=Path)
parser.add_argument("--host", action="store_true")
args = parser.parse_args()
if args.host == bool(args.cc and args.fc and args.libdir):
    sys.exit("give either --host or all of --cc, --fc and --libdir")
OUT = args.out.resolve()
OUT.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PATH=str(CYGWIN) + os.pathsep + os.environ["PATH"])
CC = args.cc or [(CYGWIN / "gcc.exe").as_posix()]
FC = args.fc or [(CYGWIN / "gfortran.exe").as_posix()]


def run(cmd, check=True):
    r = subprocess.run([str(c) for c in cmd], env=env, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(str(c) for c in cmd), r.stdout, r.stderr))
    return r


def source(name):
    return HERE / (name + (".F90" if name in ("do", "sections") else ".c"))


def expect(name, checks, broken):
    return "S9-OMP %s %s checks=%d failures=%d" % (name, "FAIL" if broken else "PASS", checks, int(broken))


runs, bad = [], []
programs = dict(PROGRAMS, **({} if args.host else CARD_ONLY))
for name, checks in programs.items():
    fortran = name in ("do", "sections")
    drv = FC if fortran else CC
    std = [] if fortran else ["-std=gnu11"]
    for broken in (False, True):
        b = ["-DBREAK"] if broken else []
        stem = "claude-s9omp-%s%s" % (name, "-break" if broken else "")
        obj = OUT / (stem + ".o")
        run([*drv, *std, "-O2", "-fopenmp", *b, "-I" + HERE.as_posix(), "-c", source(name), "-o", obj])
        if args.host:
            exe = OUT / (stem + ".exe")
            run([*drv, "-fopenmp", obj, "-o", exe])
            out = run([exe], check=False).stdout
            want = expect(name, checks, broken)
            ok = want in out.splitlines()
            print("%-28s %s" % (stem, "ok" if ok else "WRONG:\n" + out))
            if not ok:
                bad.append(stem)
            continue
        prog = OUT / (stem + "-shared.mic")
        run([*drv, "-fopenmp", obj, "-Wl,-rpath,$ORIGIN", "-o", prog])
        runs.append("%s %s %s" % (prog.name, ",".join(LIBS), expect(name, checks, broken)))
        if not broken and name != "runtime":
            # libgomp.a linked in; the other runtimes stay shared (the sysroot has no static glibc).
            prog = OUT / (stem + "-static.mic")
            run([*drv, obj, (args.libdir / "libgomp.a").as_posix(), "-pthread", "-Wl,-rpath,$ORIGIN", "-o", prog])
            runs.append("%s %s %s" % (prog.name, ",".join(LIBS[1:]), expect(name, checks, False)))
        obj.unlink()
if args.host:
    sys.exit("host check failed: " + " ".join(bad) if bad else 0)
# LF only: the card reads it with a shell, and a CR would end every expected line.
(OUT / "runs.txt").write_bytes(("\n".join(runs) + "\n").encode("utf8"))
print("\n".join(runs))
