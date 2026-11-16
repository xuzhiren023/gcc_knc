# S13-01 primary gate handoff

Host staging has two steps: run `tools/m4_gate.py stage` with the shared Cygwin
Python through tools/run.py for compilation/lint/references, then run
`python tools/m4_gate.py freeze` with Windows Python for the final configuration
and script writes. The latter uses Windows Git for the ticket revision and does
not rebuild or retest anything. This avoids Cygwin/Windows ownership-identity
differences without changing Git's ownership protection.

This is serial -O2 GCC-KNC versus GCC 5.1.1 **with the SQLite donor assembly
exception**. `freeze.json` records all four ordinary SQLite assembly outcomes,
their retained diagnostics (including failed kmov assembly), and the highest
assembling donor level used on every profile. GCC-KNC stays at -O2 -march=knc.
The prefix is lane 1 `.work/_shared/gcc-knc-16.2.0`, frozen by the lead at
knc b2ce6a9eebf with target libraries reinstalled 2026-11-15. Lane 2 is unused.
The staged per-build logs contain complete commands; runtime-prefix.json records
driver and selected runtime revisions and dependency graphs. Inputs, source
versions, flags, checker code and commands are fixed before timing. HPCG's only
source change is the authorized addition of `n` to its default(none) shared list,
identical for both compilers. Its input is 104 cubed, requested time zero, exactly
one reported CG set; unequal actual iteration work blocks scoring.

The scored set is exactly the canonical 17 programs, including adi, durbin and
bzip2. Unsealing means adding these votes now; their artifacts, observations,
timings and the full score remain under `.work/_shared/m4-sealed/S13-01/`.
Public output is readiness and pass/fail. No held-out data may guide tuning.
Profiles constrain cores and memory on a 7120, not clock or per-core bandwidth;
these are not native 3120/5110 measurements.

## Lead preconditions

1. Provision and verify lead/runner-only ACLs on the sealed directory, its
   parents, and runner/transport scratch and log paths. Engineers neither
   provision ACLs nor inspect held-out outputs, timings or sealed logs.
2. Review `freeze.json`, all selected build records and complete commands.
   Verify the installed prefix identity against the frozen lead revision.
   Preserve the SQLite exception and failure diagnostics in every headline.
3. Book an exclusive window for each profile, with PhiWeather coordination.
   No foreign workload or overlapping job is allowed. The staged scripts use
   `card_run --benchmark`, all granted CPUs, a single pinned benchmark worker,
   ordinary unprivileged allocations, and fresh processes with no external
   prewarming. Source-internal warm-up and checks remain timed.
4. Write `environment-policy.json` in the public stage before the first launch,
   with `lead_verified: true`, a nonempty `clock_power_policy` describing the
   externally verified start/end policy, and `exclusive_window` identifying the
   booking. Keep the policy identical across every model/block. Confirm it at
   the start and end of each booked window. Generic sysfs observations record
   unavailable interfaces explicitly; they do not establish unavailable card
   power controls. The lead must verify those controls externally.
5. Verify the duration budget below against existing sealed feasibility data
   without exposing it to engineers. Do not resize workloads using gate results.
   Refresh the coordination turn as required for these long windows.

## Card time and profile split

There are 204 timed launches plus six correctness-only control launches per
profile, 630 launches total. The public S11-18 serial pilot maximum latencies
for the 14 development programs sum to about 1,198 seconds. Twelve members of
each program therefore account for about **4.0 hours per profile**, before the
three held-out programs, transfers and controls. The HPCG pilot dominates and
is a conservative proxy: it predates the fixed-one-set gate workload.

Reserve **5-7 hours for full 7120, 5-7 hours for 3100, and 5-7 hours for 5100**
(15-21 hours total); this is a planning estimate, not native final-head timing.
Held-out feasibility timings have not been read by the engineer. The lead must
confirm that their sum plus transport/control time fits the booked window;
until then the upper budget is unverified. The combined gate does not fit one
ordinary window, so scripts split by profile, in full/3100/5100 order. Each
profile keeps all six rounds in its exclusive window. Reserve the same budget
again only if the predeclared extension is called for. No selective repeats.
The 3,600-second per-launch timeout is a failure ceiling, not an expected time.

## Run, collect and score (lead only)

Run from the ticket worktree until merged, through `tools/run.py`:

```
python tools/run.py --name S13-01-primary-full --inputs tools/m4_gate.py tools/corpus.py tools/corpus -- powershell.exe -NoProfile -File ../_shared/S13-01/initial.ps1 -Profile full -AclVerified
python tools/run.py --name S13-01-primary-3100 --inputs tools/m4_gate.py tools/corpus.py tools/corpus -- powershell.exe -NoProfile -File ../_shared/S13-01/initial.ps1 -Profile 3100 -AclVerified
python tools/run.py --name S13-01-primary-5100 --inputs tools/m4_gate.py tools/corpus.py tools/corpus -- powershell.exe -NoProfile -File ../_shared/S13-01/initial.ps1 -Profile 5100 -AclVerified
python tools/run.py --name S13-01-score --inputs tools/m4_gate.py tools/corpus.py tools/m4_score.py -- python ../_shared/S13-01/runner/entry.py score --stage ../_shared/S13-01
```

