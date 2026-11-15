# Input format

Schema: `schemas/kernel.schema.json` (`knc-twin.kernel/1`). Examples: `fixtures/*.json`.

## Kernel

```json
{
  "schema": "knc-twin.kernel/1",
  "name": "saxpy_loop",
  "unit_of_work": {"description": "16 floats of y = a*x + y", "count": 4},
  "numerical_policy": {"rounding": "rn", "ftz": false, "daz": false, "nan_compare": "any_nan"},
  "init": {"memory": [{"addr": "0x100000", "f32": [1, 2, 3]}], "registers": {"zmm2": {"f32_broadcast": 2.0}}},
  "streams": [{"context": 0, "init": {"registers": {"rax": "0x100000"}}, "instructions": [ ...records... ]}],
  "loop": {"label": "L", "trip_count": 4},
  "scenario": {"memory": {"type": "fixed_level", "level": "l1"}, "branch": {"type": "all_predicted"}},
  "expected": {"memory": [{"addr": "0x200000", "f32": [3, 5, 7]}], "registers": {"0": {"rcx": 64}}}
}
```

- `unit_of_work.count`: units completed by one run of all streams. Predictions are also given
  per unit. With `--contexts` selecting a subset, the count is scaled proportionally.
- `init.registers` applies to every stream; a stream's `init.registers` overrides.
- Values: integers may be decimal or `"0x..."` strings. `f32`/`f64` lists accept numbers that
  are exactly representable (anything else is rejected: give the bit pattern `"0x3f800001"`),
  `"nan"`, `"inf"`, `"-inf"`, `"-0.0"`. zmm registers: `{"f32": [16 values]}`, `{"u32": [...]}`,
  `{"f64": [8]}`, `{"u64": [8]}`, `{"f32_broadcast": x}`, `{"u32_broadcast": x}`, `{"f64_broadcast": x}`.
  Mask registers: 16-bit integers. `flags`: `{"ZF": 1, ...}`.
- `memory_default`: byte value for reads of uninitialized memory; without it such a read is
  `invalid_input`.
- `expected`: registers per context (keyed by context index as a string) and memory blocks.
  NaNs match any NaN unless `nan_compare` is `"bits"`.

## Records (Intel operand order, destination first)

```json
{"id": "fma", "op": "vfmadd231ps", "ops": ["zmm1", "zmm2", {"base": "rax", "index": "rcx", "scale": 4, "disp": 64}],
 "mask": "k1", "rounding": "rn", "label": "L", "encoding": {"disp32": false}, "deps": ["ld"], "comment": "..."}
```

- `op`: a mnemonic from `capabilities` (`knc_twin.py capabilities`). Anything else is rejected.
- `ops`: registers (`rax`, `eax`, `zmm0`..`zmm31`, `k0`..`k7`), immediates (int or string),
  labels (branch targets), memory operands `{"base","index","scale","disp","broadcast","vindex"}`.
  `broadcast` is `"1to16"` or `"1to8"`; other swizzles are unsupported. Gathers use `vindex`.
- Operand roles per mnemonic are in `scripts/knc_model/isa.py`. FMA forms: 132 = op1*op3+op2,
  213 = op2*op1+op3, 231 = op2*op3+op1. Conversions take a rounding immediate (bits 1:0:
  rn, rd, ru, rz; exponent-adjust bits must be zero). Compare predicates: FP 0 eq, 1 lt, 2 le,
  3 unord, 4 neq, 5 nlt, 6 nle, 7 ord; integer 0 eq, 1 lt, 2 le, 4 ne, 5 nlt, 6 nle.
- `mask`: write mask with merge semantics; on gathers it is the completion mask (cleared).
- `width`: 32 or 64 for scalar memory forms with no register to imply it.
- `encoding`: optional hints (`bytes`, `disp32`, `disp`, `imm`) for the pairing rules.
- `deps`: extra explicit dependencies on earlier ids (e.g. x87 stack, fences).
- `addr {start, stride}` and `lines`: address descriptions for static traces (below).
- 8/16-bit registers, memory-destination ALU forms, `rsp` writes (for prepare-native) and
  swizzle modifiers are rejected.

## GAS AT&T subset

A stream may give `"asm_file": "kernel.s"` (relative to the kernel file) or `"asm": "..."`
instead of `instructions`. Accepted: labels `L:`, `#` comments, ignored directives (`.text`,
`.globl`, `.p2align`, `.type`, `.size`, `.cfi_*`, `.section`, `.file`), mnemonics with `q`/`l`
size suffixes on scalar ops, operands `%reg`, `$imm`, `disp(%base,%index,scale)`, a write mask
`{%k1}` and rounding `{rn}`/`{rd}`/`{ru}`/`{rz}` on the destination, `{1to16}`/`{1to8}` on a
memory source, `lock addl $imm, mem`. Rejected: any other swizzle, `w`/`b` suffixes, segment
prefixes, `ret`/`nop` (strip the epilogue), unknown mnemonics and directives. Operands are
reversed into Intel order; record ids become `L<line>`.

## Scenarios

- `memory.type`: `fixed_level` (`level`), `classified` (`default`, `ranges` of `{start,end,level}`),
  `line_tracking` (`cold_level`, optional `warm` ranges, `hardware_prefetcher` must be `"off"`).
- `branch.type`: `all_predicted`, `all_mispredicted`, `exit_mispredicted` (a branch whose direction
  differs from its previous instance), `ids_mispredicted` with `ids`.

## Traces

`simulate` and `bounds` need a dynamic trace per context. Default `--trace-source functional`
runs the exact interpreter (addresses, taken branches and gathered lines come from execution; a
wrong expected output stops the run with `functional_mismatch`). `--trace-source static` unrolls
straight-line code or one loop (`loop.label`, `loop.trip_count`) without executing: memory
records then need `addr {start, stride}` and gathers a `lines` hint; the functional check is
reported as not run. No trace from the card is ever required.

## Analytic parameters

`bounds --scale card|pair --params file.json`: see `schemas/analytic-params.schema.json` and
`analytic-scales.md`.
