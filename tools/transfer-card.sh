#!/bin/sh
# Invoked only by card_run --benchmark --threads 240. All files are staged there.
set -eu
cd "$(dirname "$0")"
exec ./transfer-card.mic lease "$@"