Each pair is adjacent, with orders AB, BA, AB, BA, AB, BA (A donor, B GCC-KNC).
Rounds follow canonical program order. Pair IDs, start order, chronological raw
timestamps, launch-to-exit CLOCK_MONOTONIC_RAW duration, environment snapshots,
actual mapped runtimes, allocation/page observations, topology/affinity,
transport validity, build identity and checks remain in the raw records/captures.
The runtime probe emits start/end observations; PB/STREAM/codecs/SQLite also
record page/runtime observations while materializing their complete outputs.
Environment recording is included symmetrically in both process latencies.
NPB/HPCG retain their packaged checks and start/end runtime observations.

Independent host C references are compiled at -O0 -ffp-contract=off, with their
own initialized inputs, no donor linkage/output and independent scalar methods.
All eight PolyBench outputs use the frozen additive bound
`abs(actual-reference) <= 1e-8 + 1e-6*abs(reference)` after finiteness checks.
STREAM independently computes its exact initialization/warm-up/20-batch
recurrence and checks every element of a, b and c using that bound. It writes
all raw doubles before exit; the supervisor losslessly run-length encodes
equal consecutive values after timing, with 17 significant digits and complete
counts. No average or aggregate replaces an element check. PB donor agreement
is secondary information. Missing references block collection.

Correctness-only native launches precede each profile's scored block: PB-gemm
corrupts a live-out, STREAM corrupts one array element, NPB appends a failing
verification condition, HPCG appends invalidity, zlib corrupts a restored byte,
and SQLite corrupts one integer result. The same production validation path
must reject them and record evidence of injection; transport failures do not
count as rejection. Normal codec launches also exercise peer cross-decoding
and rejection of a corrupted compressed stream. Native controls are not votes
or timing samples. The host fixtures exercise these checker families too.
Each fresh process prints one start/materialize/end environment set, so a codec
launch carries up to three in process order; the timed workload's set is the
launch's, and a repeated or interleaved set in one process is an error.

If a completed block was checked by an older parser, the lead re-derives it
from its stored captures (`entry.py recheck --stage ../_shared/S13-01 --profile
full --block initial`). Captures and `-raw.jsonl` stay as written; the command
records changed checks in `-recheck.json` (held-out ones sealed), rewrites
`-checked`, `-controls` and `-done`, and later collection re-derives too.

The scorer re-collects the raw records, requires all launches and all controls,
and uses tools/m4_score.py's frozen 10,000-replicate random.Random(1514)
bootstrap, paired program medians, fixed 17-program median, one-sided 95%
lower bound, and strict >5% regression intervals. Full details and every
confirmed regression are sealed in `score.json`. The report lists every
program with median speedup <=1.00 on any model: held-out misses are found,
never tuned; development misses are defects. These owner-target findings do
not silently change ADR-0015's primary pass rule. The lead records known-cause
regression reviews and the decision; no automated report claims that review.
Optional sealed `reviewed-causes.json` maps model names to program names to
nonempty lead-reviewed diagnostic/ticket references, passed unchanged to the
frozen scorer. An absent review cannot explain away a confirmed regression.

## Exactly one extension, only on protocol trigger

After the complete initial three-profile score, the lead inspects the sealed
`extend` field. Only if true, run `extension.ps1` in full/3100/5100 order with
the same wrapper arguments and distinct names `S13-01-extension-<profile>`.
That script refuses execution unless the initial score calls for extension.
Orders are BA, AB, BA, AB, BA, AB for every program on every model. Then run:

```
python tools/run.py --name S13-01-score-extended --inputs tools/m4_gate.py tools/corpus.py tools/m4_score.py -- python ../_shared/S13-01/runner/entry.py score --stage ../_shared/S13-01 --extended
```

All twelve pairs enter the final calculation. No third block, deleted samples
or selective extension is supported. Attempted blocks cannot be overwritten;
invalid primary data blocks the gate. Any infrastructure recovery requires a
recorded lead decision, preservation of the aborted block, and a complete
replacement block under the same policy. Correctness failures use the owner's
repair policy, never infrastructure relabelling.

The scripts use the small frozen runner copied under `S13-01/runner`, so merging
and deleting the ticket worktree does not remove the entry point. The runner's
project tools/card_run transport remains the lead's coordinated transport. From
the main checkout after merge, replace `../_shared/S13-01` in the commands above
with `.work/_shared/S13-01`.

## Later labelled panels

The primary entry points run no -O3, -mphinix, PGO or OpenMP panels. These are
staged separately after S12-09 merges, using its docs/handoff/M4-PROTOCOL.md
exact lines. PGO training excludes held-outs and is separate from evaluation;
GCC-KNC OpenMP at 240 threads has 60/120 side panels and the explicit label
"the donor toolchain has no OpenMP runtime". They never change the primary
decision. No panel script in this primary handoff implies native qualification.
