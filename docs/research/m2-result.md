# Milestone M2 result: useful vector target

**Decision:** M2 passes. Accepted 2026-11-07 by the lead under the owner's pre-approval ("You have my
pre-approval of conclude sprint 6 and start sprint 7 if result is expected").

**Compiler:** GCC `knc` `57bec527e002` (Sprint 6 head: S6-05 cost model, S6-06 scheduler).
**Rule:** ADR-0010 with amendments 1 and 2 (five launches; the gain fraction at least 0.5 in every
launch and its one-sided 95% lower bound at least 0.5; GCC-KNC at most 1.05 x x87 at every length in
every launch; spread is a flag, validity is mechanical).
**Data:** `.work/_shared/tmp/claude-s6-m2s6final/` (binary `.work/_shared/M2-s6final`, kernels compiled
at the head, interleaved paired fixture of S6-15), 150 `--benchmark` jobs on 2026-11-07
(15:00-18:00Z, paused 16:31-16:40Z for a WRF screen), all valid; `decide.py` output in
`decide-c60.json`.

| Condition (FP32 affine, 60 cores x 4 threads) | Result | Required |
|---|---|---|
| Gain fraction at L2, per launch | 0.761, 0.818, 0.739, 0.731, 0.784 | each at least 0.5 |
| One-sided 95% lower bound of the mean (mean 0.767) | 0.733 | at least 0.5 |
| Worst GCC-KNC / x87 time over 12 lengths and 3 working sets, all launches | 0.627 (60 cores), 0.608 (1 core) | at most 1.05 |

Regime-step flags: 8 of 225 build measurements (reported, not discarding). At 1 core the L2 gain
fraction is 0.811-0.812 in all five launches. The pre-tuning baseline (`claude-s6-m2base2`, GCC after
S6-11) also passed: lower bound 0.752, worst 0.625.

**Context:** card power is the same for every build (about 164-172 W), so GCC-KNC uses about 8.7x less
energy per element than x87 at L2 (S6-13). Other M2 kernels at L2 (S6-05/S6-06 paired runs): stencils
reach 81-87% of the hand-written IMCI gain, FP64 affine 71-76%, mat16 about 26%, mat8 about 2%.

**Known weak spots (proposed Sprint 8 block, `docs/BACKLOG.md`):** odd short lengths fall back to x87
tails (E4-04), small matrices (mat8, made 10% slower by S6-06), the per-loop cost trade-off (E5-11),
no software prefetch yet (E5-07), and the checks C1-C10 of `docs/research/knc-optimization-sources.md`.

**Not established:** whether the early slow regime that the interleaved fixture absorbs comes from
OS activity or a per-core hardware effect (`docs/research/m2-noise-diagnosis.md`).
