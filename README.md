# GCC-KNC

GCC-KNC is a GCC 16.2 cross compiler for the Intel® Xeon Phi™ x100 coprocessor (Knights
Corner, KNC). It compiles ordinary C, C++ and Fortran into native KNC programs that use the
card's 512-bit IMCI vector unit. The compiler runs on a host PC. The programs run on the card.

It is a general-purpose compiler. It is not tuned to any one application.

## Status

The project is in milestone M4 (broad optimization). M1 to M3 are accepted. M5 (program corpus)
and M6 (release) are still ahead. [STATUS.md](STATUS.md) shows the tickets, and
[CURRENT_STATE.md](CURRENT_STATE.md) shows what is proven and how.

| Milestone | What it means | State |
|---|---|---|
| M1 Mixed native code | Scalar KNC code, the K1OM ABI and links with GCC 5.1.1 objects | Accepted 2026-11-04 |
| M2 Useful vector target | The vectorizer emits IMCI and beats x87 code on the card | Accepted 2026-11-07 |
| M3 Runtimes | libgcc, libstdc++, libgfortran, libatomic and libgomp run on the card | Accepted 2026-11-11 |
| M4 Broad optimization | Whole programs faster than the GCC 5.1.1 KNC compiler | Final measurement running |
| M5, M6 | Program corpus, then a release | Not started |

## What works

These results are at the Sprint 12 head (GCC `knc` `b2ce6a9eebf`, 2026-11-15).

- C, C++ and Fortran compile for `k1om-mpss-linux` with `-march=knc`. The output passes the
  project's ISA lint (`tools/knc_lint`): no SSE, AVX, `cmov`, `fcomi` or other non-KNC
  instructions.
- The vectorizer emits IMCI on `zmm` registers: packed float and double arithmetic, FMA,
  masked loop tails, gathers, scatters, prefetches and streaming stores.
- GCC's execute test suite passes natively on the card: 1,680 of 1,681. The one miss is a test
  harness option, not the compiler.
- On x86, the fork emits the same code as stock GCC 16.2: 1,962 of 1,962 files identical at
  `-O2 -mavx512f`.
- Runtime libraries for the card: libgcc (static and shared), libstdc++, libgfortran,
  libatomic and libgomp (OpenMP, up to 240 threads).
- `libknc_vmath`: vector `expf`, `logf`, `powf`, `exp`, `log` and `pow` within 1 ULP. Vectorized
  loops call it automatically.
- `-mphinix`: one flag for the measured best set of options.

## Known limits

- **Card hardware is needed to run programs.** Nothing here emulates KNC. You can build the
  compiler and produce assembly on any host.
- **The assembler and linker are old.** Linking needs the MPSS binutils 2.22 for k1om and a
  sysroot taken from a card. Upstream binutils removed K1OM in 2.39. Neither is in this
  repository (see [BUILDING.md](docs/BUILDING.md)).
- **No LTO.** binutils 2.22 cannot support it.
- **No IMCI intrinsics header yet.** Vector code comes from the vectorizer and from
  `libknc_vmath`.
- **IEEE floating point by default.** GCC-KNC keeps subnormals and correctly rounded division,
  unlike ICC's `-mmic` default. Use `-ffast-math` to opt out.
- **Profile-guided optimization works with the standard GCC flags.** Training must run on the
  card. A one-flag PGO driver is planned, not built.
- **The build scripts were written for a Windows host with Cygwin.** The Linux steps in
  [BUILDING.md](docs/BUILDING.md) are derived from them and are not yet tested on Linux.

## Two repositories

| Repository | What it holds |
|---|---|
| This one, [`gcc_knc`](https://github.com/xuzhiren023/gcc_knc) | Tests, tools, docs, tickets, decisions (ADRs) and the `libknc_vmath` source (`contrib/knc-vecmath`) |
| The GCC fork, [`gcc_16_knc`](https://github.com/xuzhiren023/gcc_16_knc), branch `knc` | The compiler: GCC `releases/gcc-16.2.0` plus the KNC changes, mostly in `gcc/config/i386/` (`imci.md`, `knc.md`, `i386-knc.cc`, `linux-k1om.h`) |

You need both. The tools in this repository expect the fork at `.work/_shared/gcc` and the KNC
toolchain at `.work/_shared/toolchain`. [BUILDING.md](docs/BUILDING.md) explains the layout.

## Start here

| Document | For |
|---|---|
| [Building](docs/BUILDING.md) | Building the compiler on Linux or on Windows with Cygwin |
| [Using](docs/USING.md) | Compiling for KNC: flags, OpenMP, vector math, PGO, examples |
| [Flags](docs/gcc-knc-flags.md) | What `-march=knc` and `-mphinix` do, and the ICC `-mmic` equivalents |
| [Card runs](docs/card-run.md) | How this project runs programs on the card |
| [Project plan](docs/PROJECT_PLAN.md) | Goals, milestones and risks |
| [Decisions](docs/adr/) | ISA, ABI, floating point, tuning and clean-room rules |
| [Development cycle](docs/DEVELOPMENT_CYCLE.md), [Collaboration](docs/COLLABORATION.md) | How the work is done |
| [`knc-twin/`](knc-twin/README.md) | A KNC core model for checking kernels on the host |

`AGENTS.md`, `CLAUDE.md`, `KICKOFF.md` and `work/tickets/` are for the agents that build this
project.

## Licence

- **This repository:** the project's own code, tests, docs and `knc-twin` are licensed under the
  Apache License 2.0 ([LICENSE](LICENSE)).
- **Third-party files** keep their own licences. In `contrib/knc-vecmath` these are the Arm
  optimized-routines licence (MIT or Apache-2.0 with LLVM exception) and the musl licence (MIT),
  as listed in its [PROVENANCE.md](contrib/knc-vecmath/PROVENANCE.md).
- **The GCC fork:** GPL-3.0-or-later, with the GCC Runtime Library Exception for the runtime
  libraries, as upstream GCC.

Intel and Xeon Phi are trademarks of Intel Corporation or its subsidiaries. This project is not
affiliated with Intel.
