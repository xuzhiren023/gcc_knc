"""Run a build_suite.py directory on the card through tools/card_run, one packed upload per job.

Lead harness; only the interactive lead runs card jobs. Each chunk is one card job using S2-18's
parallel driver (tools/claude-torture.c, built here with the donor) at -j 80 on our cores 40-59
(4 threads per core, owner 2026-11-04), 96 MiB per program. Programs travel as one pack
(--file-list, S4-12); a batch splits only when maxStageMiB requires it. A chunk refused
for infrastructure is retried up to twice. Receipts go to OUTDIR/result<N>.json.

usage: python harness/card/run_suite.py PROGDIR OUTDIR
"""
import json
import argparse
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO.parent.parent if REPO.parent.name == ".work" else REPO
SHARED = PROJECT / ".work/_shared"
STATE = PROJECT / ".work/_state/card"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("programs", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--transfer", choices=("ssh", "dma", "auto"), default="auto")
parser.add_argument("--dma-threshold", type=int, default=1048576)
args = parser.parse_args()
P = args.programs.resolve()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
STATE.mkdir(parents=True, exist_ok=True)

# The parallel driver, built once with the donor.
driver = SHARED / "tmp/claude-torture-driver/claude-torture"
if not driver.exists():
    driver.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH=str(SHARED / "toolchain/cygwin/bin") + os.pathsep + os.environ["PATH"])
    subprocess.run([(SHARED / "toolchain/cross/bin/k1om-mpss-linux-gcc.exe").as_posix(), "-O2",
                    str(REPO / "tools/claude-torture.c"), "-o", str(driver)], check=True, env=env)

# card_run takes memoryMB only from its config: 80 programs x 96 MiB = 7680 MiB, within our 10 GiB budget (owner, 2026-11-04).
config = json.loads((PROJECT / "config/card.local.json").read_text(encoding="utf8"))
config["memoryMB"] = 7680
cfg = STATE / "card-j80.json"
cfg.write_text(json.dumps(config, indent=1), encoding="utf8")

entries = [l for l in (P / "claude-torture.list").read_text(encoding="utf8").splitlines() if l.strip()]
rel = os.path.relpath(P, REPO)
# S4-12: one packed upload per job (--file-list), so chunk only when maxStageMiB requires it.
# The stage also carries the driver, claude-pin and claude-unpack; keep 64 KiB for the list.
limit = config.get("maxStageMiB", 64) * 1024 * 1024 - 64 * 1024 - driver.stat().st_size - sum(
    (SHARED / name).stat().st_size for name in ("claude-pin.mic", "claude-unpack.mic"))
limit -= Path(config.get("transferHelper", str(SHARED / "claude-transfer.mic"))).stat().st_size
chunks, size = [[]], 0
for e in entries:
    n = (P / e.split()[0]).stat().st_size
    if chunks[-1] and size + n > limit:
        chunks.append([])
        size = 0
    chunks[-1].append(e)
    size += n
all_lines = []
for k, chunk in enumerate(chunks):
    lst = P / ("claude-chunk%d.list" % k)
    lst.write_text("\n".join(chunk) + "\n", encoding="utf8")
    stage = P / ("claude-chunk%d.stage" % k)
    stage.write_text("\n".join([os.path.join(rel, lst.name)] +
                               [os.path.join(rel, e.split()[0]) for e in chunk]) + "\n", encoding="utf8")
    for attempt in range(3):
        cmd = [sys.executable, "tools/card_run", "--config", str(cfg), "--timeout", "900",
               "--transport-timeout", "120", "--receipt", str(OUT / ("result%d.json" % k)),
               "--file-list", str(stage), "--threads", "80", "--transfer", args.transfer,
               "--dma-threshold", str(args.dma_threshold)]  # Shared packed file transport.
        cmd += [str(driver), "-j", "80", "--limit-mb", "96", lst.name]
        done = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
        lines = [l for l in done.stdout.decode("utf8", "replace").splitlines()
                 if l.split(" ")[0] in ("PASS", "FAIL", "TIMEOUT")]
        r = json.loads((OUT / ("result%d.json" % k)).read_text(encoding="utf8"))
        print("chunk", k, "attempt", attempt, "exit", done.returncode, r.get("result_class"),
              dict(Counter(l.split(" ")[0] for l in lines)), str(r.get("detail") or "")[:160], flush=True)
        if r.get("transfer_stop"):
            raise SystemExit("STOP: transfer integrity or cleanup unresolved; no suite retry")
        if r.get("result_class") != "infrastructure":
            break
    all_lines += lines
(OUT / "actual.txt").write_text("\n".join(all_lines) + "\n", encoding="utf8")
print("total", len(all_lines), "of", len(entries), dict(Counter(l.split(" ")[0] for l in all_lines)))
for l in all_lines:
    if not l.startswith("PASS"):
        print(l[:200])
