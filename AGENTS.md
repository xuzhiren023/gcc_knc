# AGENTS.md: GCC-KNC engineer rules

You work on **one ticket** in a fresh session, in its own worktree. Your ticket is your brief:
`python tools/pm.py show <ID>`. Do not read the plan or other documents unless the ticket
points to them. You talk to the tech lead only through the ticket, and to nobody else.

## Commit with one command

Always commit with `python tools/pm.py commit <ID> -m "<message>"`, alone in its command. It
stages everything in your worktree. `git add` and `git commit` inside a longer script fail on
the sandbox's protection of `.git`.

## Finish with one command

- `python tools/pm.py submit <ID> --note "<what ran, results, log path>"` when acceptance is met
- `python tools/pm.py red <ID> --note "..."` on deep code tickets, after the failing test commit
- `python tools/pm.py ask <ID> "<reduced reproducer and specific question>"` after two real failed attempts, or if a rule below blocks you

Then stop. Do not write a summary, and do not start another ticket.

## Spend carefully

- **Test what the ticket asks for, once.** Do not re-verify passing work, add tests beyond the acceptance criteria, or check the same thing a second way.
- **No hashing, checksums, manifests of hashes, receipts or provenance files.** Git identifies content.
- **Builds and tests go through** `python tools/run.py --name <name> --inputs <paths> -- <command>`. It keeps output short and skips repeats. Do not read whole logs: search them, or read the tail.
- Read files in parts, and search before you open anything large.
- Hooks enforce most of this. If one refuses a command, do not look for a way around it. Change approach, or ask.

## Keep the disk small

- Everything in your worktree is deleted when the ticket merges. Keep nothing there that must outlive the ticket.
- The GCC checkout, toolchain and build trees live once, in the shared build area (`.work/_shared`). Never copy them.
- No per-attempt, per-run or dated output folders. Overwrite the previous output, and delete what you no longer need.
- Large inputs and outputs stay out of git. Ask the lead if something truly must be kept.

## Test first

Code tickets: a `test(<ID>): ... [red]` commit that fails for the expected reason, then the
smallest passing change, then an optional refactor. Tests must be able to fail. Do not weaken,
skip or `xfail` a test to make progress.

## Report results as they are

A test that has not run on the card has not passed natively. Never invent or extrapolate a
result. Report infrastructure failures as infrastructure failures.

## Do not change

`tests/acceptance/`, `docs/adr/`, `harness/`, `.codex/`, `work/tickets/`, this file, or
milestone criteria. Ask if you think one is wrong. Do not push or merge.

## Compiler rules

- KNC never sets `TARGET_AVX512F` or any SSE or AVX flag. Vector patterns go in `gcc/config/i386/imci.md`, conditioned on `TARGET_KNC`.
- The donor GCC is a reference. Check that a mechanism still exists before porting anything.
- Keep shared i386 changes minimal and in separate commits.
- No implicit fast-math or precision change. Vector divide and square root stay scalar until proven correct for that mode.
- Do not hide a cost. Spills, helper calls and memory transfers must be visible to the optimizer.
- Do not emit opaque bytes to get around the assembler's architecture checks.
- Do not tune to one program. This is a general-purpose compiler.

## Environment

- Compilers run on the host, and programs run on the card. Use the card only through `tools/card_run`. It may be in use by other work, and other projects' folders are read-only.
- Windows 10, 12 threads, about 16 GB of memory. Use `make -j8` at most.
- Until S0-01 is done, tools are in `C:\Users\xuzhi\Documents\PhiWeather\.tools\knc-bootstrap`. Put its `cross\bin` and `cygwin\bin` on `PATH`, and use that Cygwin's `python3`, `gcc` and `make`.
- GCC checkouts need `core.autocrlf=false` and `core.fileMode=false`.
- Keep build trees, dumps, sysroots and vendor documents out of git.
- Commits are `test(ID): ... [red]`, `feat(ID): ...`, `fix(ID): ...`, `refactor(ID): ...`, or `docs(ID): ...`. Give the reason, and the source (ISA section, paper or donor file) where relevant.
