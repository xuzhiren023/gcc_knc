# S6-02 M2 kernels: red-review fixture

This first commit establishes the correctness rejection path before implementing
the real references, kernel matrix and timing driver. It is not an M2 result.
Only new files in this directory are authorized by the ticket's lead answer.

Run from the worktree root:

```text
python tools/run.py --name S6-02-negative-build --inputs tests/acceptance/m2_kernels -- python tests/acceptance/m2_kernels/build.py negative
python tools/run.py --name S6-02-checker-red --inputs tests/acceptance/m2_kernels -- python tests/acceptance/m2_kernels/build.py host-negative
```

The first command compiles the checker with shared GCC 16, assembles both objects
with donor binutils `--march=k1om`, links and lints the executable. It leaves
`.work/_shared/S6-02/m2-negative.mic` for the lead's correctness card job.
The checker uses `-DNEGATIVE_CONTROL` to select the deliberately wrong hand-written
IMCI copy kernel. It omits the affine multiply and add. Expected native outcome:
75 failing nonempty lengths, exit 1; length zero succeeds without touching output.
The first mismatch is `length=1 index=0 got=c17c0000 want=c1f80000`.
The final line is `correctness affine_f32 imci: 75 failing lengths`.

The second command checks the same rejection logic on the host with an explicitly
labelled C copy stand-in. It first checks a correct scalar result at length 17,
then exits 1 on the wrong results. It does not execute or emulate IMCI, and is not
native card evidence. Infrastructure failures exit separately from mismatches.

Inputs and output bases are 64-byte aligned. Every output is compared bitwise
with the scalar reference, with guards on both sides. Inputs are signed quarter
integers, `a=2`, `b=0.5`: every intermediate and result is exactly representable
in FP32, so no tolerance or rounding-mode/excess-precision exception is needed.
Contraction and vectorization are disabled in the checker. Cases cover 0..64,
the ADR-0010 boundary lengths, and its 1/2/4-density working-set rows.

After red review, the normal build will call `m2_affine_f32_imci`; that symbol is
intentionally not supplied in this test-first commit. FP64, stencils, matrix-vector
products, the real references and timing remain to be implemented. Timing must
follow `docs/adr/0010-knc-measurement-protocol.md`, use RAW wall makespans for M2,
retain all samples, and treat same-worker TSC ticks as diagnostics only.
No native result or performance claim is made by these host build commands.
