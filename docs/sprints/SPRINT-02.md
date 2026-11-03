# Sprint 2: scalar C with the KNC ABI

**Goal:** GCC 16 compiles scalar C, float and double included, to the KNC calling convention, so
its objects link and interoperate with the donor's in both directions, and it builds its own
static `libgcc`. Milestone M0 was decided as adjust (owner, 2026-11-02): GCC 16 stays the base,
and Sprint 2 runs on this Windows/Cygwin host.

**Cap:** two weeks. The card is on the owner's hold, so every ticket proves what it can on the
host (T0 to T2) and lists its native (T3, T4) checks separately, to run once the card is free.
A ticket is done on host evidence; its native line stays unticked until then, as S0-04's did.

**The donor's convention, measured by the lead on 2026-11-02** (donor `-O2 -S` of small
functions): it is the x86-64 SysV convention with `zmm` in place of `xmm`. `float` and `double`
arguments go in lane 0 of `zmm0` to `zmm7`, the ninth on the stack; results come back in `zmm0`.
Structs split by SysV eightbyte classes (`{double, float}` uses `zmm0` and `zmm1`). Varargs callers
set `%al` to the count of vector registers used. Bodies are x87: values move by `vpackstorelpd` or
`vpackstorelps` under a one-lane mask to the stack and are loaded with `fld`, and go back with
`vbroadcastsd` or `vbroadcastss`. The mask comes from `movl $1, %eax; kmov %eax, %k2`.

The work is in tickets, in `work/tickets/S2-*.md`, in this order:

| Ticket | What it delivers |
|---|---|
| S2-01 | Design: how GCC 16 exposes `zmm` and `k` registers under `-march=knc` with SSE off (research; the lead writes the ADR) |
| S2-02 | `float` and `double` arguments and results in `zmm` lane 0, x87 bodies (E2-01) |
| S2-03 | Varargs and callbacks with the donor's register save area (E2-01) |
| S2-04 | Scalar transfers through memory and mask scratch, and the secondary-reload reproducer (E2-02) |
| S2-05 | x87 compares for NaN, signed zero and unordered, and 64-byte `zmm` spill alignment (E2-03) |
| S2-06 | Atomics without `cmpxchg16b`, spin hint by `delay` (E2-04) |
| S2-07 | GCC 16 builds its own static `libgcc` for `k1om`, removing the donor bridge (E2-05) |
| S2-08 | `hello`, scalar FP and `printf` on the card, and a first `c-torture/execute` baseline (E2-06); needs the card |

## Sprint exit

- [ ] S2-01 to S2-07 approved and merged, or explicitly returned to the backlog
- [ ] S2-08 done, or returned to the backlog if the card is still on hold
- [ ] `CURRENT_STATE.md` updated, and the GCC `knc` branch is ready for the owner to push
- [ ] Sprint 3 refined from E3
- [ ] Three-line retro below

## Retro

*(at close)*
