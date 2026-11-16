# Plan after M4: Sprint 14 to Sprint 17 (M5, M6)

Lead plan, 2026-11-15. Inputs: the verified history (S0-S13), the M4 gate (S13-01, full profile only by owner decision),
the GPT Pro triage (`docs/research/gpt-pro-2026-11-15-triage.md`), `model-first-optimization-method.md`,
`knc-twin-trial.md`, `phi-literature-survey.md`, `knc-reference-gaps.md`, `system-tuning-playbook.md` and
`code-style-coverage.md`. GitHub issues mirror this plan; tickets in `work/tickets/` stay the working channel.

## Where we stand

- M1-M3 accepted; M4 measured on the 7120 full profile only (owner cancelled 3100/5100). M0 was "adjust", never accepted.
- Strong on regular numerical code: PolyBench 1.5-3.9x, STREAM 3.1x, NPB-CG 2.7x over GCC 5.1.1. Weak on everything else:
  NPB-EP/IS 1.10x, zlib about 1.03x, SQLite 1.04x, HPCG about 1.07x.
- Sprint 12's three themes closed with no compiler change. Only S12-31 (HPCG) moved a program. We picked themes by
  hypothesis and proved them wrong after building probes; the model-first method (S13-05) and knc-twin (S13-06) now
  exist to bound a theme before we spend a sprint on it.
- Open defects: two -O3 ICEs (S12-34, S12-38), one slower-than-GCC-5.1.1 case (S12-42), zlib -2.5% (minor), double log
  at one thread per core (minor). 16/32-byte generic vectors still scalar. No KNC intrinsics header. No one-flag PGO.
- Portability is eroding: forward-port conflicts 14 (upstream master) and 4 (gcc-16 branch), from 2 and 0 at M1; 794
  changed lines in shared i386 files.
- Tools are Windows-bound (card_run uses Windows OpenSSH, several tools expect `.exe`); the owner's Z840 is Linux.
- Records drift (CURRENT_STATE stale since 2026-11-08 in places); staged evidence went unread (S12-12 batch).

## Principles for the next milestones

1. **Correct before fast.** A general-purpose compiler with open ICEs and a slower-than-donor case is not general.
2. **Model before building.** Every optimization ticket bounds its gain with model-first (and knc-twin for one core)
   before implementation; a theme whose bound is under 5% whole-program is not started.
3. **Breadth is measured, not claimed.** The code styles we do not cover (N amateur, C abstraction-heavy C++, G generated)
   get scored programs, not only unscored checks.
4. **Portable and reproducible.** Anyone builds from the public repos on Linux; the card tools run from a Linux host.
5. **Small shared footprint.** Every sprint that touches shared GCC files reruns the forward-port drill and does not raise
   the conflict count.
6. **Read what we stage.** A card window's outputs are analysed in the same sprint, or the job is not staged.

## M5 - Broad and correct (Sprints 14-15)

Pass rule (accepted by the owner 2026-11-16, frozen in ADR-0016, which governs where this summary differs):
- **Correctness:** zero known ICEs and zero known wrong-code at -O2 and -O3 on the GCC torture and vect suites and the
  corpus; execute suite all pass on the card.
- **Breadth:** a widened corpus of at least 25 programs that adds the N, C and G styles (S11-20 Q1-Q6 generality set as
  scored programs, WRF, FFTW generic-simd, an LLM GEMV/decode kernel), median speedup one-sided 95% LB >= 1.25x over
  GCC 5.1.1 on the 7120 full profile, and no program slower than GCC 5.1.1 beyond its measured noise.
- **Reproducible:** both repos public; a fresh clone builds on a Linux x86-64 host by `docs/BUILDING.md` to IMCI
  assembly and, with the MPSS sysroot, to card binaries; card_run works from that host.

### Sprint 14 - correctness, method and portability

