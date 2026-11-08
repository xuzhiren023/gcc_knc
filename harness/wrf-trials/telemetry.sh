#!/bin/sh
# Card-side telemetry for the WRF optimization trials (harness/wrf-trials/PLAN.md section 4).
# Usage: sh telemetry.sh <model-process-name> <output-dir> [interval-seconds]
# Start it in the job script just before the model and kill it after the model exits; it also
# stops by itself when no process of that name is left. POSIX sh and BusyBox only; reads /proc
# and /sys once per interval, writes CSV into <output-dir>.
name=${1:?process name}; out=${2:?output dir}; interval=${3:-1}
mkdir -p "$out" || exit 1

now() { awk '{print $1}' /proc/uptime; }

# Environment snapshot once.
{
  echo "date $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kernel $(uname -r)"
  echo "nr_hugepages $(cat /proc/sys/vm/nr_hugepages 2>/dev/null)"
  echo "clocksource $(cat /sys/devices/system/clocksource/clocksource0/current_clocksource 2>/dev/null)"
  echo "governor $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
  echo "cur_freq_khz $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null)"
  env | grep -E '^(OMP|GOMP|KMP)_' | sort
} > "$out/env.txt"

echo "t_s,card_uW" > "$out/power.csv"
echo "t_s,HugePages_Total,HugePages_Free,HugePages_Rsvd,AnonHugePages_kB,MemFree_kB" > "$out/mem.csv"
echo "t_s,pid,tid,cpu,vol_ctxt,invol_ctxt,utime_ticks,stime_ticks" > "$out/threads.csv"

# Wait up to 60 s for the model to appear.
pid=""; i=0
while [ -z "$pid" ] && [ $i -lt 60 ]; do
  pid=$(pidof "$name" 2>/dev/null | awk '{print $1}'); [ -z "$pid" ] && sleep 1; i=$((i+1))
done
[ -z "$pid" ] && { echo "no process $name" > "$out/telemetry-error.txt"; exit 1; }
start=$(now); mapped=0

while [ -d "/proc/$pid" ]; do
  t=$(awk -v s="$start" '{printf "%.1f", $1 - s}' /proc/uptime)
  # Whole-card power, first line of the micras power file (microwatts).
  p=$(head -n 1 /sys/class/micras/power 2>/dev/null | awk '{print $1}')
  echo "$t,$p" >> "$out/power.csv"
  awk -v t="$t" '/^HugePages_Total/{a=$2}/^HugePages_Free/{b=$2}/^HugePages_Rsvd/{c=$2}/^AnonHugePages/{d=$2}/^MemFree/{e=$2}
    END{print t","a","b","c","d","e}' /proc/meminfo >> "$out/mem.csv"
  # Every process with this name (one per MPI rank) and every thread in it.
  for p2 in $(pidof "$name" 2>/dev/null); do
    for task in /proc/$p2/task/*; do
      tid=${task##*/}
      st=$(cat "$task/stat" 2>/dev/null) || continue
      # stat field 39 = last CPU, 14/15 = utime/stime; the comm field has no spaces for WRF.
      cpu=$(echo "$st" | awk '{print $39}'); ut=$(echo "$st" | awk '{print $14}'); stt=$(echo "$st" | awk '{print $15}')
      vc=$(awk '/^voluntary_ctxt_switches/{print $2}' "$task/status" 2>/dev/null)
      ic=$(awk '/^nonvoluntary_ctxt_switches/{print $2}' "$task/status" 2>/dev/null)
      echo "$t,$p2,$tid,$cpu,$vc,$ic,$ut,$stt" >> "$out/threads.csv"
    done
  done
  # One page-size snapshot 30 s in.
  if [ $mapped -eq 0 ] && awk -v t="$t" 'BEGIN{exit !(t >= 30)}'; then
    grep -E '^[0-9a-f]+-|KernelPageSize|AnonHugePages' "/proc/$pid/smaps" > "$out/maps.txt" 2>/dev/null
    mapped=1
  fi
  sleep "$interval"
done
echo "model exited" > "$out/telemetry-done.txt"
