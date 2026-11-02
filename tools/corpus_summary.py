"""Summarize S0-07 compiler artifacts, without compiling or running programs."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys


def cfg_counts(text):
    counts = [0, 0, 0]
    for function in text.split(';; Function ')[1:]:
        succ = {int(a): set(map(int, b.split())) for a, b in
                re.findall(r'^;; (\d+) succs \{([^}]*)\}', function, re.M)}
        if 2 not in succ:
            continue
        reach, pending = set(), [2]
        while pending:
            n = pending.pop()
            if n not in reach:
                reach.add(n)
                pending.extend(succ.get(n, ()))
        pred = defaultdict(set)
        for a in reach:
            for b in succ.get(a, ()):
                pred[b].add(a)
        bits = {n: 1 << i for i, n in enumerate(sorted(reach))}
        allbits = sum(bits.values())
        dom = {n: bits[n] if n == 2 else allbits for n in reach}
        changed = True
        while changed:
            changed = False
            for n in sorted(reach - {2}):
                mask = allbits
                for p in pred[n]:
                    mask &= dom[p]
                mask |= bits[n]
                if mask != dom[n]:
                    dom[n] = mask
                    changed = True
        loops = defaultdict(set)
        for tail in reach:
            for head in succ.get(tail, ()):
                if dom[tail] & bits[head]:
                    body = {head, tail}
                    pending = [tail] if tail != head else []
                    while pending:
                        for p in pred[pending.pop()]:
                            if p not in body:
                                body.add(p)
                                pending.append(p)
                    loops[head].update(body)
        blocks = {int(n): s for n, s in re.findall(
            r'^  <bb (\d+)>[^\n]*\n(.*?)(?=^  <bb |\Z)', function, re.M | re.S)}
        for body in loops.values():
            s = '\n'.join(blocks.get(n, '') for n in body)
            counts[0] += 1
            counts[1] += bool(re.search(r' = [^;\n]* / ', s))
            counts[2] += bool(re.search(
                r'\b(?:__builtin_)?(?:sqrt|sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|'
                r'exp|exp2|expm1|log|log2|log10|log1p|pow|fabs|floor|ceil|trunc|round|'
                r'fmod|hypot|cabs|copysign|fma|scalbn)[fl]?\s*\(|\bABS_EXPR\b', s))
    return counts


def category(s):
    if re.search(r'control flow|multiple exits|number of iterations|complicated access|loop nest|consecutive inner loops', s):
        return 'control/loop form'
    if re.search(r'dependenc|alias|overlap', s):
        return 'dependence/alias'
    if re.search(r'clobbers memory|function is not vectorizable|function call|statement cannot be vectorized', s):
        return 'calls/memory effects'
    if re.search(r'no vectype|unsupported|relevant stmt|data type|not suitable|reduction|use not simple', s):
        return 'operation/type/reduction'
    if 'profitable' in s or 'cost' in s:
        return 'proxy cost'
    return 'other/unspecified'


def main():
    root = Path(sys.argv[1])
    failures = {}
    for p in root.glob('jobs-*.json'):
        for job in json.loads(p.read_text()):
            failures[job['name']] = {Path(n).stem for n in job['failures']}
    results = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        loops, reasons = {}, defaultdict(set)
        for p in d.glob('*.log'):
            if p.stem in failures.get(d.name, set()):
                continue
            active = None
            for line in p.read_text(errors='replace').splitlines():
                m = re.match(r'(.+?:\d+:\d+): (optimized|missed): (.*)', line)
                if not m:
                    if 'vectorized ' in line and ' loops in function' in line:
                        active = None
                    continue
                loc, status, message = m.groups()
                if message.startswith('loop vectorized using'):
                    loops[loc] = max(loops.get(loc, 0), int(re.search(r'using (\d+)', message)[1]))
                    active = None
                elif message == "couldn't vectorize loop":
                    loops.setdefault(loc, 0)
                    active = loc
                elif active and status == 'missed':
                    reasons[active].add(category(message))
                    active = None
        rejects = Counter()
        for loc, width in loops.items():
            if not width:
                rejects.update(reasons.get(loc) or {'other/unspecified'})
        cfg = [0, 0, 0]
        for p in d.glob('*.cfg'):
            if p.name.split('.')[0] in failures.get(d.name, set()):
                continue
            cfg = [a + b for a, b in zip(cfg, cfg_counts(p.read_text(errors='replace')))]
        row = dict(program=d.name, loops=len(loops), vectorized=sum(w > 0 for w in loops.values()),
                   v512=sum(w == 64 for w in loops.values()), cfg=cfg, reasons=rejects.most_common(3))
        results.append(row)
        print(json.dumps(row))
    (root / 'summary.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
