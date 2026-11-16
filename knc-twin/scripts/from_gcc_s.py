#!/usr/bin/env python3
"""Compiler-output adapter: GCC-KNC (or GCC 5.1.1 k1om) assembly -> knc-twin kernel records.

  from_gcc_s.py FILE.s --function NAME [--init INIT.json] --out KERNEL.json [--profile ID]
  from_gcc_s.py FILE.s --loop NAME:LABEL [--trip-count N] [--init INIT.json] --out KERNEL.json
  from_gcc_s.py FILE.s --loop LABEL [--function NAME] [--spec SPEC.json] [--contexts N]
                [--out KERNEL.json] [--report REPORT.json]
  from_gcc_s.py FILE.s [FILE2.s ...] --audit [--profile ID] [--weights W.json] [--out REPORT.json]

Regions: a whole function (every `ret` becomes a jump to a synthetic end label) or one
loop (the label and its last backward branch; exits are redirected to a synthetic end
label). Nothing is dropped or simplified: an instruction the twin cannot read is kept
in the report as unsupported, and a kernel containing it fails to load with the same
message. Data symbols referenced rip-relative are placed in a synthetic data area and
their bytes copied from the .s file's data directives.

Coverage categories reported per region: parser (syntax read), isa (mnemonic and
operand form known), functional (exact semantics implemented), timing (every latency
parameter known in the chosen profile), memory_forecast (memory records that need
addresses, i.e. an init state or addr descriptions). A region is "complete" for a
category when every instruction passes it.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from knc_model import asm as asm_mod  # noqa: E402
from knc_model import isa  # noqa: E402
from knc_model.errors import InvalidInput, MissingParameter, TwinError, Unsupported  # noqa: E402
from knc_model.kernel import Insn, Mem  # noqa: E402
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json, load_json, sha256_of_file  # noqa: E402

DATA_BASE = 0x10000000
_DATA_DIRS = (".long", ".quad", ".byte", ".short", ".value", ".word", ".zero", ".string", ".ascii", ".asciz", ".float", ".double")


class Function(object):
    def __init__(self, name, start):
        self.name = name
        self.start = start      # line index of the label
        self.end = None         # exclusive
        self.lines = []         # (lineno, text)


def parse_file(path):
    """Split a GAS file into functions (code lines with line numbers) and data symbols (bytes)."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.read().splitlines()
    functions = {}
    order = []
    data = {}
    section = ".text"
    cur = None
    cur_sym = None
    func_types = set()
    for m in re.finditer(r"^\s*\.type\s+([\w.$]+)\s*,\s*@function", "\n".join(raw_lines), re.M):
        func_types.add(m.group(1))
    rept = None  # (count, [lines]) while inside .rept/.endr
    expanded = []
    for lineno, raw in enumerate(raw_lines, 1):
        line = raw.split("#", 1)[0].strip()
        if rept is not None:
            if line == ".endr":
                count, body = rept
                rept = None
                for _ in range(count):
                    expanded.extend(body)
            else:
                rept[1].append((lineno, raw))
            continue
        if line.startswith(".rept"):
            rept = (int(line.split()[1], 0), [])
            continue
        expanded.append((lineno, raw))
    for lineno, raw in expanded:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(".section"):
            section = line.split()[1].split(",")[0]
            cur_sym = None
            continue
        if line in (".text",):
            section = ".text"
            cur_sym = None
            continue
        if line in (".data", ".bss"):
            section = line
            cur_sym = None
            continue
        if line.startswith(".size") and cur is not None:
            name = line.split()[1].rstrip(",")
            if name == cur.name:
                cur.end = lineno
                cur = None
            continue
        m = re.match(r"^([A-Za-z_.$][\w.$]*):(.*)$", line)
        if m and section.startswith((".text", ".text.")):
            name = m.group(1)
            if name in func_types and (cur is None or name != cur.name):
                if cur is not None:
                    # a file without .size directives: the next function ends this one
                    cur.end = lineno
                cur = Function(name, lineno)
                functions[name] = cur
                order.append(name)
            if cur is not None:
                cur.lines.append((lineno, raw))
            rest = m.group(2).strip()
            if not rest:
                continue
            line = rest
        if section.startswith((".text", ".text.")):
            if cur is not None:
                m = re.match(r"^\.(skip|space)\s+(\d+)\s*,\s*(0x90|144)\s*$", line)
                if m:
                    # padding of single-byte NOPs (0x90) inside code executes as that many nops
                    cur.lines.extend((lineno, "\tnop") for _ in range(int(m.group(2))))
                else:
                    cur.lines.append((lineno, raw))
            continue
        # data sections
        m = re.match(r"^([A-Za-z_.$][\w.$]*):(.*)$", line)
        if m:
            cur_sym = m.group(1)
            data[cur_sym] = bytearray()
            line = m.group(2).strip()
            if not line:
                continue
        if cur_sym is not None and line.startswith(_DATA_DIRS):
            d, _, args = line.partition(" ")
            args = args.strip()
            if d in (".long",):
                for v in args.split(","):
                    data[cur_sym] += (int(v.strip(), 0) & 0xFFFFFFFF).to_bytes(4, "little")
            elif d == ".quad":
                for v in args.split(","):
                    data[cur_sym] += (int(v.strip(), 0) & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little")
            elif d in (".short", ".value", ".word"):
                for v in args.split(","):
                    data[cur_sym] += (int(v.strip(), 0) & 0xFFFF).to_bytes(2, "little")
            elif d == ".byte":
                for v in args.split(","):
                    data[cur_sym] += bytes([int(v.strip(), 0) & 0xFF])
            elif d == ".zero":
                n = int(args.split(",")[0], 0)
                data[cur_sym] += bytes(n)
            elif d in (".string", ".asciz", ".ascii"):
                s = args.strip().strip('"').encode("utf-8").decode("unicode_escape").encode("latin-1")
                data[cur_sym] += s + (b"\0" if d != ".ascii" else b"")
            elif d in (".float", ".double"):
                import struct as _st
                for v in args.split(","):
                    data[cur_sym] += _st.pack("<f" if d == ".float" else "<d", float(v))
    for f in functions.values():
        if f.end is None:
            f.end = f.lines[-1][0] + 1 if f.lines else f.start + 1
    return functions, order, data, raw_lines


def _label_of(raw):
    m = re.match(r"^\s*([A-Za-z_.$][\w.$]*|\d+):", raw.split("#", 1)[0])
    return m.group(1) if m else None


def _is_code(raw):
    s = raw.split("#", 1)[0].strip()
    return bool(s) and not s.startswith(".") and not re.match(r"^[A-Za-z_.$][\w.$]*:\s*$", s) and not re.match(r"^\d+:\s*$", s)


def _branch_target(raw):
    s = raw.split("#", 1)[0].strip()
    if re.match(r"^[A-Za-z_.$][\w.$]*:", s):
        s = s.split(":", 1)[1].strip()
    parts = s.split(None, 1)
    if len(parts) >= 2 and parts[0].startswith("j"):
        ops = [o.strip() for o in parts[1].split(",")]
        # jknzd/jkzd take the label first and the mask second; every other jump has the label alone
        return parts[0], ops[0] if parts[0] in ("jknzd", "jkzd") else ops[-1]
    return None, None


def function_region(func):
    """Lines of a whole function with every ret turned into a jump to the synthetic end."""
    out = []
    labels = set()
    for lineno, raw in func.lines:
        lab = _label_of(raw)
        if lab:
            labels.add(lab)
        s = raw.split("#", 1)[0].strip()
        if s in ("ret", "rep ret", "rep; ret"):
            out.append((lineno, "\tjmp __knc_twin_end"))
        else:
            out.append((lineno, raw))
    out.append((func.end, "__knc_twin_end:\n\tnop"))
    return out, labels


def loop_region(func, label):
    idx = None
    for k, (lineno, raw) in enumerate(func.lines):
        if _label_of(raw) == label:
            idx = k
            break
    if idx is None:
        raise InvalidInput("label %s not found in function %s" % (label, func.name))
    back = None
    for k in range(idx, len(func.lines)):
        mn, tgt = _branch_target(func.lines[k][1])
        if tgt == label and k > idx:
            back = k
    if back is None:
        raise InvalidInput("no backward branch to %s in %s: not a loop" % (label, func.name))
    body = func.lines[idx:back + 1]
    inner_labels = set(_label_of(raw) for _, raw in body if _label_of(raw))
    out = []
    for lineno, raw in body:
        mn, tgt = _branch_target(raw)
        if mn and tgt and tgt not in inner_labels and not re.match(r"^\d+[bf]$", tgt):
            raw = re.sub(r"(?<![\w.$])" + re.escape(tgt) + r"(?![\w.$])", "__knc_twin_end", raw, count=1)
        out.append((lineno, raw))
    out.append((func.end, "__knc_twin_end:\n\tnop"))
    return out, inner_labels


def region_text(lines, total=None):
    """Join region lines in order; returns (text, origin) where origin[local_line] = source line."""
    out = []
    origin = {}
    for lineno, raw in lines:
        for part in raw.split("\n"):
            out.append(part)
            origin[len(out)] = lineno
    return "\n".join(out), origin


def remap_ids(records, origin):
    """Record ids become L<source line>, with _2, _3 ... for repeated expansions (.rept)."""
    seen = {}
    for rec in records:
        src = origin.get(rec.get("source"), rec.get("source"))
        n = seen.get(src, 0) + 1
        seen[src] = n
        rec["source"] = src
        if str(rec.get("id", "")).startswith("L"):
            rec["id"] = "L%s" % src if n == 1 else "L%s_%d" % (src, n)
    return records


def classify_records(records, profile):
    """Per-record coverage. Returns (insns_by_index, rows)."""
    rows = []
    for k, rec in enumerate(records):
        row = {"line": rec.get("source"), "id": rec["id"], "text": rec["op"] + " " + ", ".join(json.dumps(o) if not isinstance(o, str) else o for o in reversed(rec["ops"])),
               "parser": True, "isa": False, "functional": False, "timing": None, "memory": False, "class": None, "reason": None}
        try:
            insn = Insn(rec, k, 0)
        except Unsupported as e:
            row["reason"] = "unsupported: " + e.message
            rows.append(row)
            continue
        except InvalidInput as e:
            row["parser"] = False
            row["reason"] = "invalid: " + e.message
            rows.append(row)
            continue
        row["isa"] = True
        row["class"] = insn.cls
        row["functional"] = insn.functional_supported()
        if not row["functional"]:
            row["reason"] = "timing only: " + (insn.spec.get("note") or "")
        row["memory"] = bool(insn.mem is not None or insn.cls in ("vector_gather", "vector_scatter"))
        if profile is not None:
            needed = []
            key = isa.CLASSES[insn.cls]["latency"]
            if key not in (None, "memory", "gather"):
                needed.append(key)
            occ = isa.CLASSES[insn.cls].get("occupancy")
            if occ:
                needed.append(occ)
            if insn.has_swizzle:
                needed.append("latency.vector_long")
            if insn.cls == "vector_gather":
                needed += ["latency.gather_first_line", "occupancy.gather_cycles_per_line"]
            missing = [n for n in needed if not profile.has(n)]
            row["timing"] = not missing
            if missing:
                row["reason"] = (row["reason"] + "; " if row["reason"] else "") + "missing parameter(s): " + ", ".join(missing)
        rows.append(row)
    return rows


def summarize(rows):
    n = len(rows)
    def frac(key):
        return sum(1 for r in rows if r[key]) / float(n) if n else 0.0
    out = {"instructions": n,
           "parser_ok": sum(1 for r in rows if r["parser"]),
           "isa_known": sum(1 for r in rows if r["isa"]),
           "functional_exact": sum(1 for r in rows if r["functional"]),
           "timing_params_known": sum(1 for r in rows if r["timing"]) if rows and rows[0]["timing"] is not None else None,
           "memory_records": sum(1 for r in rows if r["memory"]),
           "complete": {"parser": all(r["parser"] for r in rows), "isa": all(r["isa"] for r in rows),
                        "functional": all(r["functional"] for r in rows),
                        "timing": all(r["timing"] for r in rows) if rows and rows[0]["timing"] is not None else None},
           "unsupported": sorted(set(r["reason"] for r in rows if r["reason"] and not r["isa"])),
           "timing_only_or_missing": sorted(set(r["reason"] for r in rows if r["reason"] and r["isa"])),
           "mnemonics_unknown": sorted(set(r["text"].split()[0] for r in rows if not r["isa"]))}
    return out


def live_in_registers(records):
    """Registers read before any write in record order (first-order approximation of live-ins)."""
    written = set()
    live = []
    for k, rec in enumerate(records):
        try:
            insn = Insn(rec, k, 0)
        except TwinError:
            continue
        for r in sorted(insn.reads | insn.addr_regs):
            if r not in written and r not in live and r not in ("x87", "fcw"):
                live.append(r)
        written |= insn.writes
    return live


def build_kernel(name, records, data_syms, init_overlay, trip_count=None, loop_label=None, description=""):
    syms_used = set()
    for rec in records:
        for o in rec["ops"]:
            if isinstance(o, dict) and o.get("symbol"):
                syms_used.add(o["symbol"])
    init = {"registers": {}, "memory": [], "symbols": {}}
    unresolved = []
    addr = DATA_BASE
    for s in sorted(syms_used):
        if s in data_syms:
            init["symbols"][s] = "0x%x" % addr
            if data_syms[s]:
                init["memory"].append({"addr": "0x%x" % addr, "u8": list(data_syms[s])})
            addr += (len(data_syms[s]) + 63) // 64 * 64 or 64
        else:
            unresolved.append(s)
    for r in live_in_registers(records):
        init["registers"][r] = 0
    kernel = {"schema": "knc-twin.kernel/1", "name": name, "description": description,
              "unit_of_work": {"description": "TODO: define the unit", "count": 1},
              "memory_default": 0,
              "init": init, "streams": [{"context": 0, "instructions": records}],
              "provenance": {"adapter": "from_gcc_s.py", "live_in_registers_placeholders": sorted(init["registers"]), "unresolved_symbols": unresolved}}
    if loop_label:
        kernel["loop"] = {"label": loop_label}
        if trip_count:
            kernel["loop"]["trip_count"] = trip_count
    if init_overlay:
        apply_overlay(kernel, init_overlay)
    return kernel


def apply_overlay(kernel, init_overlay):
    """Merge an --init file (init, expected, unit, policy, scenario, calls, inputs ...) into a converted kernel."""
    for key in ("init", "expected", "unit_of_work", "numerical_policy", "scenario", "loop", "memory_default", "name", "description",
                "calls", "max_steps", "inputs", "entry"):
        if key in init_overlay:
            if key == "init":
                for sub, val in init_overlay["init"].items():
                    if isinstance(val, dict) and isinstance(kernel["init"].get(sub), dict):
                        kernel["init"][sub].update(val)
                    elif isinstance(val, list) and isinstance(kernel["init"].get(sub), list):
                        kernel["init"][sub].extend(val)
                    else:
                        kernel["init"][sub] = val
            elif key == "calls":
                kernel.setdefault("calls", {}).update(init_overlay["calls"])
            else:
                kernel[key] = init_overlay[key]
    if "provenance" in init_overlay and isinstance(init_overlay["provenance"], dict):
        kernel.setdefault("provenance", {}).update(init_overlay["provenance"])
    return kernel


def convert(path, func_name, loop_label=None, trip_count=None, init_overlay=None, profile=None):
    functions, order, data, raw_lines = parse_file(path)
    if func_name not in functions:
        raise InvalidInput("function %r not in %s; functions: %s" % (func_name, path, ", ".join(order[:40])))
    func = functions[func_name]
    if loop_label:
        lines, labels = loop_region(func, loop_label)
    else:
        lines, labels = function_region(func)
    text, origin = region_text(lines)
    records, notes = asm_mod.parse_gas(text)
    remap_ids(records, origin)
    for rec in records:
        if rec["op"] == "nop" and rec.get("label") == "__knc_twin_end":
            rec["id"] = "__knc_twin_end"
    rows = classify_records(records, profile)
    summary = summarize(rows)
    name = "%s__%s" % (os.path.splitext(os.path.basename(path))[0], func_name + (("__" + loop_label) if loop_label else ""))
    kernel = build_kernel(name, records, data, init_overlay, trip_count, loop_label if loop_label else None,
                          description="%s region from %s (adapter from_gcc_s.py)" % ("loop " + loop_label if loop_label else "function", path))
    kernel["provenance"].update({"source_file": os.path.abspath(path), "source_sha256": sha256_of_file(path), "function": func_name,
                                 "loop_label": loop_label, "coverage": summary, "parser_notes": [n for n in notes if "directive" not in n]})
    return kernel, rows, summary


SPEC_KERNEL_KEYS = ("name", "description", "unit_of_work", "numerical_policy", "init", "expected", "scenario",
                    "max_steps", "memory_default", "notes")


def _text_function(raw_lines):
    """Every line of the file as one pseudo-function, for hand-written loops without `.type @function`."""
    func = Function("__text__", 1)
    func.lines = list(enumerate(raw_lines, 1))
    func.end = len(raw_lines) + 1
    return func


def _function_with_label(functions, order, raw_lines, label):
    for name in order:
        if any(_label_of(raw) == label for _, raw in functions[name].lines):
            return functions[name]
    func = _text_function(raw_lines)
    if any(_label_of(raw) == label for _, raw in func.lines):
        return func
    raise InvalidInput("loop label %r not found" % label)


def apply_spec(kernel, spec, contexts=1):
    """Merge a spec (S13-06 trial format) into an adapter kernel.

    Keys: name, description, unit_of_work, numerical_policy, init (replaces the adapter's
    placeholder init), expected, scenario, max_steps, memory_default, notes, loop (merged),
    stream_init (one init per context), addr / lines (hints by record id), plus `contexts`
    copies of the stream. Nothing here changes an instruction.
    """
    spec = dict(spec or {})
    if "kernel" in spec:
        spec = dict(spec["kernel"])
    prov = kernel.get("provenance", {})
    for key in SPEC_KERNEL_KEYS:
        if key == "init" and key in spec:
            # merged as with --init: spec registers override the adapter's zero placeholders
            for sub, val in spec["init"].items():
                val = json.loads(json.dumps(val))
                if isinstance(val, dict) and isinstance(kernel["init"].get(sub), dict):
                    kernel["init"][sub].update(val)
                elif isinstance(val, list) and isinstance(kernel["init"].get(sub), list):
                    kernel["init"][sub].extend(val)
                else:
                    kernel["init"][sub] = val
        elif key in spec:
            kernel[key] = json.loads(json.dumps(spec[key]))
    if "loop" in spec:
        kernel["loop"] = dict(kernel.get("loop", {}), **spec["loop"])
    base = kernel["streams"][0]["instructions"]
    hints = {k: spec.get(k, {}) for k in ("addr", "lines")}
    stream_init = spec.get("stream_init", [])
    streams = []
    for ctx in range(contexts):
        recs = json.loads(json.dumps(base))
        for rec in recs:
            for key, table in hints.items():
                if rec["id"] in table:
                    rec[key] = table[rec["id"]]
        stream = {"context": ctx, "instructions": recs}
        if ctx < len(stream_init):
            stream["init"] = stream_init[ctx]
        streams.append(stream)
    kernel["streams"] = streams
    kernel["provenance"] = prov
    return kernel


def convert_loop(path, loop, function=None, spec=None, contexts=1, profile=None):
    """One loop (or a whole function when loop is None) -> (conversion report, kernel or None).

    The report (knc-twin.conversion/1) lists every instruction the twin cannot read or does not
    know, with its source line, exact text and reason; the kernel is returned only when that
    list is empty. Timing-only instructions convert (functional reports them).
    """
    functions, order, data, raw_lines = parse_file(path)
    if function is not None and function not in functions:
        raise InvalidInput("function %r not in %s" % (function, path))
    if loop is None:
        if function is None:
            raise InvalidInput("give a loop label or a function")
        func = functions[function]
    else:
        func = functions[function] if function is not None else _function_with_label(functions, order, raw_lines, loop)
        if func.name not in functions:
            functions[func.name] = func
            order.append(func.name)
    if loop is not None:
        lines, _ = loop_region(func, loop)
    else:
        lines, _ = function_region(func)
    text, origin = region_text(lines)
    unsupported = []
    try:
        records, notes = asm_mod.parse_gas(text)
    except TwinError as e:
        # report the failing source line
        m = re.match(r"^line (\d+)", e.message)
        src = origin.get(int(m.group(1))) if m else None
        unsupported.append({"line": src, "text": raw_lines[src - 1].strip() if src else "", "reason": e.message})
        records, notes = [], []
    remap_ids(records, origin)
    for rec in records:
        if rec["op"] == "nop" and rec.get("label") == "__knc_twin_end":
            rec["id"] = "__knc_twin_end"
    rows = classify_records(records, profile)
    for r in rows:
        if not r["isa"] or not r["parser"]:
            src = r["line"]
            unsupported.append({"line": src, "text": raw_lines[src - 1].strip() if isinstance(src, int) else r["text"], "reason": r["reason"]})
    code_lines = [ln for ln, raw in lines if _is_code(raw) and ln <= len(raw_lines)]
    report = {"schema": "knc-twin.conversion/1", "source": os.path.basename(path), "function": func.name if func.name != "__text__" else function,
              "loop": loop, "lines": [code_lines[0] if code_lines else None, code_lines[-1] if code_lines else None] if loop is None else
              [lines[0][0], lines[-2][0] if len(lines) > 1 else lines[0][0]],
              "status": "unsupported" if unsupported else "ok", "instructions": len(records),
              "unsupported": sorted(unsupported, key=lambda u: (u["line"] or 0)),
              "coverage": summarize(rows) if rows else None,
              "notes": [n for n in notes if "directive" not in n]}
    if unsupported:
        return report, None
    name = "%s_%s" % (os.path.splitext(os.path.basename(path))[0], (loop or function).lstrip("."))
    kernel = build_kernel(name, records, data, None, None, loop,
                          description="Converted by from_gcc_s.py from %s, %s." % (os.path.basename(path), ("loop %s" % loop) if loop else ("function %s" % function)))
    kernel["provenance"].update({"source_file": os.path.basename(path), "function": report["function"], "loop_label": loop,
                                 "lines": report["lines"]})
    apply_spec(kernel, spec, contexts)
    return report, kernel


def innermost_loops(func):
    """Labels with a backward branch and no other loop label strictly inside their body."""
    loops = []
    pos = {}
    for k, (lineno, raw) in enumerate(func.lines):
        lab = _label_of(raw)
        if lab:
            pos[lab] = k
    for k, (lineno, raw) in enumerate(func.lines):
        mn, tgt = _branch_target(raw)
        if mn and tgt in pos and pos[tgt] < k:
            loops.append((tgt, pos[tgt], k))
    out = []
    for lab, a, b in loops:
        inner = [(l2, a2, b2) for (l2, a2, b2) in loops if a < a2 and b2 < b]
        if not inner and (lab, a, b) not in out:
            out.append((lab, a, b))
    return out


def audit(paths, profile, weights):
    report = {"files": [], "totals": {"functions": 0, "loops": 0, "instructions": 0, "loops_complete_functional": 0, "loops_complete_timing": 0, "loop_instructions": 0, "loop_instructions_covered_timing": 0}}
    for path in paths:
        functions, order, data, raw_lines = parse_file(path)
        frep = {"file": path, "functions": []}
        for name in order:
            func = functions[name]
            try:
                kernel, rows, summary = convert(path, name, profile=profile)
            except TwinError as e:
                summary = {"error": e.message}
                rows = []
            entry = {"function": name, "summary": summary, "loops": []}
            for lab, a, b in innermost_loops(func):
                try:
                    k2, rows2, s2 = convert(path, name, loop_label=lab, profile=profile)
                except TwinError as e:
                    s2 = {"error": e.message}
                entry["loops"].append({"label": lab, "lines": (func.lines[a][0], func.lines[b][0]), "summary": s2})
                if "instructions" in s2:
                    report["totals"]["loops"] += 1
                    report["totals"]["loop_instructions"] += s2["instructions"]
                    if s2["complete"]["functional"]:
                        report["totals"]["loops_complete_functional"] += 1
                    if s2["complete"]["timing"]:
                        report["totals"]["loops_complete_timing"] += 1
                        report["totals"]["loop_instructions_covered_timing"] += s2["instructions"]
            w = (weights or {}).get(name) or (weights or {}).get("%s:%s" % (os.path.basename(path), name))
            if w is not None:
                entry["native_seconds"] = w
            frep["functions"].append(entry)
            report["totals"]["functions"] += 1
            report["totals"]["instructions"] += summary.get("instructions", 0)
        report["files"].append(frep)
    return report


def audit_markdown(report):
    L = ["# GCC-KNC output audit (knc-twin adapter)", "",
         "Per function: instructions, how many the twin reads (parser), knows (isa), executes exactly (functional) and can time with the profile (timing). A loop is complete when every instruction in it passes. Native seconds come from the weights file when given.", ""]
    L.append("| file | function | instrs | parser | isa | functional | timing | unknown mnemonics / blockers | innermost loops (label: instrs, functional, timing) | native s |")
    L.append("|---|---|---:|---:|---:|---:|---:|---|---|---:|")
    for f in report["files"]:
        for e in f["functions"]:
            s = e["summary"]
            if "error" in s:
                L.append("| %s | %s | - | - | - | - | - | %s | | |" % (os.path.basename(f["file"]), e["function"], s["error"][:120]))
                continue
            blockers = "; ".join(s["mnemonics_unknown"][:8]) if s["mnemonics_unknown"] else ("; ".join(x[:60] for x in s["timing_only_or_missing"][:3]) if s["timing_only_or_missing"] else "")
            loops = "; ".join("%s: %d, %s, %s" % (l["label"], l["summary"].get("instructions", 0),
                                                "yes" if l["summary"].get("complete", {}).get("functional") else "no",
                                                "yes" if l["summary"].get("complete", {}).get("timing") else "no") for l in e["loops"] if "summary" in l)
            L.append("| %s | %s | %d | %d | %d | %d | %s | %s | %s | %s |" % (
                os.path.basename(f["file"]), e["function"], s["instructions"], s["parser_ok"], s["isa_known"], s["functional_exact"],
                s["timing_params_known"] if s["timing_params_known"] is not None else "-", blockers, loops, e.get("native_seconds", "")))
    t = report["totals"]
    L.append("")
    L.append("Totals: %d functions, %d instructions; %d innermost loops with %d instructions, %d loops complete for functional execution, %d complete for timing (%d instructions)." % (
        t["functions"], t["instructions"], t["loops"], t["loop_instructions"], t["loops_complete_functional"], t["loops_complete_timing"], t["loop_instructions_covered_timing"]))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--function")
    ap.add_argument("--loop", help="NAME:LABEL, or LABEL (the function is found, or given with --function)")
    ap.add_argument("--spec", help="trial spec JSON (name, unit_of_work, init, stream_init, expected, scenario, loop, addr, lines); "
                    "writes a conversion report and a kernel only when nothing is unsupported")
    ap.add_argument("--contexts", type=int, default=1, help="with --spec or --loop LABEL: streams to create, one copy each (1-4)")
    ap.add_argument("--report", help="conversion report JSON (default: stdout)")
    ap.add_argument("--trip-count", type=int)
    ap.add_argument("--init", help="JSON with init/expected/unit_of_work/scenario to merge into the kernel")
    ap.add_argument("--profile", default="card-7120-measured")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--weights", help="JSON {function or file:function -> native seconds}")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    try:
        profile = load_profile(args.profile) if args.profile else None
    except TwinError as e:
        print("profile: %s" % e.message, file=sys.stderr)
        return 2
    try:
        if args.audit:
            weights = load_json(args.weights, "weights") if args.weights else None
            report = audit(args.files, profile, weights)
            md = audit_markdown(report)
            if args.out:
                dump_json(report, args.out)
                with open(os.path.splitext(args.out)[0] + ".md", "w", encoding="utf-8") as f:
                    f.write(md)
                print("wrote %s and .md" % args.out)
            print(md)
            return 0
        if not args.function and not args.loop:
            print("give --function NAME, --loop NAME:LABEL or --audit", file=sys.stderr)
            return 2
        if args.spec or (args.loop and ":" not in args.loop):
            if not 1 <= args.contexts <= 4:
                raise InvalidInput("--contexts must be 1..4")
            spec = load_json(args.spec, "spec") if args.spec else None
            report, kernel = convert_loop(args.files[0], args.loop, args.function, spec, args.contexts, profile)
            if kernel is not None and args.out:
                dump_json(kernel, args.out)
                report["kernel"] = args.out
            text = json.dumps(report, indent=1)
            if args.report:
                with open(args.report, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text + "\n")
            else:
                print(text)
            for u in report["unsupported"]:
                sys.stderr.write("unsupported line %s: %s -- %s\n" % (u["line"], u["text"], u["reason"]))
            return 3 if report["unsupported"] else 0
        func = args.function
        label = None
        if args.loop:
            func, label = args.loop.split(":", 1)
        overlay = load_json(args.init, "init overlay") if args.init else None
        kernel, rows, summary = convert(args.files[0], func, label, args.trip_count, overlay, profile)
        if args.out:
            dump_json(kernel, args.out)
            with open(os.path.splitext(args.out)[0] + ".coverage.json", "w", encoding="utf-8") as f:
                json.dump({"summary": summary, "rows": rows}, f, indent=1)
            print("wrote %s (coverage in .coverage.json)" % args.out)
        print(json.dumps(summary, indent=1))
        if kernel["provenance"]["live_in_registers_placeholders"]:
            print("live-in registers needing init values: %s" % ", ".join(kernel["provenance"]["live_in_registers_placeholders"]))
        if kernel["provenance"]["unresolved_symbols"]:
            print("unresolved symbols (give init.symbols/memory): %s" % ", ".join(kernel["provenance"]["unresolved_symbols"]))
        return 0 if summary["complete"]["isa"] else 3
    except TwinError as e:
        print("%s: %s" % (e.status, e.message), file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
