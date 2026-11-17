# S14-58: installed-prefix torture and vector compilation sweep

Compiler: `.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe`.
This identifies the installed prefix used, without claiming that its binaries
identify a particular GCC Git commit.

Scope: every recursive `*.c` in `gcc.c-torture/compile`,
`gcc.c-torture/execute`, and `gcc.dg/vect`, at both `-O2` and `-O3`,
with `-march=knc`. The optimization level and architecture follow per-source
options so a source directive cannot replace the requested configuration.
The driver appends unselected `dg-options` and `dg-additional-options` in
source order. Target-selected options, effective-target requirements,
expected diagnostic directives, dump scans, and auxiliary-source directives
are not interpreted. This is a compile/assemble/lint sweep, not a DejaGNU
pass-rate claim. Ordinary compiler diagnostics need target/negative-test
review before being treated as backend defects.

Each successful compilation is assembled with `--march=k1om` and checked
by both source and decoded-object `knc_lint`. Successful `-O3` execute
objects are linked with `-lm` and the installed compiler's runtime, and
the resulting executables are linted. Only successful links with clean
lint enter the single correctness list. No GCC source was changed or built.

The initial attempt stopped while parsing options, before compiling any
test: the old quoted-option expression truncated escaped quotes. The
driver now preserves escaped characters while locating the closing quote.
The suite discovery regression failed before implementation and passed
after implementation; its logs are in `.work/_state/logs/S14_58_red-*`
and `.work/_state/logs/S14_58_suite_paths-*`.

Native execution: **NOT RUN**. Engineers stage binaries; the lead schedules
and runs the card correctness round. No wrong-code verdict can be made
until those results are available. A card timeout is an unresolved result,
not evidence of wrong code.

## Host results

```text
GCC 16 KNC C torture compile corpus (S1-05)
Scope: compile, execute, vect
dg-options and dg-additional-options without target selectors are appended; selected directives are skipped.
Flags: -march=knc -S, plus each level below.
Assembler: binutils 2.22, --march=k1om.
Lint: tools/knc_lint source checks and decoded object checks after successful assembly.
Outcome classes are exclusive: compiler failure, then assembler rejection, then lint failure.
FP ABI class requires every compiler error to be the explicit SSE-disabled ABI diagnostic.
User inline asm rejected requires every assembler error inside #APP/#NO_APP; source lint must be clean.
Timeout policy: 60s, then one 600s compiler retry; both exceeded = hang.
Slow is an additional timing class: retry completed; underlying outcome is counted too.
Whole-run wall time: 3949.887 seconds (65.831 minutes), 8 workers.
Files: 6259; measurements: 12518.

level	pass	slow	hang	ICE	compiler error	float/double ABI error	assembler rejection	lint failure	infrastructure failure	user inline asm rejected	link failure
O2	6025	2	0	0	232	0	0	0	0	2	0
O3	5879	0	0	1	233	0	0	0	0	2	144

```

The source list contains all 6,259 recursive C files; 12,518 configurations were attempted. The driver reports exclusive outcomes, with slow retries counted additionally. A nonzero sweep exit records these failures; it does not mean the sweep stopped early.

The only ICE reproduces S12-38: GIMPLE pass `vect`, with the first vectorizer
frame in `vect_analyze_slp_reduc_chain` (`tree-vect-slp.cc:4275`). No RTL
instruction is reported because the failure precedes RTL generation.
S12-34 was not observed in this sweep. No new backend defect is established.
All 144 link failures are builtins harness inputs compiled independently;
they leave the execute staging acceptance incomplete. The four assembler
rejections are two input-inline-assembly tests at both levels.

Full per-case classification: `.work/_shared/S14-58/summary.txt`.
Host run log: `.work/_state/logs/S14_58_sweep-20261117-093421.log`.

## Per-test failures

Each row is a failed configuration, including ordinary diagnostic and link failures. Pass and instruction are unknown unless present in the diagnostic. No wrong-code verdict exists before card execution. S12-34 duplication requires an underaligned narrowing-store reproducer; an unrecognizable-insn message alone does not establish it.

