# Review: is the 2% run-stability gate necessary for M2?

Consultant review for the lead, 2026-11-06. Inputs: ADR-0010 with amendment 1,
`docs/research/card-runs-s6.md`, `docs/research/knc-measurement.md`, every raw sample line under
`.work/_shared/tmp/claude-s6-{m2-test,slot5,placement,m2final}/`, and the literature below. No code
was changed and nothing was run on the card. Numbers come from `m2gate.py` (scratchpad), which
reparses the raw `sample` lines; they agree with the drivers' `summary` lines.

## Executive answer

**Not necessary.** The within-launch 2% spread rule is a diagnostic, not a validity condition for a
threshold decision with a 3-sigma margin. Across 12 valid L2 launches the gain fraction (GF) is
0.69-0.99 (mean 0.79, sd 0.09, threshold 0.5); the four launches the rule discards have GF 0.69,
0.77, 0.79 and 0.99, the same verdict as the eight it keeps. The rule fires on a regime step
inside the *first-timed* build (18 of 86 first-timed builds, against 4 of 94 second and 2 of 96
third), so it mostly measures the launch's start-up transient. It also did not catch the one real
invalidity found today (short batches). Discarding and rerunning a third of the launches is the
"keep running until it passes" pattern that S6-01 itself warned against.

**Recommended rule (ADR-0010 amendment 2, proposed wording in section 5):**

> A launch is valid when the correctness gate passed, every build's median timed batch is 50-200 ms,
> all pin checks passed, density is not 3, card_run reports no overlapping job or foreign workload,
> and the clock policy is identical at start and end. Group spread is reported, never a validity
> condition: a build whose five group medians spread 2% or more is flagged "regime step" with its
> chronological group medians, and the launch still counts.
>
> M2 passes when, over five valid launches at the L2 working set and production density:
> (a) the FP32 affine gain fraction is at least 0.5 in every launch (exact sign test, p = 1/32), and
> (b) the one-sided 95% lower confidence bound of the mean gain fraction over the launches,
> mean - t(0.95, 4) * sd / sqrt(5), is at least 0.5; and
> (c) T_gcc <= 1.05 * T_x87 at every tested length in every launch.
> If (a) or (b) fails while the mean is at least 0.5, five further launches are run and the rule is
> applied to all ten; otherwise M2 fails. Launches are never dropped or repeated for spread.

With today's variance that needs five launches (the block already running), not more. For tuning
tickets a different design is needed (section 6): before and after in the same launch, interleaved
by group, with an effect-size confidence interval; cross-launch comparison cannot resolve a few
percent at L2 and should not be attempted.

## 1. Literature

All papers below were read from the PDF text except where marked. Page/section references are to
the versions linked.

