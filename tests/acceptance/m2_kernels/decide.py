"""ADR-0010 amendment 2 decisions from complete card_run stdout files.

One job per file, including card_run's final JSON result. Decisions are JSON;
exit 0 means the evidence was read, not that the experiment passed.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics as st


def interval(values):
    rng = random.Random(1510)
    medians = sorted(st.median(rng.choices(values, k=len(values))) for _ in range(10000))
    def percentile(p):
        index = p * (len(medians)-1)
        lo = int(index)
        return medians[lo] + (index-lo)*(medians[min(lo+1, len(medians)-1)]-medians[lo])
    return [percentile(.025), percentile(.975)]


def number(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError('nonfinite ' + key)
    return value


def read(path):
    rows = {}
    result = None
    for line in path.read_text().splitlines():
        if line.startswith('{'):
            candidate = json.loads(line)
            if 'result_class' in candidate:
                result = candidate
        else:
            parts = line.split()
            if parts:
                rows.setdefault(parts[0], []).append(dict(p.split('=', 1) for p in parts[1:] if '=' in p))
    reasons = []
    launches = rows.get('launch', [])
    if len(launches) != 1:
        return None, ['expected one launch record']
    launch = launches[0]
    if not any(r.get('name') == 'correctness_done' for r in rows.get('phase', [])):
        reasons.append('missing pre-timing correctness gate')
    if any(r.get('failing_cases') != '0' for r in rows.get('correctness', [])):
        reasons.append('correctness failed')
    if {r.get('kernel') for r in rows.get('correctness', [])} != {
            'affine_f32', 'affine_f64', 'stencil1', 'stencil2', 'short', 'mat8', 'mat16'}:
        reasons.append('incomplete correctness records')
    if launch.get('threads_per_core') == '3':
        reasons.append('density 3')
    if launch.get('valid') != '1' or launch.get('sized') != '1':
        reasons.append('driver mechanical validity failed')
    summaries = rows.get('summary', [])
    builds = {r.get('build') for r in summaries}
    if not {'gcc', 'x87', 'imci'}.issubset(builds) or len(builds) != len(summaries):
        reasons.append('missing or duplicate build summaries')
    if any(not 50000000 <= number(r, 'median_ns') <= 200000000 for r in summaries):
        reasons.append('batch median outside 50-200 ms')
    policies = [{r['path']: {k: v for k, v in r.items() if k != 'phase'}
                 for r in rows.get('policy', []) if r.get('phase') == phase}
                for phase in ('start', 'end')]
    if not policies[0] or policies[0] != policies[1]:
        reasons.append('missing or changed clock policy')
    # Successful program completion also establishes that every pin check returned.
    if result is None:
        reasons.append('missing card_run final JSON')
    else:
        if (result.get('result_class') != 'program' or result.get('program_exit_code') != 0
                or result.get('exit_code') != 0):
            reasons.append('card_run or pin checks failed')
        for field in ('overlapping_jobs', 'foreign_processes'):
            if result.get(field) != []:
                reasons.append(field + ' not empty or missing')
    number(launch, 'gcc_over_x87_max')
    if launch.get('gain_fraction_defined') == '1':
        number(launch, 'gain_fraction')
    return dict(file=str(path), launch=launch, rows=rows), reasons


def key(job):
    row = job['launch']
    return tuple(row[k] for k in ('kernel', 'working_set', 'length', 'short_length',
                                  'threads_per_core', 'cores'))


def m2(jobs, invalid, density):
    selected = [j for j in jobs if j['launch']['threads_per_core'] == str(density)
                and j['launch']['cores'] == '60']
    l2 = sorted((j for j in selected if j['launch']['kernel'] == 'affine_f32'
                 and j['launch']['working_set'] == 'L2'),
                key=lambda j: int(j['launch']['launch']))
    values = [number(j['launch'], 'gain_fraction') for j in l2]
    n = len(values)
    report = dict(launch_values=values, regime_steps=sum(int(j['launch']['regime_steps'])
                                                       for j in jobs), sequential_step=1 if n <= 5 else 2)
    if values:
        mean = st.mean(values)
        # One-sided t(.95,df), only the predeclared n=5 and n=10 blocks decide.
        lower = mean - {5: 2.131846786, 10: 1.833112933}.get(n, 0)*(
            st.stdev(values)/math.sqrt(n) if n > 1 else 0)
        report.update(range=[min(values), max(values)], minimum=min(values), mean=mean,
                      lower_bound=lower if n in (5, 10) else None,
                      median_gain_ci95=interval(values),
                      a=all(v >= .5 for v in values), b=n in (5, 10) and lower >= .5,
                      c=all(number(j['launch'], 'gcc_over_x87_max') <= 1.05 for j in jobs))
    ids = {int(j['launch']['launch']) for j in l2}
    cohorts = {}
    for job in jobs:
        cohorts.setdefault(key(job), set()).add(int(job['launch']['launch']))
    if (invalid or n not in (5, 10) or ids != set(range(1, n+1))
            or any(group != ids for group in cohorts.values())
            or any(j['launch'].get('gain_fraction_defined') != '1' for j in l2)):
        report['decision'] = 'invalid-block'
    elif n == 10 and not sequential_needed(values[:5]):
        report['decision'] = 'invalid-block'
        report['reason'] = 'first five launches did not require the sequential step'
    elif report['a'] and report['b'] and report['c']:
        report['decision'] = 'pass'
    elif n == 5 and report['c'] and mean >= .5 and (not report['a'] or not report['b']):
        report['decision'] = 'run-five-more'
    else:
        report['decision'] = 'fail'
    return report


def sequential_needed(values):
    mean = st.mean(values)
    lower = mean - 2.131846786*st.stdev(values)/math.sqrt(5)
    return mean >= .5 and (min(values) < .5 or lower < .5)


def tuning(jobs, invalid, minimum, layout_checked):
    groups = {}
    for job in jobs:
        if any('gcc_over_gcc_before' in r for r in job['rows'].get('round', [])):
            groups.setdefault(key(job), []).append(job)
    reports = []
    for group, launches in sorted(groups.items()):
        launches.sort(key=lambda j: int(j['launch']['launch']))
        all_ratios, signs, reasons, notes = [], [], [], []
        for job in launches:
            rounds = job['rows']['round']
            ratios = [number(r, 'gcc_over_gcc_before') for r in rounds]
            if (len(ratios) < 5 or any(r <= 0 for r in ratios)
                    or len({(r['group'], r['round']) for r in rounds}) != len(rounds)):
                reasons.append('need at least five unique positive paired rounds per launch')
            median = st.median(ratios)
            signs.append(dict(launch=int(job['launch']['launch']), median=median,
                              sign='faster' if median < 1 else 'slower' if median > 1 else 'equal'))
            all_ratios.extend(ratios)
        ci = interval(all_ratios)
        # A within-launch step proves two states were observed, as does a >=2%
        # spread of the before build's normalized times between launches.
        before = [r for j in launches for r in j['rows'].get('summary', [])
                  if r.get('build') == 'gcc_before']
        if len(before) != len(launches):
            reasons.append('missing gcc_before summary')
        times = [number(r, 'ns_per_element') for r in before if 'ns_per_element' in r]
        states = (any(r.get('regime_step') == '1' for r in before)
                  or bool(times and (max(times)-min(times))/st.median(times) >= .02))
        if not states:
            notes.append('two performance states not established; three launches make both likely')
        if len(launches) < 3:
            reasons.append('need at least three launches')
        median = st.median(all_ratios)
        if 1-median < .02 and not layout_checked:
            reasons.append('effect under 2% requires opposite link order check')
        decision = 'reject'
        if {s['sign'] for s in signs} >= {'faster', 'slower'}:
            decision = 'placement-dependent'
        elif not invalid and not reasons and ci[1] < 1-minimum:
            decision = 'accept'
        reports.append(dict(configuration=group, median_ratio=median, ratio_ci95=ci,
                            per_launch_signs=signs, decision=decision, reasons=reasons, notes=notes))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-effect', type=float, default=.02, help='fractional required reduction')
    parser.add_argument('--density', type=int, choices=(1, 2, 4), default=4,
                        help='production density for M2')
    parser.add_argument('--layout-checked', action='store_true',
                        help='lead attests opposite link order confirmed the sub-2%% effect')
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    if not 0 <= args.min_effect < 1:
        parser.error('--min-effect must be in [0,1)')
    jobs, invalid, seen = [], [], set()
    for path in args.files:
        try:
            job, reasons = read(path)
            if job:
                identity = key(job) + (job['launch']['launch'],)
                if identity in seen:
                    reasons.append('duplicate launch')
                seen.add(identity)
            if reasons:
                invalid.append(dict(file=str(path), reasons=reasons))
            elif job:
                jobs.append(job)
        except (OSError, ValueError, KeyError, TypeError) as error:
            invalid.append(dict(file=str(path), reasons=[str(error)]))
    print(json.dumps(dict(m2=m2(jobs, invalid, args.density),
                          tuning=tuning(jobs, invalid, args.min_effect, args.layout_checked),
                          invalid=invalid), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
