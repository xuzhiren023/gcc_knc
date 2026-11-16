"""Opt-in captured reciprocal words. Tables are never selected by default.

Files contain little-endian u32 words. Reads are deferred until an active normal
input needs an entry, and large captures are not copied into the Python heap.
"""
import math
import os
import struct

from .errors import InvalidInput, Unsupported
from .util import resource_path

COUNTS = {"vrcp23ps": 1 << 23, "vrsqrt23ps": 1 << 24}


def table_path(name):
    if not isinstance(name, str) or not name or os.path.basename(name) != name or "/" in name or "\\" in name:
        raise InvalidInput("reciprocal table file must be a basename under fixtures/tables")
    return resource_path("fixtures", "tables", name)


def validate_descriptor(op, desc):
    if op not in COUNTS or not isinstance(desc, dict):
        raise InvalidInput("unknown reciprocal table operation %r" % op)
    table_path(desc.get("file"))
    count = desc.get("entries")
    synthetic = desc.get("status") == "synthetic"
    if isinstance(count, bool) or not isinstance(count, int) or (count != COUNTS[op] and not (synthetic and count == 1024)):
        raise InvalidInput("%s table needs %d entries (or 1024 explicitly synthetic entries)" % (op, COUNTS[op]))
    if desc.get("status") not in ("measured", "synthetic"):
        raise InvalidInput("reciprocal table status must be measured or synthetic")
    if desc.get("exponent_scaling_verified") is not True:
        raise InvalidInput("reciprocal table needs exponent_scaling_verified: true; check exponent scaling first")
    if not desc.get("source"):
        raise InvalidInput("reciprocal table needs a source")


class Tables(object):
    def __init__(self, descriptors):
        if not isinstance(descriptors, dict):
            raise InvalidInput("numerical_policy.reciprocal_tables must be an object")
        self.descriptors = descriptors
        for op, desc in descriptors.items():
            validate_descriptor(op, desc)

    def lookup(self, op, bits):
        desc = self.descriptors[op]
        exp = ((bits >> 23) & 255) - 127
        index = bits & 0x7fffff
        if op == "vrsqrt23ps":
            parity = exp & 1
            index += parity << 23
            shift = -(exp - parity) // 2
        else:
            shift = -exp
        if index >= desc["entries"]:
            raise Unsupported("%s input index %d is outside the synthetic table's captured range" % (op, index))
        path = table_path(desc["file"])
        try:
            with open(path, "rb") as handle:
                if os.fstat(handle.fileno()).st_size != 4 * desc["entries"]:
                    raise InvalidInput("%s table byte length does not match entries" % op)
                handle.seek(index * 4)
                raw = handle.read(4)
        except OSError as e:
            raise InvalidInput("cannot read %s table: %s" % (op, e))
        word, = struct.unpack("<I", raw)
        exponent = (word >> 23) & 255
        if word & 0x80000000 or exponent in (0, 255):
            raise InvalidInput("%s table entry %d must be positive and normal" % (op, index))
        exponent += shift
        sign = bits & 0x80000000 if op == "vrcp23ps" else 0
        if exponent <= 0:
            return sign
        if exponent >= 255:
            return sign | 0x7f800000
        return sign | (exponent << 23) | (word & 0x7fffff)


def scatter_parameter(row):
    value = row.get("cycles_per_line")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise InvalidInput("scatter result needs a finite positive cycles_per_line")
    return {"name": "occupancy.scatter_cycles_per_line", "value": value, "unit": "cycles/line",
            "note": row.get("note", "isolated per-line scatter occupancy")}
