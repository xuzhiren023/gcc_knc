#!/usr/bin/env python3
"""Join vectorizer reports to exclusive sampled source regions (S12-19).

PCs must refer to the sampled ELF, never a newly compiled executable. Unknown
source lines remain unmapped. Source-region bounds are supplied separately:
neither a hot function nor an assembly backedge proves a source-loop boundary.
Reason totals overlap when a loop has multiple blockers.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import posixpath
import re
import subprocess

from code_census import DEVELOPMENT, local_path, validate_program


@lru_cache(maxsize=8192)
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


def source_lookup(regions):
    """Index a fixed region set; repeated diagnostics commonly share a location."""
    files = defaultdict(list)
    for region in regions:
        files[source_path(region['file'])].append(region)

    @lru_cache(maxsize=None)
    def lookup(filename, line):
        return innermost([r for r in files.get(source_path(filename), ())
                          if r['line_start'] <= line <= r['line_end']])
    return lookup


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
                                  'statement clobbers memory', 'unsupported slp instances')):
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


def triage_program(program, opt_info, regions, pc_text, cpu_seconds, variant='serial',
                   include_unsampled=False):
    validate_program(program)
    validate_regions(regions)
    if not math.isfinite(cpu_seconds) or cpu_seconds < 0:
        raise ValueError('CPU seconds must be finite and nonnegative')
    reports = defaultdict(list)
    lookup = source_lookup(regions)
    for report in diagnostics(opt_info):
        region = lookup(report['file'], report['line'])
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
        if not count and not include_unsampled:
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
                         cpu_seconds=count / total * cpu_seconds if total else None,
                         diagnostics=evidence))
    rows.sort(key=lambda r: (-r['samples'], r['id']))
    return dict(program=program, variant=variant, rows=rows, total_samples=total,
                cpu_seconds=cpu_seconds, unmapped_samples=unmapped,
                unmapped_cpu_seconds=unmapped / total * cpu_seconds if total else None)


def summarize(program_results):
    totals = defaultdict(lambda: dict(cpu_seconds=0.0, samples=0, loops=0))
    for result in program_results:
        for row in result['rows']:
            if not row['samples']:
                continue
            for reason in set(row['reasons']):
                if row['cpu_seconds'] is None:
                    continue
                totals[reason]['cpu_seconds'] += row['cpu_seconds']
                totals[reason]['samples'] += row['samples']
                totals[reason]['loops'] += 1
    return dict(reasons=sorted([dict(reason=k, **v) for k, v in totals.items()],
                              key=lambda r: (-r['cpu_seconds'], r['reason'])),
                total_samples=sum(r['total_samples'] for r in program_results),
                unmapped_samples=sum(r['unmapped_samples'] for r in program_results),
                reason_totals_are_nonadditive=True)


def query_sampled_elf(binary, pcs, addr2line, env):
    """Query observed PCs in the frozen ELF or identity-checked debug companion."""
    result = subprocess.run([str(addr2line), '-a', '-f', '-C', '-e', str(binary)],
                            input=''.join(hex(pc) + '\n' for pc in sorted(set(pcs))),
                            text=True, capture_output=True, env=env, check=True)
    if result.stderr.strip():
        raise RuntimeError('addr2line diagnostics: ' + result.stderr.strip())
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


def source_loops(filename, text):
    """Lexical loop bounds, never backedge envelopes or whole-function guesses.

    Handles structured free-form Fortran DO and C-family balanced statements.
    Macro expansions and unbalanced/ambiguous constructs remain unestablished.
    No source text is copied into the output.
    """
    filename = source_path(filename)
    bounds = []
    if filename.lower().endswith('.f90'):
        stack = []
        for number, line in enumerate(text.splitlines(), 1):
            line = line.split('!', 1)[0].strip().lower()
            start = re.match(r'^(?:\w+\s*:\s*)?do\b\s*(\d+)?', line)
            if start:
                stack.append((number, start[1]))
            if re.match(r'^end\s*do\b', line) and stack:
                first, _ = stack.pop()
                bounds.append((first, number))
            label = re.match(r'^(\d+)\s+', line)
            while label and stack and stack[-1][1] == label[1]:
                first, _ = stack.pop()
                bounds.append((first, number))
    else:
        # Preserve newlines while excluding comments, string literals and directives.
        pattern = r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|^[ \t]*\#(?:[^\n]*\\\n)*[^\n]*'
        clean = re.sub(pattern, lambda m: re.sub(r'[^\n]', ' ', m[0]), text, flags=re.M)
        newlines = [m.start() for m in re.finditer('\n', clean)]
        tokens = [(m[0], bisect_right(newlines, m.start()) + 1)
                  for m in re.finditer(r'\w+|[^\s]', clean)]
        pairs, stack = {}, []
        for i, (token, _) in enumerate(tokens):
            if token in ('(', '{', '['):
                stack.append(i)
            elif token in (')', '}', ']'):
                if not stack or tokens[stack[-1]][0] != {')': '(', '}': '{', ']': '['}[token]:
                    return []
                first = stack.pop()
                pairs[first] = i
        if stack:
            return []
        def statement_end(i):
            if i >= len(tokens):
                raise ValueError('missing statement')
            token = tokens[i][0]
            if token == '{':
                return pairs[i]
            if token in ('for', 'while', 'if', 'switch'):
                if tokens[i + 1][0] != '(':
                    raise ValueError('macro condition')
                end = statement_end(pairs[i + 1] + 1)
                if token == 'if' and end + 1 < len(tokens) and tokens[end + 1][0] == 'else':
                    end = statement_end(end + 2)
                return end
            if token == 'do':
                end = statement_end(i + 1)
                if tokens[end + 1][0] != 'while':
                    raise ValueError('incomplete do loop')
                return pairs[end + 2] + 1
            while i < len(tokens):
                if tokens[i][0] == ';':
                    return i
                if tokens[i][0] in ('}', '{'):
                    raise ValueError('unknown statement')
                i = pairs.get(i, i) + 1
            raise ValueError('unterminated statement')
        tails = set()
        for i, (token, line) in enumerate(tokens):
            if token not in ('for', 'while', 'do') or i in tails:
                continue
            try:
                end = statement_end(i)
                if token == 'do':
                    tails.add(statement_end(i + 1) + 1)
                bounds.append((line, tokens[end][1]))
            except (ValueError, KeyError, IndexError, RecursionError):
                continue
    return [dict(id=f'{filename}:{first}-{last}', file=filename,
                 line_start=first, line_end=last, kind='loop')
            for first, last in sorted(set(bounds))]


def analyze_collection(shared, output, programs, resume=False):
    """Rank observed loops only after the frozen/debug .text identity gate."""
    profiles = {r['key']: r for r in json.loads(
        (shared / 'S11-15/batch-attribution.json').read_text())}
    batch = (shared / 'S11-15/batch-attribution-pcs.txt').read_text()
    env = dict(os.environ)
    env['PATH'] = str(shared / 'toolchain/cygwin/bin') + os.pathsep + env.get('PATH', '')
    results = []
    for program in programs:
        validate_program(program)
        for variant in ('serial', 'openmp'):
            directory = output / 'debug' / (variant + '-' + program)
            if not (directory / 'collection.json').exists():
                continue
            if resume and (directory / 'triage.json').exists():
                results.append(json.loads((directory / 'triage.json').read_text()))
                print(variant + '-' + program + ': reusing completed analysis', flush=True)
                continue
            capture = json.loads((directory / 'collection.json').read_text())
            if capture['program'] != program or capture['variant'] != variant:
                raise ValueError('collection identity mismatch')
            opt = Path(capture['opt_info']).read_text(errors='replace')
            regions = []
            for filename in capture['sources']:
                regions.extend(source_loops(filename, local_path(filename).read_text(errors='replace')))
            # A compiler loop-site diagnostic is also positive loop evidence.
            # Use only that single line when lexical bounds are unavailable;
            # never extend it across neighboring lines or an entire function.
            known_sources = set(capture['sources'])
            for d in diagnostics(opt):
                if (d['file'] in known_sources and
                    (d['message'] == "couldn't vectorize loop" or
                     re.match(r'(?:epilogue )?loop vectorized using ', d['message'])) and
                        source_match(regions, d['file'], d['line']) is None):
                    regions.append(dict(id=f'{d["file"]}:{d["line"]}-site', file=d['file'],
                        line_start=d['line'], line_end=d['line'], kind='loop',
                        boundary_evidence='compiler loop site only'))
            profile = profiles.get(capture['key'])
            pc_text = batch
            if program == 'PB-gemm':
                # Pilot: retain every sample in the denominator, including libraries.
                pilot = (shared / 'S11-15/attribution-pcs.txt').read_text()
                pc_text = '\n'.join('serial-PB-gemm ' + ('profile-workload' if f[1] == 'gemm' else f[1])
                                    + ' ' + f[2] + ' tid=pilot'
                                    for line in pilot.splitlines() if len(f := line.split()) >= 3)
                # Nominal sampled time, not a fabricated CPU-account total.
                profile = dict(key='pilot-PB-gemm', account=None,
                               issues=['six-launch pilot; time uses nominal 10 ms per sample'])
            samples = list(samples_for(pc_text, program, variant)) if profile else []
            cpu = (profile['account']['user'] + profile['account']['system']
                   if profile and profile.get('account') else len(samples) * .01)
            locations = []
            if capture['text_equal'] and samples:
                addr = query_sampled_elf(Path(capture['debug']),
                    [pc for module, pc in samples if module == 'profile-workload'],
                    shared / 'toolchain/cygwin/bin/addr2line.exe', env)
                (directory / 'sampled.addr2line').write_text(addr)
                locations = parse_addr2line(addr)
                mapped = regions_from_addr2line(addr, regions, 'profile-workload')
            else:
                mapped = []
            mapped_by_id = {r['id']: r for r in mapped}
            regions = [mapped_by_id.get(r['id'], dict(r, module='profile-workload', pc_ranges=[]))
                       for r in regions]
            # Straight-line attribution is deliberately explicit and conservative:
            # only return statements outside established loops, never an entire file.
            for loc in locations:
                if not loc['line'] or loc['file'] == '??' or source_match(regions, loc['file'], loc['line']):
                    continue
                filename = source_path(loc['file'])
                if filename not in capture['sources']:
                    continue
                lines = local_path(filename).read_text(errors='replace').splitlines()
                if loc['line'] <= len(lines) and re.fullmatch(
                        r'\s*return(?:\s+[0-9]+)?\s*;?\s*', lines[loc['line'] - 1]):
                    rid = filename + ':return-' + str(loc['line'])
                    found = next((r for r in regions if r['id'] == rid), None)
                    if found:
                        found['pc_ranges'].append((loc['pc'], loc['pc'] + 1))
                    else:
                        regions.append(dict(id=rid, file=filename, line_start=loc['line'],
                            line_end=loc['line'], kind='not a loop', module='profile-workload',
                            pc_ranges=[(loc['pc'], loc['pc'] + 1)]))
            result = triage_program(program, opt, regions, pc_text if profile else '', cpu,
                                    variant, include_unsampled=True)
            result.update(text_equal=capture['text_equal'], profile=profile,
                          static_only=not any(r['samples'] for r in result['rows']),
                          observed_strides=None, observed_masks=None)
            # Unmatched diagnostics are evidence too; never silently discard them.
            lookup = source_lookup(regions)
            result['unmatched_diagnostics'] = [d for d in diagnostics(opt)
                if lookup(d['file'], d['line']) is None]
            result['static_reason_loops'] = dict(Counter(reason for row in result['rows']
                                                         for reason in row['reasons']))
            (directory / 'triage.json').write_text(json.dumps(result, indent=2) + '\n')
            results.append(result)
            print(f'{capture["key"]}: {result["total_samples"] - result["unmapped_samples"]}'
                  f'/{result["total_samples"]} samples mapped; {len(regions)} source loops', flush=True)
    summary = summarize(results)
    # Zero sample loops are static evidence, not a measured zero-cost opportunity.
    summary['reasons'] = [r for r in summary['reasons'] if r['samples']]
    (output / 'triage-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_tables(results, summary, output / 'rankings.md')
    return results


def write_tables(results, summary, path):
    text = ['# Development corpus vectorization triage', '',
            'Time is sampled CPU time, not wall time or predicted speedup. Reasons overlap.',
            'PCs with failed executable identity or unknown source ownership stay unmapped.',
            'Static-only rows have no sampled-time rank. Dynamic strides/masks were not captured.', '',
            '| Reason | Sampled CPU seconds | Samples |', '| --- | ---: | ---: |']
    for r in summary['reasons']:
        text.append(f'| {r["reason"]} | {r["cpu_seconds"]:.4f} | {r["samples"]} |')
    if not summary['reasons']:
        text.append('| No attributable missed time | unavailable | unavailable |')
    for result in results:
        text += ['', '## ' + result['variant'] + '-' + result['program'], '',
                 f'.text identical: {result["text_equal"]}; samples: {result["total_samples"]}; '
                 f'unmapped: {result["unmapped_samples"]}.', '',
                 '| Source loop | Status | Reasons | Samples | CPU seconds |',
                 '| --- | --- | --- | ---: | ---: |']
        for row in result['rows']:
            if not row['samples']:
                continue
            label = Path(row['file']).name + ':' + str(row['line_start'])
            text.append(f'| {label} | {row["status"]} | {", ".join(row["reasons"])} | '
                        f'{row["samples"]} | {row["cpu_seconds"]:.4f} |')
        if not any(r['samples'] for r in result['rows']):
            text.append('| No attributable source loops | unknown | | unavailable | unavailable |')
        functions = (result.get('profile') or {}).get('functions', [])
        if functions:
            text += ['', 'Existing hot functions (no implied source-loop ownership):', '',
                     '| Function | Samples |', '| --- | ---: |']
            for function in functions[:5]:
                text.append(f'| {function["name"]} | {function["samples"]} |')
        text += ['', 'Static missed reasons (loop counts, not time):', '',
                 '| Reason | Loops |', '| --- | ---: |']
        for reason, count in sorted(result['static_reason_loops'].items(), key=lambda p: (-p[1], p[0])):
            text.append(f'| {reason} | {count} |')
        text += ['', 'Static loop inventory (source order; no time rank):', '',
                 '| Source loop | Status | Reasons |', '| --- | --- | --- |']
        for row in sorted(result['rows'], key=lambda r: (r['file'], r['line_start'], r['line_end'])):
            if row['kind'] == 'loop' and row['diagnostics']:
                label = Path(row['file']).name + ':' + str(row['line_start'])
                text.append(f'| {label} | {row["status"]} | {", ".join(row["reasons"])} |')
    path.write_text('\n'.join(text) + '\n')


def report_collection(output, programs):
    """Render existing analysis without recompiling or repeating source attribution."""
    results = []
    for program in programs:
        validate_program(program)
        for variant in ('serial', 'openmp'):
            path = output / 'debug' / (variant + '-' + program) / 'triage.json'
            if path.exists():
                results.append(json.loads(path.read_text()))
    summary = summarize(results)
    (output / 'triage-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_tables(results, summary, output / 'rankings.md')
    print(f'{len(results)} program/variant tables written to {output / "rankings.md"}')


def cygpath(path):
    value = source_path(Path(path).resolve())
    return '/cygdrive/' + value[0].lower() + value[2:] if value[1:3] == ':/' else value


def collect_debug(shared, output, programs, resume=False):
    """Replay frozen compiler commands, changing only output paths and debug/report flags.

    Do not use the corpus staging entry point: it also stages sealed programs.
    Original generated headers and patched HPCG source remain the inputs.
    """
    builds = json.loads((shared / 'S11-18/builds.json').read_text())
    profiles = json.loads((shared / 'S11-15/batch-attribution.json').read_text())
    keys = {p['key'] for p in profiles}
    env = dict(os.environ)
    env['PATH'] = str(shared / 'toolchain/cygwin/bin') + os.pathsep + env.get('PATH', '')
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for program in programs:
        validate_program(program)
        variants = ['serial']
        if 'openmp-' + program in keys:
            variants.append('openmp')
        for variant in variants:
            rows = [r for r in builds if not r.get('held_out') and r['program'] == program
                    and r['compiler'] == 'gcc-knc' and r['variant'] == variant
                    and r['check'] == 'pass']
            if len(rows) != 1:
                raise ValueError('need one frozen build: ' + program + '/' + variant)
            row = rows[0]
            key = variant + '-' + program
            directory = output / 'debug' / key
            directory.mkdir(parents=True, exist_ok=True)
            if resume and (directory / 'collection.json').exists():
                results.append(json.loads((directory / 'collection.json').read_text()))
                print(key + ': reusing completed collection', flush=True)
                continue
            # Search only command records, never read compiler log bodies.
            with local_path(row['log']).open() as log:
                commands = [json.loads(line[8:]) for line in log if line.startswith('COMMAND ')]
            commands = [c for c in commands if re.search(r'k1om-mpss-linux-(gcc|g\+\+|gfortran)$', c[0])]
            if not commands:
                raise ValueError('no frozen compiler commands for ' + key)
            outputs = {c[c.index('-o') + 1]: cygpath(directory / Path(c[c.index('-o') + 1]).name)
                       for c in commands}
            opt = directory / 'vector.opt'
            opt.unlink(missing_ok=True)
            sources, aliases = set(), {}
            with (directory / 'build.log').open('w') as log:
                for command in commands:
                    # The NPB C timer compilation intentionally lacks -fopenmp;
                    # the frozen Fortran link/compilation carries it.
                    if not all(flag in command for flag in row['requested_flags']):
                        raise ValueError('frozen flags disagree with builds.json: ' + key)
                    args = []
                    for arg in command:
                        replacement = outputs.get(arg, arg)
                        # Retired S11-18 support paths are relocated to this checkout.
                        if '/tools/corpus/' in arg and not local_path(arg).exists():
                            replacement = cygpath(root / 'tools/corpus' / arg.rsplit('/', 1)[1])
                            aliases[arg] = replacement
                        args.append(replacement)
                        if re.search(r'\.(?:c|cpp|f90)$', replacement, re.I):
                            sources.add(replacement)
                    args[0] = str(local_path(args[0])) + ('.exe' if os.name == 'nt' else '')
                    args[1:1] = ['-g', '-fopt-info-vec-all=' + cygpath(opt)]
                    log.write('COMMAND ' + json.dumps(args) + '\n')
                    log.flush()
                    subprocess.run(args, cwd=directory, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
            frozen = next(local_path(f) for f in row['files'] if Path(f).name == 'workload')
            if program == 'PB-gemm':
                frozen = shared / 'S11-15/gemm'
            objdump = shared / 'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'
            def text_disassembly(binary):
                dump = subprocess.run([str(objdump), '-d', '-j', '.text', str(binary)],
                                      env=env, text=True, capture_output=True, check=True).stdout
                # Discard only the filename/file-format banner. Addresses, symbols,
                # bytes and all decoded instructions must agree.
                return dump[dump.index('Disassembly of section .text:'):]
            equal = text_disassembly(frozen) == text_disassembly(directory / 'workload')
            result = dict(program=program, variant=variant, key=key, flags=row['flags'],
                          frozen=str(frozen), debug=str(directory / 'workload'),
                          text_equal=equal, sources=sorted(sources), source_aliases=aliases,
                          opt_info=str(opt))
            (directory / 'collection.json').write_text(json.dumps(result, indent=2) + '\n')
            results.append(result)
            print(key + ': .text ' + ('identical' if equal else 'DIFFERS; PCs stay unmapped'), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    audit = commands.add_parser('audit', help='audit frozen S11-15 source mapping')
    root = Path(__file__).resolve().parents[1]
    shared = root.parent / '_shared' if root.parent.name == '.work' else root / '.work/_shared'
    audit.add_argument('--shared', type=Path, default=shared)
    audit.add_argument('--output', type=Path, default=shared / 'S12-19')
    collect = commands.add_parser('collect', help='replay development builds with debug and opt-info')
    collect.add_argument('--shared', type=Path, default=shared)
    collect.add_argument('--output', type=Path, default=shared / 'S12-19')
    collect.add_argument('--program', choices=DEVELOPMENT, action='append')
    collect.add_argument('--resume', action='store_true', help='reuse completed collection results')
    analyze = commands.add_parser('analyze', help='join collected reports with existing profiles')
    analyze.add_argument('--shared', type=Path, default=shared)
    analyze.add_argument('--output', type=Path, default=shared / 'S12-19')
    analyze.add_argument('--program', choices=DEVELOPMENT, action='append')
    analyze.add_argument('--resume', action='store_true', help='reuse completed program analyses')
    report = commands.add_parser('report', help='render completed analyses without rerunning them')
    report.add_argument('--output', type=Path, default=shared / 'S12-19')
    report.add_argument('--program', choices=DEVELOPMENT, action='append')
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
    elif args.command == 'collect':
        collect_debug(args.shared, args.output, args.program or DEVELOPMENT, args.resume)
    elif args.command == 'analyze':
        analyze_collection(args.shared, args.output, args.program or DEVELOPMENT, args.resume)
    elif args.command == 'report':
        report_collection(args.output, args.program or DEVELOPMENT)
    else:
        regions = regions_from_addr2line(args.addr2line.read_text(),
                                        json.loads(args.regions.read_text()), args.module)
        result = triage_program(args.program, args.opt_info.read_text(), regions,
                                args.pcs.read_text(), args.cpu_seconds, args.variant)
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
