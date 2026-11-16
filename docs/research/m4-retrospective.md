# M4 retrospective: spend less time recovering, close the evidence loop

S13-03, 2026-11-16. Review of Sprint 11-13 ticket notes and every row of
[practice-lessons](practice-lessons.md), after the M4 decision. This is a
research deliverable for the lead: proposed tool, template, rule and skill
changes below have not been applied by this ticket.

M4 produced a useful compiler and a credible, qualified result. The
[accepted result](m4-result.md) reports a 2.194x median speedup and 2.162x
one-sided lower bound across 17 programs on the full 7120 profile. Every
scored launch passed correctness and six checker families rejected corruption.
The owner accepted held-out bzip2's 0.927x as a reviewed known limit for the
next milestone; the target of beating GCC 5.1.1 on every program was not met.
The owner cancelled the smaller-profile gate blocks and optional panels.
Those results remain unrun, rather than being inferred from the full profile.

Our most avoidable cost was reaching the final gate before its execution
pipeline was ready. Next came repeated environment and submission failures
that consumed whole engineer sessions. Some research correctly ended without
a compiler change: stopping an unsupported optimization was a useful result.

## Evidence and limits of this review

The local record contains 77 ticket files: S11-01..29, S12-01..42 and
S13-01..06. Screening their dated notes finds 170 engineer `ask` entries,
23 lead `changes` entries, 42 budget-escalation entries and 40 budget-raise
decision entries. These are counts of recorded lines, not distinct failures,
review rounds, engineer hours or actual token spend. Questions include proper
card/build handoffs and deliberate proof gates. S12-09 repeats a budget
escalation; S11-15 records session and token decisions for the same extension.
Draft tickets without execution notes contribute no execution evidence.

The ranking below is qualitative. Ticket notes record long outages and
repeated work but do not provide a comparable accounting of all engineer and
card hours. No total hours saved, return-on-investment percentage or new
native performance result is claimed. Links to tickets identify the dated
record; their recommendations are distinguished from deployed fixes.

## Where time bought the least result

| Priority | Evidence and cost | What the work actually established | Change in practice |
| --- | --- | --- | --- |
| 1 | [S13-01](../../work/tickets/S13-01.md), Nov 15 recovery notes: the first block had false overlap/watchdog alarms; codecs then failed collection; a session exit broke SSH after launch 105; DMA cleanup failed under a concurrent host build. Four abandoned block attempts are reported in the result. | These were infrastructure failures, not compiler regressions. Eventually 106 timed launches were adopted and 104 unfinished launches resumed. Repeating an entire block was unnecessary once valid captures could be recovered under the amended protocol. | Rehearse the complete launch/collect/score path before a long reservation; detach the runner, keep the host quiet and use the approved recovery policy (P1/P2 below). |
| 2 | [S11-02](../../work/tickets/S11-02.md): four recorded review rounds; session limits rose 6 to 9 to 12 to 14 and input budget 12M to 18M. Host fakes missed driver offsets above 2^62, publication modes and generated-script line endings. | DMA eventually passed native acceptance and improved large-file transfer, so the feature was worthwhile. Its rollout and recovery burden made it a poor default for the final timed gate, which moved to SSH-only transfers. | Test at the C/transport boundary that can fail; keep transfer qualification separate from compute qualification. Preserve the measured DMA benefit without making every timed launch depend on it (P1/P3). |
| 3 | [S12-04](../../work/tickets/S12-04.md) and [S12-17](../../work/tickets/S12-17.md): small harness fixes needed repeated session extensions, launcher repairs and red-history repairs; the lead finished submissions. S12-21/23/30 repeatedly hit lead-owned shared outputs; many tickets could not rebase. | Much of this produced no new compiler or card evidence. S12-28, S12-33/37 and S12-39 subsequently removed recurring causes. | Carry these fixes into the next milestone before opening more lanes; preflight the actual engineer environment and prepare permitted integration/submit paths (P3). |
| 4 | [S12-30](../../work/tickets/S12-30.md): repeated red reviews, scanner repairs, missing C++/OpenMP headers, five recorded budget escalations and a whole-file CRLF rewrite caught by the lead. [S12-19](../../work/tickets/S12-19.md) initially resolved none of 15,109 samples; final coverage was 11.35%. | Hand-written profitable sparse code and synthetic source joins did not establish that the compiler could recognize and legally emit the application form. Partial profile attribution remained partial. | Require one real application-shaped, end-to-end proof before extending a heuristic or building its reporting machinery. Budget prototype/scanner repair separately; preserve explicit coverage limits (P4). |
| 5 | [S11-21](../../work/tickets/S11-21.md): session limit rose 6 to 10 to 14 to 17 amid incomplete exports, CRLF, mixed host tools and target build failures. [S12-35](../../work/tickets/S12-35.md) encountered missing link inputs and incompatible Fortran module versions. | WRF became a valuable compiler stress workload and exposed real ICEs. Much setup cost was portability/integration work rather than optimization evidence. | Separate provisioning/build readiness from performance tickets; specify the host tools, target prefix, modules and link inputs before dispatch (P3/P4). |

