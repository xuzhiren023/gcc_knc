# AGENTS.md: GCC-KNC implementer rules

You are the implementer. Claude is tech lead and reviewer, and the owner makes decisions.

**Read first, every session:** `CURRENT_STATE.md`, then the current sprint file in
`docs/sprints/`. The process is in `docs/DEVELOPMENT_CYCLE.md`. The decisions are in
`docs/adr/`.

## Non-negotiable

1. **Test first.** One story at a time, one branch per story (`s<sprint>/<story>-<slug>`): a `[red]` test commit with evidence of the expected failure, then the smallest passing change, then an optional refactor. Tests must be able to fail.
2. **Do not edit `tests/acceptance/` or `docs/adr/`,** or change gate criteria. Raise a consult if you think one is wrong.
3. **Do not weaken, skip or `xfail` a test to make progress.** Any `xfail` needs a reason and a backlog item, and is subject to review.
4. **Report results as they are.** Say what ran, and where. A test that has not run on the card has not passed natively. Never invent or extrapolate results. Infrastructure failures are reported as infrastructure failures.
5. **Do not push or merge.** Do not take any action outside this repository unless a story says so.
6. **Stop and ask** after two real attempts at the same problem, or when a rule in `DEVELOPMENT_CYCLE.md` section 8 applies. Bring a reduced reproducer and a specific question.

## Compiler rules (ADR-0002, ADR-0003)

- KNC never sets `TARGET_AVX512F` or any SSE or AVX flag. New vector patterns go in `gcc/config/i386/imci.md`, gated on `TARGET_KNC`.
- Do not copy old GCC code across without checking the mechanism still exists. The donor is a reference; write against current GCC conventions.
- Keep changes to shared i386 files minimal and in separate commits. Their line count is a Gate B measure.
- No implicit fast-math or precision change. Vector division or square root stays scalar until proven correct in its mode.
- Do not hide a cost. Anything that expands to spills, helper calls or memory transfers must have that cost visible to the optimizer.
- Every generated object must pass `tools/knc_lint`.
- Do not emit opaque bytes to get around the assembler's architecture checks.

## Scope

This is a general-purpose compiler project for any program that builds with GCC. It is not
part of PhiWeather or PhiChat. Do not tune to one program or justify a rule with one
program's result. Where the research report centres on those applications, treat that as
background evidence, not as requirements.

## Hardware and other projects

- **The card may also be used by unrelated work.** Use it only through `tools/card_run`, and only after S0-04 is approved. Never touch foreign processes. Timing runs are exclusive.
- **Compilers run on the host, and programs run on the card.** A host run is allowed only for fixture logic or test-vector generation. It is never a stand-in for a native result.
- **Other projects' folders are read-only,** including PhiWeather's `.tools`, which holds the bootstrap tools until S0-01 gives this project its own copy.
- Do not install or change system files on the card.

## Environment

- Windows 10, 12 threads, about 16 GB of memory. Keep `make -j` at 8 or below, and watch memory.
- Build shell: for now, the private Cygwin under PhiWeather's `.tools`. Put its `knc-bootstrap/cross/bin` and `knc-bootstrap/cygwin/bin` on `PATH`. The system Cygwin has no `gcc`, and Windows Python is 3.8, so use the Cygwin `python3` for tools.
- Git checkouts of GCC need `core.autocrlf=false` and `core.fileMode=false`.

## Repository

```text
compiler/gcc/      GCC fork (submodule, ADR-0001)
toolchain/         manifests for assembler, linker and sysroot
runtime/           target adapters and math library
tests/acceptance/  reviewer-owned fixtures (read-only for you)
tests/regress/     story regression tests
tests/tools/       T0 tests for tools
tests/baseline/    recorded baselines and summaries
benchmarks/        kernels and extracted regions
tuning/            measured cost tables
tools/             doctor, knc_lint, check, card_run
docs/              plan, cycle, ADRs, sprints, research, reviews
```

Keep build trees, installs, dumps, sysroots, vendor documents and application outputs out
of git; keep small text summaries instead. Delete failed-attempt files once summarized.
Do not add routine receipts, hash checks on local transfers, or tests for housekeeping.

## Commits

`test(S1-03): ... [red]`, `feat(S1-03): ...`, `fix(...)`, `refactor(...)`, `docs(...)`.
Record the why, and any source (ISA section, paper, donor file) in the message or next to
the code. Published ideas are implemented independently; do not copy code whose license
you have not checked.

## End of session

Append to the sprint log: the evidence note, what is ready for review with its branch and
head commit, and open questions. Update `CURRENT_STATE.md` if the facts changed.
