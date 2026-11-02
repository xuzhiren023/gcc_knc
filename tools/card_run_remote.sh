# S0-04 private-session helpers. Loaded on stdin, never installed on the card.
# All helpers and their children inherit the private cwd.
guard_dir() {
    case "$run_dir" in
        /var/volatile/tmp/gcc-knc-????????????????????????????????) ;;
        *) return 91 ;;
    esac
    suffix=${run_dir##*/gcc-knc-}
    case "$suffix" in *[!0-9a-f]*) return 91 ;; esac
    [ ! -L "$run_dir" ] && [ -d "$run_dir" ] &&
        [ "$(pwd -P)" = "$run_dir" ] &&
        [ "$(stat -c %u "$run_dir")" = "$(id -u)" ]
}
guard_boot() {
    guard_dir && [ -n "$boot_id" ] &&
        [ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id" ]
}
owned_pid() {
    [ "$1" != "$$" ] || return 1
    pid_exe=$(readlink "/proc/$1/exe" 2>/dev/null)
    pid_cwd=$(readlink "/proc/$1/cwd" 2>/dev/null)
    case "$pid_exe" in "$run_dir"|"$run_dir"/*) return 0 ;; esac
    case "$pid_cwd" in "$run_dir"|"$run_dir"/*) return 0 ;; esac
    return 1
}
snapshot() {
    guard_dir || return 91
    printf 'BOOT\t'
    cat /proc/sys/kernel/random/boot_id || return 92
    for proc in /proc/[0-9]*; do
        proc_pid=${proc##*/}
        proc_exe=$(readlink "$proc/exe" 2>/dev/null)
        proc_cwd=$(readlink "$proc/cwd" 2>/dev/null)
        proc_name=
        IFS= read -r proc_name < "$proc/comm" 2>/dev/null
        proc_ppid=
        while read -r proc_key proc_value proc_rest; do
            if [ "$proc_key" = PPid: ]; then proc_ppid=$proc_value; break; fi
        done < "$proc/status" 2>/dev/null
        [ -d "$proc" ] || continue
        printf 'PROC\t%s\t%s\t%s\t%s\t%s\n' "$proc_pid" "$proc_ppid" "$proc_name" "$proc_exe" "$proc_cwd"
    done
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
        [ "$sig" = KILL ] || sleep 0.1
    done
    # A surviving owned process makes removal unsafe (e.g. uninterruptible I/O).
    for proc in /proc/[0-9]*; do
        owned_pid "${proc##*/}" && return 93
    done
    return 0
}
cleanup() {
    stop_owned && guard_boot || return 92
    # No computed parent path, glob, symlink, or directory from another boot.
    rm -rf -- "$run_dir"
}
start_job() {
    guard_boot && [ -f watchdog.sh ] || return 92
    job_limit=$1
    shift
    : > stdout
    : > stderr
    # Both background shells detach their SSH file descriptors and ignore HUP.
    # The watchdog survives a broken control connection and applies the same
    # exact-directory and boot guards as host-requested termination.
    (trap '' HUP; exec sh ./watchdog.sh "$run_dir" "$boot_id" "$job_limit") \
        < /dev/null > /dev/null 2>&1 &
    (trap '' HUP; ./program "$@"; printf '%s\n' "$?" > status) \
        < /dev/null > stdout 2> stderr &
}