| Test | Level | Classification | Diagnostic | Pass | Instruction | Duplicate/new |
|---|---|---|---|---|---|---|
| gcc.c-torture/compile/20030305-1.c | O2 | compiler error | error: initialization of flexible array member in a nested context | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/20111209-1.c | O2 | compiler error | error: invalid pointer mode 'SI' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/dll.c | O2 | compiler error | error: return type defaults to 'int' [-Wimplicit-int] | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-1.c | O2 | compiler error | error: invalid register name for 'cp0count' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-2.c | O2 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-3.c | O2 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-4.c | O2 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr100305.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr10153-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr10153-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr106433.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr108237.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr110386-2.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr28865.c | O2 | compiler error | error: initialization of flexible array member in a nested context | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr29201.c | O2 | compiler error | error: return type defaults to 'int' [-Wimplicit-int] | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr33614.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr34856.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr39928-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr48767.c | O2 | compiler error | error: second argument to 'va_arg' is of incomplete type 'void' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr83547.c | O2 | compiler error | error: void value not ignored as it ought to be | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr86637-2.c | O2 | compiler error |  | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr88347.c | O2 | compiler error | cc1: error: bad value '603e' for '-mtune=' switch | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr89235.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr92618.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr97576.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr99647.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-3.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-5.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-6.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-dup-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-3.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/builtins/lib/bfill.c | O2 | compiler error | error: implicit declaration of function 'abort' [-Wimplicit-function-declaration] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/builtins/lib/bzero.c | O2 | compiler error | error: implicit declaration of function 'abort' [-Wimplicit-function-declaration] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-1.c | O2 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-2.c | O2 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-3.c | O2 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4.c | O2 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4f.c | O2 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4l.c | O2 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr109938.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr109986.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr123753.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr80692.c | O2 | compiler error | error: decimal floating-point not supported for this target | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr92618.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr94524-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr94524-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/simd-6.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-70.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-layout-17.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-layout-18.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr101615-1.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr101756.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr54400.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839-v8.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-add-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-add-pattern-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mla-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mls-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mul-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-add-pattern-template.c | O2 | compiler error | error: unknown type name 'TYPE' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-add-template.c | O2 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mla-template.c | O2 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mls-template.c | O2 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mul-template.c | O2 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-add-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-add-pattern-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mla-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mls-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mul-half-float.c | O2 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-slp-perm.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mdejagnu-cpu=power9' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-vect-reversed.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mvsx' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-vect-store-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mvsx' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-mixed-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-6.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-7.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-6.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-7.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-10.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-11.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-12.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-6.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-7.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-8.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-9.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-10.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-11.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-12.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-13.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-14.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-6.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-7.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-8.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-9.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/no-dynamic-lmul-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111153-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111317.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr11153-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111848.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr112387-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr112387-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114264.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114506.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114516.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-10.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-11.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-12.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-3.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-4.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-5.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-6.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-7.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-8.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-9.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vse-slp-1.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vse-slp-2.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-1.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-2.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-3.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-4.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123190-1.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123190-2.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123225.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-vect-epil-1.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/gimplefe-40.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/gimplefe-41.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr101505.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr108950.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr111754.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr115753-1.c | O2 | compiler error | error: invalid conversion to type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr115753-2.c | O2 | compiler error | error: invalid conversion to type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr48765.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mdejagnu-cpu=power6' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr59984.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr62021.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr63530.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '--param="max-completely-peeled-insns=400"'; did you mean '--param=max-completely-peeled-insns='? | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr64421.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr68339.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr84711.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-2.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-3.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-4.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-5.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-6.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-7.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr92554.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr93069.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr95539.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/slp-simd-clone-1.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/slp-simd-clone-2.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-82_64.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mpowerpc64' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-83_64.c | O2 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mpowerpc64' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-bic-bitmask-23.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-div-bitmask-4.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-nop-move.c | O2 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-pr124802.c | O2 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-1.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-11.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-13.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-14.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-15.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16b.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16c.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16d.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16e.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16f.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17b.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17c.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17d.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17e.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17f.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18b.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18c.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18d.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18e.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18f.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-2.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-20.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-21.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-3.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-4.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-5.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-6.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-7.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-8.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-9.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-pr121130.c | O2 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/920520-1.c | O2 | user inline asm rejected | Error: junk at end of line, first unrecognized character is '%' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/920521-1.c | O2 | user inline asm rejected | Error: no such instruction: 'f' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-pr123221.c | O3 | ICE | internal compiler error: Segmentation fault | vect | unknown | S12-38 |
| gcc.c-torture/compile/20030305-1.c | O3 | compiler error | error: initialization of flexible array member in a nested context | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/20111209-1.c | O3 | compiler error | error: invalid pointer mode 'SI' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/dll.c | O3 | compiler error | error: return type defaults to 'int' [-Wimplicit-int] | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-1.c | O3 | compiler error | error: invalid register name for 'cp0count' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-2.c | O3 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-3.c | O3 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/mipscop-4.c | O3 | compiler error | error: invalid register name for 'c3r1' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr100305.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr10153-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr10153-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr106433.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr108237.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr110386-2.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr28865.c | O3 | compiler error | error: initialization of flexible array member in a nested context | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr29201.c | O3 | compiler error | error: return type defaults to 'int' [-Wimplicit-int] | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr33614.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr34856.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr39928-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr48767.c | O3 | compiler error | error: second argument to 'va_arg' is of incomplete type 'void' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr83547.c | O3 | compiler error | error: void value not ignored as it ought to be | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr86637-2.c | O3 | compiler error |  | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr88347.c | O3 | compiler error | cc1: error: bad value '603e' for '-mtune=' switch | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr89235.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr92618.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr97576.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/pr99647.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-3.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-5.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-6.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/vector-dup-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/20050316-3.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/builtins/lib/bfill.c | O3 | compiler error | error: implicit declaration of function 'abort' [-Wimplicit-function-declaration] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/builtins/lib/bzero.c | O3 | compiler error | error: implicit declaration of function 'abort' [-Wimplicit-function-declaration] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-1.c | O3 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-2.c | O3 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-3.c | O3 | compiler error | error: passing argument 2 of 'signal' from incompatible pointer type [-Wincompatible-pointer-types] | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4.c | O3 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4f.c | O3 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/ieee/fp-cmp-4l.c | O3 | compiler error | error: expected ';', ',' or ')' before 'true' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr109938.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr109986.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr123753.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr80692.c | O3 | compiler error | error: decimal floating-point not supported for this target | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr92618.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr94524-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/pr94524-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/simd-6.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-70.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-layout-17.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-layout-18.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr101615-1.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr101756.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr54400.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839-v8.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/bb-slp-pr95839.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-add-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-add-pattern-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mla-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mls-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/bb-slp-complex-mul-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-add-pattern-template.c | O3 | compiler error | error: unknown type name 'TYPE' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-add-template.c | O3 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mla-template.c | O3 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mls-template.c | O3 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/complex-mul-template.c | O3 | compiler error | error: expected ';', ',' or ')' before 'a' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-add-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-add-pattern-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mla-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mls-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/complex/fast-math-complex-mul-half-float.c | O3 | compiler error | error: operation not permitted on type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-slp-perm.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mdejagnu-cpu=power9' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-vect-reversed.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mvsx' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/ppc/costmodel-vect-store-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mvsx' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-ice-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul-mixed-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-6.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul1-7.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-6.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul2-7.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-10.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-11.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-12.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-6.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-7.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-8.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul4-9.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-10.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-11.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-12.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-13.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-14.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=ilp32' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-6.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-7.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-8.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/dynamic-lmul8-9.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/no-dynamic-lmul-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111153-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111317.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr11153-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr111848.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr112387-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr112387-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113112-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113247-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr113281-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114264.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114506.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/pr114516.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-10.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-11.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-12.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-3.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-4.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-5.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-6.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-7.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-8.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vla_vs_vls-9.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vse-slp-1.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/riscv/rvv/vse-slp-2.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized argument in option '-mabi=lp64d' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-1.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-2.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-3.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr104582-4.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123190-1.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123190-2.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-pr123225.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/costmodel/x86_64/costmodel-vect-epil-1.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/gimplefe-40.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/gimplefe-41.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr101505.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr108950.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr111754.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr115753-1.c | O3 | compiler error | error: invalid conversion to type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr115753-2.c | O3 | compiler error | error: invalid conversion to type '_Float16' without option '-msse2' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr48765.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mdejagnu-cpu=power6' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr59984.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr60505.c | O3 | compiler error | error: writing 1 byte into a region of size 0 [-Werror=stringop-overflow=] | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr62021.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr63530.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '--param="max-completely-peeled-insns=400"'; did you mean '--param=max-completely-peeled-insns='? | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr64421.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr68339.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr84711.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-2.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-3.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-4.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-5.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-6.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr88497-7.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr92554.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr93069.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/pr95539.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/slp-simd-clone-1.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/slp-simd-clone-2.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-82_64.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mpowerpc64' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-83_64.c | O3 | compiler error | k1om-mpss-linux-gcc: error: unrecognized command-line option '-mpowerpc64' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-bic-bitmask-23.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-div-bitmask-4.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-nop-move.c | O3 | compiler error | error: unsupported KNC register ABI mode | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-pr124802.c | O3 | compiler error | cc1: error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-1.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-11.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-13.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-14.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-15.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16b.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16c.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16d.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16e.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-16f.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17b.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17c.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17d.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17e.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-17f.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18b.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18c.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18d.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18e.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-18f.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-2.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-20.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-21.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-3.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-4.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-5.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-6.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-7.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-8.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-clone-9.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.dg/vect/vect-simd-pr121130.c | O3 | compiler error | error: SSE, AVX and MMX options are not supported with '-march=knc' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/920520-1.c | O3 | user inline asm rejected | Error: junk at end of line, first unrecognized character is '%' | unknown | unknown | new/unresolved |
| gcc.c-torture/compile/920521-1.c | O3 | user inline asm rejected | Error: no such instruction: 'f' | unknown | unknown | new/unresolved |
| gcc.c-torture/execute/builtins/20010124-1-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/20010124-1.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-1-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-1.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-3-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/abs-3.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/complex-1-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/complex-1.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/fprintf-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/fprintf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/fputs-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/fputs.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/abs.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/fprintf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/main.c | O3 | link failure | main.c:(.text.startup+0xf): undefined reference to 'main_test' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/memchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/memcmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/memmove.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/mempcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/memset.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/printf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/sprintf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/stpcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strcat.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strcmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strcspn.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strlen.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strncat.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strncmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strncpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strnlen.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strpbrk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strrchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strspn.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/lib/strstr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memchr-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memcmp-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memcmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memcpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memcpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memmove.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memops-asm-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memops-asm.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/mempcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memset-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memset-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memset-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/memset.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr22237-1-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr22237-1.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr22237-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr22237.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr23484-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr23484-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr93262-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/pr93262-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/printf-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/printf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/snprintf-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/snprintf-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/sprintf-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/sprintf-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/sprintf-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/sprintf.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/stpcpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/stpcpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/stpncpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/stpncpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcat-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcat-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcat-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcat.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strchr-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcmp-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcspn-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strcspn.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen-3-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen-3.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strlen.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncat-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncat-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncat-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncat.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncmp-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncmp-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncmp-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncmp.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncpy-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncpy-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncpy-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strncpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strnlen-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strnlen.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpbrk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpbrk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpcpy-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpcpy-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpcpy-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strpcpy.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strrchr-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strrchr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strspn-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strspn.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strstr-asm-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strstr-asm.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strstr-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/strstr.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-1-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-1.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-2-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-2.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-3-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/uabs-3.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/vsnprintf-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/vsnprintf-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/vsprintf-chk-lib.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |
| gcc.c-torture/execute/builtins/vsprintf-chk.c | O3 | link failure | /sandbox/build/tmp/tmp/work/k1om-mpss-linux/glibc-2.14.1+mpss3.8.6-1/glibc-2.14.1+mpss3.8.6/csu/../sysdeps/x86_64/start.S:114: undefined reference to 'main' | unknown | unknown | staging harness: builtins.exp pairing required |

