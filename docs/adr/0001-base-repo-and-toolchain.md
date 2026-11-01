# ADR-0001: GCC base, repository layout and toolchain pins

**Status:** Accepted, subject to Gate A. **Date:** 2026-11-01. **Decider:** Claude; the owner may overrule.

## Decision

| Topic | Decision |
|---|---|
| Compiler base | The GCC 16 release branch, starting at tag `releases/gcc-16.2.0`. |
| Fallback | GCC 14.4 only if Gate A records a concrete blocker in 16.2. Being merely harder is not a blocker. |
| Fork lifetime | Permanent private fork. Pick up 16.x fixes when needed. Move to a new major version only for a concrete need, not on a schedule. |
| Source location | A GCC fork in its own repository, checked out at `compiler/gcc` as a git submodule. This repository holds tests, tools, docs and runtime code. |
| Assembler and linker | MPSS binutils 2.22+mpss3.8.6. Bootstrapped from the existing local build; this project has its own copy or rebuild by the end of Sprint 0. |
| Link sysroot | The sysroot derived from the card (glibc 2.21). Native tests run against the card's installed libraries. |
| Build host | Cygwin with GCC 14.4, pending Gate A. If the TDD loop misses its budget, ask the owner to enable WSL2. |
| Target triple | `k1om-mpss-linux`, matching the existing tools. |
| LTO | Disabled. It needs a newer binutils than we can use. |

## Why

**A separate GCC repository.** GCC's tree and history are too large to share with
planning documents and tests. Keeping them apart keeps this repository quick to clone
and keeps compiler commits reviewable with ordinary `git log`. Patches can be exported
from the fork for any release audit.

**A permanent fork.** GCC 15 removed Knights Landing and Knights Mill, and binutils
2.39 removed K1OM. Upstream acceptance of a Knights Corner target is not a realistic
plan, so rebase cost is a design constraint. Keep the patch series small and
modular, and keep KNC code in new files wherever possible.

**GCC 16 over 14.** It starts the longest available support window, and a private fork
benefits from a recent base. The bridge option stays open until Gate A has real data.

## Consequences

- The owner must create the fork repository before S1 (or accept a local-only fork
  for now).
- Set `core.autocrlf=false` and `core.fileMode=false` in the GCC checkout. The donor
  checkout on this machine shows every file modified because of line endings, so its
  `git status` cannot be trusted.
- A GCC source tree on Windows also has case-sensitivity concerns. S0-06 checks this.
- This project is independent of PhiWeather. Its `.tools` folder is read-only bootstrap input until Sprint 0 ends.
