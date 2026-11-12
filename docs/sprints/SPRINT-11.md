# Sprint 11: data in and out at the link limit, bandwidth for LLM decode, corpus harness (Milestone M4, part 1)

**Status:** started 2026-11-12 (written by the lead on the owner's request, after the sprint's first tickets ran).
Engineers: Codex through `tools/dispatch.py`; the lead builds GCC and runs every card job (owner 2026-11-12).

**Goal:** three things are demonstrably true at the end.
1. **Transport at the link limit.** Bulk data moves between the host and the card at the maximum of this card's
   PCIe link (Gen2 x4: about 1.6-1.7 GB/s of data per direction), both ways, every transfer checksum-verified,
   and `tools/card_run` and `harness/card/run_suite.py` use that method with SSH as the fallback. Owner
   2026-11-12: "as long as we proven to max out pcie 2.0x4, we are good".
2. **A measured route to higher memory bandwidth, LLM decode first.** The weight-streaming GEMV workload and the
   STREAM classes are measured on the card with long samples; each lever that moves them is known, and the
   winners are written as compiler and runtime stories for Sprint 12. Target 264-299 GB/s (75-85% of 352);
   reaching it is not a sprint exit condition, measuring the way there is. Owner 2026-11-12: this "directly
   impact[s] on fast llm decode".
3. **The M4 corpus can be run.** Every corpus program builds with GCC 5.1.1 (the donor) and GCC-KNC, runs on the
   card with frozen inputs and a correctness check, and reports time per program in one command, so Sprint 12 can
   profile and Sprint 13 can decide M4.

| Ticket | What | State (2026-11-12) |
|---|---|---|
| S11-01 | Transport inventory, DMA comparison, measurement tool | done |
| S11-03, S11-04, S11-07 | Tool fixes: card `/tmp` path, firewall (host connects out), listener timing | done |
| S11-10 | Runner options (repeats, sizes, loads, concurrency) and two runner bugs | doing |
| S11-02 | card_run and run_suite use the measured best method, SSH fallback | waits for the link-max numbers; lead writes acceptance |
| S11-05, S11-06 | Bandwidth research, benchmark fixes, sweeps 1-2 (read 186, rmw 179, write 170, triad 168, copy 164 GB/s) | done |
| S11-09 | GEMV weight streaming for LLM decode (fp32, int8, fp16) | waits for its card sweep |
| S11-08 | `-Wknc-unsafe-cbrtl` usable in `#pragma GCC diagnostic` | done |
| S11-11 | Corpus run harness: drivers, frozen inputs, correctness checks, both compilers, one command | new |
| S11-12 | Sprint 11 batch check: full suite on the card, x86, forward-port drill, sweeps | new, last |

Card measurements so far (2026-11-12): SSH stream 11/17 MiB/s up/down, raw TCP 174/320 MiB/s, SCIF DMA read
1.67 GB/s card-to-host (at the link limit) and 1.35 GB/s host-to-card at 64 MiB; SCIF messages 0.1-0.2 MiB/s.

**Out of scope:** an x16 slot or other hardware change (owner's call); ECC, clock or MPSS configuration changes
(owner decisions, listed with their expected gain by the research tickets).

**Cap:** two weeks from 2026-11-12.
