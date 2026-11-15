"""List changed constant/stack vector reads in the saved S11-27 torture diff."""
import argparse
from collections import Counter
from pathlib import Path
import re

from s12_29_checks import broadcast_alignment


def reads(assembly):
    result = []
    for number, line in enumerate(assembly.splitlines(), 1):
        text = line.strip()
        # AT&T syntax: a vector read has memory before a destination register.
        # Include arithmetic, masked reads and folded broadcasts, not just mov.
        if (text.startswith('v')
                and re.search(r'(?:\.LC[^\s,]*\(%rip\)|[^\s,]*\(%(?:rsp|rbp)\))', text)
                and re.search(r'\),\s*%|\)\{[^}]+\},\s*%', text)):
            result.append((number, text))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diff', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    old_dir, new_dir = args.diff / 'old', args.diff / 'new'
    names = (args.diff / 'different.txt').read_text().splitlines()
    report = []
    changed_reads = 0
    for name in names:
        old = (old_dir / (name + '.s')).read_text()
        new = (new_dir / (name + '.s')).read_text()
        old_reads = Counter(text for _, text in reads(old))
        added = []
        for number, text in reads(new):
            if old_reads[text]:
                old_reads[text] -= 1
            else:
                added.append((number, text))
        if not added:
            continue
        changed_reads += len(added)
        report.append(name)
        failures = {int(re.search(r' line (\d+):', failure)[1]): failure
                    for failure in broadcast_alignment(new)}
        for number, text in added:
            report.append('  %d: %s' % (number, text))
            if number in failures:
                report.append('    CHECK: ' + failures[number])
    summary = ('Saved assembly: old=%d new=%d; different.txt=%d; '
               'added constant/stack vector reads=%d'
               % (len(list(old_dir.glob('*.s'))), len(list(new_dir.glob('*.s'))),
                  len(names), changed_reads))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(summary + '\n\n' + '\n'.join(report) + '\n')
    print(summary)
    print('Report: ' + str(args.report))


if __name__ == '__main__':
    main()
