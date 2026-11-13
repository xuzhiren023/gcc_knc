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
these diagnostics completed TestCG, TestSymmetry or TestNorms. Full native
correctness and timings still require the pilot after S11-29 lands.

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
results.jsonl and status.json. The lead must review all thirty launches,
equal paired work and wall-time differences between builds. These native
acceptance results are pending; host fixture success is not native success.

Host unequal-work fixtures already passed in the preceding session (red
commit 75ce3838; implementation ede7b91c). The memory supervisor was already
cross-built and linted. Do not rerun the memory round or rebuild to launch
the pilot. The prior red-first evidence remains unchanged.
