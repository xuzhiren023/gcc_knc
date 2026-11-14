# Correctly rounded vector division and square root on KNC (S5-03)

Research for backlog E4-03 and ADR-0003 point 4. Read only: no GCC build and no card job.
Date 2026-11-05. GCC references are to the shared checkout, branch `knc` at `c759f17f1b9`.
"Manual" means Intel 327364-001, the Xeon Phi coprocessor ISA reference
(`.work/_shared/intel-327364-001-xeon-phi-isa.txt`). Page numbers are the printed page numbers.
Some manual tables lost their symbols (the infinity sign and minus sign) in the text conversion.
Where I read a garbled table, I say so and give the reading that agrees with the prose.

## Summary

- **FP32 square root is proven for any `vrsqrt23ps` that meets the manual's bound.** The proof is an
  exhaustive exact model on the host. It covers all 2^24 reduced arguments, every estimate the
  manual allows and all four rounding modes, and it also confirms that the inexact flag is right.
  The sequence is about 19 instructions for 16 lanes, with no branch. Implement it now.
- **FP32 division is proven, with one fix.** The proof is a short derivation (Lemma B, section 2.3)
  plus three host checks:
  - the reciprocal step, exhaustively over all 2^23 divisor significands;
  - the whole core, exhaustively at precisions 6 to 11;
  - 82 million hard FP32 pairs.
  The fix: when the divisor's significand is all ones (Markstein's known exception), the core
  can return the wrong neighbour. Two instructions remove that case, and the checks then find no
  failure. The fast path is about 27 instructions for 16 lanes, plus a branch to a rare path. The
  rare path handles special operands, and subnormal results, which need a midpoint fix after scaling.
  Implement it now, after square root.
- **Historical FP64 status, superseded 2026-11-14 (S12-13): FP64 needs about 34 instructions (division) and 31 (square root) for 8 lanes.** By instruction
  count this is probably cheaper than 8 scalar x87 divides. But no KNC x87 timing is published,
  and none can be measured under the shared-card rules. Division is mostly proven (section 3.1).
  Square root has one open proof obligation (section 3.2). Do FP64 later. Until then it stays
  scalar, as ADR-0003 requires.
  **Current inventory:** GCC `619e14b479a9` contains FP64 divide/sqrt
  expansions, including masked sqrt, with `KNC_DIV_DF_INSNS=34` and
  `KNC_SQRT_DF_INSNS=35` in `i386-knc.cc`. The old proof questions below
  belong to this proposal; source presence does not close them or certify
  a native pass. Reconcile the implemented algorithm and its existing
  qualification before commissioning new proof work. R04 slides 9,18 and
  R27 pp.39,55–56 ([index](knc-references.md)) constrain flags, traps and
  precision; instruction counts are neither dependency costs nor proofs.
- **Three findings for the lead, outside the sequences:**
  - Scalar x87 FP64 division and square root are not correctly rounded on the card. The card's
    x87 runs at 64-bit precision (glibc default), so the result is rounded twice, and 64 < 2·53+2.
    The `s5_ops` checks `div_f64` and `sqrt_f64` can therefore fail on the scalar baseline, and on
    any x87 peel or remainder.
  - `-ffast-math` links `knc-crtfastmath.c`, which sets FTZ and DAZ. A vectorized FP32 division
    then flushes subnormals, so the `s5_ops` `fast` row can fail on its subnormal inputs. That
    behaviour is correct under DAZ.
  - The card's `fetestexcept` ORs the x87 status word with MXCSR (disassembled from
    `sysroot/lib64/libm-2.21.so`). So vector flags are observable exactly like x87 flags.

## 1. Estimates and other IMCI aids

### 1.1 `vrcp23ps` and `vrsqrt23ps`

| | `vrcp23ps` (p. 577-579) | `vrsqrt23ps` (p. 588-590) |
|---|---|---|
| Bound | "0.912ULP (relative error)" | "0.775ULP (relative error)" |
| Domain | every float32 | every float32 |
| NaN in | the input, quieted; #I if sNaN | the input, quieted; #I if sNaN |
| ±0 in | ±inf, #Z | +0 gives +inf, -0 gives -inf, #Z (Table 6.29, garbled) |
| +inf in | +0 | +0 |
| -inf in | -0 | canonical NaN, #I |
| Negative finite in | -1/\|x\| | canonical NaN, #I |
| Exact cases | 2^n gives 2^-n | 2^(2n) gives 2^-n |
| Input denormals | treated as zero, always (not MXCSR.DAZ) | treated as zero, always |
| Tiny results | flushed to zero, always (not MXCSR.FZ) | flushed to zero, always |
| Flags | Invalid, Zero (p. 578) | Invalid, Zero (p. 589) |
| Rounding override | none; EH=1 gives only `{sae}` | none; only `{sae}` |
| Memory forms | no broadcast or up-conversion (Table 4.2, p. 61) | same |

Notes:

- **Reading the bound.** I read "0.912 ULP" as |y - 1/b| <= 0.912 ulp(y), where ulp is measured in
  y's binade. That gives |b·y - 1| < 2^-23 for every b. All the checks below also pass with
  1 ulp, so the reading does not decide any result.
- **Subnormal inputs.** A negative subnormal fed to `vrsqrt23ps` returns -inf and sets #Z
  (p. 588 prose), because it is treated as -0.
- **FTZ and DAZ.** The appendix C.3 table (p. 686-688) is garbled. For `vrcp23ps` it reads "YES / NO".
  I trust the instruction pages, which say YES for both.
- **Consequence.** Both estimates are usable only when the input and the result are normal. Every
  sequence below therefore reduces its argument to [1/2, 2) first.
- **Others.** `vlog2ps` (p. 373) has 4 ulp relative error outside [0.5, 2] and absolute error
  2^-21 inside it. `vexp223ps` (p. 190) has 0.99 ulp and takes a fixed-point input. Neither is
  useful for a correctly rounded division or square root.

### 1.2 Other aids