- **Hoefler & Belli, SC15** ([PDF](https://htor.inf.ethz.ch/publications/img/hoefler-scientific-benchmarking.pdf)).
  Twelve rules; the ones that bear on this question, verbatim: Rule 5 "Report if the measurement
  values are deterministic. For nondeterministic data, report confidence intervals of the
  measurement." Rule 6 "Do not assume normality of collected data (e.g., based on the number of
  samples) without diagnostic checking." Rule 7 "Compare nondeterministic data in a statistically
  sound way, e.g., using non-overlapping confidence intervals or ANOVA." Rule 8 "Carefully
  investigate if measures of central tendency such as mean or median are useful to report." Rule 10
  "For parallel time measurements, report all measurement, (optional) synchronization, and
  summarization techniques." Section 2.1.3 "Do not Cherry-pick": "all results are presented, even
  the ones that do not show the desired effect." They give the nonparametric CI of the median by
  ranks (n/2 -+ z * sqrt(n)/2) and note that the number of measurements can be chosen from the CI
  width ("We collected measurements until the 99% confidence interval was within 5% of our reported
  means"). **Nothing in the paper supports a fixed spread cut-off that invalidates a run**; the
  instrument it prescribes is a CI around the reported statistic, plus full reporting.
- **Kalibera & Jones, ISMM 2013** ([Kent AAM](https://kar.kent.ac.uk/33611/45/p63-kaliber.pdf)) and
  **"Quantifying Performance Changes with Effect Size Confidence Intervals"** (Kent TR 4-12,
  [arXiv 2007.10899](https://arxiv.org/abs/2007.10899); read in part). Three points. (i) "repetition
  is most needed where most non-determinism occurs in the experiment": estimate the variance at each
  level (compile, execution, iteration) from an initial experiment and put repetitions at the level
  that dominates; "Adding repetition at the highest level will always increase the precision". (ii)
  Measurements are only usable once the run reaches an "independent state" (i.i.d. iterations); an
  "initialised" state is the lower bar; "If measurements are not i.i.d., the variance and confidence
  interval estimates will be biased." The warm-up length is established per platform by inspection,
  not by rerunning until a window looks stable. (iii) The TR argues that significance tests and
  CI-overlap "visual tests" do "not tell us what we want to know"; report an effect-size CI for the
  ratio of means, bootstrap or parametric, and compare it against "the minimal/maximal change that
  is important to us." That is exactly M2's situation: the threshold 0.5 is a practical effect size.
- **Georges, Buytaert & Eeckhout, OOPSLA 2007** ([PDF](https://dri.es/files/oopsla07-georges.pdf)).
  "prevalent methodologies can be misleading"; best-of-N hides variation; report means with 95% CIs
  over many VM invocations (their examples use 30), decide by non-overlapping CIs or ANOVA (Tukey
  HSD for pairs). JavaStats stops "as soon as the desired confidence interval width is achieved" (2%
  in Figure 17). Again the stopping variable is CI width, not a pass/fail spread on one run.
- **Mytkowicz, Diwan, Hauswirth & Sweeney, ASPLOS 2009**
  ([PDF](https://huang.isis.vanderbilt.edu/cs8395/readings/producing-wrong-data.pdf)). Environment
  size and link order moved SPEC results by amounts comparable to -O3 vs -O2 (median bias about 10%
  by Kalibera & Jones' citation of them). Remedies: "setup randomization" (many layouts, treat
  layout as a random factor) and "causal analysis". Relevant here because physical-page placement is
  this card's analogue of their layout bias: it is a *factor* to randomise over and average, not
  noise to filter out. Section 8 ("A Call to Action") was seen only by heading.
- **Curtsinger & Berger, STABILIZER, ASPLOS 2013**
  ([PDF](https://people.cs.umass.edu/~emery/pubs/stabilizer-asplos13.pdf)). Re-randomising code,
  stack and heap layout every 500 ms makes layout effects sum to a Gaussian (CLT, "30 is typical"),
  so t-test/ANOVA apply; with that, "-O3 over -O2 optimizations is indistinguishable from random
  noise" on SPEC CPU2006. The lesson for us: once placement is randomised *across launches*, launch
  means are the right unit for a parametric interval, and 5-10 launches with a 3-sigma margin are
  plenty; without randomisation, a single launch's within-run precision says nothing about the
  population.
- **Abedi & Brecht, ICPE 2017, Randomized Multiple Interleaved Trials**
  ([PDF](https://research.spec.org/icpe_proceedings/2017/proceedings/p287.pdf)). Running all trials
  of A then all of B ("multiple consecutive trials") "falsely reports a difference of up to 37.8% as
  being statistically significant ... for two identical alternatives"; interleaving alternatives in
  rounds, with a fresh random order per round ("a randomized block design ... where the blocks are
  intervals of time"), removes that. Our drivers time build A for all five groups, then B, then C:
  a consecutive design, and the flagged runs show the cost (a step during A only).
- **Bulej, Horký, Tůma, Farquet & Prokopec, ICPE 2020, Duet benchmarking**
  ([arXiv 2001.05811](https://arxiv.org/abs/2001.05811)). Running both versions simultaneously and
  pairing samples narrows 99% CIs by 5.03x (ScalaBench) and 37.4x (SPEC CPU 2017) on public clouds;
  shuffling the pairs removes the gain, so the benefit is from shared interference. Pairing within a
  launch is what the gain fraction already does for placement; interleaving by group would extend it
  to transients.
- **Maricq, Duplyakin et al., OSDI 2018, "Taming Performance Variability"**
  ([PDF](https://www.usenix.net/system/files/osdi18-maricq.pdf)). 900k measurements on 835 servers:
  distributions are mostly non-normal and often non-stationary; "Use nonparametric confidence
  intervals to avoid assumptions of normality"; "Perform enough repetitions to achieve tight
  confidence intervals"; CONFIRM estimates the repetitions for a target CI width (about 10 at CoV
  0.3%, up to 240 at CoV 9%). The 2020 follow-up on changepoints ("In Datacenter Performance, The
  Only Constant Is Change", CCGrid 2020) was **not read**; by abstract it detects regime changes
  over months, which is the right framing for the steps we see, at a different timescale.
- **Laaber, Scheuner & Leitner, EMSE 2019** (cloud microbenchmarks; **abstract only**): with
  randomised interleaved trials on the same instances, slowdowns of 10% or less are detectable using
  Wilcoxon rank-sum or overlapping bootstrap CIs. Consistent with the above; not independently
  verified here.

Summary of what the field prescribes: randomise or pair the nuisance factor, repeat at the level
where the variance is, report a CI (nonparametric unless normality is checked) around the decision
statistic, compare it to the practical threshold, and report everything. None of the sources uses a
"spread under X% or the run is invalid" acceptance rule. The closest relatives are warm-up detection
(Kalibera & Jones; Georges' steady-state window) and procurement-style variance bounds Hoefler & Belli
mention as a vendor deliverable, neither of which discards data from a comparison.

## 2. What the data say

Twelve sized-valid L2 launches (length 4096 per worker, 60 x 4) exist, from four drivers builds that
differ only in sizing and placement. Two more (slot5 launch 1 of each) are short-batch and excluded;
placement launches 4 and 5 were refused by the driver.

| Launch (file) | Order | x87 | GCC | IMCI | spread x87 / GCC / IMCI | GF | GCC/x87 |
|---|---|---|---|---|---|---|---|
| m2-test l2-1 | gcc,x87,imci | 0.1375 | 0.01382 | 0.01123 | 0.4 / 0.3 / 0.4% | 0.80 | 0.100 |
| slot5 ws-L2-2 | imci,x87,gcc | 0.1380 | 0.01671 | 0.01200 | 0.6 / 1.7 / 0.1% | 0.69 | 0.121 |
| slot5 ws-L2-3 | gcc,x87,imci | 0.1376 | 0.01534 | 0.01209 | 0.5 / **11.2** / 0.1% | 0.77 | 0.111 |
| slot5 len-4096-2 | imci,x87,gcc | 0.1377 | 0.01692 | 0.01399 | 0.6 / 0.1 / 0.4% | 0.81 | 0.123 |
| slot5 len-4096-3 | gcc,x87,imci | 0.1378 | 0.01467 | 0.01328 | 0.7 / 0.8 / 0.7% | 0.90 | 0.106 |
| placement 4096-1 | gcc,x87,imci | 0.1375 | 0.01478 | 0.01121 | 0.6 / 0.3 / 0.3% | 0.74 | 0.107 |
| placement 4096-2 | imci,x87,gcc | 0.1382 | 0.01383 | 0.01373 | 0.8 / 0.2 / **18.4**% | 0.99 | 0.100 |
| placement 4096-3 | gcc,x87,imci | 0.1370 | 0.01656 | 0.01192 | 0.8 / 0.3 / 0.4% | 0.69 | 0.121 |
| final ws-L2-1 | gcc,x87,imci | 0.1383 | 0.01708 | 0.01391 | 0.5 / **2.5** / **2.6**% | 0.79 | 0.124 |
| final ws-L2-2 | imci,x87,gcc | 0.1375 | 0.01372 | 0.01121 | 1.3 / 0.2 / 0.5% | 0.80 | 0.100 |
| final len-4096-1 | gcc,x87,imci | 0.1377 | 0.01565 | 0.01121 | 0.6 / **12.9** / 0.3% | 0.69 | 0.114 |
| final len-4096-2 | imci,x87,gcc | 0.1369 | 0.01381 | 0.01135 | 1.4 / 0.2 / 0.1% | 0.81 | 0.101 |

ns per element; GF = gain fraction; bold = fails the 2% rule.

Findings:

1. **The flagged launches carry the same verdict.** GF of the 8 clean launches: mean 0.78, sd 0.07,
   min 0.69. GF of the 4 flagged: 0.77, 0.99, 0.79, 0.69. All 12: mean 0.79, sd 0.088, min 0.69;
   GCC/x87 0.100-0.124 against a limit of 1.05. Bootstrap 95% CI of the median GF over all 12:
   [0.72, 0.81]. Dropping the flagged launches moves the mean by 0.01.
2. **The spread rule fires on the first-timed build.** Over all 86 sized launches today (all lengths,
   both core counts): first-timed build >= 2% in 18 of 86, second in 4 of 94, third in 2 of 96. The
   chronological group medians of every flagged L2 build show a *step*, not scatter: e.g. final
   len-4096-1 GCC 0.01565, 0.01572, 0.01572, 0.01371, 0.01374; placement 4096-2 IMCI 0.01376,
   0.01375, 0.01373, 0.01125, 0.01124. In the three large cases the step is 10-22%, lands between
   groups 2 and 3 (groups are 24 batches of about 100 ms, so 6-8 s into that build's timing, right
   after the launch's first touch and pilot), goes from a slow to a fast state, and the states
   coincide with the discrete levels seen *between* launches (GCC 0.0137-0.0138, 0.0147-0.0148,
   0.0153-0.0157, 0.0166-0.0171). The fourth case (final ws-L2-1) is a 2.5% step the other way in
   both vector builds. So the within-launch failures and the 18-21% cross-launch variation are one
   phenomenon, a set of placement states, one of which can change early in a launch. The mechanism
   is the other subagent's question; for the gate it is enough that the median of five group medians
   lands on one state or the other and that GF is 0.69-0.99 in either.
3. **x87 looks clean partly because it is never first.** `timing.c:216` uses
   `current_build = launch%2 ? order : 2-order` over {gcc, x87, imci}, so x87 is always timed second.
   Its four flags (2.1-4.0%) are all at the memory working set. Any "x87 is stable" inference is
   confounded with order; a full rotation (each build first in some launch) would remove that.
4. **Variance lives at the launch level.** For ln T over the 12 launches: within-launch group sd
   0.3% (clean launches) for all three builds; between-launch sd of launch means 0.3% for x87,
   9.2% for GCC, 8.5% for IMCI. By Kalibera & Jones' rule, more groups buy nothing; more launches
   buy precision; and the gain fraction removes most of the between-launch variance because the two
   vector builds move together (per-launch GF sd 0.088 against 9% on each time).
5. **Within-group samples are heavy-tailed**: |sample/group median - 1| has 99th percentile 5-9% and
   maximum 17-35%. Medians of groups remain the right robust statistic; nothing here argues for means
   of raw samples.
6. **The rule did not catch the real invalidity.** Two short-batch runs (4.4 ms samples) passed it
   (`card-runs-s6.md`); the batch-size check added today is what catches that. S6-01's own note
   warns "do not keep adding groups until a pass or select only the fast regime".

What a 2% spread rule protects against, in principle: a launch whose single figure is not
representative because the run was unsettled or bimodal. For M2 that protection is moot (the
statistic is robust to which state the launch sits in) and the cost is a third of the launches, with
reruns that are a selection on an outcome correlated with the measured build. For density 3 (two
regimes 11% apart over the whole run) the rule was the right detector, and that use survives as a
flag plus the existing exclusion of density 3.

Statistical cost of "every launch must pass": none. Five of five launches above 0.5 is an exact
binomial sign test (p = 1/32 = 0.031 under a true median GF of 0.5), nonparametric, immune to the
discrete states. Its weakness is near the threshold: with true mean 0.6 and sd 0.09 it fails about
half the time by chance, which is why clause (b) and the sequential extension are added. The t-bound
with n = 5, t(0.95, 4) = 2.13: lower bound = mean - 0.084 at sd 0.088; today's mean 0.79 gives 0.71.
Three launches would also clear the bound (0.64) but give only p = 1/8 for the sign test, so five is
the minimum that satisfies both clauses.

## 3. Assessment of the gate

- **Right error, wrong tool.** Non-stationarity inside a launch is real and worth detecting, but the
  remedies in the literature are warm-up detection and interleaving, and the reporting remedy is a
  flag. An invalidity rule converts a diagnostic into a selection.
- **Too strict for M2, too loose for tuning.** M2 has a 3-sigma margin in GF and a 10x margin in
  GCC/x87; a spread rule adds nothing. A tuning ticket claiming 3% needs paired precision that no
  per-launch spread rule provides (section 6).
- **Measures the wrong thing.** It fires on order position, not on the build; the same binary is
  "unstable" when first and "stable" when third.
- **"Every launch must pass" is fine as a sign test**, as long as launches are not discarded first.
  Keep it, but add the confidence bound so a near-threshold result triggers more data instead of a
  coin flip, and make the number of launches fixed in advance (five, then ten) to prevent optional
  stopping.

## 4. Numbers the rule needs

- Five launches per configuration, as now. Expected lower bound with today's variance: about 0.70.
- Sequential extension to ten launches at most; ten of ten above 0.5 gives p = 0.001, and the t-bound
  at n = 10 is mean - 0.051 at sd 0.088.
- No change to groups (5 x 21) or batch size (50-200 ms, 100 ms target).
- Report per configuration: five launch values and their range, min, the t lower bound, the
  bootstrap percentile CI of the median (10,000 resamples, informational), and the count of
  regime-step flags with the build and position.

## 5. Proposed ADR-0010 wording (amendment 2)

> **Amendment 2 (date): spread is a flag, decisions use confidence bounds.**
>
> **Why.** The within-launch 2% rule (point 4) fired in 23 of 86 sized launches on 2026-11-06, in 18
> cases on the build timed first, on a 10-22% step between placement states that also explains the
> cross-launch range. The discarded launches gave the same M2 verdict as the kept ones. Discarding
> and rerunning launches on that criterion is a selection on an outcome, which the benchmarking
> literature (Hoefler & Belli 2015 rules 5-7; Kalibera & Jones 2013; Abedi & Brecht 2017) replaces
> with full reporting, repetition at the level where variance lives, and confidence intervals around
> the decision statistic. See `docs/research/m2-gate-review.md`.
>
> **Changes.**
> 1. Point 4, validity: a launch is valid when the correctness gate passed before timing, every
>    build's median timed batch is 50-200 ms, every worker's pin check passed, density is not 3,
>    card_run reports no overlapping job and no foreign workload, and the clock policy records are
>    identical at start and end. Nothing else invalidates a launch. Every sample is kept.
> 2. Point 4, reporting: for each build the five group medians are printed in chronological order
>    with their spread; a spread of 2% or more is reported as a **regime step** flag with the build,
>    its position in the launch order and the step size. Flags are counted per block and reported
>    with the result. A flagged launch counts like any other.
> 3. Point 6, M2 decision, at the L2 working set and production density over five valid launches:
>    (a) the FP32 affine gain fraction is at least 0.5 in every launch; (b) the one-sided 95% lower
>    confidence bound of the mean gain fraction, mean - t(0.95, n-1) * sd / sqrt(n), is at least
>    0.5; (c) T_gcc <= 1.05 * T_x87 at every tested length in every launch. If (a) or (b) fails
>    while the mean is at least 0.5, exactly five more launches are run and the three clauses are
>    applied to all ten; otherwise M2 fails. Launches are never repeated or dropped for spread, and
>    the number of launches is fixed before the block starts.
> 4. Point 6, reporting: with each M2 figure, the five (or ten) launch values, their range, the
>    minimum, the lower bound in (b), a bootstrap percentile 95% interval of the median gain
>    fraction, and the regime-step count.
> 5. Build order: rotated so that each build is timed first in at least one launch of five (the
>    present alternation never times x87 first). If the driver is changed to interleave builds by
>    group (one group of each build per round, order drawn per round), the gain fraction is also
>    computed per round and the per-round values are reported; this is the design the tuning rule
>    in point 7 requires.
> 6. Amendment 1's items 1, 2 and 5 stand; its items 3 and 4 are replaced by the above.

## 6. Tuning tickets (new point 7 for ADR-0010)

A tuning ticket claims a change of a few percent in one build, which M2's statistic cannot resolve:
between-launch sd of GCC time at L2 is about 9%, so an unpaired before/after across launches would
need roughly 2 * (1.96 * 9 / 3)^2, about 70 launches per arm, for a +-3% interval. Within a launch
the group sd is 0.3%. So the design must pair before and after inside a launch:

> **Point 7, tuning evidence.** Before and after are two GCC-KNC builds of the same kernel in the
> same process, on the same buffers, timed in interleaved rounds (one group of each per round,
> order drawn per round, five rounds or more), in at least three launches so that at least two
> placement states are seen. The statistic is the per-round ratio T_after / T_before; the figure is
> the median ratio with a bootstrap percentile 95% interval over all rounds of all launches
> (Kalibera & Jones' effect-size interval). A change is accepted when the interval excludes 1 and
> its near end is beyond the ticket's stated minimum effect, at every working set the ticket names.
> A result whose sign differs between launches is reported as placement-dependent, not accepted.
> Per Mytkowicz et al., code layout differs between the two binaries; a claimed effect under 2% is
> additionally checked with the two builds linked in the opposite order.

This needs a fixture change (two GCC builds in one binary and per-round interleaving), to be
written as a ticket and coordinated with the driver work in progress; no tuning result should be
quoted under the current three-build consecutive design beyond "same state as M2".

## 7. Risks and guards

- **Hiding a real regression.** A regime step could mask a slowdown in the first-timed build.
  Guards: (c) stays an every-launch rule at every length; the flag and the chronological group
  medians are always printed; order rotation puts every build first in some launch; the lower
  bound in (b) uses the launch values as they are, including any slow state.
- **Cherry-picking or optional stopping.** Guards: launches are never dropped for spread; the count
  (five, then ten) is fixed before the block; every launch value is reported with the figure; the
  sequential step runs exactly once; the rule is written in the ADR before the data are seen.
- **Non-normal launch values** (discrete states). The t-bound is approximate at n = 5; the sign
  clause (a) is exact and does not depend on the distribution, and the bootstrap interval is
  reported alongside. With a 3-sigma margin the approximation cannot change the verdict; near the
  threshold the sequential step supplies more launches.
- **A worse card state later** (another project resident, thermal, firmware). Guards: card_run's
  exclusivity and foreign-workload checks are validity conditions; the clock-policy comparison stays;
  x87 is a per-launch control whose cross-launch sd is 0.3%, so an x87 move over 2% between
  launches is reported as a card-state change and the block is repeated in full, not patched.
- **Tuning claims from M2-style data.** Guard: point 7 forbids it; a tuning ticket without the
  paired fixture reports direction only.
- **The flag loses its teeth.** A build flagged in most launches of a block (as density 3 was in
  S6-01) still deserves a diagnosis before its numbers are quoted in a tuning claim; the ADR keeps
  the density-3 exclusion and the flag count makes a persistent case visible.
