# Card batches (lead only)

The interactive lead runs every card job, under the shared card rules: cores 40-59 (from 2026-11-04; 30-59 before), at most 7 GB,
the shared ledger, and `claude-` names. These scripts are the lead's batch harness, not engineer
tooling.

- `build_suite.py OUTDIR [gcc16|donor] [--list FILE]` builds the `gcc.c-torture/execute` programs on
  the laptop and records which contain packed zmm code. Run it only while no `make.exe` is
  rebuilding `cc1`.
- `run_suite.py PROGDIR OUTDIR` runs them on the card in chunks of 300 at `-j 80` (4 threads per core, 80 MiB each), retrying a
  chunk refused for infrastructure.

When a ticket that changes generated code merges, run its own card check (the programs are in
`tests/acceptance/`), then:

```
python harness/card/build_suite.py .work/_shared/tmp/<name> gcc16
python harness/card/run_suite.py .work/_shared/tmp/<name> .work/_state/card/<name>
```

Note: before 2026-11-04 this script passed Windows source paths, so 19 sources with quoted includes failed to compile; with the fix expect about 1,680 linked (S3-10). Baseline at `knc` `edf7c69d617` (S3-14 merged; same as at `10ce7e12b64`), with the old paths: 1,692 sources, 1,661 linked, 93 with packed zmm
code, 1 ICE (`pr85169`, S3-20), and **1,661 of 1,661 PASS** on the card. For a quick check, pass
`--list .work/_shared/tmp/S2-08/claude-torture.list` to build S2-08's 256-program subset.