## Reduced commands and ticket drafts

Run on the host with the project cross and Cygwin bins on PATH. `CC` denotes the installed compiler above; `TS` is `.work/_shared/gcc/gcc/testsuite`. Each compile command below omits only the output location from the captured invocation; assembly and lint use the retained file alongside the per-case log under `.work/_shared/S14-58/LEVEL/TEST.log`.

### gcc.c-torture/compile/920520-1.c (O2, user inline asm rejected)

```sh
$CC -std=gnu89 -march=knc -O2 -S $TS/gcc.c-torture/compile/920520-1.c -o repro.s
```

Assembly reproduction: `k1om-mpss-linux-as --march=k1om repro.s -o repro.o`; lint reproduction: `python tools/knc_lint repro.s` and `python tools/knc_lint repro.o`.

Input inline assembly rejected; not established as a compiler defect. Review target requirements before opening a backend ticket.

### gcc.c-torture/compile/920521-1.c (O2, user inline asm rejected)

```sh
$CC -std=gnu89 -march=knc -O2 -S $TS/gcc.c-torture/compile/920521-1.c -o repro.s
```

Assembly reproduction: `k1om-mpss-linux-as --march=k1om repro.s -o repro.o`; lint reproduction: `python tools/knc_lint repro.s` and `python tools/knc_lint repro.o`.

