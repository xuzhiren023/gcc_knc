#!/usr/bin/env python3
"""Join vectorizer reports to exclusive sampled source regions (S12-19).

PCs must refer to the sampled ELF, never a newly compiled executable. Unknown
source lines remain unmapped. Source-region bounds are supplied separately:
neither a hot function nor an assembly backedge proves a source-loop boundary.
Reason totals overlap when a loop has multiple blockers.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
import os
from pathlib import Path
import posixpath
import re
import subprocess

from code_census import DEVELOPMENT, local_path, validate_program


def source_path(value):
    """Normalize separators, but never merge files just by basename."""
    return posixpath.normpath(str(value).replace('\\', '/'))


def innermost(regions):
    """Select the unique smallest source interval; ambiguity stays unknown."""
    if not regions:
        return None
    regions = sorted(regions, key=lambda r: r['line_end'] - r['line_start'])
    first = regions[0]
    if any(not (r['line_start'] <= first['line_start']
                and first['line_end'] <= r['line_end'])
           or (r['line_start'], r['line_end']) ==
              (first['line_start'], first['line_end']) for r in regions[1:]):
        return None
    return first


def source_match(regions, filename, line):
    return innermost([r for r in regions if source_path(r['file']) ==
                      source_path(filename) and r['line_start'] <= line <= r['line_end']])


def parse_addr2line(text):
    """Read addr2line -a -f -C (without -i); retain unknown lines explicitly."""
    lines = text.splitlines()
    if len(lines) % 3:
        raise ValueError('expected addr2line -a -f -C triples')
    result = []
    for offset in range(0, len(lines), 3):
        address, function, location = lines[offset:offset + 3]
        if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
            raise ValueError('invalid addr2line address: ' + address)
        match = re.fullmatch(r'(.+):(\d+)(?: \(discriminator \d+\))?', location)
        result.append(dict(pc=int(address, 16), function=function,
                           file=match[1] if match else None,
                           line=int(match[2]) if match else 0))
    return result


def validate_regions(regions):
    ids = set()
    for r in regions:
        if r['id'] in ids:
            raise ValueError('duplicate region id: ' + r['id'])
        ids.add(r['id'])
        if r['kind'] not in ('loop', 'not a loop'):
            raise ValueError('source region needs an established kind')
        if not 0 < r['line_start'] <= r['line_end']:
            raise ValueError('invalid source bounds')


def regions_from_addr2line(text, source_regions, module):
    validate_regions(source_regions)
    mapped = {}
    for location in parse_addr2line(text):
        if not location['line'] or location['file'] == '??':
            continue
        region = source_match(source_regions, location['file'], location['line'])
        if region is None:
            continue
        item = mapped.setdefault(region['id'], dict(region, module=module, pc_ranges=[]))
        # A queried address supplies no evidence for an unqueried neighbor.
        item['pc_ranges'].append((location['pc'], location['pc'] + 1))
    for item in mapped.values():
        item['pc_ranges'] = sorted(set(item['pc_ranges']))
    return list(mapped.values())


DIAGNOSTIC = re.compile(r'^(.+):(\d+):(\d+): (missed|optimized|note):\s*(.*)$')


def diagnostics(text):
    for line in text.splitlines():
        match = DIAGNOSTIC.match(line)
        if match:
            yield dict(file=match[1], line=int(match[2]), column=int(match[3]),
                       severity=match[4], message=match[5])


def reason_for(message):
    """Recognize evidence, not hypothetical causes inferred from source code."""
    message = message.lower()
    # GCC tree-vect-loop.cc:7480,7652; ordered reductions are not generic FP sums.
    if 'in-order' in message and 'reduction' in message:
        return 'reduction order'
    if 'alias' in message:
        return 'alias'
    if any(s in message for s in ('strided load', 'strided store', 'unknown step',
                                  'unknown stride', 'not consecutive access')):
        return 'unknown stride'
    if 'control flow' in message:
        return 'control flow'
    # tree-vect-loop.cc:1865,2556, including the installed strict-FP sum report.
    if any(s in message for s in ('not profitable', 'costings may not be worthwhile',
                                  'cost model')):
        return 'cost model'
    if any(s in message for s in ('relevant stmt not supported', 'no vectype for stmt',
                                  'unsupported data-type', 'unsupported use in stmt',
                                  'statement clobbers memory')):
        return 'unsupported operation'
    return None


def samples_for(pc_text, program, variant='serial'):
    key = variant + '-' + program
    for line in pc_text.splitlines():
        fields = line.split(maxsplit=4)
        if fields and fields[0] == key:
            if len(fields) < 4 or not fields[3].startswith('tid='):
                raise ValueError('malformed PC row: ' + line)
            yield fields[1], int(fields[2], 16)


def triage_program(program, opt_info, regions, pc_text, cpu_seconds, variant='serial'):
    validate_program(program)
    validate_regions(regions)
    if not math.isfinite(cpu_seconds) or cpu_seconds < 0:
        raise ValueError('CPU seconds must be finite and nonnegative')
    reports = defaultdict(list)
    for report in diagnostics(opt_info):
        region = source_match(regions, report['file'], report['line'])
        if region is not None and report not in reports[region['id']]:
            reports[region['id']].append(report)
    counts = Counter()
    total = unmapped = 0
    for module, pc in samples_for(pc_text, program, variant):
        total += 1
        candidates = []
        for r in regions:
            ranges = r.get('pc_ranges')
            if ranges is None:
                ranges = [(r['start'], r['end'])]
            if r['module'] == module and any(start <= pc < end for start, end in ranges):
                candidates.append(r)
        # A PC shared across unrelated source files cannot establish ownership.
        region = (innermost(candidates) if len({source_path(r['file'])
                                               for r in candidates}) <= 1 else None)
        if region is None:
            unmapped += 1
        else:
            counts[region['id']] += 1
    rows = []
    for r in regions:
        count = counts[r['id']]
        if not count:
            continue
        evidence = reports[r['id']]
        reasons = sorted({reason_for(d['message']) for d in evidence
                          if d['severity'] == 'missed'} - {None})
        vectorized = any(d['severity'] == 'optimized' and re.match(
            r'(?:epilogue )?loop vectorized using ', d['message']) for d in evidence)
        if r['kind'] == 'not a loop':
            status, reasons = 'not a loop', []
        elif vectorized:
            status, reasons = 'vectorized', []
        else:
            status = 'missed-with-reason' if reasons else 'unknown'
        rows.append(dict(r, status=status, reasons=reasons, samples=count,
                         cpu_seconds=count / total * cpu_seconds, diagnostics=evidence))
    rows.sort(key=lambda r: (-r['samples'], r['id']))
    return dict(program=program, variant=variant, rows=rows, total_samples=total,
                cpu_seconds=cpu_seconds, unmapped_samples=unmapped,
                unmapped_cpu_seconds=unmapped / total * cpu_seconds if total else None)


def summarize(program_results):
    totals = defaultdict(lambda: dict(cpu_seconds=0.0, samples=0, loops=0))
    for result in program_results:
        for row in result['rows']:
            for reason in set(row['reasons']):
                totals[reason]['cpu_seconds'] += row['cpu_seconds']
                totals[reason]['samples'] += row['samples']
                totals[reason]['loops'] += 1
    return dict(reasons=sorted([dict(reason=k, **v) for k, v in totals.items()],
                              key=lambda r: (-r['cpu_seconds'], r['reason'])),
                total_samples=sum(r['total_samples'] for r in program_results),
                unmapped_samples=sum(r['unmapped_samples'] for r in program_results),
                reason_totals_are_nonadditive=True)


def query_sampled_elf(binary, pcs, addr2line, env):
    """Query only observed PCs in the frozen ELF; do not rebuild or execute it."""
    result = subprocess.run([str(addr2line), '-a', '-f', '-C', '-e', str(binary)],
                            input=''.join(hex(pc) + '\n' for pc in sorted(set(pcs))),
                            text=True, capture_output=True, env=env, check=True)
    return result.stdout


def audit_profiles(shared, output):
    """Check the prerequisite for the production source join, for all 14 programs.

    This is an input-coverage audit, not a loop classification or a substitute
    for opt-info collection. It opens only allowlisted frozen workload ELFs.
    """
    builds = json.loads((shared / 'S11-18/builds.json').read_text())
    profiles = json.loads((shared / 'S11-15/batch-attribution.json').read_text())
    pc_text = (shared / 'S11-15/batch-attribution-pcs.txt').read_text()
    pilot = (shared / 'S11-15/attribution-pcs.txt').read_text()
    addr2line = shared / 'toolchain/cross/bin/k1om-mpss-linux-addr2line.exe'
    env = dict(os.environ)
    env['PATH'] = str(shared / 'toolchain/cygwin/bin') + os.pathsep + env.get('PATH', '')
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for program in DEVELOPMENT:
        validate_program(program)
        available = [r for r in profiles if r['key'] in
                     ('serial-' + program, 'openmp-' + program)]
        if program == 'PB-gemm':
            # Pilot PCs already use ELF addresses (s11_15_attribution.py).
            pcs = [int(fields[2], 16) for line in pilot.splitlines()
                   if len(fields := line.split()) >= 3 and fields[1] == 'gemm']
            available = [dict(key='pilot-PB-gemm', samples=len(pilot.splitlines()),
                              pilot_pcs=pcs)]
        if not available:
            results.append(dict(program=program, profile=None,
                                status='missing profile', total_samples=0))
            continue
        for profile in available:
            key = profile['key']
            variant = key.split('-', 1)[0]
            if variant == 'pilot':
                binary = shared / 'S11-15/gemm'
                pcs = profile['pilot_pcs']
            else:
                matches = [r for r in builds if not r.get('held_out')
                           and r['program'] == program and r['compiler'] == 'gcc-knc'
                           and r['variant'] == variant and r['check'] == 'pass']
                if len(matches) != 1:
                    raise ValueError('need one frozen build: ' + key)
                binaries = [local_path(p) for p in matches[0]['files']
                            if local_path(p).name == 'workload']
                if len(binaries) != 1:
                    raise ValueError('need one sampled workload ELF: ' + key)
                binary = binaries[0]
                pcs = [pc for module, pc in samples_for(pc_text, program, variant)
                       if module == 'profile-workload']
            for part in source_path(binary).split('/'):
                if part.lower() in ('pb-adi', 'adi', 'pb-durbin', 'durbin', 'bzip2'):
                    raise ValueError('held-out path refused')
            text = query_sampled_elf(binary, pcs, addr2line, env)
            (output / (key + '.addr2line')).write_text(text)
            locations = parse_addr2line(text)
            known = {r['pc'] for r in locations if r['line'] > 0 and r['file'] != '??'}
            result = dict(program=program, profile=key, binary=str(binary),
                          total_samples=profile['samples'], workload_samples=len(pcs),
                          unique_workload_pcs=len(set(pcs)),
                          source_mapped_workload_samples=sum(pc in known for pc in pcs),
                          status='source lines available' if known else 'no source lines',
                          issues=profile.get('issues', []),
                          cpu_account=profile.get('account'),
                          hot_functions=profile.get('functions', []))
            results.append(result)
            print(f'{key}: {result["source_mapped_workload_samples"]}/{len(pcs)} '
                  f'workload samples have source lines; {result["status"]}')
    (output / 'profile-coverage.json').write_text(json.dumps(results, indent=2) + '\n')
    for r in results:
        if r['status'] == 'missing profile':
            print(r['program'] + ': missing profile')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    audit = commands.add_parser('audit', help='audit frozen S11-15 source mapping')
    root = Path(__file__).resolve().parents[1]
    shared = root.parent / '_shared' if root.parent.name == '.work' else root / '.work/_shared'
    audit.add_argument('--shared', type=Path, default=shared)
    audit.add_argument('--output', type=Path, default=shared / 'S12-19')
    join = commands.add_parser('join', help='join established regions and captured diagnostics')
    join.add_argument('--program', required=True, choices=DEVELOPMENT)
    join.add_argument('--variant', choices=('serial', 'openmp'), default='serial')
    join.add_argument('--opt-info', required=True, type=Path)
    join.add_argument('--regions', required=True, type=Path,
                      help='JSON array of source regions with bounds and kind')
    join.add_argument('--addr2line', required=True, type=Path,
                      help='-a -f -C output from the sampled ELF')
    join.add_argument('--module', default='profile-workload')
    join.add_argument('--pcs', required=True, type=Path)
    join.add_argument('--cpu-seconds', required=True, type=float)
    join.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'audit':
        audit_profiles(args.shared, args.output)
    else:
        regions = regions_from_addr2line(args.addr2line.read_text(),
                                        json.loads(args.regions.read_text()), args.module)
        result = triage_program(args.program, args.opt_info.read_text(), regions,
                                args.pcs.read_text(), args.cpu_seconds, args.variant)
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
