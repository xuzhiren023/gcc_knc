# Shared-card private-session helpers. Loaded on stdin, never installed globally.
# All helpers and their children inherit the private cwd.
guard_dir() {
    case "$run_dir" in
        /tmp/claude/claude-????????????????????????????????) ;;
        *) return 91 ;;
    esac
    suffix=${run_dir##*/claude-}
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
    if [ -n "$memory_group" ] && [ -f "$memory_group/tasks" ]; then
        while read -r member; do
            [ "$member" != "$1" ] || return 0
        done < "$memory_group/tasks"
    fi
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
    while IFS= read -r line; do printf 'CPU\t%s\n' "$line"; done < /proc/cpuinfo
    while IFS= read -r line; do printf 'MEM\t%s\n' "$line"; done < /proc/meminfo
    if command -v taskset >/dev/null; then printf 'PIN\tyes\n'; else printf 'PIN\tno\n'; fi
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
        [ "$sig" = KILL ] || sleep 1
    done
    # A surviving owned process makes removal unsafe (e.g. uninterruptible I/O).
    for proc in /proc/[0-9]*; do
        owned_pid "${proc##*/}" && return 93
    done
    return 0
}
cleanup() {
    stop_owned && guard_boot || return 92
    # Remove only this invocation's empty resource group, never a parent/controller.
    if [ -n "$memory_group" ] && [ -d "$memory_group" ]; then
        rmdir "$memory_group" || return 96
    fi
    # No computed parent path, glob, symlink, or directory from another boot.
    rm -rf -- "$run_dir"
}
start_job() {
    guard_boot && [ -f claude-watchdog.sh ] || return 92
    job_limit=$1
    job_cpus=$2
    job_memory=$3
    shift 3
    # Require an existing memory controller: never mount or enable a controller.
    memory_parent=
    while read -r dev mount kind options rest; do
        case ",$options," in
            *,memory,*) [ "$kind" = cgroup ] && memory_parent=$mount ;;
        esac
    done < /proc/mounts
    if [ -z "$memory_parent" ]; then
        echo 'resident memory enforcement unavailable: no mounted memory cgroup' >&2
        return 96
    fi
    memory_group=$memory_parent/${run_dir##*/}
    mkdir "$memory_group" || return 96
    printf '%s\n' "$((job_memory * 1024 * 1024))" > "$memory_group/memory.limit_in_bytes" || return 96
    if [ -f "$memory_group/memory.use_hierarchy" ]; then
        printf '1\n' > "$memory_group/memory.use_hierarchy" || return 96
    fi
    # The watchdog inherits this exact owned group path as an argument.
    : > stdout
    : > stderr
    # Both background shells detach their SSH file descriptors and ignore HUP.
    # The watchdog survives a broken control connection and applies the same
    # exact-directory and boot guards as host-requested termination.
    (trap '' HUP; exec sh ./claude-watchdog.sh "$run_dir" "$boot_id" "$job_limit" "$memory_group") \
        < /dev/null > /dev/null 2>&1 &
    (trap '' HUP
     # A separate shell's $$ is needed to move only the workload into its group.
     taskset -c "$job_cpus" sh -c '
         printf claude-launch > /proc/self/comm
         echo $$ > "$1/tasks" || exit 96
         shift
         exec ./claude-program "$@"
     ' claude-launch "$memory_group" "$@"
     printf '%s\n' "$?" > status) \
        < /dev/null > stdout 2> stderr &
}
