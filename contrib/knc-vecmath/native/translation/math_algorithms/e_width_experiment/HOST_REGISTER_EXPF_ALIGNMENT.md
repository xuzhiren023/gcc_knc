# Cygwin register-table expf host spill repair

The new gather-free source's first host accuracy attempt `10e04fef` died before
returning from its first kernel call. Diagnosis used its retained executable
and only one16-lane input, not the unchanged1,227,024-lane corpus.

Cygwin strace at
`artifacts/test-state/host-expf-crash-diagnosis/e181dc651f9c4f828a0273879ad7b668/strace.log`
records exception `C0000005` at RIP `0x10040153f`, RSP `0x7ffffc370`.
Actual retained disassembly is `vmovdqa 0x80(%rsp),%ymm5`: effective address
`0x7ffffc3f0` is16 modulo32 and violates that instruction's32-byte alignment.
The Win64 core prolog preserves16-byte alignment and does not realign to32.
Its separate table workspace is64-aligned; the fault is the compiler's aligned
temporary shuffle spill, not an indexed-table bounds failure.
Sibling `fault.json` binds the original executable, fault and tiny input scope.

Bounded host-only alternatives remain retained:

| Attempt | Actual outcome |
| --- | --- |
| `63d465a7` with `-mstackrealign` | Same prolog and tiny SIGSEGV. |
| `6f6848bc` with preferred boundary5 | Compiler rejects boundary5; Cygwin permits only3..4. No executable. |
| `28e23cd3` with AVX2 disabled | Tiny passes, but actual disassembly still has32-byte aligned YMM loads from RSP. This is not a robust repair. |
| `9ac65cac` with AVX/AVX2/FMA disabled and contraction off | Tiny passes; actual whole executable disassembly has zero YMM/ZMM instructions, all16 values match Python rounded references; raw host MXCSR `0x1fb8`. |

These attempts are under `artifacts/test-state/host-expf-stack-realign/`.
Each preserves the exact original C/header/driver sources, actual compiler
argv and owned terminal outcome. No candidate numerical source changed.

`Check-HostRegisterExpf.py` now explicitly labels this host source diagnostic
and adds `-mno-avx -mno-avx2 -mno-fma -ffp-contract=off`. These options affect
only the Cygwin accuracy diagnostic. KNL generator flags, production BIND,
the target shuffle recipe, target ABI and target qualification stay separate.
Noncontracted host results require their own fresh corpus assessment and do
not prove the target's FMA results. Root owns that next numerical execution.
The tiny check is not a host accuracy pass, G5 export or KNC execution proof.
