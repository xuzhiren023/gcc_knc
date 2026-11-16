"""Hashing, resource resolution, stable JSON."""
import datetime
import hashlib
import json
import os

from .errors import InvalidInput


def skill_root():
    """knc-twin/ directory, resolved from this file, never from the cwd."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(*parts):
    return os.path.join(skill_root(), *parts)


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path, what="file"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise InvalidInput("%s not found: %s" % (what, path))
    except json.JSONDecodeError as e:
        raise InvalidInput("%s is not valid JSON: %s (%s)" % (what, path, e))


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def utc_now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def parse_int(value, what):
    """Accept int, or a decimal/hex string. Reject floats."""
    if isinstance(value, bool):
        raise InvalidInput("%s: boolean is not an integer" % what)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip().replace("_", "")
        try:
            if s.lower().startswith(("0x", "-0x")):
                return int(s, 16)
            if s.lower().startswith(("0b", "-0b")):
                return int(s, 2)
            return int(s, 10)
        except ValueError:
            raise InvalidInput("%s: cannot parse integer %r" % (what, value))
    raise InvalidInput("%s: expected integer, got %r" % (what, value))


def mask64(x):
    return x & 0xFFFFFFFFFFFFFFFF


def mask32(x):
    return x & 0xFFFFFFFF


def to_signed(x, bits):
    x &= (1 << bits) - 1
    if x & (1 << (bits - 1)):
        return x - (1 << bits)
    return x
