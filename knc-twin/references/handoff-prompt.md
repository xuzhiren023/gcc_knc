# Prompt for an agent that is handed knc-twin 0.4.0

Paste the text below into the other agent's instructions. It states what the twin does, how to set it
up, the one use it is good for, and every known issue as of 2026-11-16.

---

You have the `knc-twin` skill, version 0.4.0 (`python scripts/knc_twin.py --version`). It is a
standard-library Python model of the Intel Xeon Phi Knights Corner (K1OM/IMCI) core: it executes a
compiled function or loop exactly (scalar, vector, mask, x87, gather/scatter, calls into the region,
costed stubs for calls out of it) and predicts its cycles with a cycle model of one core (four
in-order contexts, U/V pairing, decoder prefix delays, store/load path, L1/L2, DTLB, L2 hardware
prefetcher, memory service rate), all measured on the project's 7120-class card. Since 0.4.0 it also
simulates 1 to 8 detailed cores on the full ring with every memory controller, as an unvalidated
scenario. Read `SKILL.md` first and follow its workflow in order.

**Setup (pick one)**
- Claude Code: `unzip knc-twin.zip -d ~/.claude/skills/` so that `~/.claude/skills/knc-twin/SKILL.md`
  exists, or point at `knc-twin/` in the gcc_knc repository on `main`. Python 3.8 or newer, standard
  library only, no network. Run `python scripts/knc_twin.py selftest --out <dir>` once (about two
  minutes; expect all tests passing) and `capabilities --out <dir>` to see the supported instruction set.
- Claude.ai: Settings > Capabilities > Skills > Upload skill, choose `knc-twin.zip`.
- Inputs you need from your build: the object file or executable that ran (or will run) on the card,
  its `k1om-mpss-linux-objdump -dr` listing, the input arrays of the measured run as binary files, and
  an independently computed expected result. Never hand it a simplified or hand-edited `.s`.
- Use the Windows or Linux CPython the project uses for everything else. On Cygwin Python the model
  runs several times slower, and the held-out replay then exceeds its budgets.

**What it is good for (its one real job):** ranking variants of a hot function or loop before you
spend card time, and saying what binds each one (issue slots, a dependency chain, x87 serialization,
misses, decode). On held-out compiled code from the card (105 rows: the S12-31 x87 row loops with every
padding and ordering variant, HPCG SpMV/SymGS cache-resident and memory-bound, the S12-30 sparse
products) its median error is 3.1% and it picked the right winner in 39 of 39 pairs that differ by more
than 5%. For the shapes listed as validated in `references/validation.md` the result is a
`calibrated_forecast` with that band. Everything else is an `unvalidated_scenario_estimate`: good for
bounds, mechanisms and large differences, not for choosing between variants within about 30%.

**How to use it well**
1. `python scripts/knc_twin.py capabilities --out d`; stop at anything your code uses that is not listed.
2. Convert the binary: `python scripts/from_binary.py prog.o --function NAME --disassembly prog.dis
   --init init.json --out k.json`. Options new in 0.4.0: `--loop ADDR|.A_xxxx` converts one loop region
   (exits become the end of the region), `--innermost` lists candidate loops with coverage, `--report`
   lists every unsupported line of a function without writing a partial kernel. Declare callees outside
   the region as costed stubs in `init.json` (`calls`: none, noreturn, memcpy/memmove/memset,
   libm.f64.NAME, and since 0.4.0 malloc/calloc/realloc/free on a declared `init.heap`); bind the measured
   run's arrays as `init.memory` file blocks; put the expected output in `expected`; set
   `provenance.shape` if a validated shape applies.
3. `simulate k.json --out d` for each variant with the same profile and scenario. Rank with `compare`
   (two results) or `batch manifest.json` (a candidate set under a frozen profile hash). For a loop too
   long to simulate to the end, `sample-loop k.json --loop LABEL` samples iterations until the window
   series agrees and the input's period is covered, and reports the spread; every sampled figure is an
   estimate. `rollup manifest.json` turns region ratios and measured time shares into a program figure
   (seconds per step); it accepts `phases` with per-phase shares.
4. To find a better instruction order for a block or loop body, `schedule k.json --method
   beam|list|modulo --out d` searches dependency-preserving orders under the measured pairing and
   latency rules and exports GAS text; on the S12-31 row loop it finds the compare-next-to-jump order the
   card measured 11% faster. Its results are estimates unless the kernel's shape is validated.
5. Report only numbers from a run with status `ok`, with the `result_class`, `assumptions`,
   `unsupported` and `limiting_constraints` fields. A `missing_parameter` or `unsupported` status is the
   answer, not something to work around. Variants the model cannot separate (within the band, unvalidated
   memory behaviour, stub-dependent) go to the card as a `prepare-native` request.
6. After a card window: `calibration-plan`, then `import-native` (kinds: timing, scatter, rcp23-table),
   then add the window's runs as held-out cases. The twin improves only through that habit.

**Known issues on 2026-11-16 (check the ticket board for their state)**
- Scatter cost per cache line is still unmeasured: a region with a scatter stops with
  `missing_parameter`. Card window 10 measured it at 2 threads; S14-23 imports that value, and the 1- and
  4-thread points come with the next card turn. The lock-prefix fence cost is also unmeasured.
- Multi-core (`simulate --scale unit|ring`): implemented, not validated. Every number is an
  `unvalidated_scenario_estimate` until S14-21 compares it with the measured GEMV (125.3 GB/s) and triad
  (168.2 GB/s) rows. Use it for mechanisms and relative effects, not for bandwidth figures.
- `prepare-native` wrote absolute memory operands as `N()`, which the K1OM assembler rejects, and
  `rollup` could label a manifest without candidates a `calibrated_forecast`. Both fixes are on ticket
  S14-15 (merging today); until it is on main, relocate such operands by hand or avoid absolute addresses
  in native requests, and read a roll-up's class with that caveat.
- A region containing an indirect `jmp *` or `call *` through the GOT (a PLT tail call on an error
  path) is refused even when that path never executes. S14-20 makes it fail only when executed; until
  then cut the region before the branch or route it to an exit label.
- Random-column sparse products (S12-30 small) run 12 to 18% slow in the model; their ranking is right,
  their absolute time is not. Listed as an open miss, not a validated shape.
- `vrcp23ps` and `vrsqrt23ps` are correctly rounded stand-ins, not the hardware tables; results that
  depend on them are marked approximate until the rcp23 capture is imported.
- Profiles for the 3120 and 5110P carry the 7120 core timing as transferred values; they are not
  calibrated on those cards.
- The held-out replay is out of the regular regress (set `KNC_TWIN_HELDOUT=1`, or run
  `validate_heldout.py --max-seconds 0`); it takes about 45 minutes on a host interpreter.
- The `schedule` command writes its `result_class` as a plain string; the other commands write a
  dictionary. Readers of result.json should accept both until it is unified.
- The one-core engine runs about 20,000 simulated instructions per second: whole programs, OS, system
  calls, files, MPI and shared-memory processes are out of scope. It is not an emulator.

Final speed numbers come from the card. The twin decides which candidates deserve card time and why.
