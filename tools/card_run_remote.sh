# Shared-card private-session helpers. Loaded on stdin, never installed globally.
# All helpers and their children inherit the private cwd.
resolve_tmp() {
    [ -z "${tmp_physical:-}" ] || return 0
    tmp_physical=$(cd /tmp && pwd -P) && [ -n "$tmp_physical" ] || {
        echo 'guard_dir: cannot resolve physical /tmp' >&2; return 91;
    }
}
resolve_run_dir() {
    case "$run_dir" in
        /tmp/claude/claude-????????????????????????????????) ;;
        *) echo "guard_dir: directory shape: $run_dir" >&2; return 91 ;;
    esac
    suffix=${run_dir##*/claude-}
    case "$suffix" in
        *[!0-9a-f]*) echo "guard_dir: job ID must be lowercase hex: $run_dir" >&2; return 91 ;;
    esac
    resolve_tmp || return 91
    physical_run_dir=${tmp_physical%/}/claude/claude-$suffix
}
guard_dir() {
    resolve_run_dir || return 91
    [ ! -L "$run_dir" ] || {
        echo "guard_dir: directory is a symlink: $run_dir" >&2; return 91;
    }
    [ -d "$run_dir" ] || {
        echo "guard_dir: directory missing: $run_dir" >&2; return 91;
    }
    [ "$(pwd -P)" = "$physical_run_dir" ] || {
        echo "guard_dir: physical cwd must equal $physical_run_dir" >&2; return 91;
    }
    [ "$(LC_ALL=C ls -ldn "$run_dir" | { read -r mode links owner rest; printf '%s' "$owner"; })" = "$(id -u)" ] || {
        echo "guard_dir: directory owner mismatch or unreadable: $run_dir" >&2; return 91;
    }
}
check_boot() {
    [ -n "$boot_id" ] || { echo 'check_boot: boot ID missing' >&2; return 92; }
    current_boot=$(cat /proc/sys/kernel/random/boot_id) && [ -n "$current_boot" ] || {
        echo 'check_boot: boot ID unreadable' >&2; return 92;
    }
    [ "$current_boot" = "$boot_id" ] || {
        echo 'check_boot: boot ID mismatch; no signalling or removal permitted' >&2; return 92;
    }
}
guard_boot() { guard_dir && check_boot; }
owned_pid() {
    [ "$1" != "$$" ] || return 1
    # Kernel-thread exe/cwd links exist to lstat but cannot be followed.
    # Read identity with shell builtins before any readlink/subshell per PID.
    [ "$1" != 2 ] || return 1
    pid_ppid=
    while read -r pid_key pid_value pid_rest; do
        if [ "$pid_key" = PPid: ]; then pid_ppid=$pid_value; break; fi
    done < "/proc/$1/status" 2>/dev/null
    [ -n "$pid_ppid" ] && [ "$pid_ppid" != 2 ] || return 1
    [ -L "/proc/$1/exe" ] || [ -L "/proc/$1/cwd" ] || return 1
    pid_exe=$(readlink "/proc/$1/exe" 2>/dev/null)
    pid_cwd=$(readlink "/proc/$1/cwd" 2>/dev/null)
    case "$pid_exe" in "$physical_run_dir"|"$physical_run_dir"/*) return 0 ;; esac
    case "$pid_cwd" in "$physical_run_dir"|"$physical_run_dir"/*) return 0 ;; esac
    return 1
}
snapshot() {
    IFS= read -r snapshot_boot < /proc/sys/kernel/random/boot_id || return 92
    printf 'BOOT\t%s\n' "$snapshot_boot"
    resolve_run_dir || return 91
    printf 'RUNDIR\t%s\n' "$physical_run_dir"
    {
    # Only admission needs the CPU map. Keep block separators for cpu_binding,
    # without shell read/printf commands for thousands of unused cpuinfo lines.
    if [ "${1:-}" != skip-cpu ]; then
        awk '/^processor[ \t]*:|^core id[ \t]*:/ {print "CPU\t" $0}
             /^$/ {print "CPU\t"}' /proc/cpuinfo
    fi
    awk '/^MemFree:/ {print "MEM\t" $0; exit}' /proc/meminfo
    set --
    for proc in /proc/[0-9]*; do
        proc_pid=${proc##*/}
        [ "$proc_pid" != "$$" ] || continue
        proc_ppid=
        while read -r proc_key proc_value proc_rest; do
            if [ "$proc_key" = PPid: ]; then proc_ppid=$proc_value; break; fi
        done < "$proc/status" 2>/dev/null
        # The control shell and its snapshot utilities are ours even before cd.
        # Match identities, never names that a foreign process could also use.
        [ "$proc_ppid" != "$$" ] || continue
        [ "$proc_pid" != 2 ] && [ "$proc_ppid" != 2 ] || continue
        [ -n "$proc_ppid" ] || continue
        proc_name=
        IFS= read -r proc_name < "$proc/comm" 2>/dev/null
        [ -d "$proc" ] || continue
        printf 'IDENT\t%s\t%s\t%s\n' "$proc_pid" "$proc_ppid" "$proc_name"
        set -- "$@" "$proc/exe" "$proc/cwd"
    done
    # One ls for all surviving user processes, no readlink/subshell per PID.
    # A disappearing process may lose either link; keep its identity with blanks.
    if [ "$#" -gt 0 ]; then LC_ALL=C ls -ldn -- "$@" 2>/dev/null || :; fi
    } | awk '
        BEGIN { FS = "\t" }
        /^CPU\t|^MEM\t/ { print; next }
        /^IDENT\t/ { ppid[$2] = $3; name[$2] = $4; next }
        /^l/ && match($0, /\/[0-9]+\/(exe|cwd) -> /) {
            split(substr($0, RSTART, RLENGTH), link, "/")
            target = substr($0, RSTART + RLENGTH)
            if (link[3] == "exe -> ") exe[link[2]] = target
            else cwd[link[2]] = target
        }
        END {
            for (pid in ppid)
                printf "PROC\t%s\t%s\t%s\t%s\t%s\n", pid, ppid[pid], name[pid], exe[pid], cwd[pid]
        }'
}
reap_one() {
    run_dir=$1
    case "$run_dir" in /tmp/claude/claude-????????????????????????????????) ;; *) return 0 ;; esac
    suffix=${run_dir##*/claude-}
    case "$suffix" in *[!0-9a-f]*) return 0 ;; esac
    [ ! -L "$run_dir" ] && [ -d "$run_dir" ] || return 0
    cd -- "$run_dir" || return 92
    guard_dir || return 0
    check_boot || return 92
    # Stale recovery never signals: any live user of this exact cwd/exe keeps it.
    for proc in /proc/[0-9]*; do
        owned_pid "${proc##*/}" && return 0
    done
    guard_boot || return 92
    rm -rf -- "$run_dir"
}
reap_stale() {
    check_boot || return 92
    reap_original=$run_dir
    reap_cwd=$PWD
    for stale_dir in /tmp/claude/claude-*; do
        reap_one "$stale_dir"
        reap_status=$?
        run_dir=$reap_original
        cd -- "$reap_cwd" || return 92
        [ "$reap_status" = 0 ] || return "$reap_status"
    done
    rmdir /tmp/claude 2>/dev/null || :
}
stop_owned() {
    guard_boot || return 92
    for sig in TERM KILL; do
        for proc in /proc/[0-9]*; do
            proc_pid=${proc##*/}
            if owned_pid "$proc_pid"; then
                guard_boot || return 92
                # Recheck identity after the boot guard; never signal by name/group.
                if owned_pid "$proc_pid"; then
                    kill -"$sig" "$proc_pid" 2>/dev/null || :
                fi
            fi
        done
        [ "$sig" = KILL ] || sleep 1
    done
    # A surviving owned process makes removal unsafe (e.g. uninterruptible I/O).
    for proc in /proc/[0-9]*; do
        owned_pid "${proc##*/}" && return 93
    done
    return 0
}
cleanup() {
    check_boot || return 92
    # Admission may have refused before creating any remote directory.
    [ -e "$run_dir" ] || return 0
    stop_owned && guard_boot || return 92
    # No computed parent path, glob, symlink, or directory from another boot.
    rm -rf -- "$run_dir" || return 92
    rmdir /tmp/claude 2>/dev/null || :
}
start_job() {
    guard_boot && [ -f claude-watchdog.sh ] && [ -x claude-pin ] || return 92
    job_limit=$1
    job_cpus=$2
    job_memory=$3
    shift 3
    : > stdout
    : > stderr
    # Both background shells detach their SSH file descriptors and ignore HUP.
    # The watchdog survives a broken control connection and applies the same
    # exact-directory and boot guards as host-requested termination.
    (trap '' HUP; exec sh ./claude-watchdog.sh "$run_dir" "$boot_id" "$job_limit") \
        < /dev/null > /dev/null 2>&1 &
    (trap '' HUP
     printf claude-launch > /proc/self/comm
     ./claude-pin "$job_cpus" "$job_memory" ./claude-program "$@"
     printf '%s\n' "$?" > status) \
        < /dev/null > stdout 2> stderr &
}
