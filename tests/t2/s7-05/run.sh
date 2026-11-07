#!/bin/sh
# Lead-only card runner. Copy the complete S7-05 directory to the card.
# Usage: sh /absolute/path/S7-05/run.sh donor|candidate
# Do not add this directory to the system loader configuration.
set -eu
case ${1-} in donor|candidate) runtime=$1;; *) echo 'usage: run.sh donor|candidate' >&2; exit 2;; esac
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
loader=/lib64/ld-linux-k1om.so.2
test -x "$loader"
test -f "$base/$runtime/libgcc_s.so.1"
# Explicit loader invocation and private first search path override existing
# LD_LIBRARY_PATH and avoid replacement of any system library.
unset LD_PRELOAD LD_LIBRARY_PATH LD_AUDIT
for exe in old-compat.mic new-compat.mic old-unwind.mic new-helpers.mic; do
    if test "$runtime" = donor && test "$exe" = new-helpers.mic; then continue; fi
    "$loader" --library-path "$base/$runtime:/lib64:/usr/lib64" \
        "$base/$exe" "$base/plugin.so" > "$base/$exe.actual"
    diff -u "$base/$exe.expected" "$base/$exe.actual"
    echo "PASS $runtime $exe expected output"
done
