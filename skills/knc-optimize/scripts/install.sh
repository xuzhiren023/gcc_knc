#!/bin/sh
# Install the packaged files; do not run any tuning or card commands.
set -eu
skill_source=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
: "${HOME:?HOME must name the installation user's home directory}"
skill_parent=${KNC_SKILL_INSTALL_ROOT:-$HOME/.claude/skills}
skill_destination=$skill_parent/knc-optimize
if [ -e "$skill_destination" ] || [ -L "$skill_destination" ]; then
    printf '%s\n' "Installation already exists: $skill_destination" >&2
    exit 1
fi
mkdir -p -- "$skill_parent"
# mkdir also refuses a destination created concurrently.
mkdir -- "$skill_destination"
cp -R -- "$skill_source/." "$skill_destination/"
printf '%s\n' "Installed knc-optimize at $skill_destination"
