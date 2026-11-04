"""Build the S3-14 TLS card check: GCC 16 and donor code sharing __thread variables.

usage: python tests/acceptance/s3_tls_card/build.py OUTDIR
Run it only while no make.exe is rebuilding cc1. Writes OUTDIR/runs.txt, one card job per line:
"program library expected-line".

Variants (main / tls_new / tls_donor / tls_lib):
  A   gcc16 -O2 / gcc16 -O2 / donor -O2 / donor -O2 -fPIC     the ticket's three cases
  B   gcc16 -O0 / gcc16 -O0 / donor -O2 / donor -O2 -fPIC
  C   donor -O2 / gcc16 -O2 / donor -O2 / gcc16 -O2 -fPIC      GCC 16's dynamic models in a .so
  D   donor -O2 / gcc16 -O0 / donor -O2 / gcc16 -O0 -fPIC
  X   A with -DCONTROL_SHARED everywhere: must print S3-TLS FAIL
Before linking, every GCC 16 object is checked for __emutls references.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHARED = REPO / ".work/_shared"
BUILD = SHARED / "gcc-build/gcc"
NM = (SHARED / "toolchain/cross/bin/k1om-mpss-linux-nm.exe").as_posix()
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PATH=str(SHARED / "toolchain/cygwin/bin") + os.pathsep + os.environ["PATH"])
CC = {"gcc16": [BUILD.as_posix() + "/xgcc.exe", "-B" + BUILD.as_posix() + "/", "-march=knc"],
      "donor": [(SHARED / "toolchain/cross/bin/k1om-mpss-linux-gcc.exe").as_posix()]}


def run(cmd):
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode:
        sys.exit("FAILED: %s\n%s" % (" ".join(cmd), r.stderr))
    return r.stdout


def obj(variant, name, cc, opt, extra=()):
    out = OUT / ("%s-%s.o" % (variant, name))
    run([*CC[cc], opt, *extra, "-pthread", "-c", str(HERE / (name + ".c")), "-o", str(out)])
    if cc == "gcc16" and "emutls" in run([NM, str(out)]):
        sys.exit("FAILED: %s uses emulated TLS" % out)
    return str(out)


VARIANTS = {"A": ("gcc16", "-O2", "donor", "-O2"), "B": ("gcc16", "-O0", "donor", "-O2"),
            "C": ("donor", "-O2", "gcc16", "-O2"), "D": ("donor", "-O0", "gcc16", "-O0"),
            "X": ("gcc16", "-O2", "donor", "-O2")}
runs = []
for v, (main_cc, new_opt, lib_cc, lib_opt) in VARIANTS.items():
    d = ["-DCONTROL_SHARED"] if v == "X" else []
    lib = "libclaude-tls%s.so" % v
    run([*CC[lib_cc], lib_opt, *d, "-fPIC", "-shared", str(HERE / "tls_lib.c"), "-o", str(OUT / lib)])
    if lib_cc == "gcc16" and "emutls" in run([NM, "-D", str(OUT / lib)]):
        sys.exit("FAILED: %s uses emulated TLS" % lib)
    main_opt = new_opt if main_cc == "gcc16" else "-O2"
    objs = [obj(v, "tls_main", main_cc, main_opt, d), obj(v, "tls_new", "gcc16", new_opt, d),
            obj(v, "tls_donor", "donor", "-O2", d)]
    prog = "claude-tls%s.mic" % v
    run([*CC[main_cc], "-pthread", *objs, str(OUT / lib), "-Wl,-rpath,$ORIGIN", "-o", str(OUT / prog)])
    for o in objs:
        os.unlink(o)
    runs.append("%s %s %s" % (prog, lib, "S3-TLS FAIL" if v == "X" else "S3-TLS PASS checks=59 failures=0"))
(OUT / "runs.txt").write_text("\n".join(runs) + "\n", encoding="utf8")
print("\n".join(runs))
