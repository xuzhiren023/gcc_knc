# S4-01: masks on KNC (ADR-0007 input)

Read only; no build, no card run. GCC citations are `file:line` in `.work/_shared/gcc` at `knc`
`0d3c0152fe3` (line numbers moved since ADR-0005: `ix86_get_mask_mode` is now `i386.cc:26073`,
the partial-vector default `i386-options.cc:3176`). Manual pages are printed pages of Intel
327364-001. Each section separates **Read** (what the source or manual says) from **Inferred**
(my design reasoning, not yet checked by a build or the card).

## 1. Mask mode and the vectorizer paths

**Read.**
- Under KNC `ix86_get_mask_mode` falls through to the vector-mask branch and returns V16SI for
  V16SF and V8DI for V8DF (`i386.cc:26073-26100`): its scalar-mask branch needs `TARGET_AVX512F`.
- A scalar-integer mask mode gives a boolean vector type with 1-bit elements in that integer mode
  (`tree.cc:10507-10523`). Middle-end code already copes with a mask mode wider than the lane count
  (`expr.cc:14031-14044`, `dojump.cc:1238-1253`).
- Manual: a mask register has 16 bits, and 64-bit-element instructions use only the low 8 (2.1.2,
  p.22). `vcmppd` writes `k[15:8] = 0` (p.145). Intel's own intrinsics type 8-lane masks as
  `__mmask8` (p.147).
- `sse.md` names the mask mode per data mode with `avx512fmaskmode`: V16SF and V16SI map to HI,
  V8DF and V8DI to QI (`sse.md:1085-1091`). The mask-taking standard names are spelled with it:
  `vec_cmp` (`sse.md:5283`), `vec_cmpu` (`5382`), `vcond_mask` (`5506`), `maskload` (`29599`),
  `maskstore` (`29628`) and the `cond_*` expanders (`2659`, `2749`, `6340`, `6443`, `6549`, `6657`).
- GCC 16 has no `vcond`/`vcondu` optab. A VEC_COND_EXPR needs `vcond_mask` with a boolean mask
  type (`optabs-tree.cc:458-466`, `optabs.def:98-101`). A comparison producing a mask needs
  `vec_cmp`/`vec_cmpu` (`optabs-tree.cc:447-451`).
- If-conversion turns a possibly-trapping conditional load or store into MASK_LOAD/MASK_STORE
  only if `maskload`/`maskstore` exist (`tree-if-conv.cc:957-990`, `1071-1098`, `2808-2843`). A
  store is always predicated (`tree-if-conv.cc:1094-1095`). It becomes an unconditional
  read-modify-write only when it cannot trap and cannot introduce a store data race
  (`tree-if-conv.cc:926-953`); for a global array it can, so the store needs MASK_STORE. A
  conditional trapping call or operation needs `cond_<op>` (`tree-if-conv.cc:997-1019`).
- `maskload` and `maskstore` may not FAIL (`doc/md.texi:7759`).

**Decision input.** `get_mask_mode` returns **HImode for V16SF and V16SI, QImode for V8DF and
V8DI**. That is the AVX-512 rule, reached with one term in the existing scalar-mask branch
(`|| (TARGET_KNC && vector_size == 64)` next to `i386.cc:26080`). It makes every mask-taking
name match an `sse.md` expander name, so one expander covers all four modes. The cost is an
amendment to ADR-0004: `k1`-`k7` hold QI as well as HI (today only HI, `i386-knc.cc:450-451`).
QI masks move and spill through a GPR like HI (`imci.md:93-110`).

**Hazard.** In a QI mask, bits 15:8 are undefined. `knot` and `kxnor` set them, and
`kortest`, `jkzd`/`jknzd`, `kmov r32,k` and `kconcat*` read all 16 bits (pp.73-106). A QI
consumer of those must clear or ignore the high byte.

