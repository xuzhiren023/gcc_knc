#!/bin/sh
# Lead only, inside card_run's staged working directory. No system writes.
set -eu
phase=${1:-first}
binary=./membw.mic
if [ "$phase" != second-plan ]; then chmod u+x "$binary"; fi
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
    echo "CASE $case_no --mib 256 --passes 8 --repeats 5 $*"
    if [ "$phase" = second-plan ]; then return; fi
    "$binary" --mib 256 --passes 8 --repeats 5 "$@"
}
second_case() {
    workload=$1
    shift
    # Preserve separate first-sweep candidates, without accepting small offsets
    # or fence differences that lie inside the observed variation.
    case "$workload" in
        read) set -- --pages small --pf0 16 --pf1 32 "$@";;
        write) set -- --pf0 8 --pf1 32 "$@";;
        rmw) set -- --pf0 16 --pf1 32 --evict both "$@";;
    esac
    run --threads 60 --placement spread --pages huge --store ngo \
        --pf0 8 --pf1 64 --mib 2048 --passes 32 --workload "$workload" "$@"
}
if [ "$phase" != second-plan ]; then snapshot; fi
case "$phase" in
    second|second-plan)
        # 1-18: triad calibration first; separate size from sample duration.
        for w in triad read write copy rmw stencil; do
            second_case "$w" --mib 256 --passes 8
            second_case "$w" --passes 8
            second_case "$w"
        done
        # 19-24: keep the final completion fence, remove intermediate fences.
        for w in triad read write copy rmw stencil; do
            second_case "$w" --pass-fence final
        done
        # 25-42: density x coordinated prefetch, with long samples.
        for w in read write copy triad rmw stencil; do
            second_case "$w" --threads 120 --pf0 8 --pf1 64
            second_case "$w" --threads 120 --pf0 32 --pf1 128
            second_case "$w" --threads 60 --pf0 32 --pf1 128
        done
        # 43-52: instruction issue, store density and combined class winners.
        second_case read --read-chains 1
        second_case read --read-chains 4
        second_case write --threads 240
        second_case write --store nr
        second_case write --store normal --prefetch exclusive
        second_case copy --schedule cyclic --chunk-lines 1024 --evict l2
        second_case triad --offset-lines 62 --unroll 8
        second_case triad --split 1 --chunk-lines 1024
        second_case rmw --schedule cyclic --chunk-lines 1024
        second_case stencil --chunk-lines 128 --evict l1
        # 53-58: new allocations, closing long references for every class.
        for w in triad read write copy rmw stencil; do second_case "$w"; done
        ;;
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
        run --threads 60 --pages huge --first-touch serial --workload triad
        run --threads 60 --pages small --first-touch serial --workload triad
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
    *) echo "expected probe, first, second, second-plan, or confirm" >&2; exit 2;;
esac
if [ "$phase" != second-plan ]; then snapshot; fi
