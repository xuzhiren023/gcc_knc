# ADR-0006: Shared i386 changes must stay correct for x86 and portable to new GCC releases

**Status:** Accepted. **Date:** 2026-11-03. **Decider:** owner (direction), Claude (rules).

## Context

The owner chose on 2026-11-03 to keep KNC inside GCC's i386 backend, on two conditions: it must
be correct, and it must not break apart every time GCC is updated. Our work has to carry forward
to future GCC releases.

Until now the only measure was a count of changed shared lines (ADR-0002, M1's 300). A count does
not say whether a change rots on the next release or quietly changes x86_64 code.

First measurement, by the lead on 2026-11-03: our whole diff (`releases/gcc-16.2.0..knc`, 25
files) applied onto upstream `master` at `7eb405c3d11` (2026-11-01, GCC 17 development) with
`git merge-tree --merge-base=releases/gcc-16.2.0`. Upstream had changed the i386 files we touch by
thousands of lines since 16.2 (`i386-expand.cc` +3,390/-478, `i386.md` +2,394/-1,445, `sse.md`
+1,929/-163, `i386.cc` +1,306/-448). Only two files conflicted, both trivially:

- `i386-c.cc`: upstream fixed a typo in the comment next to our `__KNC__` block.
- `i386-protos.h`: upstream added prototypes where we added `ix86_expand_knc_cas`.

That is textual portability only. Whether trunk with our diff builds and passes our tests is not
measured yet.

## Decision

1. **Shared files hold hooks, not code.** A shared change is one of three things:
   - a `TARGET_KNC` term in an existing condition;
   - an early `if (TARGET_KNC) return ix86_knc_...;` into `i386-knc.cc`;
   - one entry in a table, option or iterator.

   Function bodies, `switch` tables and prototypes go in `i386-knc.cc` and `i386-knc.h`, never
   `i386-protos.h`. The existing `ix86_expand_knc_cas` in `i386-expand.cc` and the move `switch`
   in `ix86_expand_move` move out (S3-13).
2. **Hooks sit where upstream rarely edits:** at a function's entry, or at its own line in a
   condition. Do not insert them in the middle of code that upstream is rewriting.
3. **Never copy upstream code into a KNC file to change it.** A copy compiles today and silently
   misses upstream fixes. Call the original, or hook in front of it.
4. **Machine description:** KNC patterns live in `imci.md`. Shared `.md` changes are limited to
   expander-only iterators and conditions (ADR-0005). An existing SSE or AVX pattern is never
   widened to cover KNC.
5. **x86 stays unchanged.** A C-only `x86_64` `cc1` built from our tree and one built from the
   stock release give identical `-O2` and `-O2 -mavx512f` assembly over the torture compile files.
   This is checked at every milestone (S3-11 for M1), and from Sprint 4 once per batch check
   (`docs/DEVELOPMENT_CYCLE.md` section 4): after every two or three merged gcc tickets that
   change a shared file, not after each one (owner, 2026-11-04).
6. **A forward-port drill runs at each sprint end and each milestone.** It applies our diff onto
   the newest upstream `master` and the newest release branch, and records the conflicts per file
   in `docs/research/forward-port.md`. At each milestone it also builds trunk with our diff
   (C-only) and runs T1 and T2 against it. Conflicts, build breaks and test failures there are
   portability findings, ticketed like bugs.
7. **What gets reported.** Shared lines stay counted, alongside three more figures: the number of
   hunks in shared files, the drill's conflicts, and any x86_64 differences. M1's go decision weighs
   all four.

## Consequences

- A little more indirection: logic sits in `i386-knc.cc` behind a one-line hook. That is the point,
  because upstream churn then touches a line, not a block.
- Two new costs per milestone: an x86_64 `cc1` build per tree (about an hour each the first time,
  incremental after), and a trunk build for the drill.
- The drill needs a current `upstream`. Refreshing it is a `git fetch` from gcc.gnu.org, which the
  owner allows or does. The engineer never has network access.
- Tickets that touch shared files cite this ADR, and reviews check rules 1-4.
