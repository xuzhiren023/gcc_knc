#!/usr/bin/env python3
"""Generate S14-13 native request skeletons; never build or contact a card.

The minimal driver cannot prime ownership or discover a physical address hash.
Each request therefore carries its experimental prerequisites explicitly.
"""
import argparse
import json
from pathlib import Path

from knc_model import cli


def kernel(name, cores=60, lines=16):
    raw = {"schema": "knc-twin.kernel/1", "name": name,
           "unit_of_work": {"description": "detailed 64-byte reads", "count": cores * lines},
           "init": {"memory": []}, "streams": [],
           "scenario": {"memory": {"type": "line_tracking", "cold_level": "memory",
                                    "hardware_prefetcher": "off"}}}
    td_line = 0
    for core in range(cores):
        if name == "multicore-ring-distance":
            addresses = [0x100000] * lines
        elif name == "multicore-channel-saturation":
            addresses = [0x100000 + core * 0x10000 + i * 1024 for i in range(lines)]
        elif name == "multicore-td-contention":
            addresses = []
            while len(addresses) < lines:
                if (td_line ^ (td_line >> 6)) % 64 == 0:
                    addresses.append(0x100000 + td_line * 64)
                td_line += 1
        else:
            addresses = [0x100000 + core * lines * 64 + i * 64 for i in range(lines)]
        for address in sorted(set(addresses)):
            raw["init"]["memory"].append({"addr": address, "f32": [1.0] * 16})
        # Use one relocated base and displacements, never absolute model addresses.
        base = min(addresses)
        raw["streams"].append({"core": core, "context": 0,
            "init": {"registers": {"rax": base}},
            "instructions": [{"op": "vmovaps", "ops": ["zmm0", {"base": "rax", "disp": a - base}]}
                             for a in addresses],
            "expected": {"registers": {"zmm0": {"f32": [1.0] * 16}}}})
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.out).resolve()
    plan = json.loads((Path(__file__).resolve().parents[1] / "references" / "calibration-plan.json").read_text())
    for spec in plan["microbenchmarks"]:
        if not spec["id"].startswith("multicore-") or spec["status"] == "needs-driver":
            continue
        name = spec["id"]
        out = root / name
        out.mkdir(parents=True, exist_ok=True)
        raw = kernel(name, 2 if name == "multicore-ring-distance" else 60)
        raw["provenance"] = {"description": spec["why"], "experimental_prerequisites": spec["prerequisites"]}
        path = out / "input.json"
        path.write_text(json.dumps(raw, indent=2) + "\n")
        code = cli.main(["prepare-native", str(path), "--out", str(out)])
        if code:
            return code
        (out / "experiment.json").write_text(json.dumps(spec, indent=2) + "\n")
        print("staged %s: %d workers; operator preconditioning required" % (name, len(raw["streams"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
