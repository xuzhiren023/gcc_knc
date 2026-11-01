# GCC-KNC

A modern GCC toolchain for Intel Xeon Phi Knights Corner (initially the 7120P): ordinary
C, C++ and Fortran compiled to native, correct and profitable KNC programs. Compilers run on
the host. Programs run on the card.

**Status:** kickoff. Nothing is built yet. See [CURRENT_STATE.md](CURRENT_STATE.md).

| Start here | For |
|---|---|
| [Status](STATUS.md) | Where the project stands right now |
| [Kickoff](KICKOFF.md) | How to start the work, with the GPT-6.1 prompt |
| [Project plan](docs/PROJECT_PLAN.md) | Goals, roadmap, milestones, forecast, risks, owner decisions |
| [Collaboration](docs/COLLABORATION.md) | How the agents work together, and what you do |
| [Cost harness](docs/HARNESS.md) | Enforced limits on wasted credit |
| [Development cycle](docs/DEVELOPMENT_CYCLE.md) | Agile and TDD process, test tiers, review, card discipline |
| [Research review](docs/reviews/2026-11-01-research-review.md) | What the research got right, and what changes the plan |
| [Backlog](docs/BACKLOG.md), [Sprint 0](docs/sprints/SPRINT-00.md), `work/tickets/` | The work |
| [ADRs](docs/adr/) | Base, ISA and floating-point decisions |
| [Research report](GCC_KNC_TECHNICAL_RESEARCH_REPORT_20261101.md) | Background |
| [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md) | Agent rules |

No build instructions exist yet. S0-01 and S0-03 add `tools/doctor` and `tools/check`.