**Inferred.** HImode for every mode keeps ADR-0004 unchanged and moves the 8-lane names into
`imci.md`. But the 16-lane names collide with `sse.md` anyway. HImode also blocks 16-to-8-lane
mask packing: `vec_pack_sbool_trunc` needs fewer than 8 lanes (`tree-vect-stmts.cc:14354-14361`),
and `vec_pack_trunc_hi` gives SI. So QI is the better fit.

| Case | GIMPLE after if-conversion | Optabs GCC 16 queries | Where KNC plugs in |
|---|---|---|---|
| (a) `if (a[i] > b[i]) c[i] = x[i]` | mask = `a>b`; MASK_STORE `c`; MASK_LOAD `x` if `x` may trap | `vec_cmp<V><M>`, `maskstore<V><M>`, `maskload<V><M>` | `vec_cmp` widening plus `ix86_expand_mask_vec_cmp` entry hook; `maskload`/`maskstore` widening plus dispatch (section 5) |
| (b) `c[i] = a[i] > b[i] ? x[i] : y[i]` | VEC_COND_EXPR | `vec_cmp`, `vcond_mask_<V><M>` | `vcond_mask` widening; vec_merge matched by a new `imci.md` blend |
| (c) `fabs` | ABS_EXPR | `abs<V>2` (`sse.md:2603-2608`, VFB, `TARGET_SSE`) | widening plus entry hook; `vpandd` with a `{1to16}` sign-clear constant; no mask |
| (c) `fmin`/`fmax` calls | IFN_FMIN/FMAX | `fmin<V>3`/`fmax<V>3` (no `sse.md` instance) | `imci.md` only: `vgminps`/`vgmaxps`/`pd` (pp.333-348) |
| (c) `a < b ? a : b` | stays VEC_COND_EXPR unless `-ffinite-math-only -fno-signed-zeros` | `vec_cmp` plus `vcond_mask` | same as (b); MIN_EXPR (`smin<V>3`, `sse.md:3318`, VFH-gated) not provided at first |
| (c) int `min`/`max` | MIN_EXPR | `smin/smax/umin/umax<V16SI>3` (`sse.md:18040`) | widening; `vpminsd`/`vpmaxsd`/`vpminud`/`vpmaxud` (pp.497-506); none for V8DI |
| (d) `if (c) p[i] = v` | MASK_STORE (or a read-modify-write `vcond_mask` if race-free) | `vec_cmp`, `maskstore` (or `vcond_mask`) | as (a) |

`cond_<op>` is not needed for (a)-(d). It is needed for masked tails (section 5).

## 2. IMCI forms

**Read.**
- **FP compares** `vcmpps`/`vcmppd k2{k1}, zmm1, S(zmm2/m), imm8` (pp.144-151). The immediate
  has 3 bits: eq 0, lt 1, le 2, unord 3, neq 4, nlt 5, nle 6, ord 7 (p.150). gt and ge exist
  only as operand swaps. With a NaN operand eq, lt, le and ord return 0, and the rest return 1.
  lt, le, nlt and nle raise invalid on a QNaN; eq, neq, unord and ord are quiet (p.149; 4.1.3.1,
  p.57). Denormals compare as zero only if MXCSR.DAZ=1 (p.149). The write-mask disables a lane's
  compare and writes 0 to that destination bit (p.149). FP exception flags come only from enabled
  lanes (2.1.2, p.22).
- **Integer compares** `vpcmpd`/`vpcmpud` take imm eq 0, lt 1, le 2, neq 4, nlt 5, nle 6; 3 and 7
  are reserved (pp.463-466, 476-479). The pseudo-forms are `vpcmpeqd`/`vpcmpgtd`/`vpcmpltd`
  (pp.467-475), and `vptestmd` sets a mask from an AND (p.568). These codes equal GCC's integer
  AVX-512 immediates (`i386-expand.cc:4756-4779`). There is **no** `vpcmpq`, `vpcmpuq`,
  `vptestmq` or `vp{min,max}{s,u}q`: none appear in the contents (pp.5-10), and searching the
  manual text finds no `VPCMPQ`.