There was also repeated administrative cost at submission. S11-01/05/11/18,
S12-01/02/10/12/15/19/37/39 and S13-05/06 needed size or test-budget decisions.
Required benchmark sources, research data and baseline records were often
counted as excess tests. This argues for correctly scoped budgets at ticket
creation, not removing the controls that catch overscope. S13-06's very large
generated-data diff is also a reason to ask what small durable example proves
the deliverable before admitting generated output to Git.

## Rules and tools that paid off

* **Frozen scoring and independent checks.** S11-14 separated the primary
  decision from optional modes and kept the held-out result visible. S13-01
  exposed missing independent PolyBench/STREAM references before scoring.
  The final result discloses bzip2 and the owner's reduced profile scope.
  Keep this discipline; implement readiness checks earlier, rather than
  negotiating them during the final card reservation.
* **Proof before implementation.** S12-06's static argument and 37-second
  card diagnostic found no compiler-removable scalar cost. S12-08 found no
  proven hot spill removal. S12-07 stopped when its gain premise was unproven.
  A research/no-change closure avoided turning those observations into
  speculative backend changes. These are successful stops, not wasted tickets.
* **Independent numerical recheck and valid timing.** The screen's reported
  3.87M ULP pow error became 0.503 ULP under exact host recheck. S12-18 repaired
  batch calibration and obtained valid native exp/log/pow results instead of
  changing the library to chase invalid timings. Keep both validation paths.
* **Red tests and focused review.** S11-27 exposed scratch-lifetime wrong
  code; S12-29 exposed an alignment fault and then a reload problem. Reviews
  caught tests committed together with their fixes in S11-08, S12-04/17/33,
  and caught stale card consumers after S12-37 moved outputs. A red test must
  fail for the specified behavior; a failing fixture or impossible scanner
  predicate is not that proof. Commit the test before editing the fix when
  the commit tool stages the whole worktree.
* **Shared-resource ownership in tools.** S12-28's lane lock prevents two
  dispatchers from assigning one ticket. S12-33/37 isolate test outputs and
  provide explicit card staging. S12-39 moves integration to the authorized
  lead path and aborts conflicting merges cleanly. These remove repeated
  recovery work more reliably than asking engineers to remember exceptions.
* **Bounded checks and explicit handoff.** `tools/run.py` provides short
  output, retained log paths and repeat suppression. Batch tickets collect
  broad compiler checks; engineer staging and lead card execution keep card
  ownership explicit. Keep the distinction between host pass, staged binary,
  valid native answer and valid native timing all the way through closure.

## What the research changed about how we should work

| Input reviewed | Useful integration | Next-milestone consequence |
| --- | --- | --- |
| S12-10 [reference gaps](knc-reference-gaps.md), corrections and residual experiment table | Existing features and stale notes must be checked before proposing work. Documents can constrain a mechanism without proving its benefit on the installed system. | Select the cheapest discriminating experiment for an exposed cost; reuse earlier measurements and identify the exact remaining uncertainty. Do not add overlapping gain estimates. |
| S12-13 [digest](knc-digest-2026-11.md) and S12-14 [42-row audit](s12-14-model-audit.md) | Separate wording corrections, changes needing measurement, and settings to retain. Source revision, installed binary and deployed runtime are separate evidence. The R09 review round demonstrated that even a digest can misread a table's version columns. | Each accepted row needs a destination ticket or explicit defer/reject reason. Keep R-number, edition/page, hardware applicability and verified/reported/inference labels; review original pages for consequential claims. |
| S12-15 [literature survey](phi-literature-survey.md), fourteen proposed follow-ups | It supplied mechanisms beyond the original themes: indirect prefetch, region-dependent density, profile triage and explicit vector-math contracts. Whole solves, conversion/setup and runtime overhead matter as much as a kernel. | Admit one bounded mechanism proof per proposal. Do not import a historical headline speedup or claim current KNC support from a later platform. Leave OS/library redesign to its own scoped work. |
| S12-16 [system playbook](system-tuning-playbook.md), card-practice consequences and measurement plan | Verify the active path, actual placement/pages, complete-workload objective and rollback before changing a default. Capacity profiles are constrained runs, not native qualification of other models. | Record environment and host interference at the measurement boundary; compare one setting at a time when a symptom warrants it. Keep machine changes out of a compiler gate. |