Input inline assembly rejected; not established as a compiler defect. Review target requirements before opening a backend ticket.

### gcc.dg/vect/vect-pr123221.c (O3, ICE)

```sh
$CC -fno-tree-pre -march=knc -O3 -S $TS/gcc.dg/vect/vect-pr123221.c -o repro.s
```

Existing ticket S12-38; no new draft.

### gcc.c-torture/compile/920520-1.c (O3, user inline asm rejected)

```sh
$CC -std=gnu89 -march=knc -O3 -S $TS/gcc.c-torture/compile/920520-1.c -o repro.s
```

Assembly reproduction: `k1om-mpss-linux-as --march=k1om repro.s -o repro.o`; lint reproduction: `python tools/knc_lint repro.s` and `python tools/knc_lint repro.o`.

Input inline assembly rejected; not established as a compiler defect. Review target requirements before opening a backend ticket.

### gcc.c-torture/compile/920521-1.c (O3, user inline asm rejected)

```sh
$CC -std=gnu89 -march=knc -O3 -S $TS/gcc.c-torture/compile/920521-1.c -o repro.s
```

Assembly reproduction: `k1om-mpss-linux-as --march=k1om repro.s -o repro.o`; lint reproduction: `python tools/knc_lint repro.s` and `python tools/knc_lint repro.o`.

