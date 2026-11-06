# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-06 00:15.

**Next: the tech lead, on S5-15.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[###################-]` 91 of 95

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | Done | 43 of 43 tickets |
| M2 | Useful vector target | In progress | 31 of 35 tickets |
| M3 | Runtimes | Not started | Not planned in detail yet |
| M4 | Broad optimization | Not started | Not planned in detail yet |
| M5 | Program corpus | Not started | Not planned in detail yet |
| M6 | Release | Not started | Not planned in detail yet |

## Tickets

| Ticket | What | State | Latest |
|---|---|---|---|
| S0-01 | Toolchain manifest and doctor | Done | Reviewed: red commit real; tests fail on the missing-tool cases; doctor rerun OK, required tools present, d... |
| S0-02 | ISA lint | Done | knc_lint now rejects the listed non-KNC instructions in .s, .o, archives, shared objects and executables, a... |
| S0-03 | Test runner and red baseline | Done | tools/check now runs t0, t1 and t2 on the donor in about 16 seconds and records the expected baseline, with... |
| S0-04 | Card runner | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S0-05 | Donor inventory | Done | The donor inventory now covers the whole tree with port/rewrite/drop decisions, the GCC 16.2 runtime audit ... |
| S0-06 | GCC 16.2 fork and timing | Done | GCC 16.2 is checked out on branch knc in the shared build area and builds stock x86_64 C+Fortran on Cygwin ... |
| S0-07 | Benchmark corpus and coverage estimate | Done | We now have a proposed public benchmark corpus (PolyBench, STREAM, NPB, HPCG, zlib, SQLite, with bzip2 and ... |
| S0-08 | Toolchain independent of PhiWeather | Done | The shared k1om gcc, g++ and gfortran were rebuilt so their assembler, linker and sysroot all resolve insid... |
| S0-09 | T1 scan sees KNC mask-branch loops | Done | The T1 check now recognises KNC vector loops that close with the mask branches jknzd and jkzd, so correct G... |
| S0-10 | Card sysroot links Fortran, libm and pthreads | Done | Fortran programs and C programs using -lm, -lpthread, -ldl or -lrt now link with default flags against the ... |
| S1-01 | Tickets can change the GCC fork | Done | Tickets marked gcc: yes now get their own branch in the GCC fork, count its changes in the size budget, sho... |
| S1-02 | GCC 16.2 builds for k1om-mpss-linux | Done | GCC 16.2 now configures and builds its C compiler for k1om-mpss-linux, using the shared KNC assembler, link... |
| S1-03 | tools/check runs source-level tests against GCC 16 | Done | tools/check t1 --compiler gcc16 now compiles each tests/t1/*.c test and checks its scan, scan-not, per-func... |
| S1-04 | -march=knc with no SSE, AVX, MMX, CMOV, FCOMI or MFENCE | Done | GCC 16 now accepts -march=knc (the k1om default): it predefines __KNC__ and no SSE/MMX/AVX macros, rejects ... |
| S1-05 | Integer C assembles with as 2.22 and lints clean | Done | All 2003 GCC torture compile files now build for KNC at -O0, -O2 and -O2 -g and assemble with the card's ol... |
| S1-06 | K1OM link defaults | Done | GCC 16 now targets the K1OM ABI by default: it passes --march=k1om to as and -m elf_k1om to ld, uses the /l... |
| S1-07 | Milestone M0 evidence note | Done | M0 is settled as adjust: GCC 16.2 builds a k1om cc1 whose assembly the 2.22 assembler accepts, an options-f... |
| S2-01 | Design for zmm and mask registers under -march=knc | Done | The register design for KNC is settled on paper: all 32 zmm and 8 mask registers become usable under -march... |
| S2-02 | Float and double arguments and results in zmm lane 0 | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-03 | Varargs with the donor's register save area | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-04 | Scalar transfers through memory and mask scratch | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-05 | x87 compares and zmm spill alignment | Done | gcc16 now has tests proving it picks the IEEE-correct x87 compare for every float, double and long double c... |
| S2-06 | Atomics without cmpxchg16b, spin hint by delay | Done | Native line ticked: passed on the card in the lead's run of S2-10's batch (`docs/research/card-runs-s2.md`). |
| S2-07 | GCC 16 builds its own static libgcc for k1om | Done | GCC 16 now links KNC programs with its own static libgcc, crtbegin and crtend, with no donor files, and its... |
| S2-08 | hello, scalar FP and printf on the card | Done | Card line ticked: the 256-program torture batch passed 256 of 256 on the card with `-j 30` (`docs/research/... |
| S2-09 | GCC 16 builds gfortran, and the secondary-reload reproducer passes | Done | The shared GCC 16 build now includes a gfortran compiler (no Fortran runtime library yet), and the Fortran ... |
| S2-10 | First card runs for the queued native checks | Done | Ten programs ran on the shared Xeon Phi with output identical to their references: hello, the m1_affine fix... |
| S2-11 | card_run follows the shared card rules and runs hello on the card | Done | tools/card_run now runs programs on the shared Xeon Phi under the owner's card rules (ledger lines, cores 3... |
| S2-12 | card_run polls the card gently and reports what it reaped | Done | card_run now checks job status on its existing SSH session with backoff to 5 s and opens output connections... |
| S2-13 | Card tests pass again, and approve runs them | Done | All card tests in tests/tools pass again under Cygwin Python, and pm.py approve now refuses to merge any br... |
| S2-14 | card_run stages extra files, so one job can run a batch | Done | card_run can now stage extra files next to the program with --file (size-capped by maxStageMiB, unsafe or d... |
| S2-15 | -ffast-math links on KNC with a KNC crtfastmath | Done | Card line ticked: `.work/_shared/tmp/S2-15/Ofast.mic` exits 0 on the card and prints `MXCSR after startup: ... |
| S2-16 | Card batch files are readable by the lead | Done | Card batch programs are now written 0755 and data files 0644, so the lead can read and stage them; Cygwin n... |
| S2-17 | card_run tolerates ending processes, and stages batch files correctly | Done | card_run now skips processes that end mid-snapshot instead of failing the run, keeps a finished program's r... |
| S2-18 | The card test driver runs programs in parallel on our 30 cores | Done | Card line ticked: the 256-program torture batch passed 256 of 256 on the card with `-j 30` (`docs/research/... |
| S2-19 | The card snapshot's awk runs under BusyBox | Done | The card runner's process snapshot no longer trips BusyBox awk, and a T0 test now rejects any card awk line... |
| S3-01 | Packed modes and IMCI patterns in GCC 16: entry points, audit and line estimate | Done | The packed-mode audit (docs/research/knc-packed-modes.md) is accepted: it maps every pattern and hook the f... |
| S3-02 | One helper for optional tools/check selections | Done | tools/check optional selections now come from one table, several flags given together all run and each repo... |
| S3-03 | Native probe of unaligned pairs and masked aligned forms at page boundaries | Done | Acceptance lines ticked: the lead ran the probe on the card, 3,148 cases with 0 failures; the fault table a... |
| S3-04 | Packed modes legal under -march=knc, with aligned moves, spills and constants | Done | Under -march=knc, 64-byte float, double, int and long long vectors now live in zmm registers, with aligned ... |
| S3-05 | Unaligned packed moves through load and store pairs | Done | Packed copies through pointers of unknown alignment now compile, for all four 512-bit modes, to unmasked lo... |
| S3-06 | Packed FP add, sub, mul, FMA and broadcasts for V16SF and V8DF | Done | Under -march=knc, 512-bit float and double vectors now compile to packed add, subtract, multiply, fused mul... |
| S3-07 | Auto-vectorization on zmm, with x87 peel and remainder; m1_affine T1 and T2 green | Done | With -mknc, GCC 16 now auto-vectorizes simple float and double loops at default -O2 into packed zmm multipl... |
| S3-08 | Fortran twin of m1_affine vectorizes and links | Done | The Fortran twin of the M1 affine kernel now builds with GCC 16 gfortran, vectorizes on zmm (FMA at -ffp-co... |
| S3-09 | Packed integer add, sub, mul, logic and broadcast for V16SI; logic for V8DI | Done | 32-bit integer vector add, sub, multiply, and/or/xor and broadcasts now compile to single IMCI instructions... |
| S3-10 | Card batch for Sprint 3 and m1_affine | Done | Card run done. Every row passes: m1_affine three ways, vector, FP and special-value programs, ABI cross-lin... |
| S3-11 | Milestone M1 note: fixture, line counts, ICE classes and backend cost comparison | Done | The M1 evidence note is in: x86_64 assembly is unchanged by our shared i386 lines (1,962 identical files at... |
| S3-12 | tools/portability: forward-port drill and x86_64 unchanged check | Done | tools/portability.py now checks whether the KNC changes still merge onto newer GCC (master has 2 conflicts,... |
| S3-13 | Move KNC code out of shared i386 files into i386-knc | Done | KNC code now lives in i386-knc.cc/.h behind one-line hooks in the shared i386 files (shared diff 324 lines/... |
| S3-14 | Native TLS for k1om, and every x86_64-only configure case that misses k1om | Done | GCC 16 now emits native %fs TLS for k1om, matching the donor's sequences at -O2, -O2 -fPIC and -O0 instead ... |
| S3-15 | ABI gaps: packed vectors through varargs and ms_abi, complex values, rounding mode across calls | Done | Packed vectors passed through varargs or ms_abi now give the KNC ABI error instead of crashing the compiler... |
| S3-16 | Nothing writes to Documents/_shared from the main checkout | Done | Torture and x87 probe outputs now stay in the repository's .work/_shared when run from the main checkout, a... |
| S3-17 | card_run takes each process's parent from the same status read that admits it | Done | card_run no longer refuses jobs when a kernel thread's first status read fails: each process's parent now c... |
| S3-18 | card_run keeps every job's receipt, and the ledger finish line says why a job was refused | Done | card_run now saves every job's result under .work/_state/card/ (newest 200 kept), and the ledger finish lin... |
| S3-19 | card_run's snapshot silences the status redirect before it can fail | Done | A card process that exits mid-snapshot no longer makes card_run refuse the job, and a lint stops the redire... |
| S3-20 | 64-byte XImode memory-to-memory copy ICEs (gcc.c-torture/execute/pr85169.c) | Done | Card after merge: pr85169 passes, and the full execute suite passes 1,681 of 1,681 at 73cc9c03798 (docs/res... |
| S3-21 | Unaligned packed accesses need element alignment; byte-aligned ones must not use load/store pairs | Done | Byte-aligned vector copies (like pr65369) no longer use the KNC load/store pair instructions that need elem... |
| S3-22 | The last three KNC blocks in shared i386 code become hooks (ADR-0006 rules 1-4) | Done | The last three KNC blocks in shared i386 code (zero-call-used-regs, the 16-byte CAS macro, the varargs save... |
| S3-23 | KNC's atomic_storeti survives upstream's new one; trunk builds C-only and runs T1 and T2 | Done | KNC's 128-bit atomic store and exchange now live in i386-knc.cc helpers with unchanged output, and upstream... |
| S3-24 | Skip GCC builds that are already current (shared tree and the x86 check's stock tree) | Done | GCC builds are now skipped when nothing changed: tools/gcc_build.py --if-stale skips the shared tree's make... |
| S3-25 | va_arg of an unsupported KNC type leaves a broken expansion; release builds hide the ICE | Done | Rejecting va_arg of an unsupported KNC vector type now ends with its error message and no hidden compiler c... |
| S4-01 | Masks on KNC: GCC 16 entry points, IMCI forms, reuse audit and masked-tail design (ADR-0007 input) | Done | The mask design input for Sprint 4 is done: KNC masks are HI for 16-lane and QI for 8-lane vectors, compare... |
| S4-02 | Vector compares into k masks, mask logic and mask spills for the packed modes | Done | Float, double and int vector compares now produce KNC k masks and vectorize with blends (?: and select loop... |
| S4-03 | Blends and if-conversion: conditional loops, ?:, fabs, min and max vectorize with masks | Done | Conditional loops now vectorize on KNC: selects and conditional stores on 64-byte aligned arrays through gu... |
| S4-04 | V8DI add and sub through the IMCI carry form, so long add loops vectorize | Done | 64-bit integer vector add and sub now vectorize through KNC's carry instructions, and the shared add/sub ex... |
| S4-05 | Masked epilogues for aligned loops: while_ult, the finish_cost term, cond_<op> for FP | Done | Aligned loops (no alignment peel) now finish with a guarded masked vector epilogue instead of the x87 remai... |
| S4-06 | Batch check after S4-02, S3-09 and S4-03: x86, drill and ICE sweeps at the batch head | Done | Batch check at ae8a033c5f3: no compiler crashes in the -O2 vectorize and -O3 sweeps, 280 shared lines in 68... |
| S4-07 | Final Sprint 4 batch check at the sprint head | Done | Final Sprint 4 check at c759f17f1b9: x86 assembly identical to stock GCC 16.2 on all 1,962 files, every ups... |
| S4-08 | Small fixes from M1: the varargs V4SF assert checks alignment; S3-10 ABI expected files | Done | The varargs save path now asserts a 16-byte aligned slot and is limited to 64-bit KNC, with generated code ... |
| S4-09 | LRA folds a misaligned vector load into vaddps/vsubps/vmulps ("m" constraint), which faults on the card | Done | Vectorized float and double add, sub and mul no longer fold a misaligned array load into the instruction, w... |
| S4-10 | pm.py approve merges a GCC ticket without rewriting files in the shared checkout | Done | Approving a GCC ticket no longer rewrites the merged files in the shared GCC checkout, so the next build is... |
| S4-11 | gcc_build.py refuses a build tree whose mddeps.mk has lost the .md includes | Done | A shared GCC build tree that has lost its .md dependency list is now rebuilt and checked instead of being c... |
| S4-12 | card_run stages a whole batch in one upload, so card cores are busy instead of waiting on SSH | Done | card_run can now ship a whole batch of programs in one packed upload, unpacked on the card by a small check... |
| S4-13 | Rebuild the x86 check's trees under the current user and run the x86 comparison at the knc head | Done | The x86 check now runs under this user from .work/_shared/portability-claude, and at the S4-04 head x86 ass... |
| S4-14 | Misaligned masked access: a guarded aligned split in KNC maskload/maskstore, tested | Done | Misaligned conditional loads and stores now use a guarded split into at most two aligned masked moves plus ... |
| S5-01 | Gather, scatter, permutes, reductions and FP min/max on KNC: GCC 16 entry points, IMCI forms, fault footprint (ADR-0008 input) | Done | Gather/scatter, permute, reduction and FP min/max design input is in: 16-lane gathers and scatters need no ... |
| S5-02 | Int and FP conversions, and memory up/down conversions for byte and word data on KNC (ADR-0008 input) | Done | Conversion design input is in: int/float and float/double conversions map to single IMCI instructions with ... |
| S5-03 | Correctly rounded vector division and square root for V16SF and V8DF: sequences, proof plan, test plan (ADR-0003 point 4 input) | Done | Correct rounding plan for vector division and square root: FP32 square root is proven exhaustively for any ... |
| S5-04 | card_run shares the card with the PhiWeather tuning session: project tag, own-budget count, timed-job refusal, staging limit, packed S3-10 batch | Done | card_run now shares the card safely with the PhiWeather tuning session: our ledger rows say project gcc-knc... |
| S5-05 | knc_lint accepts the decoded %ymm source of vcvtdq2pd, vcvtudq2pd and vcvtps2pd | Done | knc_lint no longer rejects correct vcvtdq2pd, vcvtudq2pd and vcvtps2pd, whose 8-lane register source objdum... |
| S5-06 | KNC vec_perm_const: reversed, stride-2 and interleaved loops vectorize with swizzle, vpermf32x4, vpshufd, valignd and vpermd | Done | Reversed, stride-2 and constant-shuffle vector code now uses IMCI permutes (swizzle, vpermf32x4, vpshufd, v... |
| S5-07 | KNC reductions: vpermf32x4 and swizzle trees for plus, min/max and logic, with no stack accumulator | Done | Integer sum, min/max and logic reductions, and FP sums under -ffast-math, now end in an IMCI vpermf32x4 and... |
| S5-08 | KNC same-width conversions: int32/uint32 to and from float as single vcvtfxpnt instructions (the ADR-0008 named-insn exception) | Done | Int32/uint32 to float and float to int32/uint32 loops now vectorize as single IMCI vcvtfxpnt instructions w... |
| S5-09 | Card probe of vrcp23ps, vrsqrt23ps and vgetmant (S5-03 P1a-e), to back the division and square-root proofs | Done | A card probe now measures vrcp23ps and vrsqrt23ps against the error bounds the FP32 division and square-roo... |
| S5-10 | Correctly rounded FP32 vector square root for V16SF (S5-03 ticket A) | Done | Vectorized FP32 square root on KNC is now correctly rounded for every one of the 2^32 inputs, checked on th... |
| S5-11 | Correctly rounded FP32 vector division for V16SF, with cond_div (S5-03 ticket B) | Done | Vectorized FP32 division on KNC is now correctly rounded, with IEEE flags, in all four rounding modes: 1.8 ... |
| S5-12 | KNC float/double-width conversions: vcvtps2pd, vcvtpd2ps, vcvtdq2pd, vcvtfxpntpd2dq with vpermf32x4 halves | Done | Loops that convert between float and double, or between int and double, now vectorize on KNC with full 512-... |
| S5-13 | KNC 16-lane gather and scatter: vgatherdps/vpgatherdd and the scatter forms in a jknzd loop, through the optabs | Done | Loops that read or write float or int arrays through a signed int index (a[i] = b[idx[i]], a[idx[i]] = b[i]... |
| S5-14 | KNC 8-lane gather and scatter for V8DF/V8DI through the builtin hooks, reading the low 8 dwords of a V16SI index | Done | Loops that read or write double or long arrays through an int index now vectorize on KNC as two 8-lane gath... |
| S5-15 | KNC FP min/max: MIN_EXPR/MAX_EXPR and fmin/fmax as vgminps/vgmaxps (pd), with their reductions | Waiting for review | GCC 41a1abe5bbb built incrementally; red failed as expected; T0 52 passed; T1/T2 passed except obsolete sca... |
| S5-16 | KNC byte and word data: V16QI/V16HI transport modes, widening up-converting loads and narrowing down-converting stores | Not started |  |
| S5-17 | Sprint 5 mid batch check after S5-06, S5-07 and S5-08 | Done | x86 check (lead, portability-claude) at knc 9690ac8906a vs releases/gcc-16.2.0: -O2 and -O2 -mavx512f ident... |
| S5-18 | Final Sprint 5 batch check at the sprint head | Not started |  |
| S5-19 | card_run shares cores with the PhiWeather session - compact per-job core claims from the ledger, and round-robin turns for benchmark jobs | Done | card_run now packs each job onto whole cores taken from 59 downward, shares the card with the PhiWeather se... |
| S5-20 | card_run refuses engineer sandbox sessions, so card jobs stay with the lead | In progress |  |

## Recent activity

- 2026-11-06 00:15 **S5-15** engineer submit: GCC 41a1abe5bbb built incrementally; red failed as expected; T0 52 passed; T1/T2 passed except obsolete scans, now fixed bb09b54 and both pass. Log...
- 2026-11-06 00:13 **S5-15** lead answer: Yes: replace the obsolete 'no vgmin/vgmax in fmin_*/fmax_*' scans in knc-mask-cond with positive scans (ADR-0008 point 3 as amended; the S4 ban pre...
- 2026-11-06 00:12 **S5-15** engineer ask: GCC 41a1abe5bbb builds; new minmax T1 passes. Existing knc-mask-cond-O2/O3 ban vgmin in fmin_f32. Reproducer: c[i]=__builtin_fminf(a[i],b[i]) now v...
- 2026-11-05 23:34 **S5-15** lead answer: Yes: define a local code attribute in imci.md (e.g. knc_maxmin: smax 'max', smin 'min'), not in sse.md, and continue.
- 2026-11-05 23:33 **S5-15** engineer ask: Two builds failed: first ssescalarmode before definition (fixed); second genflags: unresolved iterator in *knc_reduc_<maxmin>v8df_swizzle. Reproduc...
- 2026-11-05 23:18 **S5-14** lead approve: Loops that read or write double or long arrays through an int index now vectorize on KNC as two 8-lane gathers or scatters per 16 indices, and pass...
- 2026-11-05 23:08 **S5-14** engineer submit: GCC ab967b42a6e: both one-line ABI hooks share the private gather type/decl predicate. Incremental build and full T1 PASS (four -O3 scans). All REA...
- 2026-11-05 23:02 **S5-14** lead answer: Yes. Use one helper, e.g. ix86_knc_gather_builtin_type_p (fntype or decl), shared by both hooks, with each i386.cc dispatch one line; zmm0 for exac...

## Cost

- From the script, engineer: 219 sessions, 530.0M input tokens
- From the script, lead: 184 sessions, 58.7M input tokens
- Started by hand, Claude: 9 sessions, 1030.9M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 12.6 GiB of 100 GiB. 178 GiB free on the drive.