This ticket introduces no new hardware facts or replacement tuning constants.
The research documents retain their own R-number/page and applicability
qualifications. Their proposed experiments are not counted here as completed
native tests. The model-first workflow delivered by S13-05 and evaluated by
S13-06 should remain a proof aid: label predictions and unsupported forms;
do not use close predicted rankings as a substitute for card evidence.

## Disposition of every practice-lessons row

Row numbers below follow the living table's order on 2026-11-16, identified
also by subject so later insertion does not change their meaning. A completed
follow-up can supersede a stale `open` label; it does not prove every native
acceptance item or broader practice is closed. No living-table edits are made
by this ticket.

| Row / subject | Evidence reviewed and disposition for the lead |
| --- | --- |
| 1. Stale hardware notes and unidentified editions | Retain the closed citation rule and S12-13 reference index. S12-13's R09 correction shows why original-page review and applicability labels still matter. Carry into P4/P6. |
| 2. Research without integration | Still a process gap. S12-13/14 produced accepted audit rows and follow-up tickets, but template wording remains open in the table. P6 supplies a concrete closure rule. |
| 3. RLIMIT_AS dependency and BusyBox sleep | S12-17 fixed explicit-limit execute startup; S12-04 fixed waits/scanning. Their approval notes still handed native checks to the next window. Keep the proposed 1-2 minute card smoke requirement open until encoded and exercised; P1/P3. |
| 4. Invalid vmath batches and staging treated as completion | S12-18 records valid native runs for full/3100/5100 and closes that incident. The general staging-to-valid-run rule remains needed in P5. Later one-thread-per-core log limits in the M4 result are separate scope. |
| 5. Pow screen reference wrong near hard cases | Retain the existing exact recheck and its batch-summary requirement. A screen result alone does not authorize a numerical change; P4/P5. |
| 6. S12-06 proof-first stop | Retain the phase-1 gate and research/no-change outcome. Extend its template to require removable-time evidence and a legal emitted form; P4. |
| 7. Duplicate lane dispatcher | Table says open; S12-28 approved a per-lane live-process lock on Nov 14, including dead-holder recovery tests. Reconcile the row as implemented; retain the lock in P3. |
| 8. Small fixes exhausted sessions mid-submit | S12-04/17 notes confirm lead-completed submissions after extensions. Not solved by larger budgets alone. P3 makes environment and integration readiness a shared prerequisite and leaves a friction allowance. |
| 9. Lead-owned T2 files | Table's cleanup workaround is superseded for checks by S12-33 and S12-37 approval: outputs go under `runner.out`, with explicit export for card consumers. Record implemented scope; native staging still needs its own validation. P3/P5. |
| 10. Shared T1 dict conflicts and failed approve merges | S12-39 implements clean integration/conflict abort and notes overlap with draft S12-03. A separate per-ticket T1 registry is not established by that fix. Keep registry contention as remaining work under P3. |
| 11. CRLF whole-file GCC rewrites | Lead repaired S12-30; no completed commit guard is recorded in these ticket notes. Keep open: add LF regression prevention and whitespace reporting to `pm.py commit` before next compiler work; P3. |
| 12. Engineer rebase metadata denied | Closed by S12-39: status-only divergence is allowed, real missing changes still require integration, approve merges/aborts. Update conflicting engineer instructions rather than repeating unauthorized rebases; P3. |
| 13. Check tickets required fabricated red | Retain `type: check` for batch checks and `research` for proof-only/no-change work. Dispatch must validate type against deliverable; P3/P4. |
| 14. FIFO gate cut an open turn | Living row records PhiWeather gate support and 5/5 replay checks, so retain its closed status. S12-36's earlier one-sided fix alone was insufficient. P2 covers the remaining end-to-end lease lifecycle. |
| 15. Four final-gate block losses | ADR-0015 amendment 1 and S13-01 implement SSH-only timed staging, bounded untimed retry and adopt/resume; detached execution also became practice. Retain the fixes, add mandatory rehearsal and supervised execution in P1/P2. |
| 16. Host build load broke transport | Lead rule exists; AGENTS/card-run documentation remains open in the table. P1 makes quiet-host ownership and begin/end coordination a written operator precondition. |
| 17. 3.5-hour estimate versus roughly six-hour block | Open. The S13-01 engineer had already warned 5-7 hours/profile. Generate duration from the frozen plan and measured complete-launch costs; show remaining-time updates (P2). |
| 18. Lead patched instead of maintaining overview/status | Retain the closed lead-delegation rule recorded in the table. P2 requires a watcher and status before recovery. Transfer this lead-only responsibility into the agent-team skill; it does not authorize engineers to take card turns. |
| 19. Window 10 queue refresh and self-matching wait | Open: table records loss of queue order followed by a self-matching process-name wait and 4.7 hours lost. Preserve original queued time; wait on a ledger/PID state, emit heartbeat and alarm on stalled progress (P2). The S14-22 pointer is recorded here without reviewing another sprint's ticket. |