Input inline assembly rejected; not established as a compiler defect. Review target requirements before opening a backend ticket.

### Builtins staging harness gap

The `gcc.c-torture/execute/builtins/builtins.exp` harness treats a test, its `-lib.c` companion, and `lib/main.c` as one executable. It also supplies `-fno-tree-dse -fno-tree-loop-distribute-patterns -fno-tracer -fno-ipa-ra -fno-inline-functions`. The raw recursive sweep compiled these files individually; their missing-main/companion link failures are harness failures, not new GCC defects. The paired tests are not in the current correctness list.

Reduced example:

```sh
$CC -march=knc -O3 -S $TS/gcc.c-torture/execute/builtins/abs-1.c -o abs.s
k1om-mpss-linux-as --march=k1om abs.s -o abs.o
$CC -march=knc -O3 abs.o -lm -o abs.mic
```

The link reports missing `main`; compiling the companion alone also leaves `inside_main` unresolved. No additional execution or recompilation was attempted.

Draft for lead: **Complete S14-58 builtins staging using the testsuite harness model**. Preserve the raw host sweep results, then stage each builtins test with its companion and common main using the harness flags, lint each binary, and append each successful paired test once to the same correctness list. Do not list helper files as independent executables. Confirm whether these harness flags should also define an additional compile configuration, or apply only to the native staging pass.

## Partial card staging (not executed)

1744 lint-clean execute binaries plus the lint-clean driver are staged under `.work/_shared/S14-58/card/` (27,371,518 payload bytes). `claude-torture.list` is the single correctness run list; `card-files.list` supplies its inputs. The driver inherits the job affinity, starts at most 60 independent serial processes, and records ordered PASS/FAIL/TIMEOUT plus `claude-torture.details`. A timeout is not a wrong-code verdict.

This is the standalone subset, not the complete execute suite; resolve the builtins gap before claiming complete staging. Lead only, from the main checkout, in an owner-approved window:

```sh
python tools/card_run --threads 240 --timeout 7200 --file-list .work/_shared/S14-58/card/card-files.list .work/_shared/S14-58/card/claude-torture.mic -j 60 --limit-mb 128 claude-torture.list
```

Native results: **NOT RUN**. Triage every native FAIL/TIMEOUT using the retained test name and details before treating this as a zero-wrong-code result. x86 not run.