- **`vgetmantps` / `vgetmantpd`** (p. 324-326, p. 319).
  - Returns the significand normalized to an interval chosen by the immediate: [1,2), [1/2,2),
    [1/2,1) or [3/4,3/2). Bits I1:I0 = 01 selects [1/2,2) by exponent parity: odd unbiased
    exponents give [1/2,1). That is the square-root reduction.
  - Sign control: keep the source sign (00), force 0 (01), or return NaN with #I for a negative
    source (1x). The 1x form also catches -0, so square root cannot use it.
  - Specials (Table 6.20): ±0, ±inf and NaN pass through.
  - The prose says denormals are "explicitly normalized" (DAZ off). The pseudo-code (p. 325) does
    not show that step. Probe P1 checks it.
  - Flags: Invalid, Denormal. DAZ follows MXCSR. Takes `{sae}`.
- **`vgetexpps` / `vgetexppd`** (p. 316-317, p. 313). Returns the unbiased exponent as a float,
  and normalizes denormals first unless DAZ is set. Table 6.18 (garbled) reads: ±0 gives -inf,
  ±inf gives +inf, NaN gives the quieted NaN. Flags: Invalid, Denormal.
- **`vscaleps`** (p. 591-592).
  - Computes zmm2·2^k with an int32 k and rounds like `vmulps`: the MXCSR mode or an override, FZ
    and DAZ from MXCSR. Out-of-range results become ±inf or 0.
  - Flags: Overflow, Underflow, Invalid, Precision, Denormal.
  - **There is no `vscalepd`.** FP64 scaling must add to the exponent field, or multiply by powers of two.
- **`vfixupnanps` / `vfixupnanpd`** (p. 197-198, p. 193).
  - Classifies one source into -inf, <0, -0, +0, >0 and +inf. A 21-bit table maps each class to
    a token: no change, ±inf, ±0, QNaN indefinite, or ±NMAX. A NaN source passes through quieted.
  - Raises #I only for an sNaN source. Producing the NaN token does not raise #I, as far as the
    pseudo-code shows.
  - It sees one operand only. That suits square root, but not division.
- **`vrndfxpntps`** (p. 584). Rounds to an integer or fixed-point value. Not needed here.
- **Rounding overrides** (§4.6.1, p. 63; e.g. `vfmadd231ps`, p. 221-222). With EH=1 a register
  form takes `{rn}`, `{rd}`, `{ru}` or `{rz}`, each with or without SAE. The override beats
  MXCSR.RC. A memory operand cannot be combined with an override. The `-sae` forms let
  intermediate steps raise no flags.
- **Flags** (§4.1.3, p. 56-59). All exceptions are masked. Each instruction ORs the flags of its
  active lanes into MXCSR, and the flags are sticky. Underflow means tiny after rounding with
  unbounded exponent, and inexact (p. 59). The pseudo-code computes nothing in a lane whose mask
  bit is clear. I read that as: masked-off lanes raise no flags. Probe P1 confirms it.
- **NaN choice** (Table 4.3, p. 64). For two NaN operands the first is returned. x87 returns the
  one with the larger significand instead. Only NaN payload bits differ.

## 2. FP32 (V16SF)

### 2.1 Reduction

Each operand is split into significand and exponent with `vgetmantps` and `vgetexpps`. The core
works on significands in [1,2), or [1/2,2) for square root. `vscaleps` then applies the exponent.
This keeps both estimates away from their DAZ/FTZ edges. Subnormal operands need no separate path,
because `vgetmant` and `vgetexp` normalize them when DAZ=0. No intermediate step can overflow or
underflow. Only the final scaling can, and section 2.4 handles it.

Constraints for the implementation:

- Every main-path instruction is either `{rn-sae}` or write-masked to the regular lanes. The
  regular lanes have finite nonzero operands. Garbage computed in special lanes must not raise flags.
- Two instructions per sequence are left without SAE, so their flags reach MXCSR: the final FMA
  and `vscaleps`. Both use the dynamic MXCSR.RC (section 2.3, directed modes).

### 2.2 Division sequence (fast path)

Inputs `a` and `b` are V16SF. Constants: `ONE`, `ALL1 = 0x3FFFFFFF` (2 - 2^-23),
`YALL1 = 0x3F000001` (= RN(1/ALL1)), and `SIGN = 0x80000000`.

```
 1  ma = vgetmantps{sae} a, [1,2), sign kept
 2  mb = vgetmantps{sae} b, [1,2), sign 0
 3  ea = vgetexpps{sae} a
 4  eb = vgetexpps{sae} b
 5  kf = vsubps{rn-sae} ea, eb          ; exact; inf or NaN if an operand is 0, inf or NaN
 6  t  = vsubps{rn-sae} kf, kf          ; 0 on regular lanes, NaN otherwise
 7  kreg = vcmpps.eq t, 0               ; quiet predicate, no flag on NaN
 8  k  = vcvtfxpntps2dq{sae} kf         ; int32 exponent difference
 9  sb = vpandd b, SIGN
10  ma = vpxord ma, sb                  ; quotient sign
11  y0 = vrcp23ps{sae} mb
12  e0 = vfnmadd{rn-sae} mb, y0, ONE    ; 1 - mb*y0 (exact, E1)
13  y1 = vfmadd{rn-sae} e0, y0, y0
14  k1 = vcmpps.eq mb, ALL1             ; Markstein's exception
15  y1{k1} = vmovaps YALL1
16  q0 = vmulps{rn-sae} ma, y1
17  r0 = vfnmadd{rn-sae} mb, q0, ma     ; ma - mb*q0
18  q1 = vfmadd{rn-sae} r0, y1, q0      ; faithful
19  r1 = vfnmadd{rn-sae} mb, q1, ma     ; exact
20  qm{kreg} = vfmadd r1, y1, q1        ; dynamic RC: correctly rounded significand quotient
21  res{kreg} = vscaleps qm, k          ; dynamic RC: exact, or overflow, or tiny
22  ab = vpandd res, 0x7FFFFFFF
23  kt{kreg} = vpcmpud.le ab, 0x00800000 ; tiny or exactly FLT_MIN: may need the midpoint fix
24  krare = knot kreg ; kor krare, kt    ; 2 mask ops
26  kortest krare ; jnz rare_path       ; 2
```

