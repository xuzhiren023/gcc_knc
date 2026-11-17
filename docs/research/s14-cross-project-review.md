# What other projects already proved for GCC-KNC (review, 2026-11-16)

Lead review at the owner's request: findings by PhiWeather, knc-boinc, knc-twin and PhiChat, checked against the
Sprint 14-17 plan (`docs/PLAN-M5-M6.md`), ADR-0016 and the open board. Three read-only reviewers collected them; the
lead spot-checked the numbers marked (checked) against the cited files. Peer folders are read-only and timings there
are GCC 5.1.1 images unless marked otherwise. Paths: PW = C:/Users/xuzhi/Documents/PhiWeather, KB = .../knc-boinc,
KT = .../knc-twin, PC = .../PhiChat, CC = .../card-coordination.

## Done or largely done by another project

| Our item | What they established | Source | Effect on our work |
|---|---|---|---|
| S14-30 WRF gap vs Sirocco | Plain and patched GCC-KNC WRF both 1.20x of Sirocco over 25 h (5.006 vs 4.171; 5.012 vs 4.166), accuracy guards all held. Sirocco's source-level gains not in our arms: get_fieldstr hoist 4.77% (checked), halo/nest batching 3.63%, IMCI memcpy 2.5%; hand kernels K4/K6/K7/K9 each 4-5% when added. `-fstack-arrays` -0.23% (no effect). | PW twin and S1126 reports; PW/artifacts/release/wrf-knc-sirocco-2.0/evidence/hoist/SPLIT_RESULT.md; PW/docs/implementation/SCALAR_DYNAMICS_VECTOR_OPTIONS_20261112.md | Steps 1 and 3 mostly answered: at least 8 of the 20 points are source/runtime work, heap arrays are not a cause. S14-30 shrinks to the codegen remainder. |
| S12-12 card experiments (page backing, prefetch, allocator) | 2 MiB heap on WRF: 0.42%, below noise. Short rows 8.0 GB/s, 19.5 with vprefetch0 (2.4x) (checked). malloc/free 1.1-1.6% of wall. | PW KNC_DECK_OPTIMIZATION_CYCLE_20261112.md; CC/wrf-hot-loops-for-gcc-knc.md section 5 | Three of S12-12's open questions have WRF-scale answers; analyse only what remains. |
| S14-03 scheduler model | Twin rules measured on card: x87 issues alone, NOPs never pair, a load issues 4 cycles after a store, load+store pair; 22/22 x87 row variants ranked right. Scheduler-off HPCG -7.9% predicted by the twin (already fixed by S12-31 rule A). | KT references/validation.md, parameters.md; KT tests/heldout_native/s12-31-hpcg-104 (checked) | Pairing and bypass table exists; S14-03 copies it instead of measuring. |
| S14-44 lane-0 scalar | x87 add/mul latency 3, vector 4, x87 div 38-39; fcom+fnstsw chain ~7 ticks/site at 1 thread, ~13 at 2. Ready repros: nbMakeTree, mixed-dwarf generator. | KT parameters.md; KT w11-x87 measurements; KB docs/vector-gravity.md | Step 1 inputs exist; the case for lane 0 rests on compares and transfers, not add/mul. |
| S12-20 vmath contract | Users need a proven error bound (S8-05 demands a rigorous bound with safety factor and exact fallback), not a measured max ULP. Card glibc pow up to 318 ULP off; crlibm 6,272/6,272 bit-identical (checked). | KB work/tickets/S8-05.md; KB docs/sprints/sprint-1.md | The contract's requirements are now specified by a real user. |
| S14-08 quantized GEMV | PhiChat production Q4/Q5/Q6 kernels are the FP-dequantize form; no VPMADD231D or VPERMD anywhere. Real decode is ~8% of read bandwidth (11.5-14.8 GB/s of weights). Twin card row: fp32 GEMV 125 GB/s of weights vs 186 GB/s read. | PC/tools/native-runner/context-matrix/panel8.S; PC/docs/DECODE3.md; KT validation.md | Baseline form and roof known; S14-28/S14-08 only need forms (c) and (d). |
| M5 corpus (ADR-0016) | MilkyWay N-body pinned 1.96 builds with GCC-KNC, bit-identical to x86 on three cases; phase timers; scalar (N) and vector-walk (G) builds. | KB docs/sprints/sprint-1.md, work/tickets/S8-01.md | A ready scored-program candidate with an oracle (owner decision: ADR-0016 lists the units). |

## Evidence that changes a plan item

- **S12-27 (latency-aware scalar loops): weaker case for unroll/interleave.** WRF x87 chains are dependency bound
  (RecMII 1,116 vs ResMII 412) (PW twin STUDY s5); the gain is in vectorizing or hoisting, not interleaving.
- **S13-02 (per-region thread density): stronger case.** WRF ~9,850 regions per rank-step, barrier wait 45-58% of
  thread samples, fork/join 2.4-2.5% of wall; PhiChat runs 2/core for small-model decode and 4/core for large and
  prefill; WRF 3/core is 17-45% slower. knc-boinc's parallel tree build was 5x slower on the card (cause open).
- **S14-06 (branch cost): stronger at 4 threads/core.** Fixed-direction branch 6.2 ticks at 1 thread, 17.0 at 4;
  random 27.8 at 4 (KT parameters.md).
- **Bandwidth target 264-299 GB/s: independent evidence against.** PhiWeather and PhiChat both see 170-190 GB/s as
  the practical read limit; no project exceeds 190.
- **One-flag PGO: low value on WRF.** +0.78% (noise), changed FP sequences in 302/484 functions. Keep PGO scoped to
  branchy integer code; owner's one-flag item stands but its WRF benefit should not be promised.
- **S14-05 paired forms:** knc-boinc's vector walk gained only 2% (pointer-chase bound) though the twin predicted busy
  lanes; a G form is not automatically faster.

## New compiler work found

1. **Unswitching on loop-invariant tests does not fire** (`-funswitch-loops` is in -mphinix): WRF
   `sixth_order_diffusion` stays x87; a source-specialised version runs 6.1x fewer instructions per point (202.7 to
   33.2, exact) (checked, PW twin STUDY s11). Ceiling 2.5% of WRF wall when D6 is on. Draft S14-52.
2. **Short-tile masked tails lower to gather/scatter retry loops** (13 vscatterdps, 28 gathers in rk_update_scalar)
   (checked) and 32-40 byte zero loops become `memset` calls. Masked `vpackstore`/`vloadunpack` lowering and no
   memset for tiny rows. Issue #32; draft S14-54.
3. **No prefetch for pointer chasing** (knc-boinc force walk 4-5x above model): S14-48, dispatched.
4. **knc-machine.yaml vs knc-twin disagree**: scatter completion (null vs 11.2 cycles/line), branch mispredict (null vs
   5), x87 compare chain (unmeasured; twin assumed 3, wrong by 31-49%). This is the plan's "reconcile twin/yaml" item;
   S14-50.
5. **Twin calibration at 2-4 threads/core is weak** (scatter -44/-48%, div10 -19 to -27%): knc-twin's T1-09 owns it;
   the eight wrf-n8 card rows (approved window) feed it.

## Nothing found for

C++/LTO (S14-07), Linux-host build (S13-04), 16/32-byte generic vectors (S14-01), SMS (closed no-go by S14-26), the
intrinsics header, DMA overlap beyond PhiChat's "8 copy threads, 1.5 GB/s goal unmet" (S12-05). No user-found
GCC-KNC wrong-code defect in any project.
