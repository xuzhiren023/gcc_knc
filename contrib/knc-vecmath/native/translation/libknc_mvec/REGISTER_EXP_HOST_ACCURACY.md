# Fresh register-table DP8 exp host accuracy

The changed `e_exp_register.c` passed one new host compile/execution and
independent assessment. Result:
`artifacts/test-state/host-exp-register/ed9703b950f14fe9b4218f756295a4df/result.json`,
SHA256 `02d4be46a16728b3ef3c58b57bb3ca8124673e5748875b0b1b4be0721d4afc80`.
The experiment declaration precedes compilation in sibling `experiment-plan.json`.

It reuses only cached independent DP8 packets/references from b595df3d:
177312 vectors,1397157 active lanes and21339 inactive lanes. All256 masks
and separate output/input alias/merge alias cases were included. Value,
exception-vector, profile, inactive-merge and empty-mask FP mismatches are
all zero. Finite rounded-reference distance counts are1116192 exact and59
one-step. Those59 changed words received fresh independent interval checks;
the maximum conservative error is0.505430639581543ULP, below1. Specials and
zero-input identities are exact; inactive lanes preserve merge bits.

This is **host accuracy only**: Cygwin SSE2, AVX/AVX2/AVX512/FMA disabled and
contraction off, avoiding the known Cygwin aligned AVX-spill failure. Linux
KNL BIND flags are unchanged. Neither the old algorithm nor its outputs were
executed/read. Both owned jobs ended with zero active processes; source drift
is empty. Two new bounded assessor controls passed without a kernel run.

New target exp emission, exact instruction qualification, ABI/runtime image
binding and card accuracy remain necessary. Phase3 is39 registered /38
verified=True. Target G5 remains **1/36**, solely expf under
`artifacts/native/knc-g5-expf.json` SHA256
`121f955c2f2c2f2a06b512d2992dddf284dd09cb20120b7b1720c02ad9b418e9`.
No full G3/G5/G6/G10 pass or performance gain is implied.
