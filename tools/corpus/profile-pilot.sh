#!/bin/sh
# S11-15: bounded existing-perf pilot on the unchanged S11-18 PB-gemm binary.
set -eu
cd -- "$(dirname -- "$0")"
event=${1:-cpu-clock:u}
case "$event" in cpu-clock:u|cycles:u) ;; *) exit 2 ;; esac
command -v perf >/dev/null 2>&1 || { echo 'PROFILE_BLOCKED no existing perf executable'; exit 3; }
echo "PROFILE_METHOD event=$event frequency=99 compiler=gcc-knc program=PB-gemm"
perf --version
uname -r
cat /proc/sys/kernel/perf_event_paranoid
export PROFILE_EVENT="$event"
cat > workload <<'EOF'
#!/bin/sh
if [ "$PROFILE_MODE" = sample ]; then
    exec perf record -e "$PROFILE_EVENT" -F 99 -m 64 -o perf.data -- ./gemm
fi
exec ./gemm
EOF
chmod +x workload gemm launch
rm -f reference.bin
for pair in 1 2 3; do
    case "$pair" in 2) order='sample plain' ;; *) order='plain sample' ;; esac
    for mode in $order; do
        export PROFILE_MODE="$mode"
        rm -f arrays.bin perf.data perf.data.old
        echo "PROFILE_BEGIN pair=$pair mode=$mode"
        if ./launch serial PB-gemm > launch.out 2> launch.err; then
            grep '^CORPUS_\(META\|TIME\|CLOCK\|RUNTIME\) ' launch.out
            cat launch.err
        else
            tail -n 12 launch.err
            echo "PROFILE_BLOCKED launch pair=$pair mode=$mode"
            exit 3
        fi
        # Materialized complete live-outs, not a checksum. This checks perturbation;
        # independent donor correctness still belongs to the primary harness.
        [ -s arrays.bin ] || { echo 'PROFILE_BLOCKED missing live-outs'; exit 3; }
        if [ -f reference.bin ]; then
            cmp arrays.bin reference.bin || { echo 'PROFILE_BLOCKED changed live-outs'; exit 3; }
        else
            cp arrays.bin reference.bin
        fi
        echo 'PROFILE_LIVEOUT identical'
        if [ "$mode" = sample ]; then
            # Preserve symbol/IP evidence in the returned log before overwriting data.
            perf report --stdio -n --sort dso,symbol -i perf.data > report.out 2> report.err || {
                cat report.err; echo 'PROFILE_BLOCKED perf report'; exit 3;
            }
            echo 'PROFILE_REPORT_BEGIN'
            cat report.out report.err
            echo 'PROFILE_REPORT_END'
            perf script -i perf.data > samples.out 2> samples.err || {
                cat samples.err; echo 'PROFILE_BLOCKED perf script'; exit 3;
            }
            lines=$(wc -l < samples.out)
            [ "$lines" -gt 0 ] && [ "$lines" -le 20000 ] || {
                echo "PROFILE_BLOCKED empty or oversized sample output lines=$lines"; exit 3;
            }
            echo 'PROFILE_SAMPLES_BEGIN'
            cat samples.out samples.err
            echo 'PROFILE_SAMPLES_END'
            # Dump record headers to expose LOST/THROTTLE records independently of
            # report percentages. Full raw dump stays bounded and local to the job.
            perf report -D -i perf.data > records.out 2> records.err || {
                cat records.err; echo 'PROFILE_BLOCKED record inspection'; exit 3;
            }
            echo 'PROFILE_RECORD_DIAGNOSTICS_BEGIN'
            grep -E 'LOST|THROTTLE|TOTAL|SAMPLE|MMAP' records.out || true
            cat records.err
            echo 'PROFILE_RECORD_DIAGNOSTICS_END'
        fi
        echo "PROFILE_END pair=$pair mode=$mode"
    done
done
echo 'PROFILE_CAPTURE_COMPLETE qualification pending host analysis'
