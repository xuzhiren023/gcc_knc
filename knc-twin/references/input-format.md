# Input format

Schema: `schemas/kernel.schema.json` (`knc-twin.kernel/1`). Examples: `fixtures/*.json`,
`fixtures/gcc/` (real GCC-KNC output with inputs and expected results).

## From compiler output: `scripts/from_gcc_s.py`

```
from_gcc_s.py FILE.s --function NAME [--init INIT.json] --out KERNEL.json [--profile ID]
from_gcc_s.py FILE.s --loop NAME:LABEL [--trip-count N] [--init INIT.json] --out KERNEL.json
from_gcc_s.py FILE.s [FILE2.s ...] --audit [--profile ID] [--weights W.json] --out REPORT.json
```

- A **function** region is the whole function; every `ret` becomes a jump to a synthetic end
  label so the stream terminates. A **loop** region is the label and its last backward branch;
  branches that leave the loop are redirected to the synthetic end label. `call` stays in the
  records and makes the kernel fail to load with "region boundary": cut the region or treat the
  callee separately. Nothing is dropped: every instruction the twin cannot read is listed with
  its source line and reason in `KERNEL.coverage.json` and in the audit.
- `.rept/.endr` are expanded; data symbols referenced `symbol(%rip)` are copied from the file's
  data directives (`.long .quad .byte .short .zero .string .float .double`) into a synthetic data
  area (`init.symbols`, `init.memory`), 64-byte aligned per symbol. Unknown symbols (externs,
  TLS `@gottpoff`) are reported as unresolved. Record ids are `L<source line>` (`_2`, `_3` for
  repeated expansions).
- Live-in registers (read before written) are listed and given placeholder zeros; `--init`
  merges a JSON with `init`, `expected`, `unit_of_work`, `numerical_policy`, `scenario`, `loop`,
  `memory_default` from an independent reference (host run, hand calculation).
- `--audit` reports per function and per innermost loop: instructions, parser/isa/functional/
  timing coverage with the chosen profile, blockers, and "complete" flags. `--weights` maps
  function (or `file.s:function`) to native seconds so the report can say how much measured
  test time a complete region covers.

The adapter does not simplify: masks, swizzles, conversions, x87 stack operations, spills and
reloads, scatter completion and flag effects are kept as emitted.

## Kernel

```json
{
  "schema": "knc-twin.kernel/1",
  "name": "saxpy_loop",
  "unit_of_work": {"description": "16 floats of y = a*x + y", "count": 4},
  "numerical_policy": {"rounding": "rn", "ftz": false, "daz": false, "nan_compare": "any_nan", "x87_control_word": "0x037f"},
  "init": {"memory": [{"addr": "0x100000", "f32": [1, 2, 3]}], "registers": {"zmm2": {"f32_broadcast": 2.0}}, "symbols": {".LC0": "0x10000000"}},
  "streams": [{"context": 0, "init": {"registers": {"rax": "0x100000"}}, "instructions": [ ...records... ]}],
  "loop": {"label": "L", "trip_count": 4},
  "scenario": {"memory": {"type": "fixed_level", "level": "l1"}, "branch": {"type": "all_predicted"}},
  "expected": {"memory": [{"addr": "0x200000", "f32": [3, 5, 7]}], "registers": {"0": {"rcx": 64, "st0": 1.5, "x87_depth": 1}}},
  "provenance": {"shape": "l1_resident_vector_chain"}
}
```

- `unit_of_work.count`: units completed by one run of all streams. Predictions are also given
  per unit. With `--contexts` selecting a subset, the count is scaled proportionally.
- `init.registers` applies to every stream; a stream's `init.registers` overrides. x87 initial
  values: `"x87": [values pushed in order]`, `"fcw": "0x037f"`.
- Values: integers may be decimal or `"0x..."` strings. `f32`/`f64`/`f16` lists accept numbers that
  are exactly representable (anything else is rejected: give the bit pattern `"0x3f800001"`),
  `"nan"`, `"inf"`, `"-inf"`, `"-0.0"`. zmm registers: `{"f32": [16 values]}`, `{"u32": [...]}`,
  `{"f64": [8]}`, `{"u64": [8]}`, `{"f32_broadcast": x}`, `{"u32_broadcast": x}`, `{"f64_broadcast": x}`,
  `{"u64_broadcast": x}`. Mask registers: 16-bit integers. `flags`: `{"ZF": 1, ...}`.
- `memory_default`: byte value for reads of uninitialized memory; without it such a read is
  `invalid_input`.
- `expected`: registers per context (keyed by context index as a string) and memory blocks.
  NaNs match any NaN unless `nan_compare` is `"bits"`. x87: `st0`..`st7` as f64 values (the
  extended value rounded to double) or `{"f80": "0x..."}`, and `x87_depth`.
- `provenance.shape`: optional declared kernel shape for result classification
  (`validation.md` lists the validated shapes).

## Records (Intel operand order, destination first)

```json
{"id": "fma", "op": "vfmadd231ps", "ops": ["zmm1", {"reg": "zmm2", "swizzle": "cdab"}, {"base": "rax", "index": "rcx", "scale": 4, "disp": 64, "conv": "float16"}],
 "mask": "k1", "rounding": "rn", "label": "L", "encoding": {"disp32": false}, "deps": ["ld"], "comment": "..."}
```

