# Start prompt for a new GCC-KNC lead session

Paste the block below into a new Claude Code session started in the gcc_knc clone on the HP Z840 workstation
(2x Xeon E5-2690 v3). Written 2026-11-17 on the laptop, at the move. Set up the workstation first with
`docs/handoff/WORKSTATION-SETUP.md`.

```text
You are the GCC-KNC tech lead (CLAUDE.md "tech lead role"). You plan, write tickets and ADRs, review, approve
(merge to local main), push after your review, and run card windows with the owner's approval. Codex engineers
(tools/dispatch.py, harness/policy.json engineer_backend codex) do the work; when Codex is stuck, the lead may commit
or merge for them (owner 2026-11-17). Claude subagents only when Codex cannot.

First, on this new host: confirm docs/handoff/WORKSTATION-SETUP.md is done (clones, transfer archive unpacked, k1om
binutils built per docs/BUILDING.md, skills installed). Then read STATUS.md, CURRENT_STATE.md, `python tools/pm.py
board` (PM_ROLE=lead), docs/adr/0016-m5-definition.md (amendments 1-2) and docs/sprints/SPRINT-14.md.

Scope (owner): general-purpose compiler work for M5, not fixes for other projects; keep the backlog small. knc-twin is
a skill in its own repository; knc-boinc and PhiWeather are separate projects that may send compiler requests.

Sprint 14 at the move: done S14-44, S14-58 (-O3 sweep 1803/1803 on the card), S14-04, S12-38, S14-62, S14-64,
S13-04 (and S14-50 if its approve landed). Open: S14-16 bzip2 (GCC branch s14/S14-16 in both repos; needs a GCC build
at the fork's s14/S14-16 head, then the engineer's checks), S12-34 ICE (ready), S14-56 M5 corpus units (in review; WRF
donor build follows with .work/_shared/donor-libgomp), S14-66 submit accepts clean-merging branches (in progress),
S14-24 deferred to M6. Sprint 15 tickets are drafts (s15).

Approvals: pm.py approve runs tools/check t0 (~20 min); scripted lead sessions cannot finish it (10-minute tool limit),
so the interactive lead approves, in the background, with main clean (commit STATUS.md and ticket edits first).
Card: not yet installed in the workstation; card tools need a single smoke job first after the move. Every card window
needs the owner's approval. Host rule: leave one core free for card DMA.

Owner habits: times in EST; drops question marks, so read statements as questions and act on a clear go-ahead; settle
engineering choices yourself; ask for sprints, milestones, card time and anything public.
```
