# M4 result: broad optimization (S11-S13)

Decision 2026-11-16: **pass**, with one documented known limit. Gate: S13-01, GCC-KNC `knc` b2ce6a9eebf (target
libraries rebuilt from the same compiler) vs GCC 5.1.1, strict serial `-O2 -march=knc` vs `-O2` (SQLite donor
exception per ADR-0015), 17 programs (14 development, 3 held-out unsealed at the gate), six AB/BA pairs each.

| Measure | Result |
| --- | --- |
| Profile | 7120 full card only. The owner cancelled the 3100 and 5100 blocks (ADR-0015 amendment 1); the S11-15/S11-28 pilots showed the same direction there |
| 17-program median speedup | **2.194x**, one-sided 95% lower bound **2.162x** (bar 1.25x), CI 2.137-2.223, bootstrap 10,000 draws, seed 1514 |
| Correctness | every launch passed; all six checker families rejected injected corruption |
| Confirmed >5% regression | bzip2 (held-out) 0.927x, CI 0.900-0.936: known cause reviewed (below) |
| Owner target "faster than GCC 5.1.1 on every program" | one miss: bzip2 (held-out, found, never tuned) |

Per-program speedups (7120): PB-cholesky 3.78, PB-atax 3.14, PB-ludcmp 3.08, PB-durbin 2.82, STREAM 2.78,
PB-gemm 2.67, PB-heat-3d 2.25, PB-jacobi-2d 2.20, PB-adi 2.19, NPB-CG 1.99, NPB-MG 1.58, NPB-IS 1.15, NPB-EP 1.09,
HPCG 1.08, zlib 1.06, SQLite 1.05, bzip2 0.93. Regular numerical code gains 1.6-3.8x; integer, branchy and
scalar-FP programs gain 5-15%.

**Known limit: bzip2 0.927x.** Cause (docs/research/m4-bzip2-diagnosis.md, lead-authorized held-out diagnosis,
exposure recorded): KNC tuning prices mask-to-GPR moves below a GPR move, so the register allocator keeps a byte in
k0 inside mainGtU (16 `kmov` per iteration plus address-generation stalls), about 75% of the gap; GCC 16 also
loses compare-load folding in a merged return block. Owner 2026-11-15: M4 passes with bzip2 as a documented known
limit; fix as a must-fix in M5 (S14-16, S14-17). Other accepted minor limits: zlib gave back 2-3% to S12-31 (still
1.06x), double vector log slower than scalar at one thread per core, S12-34/S12-38 -O3 ICEs, S12-42 small sparse
loops (likely fixed by S12-31; card rerun pending).

**How the measurement went.** Four full blocks were lost to infrastructure, not workloads: card_run false alarms,
a codec parser bug, ssh failing when the lead session exited, and a DMA helper deadline under host build load. The
fixes (SSH-only transfers, transport retry, adopt-and-resume of timed launches, detached runs) are in ADR-0015
amendment 1 and S13-01; the scored block is aborted-2's 106 timed launches plus 104 resumed launches. Lessons:
docs/research/practice-lessons.md (2026-11-15 rows).

Not scored (labelled panels, not run at M4 by owner choice): -O3, -mphinix, PGO, OpenMP at 240 threads.
