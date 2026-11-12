#!/usr/bin/env python3
"""S11-01 build/loopback and lead-only exclusive-turn transfer runner.

No native action occurs for build or loopback. Results are payload measurements,
not provenance records. No vendor libraries/headers are staged or distributed.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import queue
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
OUT = SHARED / 'S11-01'
if (HERE / 'transfer-host.exe').exists():
    OUT = HERE
    SHARED = HERE.parent
    PROJECT = SHARED.parent.parent
TC = SHARED / 'toolchain'
ENV = dict(os.environ, PATH=os.pathsep.join(map(str, (TC / 'cross/bin', TC / 'cygwin/bin')))
           + os.pathsep + os.environ['PATH'])
SIZES = (4096, 1048576, 67108864, 1073741824)
METHODS = ('pipe', 'scp', 'tar', 'tcp', 'scif-msg', 'scif-write', 'scif-read', 'scif-vwrite', 'scif-mmap')
LEASE_DIRECTORY = re.compile(r'(?:/tmp|/var/volatile/tmp)/claude/claude-[a-f0-9]{32}\Z')


def command(argv):
    print('+ ' + ' '.join(map(str, argv)), flush=True)
    subprocess.run([v.as_posix() if isinstance(v, Path) else str(v) for v in argv], env=ENV, check=True)


def build(host_only=False, card_only=False, output_dir=None):
    output_dir = OUT if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    flags = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-pthread']
    if not card_only:
        command([TC / 'cygwin/bin/gcc.exe', *flags, HERE / 'transfer_bench.c',
                 '-o', output_dir / 'transfer-host.exe'])
    if host_only:
        return
    import storage
    slot = storage.gcc_slot()
    version = (SHARED / storage.GCC_SLOTS[slot][0] / 'gcc/BASE-VER').read_text().strip()
    prefix = SHARED / ('gcc-knc-' + version + ('' if slot == '1' else '-' + slot))
    command([prefix / 'bin/k1om-mpss-linux-gcc.exe',
             '--sysroot=' + (TC / 'sysroot').as_posix(), *flags, '-march=knc',
             '-fno-tree-vectorize', HERE / 'transfer_bench.c', '-ldl',
             '-o', OUT / 'transfer-card.mic'])
    command([sys.executable, HERE / 'knc_lint', OUT / 'transfer-card.mic'])
    for name in ('host_card_transfer.py', 'transfer-card.sh'):
        shutil.copyfile(HERE / name, OUT / name)
    command([TC / 'cygwin/bin/chmod.exe', '755', OUT / 'transfer-card.mic', OUT / 'transfer-card.sh'])
    print('STAGED (no card execution): ' + str(OUT))


def start_endpoint(role, method, address, port, nonce, size, repeats, direction, cpus='-', corrupt=False, **kwargs):
    args = [str(OUT / 'transfer-host.exe'), role, method, str(address), str(port), nonce,
            str(size), str(repeats), direction, cpus]
    if corrupt:
        args.append('corrupt')
    return subprocess.Popen(args, env=ENV, stderr=subprocess.PIPE, **kwargs)


def ready(proc):
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(proc.stderr.readline()), daemon=True).start()
    try:
        line = lines.get(timeout=20)
    except queue.Empty:
        raise RuntimeError('card endpoint startup deadline: no listener announcement within 20 seconds')
    try:
        row = json.loads(line)
        if not isinstance(row, dict) or row.get('ready') is not True:
            raise ValueError('not ready')
        return row
    except (ValueError, TypeError):
        raise RuntimeError('endpoint startup failed: ' + line.decode(errors='replace'))


def lease_ready(proc, log, nonce):
    """Drain card_run output continuously, retaining its diagnostics after startup."""
    announcements = queue.Queue()

    drained = threading.Event()

    def drain():
        try:
            for line in iter(proc.stdout.readline, b''):
                log.write(line)
                log.flush()
                try:
                    row = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(row, dict) and row.get('ready') is True:
                    announcements.put(row)
        finally:
            drained.set()
            announcements.put(None)

    threading.Thread(target=drain, daemon=True).start()
    try:
        # The card listener waits 90 s, exceeding this deadline plus card_run's 10 s relay interval.
        row = announcements.get(timeout=60)
    except queue.Empty:
        raise RuntimeError('lease startup deadline: no card listener announcement; see card-control.log')
    if not row or row.get('nonce') != nonce or type(row.get('port')) is not int or not 0 < row['port'] <= 65535:
        raise RuntimeError('invalid card lease listener announcement; see card-control.log')
    proc._card_log_drained = drained
    return row


def rows_from(output, code):
    rows = []
    for line in output.decode(errors='replace').splitlines():
        if line.startswith('{'):
            row = json.loads(line)
            if 'integrity' in row:
                if row['integrity'] != 'match':
                    raise RuntimeError('integrity mismatch: ' + line)
                rows.append(row)
    if code or not rows:
        raise RuntimeError('endpoint failure: ' + output.decode(errors='replace')[-2000:])
    return rows


def loopback(method, direction, size, corrupt=False):
    nonce = secrets.token_hex(16)
    host = peer = None
    try:
        if method != 'pipe':
            peer = start_endpoint('card', method, '127.0.0.1', 0, nonce, size, 2,
                                  direction, corrupt=corrupt, stdout=subprocess.DEVNULL)
            greeting = ready(peer)
        else:
            greeting = {'port': 0}
        host = start_endpoint('host', method, '127.0.0.1', greeting['port'], nonce, size, 2, direction,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE if method == 'pipe' else subprocess.DEVNULL)
        if method == 'pipe':
            peer = start_endpoint('card', method, '127.0.0.1', 0, nonce,
                                  size, 2, direction, corrupt=corrupt,
                                  stdin=host.stdout, stdout=host.stdin)
        if host.stdout:
            host.stdout.close()
            host.stdout = None
        host.stdin.close()
        host.stdin = None
        _, output = host.communicate(timeout=60)
        _, peer_output = peer.communicate(timeout=60)
        result = rows_from(output, host.returncode)
        if peer.returncode:
            raise RuntimeError(peer_output.decode(errors='replace'))
        return result
    finally:
        # Only fake/localhost processes enter this path. Never kill a DMA process.
        for proc in (host, peer):
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()


def event_log():
    """Fail closed on access errors; no matching bugcheck events is a valid zero."""
    script = """$ErrorActionPreference='Stop'
