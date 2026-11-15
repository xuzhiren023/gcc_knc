"""Dynamic traces for the timing engine: from functional execution, or statically
unrolled from explicit control-flow and address descriptions (no card trace needed)."""
from .errors import InvalidInput, Unsupported
from .functional import TraceEvent, lines_of


def static_trace(kernel, stream, trip_count=None):
    """Unroll a stream without executing it.

    Supported shapes: straight-line code (no branch), or straight-line code with one
    loop: a label, a body, and exactly one backward conditional branch to that label
    (the kernel's 'loop' block gives label and trip_count). Memory addresses come from
    each record's addr {start, stride}: address of the n-th dynamic instance is
    start + n*stride. Anything else is unsupported here; use functional tracing.
    """
    insns = stream.insns
    branches = [i for i in insns if i.is_branch]
    occurrences = {}
    events = []
    seq = 0

    def emit(insn, taken=None):
        nonlocal seq
        n = occurrences.get(insn.id, 0)
        occurrences[insn.id] = n + 1
        ev = TraceEvent(stream.context, insn, seq=seq, taken=taken)
        seq += 1
        if insn.mem is not None or insn.cls in ("prefetch_l1", "prefetch_l2", "vector_gather"):
            if insn.addr_desc is None:
                raise Unsupported("static trace: instruction %s (%s) accesses memory but has no addr {start, stride} description; give one or use functional tracing" % (insn.id, insn.op),
                                  {"instruction": insn.id})
            addr = insn.addr_desc["start"] + n * insn.addr_desc["stride"]
            ev.addr = addr
            if insn.cls == "vector_gather":
                k = insn.lines_hint
                if k is None:
                    raise Unsupported("static trace: gather %s needs a 'lines' hint (number of distinct cache lines touched)" % insn.id)
                ev.lines = tuple(addr + 64 * j for j in range(k))
                ev.nbytes = 64
            else:
                ev.nbytes = insn.mem_bytes or 64
                ev.lines = lines_of(addr, ev.nbytes)
            if insn.cls in ("prefetch_l1", "prefetch_l2"):
                ev.pf_level = insn.spec["level"]
        if insn.mask is not None:
            ev.mask_bits = None  # unknown statically
        events.append(ev)

    if not branches:
        for i in insns:
            emit(i)
        return events, ["static trace: straight-line stream, executed once"]
    if len(branches) != 1 or kernel.loop is None:
        raise Unsupported("static trace supports at most one loop described by kernel.loop; this stream has %d branches" % len(branches))
    br = branches[0]
    label = kernel.loop["label"]
    if br.target != label:
        raise Unsupported("static trace: the branch %s does not target the loop label %r" % (br.id, label))
    head = stream.labels[label]
    if head > br.index:
        raise Unsupported("static trace: forward branch to the loop label is not a loop")
    tc = trip_count if trip_count is not None else kernel.loop.get("trip_count")
    if tc is None:
        raise Unsupported("static trace: kernel.loop.trip_count is required (no functional execution to discover it)")
    tc = int(tc)
    if tc < 1:
        raise InvalidInput("loop.trip_count must be >= 1")
    for i in insns[:head]:
        emit(i)
    for t in range(tc):
        for i in insns[head:br.index]:
            emit(i)
        emit(br, taken=(t != tc - 1))
    for i in insns[br.index + 1:]:
        emit(i)
    return events, ["static trace: loop %r unrolled %d times; the loop branch is taken %d times and falls through once" % (label, tc, tc - 1)]


def loop_body(kernel, stream):
    """(head_index, back_branch_index) of the kernel's loop in this stream, or None."""
    if kernel.loop is None:
        return None
    label = kernel.loop["label"]
    if label not in stream.labels:
        return None
    head = stream.labels[label]
    back = None
    if kernel.loop.get("back_branch"):
        back = stream.by_id.get(kernel.loop["back_branch"])
        if back is None:
            raise InvalidInput("loop.back_branch %r not in stream" % kernel.loop["back_branch"])
        back = back.index
    else:
        for i in stream.insns:
            if i.is_branch and i.target == label and i.index >= head:
                back = i.index
        if back is None:
            raise InvalidInput("no backward branch to loop label %r in context %d" % (label, stream.context))
    return head, back
