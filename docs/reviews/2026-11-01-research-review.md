# Review of the GCC-KNC research report

**Reviewer:** Claude. **Date:** 2026-11-01.
**Subject:** Astra's [technical research report](../../GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md).

**Scope correction from the owner, same day:** GCC-KNC is a new, general-purpose project
for any program that builds with GCC. It has nothing to do with PhiWeather or PhiChat.
The report's application measurements are background evidence about the hardware, not
goals. The plan has been updated; F8's effect below reflects this.

## Verdict

**Adopt the direction, with corrections.** A KNC subtarget in the i386 backend of
a modern GCC is still the right architecture, and the report's discipline on
measurement and floating-point policy is good. But it overstates what the donor
compiler gives us. Almost all of the vector backend is new work, and that work
has to be written from the ISA manual, not ported. The plan is sized for that.

The method was to run the donor compiler and assembler locally, read the ISA
manual, and compare retained numbers with their source files. No card job ran.

## Findings that change the plan

Severity reflects the effect on plan and schedule. "Measured" means I ran it on
2026-11-01; the commands are in [the appendix](#appendix-reproducing-the-probes).

### Critical

**F1. The donor has no vector code generation to port.** (Measured.)
`ix86_preferred_simd_mode` returns `word_mode` when `!TARGET_SSE`, and KNC sets no
SSE. At `-O3`, `affine_f32` compiles to x87 only, with the note `not vectorized:
no vectype for stmt`. `knc.md` is about 265 lines and covers scalar moves and reloads.
The report's table lists "instruction forms" as reusable, and its §16.2 says to
"adapt the smallest target slice", which reads as a port.
*Effect:* the donor supplies ABI, scalar lowering, reload lessons and options.
The IMCI patterns are net-new. M1 is split into scalar and vector sprints.

**F2. `-mavx512f` is not a route to KNC vectors.** (Measured.) On the same loop the
donor does emit one `vfmadd132ps`, but its peel and remainder code uses
`vfmadd132ss`, and a divide loop uses `vdivsd`. The assembler rejects both on
`k1om`, so the file does not assemble. This is why the donor's README splits
sources. Tails and scalars cannot be repaired by adjusting flags.
*Effect:* [ADR-0002](../adr/0002-imci-separate-isa.md): IMCI gets its own ISA flag
and pattern file, and KNC never sets `TARGET_AVX512F`.

### High

**F3. There is no hardware vector divide or square root, and the report does not
plan for it.** (ISA manual and assembler.) The manual has no `VDIV*` or `VSQRT*`
entries, and the assembler rejects `vdivps` and `vsqrtpd`. The only hardware
estimates are `vrcp23ps` and `vrsqrt23ps`, and they are FP32 only. The report
treats division as part of a math library, but it also forbids implicit fast-math.
So plain `a / b` in a vectorized loop needs a correctly rounded sequence, or it
must stay scalar. Numeric code divides often, so this decides whether many
loops vectorize at all.
*Effect:* [ADR-0003](../adr/0003-fp-defaults-and-division.md); its own story, E4-03.

**F4. Unaligned access and tails are harder than the report implies.** (ISA manual
and assembler.) `vmovups` does not exist, and aligned moves fault on misaligned
addresses. Unaligned access takes a `vloadunpackl*`/`vloadunpackh*` pair and
`vpackstorel*`/`vpackstoreh*`. GCC's masked-tail machinery assumes masked-out
lanes do not fault. Whether that holds for these forms at a page boundary still
has to be measured on the card.
*Effect:* the M1 fixture places arrays flush against a `PROT_NONE` page. The
masked tail design waits on a native probe, E3-01.

**F5. Gather and scatter must loop.** (ISA manual.) One execution may complete only
part of the mask, and the manual says software should re-execute it until the mask
is empty. The RTL pattern therefore contains control flow and a mask clobber, and
its cost is variable. The report treats gather only as a costing question.
*Effect:* a dedicated story, E4-02, with a test for loop lowering.

**F6. KNC breaks more of the x86-64 baseline than SSE.** (Manual App. B, assembler.)
These are unsupported: `CMOV`, `FCMOVcc`, `FCOMI`, `FCOMIP`, `FUCOMI`, `FUCOMIP`,
`CMPXCHG16B`, `PAUSE`. The assembler also rejects `mfence`, `lfence` and `sfence`.
It *accepts* `pause` even though the manual lists it as unsupported, so a clean
assemble is not proof of legality. The donor also disables direct moves between
general and vector registers, so every such transfer goes through memory. I expect
current GCC runtime libraries to depend on some of this (spin waits, 16-byte
atomics, `__float128`, SSE build flags); S0-05 replaces that expectation with a list.
*Effect:* an ISA lint over every generated object, including runtime libraries,
is a Sprint 0 deliverable and a permanent test tier.

**F7. Test-driven development needs a design the report does not give.** There is
one card, it may be used by other work, and timing runs are exclusive. I know of no
usable KNC emulator (S0-01 confirms that). The report lists validation layers, but
not a loop fast enough to run on every change.
*Effect:* seven test tiers, of which the three used on every change need no card. See
[DEVELOPMENT_CYCLE.md](../DEVELOPMENT_CYCLE.md).

**F8. The value of the project is not yet established.** The report's arithmetic is
correct: at 4× kernel speedup, reaching 3 s/step needs about 57% of runtime to be
accelerated. But no retained evidence shows that share is reachable. From the
Fairborn result (2.574× kernel, 0.869% step saving), that kernel covered roughly
1.4% of the step, assuming its gain carried through fully. PhiWeather's `CURRENT_STATE.md` also lists performance tuning as
closed, with a 5.228 s/step baseline rather than the report's 5.243.
*Effect:* the question widens to programs in general. S0-07 proposes a public corpus and
estimates vectorizable coverage from compile reports before heavy backend work, and
Gate E measures whole programs against GCC 5.1.1.

### Medium

**F9. "The retained sysroot" is three different things.** The donor comes from MPSS
3.6.1, the source lock pins an MPSS 3.8.6 SDK sysroot, and `.tools/project-host/sysroot`
was copied from the card (glibc 2.21, `libstdc++.so.6.0.21`, 2.6.38 kernel headers).
`ABI.md` records that the card's libc, libm and loader differ from a local link
sysroot. glibc 2.21 also predates libmvec, so no vector math library exists to
link against. *Effect:* ADR-0001 chooses the card-derived sysroot.

**F10. The assembler is a permanent constraint.** Upstream dropped K1OM in binutils
2.39, and our `as` identifies as 2.22.52 from 2012. GCC's prerequisites require
binutils 2.35 or newer for LTO. *Effect:* LTO is out of scope unless K1OM is forward-ported
to a newer binutils, and every GCC feature that needs a newer assembler must be
disabled or worked around.

**F11. Upstream is moving away from this hardware.** GCC 15 removed Knights Landing
and Knights Mill, so the report's "until upstream acceptance actually occurs" should
not shape planning. *Effect:* plan for a permanent private fork. Stay on the GCC 16
branch and rebase only for a concrete need.

**F12. The host is undecided.** The report says "use a modern host compiler". In
practice, WSL is not set up, the Docker daemon is not running, the system Cygwin has
no `gcc`, and the working GCC 14.4 lives in PhiWeather's private Cygwin. Its cross
tools need that Cygwin's DLLs on `PATH`, or `cc1` fails on `cygmpc-3.dll`. The
machine has 12 threads and about 16 GB of memory. *Effect:* S0-06 measures the TDD
loop on Cygwin, and Gate A decides whether to ask for WSL2.

**F13. Milestones have no exit criteria.** They say what to deliver, not when to stop
or change course. *Effect:* decision gates A to E with numeric triggers.

**F14. Provenance limits what can ship.** The lock file records that sysroot
redistribution review is still open, and the report notes confidentiality footers
on the CERN slides. *Effect:* no sysroot or vendor material enters this repository.
Release packaging is blocked on that review.

## What I checked and found correct

| Claim | Result |
|---|---|
| F7 allocator, 14.0672 → 5.5203 s/step, system share 49.67% → 11.76% | Matches `F7_ATTRIBUTION.md` |
| G1 lower bound, 5.34× | Matches `G1_PERFORMANCE.md`; upper bound not checked |
| Fairborn, 2.574×, 0.663%, 0.869% | Matches; 0.869% recomputed from step medians |
| U/V ordering, 1.85%, 6.73%, 2.82% | Matches |
| Phoenix O vs R, 2.2872% | Matches; recomputed |
| DECODE3 tokens/s figures | Matches |
| Retired P build, 10.0041 s/step | Matches the conclusion file |
| 42.8%, 1.75×, f ≈ 57% | Recomputed, correct |
| Donor commit `af7cc04` and its license | Matches the lock file and the checkout |
| KNC scalar ABI uses `zmm` lanes with x87 bodies | Matches `ABI.md` and donor output |
| GCC 16.2, 15.3 and 14.4 are the supported releases | Confirmed on gcc.gnu.org |
| C++14 host compiler, GCC 5.4 or newer | Confirmed |
| `edgcpp/compiler` is a frontend project with source-generating backends | Confirmed; publication date not checked |

**Not checked:** the LIBXSMM and ISPC release notes, the Tian and Pabst material, and
the PRACE, McCalpin and Fang sources. The report's statements about them are plausible,
and they are inputs to experiments rather than decisions. Treat them as leads.

The local report also uses absolute paths under `C:\Users\xuzhi`, which is fine in a
private repository. Check the repository's visibility before the first push.

## Appendix: reproducing the probes

```bash
K=/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap
export PATH=$K/cross/bin:$K/cygwin/bin:$PATH
k1om-mpss-linux-gcc -std=gnu99 -O3 -fopt-info-vec-missed -S affine.c -o affine.s
k1om-mpss-linux-gcc -std=gnu99 -O3 -mavx512f -S affine.c -o a512.s
k1om-mpss-linux-as --march=k1om --64 a512.s -o a512.o
```

Assembler results with `--march=k1om`:

| Accepted | Rejected |
|---|---|
| `vaddps`, `vrcp23ps`, `vloadunpacklps`, `delay`, `popcnt`, `pause`, `rep; nop` | `cmovl`, `fcomi`, `fucomip`, `mfence`, `lfence`, `sfence`, `cmpxchg16b`, `vmovups`, `vdivps`, `vsqrtpd`, `vfmadd132ss`, `vdivsd`, `addss`, `movd %eax,%xmm0` |

## Sources

- [GCC home page, supported releases](https://gcc.gnu.org/)
- [GCC prerequisites](https://gcc.gnu.org/install/prerequisites.html)
- [Intel Xeon Phi Coprocessor ISA reference 327364-001](https://www.intel.com/content/dam/develop/external/us/en/documents/327364001en.pdf), including the gather/scatter guidance and Appendix B
- [Binutils commit dropping L1OM/K1OM from gas](https://gnu.googlesource.com/binutils-gdb/+/c085ab00c7b2877e35420ee196d24f9eeb9233f4) and the [2.39 gas NEWS entry](https://src.rcs.uwaterloo.ca/xref/netbsd-src/external/gpl3/binutils.old/dist/gas/NEWS)
- [Phoronix: Xeon Phi support removed in GCC 15](https://www.phoronix.com/news/GCC-15-Drops-Intel-Xeon-Phi)
- [Open EDG compiler repository](https://github.com/edgcpp/compiler)
