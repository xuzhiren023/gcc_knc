S11-28 lead handoff (native results pending)
===========================================

Run `lead-memory.ps1` with Windows PowerShell. It launches eleven separate,
exclusive card_run jobs: KNC OpenMP 104 cubed at 56/112/224 threads on 3100 and
59/118/236 on 5100; 104 cubed at 224 threads on 3100 with MALLOC_ARENA_MAX=2;
96/88/80 cubed at 224 threads on 3100; KNC serial 104 cubed on 3100.
All use rt=0. Arena setting exists only in the one diagnostic child.
No S11-18 output is modified; its three existing HPCG binaries and runtime
libraries were copied into S11-28, as was its already-built launcher.

The supervisor samples the HPCG child's /proc/PID/status every 0.5 seconds,
printing VmPeak, VmHWM and VmSize in KiB. It stops a child after 60 seconds so
the round takes at most eleven minutes of workload plus transport (expected
under fifteen minutes). Each card_run has a 75-second timeout. Memory rows,
including failures, are written to memory-results.json; full samples and
reports are in memory/NN.stdout. These are correctness/memory diagnostics;
their times never enter scores. A timeout or missing sample is not a pass.
Sampled maxima may miss peaks between samples; VmHWM and VmPeak retain earlier
peaks while the process is alive. A timeout gives only a lower bound on the
completed program's peaks. The reference pilot took about 10-14 minutes per
successful 104-cubed process, so full correctness is unlikely within this
bounded diagnostic round. Longer completed checks may require another lead
round before a grid can be chosen. Do not claim full-run memory from a timeout.

Return memory-results.json and captures through the ticket. Select the largest
completed, valid grid with default arenas at 224 threads under 3100 whose
VmHWM is at most 0.8 * 5632 MiB = 4505.6 MiB (4613734.4 KiB).
The 3100 address-space ceiling is 5767168 KiB; 5100 is 7864320 KiB.
Compare arena=2 with default at the same grid/profile/density. Reduced VmPeak
and a completed arena=2 case support the arena explanation; lack of a full run
leaves it unresolved. Low sampled resident memory in an aborted run alone
does not establish that the whole workload fits physical RAM.
If a completed 104-cubed run demonstrates resident headroom but the default
profile aborts on reserved space, recommend a card_run profile that constrains
resident use separately from virtual reservations. card_run is unchanged here.
No grid is frozen and no arena hypothesis is claimed confirmed yet.

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

After the lead chooses a grid, update tools/corpus.py's INPUTS HPCG label and
staged hpcg.dat generation to that grid and rt=0, identically for every model
and compiler. These changes deliberately await measured memory, per ticket.

Then `lead-pilot.ps1 -Grid <chosen>` runs only HPCG: two alternating donor/KNC
serial pairs per full/3100/5100 profile, plus two KNC OpenMP launches at each
of three densities per profile. Thirty exclusive launches total; no memory
supervisor or arena override. Estimated card time at 104 cubed is 4-7 hours,
based on S11-18's successful launch durations; smaller grids may reduce this.
Per-launch timeout is 900 seconds. Each launch records full validity and actual
work, and collection rejects unequal serial work or any set count other than
one. Wall time uses the existing launch-to-exit CLOCK_MONOTONIC_RAW boundary;
HPCG GFLOP/s remains diagnostic. Outputs are pilot/NN.stdout and .stderr,
raw-results.jsonl, results.jsonl and status.json. Review every row and timings;
host checks cannot establish that every launch passes or that build times vary.

Host status: unequal-work fixture checks passed; monitor cross-built and linted.
No card job was started by the engineer. Neither memory nor native correctness
nor pilot timing acceptance has been established.
