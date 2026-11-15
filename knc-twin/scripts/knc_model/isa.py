"""The supported IMCI/K1OM instruction subset.

Each entry says: timing class, Intel-order operand roles, whether exact functional
semantics are implemented, and notes. Anything not in this table is rejected as
unsupported: it never gets a default cost.

Operand role syntax (Intel operand order: destination first):
  w:   written          r:   read          rw:  read and written
  a:   address only (lea)                   t:   branch target label
  kinds after the colon: g (gpr, any width), v (zmm), k (mask), m (memory), i (immediate),
  x (x87 st register), combinations such as gm, gmi, vm, km, xm, xgm; mi = memory with a
  vector index (gather/scatter). A spec's "ops" may be a list of alternatives (different arities).
"""

CLASSES = {
    "scalar_alu":        {"pipes": "UV", "latency": "latency.scalar_alu", "kind": "scalar"},
    "scalar_rmw":        {"pipes": "UV", "latency": "latency.scalar_alu", "kind": "rmw"},
    "scalar_imul":       {"pipes": "U", "latency": "latency.scalar_imul", "kind": "scalar"},
    "scalar_idiv":       {"pipes": "UV_both", "latency": "latency.scalar_idiv", "kind": "scalar", "occupancy": "latency.scalar_idiv"},
    "scalar_load":       {"pipes": "UV", "latency": "memory", "kind": "load"},
    "scalar_store":      {"pipes": "UV", "latency": None, "kind": "store"},
    "branch":            {"pipes": "UV", "latency": None, "kind": "branch"},
    "mask_op":           {"pipes": "UV", "latency": "latency.mask_op", "kind": "scalar"},
    "vector_arith":      {"pipes": "U", "latency": "latency.vector_arith", "kind": "vector"},
    "vector_long":       {"pipes": "U", "latency": "latency.vector_long", "kind": "vector"},
    "vector_convert_df": {"pipes": "U", "latency": "latency.vector_convert_df", "kind": "vector"},
    "vector_load":       {"pipes": "U", "latency": "memory", "kind": "load"},
    "vector_store":      {"pipes": "UV", "latency": None, "kind": "store"},
    "vector_packstore":  {"pipes": "UV", "latency": None, "kind": "store"},
    "vector_gather":     {"pipes": "UV_both", "latency": "gather", "kind": "gather"},
    "vector_scatter":    {"pipes": "UV_both", "latency": None, "kind": "scatter", "occupancy": "occupancy.scatter_cycles_per_line"},
    "prefetch_l1":       {"pipes": "UV", "latency": None, "kind": "prefetch"},
    "prefetch_l2":       {"pipes": "UV", "latency": None, "kind": "prefetch"},
    "x87_add":           {"pipes": "U", "latency": "latency.x87_add", "kind": "x87"},
    "x87_mul":           {"pipes": "U", "latency": "latency.x87_mul", "kind": "x87", "occupancy": "occupancy.x87_mul"},
    "x87_div":           {"pipes": "U", "latency": "latency.x87_div", "kind": "x87", "occupancy": "occupancy.x87_div"},
    "x87_sqrt":          {"pipes": "U", "latency": "latency.x87_sqrt", "kind": "x87", "occupancy": "latency.x87_sqrt"},
    "x87_move":          {"pipes": "U", "latency": "latency.x87_move", "kind": "x87"},
    "x87_load":          {"pipes": "U", "latency": "memory", "kind": "x87load"},
    "x87_store":         {"pipes": "U", "latency": None, "kind": "x87store"},
    "x87_compare":       {"pipes": "U", "latency": "latency.x87_compare", "kind": "x87"},
    "x87_control":       {"pipes": "UV_both", "latency": "latency.x87_control", "kind": "x87"},
    "fence":             {"pipes": "UV_both", "latency": "latency.fence", "kind": "fence"},
}

FLAGS = ("ZF", "SF", "CF", "OF", "PF")
SWIZZLES = ("cdab", "badc", "dacb", "aaaa", "bbbb", "cccc", "dddd")
BROADCASTS = ("1to16", "4to16", "1to8", "4to8")
UPCONV_PS = ("float16", "uint8", "sint8", "uint16", "sint16")
UPCONV_D = ("uint8", "sint8", "uint16", "sint16")
DOWNCONV_PS = ("float16", "uint8", "sint8", "uint16", "sint16")
DOWNCONV_D = ("uint8", "sint8", "uint16", "sint16")

