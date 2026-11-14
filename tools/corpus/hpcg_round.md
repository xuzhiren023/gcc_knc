S11-28 lead handoff: frozen 104 cubed, one benchmark CG set
========================================================

The lead's 2026-11-13 ticket answer settles the grid at 104 cubed for every
model and compiler. hpcg.dat uses runtime zero; tools/corpus.py now stages
this input for both full and selective HPCG staging. The input label is
HPCG-3.1-104x104x104-rt0. No HPCG source or compiler build changed here.

Lead memory round (2026-11-13, about 10.5 minutes)
------------------------------------------------

Source: memory-results.json and memory/NN.stdout in this staging directory.
Lead log: .work/_state/logs/S11_28_memory-20261113-145740.log.
The supervisor sampled VmPeak, VmHWM and VmSize every 0.5 seconds. Values
below are KiB, directly from the returned results; exit 124 is the 60-second
diagnostic timeout, exit 134 is bad_alloc. No case completed correctness.

| Profile | Threads | Grid | Arenas | Exit | VmPeak | VmHWM | VmSize |
|---|---:|---:|---|---:|---:|---:|---:|
| 3100 | 56 | 104 | default | 124 | 4958676 | 920212 | 4958676 |
| 3100 | 112 | 104 | default | 134 | 1470288 | 510492 | 1470288 |
| 3100 | 224 | 104 | default | 134 | 2550476 | 674652 | 2550476 |
| 5100 | 59 | 104 | default | 124 | 5180036 | 915532 | 5180036 |
| 5100 | 118 | 104 | default | 134 | 6336332 | 694960 | 6336332 |
| 5100 | 236 | 104 | default | 134 | 2647376 | 670960 | 2647376 |
| 3100 | 224 | 104 | 2 (diagnostic) | 124 | 2817620 | 905436 | 2817620 |
| 3100 | 224 | 96 | default | 134 | 5767160 | 651552 | 5767160 |
| 3100 | 224 | 88 | default | 124 | 5724320 | 543692 | 5724320 |
| 3100 | 224 | 80 | default | 124 | 5593064 | 404384 | 5593064 |
| 3100 | 1 | 104 | default | 124 | 937616 | 921280 | 937616 |

The lead confirmed the arena explanation: at 104 cubed / 224 threads under
3100, default arenas abort whereas MALLOC_ARENA_MAX=2 survives the window.
The maximum observed VmHWM is 921280 KiB (899.7 MiB), below the 3100's
20%-headroom threshold of 4613734.4 KiB (4505.6 MiB). Smaller grids do not
solve the virtual reservation problem: 96 aborts, and 88/80 approach the
5767168 KiB RLIMIT_AS ceiling. The lead therefore retained the largest tested
grid, 104, and assigned the resident-memory profile correction to S11-29.
Recommend limiting resident memory independently of reserved address space;
card_run is unchanged by S11-28. The arena setting is diagnostic only and
must never enter the primary environment.

These are bounded samples: aborted samples may miss the last allocation and
timeout VmHWM is a lower bound on whole-run peak memory. The grid choice and
arena conclusion above are the lead's explicit decision, not a claim that
these diagnostics completed TestCG, TestSymmetry or TestNorms. The lead subsequently completed the native pilot after S11-29; see below.

Source confirmation (HPCG 3.1, shared corpus-build/sources/hpcg-3.1):
- ReadHpcgDat.cpp accepts zero runtime (only negative values are replaced).
- main.cpp:85 enables QuickPath for zero; :186 reduces the repeated reference
  SpMV/MG calls from ten to one; :316-317 computes exactly one benchmark CG set.
- main.cpp still calls TestCG, TestSymmetry and TestNorms. TestNorms.cpp divides
  variance by its sample count, so one finite sample has zero variance.
- ReportResults.cpp:300-318 emits per-set and total reference/optimized
  iterations. Sets are derived from both total/per-set quotients, which must
  be positive integral and identical. The report has no standalone set field.
- ReportResults.cpp:371-399 marks correctness valid when all checks pass, even
  below the 1800-second submission duration; the report then warns about that
  duration. This work is a compiler comparison, not an HPCG submission.

Lead pilot (after S11-29)
------------------------