## Six changes to carry into the next milestone

The lead owns adoption, protected-file changes and the user-level agent-team
skill update. Each item names an enforceable destination and a small closure
check. These are proposed follow-ups, not claims of changes already shipped.

| ID / order | Practice and durable destination | Completion evidence |
| --- | --- | --- |
| P1. Before the next long card block | Add a readiness step to `tools/m4_gate.py` or its successor and the card-run operator template; write the matching AGENTS.md rule. Run 2-3 short launches through the actual detached launcher, transfer, environment capture, codec/multiple-process collection, independent checker and scorer paths. Cover each changed path across that rehearsal and the 1-2 minute harness smoke. Require clean stderr, provisioned sealing and a quiet host; coordinate begin/end with the other card/host users through the lead. Retain ADR-0015's SSH-only timed path and explicit retry/adoption policy. | A lead-recorded rehearsal produces accepted records and a score before the long reservation begins. Deliberately stop an untimed host fixture and show recovery cannot silently rerun observed timing. Native smoke is pending until the lead runs it. |
| P2. Before reserving a multi-hour turn | Put reservation/refresh/wait/detach/heartbeat behavior in one card-script helper, not ad hoc PowerShell. Preserve queue admission time on renewal, wait by ledger or known PID, close in a finalization path, and alarm when progress exceeds the expected job duration. Generate time estimates from plan counts and observed full-launch durations, including transfers, checks and controls. Add handback deadline and remaining-work reporting to the operator template and agent-team lead checklist. | Host lifecycle checks exercise renew, checker self-match avoidance, stalled runner and cleanup; the next coordinated short turn confirms both projects honor the reservation. The lead can see progress and deadline without becoming the runner's parent session. |
| P3. Before dispatching parallel work | Extend `dispatch.py`/`pm.py` preflight and ticket template: real acceptance, correct type/lane, actual option names, available host interpreter/dependencies, installed prefix/header paths, authorized build/integration route and scoped budgets. Preserve S12-28/33/37/39. Add the LF guard to `pm.py commit`; propose per-ticket T1 registration as a separate small change. Reconcile AGENTS.md's rebase instruction with S12-39. | One light ticket reaches submit in the engineer sandbox using canonical commands without an environment waiver; an LF fixture is refused before a whole-file rewrite is committed. Existing lock/output/integration acceptance stands; do not rerun it merely for the retrospective. |
| P4. At optimization/research admission | Extend the ticket template/model-first checklist: observed hot cost, non-overlapping removable-time bound, legal compiler-emittable application form, oracle, smallest proof, controls and stop/no-change condition. Require source index/applicability labels for hardware claims and report profile coverage/unsupported forms. Review the proposed red before fix work on deep code tickets. | One real application form passes through the recognizer and backend evidence path; the old behavior fails the red for the intended reason. If the bound or legality fails, close as research with no speculative implementation. |
| P5. At staging and batch closure | Add a compact handoff table to staging and batch-check templates: job/path, runtime prefix, command/threads/profile, owner, validity/correctness/timing state and result/log or explicit not-validated reason. List every staged timing job in the following batch check. Keep exact-screen recheck in the same result summary and preserve explicit export/import paths for native consumers. | A batch cannot silently omit a staged job: it names either a valid native result or the unresolved blocker. Infrastructure failure and host-only success cannot be reported as native pass. This is a ticket summary, not a new provenance/receipt file. |
| P6. At research review, within the sprint | Add the digest/disposition step to research templates and the user-level agent-team skill: every accepted recommendation maps to a code/runtime/practice ticket or ADR amendment with proof needed; all others get defer/reject reasons. Reconcile stale living-lesson rows against completed follow-ups. Copy the six practices and lead ownership boundaries into the skill, linking project-specific rules rather than duplicating hardware facts. | The lead records destination IDs or explicit dispositions for accepted rows, applies the protected tool/rule/template changes under separate tickets, and records the skill update location/version in its ticket response. This document alone does not close those actions. |

For the next milestone, schedule P1/P2 before consuming another long card
window and P3 before scaling engineer lanes. Apply P4/P5/P6 through ticket
creation and review immediately. Retain the frozen correctness and scoring
discipline, the ability to stop without a code change, and the distinction
between predicted, staged and measured results.
