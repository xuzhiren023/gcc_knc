# Installing knc-twin

Requirements: Python 3.8 or newer, standard library only. No network, no card.

## Claude Code

Skills live in a `skills/` directory as one folder per skill containing `SKILL.md`
(https://code.claude.com/docs/en/skills).

- Personal (every project): unzip into `~/.claude/skills/` so that `~/.claude/skills/knc-twin/SKILL.md` exists.
- Project (shared with the repository): unzip into `<repo>/.claude/skills/knc-twin/`.

```bash
unzip knc-twin.zip -d ~/.claude/skills/
python ~/.claude/skills/knc-twin/scripts/knc_twin.py selftest --out /tmp/knc-twin-selftest
```

Claude Code loads the skill's description at session start and reads `SKILL.md` when the task
matches (KNC/IMCI simulation, kernel checks, schedule comparison, bounds). Invoke explicitly
with `/knc-twin`.

## Claude.ai (web and desktop)

Settings > Capabilities > Skills > Upload skill, choose `knc-twin.zip`
(https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview). The zip's top-level
folder must be `knc-twin/` with `SKILL.md` directly inside, which is how `knc-twin.zip` is built.
The skill's scripts run in Claude's code-execution sandbox; outputs are written below the
sandbox working directory (`--out`), so ask for the `result.json`/`summary.md` to be shown.

## Claude API / Agent SDK

Upload the same zip through the Skills API or mount the folder in the container's skills
directory; the entry point is `scripts/knc_twin.py` and needs only Python.

## Verify

```bash
python knc-twin/scripts/knc_twin.py capabilities --out out/caps
python knc-twin/scripts/knc_twin.py selftest --out out/selftest
python knc-twin/scripts/knc_twin.py simulate knc-twin/fixtures/saxpy_loop.json --out out/saxpy
```

`selftest` runs the bundled synthetic tests and oracle checks. Passing them means the engine works as
specified here; the comparison with hardware is `references/validation.md`.

To read compiler output: `python knc-twin/scripts/from_gcc_s.py file.s --function NAME --init init.json --out k.json`
(see `references/input-format.md`). To rank a candidate set off-card: `python knc-twin/scripts/knc_twin.py batch manifest.json --out out/batch`.

## Updating a profile with native data

Follow `references/calibration.md` (prepare-native, measure on the queue, import-native).
Installed profiles are read-only during analysis; imported calibrations are applied as
`--overlay` files until merged with a version bump.
