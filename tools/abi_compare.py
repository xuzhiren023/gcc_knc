#!/usr/bin/env python3
"""Does a GCC 16 libstdc++ export everything the donor's does? (S9-02, S9-03)

    python tools/abi_compare.py [--library LIBSTDC++.so.6] [--baseline baseline_symbols.txt]

Compares the dynamic symbol table of the donor libstdc++.so.6.0.21 (GCC 5.1, card sysroot), read
with the k1om readelf, against a built library, an ABI baseline in extract_symvers form
(FUNC:name@@ver, OBJECT:size:name@@ver, TLS:size:name@@ver), or both. A donor symbol is present
when the other side exports its name under the same version node, default (@@) or not (@): GCC 16
keeps condition_variable::wait@GLIBCXX_3.4.11 beside a newer default. Static, host only. Prints
every donor symbol that is missing and every object or TLS size that differs; exit 1 if any.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
READELF = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-readelf'
DONOR = SHARED / 'toolchain/sysroot/usr/lib64/libstdc++.so.6.0.21'
NODES = ('GLIBCXX', 'CXXABI')


def library_symbols(library):
    """{(name, version): (type, size)} for LIBRARY's defined, versioned libstdc++ symbols."""
    text = subprocess.run([str(READELF), '-W', '--dyn-syms', str(library)], stdout=subprocess.PIPE,
                          universal_newlines=True, check=True).stdout
    symbols = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 8 or not parts[0].endswith(':') or parts[6] == 'UND':
            continue
        name, _, version = parts[7].partition('@')
        version = version.lstrip('@')
        if version.startswith(NODES):
            symbols[(name, version)] = (parts[3], int(parts[2]))
    return symbols


def baseline_symbols(baseline):
    """The same map for an extract_symvers baseline file."""
    symbols = {}
    for line in Path(baseline).read_text().splitlines():
        match = re.match(r'^(FUNC|OBJECT|TLS):(?:(\d+):)?([^@:]+)@@?([A-Z0-9_.]+)$', line.strip())
        if match and match.group(4).startswith(NODES):
            symbols[(match.group(3), match.group(4))] = (match.group(1), int(match.group(2) or 0))
    return symbols


def compare(donor, new):
    """Donor symbols NEW lacks, and donor objects whose size differs in NEW."""
    missing = sorted(key for key in donor if key not in new)
    sizes = sorted(key for key in donor if key in new and donor[key][0] in ('OBJECT', 'TLS')
                   and new[key][1] and donor[key][1] != new[key][1])
    return missing, sizes


def report(label, donor, new):
    missing, sizes = compare(donor, new)
    print('%s: %d versioned symbols; donor symbols missing: %d; size differences: %d'
          % (label, len(new), len(missing), len(sizes)))
    for name, version in missing:
        print('  missing %s@%s %s:%d' % (name, version, *donor[(name, version)]))
    for name, version in sizes:
        print('  size %s@%s %d->%d' % (name, version, donor[(name, version)][1], new[(name, version)][1]))
    return not missing and not sizes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    if not args.library and not args.baseline:
        parser.error('give --library, --baseline or both')
    donor = library_symbols(DONOR)
    print('donor %s: %d versioned symbols' % (DONOR.name, len(donor)))
    ok = True
    if args.library:
        ok &= report('library ' + args.library.name, donor, library_symbols(args.library))
    if args.baseline:
        ok &= report('baseline ' + args.baseline.name, donor, baseline_symbols(args.baseline))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
