# Real compiler output fixtures

- `x87test.c` / `x87test.s`: three small functions compiled by GCC-KNC 16.2.0 (`-O2 -march=knc`, frozen gcc_knc prefix,
  2026-11-15): `f` is x87 double arithmetic (fsub/fdivl/fxch/fmulp/faddp/fsubrl), `g` an x87 float dot product with the
  compiler's unrolled loop, software prefetches and a `vbroadcastss` return, `h` a scalar integer loop. `*_init.json`
  give the inputs and hand-computed expected outputs; `x87test_{f,g,h}.json` are the kernels the adapter produced from them
  (`scripts/from_gcc_s.py x87test.s --function f --init f_init.json --out x87test_f.json`).
- `s12-30-compiler-knc.s`: the gcc_knc S12-30 gate kernels (HPCG CSR SpMV / SymGS shapes) as GCC-KNC emitted them; the
  inner loop `knc_csr_raw:.L6` is the audit's reference hot region (x87 double, movslq index loads, vprefetch0/1).

Nothing in these files was simplified to pass; unsupported forms stay unsupported and are listed by the adapter.
