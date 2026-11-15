#!/usr/bin/env python3
"""GCC-KNC or GCC 5.1.1 assembly (.s) -> knc-twin kernel for one loop.

    python scripts/from_gcc_s.py file.s --loop .L7 [--spec spec.json] [--contexts 4] [--out kernel.json]
    python scripts/from_gcc_s.py file.s --function saxpy ...      (the function's only innermost loop)

The loop body runs from its label to the last branch back to it. Every line of the body is
converted or listed in `unsupported` with its line number, exact text and reason; nothing is
dropped. A kernel is written only when nothing is unsupported. Record ids are `L<line>` of the
.s file. The spec supplies what assembly cannot: name, unit_of_work, init (and `stream_init`,
one init per context), expected, scenario, loop.trip_count, and `addr`/`lines` hints by record
id for static traces.

Writes the conversion report (knc-twin.conversion/1) to --report or stdout. Exit 0 ok,
3 unsupported, 2 invalid input.
"""
import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knc_model import asm  # noqa: E402
from knc_model.errors import InvalidInput, Unsupported  # noqa: E402
from knc_model.kernel import KERNEL_SCHEMA, Insn  # noqa: E402

_LABEL = re.compile(r"^([A-Za-z_.$][\w.$]*):")
_FUNC_END = (".cfi_endproc", ".size")
SPEC_KERNEL_KEYS = ("name", "description", "unit_of_work", "numerical_policy", "init", "expected", "scenario",
                    "max_steps", "memory_default", "notes")


def _code(raw):
    return raw.split("#", 1)[0].strip()


def _split_labels(code):
    """'a: b: insn' -> (['a', 'b'], 'insn')."""
    labels = []
    while True:
        m = _LABEL.match(code)
        if not m:
            return labels, code
        labels.append(m.group(1))
        code = code[m.end():].strip()


def _branch_target(code):
    parts = code.split(None, 1)
    if not parts or not parts[0].lower().startswith("j") or len(parts) < 2:
        return None
    ops = [o.strip() for o in parts[1].split(",")]
    for o in ops:
        if _LABEL.match(o + ":") and not o.startswith("%"):
            return o
    return None


def _function_range(lines, name):
    start = None
    for i, raw in enumerate(lines):
        labels, _ = _split_labels(_code(raw))
        if name in labels:
            start = i
            break
    if start is None:
        raise InvalidInput("function %r not found" % name)
    for j in range(start + 1, len(lines)):
        c = _code(lines[j])
        if c.startswith(_FUNC_END) or (c.startswith(".type") and "@function" in c and name not in c):
            return start, j
    return start, len(lines) - 1


def _loops(lines, lo, hi):
    """Backward-branch loops in lines[lo..hi]: label -> (label line, last back-branch line)."""
    where = {}
    loops = {}
    for i in range(lo, hi + 1):
        code = _code(lines[i])
        labels, rest = _split_labels(code)
        for lab in labels:
            where[lab] = i
        t = _branch_target(rest)
        if t is not None and t in where and where[t] <= i:
            loops[t] = (where[t], i)
    # A region that returns is a block placed out of line (jump back to a join), not a loop.
    return {lab: (a, b) for lab, (a, b) in loops.items()
            if not any(_split_labels(_code(lines[k]))[1].split(None, 1)[:1] == ["ret"] for k in range(a, b + 1))}


def _innermost(loops):
    out = []
    for lab, (a, b) in loops.items():
        if not any((c, d) != (a, b) and a <= c and d <= b for c, d in loops.values()):
            out.append(lab)
    return sorted(out, key=lambda lab: loops[lab][0])


def find_loop(lines, loop=None, function=None):
    """Return (label, first line index, last line index) of the loop body (0-based)."""
    if function is not None:
        lo, hi = _function_range(lines, function)
    else:
        lo, hi = 0, len(lines) - 1
    if loop is not None:
        starts = [i for i in range(lo, hi + 1) if loop in _split_labels(_code(lines[i]))[0]]
        if len(starts) != 1:
            raise InvalidInput("loop label %r found %d times" % (loop, len(starts)))
        end = next((j for j in range(starts[0] + 1, hi + 1) if _code(lines[j]).startswith(_FUNC_END)), hi)
        loops = _loops(lines, starts[0], end)
        if loop not in loops:
            raise InvalidInput("no branch back to %r after line %d" % (loop, starts[0] + 1))
        return (loop,) + loops[loop]
    loops = _loops(lines, lo, hi)
    inner = _innermost(loops)
    if len(inner) != 1:
        raise InvalidInput("function %r has %d innermost loops; choose one with --loop: %s" % (
            function, len(inner), ", ".join("%s (lines %d-%d)" % (lab, loops[lab][0] + 1, loops[lab][1] + 1) for lab in inner)))
    return (inner[0],) + loops[inner[0]]


