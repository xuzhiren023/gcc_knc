#!/bin/bash
# Lead: run the three engineer lanes in parallel (gcc = tree 1, gcc2 = tree 2, tools); logs in .work/_state/logs.
cd "$(dirname "$0")/.."
for lane in gcc gcc2 tools; do
  python tools/dispatch.py --lane $lane --max-sessions 6 > .work/_state/logs/dispatch-$lane-$(date +%Y%m%d-%H%M).log 2>&1 &
done
wait