INSTRUCTIONS = {}


def _add(name, cls, ops, fn=None, flags_w=False, flags_r=False, mem_size=None, note="", aliases=(), **extra):
    rec = {"name": name, "class": cls, "ops": ops, "fn": fn, "flags_w": flags_w, "flags_r": flags_r,
           "mem_size": mem_size, "note": note}
    rec.update(extra)
    INSTRUCTIONS[name] = rec
    for a in aliases:
        INSTRUCTIONS[a] = dict(rec, name=a, alias_of=name)


# ---- scalar integer -------------------------------------------------------------
for _n in ("add", "sub", "and", "or", "xor", "adc", "sbb"):
    _add(_n, "scalar_alu", ["rw:gm", "r:gmi"], fn="alu2", flags_w=True, flags_r=(_n in ("adc", "sbb")),
         note="register or memory destination (memory destination is a read-modify-write, class scalar_rmw)")
_add("cmp", "scalar_alu", ["r:gm", "r:gmi"], fn="cmp", flags_w=True)
_add("test", "scalar_alu", ["r:gm", "r:gi"], fn="test", flags_w=True)
_add("bt", "scalar_alu", ["r:gm", "r:gi"], fn="bt", flags_w=True, note="CF = selected bit; other flags left unchanged (undefined)")
_add("mov", "scalar_alu", ["w:gm", "r:gmi"], fn="mov", note="8/16/32/64-bit register or memory move; memory forms take the load/store class")
_add("movabs", "scalar_alu", ["w:g", "r:i"], fn="mov")
_add("lea", "scalar_alu", ["w:g", "a:m"], fn="lea")
for _n, _sw, _dw, _sx in (("movslq", 32, 64, True), ("movsbl", 8, 32, True), ("movsbq", 8, 64, True), ("movswl", 16, 32, True), ("movswq", 16, 64, True),
                           ("movzbl", 8, 32, False), ("movzbq", 8, 64, False), ("movzwl", 16, 32, False), ("movzwq", 16, 64, False),
                           ("movsbw", 8, 16, True), ("movzbw", 8, 16, False)):
    _add(_n, "scalar_alu", ["w:g", "r:gm"], fn="movx", src_width=_sw, dst_width=_dw, sign=_sx, mem_size=_sw // 8)
_add("cltq", "scalar_alu", [], fn="cltq", note="rax = sign-extend eax")
_add("cltd", "scalar_alu", [], fn="cltd", note="edx = sign of eax")
_add("cqto", "scalar_alu", [], fn="cqto", note="rdx = sign of rax")
_add("inc", "scalar_alu", ["rw:gm"], fn="incdec", flags_w=True, note="does not change CF")
_add("dec", "scalar_alu", ["rw:gm"], fn="incdec", flags_w=True, note="does not change CF")
_add("neg", "scalar_alu", ["rw:gm"], fn="neg", flags_w=True)
_add("not", "scalar_alu", ["rw:gm"], fn="not")
for _n in ("shl", "shr", "sar", "sal"):
    _add(_n, "scalar_alu", [["rw:gm", "r:gi"], ["rw:gm"]], fn="shift", flags_w=True,
         note="immediate or %cl count; CF per the SDM, OF only defined for a count of 1 (left unchanged otherwise)")
_add("imul", "scalar_imul", [["rw:g", "r:gmi"], ["w:g", "r:gm", "r:i"], ["r:gm"]], fn="imul", flags_w=True,
     note="two- and three-operand forms are exact; the one-operand rdx:rax form is unsupported")
_add("idiv", "scalar_idiv", ["r:gm"], fn="idiv", flags_w=True, signed=True, note="rdx:rax / src; latency.scalar_idiv must be known")
_add("div", "scalar_idiv", ["r:gm"], fn="idiv", flags_w=True, signed=False)
_add("push", "scalar_store", ["r:gmi"], fn="push", mem_size=8, note="rsp -= 8; store")
_add("pop", "scalar_load", ["w:gm"], fn="pop", mem_size=8, note="load; rsp += 8")
_add("leave", "scalar_load", [], fn="leave", mem_size=8, note="rsp = rbp; pop rbp")
_add("nop", "scalar_alu", [], fn="nop", note="costs an issue slot only")
_add("movzx", "scalar_alu", ["w:g", "r:gm"], fn=None, note="use the GAS mnemonics movzbl/movzwl/movzbq/movzwq")
_add("call", "branch", ["t"], fn=None, note="REGION BOUNDARY: calls are not simulated; cut the region at the call or treat the callee as unsupported")
_add("ret", "branch", [], fn=None, note="REGION BOUNDARY: a region ends before ret")
for _n in ("cmove", "cmovne", "cmovl", "cmovg", "cmovle", "cmovge", "cmova", "cmovb", "cmovae", "cmovbe"):
    _add(_n, "scalar_alu", ["rw:g", "r:gm"], fn=None, note="KNC has no CMOV; -march=knc never emits it (S1-04)")

# ---- branches and setcc ------------------------------------------------------------
_COND = {"z": "zf", "e": "zf", "nz": "nzf", "ne": "nzf", "l": "lt", "nge": "lt", "ge": "ge", "nl": "ge", "g": "gt", "nle": "gt",
         "le": "le", "ng": "le", "b": "cf", "c": "cf", "nae": "cf", "ae": "ncf", "nb": "ncf", "nc": "ncf", "a": "a", "nbe": "a",
         "be": "be", "na": "be", "s": "sf", "ns": "nsf", "p": "pf", "pe": "pf", "np": "npf", "po": "npf"}
_add("jmp", "branch", ["t"], fn="jmp")
for _suf, _c in _COND.items():
    _add("j" + _suf, "branch", ["t"], fn="jcc", flags_r=True, cond=_c)
    _add("set" + _suf, "scalar_alu", ["w:gm"], fn="setcc", flags_r=True, cond=_c, mem_size=1)
_add("jkzd", "branch", ["r:k", "t"], fn="jk", cond="kz", note="branch if mask is zero")
_add("jknzd", "branch", ["r:k", "t"], fn="jk", cond="knz", note="branch if mask is nonzero")

# ---- mask ops ------------------------------------------------------------------------
_add("kmov", "mask_op", ["w:kg", "r:kg"], fn="kmov", note="k<-k, k<-gpr (low 16 bits), gpr<-k (zero-extended)")
for _n in ("kand", "kor", "kxor", "kxnor", "kandn", "kandnr"):
    _add(_n, "mask_op", ["rw:k", "r:k"], fn="klogic")
_add("knot", "mask_op", ["w:k", "r:k"], fn="knot")
_add("kortest", "mask_op", ["r:k", "r:k"], fn="kortest", flags_w=True, note="ZF = (k1|k2)==0, CF = (k1|k2)==0xffff")

# ---- vector FP ------------------------------------------------------------------------
for _fmt, _suf in (("f32", "ps"), ("f64", "pd")):
    for _op, _k in (("vadd", "add"), ("vsub", "sub"), ("vsubr", "subr"), ("vmul", "mul"), ("vmax", "max"), ("vmin", "min")):
        _add(_op + _suf, "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt=_fmt, opk=_k, mem_size=64,
             note=("max/min follow the x86 rule: a NaN or equal-zero operand returns the second source (assumed for KNC)" if _k in ("max", "min") else ""))
    for _base, _negp, _negc in (("vfmadd", False, False), ("vfmsub", False, True), ("vfnmadd", True, False), ("vfnmsub", True, True)):
        _add("%s132%s" % (_base, _suf), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmt, form="132", negp=_negp, negc=_negc, mem_size=64)
        _add("%s213%s" % (_base, _suf), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmt, form="213", negp=_negp, negc=_negc, mem_size=64)
        _add("%s231%s" % (_base, _suf), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmt, form="231", negp=_negp, negc=_negc, mem_size=64)
    _add("vcmp" + _suf, "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vcmp", fmt=_fmt, mem_size=64,
         note="predicate immediate: 0 eq, 1 lt, 2 le, 3 unord, 4 neq, 5 nlt, 6 nle, 7 ord")
    for _pred, _pn in enumerate(("eq", "lt", "le", "unord", "neq", "nlt", "nle", "ord")):
        _add("vcmp%s%s" % (_pn, _suf), "vector_arith", ["w:k", "r:v", "r:vm"], fn="vcmp", fmt=_fmt, fixed_pred=_pred, mem_size=64)
    _add("vblendm" + _suf, "vector_arith", ["w:v", "r:v", "r:vm"], fn="vblendm", fmt=_fmt, mem_size=64, note="dst = mask ? src2 : src1 per lane")
_add("vcvtfxpntdq2ps", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_i2f", mem_size=64, note="imm bits 1:0 rounding (0 rn,1 rd,2 ru,3 rz); exponent adjust bits must be 0")
_add("vcvtfxpntudq2ps", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_u2f", mem_size=64)
_add("vcvtfxpntps2dq", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_f2i", signed=True, mem_size=64)
_add("vcvtfxpntps2udq", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_f2i", signed=False, mem_size=64)
_add("vcvtfxpntpd2dq", "vector_convert_df", ["w:v", "r:vm", "r:i"], fn="vcvt_d2i", signed=True, mem_size=64, note="8 doubles -> 8 int32 in the low lanes; upper lanes set to zero (assumed)")
_add("vcvtfxpntpd2udq", "vector_convert_df", ["w:v", "r:vm", "r:i"], fn="vcvt_d2i", signed=False, mem_size=64)
_add("vcvtps2pd", "vector_convert_df", ["w:v", "r:vm"], fn="vcvt_s2d", mem_size=64, note="low 8 floats -> 8 doubles (exact); latency assumed equal to pd->dq (7)")
_add("vcvtpd2ps", "vector_convert_df", ["w:v", "r:vm"], fn="vcvt_d2s", mem_size=64, note="8 doubles -> low 8 floats, upper lanes zero (assumed); rounding per numerical policy")
_add("vrndfxpntps", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vrnd", mem_size=64, note="round to an integer-valued float with the immediate's rounding mode")
_add("vrcp23ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only (23-bit approximate reciprocal; exact bit pattern not modeled)")
_add("vrsqrt23ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vlog2ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vexp223ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vscaleps", "vector_arith", ["w:v", "r:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vpermd", "vector_long", ["w:v", "r:v", "r:vm"], fn="vpermd", mem_size=64, note="dword permute: dst[i] = src2[idx[i] & 15]")
_add("vpermf32x4", "vector_long", ["w:v", "r:vm", "r:i"], fn="vpermf32x4", mem_size=64, note="128-bit group permute: group i <- group (imm >> 2i) & 3")

# ---- vector int32 / int64 -----------------------------------------------------------------
for _n, _k in (("vpaddd", "add"), ("vpsubd", "sub"), ("vpsubrd", "subr"), ("vpandd", "and"), ("vpord", "or"), ("vpxord", "xor"), ("vpandnd", "andn"),
               ("vpmulld", "mullo"), ("vpmulhd", "mulhs"), ("vpmulhud", "mulhu"), ("vpminsd", "mins"), ("vpmaxsd", "maxs"), ("vpminud", "minu"), ("vpmaxud", "maxu"),
               ("vpsllvd", "shlv"), ("vpsrlvd", "shrv"), ("vpsravd", "sarv")):
    _add(_n, "vector_arith", ["w:v", "r:v", "r:vm"], fn="vint2", opk=_k, mem_size=64)
for _n, _k in (("vpandq", "and"), ("vporq", "or"), ("vpxorq", "xor"), ("vpandnq", "andn")):
    _add(_n, "vector_arith", ["w:v", "r:v", "r:vm"], fn="vint2q", opk=_k, mem_size=64, note="64-bit logic (KNC has no 64-bit integer arithmetic)")
for _n, _k in (("vpslld", "shl"), ("vpsrld", "shr"), ("vpsrad", "sar")):
    _add(_n, "vector_arith", ["w:v", "r:vm", "r:i"], fn="vshift_imm", opk=_k, mem_size=64)
_add("vpcmpd", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vpcmp", signed=True, mem_size=64, note="predicate: 0 eq, 1 lt, 2 le, 4 ne, 5 nlt, 6 nle")
_add("vpcmpud", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vpcmp", signed=False, mem_size=64)
_add("vpcmpeqd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=0, mem_size=64)
_add("vpcmpgtd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=6, mem_size=64)
_add("vpcmpltd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=1, mem_size=64)
_add("vpbroadcastd", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=4, mem_size=4, note="dword broadcast from memory")
_add("vbroadcastss", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=4, mem_size=4)
_add("vbroadcastsd", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=8, mem_size=8)
_add("vpbroadcastq", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=8, mem_size=8)
for _n in ("vbroadcastf32x4", "vbroadcasti32x4"):
    _add(_n, "vector_load", ["w:v", "r:m"], fn="vbroadcast4", elem=4, mem_size=16, note="16-byte group broadcast to 4 groups")
for _n in ("vbroadcastf64x4", "vbroadcasti64x4"):
    _add(_n, "vector_load", ["w:v", "r:m"], fn="vbroadcast4", elem=8, mem_size=32)

# ---- vector memory --------------------------------------------------------------------------
for _n in ("vmovaps", "vmovapd", "vmovdqa32", "vmovdqa64"):
    _add(_n, "vector_load", ["w:vm", "r:vm"], fn="vmov", mem_size=64,
         note="register<->aligned memory, masked merge; store forms take the vector_store class; {float16}/{uint8}/... up- and down-conversions on the memory side")
for _n in ("vmovnrngoaps", "vmovnraps", "vmovnrngoapd", "vmovnrapd"):
    _add(_n, "vector_store", ["w:m", "r:v"], fn="vstore_ngo", mem_size=64, note="no-read store; functionally a store, timing as a store without a fill")
for _half in ("l", "h"):
    for _suf, _elem in (("ps", 4), ("pd", 8), ("d", 4), ("q", 8)):
        _add("vloadunpack%s%s" % (_half, _suf), "vector_load", ["rw:v", "r:m"], fn="vunpack", half=_half, elem=_elem, mem_size=64,
             note="unaligned load half: l takes the elements before the next 64-byte boundary, h those at or after it; masked merge; up-conversions on the memory operand")
        _add("vpackstore%s%s" % (_half, _suf), "vector_packstore", ["w:m", "r:v"], fn="vpackstore", half=_half, elem=_elem, mem_size=64,
             note="unaligned store half; masked; down-conversions on the register operand")
_add("vgatherdps", "vector_gather", ["w:v", "r:mi"], fn="vgather", elem=4, fmt="f32", note="dword gather with masked completion: gathered lanes have their mask bit cleared")
_add("vpgatherdd", "vector_gather", ["w:v", "r:mi"], fn="vgather", elem=4, fmt="i32")
_add("vgatherdpd", "vector_gather", ["w:v", "r:mi"], fn="vgather", elem=8, fmt="f64", note="8 doubles; the low 8 dword indices are used")
_add("vpgatherdq", "vector_gather", ["w:v", "r:mi"], fn="vgather", elem=8, fmt="i64")
_add("vscatterdps", "vector_scatter", ["w:mi", "r:v"], fn="vscatter", elem=4, note="dword scatter with masked completion; occupancy.scatter_cycles_per_line must be known")
_add("vpscatterdd", "vector_scatter", ["w:mi", "r:v"], fn="vscatter", elem=4)
_add("vscatterdpd", "vector_scatter", ["w:mi", "r:v"], fn="vscatter", elem=8)
_add("vpscatterdq", "vector_scatter", ["w:mi", "r:v"], fn="vscatter", elem=8)
for _n in ("vprefetch0", "vprefetche0"):
    _add(_n, "prefetch_l1", ["r:m"], fn="prefetch", level="l1", mem_size=64)
for _n in ("vprefetch1", "vprefetch2", "vprefetchnta", "vprefetche1", "vprefetche2", "vprefetchenta"):
    _add(_n, "prefetch_l2", ["r:m"], fn="prefetch", level="l2", mem_size=64)

# ---- x87 (GAS AT&T mnemonics; stack modeled exactly; extended precision with the control word) ----
_X87_MEM = {"s": 4, "l": 8, "t": 10}
for _suf, _sz in _X87_MEM.items():
    _add("fld" + _suf, "x87_load", ["r:m"], fn="x87", op="fld", mem_size=_sz)
    _add("fst" + _suf, "x87_store", ["w:m"], fn="x87", op="fst", mem_size=_sz, pop=False)
    _add("fstp" + _suf, "x87_store", ["w:m"], fn="x87", op="fst", mem_size=_sz, pop=True)
for _suf, _sz in (("s", 4), ("l", 8), ("q", 8)):
    _add("fild" + _suf, "x87_load", ["r:m"], fn="x87", op="fild", mem_size=_sz)
    _add("fistp" + _suf, "x87_store", ["w:m"], fn="x87", op="fistp", mem_size=_sz, pop=True, note="rounds with the control word's RC")
    _add("fisttp" + _suf, "x87_store", ["w:m"], fn="x87", op="fisttp", mem_size=_sz, pop=True, note="truncates")
    _add("fist" + _suf, "x87_store", ["w:m"], fn="x87", op="fistp", mem_size=_sz, pop=False)
_add("fld", "x87_move", ["r:x"], fn="x87", op="fld")
_add("fst", "x87_move", ["w:x"], fn="x87", op="fst", pop=False)
_add("fstp", "x87_move", ["w:x"], fn="x87", op="fst", pop=True)
_add("fldz", "x87_move", [], fn="x87", op="fldconst", const="zero")
_add("fld1", "x87_move", [], fn="x87", op="fldconst", const="one")
_add("fxch", "x87_move", [["r:x"], []], fn="x87", op="fxch")
_add("fchs", "x87_move", [], fn="x87", op="fchs")
_add("fabs", "x87_move", [], fn="x87", op="fabs")
_add("fsqrt", "x87_sqrt", [], fn="x87", op="fsqrt", note="correctly rounded in the control word's precision and RC; latency.x87_sqrt must be known")
for _op, _cls in (("fadd", "x87_add"), ("fsub", "x87_add"), ("fsubr", "x87_add"), ("fmul", "x87_mul"), ("fdiv", "x87_div"), ("fdivr", "x87_div")):
    _add(_op, _cls, [["rw:x", "r:x"], []], fn="x87", op=_op, pop=False,
         note="AT&T forms: '%st(i), %st' -> st0 = st0 OP st(i); '%st, %st(i)' -> st(i) = st0 OP st(i) for fsub/fdiv and st(i) OP st0 for fsubr/fdivr (GAS reversal); no operands -> faddp-like st(1), st0 with pop")
    _add(_op + "p", _cls, [["rw:x", "r:x"], []], fn="x87", op=_op, pop=True)
    for _suf, _sz in (("s", 4), ("l", 8)):
        _add(_op + _suf, _cls, ["r:m"], fn="x87", op=_op, mem=True, mem_size=_sz, note="memory source: st0 = st0 OP mem (OP reversed for fsubr/fdivr)")
for _op, _sz in (("fiadd", 4), ("fisub", 4), ("fisubr", 4), ("fimul", 4), ("fidiv", 4), ("fidivr", 4)):
    _add(_op + "l", "x87_add" if "mul" not in _op and "div" not in _op else ("x87_mul" if "mul" in _op else "x87_div"), ["r:m"], fn="x87", op=_op[1:], mem=True, mem_int=True, mem_size=_sz)
for _op in ("fcom", "fcomp", "fucom", "fucomp"):
    _add(_op, "x87_compare", [["r:x"], []], fn="x87", op="fcom", pop=_op.endswith("p"), unordered_ok=_op.startswith("fu"), note="sets C0/C2/C3 in the status word")
_add("fcompp", "x87_compare", [], fn="x87", op="fcom", pop=2, unordered_ok=False)
_add("fucompp", "x87_compare", [], fn="x87", op="fcom", pop=2, unordered_ok=True)
for _op in ("fcomi", "fcomip", "fucomi", "fucomip"):
    _add(_op, "x87_compare", ["r:x", "r:x"], fn="x87", op="fcomi", pop=_op.endswith("p"), unordered_ok=_op.startswith("fu"), flags_w=True, note="sets ZF/PF/CF")
_add("fnstsw", "x87_control", ["w:gm"], fn="x87", op="fnstsw", mem_size=2, note="status word: C0 bit 8, C1 bit 9, C2 bit 10, C3 bit 14, TOP bits 11-13")
_add("fnstcw", "x87_control", ["w:m"], fn="x87", op="fnstcw", mem_size=2)
_add("fldcw", "x87_control", ["r:m"], fn="x87", op="fldcw", mem_size=2, note="RC bits 10-11 and PC bits 8-9 take effect for later instructions")
_add("fwait", "x87_move", [], fn="x87", op="nop")
_add("fnclex", "x87_control", [], fn="x87", op="nop")

# ---- fences ------------------------------------------------------------------------------------
_add("lock_add", "fence", ["rw:m", "r:gi"], fn=None, note="lock add used as a publication fence; latency.fence must be known")
_add("mfence", "fence", [], fn=None, note="latency.fence must be known")


def lookup(mnemonic):
    return INSTRUCTIONS.get(mnemonic.lower())


def class_info(cls):
    return CLASSES[cls]


def capabilities_table():
    rows = []
    for name in sorted(INSTRUCTIONS):
        rec = INSTRUCTIONS[name]
        if "alias_of" in rec:
            continue
        rows.append({"mnemonic": name, "class": rec["class"], "pipes": CLASSES[rec["class"]]["pipes"],
                     "functional": rec["fn"] is not None, "note": rec.get("note", "")})
    return rows