def convert_lines(lines, label, first, last):
    """Records and the unsupported list for lines[first..last]."""
    records, unsupported, notes = [], [], []
    count = 0
    seen = set()
    pending = []
    alias = {}
    for i in range(first, last + 1):
        raw = lines[i]
        lineno = i + 1
        labels, code = _split_labels(_code(raw))
        pending += labels
        seen.update(labels)
        if not code:
            continue
        if code.startswith("."):
            try:
                _, dnotes = asm.parse_gas(code)
                notes += ["line %d: %s" % (lineno, n.split(": ", 1)[1]) for n in dnotes]
            except (Unsupported, InvalidInput) as e:
                unsupported.append({"line": lineno, "text": raw.strip(), "reason": str(e).split(": ", 1)[1]})
            continue
        count += 1
        try:
            recs, _ = asm.parse_gas(code)
            rec = recs[0]
            rec["id"] = "L%d" % lineno
            Insn(rec, len(records), 0)
        except (Unsupported, InvalidInput) as e:
            unsupported.append({"line": lineno, "text": raw.strip(), "reason": str(e).split(": ", 1)[-1]})
            pending = []
            continue
        if pending:
            rec["label"] = pending[0]
            for extra in pending[1:]:
                alias[extra] = pending[0]
            pending = []
        records.append(rec)
    defined = seen
    for rec in records:
        ops = rec.get("ops", [])
        if rec["op"].startswith("j") and ops and isinstance(ops[-1], str):
            target = alias.get(ops[-1], ops[-1])
            ops[-1] = target
            if target not in defined:
                unsupported.append({"line": int(rec["id"][1:]), "text": lines[int(rec["id"][1:]) - 1].strip(),
                                    "reason": "side exit to %s outside the loop; the twin needs every branch target inside the stream" % target})
    if not any(r.get("label") == label for r in records) and not any(u["line"] > first for u in unsupported):
        unsupported.append({"line": first + 1, "text": lines[first].strip(), "reason": "loop label has no instruction"})
    unsupported.sort(key=lambda u: u["line"])
    return records, unsupported, notes, count


def build_kernel(records, label, spec, contexts, source, first, last):
    spec = dict(spec or {})
    if "kernel" in spec:
        spec = dict(spec["kernel"])
    kernel = {"schema": KERNEL_SCHEMA}
    for key in SPEC_KERNEL_KEYS:
        if key in spec:
            kernel[key] = copy.deepcopy(spec[key])
    kernel.setdefault("name", "%s_%s" % (os.path.splitext(os.path.basename(source))[0], label.lstrip(".")))
    kernel["description"] = (kernel.get("description", "") + " " if kernel.get("description") else "") + \
        "Converted by from_gcc_s.py from %s, loop %s, lines %d-%d." % (os.path.basename(source), label, first + 1, last + 1)
    hints = {k: spec.get(k, {}) for k in ("addr", "lines")}
    stream_init = spec.get("stream_init", [])
    streams = []
    for ctx in range(contexts):
        recs = copy.deepcopy(records)
        for rec in recs:
            for key, table in hints.items():
                if rec["id"] in table:
                    rec[key] = table[rec["id"]]
        stream = {"context": ctx, "instructions": recs}
        if ctx < len(stream_init):
            stream["init"] = stream_init[ctx]
        streams.append(stream)
    kernel["streams"] = streams
    kernel["loop"] = dict(spec.get("loop", {}), label=label)
    return kernel


def convert(path, loop=None, function=None, spec=None, contexts=1):
    """Return (report, kernel or None)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    label, first, last = find_loop(lines, loop, function)
    records, unsupported, notes, count = convert_lines(lines, label, first, last)
    report = {"schema": "knc-twin.conversion/1", "source": os.path.basename(path), "function": function, "loop": label,
              "lines": [first + 1, last + 1], "status": "unsupported" if unsupported else "ok",
              "instructions": count,
              "unsupported": unsupported, "notes": notes}
    kernel = None if unsupported else build_kernel(records, label, spec, contexts, path, first, last)
    return report, kernel


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("source")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--loop", help="loop label, e.g. .L7")
    g.add_argument("--function", help="function whose only innermost loop is converted")
    p.add_argument("--in-function", dest="in_function", help="with --loop: search the label inside this function only")
    p.add_argument("--spec", help="kernel overlay JSON (name, unit_of_work, init, stream_init, expected, scenario, loop, addr, lines)")
    p.add_argument("--contexts", type=int, default=1, help="streams to create, one copy of the loop each (1-4)")
    p.add_argument("--out", help="kernel JSON to write (only when nothing is unsupported)")
    p.add_argument("--report", help="conversion report JSON (default: stdout)")
    a = p.parse_args(argv)
    try:
        if not 1 <= a.contexts <= 4:
            raise InvalidInput("--contexts must be 1..4")
        spec = None
        if a.spec:
            with open(a.spec, "r", encoding="utf-8") as f:
                spec = json.load(f)
        report, kernel = convert(a.source, a.loop, a.function or a.in_function, spec, a.contexts)
    except InvalidInput as e:
        print(json.dumps({"schema": "knc-twin.conversion/1", "status": "invalid_input", "message": str(e)}, indent=1))
        return 2
    if kernel is not None and a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(kernel, f, indent=1)
        report["kernel"] = a.out
    text = json.dumps(report, indent=1)
    if a.report:
        with open(a.report, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    else:
        print(text)
    for u in report["unsupported"]:
        sys.stderr.write("unsupported line %d: %s -- %s\n" % (u["line"], u["text"], u["reason"]))
    return 3 if report["unsupported"] else 0


if __name__ == "__main__":
    sys.exit(main())
