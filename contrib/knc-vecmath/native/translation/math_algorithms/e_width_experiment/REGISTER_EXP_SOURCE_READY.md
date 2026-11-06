# DP8 exp register-table source readiness

The additive source is ready for the root-owned first Linux-target emission.
It has not been compiled or executed. Source status does not establish zero
gathers in actual assembly, numerical accuracy, ABI qualification or G5.
The declared varying factor, expected signature, metrics, falsifier, bound
and stop rule were written in [REGISTER_EXP_PLAN.md](REGISTER_EXP_PLAN.md)
before generating/checking the source.

- `e_exp_register.c` preserves the historical exp arithmetic and all special
  paths, changing only the lookup and private entry-point spelling to
  `phi_host_exp_register_e8`. Its SHA256 is
  `b164220a8c065599c488fa5a8f9403adedbc8920059f25200499cb4f30940944`.
- `e_exp_register_table.h` contains 32 fixed aligned64B objects: sixteen
  eight-entry tail shards and sixteen scale shards. Paired32-bit selectors
  reconstruct both uint64 halves with no FP conversion. Its SHA256 is
  `183328d1ab54b47eeaf0ead8f988ce18739fb4f3424d652543ba9c33ea01dc16`.
- `../../libknc_mvec/src/e_exp_register_export.c` supplies the alternative
  `_ZGVeN8v_exp(knc_mvec_f64x8)` definition returning `knc_mvec_f64x8` through
  the unchanged export adapter. Its SHA256 is
  `4c86084332b5a4ce6140331792d2fa27382d6feea67c2a59ca2e1ea90c13a02e`.
  The old and new exp adapters are alternative translation units.

The pointer API is
`int phi_host_exp_register_e8(const uint64_t input[8], unsigned active,
const uint64_t merge[8], uint64_t output[8])`. It retains the historical low8
software-mask restriction, neutral input zero, full readable64B buffers and
exact input/output or merge/output alias contract. The optional research
negative symbol is `phi_host_exp_register_e8_unsafe_negative` under
`PW_ENABLE_NEGATIVE_CONTROL`; the export adapter rejects that macro.

One source-only check completed at
`artifacts/test-state/exp-register-source/3bea39fa743d46f089e10482b3c7d403/result.json`,
SHA256 `d7c0843f5ff9bfd37f67634121cfc514e7ed50f5c1f875e9837669906c02cf91`.
The result and consumed source snapshots are retained. It authenticated the
unchanged historical exp source and official Arm data/configuration/license,
checked all256 original uint64 table words and every index in every one of8
mixed lanes with unrelated high bits: 128 vectors, 1,024 lanes, 2,048 uint64
comparisons (4,096 dword halves), zero mismatches. Completed wrong-half and
wrong-shard models produced 2,040 and 2,048 mismatches. Source corruptions in
arithmetic, one static table bit and one group binding were all rejected.
No compiler, FP kernel, old numerical corpus or card was run. The retained
historical <=0.506 ULP sample has not been relabeled as a new-source result.

The preparation/check entry point is
`scripts/Prepare-KncExpRegisterSource.py`; its default mode checks existing
sources into a fresh owned artifact directory. `--write-new-sources` creates
only absent files and refuses overwrite. It is a source/data check, not a
compiler, target instruction oracle or numerical assessor.

The direct source include closure is the new export, unchanged
`e_export_adapter.h`/`include/knc_mvec_abi.h`, new core/table, unchanged
`e_algorithms.h`, pinned `arm-optimized-routines-v26.01-dp/math/math_config.h`
and standard `stdint.h`, `string.h`, `math.h` dependencies. The unchanged
official `exp_data.c` still supplies range-reduction constants and polynomial
coefficients at link. Use the existing explicit Linux-header D3 compiler
flags/include directories unchanged, with `HAVE_FAST_FMA=0` and the selected
strict contraction policy. Only the actual first `-M`/`-S` can freeze the
complete system-header/tool closure and instruction census.

Current registered domains expose these concrete source-induced gaps:
`vpsllq`512 immediate32, `vpslld`512 immediate1, `vpsrld`512 immediate3,
dword equality predicate0 and full-width VPERMD with the32 new readonly
objects. Existing base shift/mask rules do not cover those combinations.
The expf exact56 rule is explicitly parent-source-bound, including its own
qword shift32 witness; its recipe cannot be transferred to this source.
The compiler may choose different shifts, mask materialization, VPORD/VPORQ
or VPTERNLOGD, and may spill under table/register pressure. This is a list of
unmet source operations, not a fabricated emitted instruction inventory.
Freeze and qualify the actual literals/registers/addresses after emission.

The DP8 export argument/return, nested pointer calls, emitted DP/FMA
special-value and exception behavior, stack alignment, D1/D2/D3 mask/scratch
effects, actual source/static-data binding and new independent <=1 ULP
numerical assessment remain prerequisites. The root owns compilation and
target release; the host-assessment owner has the new pointer API and source
identities. No production source selection or gate count changes here.
