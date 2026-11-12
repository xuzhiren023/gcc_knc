#!/bin/sh
# Lead only, inside card_run's staged working directory. No system writes.
set -eu
phase=${1:-first}
binary=./membw.mic
chmod u+x "$binary"
case_no=0
snapshot() {
    echo "METADATA $(date -u)"
    uname -a
    for f in /proc/meminfo /proc/loadavg /proc/sys/kernel/perf_event_paranoid \
        /sys/kernel/mm/transparent_hugepage/enabled \
        /sys/kernel/mm/transparent_hugepage/defrag \
        /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor \
        /sys/devices/system/cpu/cpu1/cpufreq/scaling_cur_freq \
        /sys/devices/system/cpu/cpu1/cpufreq/cpuinfo_max_freq \
        /sys/devices/system/cpu/cpufreq/boost \
        /sys/class/thermal/thermal_zone*/temp; do
        if [ -r "$f" ]; then echo "FILE $f"; cat "$f"; else echo "UNAVAILABLE $f"; fi
    done
}
run() {
    case_no=$((case_no+1))
    echo "CASE $case_no $*"
    "$binary" --mib 256 --passes 8 --repeats 5 "$@"
}
snapshot
case "$phase" in
    probe)
        # Expose the actual registered PMUs/aliases rather than assuming Xeon
        # server event encodings work on KNC. Nothing is installed or enabled.
        "$binary" --probe 1
        for d in /sys/bus/event_source/devices/*; do
            [ -d "$d" ] || continue
            echo "PMU $d"
            for f in "$d"/type "$d"/cpumask "$d"/events/* "$d"/format/*; do
                if [ -r "$f" ]; then echo "FILE $f"; cat "$f"; fi
            done
        done
        ;;
    first)
        # 1: store semantics, then density and huge pages (8 cases).
        for s in normal nr ngo; do run --store "$s" --threads 0; done
        for t in 60 120; do run --threads "$t" --placement spread; done
        for t in 60 120 240; do run --threads "$t" --placement spread --pages huge; done
        # 2: two-level prefetch and exclusive ownership (6 cases).
        run --threads 60 --pages huge --prefetch none
        for pair in '8 32' '8 64' '16 64' '32 128'; do
            set -- $pair
            run --threads 60 --pages huge --pf0 "$1" --pf1 "$2"
        done
        run --threads 60 --pages huge --store normal --prefetch exclusive
        # 3: placement/channel conflicts, reusing the same allocation size (7).
        for off in 1 62 124 992; do run --threads 60 --pages huge --offset-lines "$off"; done
        run --threads 60 --pages huge --padding-lines 17
        run --threads 60 --pages huge --placement compact
        run --threads 60 --pages huge --placement reverse
        # 4: batching/blocking and first-touch order (6).
        for chunk in 128 1024; do
            run --threads 60 --pages huge --chunk-lines "$chunk" --split 1
            run --threads 60 --pages huge --chunk-lines "$chunk" --schedule cyclic
        done
        run --threads 60 --pages huge --first-touch serial
        run --threads 60 --pages small --first-touch serial
        # 5: instruction overhead, eviction, fence and far hint (7).
        for u in 1 8; do run --threads 60 --pages huge --unroll "$u"; done
        for ev in l1 l2 both; do run --threads 60 --pages huge --evict "$ev"; done
        run --threads 60 --pages huge --fence chunk
        run --threads 60 --pages huge --prefetch l2
        # 6: core scaling; then a closing reference for drift (4).
        for t in 16 32 48; do run --threads "$t" --pages huge --placement spread; done
        run --threads 60 --pages huge
        ;;
    confirm)
        # Append a chosen configuration to sweep.sh confirm arguments. Pair
        # reference/candidate twice to distinguish tuning from thermal drift.
        shift
        run --threads 60 --pages huge
        run "$@"
        run "$@"
        run --threads 60 --pages huge
        ;;
    *) echo "expected probe, first, or confirm" >&2; exit 2;;
esac
snapshot
