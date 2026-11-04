"""Run a build_suite.py directory on the card through tools/card_run, in chunks of 300 programs.

Lead harness; only the interactive lead runs card jobs. Each chunk is one card job using S2-18's
parallel driver (tools/claude-torture.c, built here with the donor) at -j 60 on our cores 40-59
(3 threads per core, owner 2026-11-04), 96 MiB per program. Chunks keep the Windows command line under 32K characters. A chunk refused
for infrastructure is retried up to twice. Receipts go to OUTDIR/result<N>.json.

usage: python harness/card/run_suite.py PROGDIR OUTDIR
"""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / ".work/_shared"
STATE = REPO / ".work/_state/card"
P = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
STATE.mkdir(parents=True, exist_ok=True)

# The parallel driver, built once with the donor.
driver = SHARED / "tmp/claude-torture-driver/claude-torture"
if not driver.exists():
    driver.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH=str(SHARED / "toolchain/cygwin/bin") + os.pathsep + os.environ["PATH"])
    subprocess.run([(SHARED / "toolchain/cross/bin/k1om-mpss-linux-gcc.exe").as_posix(), "-O2",
                    str(REPO / "tools/claude-torture.c"), "-o", str(driver)], check=True, env=env)

# card_run takes memoryMB only from its config: 60 programs x 96 MiB = 5760 MiB, under 7 GB.
config = json.loads((REPO / "config/card.local.json").read_text(encoding="utf8"))
config["memoryMB"] = 5760
cfg = STATE / "card-j60.json"
cfg.write_text(json.dumps(config, indent=1), encoding="utf8")

entries = [l for l in (P / "claude-torture.list").read_text(encoding="utf8").splitlines() if l.strip()]
rel = os.path.relpath(P, REPO)
all_lines = []
for start in range(0, len(entries), 300):
    chunk, k = entries[start:start + 300], start // 300
    lst = P / ("claude-chunk%d.list" % k)
    lst.write_text("\n".join(chunk) + "\n", encoding="utf8")
    for attempt in range(3):
        cmd = [sys.executable, "tools/card_run", "--config", str(cfg), "--timeout", "900",
               "--transport-timeout", "120", "--receipt", str(OUT / ("result%d.json" % k)),
               "--file", os.path.join(rel, lst.name)]
        for e in chunk:
            cmd += ["--file", os.path.join(rel, e.split()[0])]
        cmd += [str(driver), "-j", "60", "--limit-mb", "96", lst.name]
        done = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
        lines = [l for l in done.stdout.decode("utf8", "replace").splitlines()
                 if l.split(" ")[0] in ("PASS", "FAIL", "TIMEOUT")]
        r = json.loads((OUT / ("result%d.json" % k)).read_text(encoding="utf8"))
        print("chunk", k, "attempt", attempt, "exit", done.returncode, r.get("result_class"),
              dict(Counter(l.split(" ")[0] for l in lines)), str(r.get("detail") or "")[:160], flush=True)
        if r.get("result_class") != "infrastructure":
            break
    all_lines += lines
(OUT / "actual.txt").write_text("\n".join(all_lines) + "\n", encoding="utf8")
print("total", len(all_lines), "of", len(entries), dict(Counter(l.split(" ")[0] for l in all_lines)))
for l in all_lines:
    if not l.startswith("PASS"):
        print(l[:200])
