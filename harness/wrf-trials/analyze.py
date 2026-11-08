"""Analyze WRF optimization trials (harness/wrf-trials/PLAN.md).

Reads WRF's per-step "Timing for main" lines from rsl.out.0000 in each run directory.

  python analyze.py --pilot RUN_DIR ...
      Window-length choice: for N in 24, 36, 48, 60 measured steps after the start-up steps, the
      median step time, the run-to-run spread, and the gap to the 60-step value.
  python analyze.py --skip K --steps N --baseline B1 B2 ... --arm A1 A2 ...
      Pairs baseline and arm runs in the order given (interleaved B, A, B, A in the card window),
      reports per-pair ratios T_arm/T_baseline of the median step time, their median, and a
      bootstrap 95% interval (10,000 resamples, fixed seed). An effect counts if the interval
      excludes 1 and the median ratio differs from 1 by more than 2%.
Optional telemetry summaries (power.csv, mem.csv, threads.csv) are printed when present.
"""
import argparse
import csv
import os
import random
import re
import statistics as st

STEP = re.compile(r"Timing for main: time \S+ on domain\s+(\d+):\s+([0-9.]+) elapsed seconds")


def step_times(run_dir, domain=1):
    times = []
    with open(os.path.join(run_dir, "rsl.out.0000"), errors="replace") as f:
        for line in f:
            m = STEP.search(line)
            if m and int(m.group(1)) == domain:
                times.append(float(m.group(2)))
    return times


def window_median(times, skip, n):
    w = times[skip:skip + n]
    if len(w) < n:
        raise ValueError("run has %d steps after skipping %d; need %d" % (len(times) - skip, skip, n))
    return st.median(w)


def telemetry(run_dir):
    out = []
    p = os.path.join(run_dir, "power.csv")
    if os.path.exists(p):
        w = [float(r["card_uW"]) / 1e6 for r in csv.DictReader(open(p)) if r["card_uW"]]
        if w:
            out.append("power mean %.1f W (min %.1f, max %.1f, %d samples)" % (st.mean(w), min(w), max(w), len(w)))
    m = os.path.join(run_dir, "mem.csv")
    if os.path.exists(m):
        rows = list(csv.DictReader(open(m)))
        if rows:
            used = max(int(r["HugePages_Total"] or 0) - int(r["HugePages_Free"] or 0) for r in rows)
            out.append("2 MB pages in use (max) %d = %.1f GB" % (used, used * 2 / 1024))
    t = os.path.join(run_dir, "threads.csv")
    if os.path.exists(t):
        last = {}
        for r in csv.DictReader(open(t)):
            last[r["tid"]] = r
        inv = sum(int(r["invol_ctxt"] or 0) for r in last.values())
        cpus = len({r["cpu"] for r in last.values()})
        out.append("threads %d on %d CPUs, involuntary context switches %d" % (len(last), cpus, inv))
    return out


def pilot(dirs, skip):
    runs = [step_times(d) for d in dirs]
    ref = [window_median(r, skip, 60) for r in runs]
    print("start-up steps skipped: %d" % skip)
    for n in (24, 36, 48, 60):
        meds = [window_median(r, skip, n) for r in runs]
        spread = (max(meds) - min(meds)) / st.median(meds)
        gap = st.median([abs(a / b - 1) for a, b in zip(meds, ref)])
        print("N=%2d  median %.3f s  run spread %.1f%%  gap to 60-step %.2f%%" % (n, st.median(meds), spread * 100, gap * 100))
    print("Choose the smallest N with gap < 1% and spread < 2% (PLAN.md section 3).")


def compare(base, arm, skip, n):
    if len(base) != len(arm):
        raise SystemExit("baseline and arm need the same number of runs (paired in card order)")
    ratios = [window_median(step_times(a), skip, n) / window_median(step_times(b), skip, n) for b, a in zip(base, arm)]
    rng = random.Random(1510)
    boots = sorted(st.median([rng.choice(ratios) for _ in ratios]) for _ in range(10000))
    lo, hi = boots[249], boots[9749]
    med = st.median(ratios)
    effect = (lo > 1 or hi < 1) and abs(med - 1) > 0.02
    print("pairs %d  ratios %s" % (len(ratios), " ".join("%.3f" % r for r in ratios)))
    print("median T_arm/T_base %.3f  95%% interval [%.3f, %.3f]  -> %s" % (
        med, lo, hi, ("faster" if med < 1 else "slower") if effect else "no measurable effect"))
    for label, dirs in (("baseline", base), ("arm", arm)):
        for d in dirs[:1]:
            for line in telemetry(d):
                print("%s %s: %s" % (label, os.path.basename(d.rstrip("/\\")), line))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", nargs="+")
    ap.add_argument("--baseline", nargs="+")
    ap.add_argument("--arm", nargs="+")
    ap.add_argument("--skip", type=int, default=12, help="start-up steps to drop (default 12)")
    ap.add_argument("--steps", type=int, default=36, help="measured steps (from the pilot)")
    a = ap.parse_args()
    if a.pilot:
        pilot(a.pilot, a.skip)
    elif a.baseline and a.arm:
        compare(a.baseline, a.arm, a.skip, a.steps)
    else:
        ap.error("give --pilot, or --baseline and --arm")


if __name__ == "__main__":
    main()