- **Blends.** `vblendmps`/`vblendmpd`/`vpblendmd`/`vpblendmq zmm1{k}, zmm2, S(zmm3/m)` give
  `k[n] ? src3 : zmm2`, with no write-masking (pp.126-131, 453-458). This is GCC's
  `(vec_merge op1 op2 k)` with op1 = src3.
- **Masked moves.** `vmovaps`/`vmovapd`/`vmovdqa32`/`vmovdqa64` with `{k}` need a 64-byte aligned
  memory operand and **merge** into the destination (pp.376-387; 2.1.2, p.22). There is no `{z}`
  zeroing. `k0` as a write-mask means "no mask" (2.1.2.1, p.22), so masked instructions take
  `k1`-`k7` (constraint `YL`, `imci.md:12-13`). Under a mask, the pairs `vloadunpack*`/`vpackstore*`
  **compact** the stream, so lane n is not at A+n·e unless the mask is a prefix (p.361, p.417).
- **Mask logic.** Every form is 2-operand and destructive, `k1 = k1 op k2`: `kand` (p.79), `kandn`
  `~k1&k2` (p.81), `kandnr` `k1&~k2` (p.83), `kor` (p.99), `kxor` (p.105), `kxnor` (p.103; with
  `k1 = k2` it sets 0xFFFF). `knot k1,k2` (p.97). `kortest k1,k2` sets ZF if the OR is 0 and CF if
  it is all ones, over 16 bits (p.101). `jkzd`/`jknzd k, rel` branch on a mask (pp.73-78).
  `kmerge2l1h k1,k2` gives `k1 = {k2[7:0], k1[15:8]}`, so with `k2 = k1` it swaps the two bytes
  (p.91). `kmerge2l1l k1,k2` sets `k1[15:8] = k2[7:0]` (p.93).
- **Mask and GPR.** `kmov k,k`, `kmov r32,k` (zero-extends) and `kmov k,r32` (low 16 bits)
  (p.95). Using a memory operand is `#UD` (p.96). `kconcath`/`kconcatl r64,k1,k2` pack two masks
  into a GPR (pp.85-88), and `kextract k,r64,imm` takes a 16-bit field (p.89). Spills already go
  through a GPR (`imci.md:93-110`).

**Lacks against AVX-512F (read).** There is no `kshift*`, `kunpck*`, `ktest`, `kadd`, 3-operand
or `b`/`w`/`d`/`q`-suffixed mask logic. There is no zeroing-masking. FP compares have 8
predicates, not 32. There are no 64-bit-element integer compares, tests or min/max.

