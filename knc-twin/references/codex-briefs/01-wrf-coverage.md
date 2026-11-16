# Codex ticket brief: knc-twin, finish coverage of PhiWeather's WRF hot routines

For the GCC-KNC lead to dispatch on a Codex lane (`tools/dispatch.py`; backend codex, depth deep,
model per `harness/policy.json`, today gpt-6-astra). Branch `twin/0.3` of gcc_knc, folder `knc-twin/`.
The engine, adapter and tests are standard-library Python 3.8; keep it so. Never copy vendor text
(ADR-0013): facts and page references only from `docs/research/knc-references.md` (R-numbers) and
the ISA manual text at `.work/_shared/intel-327364-001-xeon-phi-isa.txt`.

## Where this starts

knc-twin 0.3.1 reads and executes the 13 mnemonics PhiWeather listed (see `CAPABILITY_REPORT.md`
section 1b and `tests/test_wrf_forms.py`). `tests/heldout_native/wrf_coverage.py` converts the 13
routines from the objects in
`C:\Users\xuzhi\Documents\PhiWeather\artifacts\test-state\accuracy-host-20261113\patched-gccknc-build-20261115\WRF-4.8.0-patched`
(read-only; the study with the defect list is `...\twin-study-20261116\STUDY.md`, section 9, and
`coverage-functions.md`, `coverage-loops.csv`). Today 9 of 13 convert whole; timing waits on one
parameter (scatter occupancy). Still blocked:

1. `advect_scalar`, `advect_scalar_pd` (`module_advect_em.o`): `jmpq *0x0(,%rdx,8)` with an
   `R_X86_64_32S .rodata+0x88` relocation, i.e. a switch jump table whose entries are
   `R_X86_64_64` relocations into `.text` in `.rela.rodata`.
2. `mp_thompson`: 48 `vcvtps2pd %ymm0,%zmm0` (the source is the low 256 bits written as `%ymm`).
3. `mynnedmf_driver` is in `module_bl_mynnedmf_driver.o` and `sixth_order_diffusion` in
   `module_big_step_utilities_em.o`: add them to `wrf_coverage.ROUTINES`.
4. WRF tiles are 6 to 10 points wide, so the 16-lane vector main loops are never entered; the
   executed code is the masked remainder path. `from_binary.py` has no loop-region mode (only
   `from_gcc_s.py --loop` has), so a user cannot cut the remainder loop out of the function.
5. `from_binary.py` stops at the first unsupported instruction; there is no complete-listing mode
   (PhiWeather wrote `tools/coverage.py` locally to get per-line coverage).
6. Callees: `__knc_vmath_expf_16`, `expf`, `__module_bl_mynnedmf_MOD_qsat_blend`,
   `__module_bl_mynnedmf_MOD_tridiag2`, `__module_bl_mynnedmf_MOD_moisture_check`, `memcpy`,
   `memset`, `malloc`, `free` need costed stubs or `--with-callee`.

## Work items

A. **Jump tables in the binary adapter.** In `scripts/knc_model/elf.py` read `.rela.rodata` (and
`.rela.rodata.*`); in `scripts/from_binary.py`, for `jmp *disp(,%reg,8)` with a relocation to a
rodata symbol, resolve the table: entries are 8-byte relocations into the function; emit a
`jmp_table` record (new ISA entry, class `branch`, functional handler: index register value selects
the target label; out-of-range index is `invalid_input`). Timing: a taken indirect jump; whether it
is predicted follows the scenario's branch rule (document the assumption; R02 ch.4 says nothing
about indirect targets). Bounds: unsupported in the reorder search (branches already are). Test:
a hand-built object is not needed; test the resolver on a recorded listing plus a synthetic
`Elf`-like object, and the handler on a kernel with a `jmp_table` record.

B. **`vcvtps2pd %ymm` form.** Accept `%ymm0-31` as a register name meaning the low 8 lanes of the
same zmm (`kernel.py` Reg; a `ymm` operand is the zmm base, width 256) for `vcvtps2pd` and the
converting forms that take it; functional semantics are the existing `vcvt_s2d` on lanes 0-7.
Reject `%ymm` anywhere else with a clear message.

C. **Loop-region mode for `from_binary.py`.** `--loop ADDR|LABEL [--function NAME]`: the region
is the loop head (an address or an `.A_xxxx` label) to its last backward branch; exits become
jumps to a synthetic end label, as `from_gcc_s.loop_region` does; the kernel's `entry` stays
`region` and live-in registers get placeholders. Include the same `--report` coverage output.
Add `--innermost` to list the function's innermost loops with their addresses, instruction counts
and the twin's coverage, so a user can pick the masked remainder loop WRF executes.

D. **Complete-listing mode.** `--report` must never stop at the first unsupported instruction:
convert what parses, record every unsupported line with its address, text and reason, and write
the kernel only when the list is empty (as `from_gcc_s.py --loop ... --report` does). Replace
PhiWeather's `tools/coverage.py` need: `wrf_coverage.py` gets per-loop rows from the same report.

E. **Scatter cost and the reciprocal tables.** Nothing to measure here (card time is after M4):
make `import-native` accept the two new measurement kinds the calibration plan names
(`references/calibration-plan.json`: `scatter`, `rcp23-table`): a per-line scatter occupancy row,
and a table file (2^23 or 2^24 32-bit entries) that `vrcp23ps`/`vrsqrt23ps` then use instead of
the correctly rounded stand-in, with the kernel result no longer marked approximate. Table files
live under `fixtures/tables/` and are loaded lazily; add a 1,024-entry synthetic table test.

F. **Stubs for the WRF callees.** A `calls` file template for the six callees above with
`status: assumed` costs and the model each needs (`libm.f32.exp` for `expf`; `none` with a cost
for the Fortran helpers until they are included with `--with-callee`), and a documented example in
`references/input-format.md`.

## Done when

- `wrf_coverage.py` reports all 13 routines converting whole (functional complete), with the
  loop list per routine; the only timing blocker left is `occupancy.scatter_cycles_per_line`.
- `selftest` passes with new tests for A to E (red first for the parser and resolver changes).
- `CAPABILITY_REPORT.md` section 1b and `references/input-format.md` updated; `AUDIT.md`
  regenerated; nothing in the recorded held-out predictions changes (run
  `scripts/validate_heldout.py --cases tests/heldout_native` without `--record` and show no
  "differs" line), or re-record with a stated reason.
- Host rule until the lead says M4 is done: one single-threaded process at a time, no builds, no card.
