# GCC-KNC status

Updated automatically at every ticket change. Last update: 2026-11-01 21:58.

**Next: the tech lead, on S0-03.** Ask a Claude session in this folder: "Act as tech lead. Handle what the board needs."

Current tickets: `[#####---------------]` 2 of 8

## Milestones

| | Milestone | State | Progress |
|---|---|---|---|
| M0 | Foundation | In progress | 2 of 8 tickets |
| M1 | Mixed native code | Not started | Not planned in detail yet |
| M2 | Useful vector target | Not started | Not planned in detail yet |
| M3 | Runtimes | Not started | Not planned in detail yet |
| M4 | Broad optimization | Not started | Not planned in detail yet |
| M5 | Program corpus | Not started | Not planned in detail yet |
| M6 | Release | Not started | Not planned in detail yet |

## Tickets

| Ticket | What | State | Latest |
|---|---|---|---|
| S0-01 | Toolchain manifest and doctor | Done | Reviewed: red commit real; tests fail on the missing-tool cases; doctor rerun OK, required tools present, d... |
| S0-02 | ISA lint | Done | knc_lint now rejects the listed non-KNC instructions in .s, .o, archives, shared objects and executables, a... |
| S0-03 | Test runner and red baseline | Waiting for review | Red test 36a8d3f proved fixed output collision; fix d89111e uses per-Runner TemporaryDirectory and cleanup.... |
| S0-04 | Card runner | Not started |  |
| S0-05 | Donor inventory | Not started |  |
| S0-06 | GCC 16.2 fork and timing | Not started |  |
| S0-07 | Benchmark corpus and coverage estimate | Not started |  |
| S0-08 | Toolchain independent of PhiWeather | Not started | Tested: `gcc -v` shows `--with-as`, `--with-ld` and `--with-sysroot` compiled in with PhiWeather paths, and... |

## Recent activity

- 2026-11-01 21:58 **S0-03** engineer submit: Red test 36a8d3f proved fixed output collision; fix d89111e uses per-Runner TemporaryDirectory and cleanup. tools/check t0 t1 t2 --compiler donor -...
- 2026-11-01 21:55 **S0-03** lead answer: Yes, but through the runner: no ACL edits, and no cleanup by hand. Likely cause, inferred and not proved because this session could not run icacls:...
- 2026-11-01 21:54 **S0-03** engineer ask: Red e9f46ee; fix a3b8aad implements directory checks, trace parser and cache fix. Created empty lib and usr/lib. Two donor runs (15.70s/16.76s), in...
- 2026-11-01 21:50 **S0-03** owner decide: Owner approved on 2026-11-01: sessions raised to 5, one to finish and one for review changes. Follow the 21:35 lead note.
- 2026-11-01 21:35 **S0-08** lead note: Tested: `gcc -v` shows `--with-as`, `--with-ld` and `--with-sysroot` compiled in with PhiWeather paths, and `-B<shared>/cross/bin/` does not change...
- 2026-11-01 21:35 **S0-03** lead recommend: Owner: raise `sessions` to 5 on this ticket, one to finish and one for review changes. pm.py decide alone sends it straight back here, because the ...
- 2026-11-01 21:35 **S0-03** lead note: Tested from the lead session in a throwaway sysroot, so do not re-derive it. Adding empty lib and usr/lib makes the link exit 0: K1OM machine, inte...
- 2026-11-01 21:31 **S0-03** lead escalate: budget: 3 engineer sessions used; the budget is 3

## Cost

- From the script, engineer: 8 sessions, 3.7M input tokens
- From the script, lead: 8 sessions, 4.2M input tokens
- Started by hand, Claude: 2 sessions, 48.6M input tokens
- Started by hand, GPT: 1 sessions, 0.9M input tokens
- Input tokens include the context re-read on every turn, most of it cached and cheap.

## Disk

The project uses 1.8 GiB of 100 GiB. 372 GiB free on the drive.