Run lead-pilot.ps1 with Windows PowerShell (104 cubed is now the default and
only allowed grid). It runs only HPCG: two alternating donor/KNC serial pairs
per full/3100/5100 profile, plus two KNC OpenMP launches at each of three
densities per profile. Thirty exclusive launches total, one card_run each;
no supervisor or arena override. Expected card time is 4-7 hours, based on
S11-18's successful 104-cubed launches. Per-launch timeout is 900 seconds.
No S11-18 files are modified. Existing binaries, libraries and launcher
are staged here; no engineer card job is authorized.

Each report must pass TestCG, TestSymmetry and TestNorms. Collection records
reference/optimized iterations per set and totals, derives set counts, and
rejects anything other than one set or unequal work in a serial pair.
Wall time uses launch-to-exit CLOCK_MONOTONIC_RAW; GFLOP/s is diagnostic only.
Outputs: pilot/NN.stdout and .stderr, plan.json, raw-results.jsonl,
results.jsonl and status.json. The lead returned the thirty completed launches and the staging rerun described below.
Host fixtures and native results are recorded separately.

Host unequal-work fixtures already passed in the preceding session (red
commit 75ce3838; implementation ede7b91c). The memory supervisor was already
cross-built and linted. Do not rerun the memory round or rebuild to launch
the pilot. The prior red-first evidence remains unchanged.


Returned native pilot (2026-11-14)
---------------------------------

The lead ran the pilot 02:15-07:40 EST (325 minutes), then reran launch 27
at 08:06. Log: .work/_state/logs/S11_28_pilot-20261114-021459.log.
The first attempt at 27 failed during SSH upload before HPCG started;
this is an infrastructure failure, not a native failure. Its captures are
pilot/27.stdout and pilot/27.stderr. The successful replacement is
rerun27.json with pilot/27r.stdout and pilot/27r.stderr (589.441 seconds).

| Profile | Run | Donor serial (s) | KNC serial (s) | KNC / donor | KNC OMP 1/core (s) | 2/core (s) | 4/core (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| full | 0 | 765.986 | 771.323 | 1.00697 | 568.735 | 582.155 | 544.404 |
| full | 1 | 766.324 | 772.794 | 1.00844 | 569.480 | 563.332 | 530.073 |
| 3100 | 0 | 772.886 | 782.841 | 1.01288 | 569.961 | 565.163 | 548.715 |
| 3100 | 1 | 768.728 | 780.126 | 1.01483 | 574.329 | 562.475 | 543.194 |
| 5100 | 0 | 771.454 | 783.899 | 1.01613 | 573.857 | 579.223 | 553.093 |
| 5100 | 1 | 778.779 | 773.041 | 0.99263 | 589.441 | 570.862 | 550.301 |

Times are launch-to-exit CLOCK_MONOTONIC_RAW; run indices are zero-based.
The last row uses 27r for OpenMP 1/core. Every completed capture passes the
required correctness report sections and reports VALID with one CG set.
All six serial pairs have reference 50 and optimized 51 iterations (both
per-set and total). OpenMP optimized iterations vary between 50 and 51,
so that panel remains diagnostic. All profiles use 104 cubed and rt=0.

These actual wall times differ in every serial pair: KNC is slower in five
pairs (KNC/donor 1.007-1.016), faster in the final 5100 pair (0.993).
HPCG's GFLOP/s rating is lower for KNC in all six pairs (0.0845-0.0847
versus donor 0.0860-0.0863); ratings are diagnostic only, never the score.
No repeated timing run was requested.

Acceptance evidence:
- [x] Red-first recorded-report fixture test: 75ce3838; green ede7b91c.
- [x] Returned memory table, arena diagnosis, and lead's frozen grid decision.
- [x] Lead pilot: all 30 intended launches complete and pass after one upload
  retry; six serial pairs have equal work and differing build wall times.
- [x] Final results reconciliation: the lead ran finalize-pilot.py at
  aad1ae22 on 2026-11-14 at 08:46 EST and reported PASS. results.jsonl
  retains launch 27's infrastructure error marked superseded_by 27r and
  appends 27r: 31 attempts, 30/30 effective launches. status.json is pass.
  raw-results.jsonl retains the original 30 attempts.

The staged finalize-pilot.py validates the returned captures, then performs
that reconciliation and writes status for 30 successful intended launches
and 31 recorded attempts. The engineer's first write was denied; the lead
completed the protected update and refreshed staged README.md.
Successful finalization log:
.work/_state/logs/S11_28_finalize_pilot-20261114-084648.log.
No engineer card jobs or GCC builds ran.
