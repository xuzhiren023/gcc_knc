#!/bin/sh
# One frozen workload per card_run, which enforces the 600 second launch cap.
set -eu
cd -- "$(dirname -- "$0")"
program=$1
density=$2
mode=$3
case "$mode" in plain|sample) ;; *) exit 3 ;; esac
unset LD_PRELOAD
mv workload profile-workload
cat > workload <<'EOF'
#!/bin/sh
if [ "$PROFILE_MODE" = sample ]; then
    export LD_PRELOAD="$PWD/profile-batch.so"
fi
exec ./profile-workload
EOF
chmod +x workload profile-workload launch
export PROFILE_MODE="$mode"
echo "PROFILE_BEGIN program=$program density=$density mode=$mode"
if ./launch "$density" "$program"; then
    if [ "$mode" = sample ]; then
        grep -q '^PROFILE_SAMPLER_COMPLETE$' workload.stderr || {
            echo 'PROFILE_BLOCKED sampler did not complete'; exit 3;
        }
    fi
else
    echo 'PROFILE_BLOCKED workload or collector failed'
    exit 3
fi
echo "PROFILE_END program=$program density=$density mode=$mode"