try {
  $e=Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-WER-SystemErrorReporting';Id=1001} -MaxEvents 1
  $id=[long]$e.RecordId
} catch {
  if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { $id=0 } else { throw }
}
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
@{bugcheckRecord=$id;boot=$boot} | ConvertTo-Json -Compress
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def ssh_args(config, compression=False, cipher=None, mac=None):
    result = ['C:/Windows/System32/OpenSSH/ssh.exe', '-T', '-F', 'NUL', '-i', config['identity'],
              '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
              '-o', 'GlobalKnownHostsFile=NUL', '-o', 'UserKnownHostsFile=' + config['knownHosts'],
              '-o', 'HostKeyAlgorithms=ssh-ed25519', '-o', 'ConnectTimeout=5',
              '-o', 'Compression=' + ('yes' if compression else 'no')]
    if cipher:
        result += ['-c', cipher]
    if mac:
        result += ['-m', mac]
    return result + ['root@' + config['host']]


def native_trial(config, lease, address, method, size, direction, repeats=20,
                 compression=False, cipher=None, mac=None):
    nonce = secrets.token_hex(16)
    host = None
    remote = None
    try:
        if method != 'tcp':
            host = start_endpoint('host', method, address, 0, nonce, size, repeats, direction,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE if method == 'pipe' else subprocess.DEVNULL)
        info = {'port': 0, 'node': 0} if method in ('pipe', 'tcp') else ready(host)
        args = ['./transfer-card.mic', 'card', method,
                str(info['node']) if method.startswith('scif-') else '0.0.0.0',
                str(info['port']), nonce, str(size), str(repeats), direction, lease['cpus']]
        directory = shlex.quote(lease['directory'])
        remote_command = ('cd ' + directory + ' && test -f claude-pinned && exec ' + shlex.join(args))
        remote = subprocess.Popen(ssh_args(config, compression, cipher, mac) + [remote_command],
                                  stdin=host.stdout if method == 'pipe' else subprocess.DEVNULL,
                                  stdout=host.stdin if method == 'pipe' else subprocess.DEVNULL,
                                  stderr=subprocess.PIPE)
        if method == 'tcp':
            info = ready(remote)
            host = start_endpoint('host', method, config['host'], info['port'], nonce, size,
                                  repeats, direction, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if host.stdout:
            host.stdout.close()
            host.stdout = None
        if host.stdin:
            host.stdin.close()
            host.stdin = None
        _, output = host.communicate(timeout=3600)
        _, errors = remote.communicate(timeout=120)
        result = rows_from(output, host.returncode)
        if remote.returncode:
            raise RuntimeError('card endpoint: ' + errors.decode(errors='replace')[-2000:])
        for row in result:
            row.update(compression=compression, cipher=cipher or 'negotiated', mac=mac or 'negotiated')
        return result
    finally:
        # A timeout never advances the matrix or force-kills a registered endpoint.
        # The lease/watchdog owns card lifetime; the lead inspects host driver state.
        alive = [p.pid for p in (host, remote) if p is not None and p.poll() is None]
        if alive:
            raise RuntimeError('STOP: endpoint cleanup uncertain; live host PIDs ' + str(alive))


def cygpath(path):
    path = Path(path).resolve()
    return '/cygdrive/' + path.drive[0].lower() + path.as_posix()[2:]


def native_files(config, lease, method, size, direction, check_event, repeats=20, compression=False, cipher=None, mac=None):
    """Actual legacy SCP or tar-over-SSH, with file IO and process startup timed."""
    exe = str(OUT / 'transfer-host.exe')
    local = OUT / 'payload.bin'
    remote_path = lease['directory'] + '/payload.bin'
    ssh = ssh_args(config, compression, cipher, mac)
    prefix = 'cd ' + shlex.quote(lease['directory']) + ' && test -f claude-pinned && exec ./transfer-card.mic '

    def payload(operation, remote):
        args = [operation, remote_path if remote else str(local), str(size), '0', lease['cpus'] if remote else '-']
        cmd = ssh + [prefix + shlex.join(args)] if remote else [exe] + args
        done = subprocess.run(cmd, env=ENV, capture_output=True, timeout=600, check=True)
        return json.loads(done.stdout)

    source = payload('generate', direction == 'down')
    result = []
    for rep in range(repeats):
        check_event()
        env = dict(ENV)
        if method == 'scp':
            # Reuse the strict SSH settings; SCP names cipher/MAC via -o too.
            options = ['-F', 'NUL', '-i', config['identity'], '-o', 'IdentitiesOnly=yes',
                       '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                       '-o', 'GlobalKnownHostsFile=NUL', '-o', 'UserKnownHostsFile=' + config['knownHosts'],
                       '-o', 'HostKeyAlgorithms=ssh-ed25519', '-o', 'ConnectTimeout=5',
                       '-o', 'Compression=' + ('yes' if compression else 'no')]
            if cipher:
                options += ['-o', 'Ciphers=' + cipher]
            if mac:
                options += ['-o', 'MACs=' + mac]
            target = 'root@' + config['host'] + ':' + remote_path
            files = [str(local), target] if direction == 'up' else [target, str(local)]
            env['S11_SCP_PREFIX'] = prefix + shlex.join(['measure', 'card', lease['cpus'], '--']) + ' '
            transport = ['C:/Windows/System32/OpenSSH/scp.exe', '-O', '-S', exe, *options, *files]
        else:
            tar = cygpath(TC / 'cygwin/bin/tar.exe')
            local_tar = shlex.join([tar, '-C', cygpath(OUT), '-cf' if direction == 'up' else '-xf', '-'])
            remote_tar = prefix + shlex.join(['measure', 'card', lease['cpus'], '--', 'tar',
                                              '-xf' if direction == 'up' else '-cf', '-'])
            if direction == 'up':
                local_tar += ' payload.bin'
            else:
                remote_tar += ' payload.bin'
            shell_ssh = [cygpath(ssh[0])] + ssh[1:]
            pipeline = (local_tar + ' | ' + shlex.join(shell_ssh + [remote_tar]) if direction == 'up'
                        else shlex.join(shell_ssh + [remote_tar]) + ' | ' + local_tar)
            transport = [str(TC / 'cygwin/bin/bash.exe'), '-o', 'pipefail', '-c', pipeline]
        done = subprocess.run([exe, 'measure', 'host', '-', '--', *transport], env=env,
                              capture_output=True, timeout=3600, check=True)
        times = {}
        for line in done.stderr.decode(errors='replace').splitlines():
            if line.startswith('{'):
                row = json.loads(line)
                if row.get('event') == 'process-time':
                    times[row['side']] = row
        if set(times) != {'host', 'card'}:
            raise RuntimeError('missing SCP/tar process timing: ' + done.stderr.decode(errors='replace')[-1000:])
        received = payload('inspect', direction == 'up')
        if received != source:
            raise RuntimeError('integrity mismatch in ' + method)
        elapsed = times['host']['seconds']
        result.append(dict(method=method, direction=direction, bytes=size, repeat=rep,
                           seconds=elapsed, MiB_s=size/1048576/elapsed, latency_us=elapsed*1e6,
                           host_cpu_seconds=times['host']['cpu_seconds'],
                           card_cpu_seconds=times['card']['cpu_seconds'],
                           card_seconds=times['card']['seconds'], sha256=received['sha256'],
                           integrity='match', compression=compression,
                           cipher=cipher or 'negotiated', mac=mac or 'negotiated',
                           timing_scope='process+file-io+ssh-startup; hashing excluded'))
        check_event()
    # Only the fixed host scratch payload is removed here; card_run owns remote cleanup.
    local.unlink(missing_ok=True)
    return result


def plan(args):
    """Yield the selected trial groups in the order the runner executes them."""
    for concurrency in args.concurrency:
        for load in args.loads:
            for method in args.methods:
                if concurrency == 2 and method in ('scp', 'tar'):
                    continue
                for size in args.sizes:
                    for direction in ('up', 'down'):
                        yield concurrency, load, method, size, direction, args.repeats


def run_native(args):
    if not args.lead_exclusive_turn:
        raise RuntimeError('lead must invoke --lead-exclusive-turn during the coordinated exclusive turn')
    config = json.loads(args.config.read_text(encoding='utf8'))
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', config['host']):
        raise RuntimeError('invalid host')
    output = OUT / 'results.jsonl'
    if output.exists():
        last = output.read_text(encoding='utf8').splitlines()[-1:]
        complete = last and json.loads(last[0]).get('event') == 'finished'
        if not complete and not args.acknowledge_prior_incomplete:
            raise RuntimeError('prior run incomplete: inspect bugcheck/dump and endpoint cleanup before --acknowledge-prior-incomplete')
    baseline = event_log()
    nonce = secrets.token_hex(16)
    card_log = (OUT / 'card-control.log').open('wb')
    card = None
    control = None
    control_lock = threading.Lock()
    heartbeat_stop = threading.Event()
    heartbeat_errors = []
    heartbeat_thread = None

    def exchange(value):
        with control_lock:
            control.sendall(value)
            if control.recv(1) != value:
                raise RuntimeError('lease control failure')

    def heartbeat():
        while not heartbeat_stop.wait(20):
            try:
                exchange(b'K')
            except BaseException as error:
                heartbeat_errors.append(str(error))
                return
    with output.open('w', encoding='utf8') as log:
        def record(row):
            log.write(json.dumps(row, sort_keys=True) + '\n')
            log.flush()

        def check_event():
            if heartbeat_errors:
                raise RuntimeError('lease heartbeat: ' + heartbeat_errors[0])
            current = event_log()
            record(dict(event='event-log-check', **current))
            if current != baseline:
                raise RuntimeError('new bugcheck or changed host boot; stop before next trial')

        record(dict(event='started', repeats=args.repeats, sizes=args.sizes,
                    loads=args.loads, concurrency=args.concurrency, methods=args.methods, **baseline))
        try:
            card = subprocess.Popen([sys.executable, str(args.project / 'tools/card_run'),
                                     '--config', str(args.config), '--benchmark', '--threads', '240',
                                     '--timeout', '43200', '--file', str(OUT / 'transfer-card.mic'),
                                     str(OUT / 'transfer-card.sh'), '0.0.0.0', '0', nonce],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            announcement = lease_ready(card, card_log, nonce)
            try:
                control = socket.create_connection((config['host'], announcement['port']), timeout=5)
            except OSError as error:
                raise RuntimeError('card lease listener unreachable (5 second connect deadline): ' + str(error)) from error
            control.settimeout(120)
            line = bytearray()
            while not line.endswith(b'\n'):
                part = control.recv(1)
                if not part or len(line) > 9000:
                    raise RuntimeError('invalid lease greeting')
                line.extend(part)
            lease = json.loads(line)
            if lease.get('nonce') != nonce or not isinstance(lease.get('directory'), str) or not LEASE_DIRECTORY.fullmatch(lease['directory']):
                raise RuntimeError('lease identity mismatch')
            if not re.fullmatch(r'\d+(,\d+){239}', lease.get('cpus', '')):
                raise RuntimeError('lease must own 240 CPUs')
            heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
            heartbeat_thread.start()
            # Read-only inventory in the exclusive turn; no config/MTU changes.
            probe = ('printf "SSH_SERVER\\n"; /usr/sbin/sshd -T 2>/dev/null | '
                     'grep -E "^(ciphers|macs|compression) "; '
                     'printf "MTU\\n"; cat /sys/class/net/mic0/mtu /sys/class/net/eth0/mtu 2>/dev/null; '
                     'printf "SCIF_LIBRARY\\n"; ls -l /usr/lib64/libscif.so.0; '
                     'printf "NFS\\n"; cat /proc/mounts; '
                     'printf "CLOCK_POLICY\\n"; cat /sys/devices/system/clocksource/clocksource0/current_clocksource '
                     '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null')
            probe_result = subprocess.run(ssh_args(config) + [probe], capture_output=True, timeout=30)
            record(dict(event='inventory', stdout=probe_result.stdout.decode(errors='replace'),
                        stderr=probe_result.stderr.decode(errors='replace'), returncode=probe_result.returncode))
            active_load = None
            for concurrency, load, method, size, direction, repeats in plan(args):
                if load != active_load:
                    exchange(b'I' if load == 'idle' else b'B')
                    active_load = load
                check_event()
                if method in ('scp', 'tar'):
                    for row in native_files(config, lease, method, size, direction, check_event,
                                            repeats, args.compression, args.cipher, args.mac):
                        row.update(load=load, concurrency=1, stream=0, repeats=repeats)
                        record(row)
                    continue
                # Workers already in flight finish; no new group after any error.
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                    trials = [pool.submit(native_trial, config, lease, args.host_address,
                                          method, size, direction, repeats, args.compression,
                                          args.cipher, args.mac) for _ in range(concurrency)]
                    for index, future in enumerate(trials):
                        for row in future.result():
                            row.update(load=load, concurrency=concurrency, stream=index, repeats=repeats)
                            record(row)
                check_event()
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=125)
            exchange(b'Q')
            control.close()
            control = None
            if card.wait(timeout=180):
                raise RuntimeError('card_run failed: see card-control.log')
            check_event()
            record(dict(event='finished'))
        except BaseException as error:
            record(dict(event='stopped', reason=str(error)))
            raise
        finally:
            # EOF makes the lease fail and lets card_run perform its guarded cleanup.
            heartbeat_stop.set()
            if control:
                control.shutdown(socket.SHUT_RDWR)
                control.close()
            # Once started, the drain owns the log through card_run cleanup.
            if card is None:
                card_log.close()
            else:
                drained = getattr(card, '_card_log_drained', None)
                if drained:
                    drained.wait()
                card_log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build')
    b.add_argument('--host-only', action='store_true')
    b.add_argument('--card-only', action='store_true')
    n = sub.add_parser('run')
    n.add_argument('--project', type=Path, default=PROJECT)
    n.add_argument('--config', type=Path, required=True)
    n.add_argument('--host-address', required=True, help='host IPv4 on existing mic virtual Ethernet')
    n.add_argument('--lead-exclusive-turn', action='store_true')
    n.add_argument('--acknowledge-prior-incomplete', action='store_true')
    n.add_argument('--methods', nargs='+', choices=METHODS, default=METHODS)
    n.add_argument('--repeats', type=int, default=20)
    n.add_argument('--sizes', nargs='+', choices=('4K', '1M', '64M', '1G'), default=('4K', '1M', '64M', '1G'))
    n.add_argument('--loads', nargs='+', choices=('idle', 'busy240'), default=('idle', 'busy240'))
    n.add_argument('--concurrency', nargs='+', type=int, choices=(1, 2), default=(1, 2))
    n.add_argument('--compression', action='store_true')
    n.add_argument('--cipher')
    n.add_argument('--mac')
    args = parser.parse_args()
    if args.action == 'run':
        if args.repeats < 1:
            parser.error('--repeats must be positive')
        size_values = dict(zip(('4K', '1M', '64M', '1G'), SIZES))
        args.sizes = tuple(size_values[value] for value in args.sizes)
    if args.action == 'build':
        build(args.host_only, args.card_only)
    else:
        run_native(args)


if __name__ == '__main__':
    main()
