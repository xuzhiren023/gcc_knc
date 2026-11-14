#!/bin/sh
# S11-15: bounded serial SIGPROF pilot on the unchanged S11-18 PB-gemm binary.
set -eu
cd -- "$(dirname -- "$0")"
echo 'PROFILE_METHOD event=ITIMER_PROF interval_us=10000 compiler=gcc-knc program=PB-gemm serial_only=1'
uname -r
unset LD_PRELOAD
export LD_LIBRARY_PATH="$PWD"
cat > workload <<'EOF'
#!/bin/sh
if [ "$PROFILE_MODE" = sample ]; then
    export LD_PRELOAD="$PWD/profile-sigprof.so"
fi
exec ./gemm
EOF
chmod +x workload gemm launch
rm -f reference.bin
for pair in 1 2 3; do
    case "$pair" in 2) order='sample plain' ;; *) order='plain sample' ;; esac
    # Two adjacent pairs per block: ~0.89 s/run would yield <300 samples
    # across only three sampled runs at a 10 ms timer resolution.
    for repeat in 1 2; do
    for mode in $order; do
        export PROFILE_MODE="$mode"
        rm -f arrays.bin
        echo "PROFILE_BEGIN pair=$pair repeat=$repeat mode=$mode"
        if ./launch serial PB-gemm > launch.out 2> launch.err; then
            grep '^CORPUS_\(META\|TIME\|CLOCK\|RUNTIME\) ' launch.out
            cat launch.err
        else
            tail -n 12 launch.err
            echo "PROFILE_BLOCKED launch pair=$pair repeat=$repeat mode=$mode"
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
            grep -q '^PROFILE_SAMPLER_COMPLETE$' launch.err || {
                echo 'PROFILE_BLOCKED sampler did not complete'; exit 3;
            }
        fi
        echo "PROFILE_END pair=$pair repeat=$repeat mode=$mode"
    done
    done
done
echo 'PROFILE_CAPTURE_COMPLETE qualification pending host analysis'
