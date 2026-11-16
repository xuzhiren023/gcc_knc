#!/usr/bin/env python3
"""A real roll-up example: the S12-31 microbench kernels converted from the binary that ran on the card.

Regions: HPCG's SpMV and SymGS row loops as the project's HPCG 3.1 serial pilot spends its time
(S11-28 profile: SpMV about 26%, MG/SymGS about 60% of the timed set; docs/research/s12-31-hpcg.md),
baseline = today's instruction order (gas_0), candidate = compare next to its jump (adj_0).
Both kernels come from tests/heldout_native/s12-31-microbench/kernels.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from knc_model.profile import load_profile  # noqa: E402
from knc_model.util import dump_json  # noqa: E402

K = "../../tests/heldout_native/s12-31-microbench/kernels/"
prof = load_profile("card-7120-measured")
manifest = {
    "schema": "knc-twin.rollup/1",
    "name": "HPCG serial pilot: compare-next-to-jump in the SpMV and SymGS row loops (S12-31 rule A)",
    "profile": "card-7120-measured", "frozen_profile_hash": prof.hash,
    "program": {"unit": "seconds per HPCG pilot run (S11-28 fixed work, serial)", "measured_per_unit": 243.7,
                "source": "docs/research/s12-31-hpcg.md 'What the result means' point 3: GCC-KNC pilot about 243.7 s"},
    "unvalidated_band_pct": 30,
    "regions": [
        {"name": "SpMV row loops", "share": 0.26, "share_source": "S11-28 pilot: 52 SpMV passes of 0.634 s in the 243.7 s run (docs/research/s12-31-hpcg.md)",
         "baseline": K + "gas_0.json", "candidate": K + "adj_0.json"},
        {"name": "SymGS row loops (MG)", "share": 0.60, "share_source": "S11-28 pilot: 51 MG applications; the SymGS sweeps are the same row loop shape",
         "baseline": K + "gas_0.json", "candidate": K + "mid_0.json"}
    ],
    "notes": ["the row loops stand in for the kernels (27 products per row, data in L1): the pilot's rows stream from memory, so the roll-up is optimistic for the memory-bound part",
              "measured outcome for comparison (not an input): S12-31 A/B, HPCG rating after/before 1.088 (lead card window 7)"]
}
dump_json(manifest, os.path.join(HERE, "manifest.json"))
print("wrote", os.path.join(HERE, "manifest.json"))
