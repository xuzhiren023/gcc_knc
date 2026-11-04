"""Build gcc.c-torture/execute programs for the card with the shared GCC 16 build or the donor.

Lead harness (not engineer tooling). Flags follow S2-08: -O2, -march=knc for GCC 16, each file's
own dg-options (quoted, bare, or brace-list form), -w, linked with -lm. It records which linked
programs contain packed zmm code.

usage: python harness/card/build_suite.py OUTDIR [gcc16|donor] [--list FILE]
  --list FILE   build only the sources named in FILE (lines "program source"), e.g. S2-08's
                .work/_shared/tmp/S2-08/claude-torture.list; default: every execute/*.c
Writes OUTDIR/claude-torture.list (program source) for what linked, and OUTDIR/build.tsv.
Run it only while no make.exe is rebuilding cc1 in .work/_shared/gcc-build.
"""
import argparse
import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / ".work/_shared"
BUILD = SHARED / "gcc-build/gcc"
SRC = SHARED / "gcc/gcc/testsuite/gcc.c-torture/execute"
OBJDUMP = (SHARED / "toolchain/cross/bin/k1om-mpss-linux-objdump.exe").as_posix()
PACKED = re.compile(r"v(add|sub|mul|fmadd\d*)p[sd]|vpadd[dq]|vpmulld|vpsub[dq]|vloadunpack|vpackstore|vbroadcast")
OPTIONS = re.compile(r'\{\s*dg-(?:additional-)?options\s+(?:"([^"\n]*)"|\{([^{}\n]*)\}|([^\s{}]+))'
                     r'(\s*\{\s*target\b)?')

parser = argparse.ArgumentParser()
parser.add_argument("outdir", type=Path)
parser.add_argument("compiler", nargs="?", default="gcc16", choices=("gcc16", "donor"))
parser.add_argument("--list", type=Path)
args = parser.parse_args()
OUT = args.outdir
OUT.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PATH=str(SHARED / "toolchain/cygwin/bin") + os.pathsep + os.environ["PATH"])
if args.compiler == "gcc16":
    cc, arch = [BUILD.as_posix() + "/xgcc.exe", "-B" + BUILD.as_posix() + "/"], ["-march=knc"]
else:
    cc, arch = [(SHARED / "toolchain/cross/bin/k1om-mpss-linux-gcc.exe").as_posix()], []
if args.list:
    sources = [SRC / l.split()[1] for l in args.list.read_text().splitlines() if l.strip()]
else:
    sources = sorted(SRC.glob("*.c"))


def build(source):
    text = source.read_text(errors="replace")
    extra = []
    for m in OPTIONS.finditer(text):
        if m[4] is None:
            extra += shlex.split(m[1] if m[1] is not None else m[2] if m[2] is not None else m[3])
    prog = "claude-t-" + source.stem + ".mic"
    obj = OUT / (source.stem + ".o")
    try:
        r = subprocess.run([*cc, "-O2", *arch, "-w", *extra, "-c", source.as_posix(), "-o", str(obj)],
                           env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return source.name, prog, "compile timeout", 0
    if r.returncode:
        last = (r.stderr.strip().splitlines() or [""])[-1]
        kind = "ICE" if "internal compiler error" in r.stderr else "compile error"
        return source.name, prog, kind + ": " + last[-160:], 0
    r = subprocess.run([*cc, "-O2", *arch, str(obj), "-lm", "-o", str(OUT / prog)],
                       env=env, capture_output=True, text=True, timeout=300)
    obj.unlink(missing_ok=True)
    if r.returncode:
        return source.name, prog, "link error: " + (r.stderr.strip().splitlines() or [""])[-1][-160:], 0
    dis = subprocess.run([OBJDUMP, "-d", str(OUT / prog)], capture_output=True, text=True, env=env)
    return source.name, prog, "linked", int(bool(PACKED.search(dis.stdout)))


with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(build, sources))
(OUT / "build.tsv").write_text("source\tprogram\tresult\tpacked\n" + "".join(
    "%s\t%s\t%s\t%d\n" % r for r in results), encoding="utf8")
(OUT / "claude-torture.list").write_text("".join(
    "%s %s\n" % (p, s) for s, p, res, _ in results if res == "linked"), encoding="utf8")
linked = [r for r in results if r[2] == "linked"]
print("sources", len(results), "linked", len(linked), "with packed zmm", sum(r[3] for r in linked))
for kind in ("ICE", "compile error", "compile timeout", "link error"):
    print(kind, sum(1 for r in results if r[2].startswith(kind)))
for r in results:
    if r[2].startswith("ICE"):
        print("ICE", r[0], r[2])
