# ADR-0004: KNC registers and the scalar FP ABI

**Status:** Accepted. **Date:** 2026-11-03. **Decider:** Claude. **Source:**
`docs/research/knc-register-design.md` (S2-01), every claim cited there; the lead checked
`i386.cc:552-566`, `constraints.md:81-95` and the donor's `i386.c:4569-4578` against it.

## Context

GCC 16 makes the vector registers reachable only with SSE, `zmm16`-`zmm31` and `k0`-`k7` only
with AVX-512F, and its SysV argument, result and varargs code requires SSE. KNC has 32 `zmm` and
8 mask registers but neither SSE nor AVX-512 (ADR-0002). The donor's convention, measured on
2026-11-02, is SysV with `zmm` lane 0 in place of `xmm`, x87 bodies, and transfers through memory
(`docs/sprints/SPRINT-02.md`). The donor got there by widening gates to `SSE || KNC`, and two of
its shortcuts are wrong: its mode hook still rejects `zmm16`-`zmm31` without AVX-512, and its
`k2` reservation sits in a branch that never runs on KNC.

## Decision

1. **Registers.** Under 64-bit `TARGET_KNC`, all 32 vector registers and `k0`-`k7` stay
   accessible, reusing GCC 16's existing hard-register numbers and classes. No SSE or AVX flag is
   set to get them. `ix86_hard_regno_mode_ok` gets an early KNC return so the generic fallback
   admits nothing else.
2. **Modes, Sprint 2.** Vector registers hold SF, DF, SI, DI, TI, TF, and XI for full-register
   transport with 64-byte aligned storage. Masks hold HI only. No packed vector mode is advertised
   until E3 adds it with its moves (ADR-0002, point 3).
3. **Constraints and patterns.** New KNC constraints map to the existing classes. `x`, `v`, `k`
   and `Yk` stay disabled on KNC, and no SSE pattern condition is widened. New patterns go in
   `imci.md` under `TARGET_KNC` and print `zmm` operands with `%g`.
4. **ABI.** KNC exceptions go only into the SysV gates for argument registers, the vector
   argument budget, result registers and varargs. SysV classification is kept: SF and DF in lane
   0 of `zmm0`-`zmm7`, results in `zmm0`, aggregates by eightbyte. The varargs save area keeps
   16-byte slots, `fp_offset` 48 and the `%al` test, saved through TI transport. The MS ABI is not
   touched. `long double` stays x87.
5. **Calls.** Every `zmm` and `k` register is caller-saved, as in the donor and GCC 16's SysV
   tables.
6. **Scratch.** A transfer gets an allocated general-register scratch and an HI mask pseudo with
   explicit definitions and uses. No hard-coded `k2`, no reserved `%eax`, and no push/pop
   fallback. A scratch must not destroy a live `%al` before a variadic call or a live `%rax`
   result.
7. **Budget.** The estimate for shared i386 edits in S2-02 to S2-05 is about 220 lines, which with
   the 45 already used leaves 35 of M1's 300. Each implementing ticket reports its count; a
   ticket that would go past 255 stops and asks the lead.

## Consequences

- Every T1 test in S2-02 to S2-05 checks output against an instruction allowlist (IMCI transfers,
  unsuffixed `kmov`, x87), not a blacklist, and also rejects `xmm`/`ymm` operands, AVX-512
  mask instructions and per-function options that turn SSE on.
- The six risks in the design note's last table are obligations of the implementing tickets: SSE
  move alternatives, mask instruction forms, enabled flags, scratch and `%al` liveness,
  misaligned spills, and the zero-call-used-regs path.
- The 300-line M1 limit will be tight. If S2 uses most of it, M1 compares against a separate
  backend early, as `docs/PROJECT_PLAN.md` intends.