That is about 27 instructions. The critical chain is 1 → 11 → 12 → 13 → 15 → 16 → 17 → 18 → 19 →
20 → 21, 11 deep. The exponent path (3-8) runs in parallel with it. The core (11-20) is the
NVIDIA-style "two-correction" sequence plus the exception fix. Section 2.3 proves it.

Rare path, only when some lane is special or tiny (the special-case results are the IEEE ones):

- **Special lanes**, where `a` or `b` is ±0, ±inf or NaN.
  - Replace each regular operand by ±1 with its own sign. A special operand stays as it is.
    Subnormals also become ±1, which avoids the DAZ input of `vrcp23ps`.
  - Then res = a'·rcp(b'). This gives every IEEE result and flag (sNaN #I from `vrcp23ps` or
    `vmulps`, 0·inf #I, x/0 #Z), with one exception: rcp(0) also raises #Z for 0/0, inf/0 and NaN/0.
  - So run `vrcp23ps` with `b'=0` lanes masked off, blend ±inf into them, and raise #Z by a
    masked `vrcp23ps` only on the lanes where `b = 0` and `a` is finite and nonzero.
  - The NaN choice follows Table 4.3 (first operand), as SSE `divps` does.
  - About 15 instructions.
- **Tiny lanes.** See section 2.4. About 18 instructions, including a read of MXCSR.RC.

### 2.3 Proof outline for the core

Notation: precision p (24), operands a, b in [1,2). B is the integer significand of b, with
2^(p-1) <= B < 2^p. u is the ulp of the quotient's binade. "Faithful" means one of the two
floating-point neighbours of the exact value.

- **Lemma A (exact residual).** If q is faithful to a/b, then r = a - b·q is representable.
  - Proof: r is a multiple of ulp(b)·u.
  - |r| = b·|a/b - q| < b·u, which is less than 2^p·ulp(b)·u. So r fits in p bits, and the FMA
    computes it exactly.
  - This is the classical correcting-term result. Markstein 2000 uses it; Boldo and Daumas 2003
    give general conditions. Underflow cannot occur on reduced operands.
- **Lemma M (distance from midpoints).**
  - a/b is never a midpoint. Proof: a = b·m with m a midpoint would need an odd significand
    of p+1 bits to divide A·2^k, but A has at most p bits.
  - Moreover, |a/b - m| >= u/(2B) for every midpoint m. Proof: a - b·m is a nonzero multiple of
    ulp(b)·u/2, then divide by b = B·ulp(b).
  - In the same way, |a/b - g| >= u/B for every floating-point g != a/b.
- **Lemma B (final correction).** Let q be faithful, let r = a - b·q be exact (Lemma A), and let
  η = b·y - 1 with |η| < 1/(B+1). Then RN(q + r·y) = RN(a/b). The proof is below.

  Write q + r·y = a/b + (a/b - q)·η.
  - Case q = RN(a/b). By Lemma M, |a/b - q| <= u/2 - u/(2B).
    So |r·y| = |a/b - q|·(1+η) < u/2 whenever |η| < 1/(B-1). The rounding returns q.
  - Case q is the other neighbour. Let a/b = q + t·u, with t in (1/2, 1] (sign mirrored for the
    other side). By Lemma M, t - 1/2 >= 1/(2B).
    Then q + r·y - RN(a/b) = u·(t - 1 + t·η).
    This lies in (-u/2, u/2) when t·(1 + η) > 1/2, which holds whenever |η| < 1/(B+1).
  - So |η| < 1/(B+1) covers both cases. Since B + 1 <= 2^p, it suffices that |b·y - 1| < 2^-p.
    The derivation uses a single u, so it covers quotients inside a binade.
  - Quotients that cross the binade at 1 are covered by the exhaustive checks E2 and E4 below.
    Markstein's published theorem (Markstein 2000, ch. 8; also Cornea-Hasegan, Golliver and
    Markstein 1999) states the same step with y = RN(1/b), which implies |η| <= B·2^-2p < 1/(B+1).
- **Directed modes and the inexact flag.**
  - If a/b is representable, then q1 = a/b (see "q1 is faithful" below) and r1 = 0, so the final
    FMA is exact and raises no inexact.
  - Otherwise, by Lemma M, a/b is at least u/B from every floating-point number. The final error
    |a/b - q1|·|η| < u/(B+1) < u/B is smaller. So q1 + r1·y1 lies strictly between the same two
    floating-point numbers as a/b. Then every rounding mode returns the right value, and the
    inexact flag is raised.
  - This is why step 20 uses the dynamic MXCSR.RC. The sequence is then correctly rounded under
    `fesetround` at no cost (Cornea-Hasegan et al. 1999 make the same claim for the Itanium
    sequences).
- **The reciprocal (steps 11-15) satisfies Lemma B's condition.** Shown exhaustively by E1. Without
  step 15 it fails for exactly one case, B = 2^p - 1 (all ones). There `vrcp23ps` may return
  y0 = 1/2, which is within 0.5 ulp. Then e0 = 2^-p, and y0 + e0·y0 is a tie, which rounds to
  even, back to 1/2. So |η| = 2^-p = 1/(B+1), and Lemma B fails. Here
  RN(1/b) = 1/2 + 2^-p, and that value satisfies Lemma B. This is the known exception in
  Markstein's reciprocal theorem (Markstein 1990; Muller et al. 2018).
- **q1 is faithful.**
  - With |η| < 1/(B+1), a/b < 2^p·u gives |a·y1 - a/b| < 2u, so q0 is within 2.5u. q0 itself
    need not be faithful.
  - r0 may then be inexact, with relative error 2^-p.
  - The exact value of the q1 step is a/b + (a/b - q0)·η, plus y1 times r0's rounding error.
    Both terms are below 3u·2^-p. So q1 is within u/2 + 3u·2^-p, which makes it faithful.
  - If a/b is representable, the same bound makes q1 = a/b.
  - Lemma A then makes r1 exact, and Lemma B finishes the proof.

