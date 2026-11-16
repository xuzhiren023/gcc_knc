# Prompt for an agent that is handed knc-twin

Paste the text below into the other agent's instructions. It states what the twin can do, what it
cannot, and the one use it is good for.

---

You have the `knc-twin` skill (`~/.claude/skills/knc-twin`, or `knc-twin/` in the gcc_knc repository,
branch `twin/0.3`; run `python scripts/knc_twin.py --version`, expect 0.3.0). It is a standard-library
Python model of ONE Intel Xeon Phi Knights Corner (K1OM/IMCI) core: it executes a compiled function or
loop exactly (scalar, vector, mask, x87, gather/scatter, calls into the region, costed stubs for calls
out of it) and predicts its core cycles with a cycle model of the four in-order contexts, the U/V
pairing rules, the decoder's prefix delays, the store/load path, L1/L2, DTLB, L2 hardware prefetcher
and the memory service rate, all measured on the project's 7120-class card. Read `SKILL.md` first and
follow its workflow in order.

**What it is good for (its one real job):** ranking variants of a hot function or loop before you
spend card time. Give it the object file or executable that will run (not the `.s`), the same input
arrays the measurement will use, and an independently computed expected result; it tells you which
variant is faster and what binds it (issue slots, a dependency chain, x87 serialization, misses,
decode). On held-out compiled code from the card (105 rows: the S12-31 x87 row loops with every
padding and ordering variant, HPCG SpMV/SymGS cache-resident and memory-bound, the S12-30 sparse
products) its median error is 3.1% and it picked the right winner in 39 of 39 pairs that differ by
more than 5%. For the shapes listed as validated in `references/validation.md` (x87 sparse row loops in
L1, L2 or streaming from memory; register vector chains; scalar/mask chains; x87 register chains;
L1/L2 dependent loads; L1 stores with prefetch) the result is a `calibrated_forecast` with that band.
Everything else is an `unvalidated_scenario_estimate`: usable for bounds, mechanisms and large
differences, not for choosing between variants within about 30% of each other.

**How to use it well**
1. `python scripts/knc_twin.py capabilities --out d` and stop at anything your code uses that is not listed.
2. Convert the binary: `python scripts/from_binary.py prog.o --function NAME --disassembly prog.dis --init init.json --out k.json`
   (`prog.dis` = `k1om-mpss-linux-objdump -dr prog.o`). Declare callees outside the region as costed
   stubs in `init.json` (`calls`); bind the measured run's arrays as `init.memory` file blocks; put the
   expected output in `expected`; set `provenance.shape` if a validated shape applies. Never simplify the
   code to make it run.
3. `simulate k.json --out d` for each variant with the same profile and scenario; `compare` or `batch`
   (frozen profile hash) to rank; `rollup manifest.json` to turn region ratios and measured time shares into
   a program figure such as seconds per step.
4. Report only numbers from a run with status `ok`, together with the `result_class`, `assumptions`,
   `unsupported` and `limiting_constraints` fields. A `missing_parameter` or `unsupported` status is the
   answer, not something to work around. Send variants the model cannot separate (within the validated
   band, unvalidated memory behaviour, stub-dependent) to the card with the `prepare-native` request.
5. After a card window, run `calibration-plan`, import measurements with `import-native`, and add the
   window's runs as held-out cases; the twin improves only through that habit.

**What it is not**
- Not a system emulator: no OS, system calls, files, MPI or shared-memory processes; no whole-program
  runs (about 20,000 simulated instructions per second). It does not stand in for a forecast run or any
  application-level accuracy question.
- Not a card simulator: pair and card scales are formulas on measured bandwidths, no ring or memory
  controller; multi-core contention is a bound, not a prediction.
- Not calibrated on the 3120 or 5110P (their profiles carry the 7120's core timing as transferred
  values), and the lock-prefix fence and scatter costs are unmeasured (such regions stop with
  `missing_parameter`).
- The decision bar (median error at most 10%, right winner in at least 90% of pairs more than 5% apart,
  loops from at least five M4 programs) is met on error and ranking but not yet on breadth: trust it on
  the validated shapes, and treat a loop shape outside them as an estimate until it has been held out.

Final speed numbers come from the card. The twin decides which candidates deserve card time and why.
