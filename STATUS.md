# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-12 21:35.

**Next: GPT-6.1, on S11-21 (Exploratory WRF build with GCC-KNC (learn-only, host-side) - how far does an unmodified WRF get, and what breaks?).** Run `python tools/dispatch.py`, or ask the tech lead to.

Current tickets: `[###################-]` 200 of 205

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 17 of 17 tickets |
| M1 | Mixed native code | Done | 43 of 43 tickets |
| M2 | Useful vector target | Done | 51 of 51 tickets |
| M3 | Runtimes | Done | 48 of 48 tickets |
| M4 | Broad optimization | In progress | 18 of 23 tickets |
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
| S10-01 | 512-bit vector arguments and results under -march=knc (ADR-0014 point 1) | Done | 64-byte vectors (__m512 and vector_size(64)) can now be passed to and returned from functions under -march=... |
| S10-02 | libknc_vmath v0 - build and requalify expf, logf, powf, exp, log, pow with GCC-KNC on the card | Done | Card qualification 2026-11-11 09:32-10:37Z (268M inputs each): expf 0.5016, logf 0.8106, exp 0.5079, log 0.... |
| S10-03 | Loops call libknc_vmath - -mveclibabi=knc, by-value entry points, automatic link (ADR-0014 points 2-3) | Done | Loops that call expf, logf, powf, exp, log or pow now vectorize under -march=knc and call GCC-KNC's own vec... |
| S10-04 | Measure vector math - math kernels and a WRF-shaped physics loop, vector vs scalar libm | Done | The vector-math benchmark (expf, logf, powf, exp, log, pow and a WRF-style theta-e column loop, vector libr... |
| S10-05 | Sprint 10 batch check | Done | Card 2026-11-11 14:16-16:56Z at knc b91ca0b5e67/f81579bb82a: execute suite 1681/1681 PASS. Vector math v0 o... |
| S10-06 | Card qualification - classify powf's 848 special-case mismatches and certify pow under 1 ULP | Done | The powf and pow card failures were traced to the card's own libm (its powl gives NaN for negative x with h... |
| S10-07 | Vector math v1a - the copied functions (sin, cos, tan, log10, atan, atan2, hyperbolics, bounded groups) in libknc_vmath and the vectorizer hook | Done | Card 2026-11-11 (S10-08 build, 240 threads): full set PASS for sinf 0.499999, cosf 0.499998, tanf 0.499995,... |
| S10-08 | Vector math v1b - the rest of the libmvec set (acos, asin, cbrt, erf, erfc, exp2, exp10, expm1, log1p, log2, hypot, sincos) | Done | The vector math library now covers the whole set GCC vectorizes with glibc's libmvec: acos, asin, cbrt, erf... |
| S10-09 | User story - double-precision loops with division and square root vectorize, correctly rounded (V8DF div, cond_div, sqrt) | Done | Double-precision loops with division or square root now vectorize under -march=knc and give the correctly r... |
| S10-10 | Card harness fixes from the Sprint 10 card turn - card_qualify binary folder, vmath bench batch sizing | Done | card_qualify now runs the card binaries from knc/ and stops before any card job when one is missing, and th... |
| S10-11 | Card-only vector math failures - double sin, cos, tan, atan2 above 1 ULP, and cbrt/cbrtf crash (SIGSEGV) | Done | Double sin, cos, tan and atan2 from the KNC vector math library are now within 1 ULP on the card (0.76 to 0... |
| S10-12 | cbrt and cbrtf crash (SIGSEGV) in qualify_v1 on the card - root cause and fix | Done | The cbrt and cbrtf qualification jobs no longer crash on the card and pass (worst 0.4996 and 0.4991 ULP): t... |
| S10-13 | User story - code that calls cbrtl under -march=knc gets a safe replacement and a compile-time warning (MPSS libm cbrtl faults) | Done | Under -march=knc, calls to cbrtl (and std::cbrt on long double) now go to GCC-KNC's own safe cube root with... |
| S11-01 | User story - the best way to move data between the host and the card, measured, and how our projects use it | Done | We now have a sourced inventory of every host-card transfer path that works without changing MPSS (SSH, tar... |
| S11-02 | card_run and run_suite move bulk data by SCIF DMA at the PCIe link limit, with the SSH stream as fallback | lead | Code review: no blocker (helper-free SSH path is main plus a wc -c check; DMA latch blocks watchdog and sta... |
| S11-03 | S11-01 transfer tool rejects the card's physical /tmp path, so the native study never starts | Done | The transfer study's tool now accepts the card's real /tmp location (/var/volatile/tmp), so its card run ca... |
| S11-04 | S11-01 transfer tool - the host opens every connection, because Windows Firewall blocks inbound TCP from the card | Done | The transfer study's host side now opens every connection to the card, so Windows Firewall no longer blocks... |
| S11-05 | Research - raise KNC's real memory bandwidth from about 175 GB/s toward 75-85% of peak, with a measured plan | Done | The memory-bandwidth research plan and a validated multithreaded KNC bandwidth benchmark are ready, with a ... |
| S11-06 | Memory bandwidth - read the first card sweep, find why our numbers sit below STREAM's, and stage sweep 2 toward 264-299 GB/s | Done | The memory-bandwidth benchmark now times only the worker passes and has a corrected long-sample baseline on... |
| S11-07 | S11-01 transfer tool - the card's listener gives up before card_run relays its announcement | Done | The transfer study's card listener now waits long enough for card_run to relay its address to the host; che... |
| S11-08 | -Wknc-unsafe-cbrtl cannot be used in #pragma GCC diagnostic ("valid for  but not for C") | Done | The cbrtl warning can now be silenced around one deliberate call with #pragma GCC diagnostic in C and C++; ... |
| S11-09 | Memory bandwidth for LLM decode - a weight-streaming GEMV workload, pushed toward 264-299 GB/s of weight bytes | Done | Weight-streaming GEMV for LLM decode is measured on the card: int8 weights reach 70 billion weights/s (2.2x... |
| S11-10 | S11-01 transfer runner - choose repetitions, sizes and load states per run, so slow methods fit a card turn | Done | The transfer runner now takes --repeats, --sizes, --loads and --concurrency so a slow method fits a card tu... |
| S11-11 | M4 corpus run harness - every corpus program built by GCC 5.1.1 and GCC-KNC, run on the card with frozen inputs and a correctness check, in one command | Done | The M4 corpus harness builds 17 programs with GCC 5.1.1 and GCC-KNC and stages checked card runs; GCC-KNC b... |
| S11-12 | Sprint 11 batch check - full native suite, x86 identity, forward-port drill, ICE sweeps, runtime prefix consistency | draft |  |
| S11-13 | Senior compiler review of the Sprint 11-13 scope (Milestone M4) against our research, with recommended plan changes | Done | A senior compiler review of the Sprint 11-13 plan is in: M4 is plausible but needs a frozen scoring and mea... |
| S11-14 | M4 scoring contract and measurement protocol, frozen before any tuning | Done | M4's scoring contract is frozen in ADR-0015 with a tested scorer: strict serial -O2 versus -O2 over 17 prog... |
| S11-15 | First development-corpus baseline and profile, GCC 5.1.1 vs GCC-KNC at -O2 (E7-03 part 1) | lead | Card runs needed. Staged method at e6b8d1c1 reviewed and fine (bounded perf cpu-clock:u 99 Hz on serial PB-... |
| S11-16 | Long-double libm hazard audit - do other MPSS long double entry points fault like cbrtl? (E7-21, bounded) | Done | The card's MPSS long double libm was probed on the card: of 12 entry points only cbrtl faults, and S10-13 a... |
| S11-17 | PGO feasibility on one complete development program (reuse of S9-18's train/use path) | lead | Needs the interactive lead's card run: from the S11-17 worktree at 1d096574, run python tools/run.py --name... |
| S11-18 | M4 corpus harness v2 - card profiles, prefix record, held-out sealing, stronger checks, and the donor-failure rule | Done | The M4 corpus harness now stages all 17 programs for the 7120 and the 3100/5100 profiles with serial voting... |
| S11-19 | Second senior review - the M4 definition and the Sprint 11-13 roadmap, adjusted | Done | The M4 definition and the Sprint 11-13 roadmap are rewritten as measure, improve, decide, each sprint with ... |
| S11-20 | Research - which compiler optimizations benefit the widest range of real code on KNC, from professional to amateur, and does our corpus cover it? | Done | We now have a code-style coverage study (docs/research/code-style-coverage.md) that ranks Sprint 12 candida... |
| S11-21 | Exploratory WRF build with GCC-KNC (learn-only, host-side) - how far does an unmodified WRF get, and what breaks? | In progress | Yes. Your precheck used the wrong input: em_real's Registry/Registry must be a copy of Registry/Registry.EM... |
| S12-01 | Sprint 12 prep - static code-quality census of the development-corpus builds (spills, x87/vector transfers, addressing, calls, code size) | Done | A static code-quality census (spill/reload proxies, x87 and x87-zmm traffic, address arithmetic, calls, bra... |
| S12-02 | Sprint 12 prep - the unscored generality check set (S11-20's six programs in the code styles our corpus lacks) | Done | The six unscored generality checks (Q1-Q6: ray tracer hit dispatch and vec3 AoS, Burkardt MD, Reference BLA... |
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
| S5-15 | KNC FP min/max: MIN_EXPR/MAX_EXPR and fmin/fmax as vgminps/vgmaxps (pd), with their reductions | Done | FP min/max loops, fmin/fmax and their reductions now vectorize on KNC as vgmin/vgmax with the C NaN rules, ... |
| S5-16 | KNC byte and word data: V16QI/V16HI transport modes, widening up-converting loads and narrowing down-converting stores | Done | Byte and word arrays now vectorize on KNC through converting loads and stores (u8/s8/u16/s16 to int and flo... |
| S5-17 | Sprint 5 mid batch check after S5-06, S5-07 and S5-08 | Done | x86 check (lead, portability-claude) at knc 9690ac8906a vs releases/gcc-16.2.0: -O2 and -O2 -mavx512f ident... |
| S5-18 | Final Sprint 5 batch check at the sprint head | Done | final x86 at knc ba973dc285b (after S5-21): -O2 and -O2 -mavx512f identical=1962 different=0 both-failed=41... |
| S5-19 | card_run shares cores with the PhiWeather session - compact per-job core claims from the ledger, and round-robin turns for benchmark jobs | Done | card_run now packs each job onto whole cores taken from 59 downward, shares the card with the PhiWeather se... |
| S5-20 | card_run refuses engineer sandbox sessions, so card jobs stay with the lead | Done | card_run now refuses to run when started from a Codex sandbox account, so only the lead puts jobs on the ca... |
| S5-21 | 32-byte short vectors pass and return in memory again, as before S5-16 and as the donor does (pr109040 regression) | Done | 32-byte short vectors (such as unsigned short vector_size(32)) are passed on the stack and returned in memo... |
| S6-01 | Measurement method on KNC: clock, pinning, thread density, working sets, repetitions and noise (ADR-0010 input) | Done | KNC now has a measured timing method: raw-monotonic wall time, fixed sibling pinning for 1-4 threads per co... |
| S6-02 | M2 kernels: affine, stencil, short-loop and small-matrix as GCC-KNC vector, x87 and hand-written IMCI builds, with a timing driver | Done | The M2 yardstick is ready and correct on the card: FP32/FP64 affine, two stencils, a short loop and 8x8/16x... |
| S6-03 | Machine characterization corpus (E5-01): latency and throughput per instruction class at 1-4 threads per core, cache and memory levels | Done | A KNC characterization corpus of 104 hand-written measurements is ready to run on the card: latency and thr... |
| S6-04 | Per-loop KNC reports (E5-03): vector factor, peel and tail choice, masks, helper calls, spills and rejection reasons | Done | With -fopt-info-vec, KNC now reports each costed loop candidate: vector mode and factor, scalar peel, maske... |
| S6-05 | -mtune=knc costs and vectorizer cost model v1 from the characterization tables (E5-09, E5-02) | Done | GCC-KNC now has a KNC cost table from the card measurements: scattered-index gathers stay scalar, reduction... |
| S6-06 | KNC scheduler v0 (E5-05): U/V pipes, 4-cycle vector latency, 3-cycle AGI | Done | GCC-KNC now schedules for KNC's two pipes with the measured latencies and threads per core: stencil1 runs 4... |
| S6-07 | First gcc.dg/vect baseline for KNC: compile scans on the host, execution on the card | Done | The gcc.dg/vect suite now has a KNC baseline: of 2,001 tests, 1,329 compile (777 linked for the card), 632 ... |
| S6-08 | Sprint 6 mid batch check after S6-04 and S6-05 | Done | At the Sprint 6 head (after the cost model and scheduler) every forward-port conflict is textual, both ICE ... |
| S6-09 | ICE in expand_vec_series_expr: KNC lane-index vectors (VEC_SERIES) for V16SI/V8DI and the FP modes | Done | Loops that build lane-index vectors (VEC_SERIES) now compile on KNC instead of crashing the compiler: 6 of ... |
| S6-10 | Unrecognizable and unconstrained insns: ffsll's scalar conditional move, and constant -1 into a k register | Done | Constant 0 and -1 loads into mask registers (kxor/kxnor) and 64-bit ffs without CMOV now compile on KNC, fi... |
| S6-11 | ICE in expand_fn_using_insn for FP64 fmax/fmin loops (S5-15 follow-up) | Done | Scalar and SLP-reduction fmin/fmax on float and double now compile on KNC through vgmin/vgmax with the C Na... |
| S6-12 | card_run --benchmark refuses while another project's processes still run on the card, whatever the ledger says | Done | card_run benchmark jobs now refuse to start while another project's programs (such as wrf.mic) are still ru... |
| S6-13 | M2 driver records card power per build: watts and joules per element next to the timings | Done | Each M2 timing launch now records the card's power for each build: all three draw about 165-172 W, so GCC-K... |
| S6-14 | ICE in cprop_hardreg - (set (reg:QI k1) (const_int 0)) for a loop-store-motion flag has no *knc_movqi alternative | Done | A regression test now guards against the mask-register constant crash seen in an S6-05 work-in-progress bui... |
| S6-15 | M2 fixture for ADR-0010 amendment 2 - paired before/after GCC builds in one process, per-round random order, and a decision script | Done | The M2 fixture can now time a before and an after GCC build of the same kernels in one process, interleaved... |
| S7-01 | Shared libgcc for KNC: symbol-version ceiling for the card's glibc 2.21 and kernel 2.6.38, and what GCC 16 adds over the donor's libgcc_s (E6-01 input) | Done | The shared libgcc plan for KNC is ready: GCC 16's libgcc_s.so.1 can be a drop-in superset of the donor's on... |
| S7-02 | libgfortran slice for KNC: descriptor ABI vs the card's GCC 5 runtime, real(16) and libquadmath, and MXCSR-safe FP control (E6-02 input) | Done | The libgfortran plan for KNC is ready: a small MXCSR-safe FP backend, kinds 4/8/10 with kind 16 deferred, a... |
| S7-03 | Shared libgcc part 1: donor ABI compatibility objects and symbol map (E6-01a) | Done | GCC-KNC's libgcc now exports everything the card's donor libgcc_s.so.1 does (all 153 symbol and version pai... |
| S7-04 | Shared libgcc part 2: shared build and driver integration (E6-01b) | Done | The KNC compiler now builds a shared libgcc_s.so.1 that keeps the donor's ABI, needs nothing newer than gli... |
| S7-05 | Shared libgcc part 3: compatibility and unwind card payloads (E6-01c) | Done | The old-client and new-client libgcc compatibility and unwind test programs are built, linted and staged wi... |
| S7-06 | Shared libgcc part 4: lead native acceptance and the install decision (E6-01d) | Done | GCC-KNC's shared libgcc_s passes every compatibility and unwind test on the card (old and new clients, exce... |
| S7-07 | libgfortran part 1: KNC floating-point backend and capability contract (E6-02) | Done | libgfortran now has a KNC floating-point backend: it sets and clears the six IEEE flags and the four roundi... |
| S7-08 | libgfortran part 2: base runtime build and the descriptor and I/O slice (E6-02) | Done | libgfortran now builds for KNC, and six Fortran programs (allocation, descriptors, bounds, I/O, kind 10, mo... |
| S7-09 | libgfortran part 3: runtime isolation and packaging (E6-02) | Done | GCC-KNC's Fortran runtime installs in its private directory, static and shared programs run on the card fro... |
| S7-10 | Sprint 7 batch check after S7-05 and S7-08 | Done | Sprint 7's final compiler matches stock GCC 16.2 on x86 (1,962/1,962 identical at -O2 and -O2 -mavx512f), h... |
| S8-01 | Card checks C1-C10 for the Sprint 8 tuning block - microbenchmarks in the knc-char corpus | Done | The knc-char corpus now measures the Sprint 8 tuning questions on the card (stores, prefetch, tails, accumu... |
| S8-02 | Masked loop tails that never touch an unmapped page, chosen by length (E4-04) | Done | round 3 card confirmation (19:04-19:10Z, binaries frozen in .work/_shared/tmp/claude-s8-02-r3, outputs in c... |
| S8-03 | Two-level software prefetch for KNC loops (E5-07) | Done | KNC loops now prefetch two levels ahead (L2 2 KiB, L1 1 KiB, in bytes so strided loops work): L2-sized stre... |
| S8-04 | Small-matrix kernels: diagnose mat8 and mat16, reject low lane use (E5-11 part 2) | Done | S8-04 closes with its diagnosis and test only: the slow small-matrix loops came from an x87 detour for the ... |
| S8-05 | Re-check the scalar-add cost on mat8 and the stencils after S8-06 (E5-11) | Done | No per-loop add-cost work is needed: with the cheaper add cost mat8 now compiles to the same code as today,... |
| S8-06 | Memory-operand forms for V16SF/V8DF arithmetic and FMA (E5-17) | Done | KNC vector add, sub, mul and FMA now read aligned memory and {1to16}/{1to8} broadcasts directly instead of ... |
| S8-07 | vpmadd231d for V16SI multiply-add (E5-14) | Done | KNC now emits vpmadd231d for vector integer multiply-add: one instruction at 4 ticks latency instead of vpm... |
| S8-08 | -mtune=knc tune-flag audit (E5-12) | Done | Card 2026-11-10 05:14-06:02Z (deferred timing, frozen 020d107325d vs S8-10 knc, L2 d4, 2 launches): M2 corr... |
| S8-09 | KNC -O2 defaults: vectorizer cost model, stride versioning, predictive commoning (E5-18) | Done | Card 2026-11-10 08:36-08:40Z (frozen set .work/_shared/tmp/claude-s8-09, log .work/_shared/tmp/claude-s8-09... |
| S8-10 | Less ring traffic: 64-byte padding of per-thread data, and card check C11 (E5-16) | Done | Per-thread arrays and the OpenMP shared block now start on their own 64-byte line, and the C11 card check s... |
| S8-11 | Sprint 8 batch check and paired M2 re-measure | Done | Card part 2026-11-10 23:39Z: execute suite 1681/1681 pass; M2 negative 1 / positive 0; paired M2 Sprint 8 v... |
| S8-12 | Fix three weak S8-01 checks - C4 page offsets, C5 row aliasing, C9 memory chain | Done | The knc-char checks C4, C5 and C9 are fixed and rebuilt: C4 now walks every page offset, C5's eight arrays ... |
| S8-13 | Streaming stores for write-only loops beyond L2 (E5-08) | Done | Loops that write arrays too large for the cache now use streaming stores: about 30% faster beyond L2 on the... |
| S8-14 | Default 64-byte data alignment and TLB-aware cache parameters (E5-13) | Done | Card 2026-11-10 (deferred timing, frozen 3516ea25905 vs S8-13): s4_masks o2v/o3 pass, guard controls exit 3... |
| S8-15 | Small-loop unroll default and the GCC-KNC flags page (E5-09) | Done | Card 2026-11-10 timing (M2 L2 vs knc, launch 1/2): at 1 thread/core mat16 0.787/0.788, stencil1 0.906/0.916... |
| S8-16 | User story - one bold flag, -mphinix, with a rising-phoenix banner and a progress bar | Done | Card 2026-11-10: correctness passes. Timing vs -O2 at density 4: mat16 12.89/12.80 (exit 3 in launch 1), sh... |
| S8-17 | Card check C12 - power by rail for a saturated vector unit against x87, idle and streaming | Done | Card check C12 is built and ready to run: it measures card power by rail (core, uncore, memory) while the v... |
| S8-18 | Second GCC tree - a gcc2 lane with its own checkout and build, so two GCC tickets run in parallel | Done | Tools now support a second GCC tree: a lane gcc2 ticket builds in gcc-2/gcc-build-2 while a gcc ticket uses... |
| S8-19 | -mtune=knc stops the tight-loop alignment pass (nops on the fallthrough path) | Done | Card 2026-11-10 11:28-12:03Z (frozen .work/_shared/tmp/claude-s8-19, log .work/_shared/tmp/claude-next.log)... |
| S8-20 | The small-loop unroll costs affine_f64 3-7% at 4 threads per core - make it follow the thread density | Done | Card 2026-11-10 21:00-23:00Z vs knc (S8-15 unroll 4), launch 1/2. Density 4: affine_f64 0.931/0.994, affine... |
| S8-21 | The prefetch pass sees masked loads and stores, so rows shorter than a vector are prefetched | Done | Card 2026-11-11 01:00Z, WRF-shaped column loop (8-float rows), pf over nopf, 7 rounds: density 4 median 0.6... |
| S8-22 | -mphinix is slower than -O2 on M2 kernels (mat16 12.9x, short 1.27x, mat8 1.13x) - find and fix | Done | Card 2026-11-11 01:11Z, -mphinix vs -O2 (launch 1/2): d4 mat16 0.923/0.878, mat8 0.908/0.912, stencil2 0.84... |
| S8-23 | Sprint 8 made the M2 short kernel 5-10% slower than Sprint 7 - bisect and fix | Done | Card 2026-11-11 04:43Z: safety holds (guard sweep 96132 checks, 0 failures; controls exit 3; M2 correctness... |
| S9-01 | libgomp for KNC: futex, affinity, ring-aware barrier, spin-wait and malloc arenas (E6-03 input) | Done | We now have a build-and-design plan for GCC-KNC's own OpenMP runtime on the card: futex-based waits with de... |
| S9-02 | libstdc++ for KNC: exceptions, RTTI, atomics, threads, packaging (E6-06 input) | Done | We now know how to build GCC 16's C++ library for the card: no newer glibc or kernel is needed, and built w... |
| S9-03 | libstdc++ and libatomic build for k1om (E6-06a) | Done | Card 2026-11-10 08:40Z (log .work/_shared/tmp/claude-s8-09.log): hello, rtti, thread, atomic16, tz and all ... |
| S9-04 | libstdc++ packaging into the private prefix and a g++ link guard (E6-06b) | Done | Card 2026-11-10 08:42Z: both xdso pairs print PASS checks=5 with LD_LIBRARY_PATH=/usr/lib64, and the loader... |
| S9-05 | libstdc++ runtime slice on the card (E6-06c) | Done | Card 2026-11-10 11:28Z: s9-05 done exit=0. All 56 programs match expected.txt, including the fixed eh progr... |
| S9-06 | libgomp for k1om: build, select, package and link guard (E6-03 A) | Done | Card 2026-11-10 11:40Z: at 60 and 240 threads every program passes except (1) locks check 4: omp_get_wtick(... |
| S9-07 | libgomp KNC affinity defaults (E6-03 B) | Done | Card 2026-11-10 ~12:15 EST, 30-core mask (cores 0-29, 120 CPUs): the KNC default jobs pass. Two explicit-se... |
| S9-08 | libgomp spin-wait with delay and the one-core measurement (E6-03 C) | Done | Card 2026-11-10 measurements 1 and 3, three launches (log .work/_shared/tmp/claude-resume.log). One core, w... |
| S9-09 | libgomp hierarchical ring-aware barrier (E6-03 D) | Done | Card 2026-11-11 08:21Z on the S9-24 libgomp: suite and tasks/cancel pass (the SIGFPE is gone); measurements... |
| S9-10 | libgomp padding, static schedule default and malloc guidance (E6-03 E) | Done | Card 2026-11-10 14:40Z: the eight OpenMP programs pass on the S9-06..S9-10 libgomp at 60 threads (6 GiB) an... |
| S9-11 | Sprint 9 batch check | Done | Sprint 9's final compiler passes the full execute suite on the card (1681/1681), matches stock GCC on x86, ... |
| S9-12 | libgomp adapts to the card: malloc arena cap from memory, core count and clock (ADR-0012) | Done | Measurement 7 cut down, 240 threads x 100000 1 KiB malloc/free, 2 reps (2026-11-10 22:xxZ): full profile (1... |
| S9-13 | User story - -mknc-card= picks the card model's tuning, and -mknc-card=native detects it | Done | Card 2026-11-10, memory working set, density 4: -mknc-card=7100 vs knc: affine_f32 1.001, stencil1 1.003, m... |
| S9-14 | card_run model profiles - run a job as a 3100, 5100 or 7100 card on our 7120P | Done | card_run --profile 3100/5100/7100/full runs a job as that card would (its compute cores and usable memory),... |
| S9-15 | libgomp's KNC spin time before sleeping, measured against fork-heavy code | Done | Card 2026-11-11, gap-join at 240 threads, DELAY 128: region entry after a 1 ms gap 0.30 ms for all; after 1... |
| S9-16 | Card probes - unaligned scalar accesses, and the VPU cost of subnormal operands | Done | Card 2026-11-11: C13 no faults, no wrong values at any offset or page crossing; worst slowdown vs aligned: ... |
| S9-17 | User guidance on the flags page - threads per core, first touch, regions, heap, and ICC differences | Done | The flags page now has a 'Writing fast code for KNC' section: threads per core, first touch and region size... |
| S9-18 | Experiment - how much do branch hints and profile-guided optimization gain on KNC? | Done | Card 2026-11-11 04:43Z, three launches, single thread, ratio to -O2 (mean of rounds): skewed hint 0.962, wr... |
| S9-19 | Experiment - auto-parallelization on KNC, and whether AutoFDO is possible on the card | Done | Card 2026-11-11: AutoFDO probe: kernel 2.6.38.8+mpss3.7.1, no perf binary, perf_event_paranoid 1, hw cycles... |
| S9-20 | Experiment - how much does instruction scheduling help the in-order core, at 1 and 4 threads per core? | Done | Card 2026-11-11 (no memory limit, S9-23), M2 at 4 threads/core, median ratio to default: nosched 0.995-1.01... |
| S9-21 | S9-18 PGO training script - BusyBox od has no -A/-t, so no profile came back | Done | The S9-18 PGO training script now dumps profiles with od -b -v, which BusyBox 1.19 on the card supports, an... |
| S9-22 | S9-18 PGO rebuild fails with coverage-mismatch on the card profiles - make the two builds identical | Done | The PGO experiment's two builds now use identical compile commands, so profiles collected on the card can b... |
| S9-23 | card_run - no address-space limit in our exclusive turns (owner - "there is no job memory limit") | Done | In our exclusive card turns, jobs now run with no address-space limit unless a profile (3100, 5100) or the ... |
| S9-24 | Sprint 9 settings from the card data, and the harness fixes the batch check needs | Done | KNC libgomp now uses the card-measured defaults: DELAY 128 while spinning, 200 ms of spinning before sleepi... |
| S9-25 | The per-core barrier is slower than the flat one on the card - make flat the default; fix S9-07's runner | Done | KNC libgomp uses the flat barrier by default again (the per-core one was 1.5-2.5x slower on the card and st... |

## Recent activity

- 2026-11-12 21:35 **S11-21** lead answer: Yes. Your precheck used the wrong input: em_real's Registry/Registry must be a copy of Registry/Registry.EM (which itself includes Registry.EM_COMM...
- 2026-11-12 21:33 **S11-21** engineer ask: a7f7e13b: Two failures: Windows Python/Cygwin link (fixed), then my precheck copied Registry.EM_COMMON instead of Registry.EM. Repro: tools/registr...
- 2026-11-12 21:09 **S11-21** owner decide: Owner standing rule (feedback 2026-11-09/10): session budget raised to 14, second extension; progress since the first: WRF v4.8.0 exported, configu...
- 2026-11-12 21:08 **S11-21** engineer escalate: budget: 10 engineer sessions used; the budget is 10
- 2026-11-12 21:07 **S11-21** lead answer: Yes to all four, in place, no new tree from the lead. (1) CRLF is the lead's export fault and it is the whole tree, not only Registry: 5,443 text f...
- 2026-11-12 21:06 **S11-21** engineer ask: 2260da22: Two em_real failures. Config terminator/RPC fixed. Repro: tools/registry -DEM_CORE=1 Registry/Registry; CRLF leaves CR in include names. ...
- 2026-11-12 20:52 **S11-21** lead answer: Yes, as a recorded cross-configure fix, with these limits. configure:1030-1036 is the only probe that executes a target binary; the Fortran 2003/20...
- 2026-11-12 20:50 **S11-21** engineer ask: 9089a9bd: serial/no-nesting configure generated. Two failures: Python keyword (fixed), then RPC probe. Repro: configure:1031 executes tools/rpc_tes...

## Cost

- From the script, engineer: 503 sessions, 1047.2M input tokens
- From the script, lead: 328 sessions, 92.8M input tokens
- Started by hand, Claude: 12 sessions, 2831.9M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 26.0 GiB of 100 GiB. 97 GiB free on the drive.