#### Host checks (exact rational emulation; scratch program, not committed)

The program emulates a p-bit binary format with unbounded exponent, using 128-bit integers. It
rounds each FMA once from the exact value, in RN, RD, RU or RZ, and compares with an exact long
division or integer square root. It enumerates every estimate y0 that the manual's bound allows
(1-2 per input), and every estimate within 1 ulp (up to 3 per input). It also covers both signs
of the quotient, because RD on a negative quotient mirrors RU on a positive one.

| Check | What | Result |
|---|---|---|
| E1 | p = 24, all 2^23 divisors, steps 11-13 | e0 always exact. Lemma B's condition fails only for B = 0xFFFFFF, y0 = 1/2, with both the 0.912 and 1 ulp sets. With p = 6..23 it is the same single case at every p |
| E2 | p = 6..11, all (a, b) pairs, steps 11-13 and 16-20, four modes | q1 always faithful, r1 always exact, inexact flag always right. RN fails exactly once per p: a = 1, B all ones. RD, RU and RZ never fail |
| Lemma B | p = 6..10, all (a, b), both faithful q, every y with \|b·y-1\| < 1/(B+1) | 0 failures; the residual is always exact |
| E4 | p = 24, 81,976,814 hard pairs: for each odd B, every A with \|a/b - m\| = N·u/(2B), N = 1..4, in both binades (A from a modular inverse of 2^24 or 2^25 mod B), plus A = B-3..B+3 and a = 1; four modes | Without step 15: RN fails twice (the all-ones case). With step 15: 0 failures, inexact flag always right |
| control | the same checker on deliberately wrong variants (y1 rounded up or toward zero; h0 in place of h1 for square root) | fails, as expected |

### 2.4 Range: overflow, subnormal results, specials

- **Normal results.** `vscaleps` is exact, so res = R(a/b).
- **Overflow.** qm·2^k overflows exactly when R(a/b) does. `vscaleps` rounds the way `vmulps`
  does: inf under RN, NMAX under RZ, and so on. It raises OE and PE. No fix is needed.
- **Subnormal results (lanes in `kt`).**
  - `vscaleps` rounds the already rounded qm a second time.
  - Under RD, RU and RZ that is harmless, because the grids nest: R_coarse(R_fine(x)) = R_coarse(x).
  - Under RN it is wrong only when qm·2^k lies exactly on a midpoint of the subnormal grid.
    Subnormal midpoints lie on qm's 24-bit grid, and no 24-bit point lies strictly between a/b
    and qm.
  - The fix, run only when MXCSR.RC is RN:
    1. Detect the midpoint with integer operations. Let d be the number of bits dropped. The
       midpoint case is when (Mq mod 2^d) = 2^(d-1), using `vpsllvd` and `vpsrlvd`.
    2. Compute rr = ma - mb·qm with `{rn-sae}`. It is exact by Lemma A.
    3. Rescale those lanes with `{ru}` if rr > 0 and `{rd}` if rr < 0. If rr = 0, a/b is the
       midpoint itself, and ties-to-even is already correct.
  - **Underflow flag.** IEEE wants UE when the result is tiny and inexact. `vscaleps` raises UE
    only when its own rounding is inexact. That misses one case: a/b is inexact (rr != 0, PE
    already set by step 20) but qm·2^k is exactly representable. The rare path raises UE there
    with one masked operation whose result is known to be tiny and inexact, for example
    FLT_MIN·(1 - 2^-24).
- **Specials.** See the rare path in section 2.2.

### 2.5 Square root sequence (no branch)

Argument reduction: x = m·2^(2j), where m = `vgetmantps`(x, [1/2,2)) and j = ceil(e/2) for
e = `vgetexpps`(x). The square root of a positive float32 is always normal, so `vscaleps` is
always exact. There is no tiny path and no overflow path. Constants: `HALF`, and the fixup table
`0x000206AD`. In class order -inf, <0, -0, +0, >0, +inf, it maps to NaN, NaN, -0, +0, no change, +inf.

```
 1  m  = vgetmantps{sae} x, [1/2,2), sign 0
 2  e  = vgetexpps{sae} x
 3  ei = vcvtfxpntps2dq{sae} e
 4  ei = vpaddd ei, 1
 5  j  = vpsrad ei, 1                   ; ceil(e/2)
 6  xm = vpsubd x, 1                    ; on the bit pattern
 7  kreg = vpcmpud.lt xm, 0x7F7FFFFF    ; 0 < x < inf, subnormals included
 8  kneg = vpcmpd.lt xm, -1             ; x < 0 and x != -0 (sign-set NaNs too)
 9  y0 = vrsqrt23ps{sae} m
10  g0 = vmulps{rn-sae} m, y0
11  h0 = vmulps{rn-sae} y0, HALF
12  r0 = vfnmadd{rn-sae} g0, h0, HALF   ; 1/2 - g0*h0
13  g1 = vfmadd{rn-sae} g0, r0, g0
14  h1 = vfmadd{rn-sae} h0, r0, h0
15  d  = vfnmadd{rn-sae} g1, g1, m      ; m - g1^2 (not always exact: 1.6% of cases, E3)
16  s{kreg} = vfmadd d, h1, g1          ; dynamic RC; the only inexact flag
17  s{kreg} = vscaleps s, j             ; exact
18  vrsqrt23ps{kneg} x                  ; result unused: raises #I for x < 0 and -inf
19  s = vfixupnanps s, x, 0x206AD       ; ±0, +inf, NaN (quieted, #I if sNaN), negative -> NaN
```

That is 19 instructions, and the chain is 1 → 9 → 10 → 12 → 13 → 15 → 16 → 17 → 19, 9 deep.
Steps 9-16 are Goldschmidt's coupled iteration with Markstein's final correction (Markstein 2000,
ch. 9; the same shape as the Itanium sequences in Cornea-Hasegan et al. 1999).

**Proof: exhaustive (E3).** I emulated steps 9-16 exactly:

- for all 2^24 values of m in [1/2, 2);
- for every y0 within 0.775 ulp (26,005,974 cases) and within 1 ulp (33,554,434 cases);
- in all four modes for step 16.