| Item | Ticket | Why now |
|---|---|---|
| Close M4: score, report, known limits, M4 tag | S13-01, S13-03 | finish the milestone |
| Write M5 definition and corpus additions (ADR-0016, M5-DEFINITION) | new (lead) | nothing is measured until frozen |
| Fix ICE: truncating V16QI store | S12-34 | correctness |
| Fix ICE: SLP vect-pr123221 at -O3 | S12-38 | correctness |
| Never slower than GCC 5.1.1: small sparse row loops | S12-42 | owner rule |
| -O3 torture and vect sweep on the card, triage every failure | new | find the next S12-34/38 before users do |
| Analyse the S12-12 card experiments (G04-G08, G10) | new | staged evidence never read |
| Forward-port drill: classify the 14/4 conflicts, shrink shared i386 changes | new | portability principle |
| Card tools from a Linux host (card_run ssh, `.exe` assumptions, gcc_build empty tree, install order) | new (S13-04 rest) | Z840 is Linux |
| Measurement method: per-region properties, lower bound, four outcomes | S14-04 | method for M5 |
| knc-twin calibration from staged native requests; reconcile 11 twin/yaml values | new (with owner's twin session) | make the model decision-grade |

### Sprint 15 - breadth and performance, model-first gated

| Item | Ticket |
|---|---|
| 16/32-byte generic vectors in zmm low lanes (FFTW generic-simd), ADR-0014 amendment first | S14-01 |
| Scored N/C/G programs (Q1-Q6 promoted) and paired source forms | S14-05 |
| Scheduler model completeness (bypasses, folded operands, pairing by encoding) | S14-03 |
| SMS on KNC: bound with knc-twin, then doloop pattern if the bound is worth it | S14-02 |
| Theme never tried: scalar addressing, control and call overhead (S11-20 rank 1) | new |
| Latency-aware scalar loops | S12-27 |
| Branch cost and if-conversion thresholds | S14-06 |
| C++: LTO/devirtualization on k1om | S14-07 |
| Sparse: land S12-30 with the column-span rule; Fortran NPB-CG | S12-30, S12-40 |
| libgomp per-region density | S13-02 |
| Quantized GEMV kernels (LLM decode, owner priority) | S14-08 |
| M5 measurement on the widened corpus | new |

Order inside Sprint 15: model every performance item first (one short model ticket per theme), then implement only
those whose bound clears 5% whole-program on at least two corpus programs.

## M6 - Release (Sprints 16-17)

Pass rule (proposed): a tagged release of both repos; binary toolchain packages for Linux x86-64 hosts (compiler,
binutils pointer, libknc_vmath; no MPSS sysroot); `docs/` complete (BUILDING, USING, known limits, update procedure for
GCC 16.x point releases); release notes with the M4/M5 numbers; the owner's BOINC-on-card acceptance test as the final
user check (context, `project-boinc-final-uat`).

| Sprint | Items |
|---|---|
| 16 | KNC intrinsics: ADR-0013 inventory ticket, then the header from the inventory and the ISA manual only; one-flag PGO (owner 2026-11-13); `-mphinix` contents chosen by corpus measurement (BACKLOG E7-14); vmath accuracy contract (S12-20) |
| 17 | Release engineering: packages, update procedure, GCC 16.x forward-port of the release, KNC vs Z840 host comparison for the notes (S14-09), BOINC UAT support |

## Owned elsewhere (not GCC-KNC scope)

PhiNix (OS, persistent SCIF dispatch, LWK vs Linux), PhiChat (LLM serving, speculative decoding, batching), PhiWeather
(WRF decomposition and timing): listed in `docs/research/for-the-other-agent.md`.

## Process changes carried forward

Close the open rows of `docs/research/practice-lessons.md` in S13-03: CRLF pre-commit check, card smoke test after any
card-side change, research tickets end with a digest step, staged jobs analysed in-sprint, approve-time registry
conflicts (S12-03), long card runs detached from the lead session (S13-01 recovery 2). Lead delegates all work to
engineers or subagents (owner, 2026-11-15).
