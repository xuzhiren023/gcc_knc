"""S2-07 static-runtime T2 lint/link and native donor comparison."""
import re
import subprocess
import sys
from pathlib import Path


def t2(runner):
    runtime = runner.gcc_build / 'k1om-mpss-linux/libgcc'
    files = [runtime / name for name in ('libgcc.a', 'crtbegin.o', 'crtend.o')]
    lint = runner.command(sys.executable, runner.root / 'tools/knc_lint',
                          *files, check=False)
    runner.say(lint.stdout)
    runner.result('t2 every libgcc archive member and CRT object lint',
                  [lint.stdout[-2200:]] if lint.returncode else [])
    for tag in ('gcc16', 'donor'):
        link(runner, tag)


def link(runner, tag):
    out = runner.tc.parent / 'tmp/S2-07'
    out.mkdir(parents=True, exist_ok=True)
    source = runner.root / 'tests/t2/knc-libgcc.c'
    cc, flags = ((runner.cc, runner.cc_flags)
                 if tag == 'gcc16' else (runner.tool('gcc'), []))
    elf = out / (tag + '-libgcc.mic')
    link = runner.command(cc, *flags, '-O2', '-fno-builtin', '-ffp-contract=off',
                          '-v', '-Wl,--trace', source, '-o', elf, check=False)
    runner.say(link.stdout)
    failures = [link.stdout[-2200:]] if link.returncode else []
    if not failures and tag == 'gcc16':
        symbols = runner.command(runner.tool('nm'), '--defined-only', elf)
        declarations = ' '.join(re.findall(r'extern[^;]+;', source.read_text()))
        for name in set(re.findall(r'\b(__\w+)\(', declarations)):
            if not re.search(r'\bT\s+' + name + r'$', symbols, re.M):
                failures.append('missing linked helper ' + name)
    runner.result('t2 ' + tag + ' integer/soft-fp helpers', failures)


def native():
    root = Path(__file__).resolve().parents[1]
    project = root.parent.parent if root.parent.name == '.work' else root
    out = project / '.work/_shared/tmp/S2-07'
    outputs = []
    for tag in ('donor', 'gcc16'):
        run = subprocess.run([sys.executable, str(root / 'tools/card_run'),
                              '--timeout', '30', str(out / (tag + '-libgcc.mic'))],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(run.stdout, end='', flush=True)
        if run.returncode:
            return run.returncode
        outputs.append([line for line in run.stdout.splitlines() if line.startswith('libgcc ')])
    if len(outputs[0]) != 5 or outputs[0] != outputs[1]:
        print('FAIL native libgcc donor comparison')
        return 1
    print('PASS native libgcc: all integer and soft-fp results match donor')
    return 0


if __name__ == '__main__':
    raise SystemExit(native())
