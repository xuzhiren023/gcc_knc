"""S9-13 -mknc-card=MODEL and -mknc-card=native (T1).

    python tools/run.py --name S9-13-t1 -- python tools/check.py t1 --compiler gcc16 --knc-card

Driver only (-###): each model and card name gives its prefetch --params on
the cc1 line, an explicit --param wins, plain -march=knc adds none, and the
option never reaches cc1.  -mknc-card=native reads fixture trees written
here, through GCC_KNC_CARD_ROOT: a 57-, 60- and 61-core card's /proc, an
MPSS host with one card and with two different cards (/sys/class/mic), and
an empty tree.  Values are in docs/gcc-knc-flags.md.
"""
import re
import subprocess

L2, L1 = 'knc-prefetch-l2-distance', 'knc-prefetch-l1-distance'
VALUES = {'generic': (32, 16), '3100': (23, 16), '5100': (29, 16), '7100': (32, 16)}
ALIASES = {'3110P': '3100', '3115A': '3100', '3120A': '3100', '3120P': '3100',
           '5110P': '5100', '5120D': '5100',
           '7110P': '7100', '7110X': '7100', '7120P': '7100', '7120X': '7100',
           '7120A': '7100', '7120D': '7100', '7120': '7100'}


def card_tree(root, cores, mem_kb):
    (root / 'proc').mkdir(parents=True, exist_ok=True)
    cpus = []
    for n in range(cores * 4):
        # Linux on KNC numbers cpu 0 on the last core (the OS core).
        core = cores - 1 if n == 0 or n > (cores - 1) * 4 else (n - 1) // 4
        cpus.append('processor\t: %d\nvendor_id\t: GenuineIntel\ncpu family\t: 11\n'
                    'model\t\t: 1\nmodel name\t: 0b/01\nphysical id\t: 0\n'
                    'core id\t\t: %d\ncpu cores\t: %d\n' % (n, core, cores))
    (root / 'proc/cpuinfo').write_text('\n'.join(cpus) + '\n')
    (root / 'proc/meminfo').write_text('MemTotal:       %d kB\nMemFree:        1024 kB\n'
                                       % mem_kb)


def host_tree(root, skus):
    (root / 'proc').mkdir(parents=True, exist_ok=True)
    (root / 'proc/cpuinfo').write_text('processor\t: 0\nvendor_id\t: GenuineIntel\n'
                                       'cpu family\t: 6\nmodel\t\t: 63\ncore id\t\t: 0\n\n')
    (root / 'proc/meminfo').write_text('MemTotal:       65536000 kB\n')
    for i, sku in enumerate(skus):
        mic = root / 'sys/class/mic' / ('mic%d' % i)
        mic.mkdir(parents=True, exist_ok=True)
        (mic / 'family').write_text('x100\n')
        (mic / 'sku').write_text(sku + '\n')
        (mic / 'state').write_text('online\n')


def t1(runner):
    out = runner.out
    source = out / 'knc-card.c'
    source.write_text('int knc_card_x;\n')
    base = [str(runner.cc), *runner.cc_flags, '--sysroot=' + str(runner.sysroot)]
    trees = out / 'knc-card-trees'
    card_tree(trees / 'card57', 57, 5_900_000)
    card_tree(trees / 'card60', 60, 7_800_000)
    card_tree(trees / 'card61', 61, 15_900_000)
    host_tree(trees / 'host1', ['C0-7120 P/A/X/D'])
    host_tree(trees / 'host2', ['C0-7120 P/A/X/D', 'C0-5110P'])
    (trees / 'none').mkdir(parents=True, exist_ok=True)

    def run(*args, root='none'):
        env = dict(runner.env)
        env['GCC_KNC_CARD_ROOT'] = str(trees / root)
        return subprocess.run([*base, *map(str, args), '-###', '-c', str(source)], env=env,
                              cwd=out, text=True, errors='replace', stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)

    def params(shown):
        """(l2, l1) as cc1 takes them (last wins; None if absent), or a failure."""
        cc1 = [line for line in shown.stderr.splitlines() if '/cc1' in line or '\\cc1' in line]
        if shown.returncode or not cc1:
            return 'exit %d %s' % (shown.returncode, shown.stderr[-600:])
        words = [a or b for a, b in re.findall(r'"([^"]*)"|(\S+)', cc1[0])]
        if any(w.startswith('-mknc-card') for w in words):
            return 'cc1 sees -mknc-card: ' + cc1[0][-400:]
        found = {}
        for word in words:
            match = re.fullmatch(r'--param=(knc-prefetch-l[12]-distance)=(\d+)', word)
            if match:
                found[match[1]] = int(match[2])
        return found.get(L2), found.get(L1)

    def expect(failures, case, shown, want, note=False):
        got = params(shown)
        if got != want:
            failures.append('%s: --params %r, want %r' % (case, got, want))
        if note != ('note:' in shown.stderr and 'knc-card' in shown.stderr):
            failures.append('%s: note %s: %r' % (case, 'missing' if note else 'present',
                                                 shown.stderr[:300]))

    failures = []
    expect(failures, 'plain -march=knc', run('-O2', '-march=knc'), (None, None))
    for model, want in VALUES.items():
        expect(failures, '-mknc-card=' + model, run('-O2', '-mknc-card=' + model), want)
    for alias, model in ALIASES.items():
        expect(failures, '-mknc-card=' + alias, run('-O2', '-mknc-card=' + alias), VALUES[model])
    expect(failures, 'last -mknc-card wins', run('-mknc-card=3100', '-mknc-card=5100'),
           VALUES['5100'])
    expect(failures, '--param after', run('-mknc-card=3100', '--param', L2 + '=40'),
           (40, 16))
    expect(failures, '--param= before', run('--param=%s=8' % L1, '-mknc-card=5100'), (29, 8))
    for case, args in (('unknown model', ['-mknc-card=9999']),
                       ('-march=x86-64', ['-mknc-card=7100', '-march=x86-64'])):
        shown = run(*args)
        if shown.returncode == 0 or 'knc-card' not in shown.stderr:
            failures.append('%s not rejected: exit %d %s'
                            % (case, shown.returncode, shown.stderr[-300:]))
    runner.result('t1 -mknc-card models, card names and explicit --param', failures)

    failures = []
    for root, model in (('card57', '3100'), ('card60', '5100'), ('card61', '7100'),
                        ('host1', '7100')):
        expect(failures, 'native on ' + root, run('-mknc-card=native', root=root),
               VALUES[model])
    expect(failures, 'native, nothing found', run('-mknc-card=native'), VALUES['generic'],
           note=True)
    shown = run('-mknc-card=native', root='host2')
    if (shown.returncode == 0 or not all(s in shown.stderr for s in ('7100', '5100'))
            or '-mknc-card=' not in shown.stderr):
        failures.append('native on two different cards: exit %d %s'
                        % (shown.returncode, shown.stderr[-300:]))
    expect(failures, '-mphinix detects', run('-mphinix', root='card60'), VALUES['5100'])
    expect(failures, '-mphinix -mknc-card=3100', run('-mphinix', '-mknc-card=3100',
                                                     root='card61'), VALUES['3100'])
    runner.result('t1 -mknc-card=native detection', failures)
