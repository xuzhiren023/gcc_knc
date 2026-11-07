#!/usr/bin/env python3
"""S7-03 donor ABI contract (host inspection only; run through tools/run.py).

Without --candidate, check the existing static archive for the necessary donor
definitions: this is the red prerequisite while shared libgcc remains disabled.
With --candidate PATH, inspect an isolated linked candidate's real .dynsym,
including all default/compatibility versions and supported GCC 16 additions.
Neither mode builds, installs, or executes target code. An archive pass does
not establish symbol versions or satisfy the candidate acceptance criterion.
Source: docs/research/knc-libgcc-shared.md, sections 1-3 and split item 1.
"""
import argparse
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
FIXTURE = ROOT / 'tests/t2/knc-libgcc-donor.exports'
ADDITIONS = {
    '__divmodti4@@GCC_7.0.0',
    *(name + '@@GCC_14.0.0' for name in (
        '__hardcfr_check', '__strub_enter', '__strub_update', '__strub_leave',
        '__mulbitint3', '__divmodbitint4', '__fixsfbitint', '__fixdfbitint',
        '__fixtfbitint', '__floatbitintsf', '__floatbitintdf', '__floatbitinttf')),
}


def inspect(tool, *args):
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    exe = TC / ('cross/bin/k1om-mpss-linux-' + tool + ('.exe' if os.name == 'nt' else ''))
    return subprocess.check_output([str(exe), *map(str, args)], env=env, text=True)


def symbols(output, archive=False):
    """Keep external definitions, excluding UND imports and ABS version labels."""
    result = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].rstrip(':').isdigit():
            continue
        _, _, size, kind, binding, visibility, section, name = fields[:8]
        if (section in ('UND', 'ABS') or binding not in ('GLOBAL', 'WEAK')
                or (not archive and visibility not in ('DEFAULT', 'PROTECTED'))):
            continue
        result[name] = (kind, int(size, 0) if size.startswith('0x') else int(size))
    return result


def mismatches(expected, actual):
    errors = []
    for name, (kind, size) in sorted(expected.items()):
        if name not in actual:
            errors.append('missing or wrongly versioned ' + name)
        elif actual[name][0] != kind:
            errors.append('wrong symbol type ' + name)
        elif kind == 'OBJECT' and actual[name][1] != size:
            errors.append('wrong object size ' + name)
    return errors


def fixture():
    expected = {}
    for line in FIXTURE.read_text().splitlines():
        if line and not line.startswith('#'):
            name, kind, size = line.split()
            expected[name] = (kind, int(size))
    assert len(expected) == 153
    assert len({name.split('@')[0] for name in expected}) == 147
    assert sum('@@' not in name for name in expected) == 6
    assert expected['__cpu_model@@GCC_4.8.0'] == ('OBJECT', 16)
    return expected


def check_detector(expected):
    # Every fixture entry must matter, including the six nondefault aliases.
    assert not mismatches(expected, expected)
    for name in expected:
        changed = dict(expected)
        value = changed.pop(name)
        assert mismatches(expected, changed), name
        changed[name.split('@')[0] + '@@GCC_99.0.0'] = value
        assert mismatches(expected, changed), name
        changed = dict(expected)
        value = changed.pop(name)
        alternate = name.replace('@@', '@') if '@@' in name else name.replace('@', '@@')
        changed[alternate] = value
        assert mismatches(expected, changed), name
    changed = dict(expected)
    changed['__cpu_model@@GCC_4.8.0'] = ('OBJECT', 12)
    assert mismatches(expected, changed)
    print('PASS detector rejects missing/wrong-version/defaultness entries and wrong CPU size')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--candidate', type=Path, help='isolated candidate ELF shared library')
    group.add_argument('--archive', type=Path, default=SHARED / 'gcc-build/k1om-mpss-linux/libgcc/libgcc.a')
    args = parser.parse_args()
    expected = fixture()
    donor = symbols(inspect('readelf', '-W', '--dyn-syms', TC / 'sysroot/lib64/libgcc_s.so.1'))
    errors = mismatches(expected, donor)
    if errors or set(donor) != set(expected):
        raise RuntimeError('donor fixture differs from sysroot: ' + '; '.join(errors))
    print('PASS fixture matches sysroot: 153 pairs, 147 names, six aliases, 16-byte CPU object')
    check_detector(expected)
    if args.candidate:
        actual = symbols(inspect('readelf', '-W', '--dyn-syms', args.candidate))
        required = dict(expected)
        required.update({name: ('FUNC', 0) for name in ADDITIONS})
        errors = mismatches(required, actual)
        unexpected = set(actual) - set(required)
        errors.extend('unintended export ' + name for name in sorted(unexpected))
        print('candidate:', args.candidate)
        print('additional exports:', ' '.join(sorted(set(actual) - set(expected))))
    else:
        # Static objects cannot prove versions, but absent definitions are a
        # concrete ABI blocker independent of the intentional shared guard.
        # Static libgcc deliberately uses hidden definitions; they still count
        # for this prerequisite, unlike a candidate's external dynamic ABI.
        actual = symbols(inspect('readelf', '-W', '--syms', args.archive), archive=True)
        required = {name.split('@')[0] for name in expected}
        errors = ['archive lacks donor definition ' + name for name in sorted(required - set(actual))]
        print('archive prerequisite only:', args.archive)
    for error in errors:
        print('FAIL ' + error)
    print('%s S7-03 %s: %d mismatches' % (
        'FAIL' if errors else 'PASS', 'candidate ABI' if args.candidate else 'archive prerequisite', len(errors)))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
