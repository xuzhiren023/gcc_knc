# Moving GCC-KNC to the HP Z840 workstation

Written 2026-11-17 by the lead on the laptop, before the move. The laptop stops new host work; the Xeon Phi card moves
after the workstation is set up. Read with `docs/BUILDING.md` (Linux recipe) and `docs/handoff/NEW-LEAD-START.md`.

**Correction (later on 2026-11-17):** the workstation runs Windows with the laptop's layout
(`C:/Users/xuzhi/Documents/gcc_knc`), so the laptop's Windows/Cygwin toolchain works there unchanged. The Linux notes
below (binutils from MPSS source) apply only to a later Linux host.

## 1. Clone (lean), in this order

```sh
cd C:/Users/xuzhi/Documents
git clone https://github.com/xuzhiren023/gcc_knc.git      # ~10 MB; clone FIRST, into a folder that does not exist yet
git clone --single-branch -b knc https://github.com/xuzhiren023/gcc_16_knc.git gcc_knc/.work/_shared/gcc   # ~1.4 GB
```

Then copy from the laptop into the same paths under gcc_knc (`.work/` is git-ignored): `.work/_shared/toolchain`
(cygwin, cross, autotools, sysroot, sysroot-development), the installed prefix `.work/_shared/gcc-knc-16.2.0`,
`.work/_shared/S10-02/host/libknc_vmath.a`, `config/card.local.json`, `.work/_state/card/known_hosts`. The knc-boinc
session offered to copy these over ssh once the clone exists.
Work-in-progress branches are on GitHub too (`git fetch origin s14/S14-16` and so on); open tickets name their branch.

## 2. Unpack the laptop-only data

Copy `gcc_knc-workstation-transfer-20261117.tar` (about 440 MB, from the laptop's Documents folder) and unpack it inside
`gcc_knc/.work/_shared/`:

| Path in the archive | What it is |
| --- | --- |
| `toolchain/sysroot`, `toolchain/sysroot-development` | the card sysroot (glibc 2.21, MPSS 3.8.6 image) copied from the card |
| `corpus-build/milkyway-nbody` | MilkyWay nbody_1.96 (1e640779) plus correctness patches, branch `m5-nbody-1.96-correctness` |
| `corpus-build/milkyway-nbody-support` | config headers, patch list and core-small inputs (M5 unit, S14-56) |
| `corpus-build/wrf-miami-classic` | WRF Miami 2024-01-06 inputs in classic netCDF, with PhiWeather's README |
| `donor-libgomp` | static GCC 5.1.1 libgomp for the donor's OpenMP builds |
| `knc-twin-20261117.bundle` (archive root) | the knc-twin repository: `git clone knc-twin-20261117.bundle ~/knc/knc-twin` |

The laptop's `toolchain/cross` and `toolchain/cygwin` are Windows binaries and are not carried over. On Linux, build the
k1om binutils 2.22 (+mpss3.8.6) and, if wanted, the GCC 5.1.1 donor from Intel's MPSS 3.8.6 source as BUILDING.md 1.2
says. The donor is only needed for comparisons, not for GCC-KNC itself.

## 3. Skills

- knc-twin: `cd ~/knc/knc-twin && ` follow its INSTALL.md (installs to `~/.claude/skills/knc-twin`).
- knc-optimize: `sh ~/knc/gcc_knc/skills/knc-optimize/scripts/install.sh`.
- model-first is a project skill inside gcc_knc (`.claude/skills/model-first`), nothing to install.

## 4. What changes on Linux

- Host CPU limit: the laptop rule (leave one core free for card DMA) carries over; on the Z840 keep one core of the
  socket that hosts the card's PCIe slot free.
- `tools/card_run` and the DMA helpers were built for Windows; S13-04 adds Linux-host support for the card tools. Run a
  single smoke job before any card window after the card moves.
- Codex engineers: `harness/policy.json` `engineer_backend: codex`; the dispatcher needs the Codex CLI on the
  workstation.

## 5. State at the move

Board: `python tools/pm.py board`. Sprint 14 plan: `docs/sprints/SPRINT-14.md`. State: `CURRENT_STATE.md`.