Result: g1 is always faithful, and the result always equals the correctly rounded square root. Step 16
raises inexact exactly when √m is not representable. d is sometimes inexact (405,109 cases at
0.775 ulp), which does not matter. So for any `vrsqrt23ps` within the manual's bound, the
sequence is correctly rounded in every rounding mode, with the right inexact flag.

Specials and flags:

- `vfixupnanps` handles every special input.
- Only step 16 can raise PE, and only on regular lanes.
- Step 18 raises #I for negative inputs, including -inf, as IEEE requires. sqrt(-0) = -0 raises
  nothing, because -0 is excluded from `kneg`.
- Under DAZ=1, a positive subnormal is classified as +0 and returns +0. That is DAZ semantics.

### 2.6 Flags compared with x87 `fdiv` and `fsqrt`

x87 computes in the 64-bit significand (Linux default precision control) and rounds again when it
stores to float. For float, that double rounding is innocuous, because 64 >= 2·24+2 (Figueroa
1995). So a stored x87 float quotient or root is correctly rounded. x87 flags go to the x87
status word, vector flags to MXCSR. The card's `fetestexcept` ORs both, and `fesetround` sets
both (checked by disassembling the card's libm).

| Flag | x87 | Vector sequences above |
|---|---|---|
| inexact | right for a stored result | right (E2, E3, E4) |
| divide-by-zero | x/0 for finite nonzero x | same (rare path) |
| invalid | 0/0, inf/inf, sNaN, sqrt(negative) | same |
| overflow | on store | same (`vscaleps`) |
| underflow | on store; tiny after rounding | same, with the explicit raise in section 2.4 |
| denormal (not in `FE_ALL_EXCEPT`) | on a subnormal operand | raised by `vgetmant`/`vgetexp` without SAE, if wanted |

What a C program could still observe:

- **NaN payload when both operands are NaN.** x87 returns the larger significand, the vector code
  the first operand. C does not specify which.
- **Excess precision.** An x87 result that is never stored keeps 64 bits and may compare
  differently. ADR-0003 point 2 already allows that.
- **Rounding mode when the compiler does not expect it to change.** Without `-frounding-math`,
  GCC may fold constants in RN, whatever the vector code does at run time.

ADR-0003 should say three things:

- The vector division and square root are correctly rounded in the current MXCSR.RC and raise the
  IEEE flags, except for the NaN payload choice above.
- They are proven only for FZ = DAZ = 0. Under FTZ or DAZ, for example after `-ffast-math` links
  `knc-crtfastmath.c`, subnormals flush.
- Scalar x87 FP64 results are not always correctly rounded (section 3.3).

## 3. FP64 (V8DF)

### 3.1 Division

Use the same reduction (`vgetmantpd`, `vgetexppd`). The estimate comes from FP32: mb in [1,2)
converts safely. The core:

```
y0 = vcvtps2pd(vrcp23ps(vcvtpd2ps{rn-sae}(mb)))     ; |mb*y0 - 1| < 2^-23.13 + 2^-24 < 2^-22.5
e0 = 1 - mb*y0                                       ; FMA; may lose 1 bit, which is harmless
t  = fma(e0, e0, e0) ; p = fma(t, e0, e0)            ; p = e0 + e0^2 + e0^3
y1 = fma(y0, p, y0)                                  ; relative error <= e0^4 + 2^-74 < 2^-73
e1 = 1 - mb*y1 ; y2 = fma(e1, y1, y1)                ; y2 = RN(1/mb) except B all ones
blend RN(1/(2-2^-52)) on the all-ones lanes          ; 2 instructions
q0 = ma*y2 ; r0 ; q1 ; r1 ; q2 (dynamic RC)          ; as in FP32, steps 16-20
```

Status of the proof:

- y1 is faithful: its relative error is below 2^-73, so it is within u/2 + 2^-73.
- y2 = RN(1/mb) by Markstein's reciprocal theorem, except when the significand is all ones.
  That theorem is published (Markstein 1990; Muller et al. 2018). E1 reproduces it with exactly
  that exception at every precision from 6 to 24. Then |η| <= B·2^-106 < 1/(B+1).
- The steps from q0 onward follow from Lemma A, Lemma M and Lemma B, which hold for any p.
- What remains is to write these bounds down and check them with a 53-bit host model on hard cases
  (section 5).

Instruction count:

| Part | Instructions |
|---|---|
| `vgetmantpd` ×2, `vgetexppd` ×2, `vsubpd`, regular-lane test (2), `vcvtfxpntpd2dq`, `vpermd` to the odd dwords, `vpslld` 20 | 10 |
| Sign | 2 |
| y0 | 3 |
| y1 | 4 |
| y2 and the exception blend | 4 |
| q0 to q2 | 5 |
| Exponent insert: masked `vpaddd` on the high dwords, valid for normal results | 1 |
| Range test on k | 2 |
| Rare mask and branch | 3 |
| **Total for 8 lanes** | **about 34** |

Overflow and subnormal results go to the rare path. Overflow multiplies by two powers of two, so
only the second multiply rounds. Subnormal results get the same midpoint fix as FP32.

### 3.2 Square root

Use m from `vgetmantpd` with [1/2,2). The core:

```
y0 = cvt(vrsqrt23ps(cvt(m)))           ; |y0*sqrt(m) - 1| < 2^-23.1
s  = y0*y0                             ; exact (y0 has 24 bits)
ε  = 1 - m*s                           ; FMA, |ε| < 2^-22
p  = ε*(1/2 + ε*(3/8 + ε*5/16))        ; 3 instructions; truncation 35/128 ε^4 < 2^-89
g0 = m*y0 ; eg = fms(m, y0, g0)        ; exact product error (2MultFMA)
t  = fma(g0, p, eg) ; g1 = g0 + t      ; g1 within u/2 + √m·2^-73: faithful
hy = 0.5*y0 ; h1 = fma(hy, p, hy)      ; 1/(2√m) to 2^-52.9
d  = m - g1^2 ; g2 = fma(d, h1, g1)    ; final, dynamic RC
```

That is 16 core instructions. Adding the reduction and exponent insert (about 8), the masks (3),
and the specials (`vfixupnanpd`, plus one masked operation that raises #I for negative inputs)
gives **about 31 for 8 lanes**.

Open obligation: the final step with d possibly inexact. In FP32, d is inexact in 1.6% of cases
and E3 still passes by exhaustion. FP64 needs Markstein's square-root final-step theorem for the
exact d, plus a bound showing that d's rounding error (relative 2^-53, under 2^-52·u after
multiplying by h1) stays below the distance of √m from a midpoint. That distance is at least
u^2/(8√m), about u·2^-56, so the bound **may not hold**. If it does not, g1 must be computed in
[1/4,1) so that d is exact (Markstein 2000, ch. 9), or the FP32 structure can be reused with one
more refinement.

### 3.3 Compared with x87, and ADR-0003's open question

- **Per element.**
  - Vector: about 34/8, roughly 4.3 vector instructions per quotient, and about 3.9 per root.
  - Scalar: one `fdivl` (or `fsqrt`) per element, plus a load and a store.
- **What decides it.**
  - Chrysos (Hot Chips 24, 2012) describes the KNC core as derived from the P54C Pentium.
  - The P5 `FDIV` is listed in x87 timing tables at 39 clocks, not pipelined. That is a secondary
    source, and nothing published gives the KNC figure.
  - If KNC kept anything like that, 8 x87 divides cost far more than 34 vector instructions.
  - **So a correct FP64 sequence is probably not slower than x87 at 8 lanes.** I cannot confirm it:
    the shared-card rules forbid timing figures. A one-off micro-benchmark would need the owner's
    agreement.
- **Answer to ADR-0003's open question.** Correctly rounded FP64 division is not obviously too
  slow. It should not be ruled out. It should follow FP32 once the FP64 proof obligations are
  closed.
- **x87 FP64 is not correctly rounded.**
  - The x87 FP64 quotient or root is rounded to 64 bits, then rounded again to 53 when stored.
    Since 64 < 2·53+2, the double rounding is not innocuous (Figueroa 1995).
  - Roughly 1 in 2^12 inexact results is one ulp off under RN. A wrong result needs the 64-bit
    value to land exactly on a 53-bit midpoint, which happens with probability 2^-11, and then
    ties-to-even picks the wrong side about half the time.
  - The vector sequence would be more accurate than the scalar code it replaces.
  - `s5_ops` `div_f64` and `sqrt_f64` require correct rounding. They will probably fail today on
    scalar x87, and later on any x87 peel or remainder. This is not run on the card yet.

## 4. GCC 16 entry points

### 4.1 Expanders today

- **`div<mode>3`.**
  - V16SF: `sse.md:2870` (VF1, `TARGET_SSE`). V8DF: `sse.md:2842` (VF2, `TARGET_SSE2`).
    Scalar: `i386.md:11739` (MODEF).
  - The VF1 and VF2 iterators gate V16SF and V8DF on `TARGET_AVX512F` (`sse.md:436`, `:450`).
    KNC never sets that, so neither expander exists under `-march=knc`.
  - The vectorizer therefore finds no optab for RDIV_EXPR on V16SF or V8DF, and the division stays
    scalar. This is the ADR-0003 fallback, already in force.
- **`sqrt<mode>2`.** `sse.md:3078` (VF2HB) and `sse.md:3083` (VF1), with the same gating.
  - C keeps `sqrt` calls scalar under the default `-fmath-errno`.
  - gfortran defaults to `-fno-math-errno`, so Fortran loops reach `IFN_SQRT`, which is
    `sqrt_optab`.
- **`cond_div<mode>`.** `sse.md:2907`, VFH, which gates V16SF on `TARGET_AVX512F`.
  - Without it, a loop with a division can never be fully masked: the division can trap, and
    there is no conditional form (`tree-vect-stmts.cc:6805-6830`). The vectorizer then falls back
    to an x87 epilogue.
  - For FP64 that matters twice over: the epilogue would double-round (section 3.3).

### 4.2 Why the i386 reciprocal sequences are not correctly rounded

- **`ix86_emit_swdivsf`** (`i386-expand.cc:20328`) emits rcp → e0 = x0·a → e1 = e0·b - a →
  res = -e1·x0 + e0.
  - That is one correction from the raw estimate: a·y0 plus a residual times y0. With y0 only
    14-bit (`rcp14`) or 12-bit (`rcpps`), the result is not even faithful.
  - Even with a 23-bit estimate it lacks Lemma B's |b·y - 1| < 2^-p.
  - There is no handling of zero, infinity or subnormals.
- **`ix86_emit_swsqrtsf`** (`:20391`) is one Newton step on rsqrt: -0.5·a·x0·(a·x0² - 3). It
  masks out a = 0 and nothing else, and it is not correctly rounded either.
- **When they are used.** Only when `TARGET_RECIP_VEC_DIV`/`_SQRT` (`i386.h:3073-3085`; the
  default mask has both bits set, `i386.opt:44`) is combined with `-ffinite-math-only
  -fno-trapping-math -funsafe-math-optimizations`. In practice that means `-ffast-math`.
  `-mrecip=` (`i386-options.cc:2035-2040`, `3012-3015`) edits the mask.
- **`ix86_builtin_reciprocal`** (`i386-builtins.cc:1788`) maps only the SSE sqrtps builtins.
- **For KNC:**
  - These functions emit `UNSPEC_RCP14`/`RSQRT14` and AVX-512 compares, so they must not be reused.
  - ADR-0003 point 5's opt-in approximate form needs its own KNC function with a stated bound.
  - The `s5_ops` `fast` row expects correct rounding even under `-ffast-math`. So the first tickets
    should keep the exact sequence in every mode, and leave the approximate form for later.

### 4.3 Where the KNC sequence should live

- **Recommended: an inline `define_expand`.**
  - Put the sequences in `imci.md` (`knc_div<mode>3`, `knc_sqrt<mode>2`, `knc_cond_div<mode>`),
    with the helper in `i386-knc.cc` (`ix86_knc_expand_div`, `_sqrt`).
  - Reach them through hooks in `sse.md`, the way `cond_fma<mode>` already does (`sse.md:6355`,
    ADR-0006).
  - The pattern names `divv16sf3` etc. are already taken by `sse.md`, so imci.md cannot define
    them again. Give the three `sse.md` expanders a local iterator, as `VF_BHSD` does at
    `sse.md:404`, such as `(V16SF "TARGET_AVX512F || TARGET_KNC")`, plus an
    `if (TARGET_KNC) { ...; DONE; }` branch.
  - Do not widen VF1 or VF2 themselves; many patterns use them.
  - All instructions stay visible to CSE, scheduling, loop-invariant motion (for the constants)
    and register allocation, and the cost is honest.
  - The rare path is a `kortest` and jump to a cold block, emitted by the expander. i386 expanders
    already emit labels and jumps, for example `ix86_expand_floorceil`.
- **Not a `define_insn_and_split`.** It would hide about 27 instructions as one insn until after
  reload. The scheduler and the cost model would see one instruction, and it would need fixed
  scratch registers. That is against "do not hide a cost".
- **Not a libgcc helper with a vector ABI, as the main form.** It adds a call, clobbers zmm
  registers, and makes the cost opaque. It would be acceptable only for the rare path, if the
  inline rare path grows too large.
- **Cost the vectorizer sees today.**
  - `ix86_division_cost` (`i386.cc:22314`) charges `ix86_vec_cost(mode, divss/divsd)`: one
    hardware divide.
  - The SQRT rtx cost (`i386.cc:23273`) tests `mode == SFmode`, which is false for V16SF, so it
    charges `sqrtsd`.
  - The vector statement cost for an `IFN_SQRT` call (`i386.cc:26664-26681`) has no SQRT case.
    It is costed as a plain `vector_stmt`.
  - The KNC tickets must add KNC branches that charge the fast-path instruction count, about 27
    and 19 (FP32) and 34 and 31 (FP64), times the FMA/`sse_op` cost. Then a loop vectorizes only
    when the vector form really pays.

## 5. Proof and test plan

### 5.1 How correct rounding is shown

1. **Argument.** Lemmas A, M and B, and the faithful-q1 step, written once in a comment block in
   `i386-knc.cc` that cites this document.
2. **Host model.** A committed host test reruns E1-E4 (FP32) and the FP64 analogues on every
   change to a sequence. It is exact integer emulation, with no hardware involved. The FP32 runs
   take about 2 minutes, plus 6 minutes for E4. The FP64 model needs 256-bit products; MPFR or
   GMP on the host is simplest for that.
3. **Hardware probes.** These remove the dependence on the manual's wording:
   - P1a: `vrcp23ps` over all 2^23 significands in [1,2).
   - P1b: `vrsqrt23ps` over all 2^24 values in [1/2,2).
   - Each probe records the error in ulps and checks the 0.912 and 0.775 bounds. If a bound is
     broken, the dumped tables go back into E1-E4 as the real y0.
   - P1c: `vgetmantps`/`vgetmantpd` on subnormals with DAZ=0.
   - P1d: no flags from masked-off lanes (a masked `vrcp23ps` of 0 must leave #Z clear).
   - P1e: `vrcp23ps(0x3FFFFFFF)`, which shows whether step 15 is needed on this part. Keep step
     15 anyway, because the proof must not depend on it.
4. **Native tests on the card**, below.

### 5.2 Test sets

- **FP32 square root: exhaustive over all 2^32 bit patterns.** This is feasible.
  - The vector kernel computes 16 roots per iteration.
  - A scalar integer check decides each result: (2q - g_lo)^2 < 4x < (2q + g_hi)^2, as in
    `s5_ops` `sqrt_ok`, and exact equality for perfect squares.
  - NaN, ±0, ±inf and negatives are compared bitwise with the IEEE result.
- **FP32 division** (exhaustive is about 2^46 per exponent pair, which is out of reach):
  - (a) The E4 hard set, generated on the card from the modular inverse, about 8.2·10^7 pairs.
    Every pair is within 4·u/(2B) of a midpoint or a representable value. This is the
    number-theoretic construction of Kahan's and Tang's tests, as Parks 2000 generalizes it.
  - (b) A = B-3..B+3 for every B, and a = 1 for every B (the Markstein class).
  - (c) An exponent sweep: all 254×254 exponent pairs, plus subnormal operands, times 64 random
    significand pairs. This covers every overflow and subnormal result. Include results in the
    last subnormal binade and results that round to FLT_MIN.
  - (d) The tiny-midpoint set: pairs whose rounded significand quotient lands exactly on a
    subnormal midpoint. Construct qm with low bits 100..0, then take a = qm·b ± one ulp of b.
  - (e) Specials: all pairs from {±0, ±min subnormal, ±FLT_MIN, ±NMAX, ±inf, qNaN, sNaN, ±1}.
    Compare values bitwise and compare `fetestexcept` flags per element.
  - (f) 2^30 random pairs. Check each with the exact residual test: the FP32 product fits in
    64-bit integers.
  - (g) Rounding modes: run (a), (b) and (d) under each of the four `fesetround` modes.
- **FP64** (later): as for FP32, but the hard set needs 128-bit modular arithmetic, and the
  residual check is the 128-bit one `s5_ops` already has (`div_ok`, `sqrt_ok`). Parks 2000 also
  gives square-root hard cases.
- **Markstein's and "Kahan's" sets as named in the ticket.** I did not find a published Markstein
  list. The hard cases his theorems care about are the all-ones divisors and the near-midpoint
  quotients, and (a) and (b) contain them. I did not check Kahan's original division test
  directly. Set (a) is the same construction: quotients nearest the midpoints.

### 5.3 MPFR

- **Host only.** The Cygwin toolchain has MPFR 4.2.2:
  `.work/_shared/toolchain/cygwin/usr/include/mpfr.h`, `.../cygwin/lib/libmpfr.dll.a` and
  `.../cygwin/bin/cygmpfr-6.dll`.
  - GCC's own build links it: `gmplibs='-lmpc -lmpfr -lgmp'` in `.work/_shared/gcc-build/config.log`.
  - The PhiWeather bootstrap has a copy too, which is read-only.
- **Not on the card.** There is no `libmpfr` in `toolchain/sysroot`. Card tests therefore use the
  exact integer checks.
- **Use of MPFR.** Validate those integer checkers on the host, and generate expected values for
  any set that cannot be checked by a residual.

### 5.4 Card time to book

These are estimates, not measurements. They assume cores 40-59 (80 threads), about 10^9 scalar
instructions per second per core in total over its threads, and the clock to be confirmed.

| Job | Work | Estimate | Book |
|---|---|---|---|
| P1a-e probes | 2.5·10^7 estimates, dump about 24 MB | under 10 s | 5 min |
| FP32 sqrt exhaustive | 2^32 × about 20 scalar check instructions | 5-60 s | 10 min |
| FP32 div sets (a)-(g) | about 1.6·10^9 checked quotients, × 4 modes for (a), (b), (d) | 1-5 min | 20 min |
| `s5_ops` (existing fixture, 4 builds) | already sized by the lead | minutes | per fixture |
| FP64 div and sqrt sets (later) | about 1.5·10^9 quotients, 128-bit checks | 2-10 min | 30 min |

The card is on hold for the owner (2026-11-04), so each job needs the owner's agreement with the
other user.

## 6. Recommendation

### FP32: implement this sprint, square root first

- **Ticket A (standard): FP32 vector square root.**
  - Content: `sqrt<mode>2` for V16SF through the `sse.md` hook and an `imci.md` expander
    (section 2.5), a KNC cost branch for SQRT/`IFN_SQRT`, and the host model E3 as a committed
    host test.
  - Acceptance:
    - the host model passes (exhaustive, four modes, flag);
    - `s5_ops` `sqrt_f32` passes in `o2v`, `o3` and `neg` as specified;
    - a T1 scan shows the loop vectorized at `-O2 -fno-math-errno` and scalar under the default
      `-fmath-errno`;
    - the native exhaustive 2^32 run reports 0 mismatches, flags included.
- **Ticket B (deep): FP32 vector division.**
  - Content: `div<mode>3` and `cond_div<mode>` for V16SF (section 2.2, rare path, section 2.4),
    the cost branch, and E1, E2 and E4 as host tests.
  - Acceptance:
    - the host models pass, and also fail without step 15;
    - `s5_ops` `div_f32` passes; that needs the `fast` row's FTZ/DAZ question settled first;
    - native sets (a)-(g) report 0 mismatches, flags included;
    - a fully masked division loop vectorizes, with no x87 remainder;
    - x86_64 output is unchanged (the batch check).
- **Ticket P (light, card): hardware probes P1a-e.** Run them before or together with A, because
  their output can only strengthen the proofs.

### FP64: later, not by default yet

**Historical ticket proposal, superseded as an implementation inventory
(S12-13).** See the summary correction above. No current FP permission is
granted or withdrawn by this annotation. R03 pp.15–22 also requires complete
ABI/call-state accounting when comparing expanded arithmetic with scalar calls.

- **Ticket C (deep, research then code): FP64 division.**
  - First close the obligations in section 3.1: the written bounds, and a 53-bit host model on
    Parks-style hard cases.
  - Then implement it like Ticket B.
  - Acceptance: as Ticket B, plus `s5_ops` `div_f64` with no x87 epilogue. That needs
    `cond_div` for V8DF.
- **Ticket D (deep): FP64 square root.**
  - First resolve the final-step obligation in section 3.2, possibly by changing the reduction to
    [1/4,1).
  - Acceptance: as Ticket A, without the exhaustive run, which is out of reach for FP64.
- **Ticket E (owner decision): one x87 versus vector timing run for FP64.** It needs the card owner's
  agreement, because the shared rules exclude timing.

### Lead and ADR follow-ups

- **ADR-0003:** add the three sentences in section 2.6.
- **`s5_ops`:** two caveats.
  - x87 FP64 double rounding (section 3.3) affects `div_f64` and `sqrt_f64` on scalar paths.
  - The `fast` row's FTZ/DAZ affects the subnormal inputs of the FP32 checks.
- **Approximate forms (ADR-0003 point 5):** a separate, later ticket. It needs its own KNC
  function with a stated bound, because the i386 functions are AVX-512 specific.

## Sources

- Intel, *Intel Xeon Phi Coprocessor Instruction Set Architecture Reference Manual*, 327364-001, 2012.
- P. Markstein, *IA-64 and Elementary Functions: Speed and Precision*, Prentice Hall, 2000
  (ch. 8 division, ch. 9 square root).
- P. Markstein, "Computation of elementary functions on the IBM RISC System/6000 processor",
  *IBM J. Res. Dev.* 34(1), 1990.
- M. Cornea-Hasegan, R. Golliver, P. Markstein, "Correctness proofs outline for Newton-Raphson
  based floating-point divide and square root algorithms", ARITH-14, 1999.
- J. Harrison, "Formal verification of IA-64 division algorithms", TPHOLs 2000. The method
  applies to a future machine-checked proof; it is not used here.
- J.-M. Muller et al., *Handbook of Floating-Point Arithmetic*, 2nd ed., Birkhäuser, 2018
  (Newton-Raphson division with an FMA; Markstein's theorems).
- S. Boldo, M. Daumas, "Representable correcting terms for possibly underflowing floating point
  operations", ARITH-16, 2003.
- S. A. Figueroa, "When is double rounding innocuous?", *ACM SIGNUM Newsletter* 30(3), 1995.
- M. Parks, "Number-theoretic test generation for directed rounding", *IEEE Trans. Computers*
  49(7), 2000.
- G. Chrysos, "Intel Xeon Phi coprocessor (codename Knights Corner)", Hot Chips 24, 2012.
- **Not verified:** I located Kahan's division-test notes and Tang's number-theoretic test work only
  by citation, and did not read them. Section 5.2 uses their construction as Parks describes it.
  The 39-clock P5 `FDIV` figure comes from secondary x87 timing tables.