**Inferred: FP compare mapping (C semantics).** EQ→eq, NE→neq, UNORDERED→unord, ORDERED→ord
are quiet. LT→lt and LE→le signal, as C `<`/`<=` should, and GT/GE are the same with operands
swapped. The quiet UNGE, UNGT, UNLE and UNLT (from `isgreaterequal` etc.; `nlt`/`nle` would
signal) are `kord = vcmpord a,b; k = vcmplt/le{kord} a,b; knot k`: the masked-off NaN lanes do not
compare, so they raise nothing (p.22). That needs the card to confirm, because the same page's
"no violation on masked-off elements" was wrong for page faults (S3-03). LTGT is
`vcmpord` followed by `vcmpneq{kord}` (2 instructions, quiet, as i386's NEQ_OQ). UNEQ is LTGT
followed by `knot` (with `knot`, padding needs care in QI). AVX-512's immediates 0x05-0x18
(`i386-expand.cc:4784-4822`) do not encode on KNC.

**Inferred: V8DI compares.** A 32-bit compare yields a bit per dword, at 2j and 2j+1. An 8-lane
mask needs bit j, and nothing in the mask file compacts bits. Two ways out, neither card-checked:
(i) `kmov` to a GPR, then a shift/or/and compress and `kmov` back (about 8 scalar instructions);
(ii) build a vector whose qword j is all-ones where true, then `vcmppd k,z,z,{unord}` (an
all-ones qword is a QNaN; unord is quiet). The NaN gives bit j directly. For LTU, the borrow chain
of section 3 leaves the 64-bit borrow in the odd bits of `kb`; then
`vpsbbd z{kodd}, kb, zero` (z zeroed) and `vcmppd {unord}`, about 6-7 instructions. LT also
XORs the sign bit of both sides. EQ is `vpxorq`, `vpord x,x{cdab}`, `vptestmd`,
`vpblendmd` and `vcmppd {ord}`. Recommendation: S4-02 leaves V8DI `vec_cmp` off. Cases (a)-(d)
on float and int32 do not need it, and tails use `while_ult` (section 5).

**Inferred: mask width conversion (mixed 16/8-lane loops, optional).** Unpack low is a
`kmov`, unpack high is `kmerge2l1h k,k` (1 instruction, no `kshift` needed), and pack is
`kmerge2l1l lo,hi`. The `sse.md` names exist (`vec_pack_trunc_qi` 19557, `vec_unpacks_lo_hi`
22245, `vec_unpacks_hi_hi` 22289). The `hi` one's RTL claims a `lshiftrt` (a zero high byte),
so KNC needs its own unspec insn behind a dispatch.

## 3. V8DI add and sub with the carry forms (S4-04)

**Read.** `vpaddsetcd zmm1{k1}, k2, S(zmm3/m)`: zmm1 += src, with carry n into k2[n]
(p.435). `vpadcd zmm1{k1}, k2, S(zmm3/m)`: zmm1 += src + k2[n], with the carry back into k2[n]
(p.429). `vpsubsetbd` (p.565) and `vpsbbd` (p.524) do the same for subtraction with a borrow.
These four are destructive in zmm1; lanes with k1 off keep zmm1 **and k2** (pp.429, 435). The
carry stays in its own lane's bit and never moves to bit n+1. `vpaddd`/`vpsubd` are
3-operand, `zmm1 = zmm2 ± src` (pp.432, 556). Register swizzle `{cdab}` swaps the inner pairs of
dwords (Table 2.2, p.29), so it exchanges the low and high dwords of each qword. `vmovdqa32`
accepts a swizzled register source (p.382).

**Inferred sequence** (qword j = dword 2j low, 2j+1 high; `kodd` = 0xAAAA in `k1`-`k7` and
`zero` hoisted out of the loop):

```
add:  vmovdqa32  t, a{cdab}         ; t[2j+1] = a.lo
      vpaddsetcd t, kc, b{cdab}     ; no write-mask: kc[2j+1] = carry(a.lo+b.lo), kc fully defined
      vpaddd     r, a, b            ; r.lo final, r.hi = a.hi+b.hi
      vpadcd     r{kodd}, kc, zero  ; r.hi += carry
sub:  same with vpsubsetbd (borrow), vpsubd r, a, b, and vpsbbd r{kodd}, kb, zero
```

This is 4 vector instructions plus 2 loop invariants. `zero` can be a `{1to16}` memory
broadcast. RTL: an `imci.md` `define_insn_and_split` on `(plus:V8DI ...)` that splits before
reload into new pseudos for `t`, `kc` (HI, clobbered) and `kodd`.

**Finding for S4-04.** `addv8di3` and `subv8di3` already exist in `sse.md`
(`<insn><mode>3` over VI_AVX2, `sse.md:16597-16603`; V8DI entry `"TARGET_AVX512F"`,
`sse.md:571-575`; VI_AVX2 is used 17 times). An `imci.md` expander with that name would collide
(ADR-0005 point 2). So S4-04 needs a shared change after all: S3-09's form for V16SI with a V8DI
entry, or an expander-only iterator in that expander. `ix86_fixup_binary_operands_no_copy` is
already hooked (`i386-expand.cc:1336-1337`).

## 4. Reuse audit

**Reusable through an ADR-0006 hook (read; each cited).**

| Item | Today | Hook |
|---|---|---|
| `ix86_get_mask_mode` | AVX-512 branch (`i386.cc:26080-26090`) | condition term |
| `vec_cmp`/`vec_cmpu` mask expanders | `sse.md:5283-5294`, `5382-5393`; iterators V48H_AVX512VL/VI48_AVX512VL have ungated 512-bit entries (`sse.md:317-324`, `495-497`) | condition `|| ix86_knc_..._p (<MODE>mode)` (excludes V8DI and the narrow modes); entry hook in `ix86_expand_mask_vec_cmp` (`i386-expand.cc:4835`) |
| `vcond_mask` | template-only, `sse.md:5506-5512` | condition; the vec_merge is matched by an `imci.md` blend |
| `maskload`/`maskstore` | template-only, `sse.md:29599-29607`, `29628-29635` | condition plus a first-statement KNC dispatch (`movxi` precedent) |
| `cond_fma`/`fms`/`fnma`/`fnms` | VFH_AVX512VL ungated at 512 (`sse.md:513-518`), body emits `fma<mode>4` plus a vec_merge (`sse.md:6340-6360`) | condition only; `fma<mode>4` is already KNC |
| `cond_<plusminus>`, `cond_mul` FP | VFH has V16SF/V8DF `"TARGET_AVX512F"` (`sse.md:392-398`) and is used 61 times | expander-only iterator (`VMOVE_KNC` precedent, `imci.md:16-25`); body `gen_<op><mode>3_mask` RTL matched by an `imci.md` masked insn |
| int `smin/smax/umin/umax` | iterator used only by this expander (`sse.md:951-954`, `18040-18046`) | V16SI entry plus a mode-limited condition |
| `abs`/`neg` | VFB gated and used by insns (`sse.md:414-420`, `2603-2619`) | expander-only iterator or audited entry; entry hook in `ix86_expand_fp_absneg_operator` (`i386-expand.cc:2173`) |
| masked epilogue choice | `ix86_vector_costs::finish_cost` (`i386.cc:26995-27067`), tune off for generic (`x86-tune.def:667-668`) | condition term (section 5) |
| mask pack/unpack | `sse.md:19557`, `22245`, `22289` | condition plus dispatch (optional) |

**Must be new in `imci.md` (read: encoding or semantics differ).**
- Compares: AVX-512 `UNSPEC_PCMP` insns use EVEX and 5-bit FP predicates. KNC needs MVEX and 3
  bits, and an optional write-mask input for the guarded quiet forms.
- Blends, masked arithmetic (`*knc_<op><mode>3_mask`) and masked aligned moves: MVEX, merge only.
- Mask logic, `kortest`, `jkzd`, `kmerge2l1*` and QI/HI `kmov`: `sse.md:2115-2590` (`kandw`
  3-operand VEX.L1, `kshift`, `kunpck`, `ktest`) and the `k` alternatives of `*movhi_internal`
  and `*movqi_internal` (`i386.md:3023`, `3190`) are AVX-512 encodings. Rule 4 forbids widening
  them.
- `while_ult<GPR><mask>`, `fmin`/`fmax<V>3`, and the V8DI carry split: no i386 instance exists,
  so the names are free.
- `ix86_expand_mask_vec_cmp` (`i386-expand.cc:4835-4864`) cannot serve FP (immediates). Its
  integer immediates match, but it emits an AVX-512 unspec, so delegate at entry instead.
  `ix86_expand_sse_cmp`/`_movcc`/`ix86_use_mask_cmp_p` (`i386-expand.cc:4221-4290`, `4367`) are
  SSE paths that KNC never reaches.

**Caution (read).** Several of these iterators have **ungated** 128/256-bit entries (for
example VI124_256_AVX512F_AVX512BW: V32QI, V16HI, V8SI). A bare `|| TARGET_KNC` in the condition
would enable those modes, so every widened condition must test the mode (`ix86_knc_packed_mode_p`,
as `sse.md` `mov<mode>` already does).

## 5. Masked tails (S4-05)

**Read: S3-03's card table** (`knc-unaligned-probe.md`, "Card results"):
F1 a pair wholly inside mapped memory never faults; F2 an unaligned half touches its whole line
whatever the mask (`mask-start` low, `mask-end` high); F3 at a 64-byte aligned address the high
half touches nothing (`high-end`); F4 an aligned load or store faults on an unmapped line even
with an empty mask (`aligned-guard`); F5 an aligned full or empty access on a mapped line does not
fault (`aligned-end`).

**Read: GCC 16 machinery.** `param_vect_partial_vector_usage` is 0 on i386
(`i386-options.cc:3176`). A target asks for a masked epilogue per loop by setting
`m_suggested_epilogue_mode` and `m_masked_epilogue = 1` in `finish_cost` (`i386.cc:27065-27066`;
`tree-vectorizer.h:1833-1839`). The vectorizer reads that back (`tree-vect-loop.cc:3095-3099`,
`3208-3212`) and with `masked_p = 1` uses partial vectors when it can
(`tree-vect-loop.cc:2077-2108`). Masks come from WHILE_ULT (`vect_verify_full_masking`,
`tree-vect-loop.cc:999-1103`), which is tried before the AVX-512 style (`2386-2387`). The AVX-512
style compares an IV vector, so 8-lane masks would need a V8DI LTU (`1186-1218`). Every access
needs `maskload`/`maskstore`. Every FP operation needs `cond_<op>`, because with
`-ftrapping-math` it "could trap" (`tree-vect-stmts.cc:6805-6831`). Masked stores are already
wrapped in an `if (mask != 0)` by default (`targhooks.cc:1646-1649`, `tree-vectorizer.cc:1413-1415`),
but loads are not, and only in vectorized loops.

**The rule (testable).** A masked vector access is emitted only so that **every 64-byte line an
instruction names contains at least one active element of that access**, an active element being
one the scalar program accesses at that point. With F1-F5 this means:
1. An aligned `vmov*{k}` is issued only if k is non-empty (F4). Given that, it is safe, because its
   one line holds an active element and so is mapped (F5).
2. A misaligned masked access never uses a pair with a non-prefix mask (compaction, p.361). It is
   expanded as an **aligned split**: lines L0 = A & -64 and L1 = L0 + 64, s = (A & 63)/e, data
   rotated with one `vpermd` (p.480), masks `(k << s)` and `(k >> (L - s))` computed in a GPR,
   and up to two aligned `vmov*{k}` merged into one register for loads. Each line is skipped with
   `jkzd` when its mask is empty. Only active lanes are written, so no store race is introduced.
3. A prefix-masked pair (the remainder after the main loop) issues its high half only when
   `n·e > 64 - (A mod 64)` (F2 `mask-end` faults otherwise; F3 makes A mod 64 = 0 free).
4. `maskload`'s else value is 0: a `vpxord` precedes the merge, since there is no `{z}`.

**Test (for S4-05's acceptance).** For each of the four modes, every element offset o in 0..L-1,
and n = 0..65: arrays placed so that the last element ends flush against a `PROT_NONE` page, and
in a second run so that the first starts right after one. Run a copy/add loop with the masked
epilogue forced, and an if-converted `if (c[i]) p[i] = v` where `p` is valid only where `c` is
true. Expect no fault, exact results, and untouched sentinels. Each case names its S3-03
counterpart: n a multiple of L must issue no access at G (`aligned-guard`); a short misaligned
remainder must not issue the high half (`mask-end`).

**What GCC 16 offers versus what stays off (inferred).**
- Use: alignment peeling (the cheap model peels but does not version); a masked **epilogue only**
  through the `finish_cost` hook; `while_ult<DI/SI><HI/QI>` in `imci.md` (mask
  `= (1 << min(rem, L)) - 1` in a GPR, then `kmov`; no vector compare, so 8-lane loops work too);
  `maskload`/`maskstore` per rules 1-4; `cond_add/sub/mul/fma*` for V16SF/V8DF.
- Profitability, not safety: the KNC `finish_cost` term asks for a masked epilogue only when every
  data reference is known 64-byte aligned after peeling (one guarded `vmov*{k}` each). Otherwise
  the scalar x87 epilogue stays (ADR-0005 point 4). Safety is in the expander, so
  `-fvect-cost-model=unlimited` cannot break it.
- Stays off: `param_vect_partial_vector_usage` stays 0 (no fully masked main loops); no
  `len_load`/`len_store`; no AVX-512-style IV-compare masks; no masked gather or scatter; no pair
  under a non-prefix mask; no masked access with an empty mask; no read past the array relying on
  page granularity.

## 6. Shared-line estimate (S4-02 to S4-05)

Measure today: 234 changed lines and 75 hunks in shared files
(`git diff --numstat releases/gcc-16.2.0 knc -- gcc/`, excluding `i386-knc.*`, `imci.md`,
`linux-k1om.h`). Counts are added plus deleted lines, as in ADR-0005.

| Ticket | Hunk (ADR-0006 form) | Lines |
|---|---|---|
| S4-02 | `i386.cc` `ix86_get_mask_mode` term | 1 |
| | `sse.md` `vec_cmp`, `vec_cmpu` conditions (2 hunks) | 4 |
| | `i386-expand.cc` `ix86_expand_mask_vec_cmp` entry delegation | 2 |
| S4-03 | `sse.md` `vcond_mask` condition | 2 |
| | `sse.md` `maskload`, `maskstore` condition plus dispatch body (2 hunks) | 14 |
| | `abs`/`neg`: condition, VFB entries or expander-only iterator, `i386-expand.cc` entry (2-3 hunks) | 6-10 |
| | int min/max: iterator entry plus condition (2 hunks) | 4 |
| S4-04 | `<insn><mode>3` V8DI: 0 if S3-09 adds the KNC iterator first, else iterator plus condition | 0-8 |
| S4-05 | `i386.cc` `finish_cost` masked-epilogue term | 2-4 |
| | `cond_fma`/`fms`/`fnma`/`fnms` conditions (4 hunks) | 8 |
| | `cond_<plusminus>`/`cond_mul`: expander-only iterator, or audited VFH entries (1-2 hunks) | 4-16 |
| optional | mask pack/unpack conditions plus dispatch (3 hunks) | 8 |

**Total:** about 47-75 lines in 16-20 hunks (55-83 lines in 19-23 hunks with the optional row).
That takes the measure to about 280-317 lines. Mask logic, QI masks, spills, `while_ult`,
`fmin`/`fmax`, the carry split and V8DI compares add nothing to shared files.

## ADR-0007 inputs

1. Mask modes: HI for V16SF/V16SI and QI for V8DF/V8DI, through one term in
   `ix86_get_mask_mode`. Amend ADR-0004 point 2: `k1`-`k7` hold HI and QI. QI bits 15:8 are
   undefined, and 16-bit consumers (`kortest`, `jkzd`, `kmov r32`) must mask them.
2. Shared hooks only as in section 4. Every widened expander condition tests the mode. Iterators
   used by insns get expander-only copies, never a widened entry without an S3-01-style audit.
3. All compare, blend, masked-move, masked-arithmetic and mask-logic insns are new `*knc_` insns
   in `imci.md`. Write-masks use `k1`-`k7` only. There is no `{z}`: a zero else value costs a
   `vpxord`.
4. FP compares follow section 2's mapping. Quiet unordered relations use an `ord`-guarded masked
   compare. The card must confirm that a masked-off NaN lane raises no invalid flag.
5. V8DI: add and sub use the 4-instruction carry sequence (`{cdab}`, `vpaddsetcd`, `vpaddd`,
   `vpadcd{kodd}`). `addv8di3` collides with `sse.md:16597`, so S4-04 needs a shared form.
   V8DI compares stay off in S4.
6. Masked tails: the line rule of section 5. Safety lives in the `maskload`/`maskstore` expander
   (guarded aligned split; prefix pairs only), profitability in the `finish_cost` hook (all data
   references 64-byte aligned). Partial-vector usage stays 0, and masks come from a scalar
   `while_ult`.
7. Masked epilogues need `cond_<op>` for every FP operation (default `-ftrapping-math`).
8. Budget: about 47-75 shared lines over S4-02 to S4-05, taking the measure to about 280-317.
