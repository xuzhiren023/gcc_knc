"""Hardware profiles: common KNC rules plus card-specific parameters, with provenance per parameter."""
import copy
import os

from . import PROFILE_SCHEMA
from .errors import InvalidInput, MissingParameter
from .util import load_json, resource_path, sha256_of_obj

VALID_STATUSES = ("documented", "measured", "literature", "derived", "assumed", "unknown", "synthetic")


class Param(object):
    __slots__ = ("name", "value", "unit", "status", "source", "alternatives", "uncertainty", "note", "applies_to")

    def __init__(self, name, d):
        self.name = name
        self.value = d.get("value")
        self.unit = d.get("unit", "")
        self.status = d.get("status", "unknown")
        self.source = d.get("source", "")
        self.alternatives = d.get("alternatives", [])
        self.uncertainty = d.get("uncertainty", "")
        self.note = d.get("note", "")
        self.applies_to = d.get("applies_to", "")

    @property
    def known(self):
        return self.status != "unknown" and self.value is not None

    def to_dict(self):
        return {"value": self.value, "unit": self.unit, "status": self.status, "source": self.source,
                "alternatives": self.alternatives, "uncertainty": self.uncertainty}


class Profile(object):
    def __init__(self, chain, merged_params, hash_):
        self.chain = chain  # list of raw profile dicts, base first
        self.params = merged_params  # name -> Param
        self.hash = hash_
        top = chain[-1]
        self.id = top["id"]
        self.version = top.get("version", "0")
        self.synthetic = bool(top.get("synthetic", False)) or any(bool(p.get("synthetic", False)) for p in chain)
        self.kind = top.get("kind", "card")
        self.description = top.get("description", "")
        self.native_measurement_ids = []
        for p in chain:
            self.native_measurement_ids.extend(p.get("native_measurement_ids", []))
        self.calibration = top.get("calibration", {"state": "uncalibrated", "statement": "No calibration block in profile.", "held_out_validation_cases": 0})
        self.sources = {}
        for p in chain:
            self.sources.update(p.get("sources", {}))
        self.used = {}  # name -> Param actually consulted by an engine run

    # --- access -------------------------------------------------------------
    def param(self, name):
        p = self.params.get(name)
        if p is None:
            raise MissingParameter("parameter %r is not defined by profile %s" % (name, self.id),
                                   {"parameter": name, "profile": self.id})
        self.used[name] = p
        return p

    def get(self, name):
        """Known value or MissingParameter. Never returns a default for an unknown parameter."""
        p = self.param(name)
        if not p.known:
            raise MissingParameter(
                "parameter %r is unknown in profile %s (%s). Import a measurement or choose a profile that sets it; the engine does not substitute a default."
                % (name, self.id, p.source or "no source"),
                {"parameter": name, "profile": self.id, "status": p.status, "source": p.source, "alternatives": p.alternatives})
        return p.value

    def get_sub(self, name, key):
        v = self.get(name)
        if not isinstance(v, dict) or key not in v or v[key] is None:
            raise MissingParameter("parameter %r[%r] is unknown in profile %s" % (name, key, self.id),
                                   {"parameter": name, "key": key, "profile": self.id})
        return v[key]

    def has(self, name):
        p = self.params.get(name)
        return p is not None and p.known

    def status_counts(self):
        counts = {}
        for p in self.params.values():
            counts[p.status] = counts.get(p.status, 0) + 1
        return counts

    def used_summary(self):
        return {n: {"value": p.value, "status": p.status, "unit": p.unit, "source": p.source}
                for n, p in sorted(self.used.items())}

    def describe(self):
        return {"id": self.id, "version": self.version, "hash": self.hash, "kind": self.kind,
                "synthetic": self.synthetic, "chain": [p["id"] for p in self.chain],
                "calibration": self.calibration, "native_measurement_ids": self.native_measurement_ids,
                "parameter_status_counts": self.status_counts()}


def _resolve_profile_file(name_or_path, search_dirs):
    if os.path.isfile(name_or_path):
        return os.path.abspath(name_or_path)
    for d in search_dirs:
        cand = os.path.join(d, name_or_path + ".json")
        if os.path.isfile(cand):
            return cand
        cand = os.path.join(d, name_or_path)
        if os.path.isfile(cand):
            return cand
    raise InvalidInput("profile %r not found (searched %s)" % (name_or_path, ", ".join(search_dirs)))


def _no_value(v):
    """None, or a dict whose leaves are all None (a structured unknown)."""
    if v is None:
        return True
    if isinstance(v, dict) and v:
        return all(_no_value(x) for x in v.values())
    return False


def _validate_raw(raw, path):
    if raw.get("schema") != PROFILE_SCHEMA:
        raise InvalidInput("profile %s: schema must be %r" % (path, PROFILE_SCHEMA))
    for key in ("id", "version", "parameters"):
        if key not in raw:
            raise InvalidInput("profile %s: missing %r" % (path, key))
    if not isinstance(raw["parameters"], dict):
        raise InvalidInput("profile %s: parameters must be an object" % path)
    for name, d in raw["parameters"].items():
        if not isinstance(d, dict) or "value" not in d:
            raise InvalidInput("profile %s: parameter %r must be an object with a 'value'" % (path, name))
        st = d.get("status", "unknown")
        if st not in VALID_STATUSES:
            raise InvalidInput("profile %s: parameter %r has status %r; allowed: %s" % (path, name, st, ", ".join(VALID_STATUSES)))
        if st == "unknown" and not _no_value(d.get("value")):
            raise InvalidInput("profile %s: parameter %r is 'unknown' but has a value" % (path, name))
        if st != "unknown" and _no_value(d.get("value")) and st != "synthetic":
            raise InvalidInput("profile %s: parameter %r has no value but status %r (use 'unknown')" % (path, name, st))
    if raw.get("kind") == "synthetic" and not raw.get("synthetic", False):
        raise InvalidInput("profile %s: kind synthetic requires synthetic: true" % path)


def load_profile(name_or_path, overlays=None, extra_dirs=None):
    """Load a profile and its 'extends' chain. Overlays (paths) are applied last, in order."""
    search_dirs = list(extra_dirs or []) + [resource_path("profiles")]
    chain = []
    seen = set()
    path = _resolve_profile_file(name_or_path, search_dirs)
    while True:
        raw = load_json(path, "profile")
        _validate_raw(raw, path)
        if raw["id"] in seen:
            raise InvalidInput("profile extends cycle at %s" % raw["id"])
        seen.add(raw["id"])
        chain.insert(0, raw)
        base = raw.get("extends")
        if not base:
            break
        path = _resolve_profile_file(base, [os.path.dirname(path)] + search_dirs)
    for ov in overlays or []:
        raw = load_json(ov, "overlay profile")
        _validate_raw(raw, ov)
        chain.append(raw)
    merged = {}
    merged_raw = {}
    for raw in chain:
        for name, d in raw["parameters"].items():
            merged[name] = Param(name, d)
            merged_raw[name] = copy.deepcopy(d)
    hash_ = sha256_of_obj({"chain": [{"id": p["id"], "version": p.get("version"), "parameters": p["parameters"]} for p in chain]})
    return Profile(chain, merged, hash_)


def list_profiles():
    out = []
    d = resource_path("profiles")
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            try:
                raw = load_json(os.path.join(d, fn), "profile")
            except InvalidInput:
                continue
            out.append({"id": raw.get("id"), "kind": raw.get("kind"), "synthetic": bool(raw.get("synthetic", False)),
                        "file": fn, "description": raw.get("description", "")[:160]})
    return out