- `op`: a mnemonic from `capabilities` (`knc_twin.py capabilities`). Anything else is rejected.
- `ops`: registers (`rax`, `eax`, `ax`, `al`, `ah`, `zmm0`..`zmm31`, `k0`..`k7`, `st`, `st(1)`),
  immediates (int or string), labels (branch targets), memory operands
  `{"base","index","scale","disp","broadcast","conv","vindex","symbol"}`. Register operands with
  modifiers are objects: `{"reg": "zmm1", "swizzle": "cdab"}` (cdab badc dacb aaaa bbbb cccc dddd)
  or `{"reg": "zmm0", "conv": "float16"}` (down-conversion on a store source). Memory `broadcast`
  is `1to16`, `4to16`, `1to8` or `4to8`; memory `conv` is `float16`, `uint8`, `sint8`, `uint16` or
  `sint16` (up-conversion). Gathers and scatters use `vindex`.
- Operand roles per mnemonic are in `scripts/knc_model/isa.py`. FMA forms: 132 = op1*op3+op2,
  213 = op2*op1+op3, 231 = op2*op3+op1. Conversions take a rounding immediate (bits 1:0:
  rn, rd, ru, rz; exponent-adjust bits must be zero). Compare predicates: FP 0 eq, 1 lt, 2 le,
  3 unord, 4 neq, 5 nlt, 6 nle, 7 ord (or the named forms `vcmpltps`...); integer 0 eq, 1 lt,
  2 le, 4 ne, 5 nlt, 6 nle.
- `mask`: write mask with merge semantics; on gathers/scatters it is the completion mask (cleared).
- `width`: 8, 16, 32 or 64 for scalar memory forms with no register to imply it.
- `encoding`: optional hints (`bytes`, `disp32`, `disp`, `imm`) for the pairing rules.
- `deps`: extra explicit dependencies on earlier ids.
- `addr {start, stride}` and `lines`: address descriptions for static traces (below).
- Rejected: `call`/`ret` (region boundaries), one-operand `imul`, `cmov*` (not on KNC),
  swizzles other than the seven above, symbolic immediates, TLS operands.

## GAS AT&T subset

A stream may give `"asm_file": "kernel.s"` (relative to the kernel file) or `"asm": "..."`
instead of `instructions`. Accepted: labels (including numeric `1:` with `1b`/`1f`), `#`
comments, ignored directives (`.text`, `.globl`, `.p2align`, `.type`, `.size`, `.cfi_*`,
`.section`, `.file`, `.loc`), mnemonics with `q`/`l`/`w`/`b` size suffixes on scalar ops,
operands `%reg`, `$imm`, `disp(%base,%index,scale)` with displacement expressions such as
`4+0(%rsi)`, `symbol(%rip)`, `%st`/`%st(i)`, a write mask `{%k1}`, rounding `{rn}`/`{rd}`/
`{ru}`/`{rz}`, swizzles `{cdab}`..., `{1to16}`/`{4to16}`/`{1to8}`/`{4to8}` and `{float16}`/
`{uint8}`/`{sint8}`/`{uint16}`/`{sint16}` on a memory operand (up-conversion) or on a store's
register source (down-conversion), `lock addl $imm, mem`, `rep ret`. Operands are reversed
into Intel order; record ids become `L<line>`.

## Scenarios

- `memory.type`: `fixed_level` (`level`), `classified` (`default`, `ranges` of `{start,end,level}`),
  `line_tracking` (`cold_level`, optional `warm` ranges, and the sub-models `tlb`,
  `hardware_prefetcher`, `memory_service`, each `"off"` or `"modeled"`; `page_bytes` 4096 or
  2097152).
- `branch.type`: `all_predicted`, `all_mispredicted`, `exit_mispredicted` (a branch whose direction
  differs from its previous instance), `ids_mispredicted` with `ids`.

## Traces

`simulate` and `bounds` need a dynamic trace per context. Default `--trace-source functional`
runs the exact interpreter (addresses, taken branches, gathered lines and x87 physical
registers come from execution; a wrong expected output stops the run with
`functional_mismatch`). `--trace-source static` unrolls straight-line code or one loop
(`loop.label`, `loop.trip_count`) without executing: memory records then need `addr {start,
stride}`, gathers a `lines` hint, x87 instructions are serialized, and the functional check is
reported as not run. No trace from the card is ever required.

## Batch manifests (`knc-twin.batch/1`)

```json
{"schema": "knc-twin.batch/1", "name": "gate variants", "profile": "card-7120-measured",
 "frozen_profile_hash": "<64 hex>", "baseline": "knc-switch-off", "too_close_fraction": 0.05,
 "candidates": [{"name": "knc-switch-off", "kernel": "k_off.json", "shape": "x87_csr_row"}, ...]}
```

`batch` refuses a profile whose hash differs from `frozen_profile_hash`, ranks the candidates
that reach status `ok`, and writes a native request under `queue/<name>/` for every candidate it
cannot rank: non-ok status, memory behaviour beyond L1 without a validated shape, or a ratio to
the baseline within `too_close_fraction`.

## Analytic parameters

`bounds --scale card|pair --params file.json`: see `schemas/analytic-params.schema.json` and
`analytic-scales.md`.
