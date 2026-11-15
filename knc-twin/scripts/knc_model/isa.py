"""The supported IMCI/K1OM instruction subset.

Each entry says: timing class, Intel-order operand roles, whether exact functional
semantics are implemented, and notes. Anything not in this table is rejected as
unsupported: it never gets a default cost.

Operand role syntax (Intel operand order: destination first):
  w:   written          r:   read          rw:  read and written
  a:   address only (lea)                   t:   branch target label
  kinds after the colon: g (gpr), v (zmm), k (mask), m (memory), i (immediate), gm (gpr or mem),
  vm (zmm or mem), km (k or gpr), mi (memory with vector index, gather/scatter)
"""

# timing class -> (pipes, latency parameter or None, extra)
#   pipes: "U" (U only), "UV" (either), "UV_both" (occupies both pipes, serializing)
CLASSES = {
    "scalar_alu":        {"pipes": "UV", "latency": "latency.scalar_alu", "kind": "scalar"},
    "scalar_imul":       {"pipes": "U", "latency": "latency.scalar_imul", "kind": "scalar"},
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
    "prefetch_l1":       {"pipes": "UV", "latency": None, "kind": "prefetch"},
    "prefetch_l2":       {"pipes": "UV", "latency": None, "kind": "prefetch"},
    "x87_add":           {"pipes": "U", "latency": "latency.x87_add", "kind": "x87"},
    "x87_mul":           {"pipes": "U", "latency": "latency.x87_mul", "kind": "x87", "occupancy": "occupancy.x87_mul"},
    "x87_div":           {"pipes": "U", "latency": "latency.x87_div", "kind": "x87", "occupancy": "occupancy.x87_div"},
    "x87_move":          {"pipes": "U", "latency": "latency.x87_add", "kind": "x87"},
    "fence":             {"pipes": "UV_both", "latency": "latency.fence", "kind": "fence"},
}

FLAGS = ("ZF", "SF", "CF", "OF")

# A thin table of records. 'fn' names the functional handler in functional.py (None = timing only).
# 'ops' are Intel-order roles. 'flags_w'/'flags_r' for the scalar flag register.
INSTRUCTIONS = {}


def _add(name, cls, ops, fn=None, flags_w=False, flags_r=False, mem_size=None, note="", aliases=(), **extra):
    rec = {"name": name, "class": cls, "ops": ops, "fn": fn, "flags_w": flags_w, "flags_r": flags_r,
           "mem_size": mem_size, "note": note}
    rec.update(extra)
    INSTRUCTIONS[name] = rec
    for a in aliases:
        INSTRUCTIONS[a] = dict(rec, name=a, alias_of=name)


# ---- scalar integer -------------------------------------------------------------
for _n in ("add", "sub", "and", "or", "xor"):
    _add(_n, "scalar_alu", ["rw:gm", "r:gmi"], fn="alu2", flags_w=True)
_add("cmp", "scalar_alu", ["r:gm", "r:gmi"], fn="cmp", flags_w=True)
_add("test", "scalar_alu", ["r:gm", "r:gi"], fn="test", flags_w=True)
_add("mov", "scalar_alu", ["w:gm", "r:gmi"], fn="mov", note="register or memory move; memory forms take the load/store class")
_add("lea", "scalar_alu", ["w:g", "a:m"], fn="lea")
_add("inc", "scalar_alu", ["rw:gm"], fn="incdec", flags_w=True, note="does not change CF")
_add("dec", "scalar_alu", ["rw:gm"], fn="incdec", flags_w=True, note="does not change CF")
_add("neg", "scalar_alu", ["rw:gm"], fn="neg", flags_w=True)
_add("not", "scalar_alu", ["rw:gm"], fn="not")
for _n in ("shl", "shr", "sar"):
    _add(_n, "scalar_alu", ["rw:gm", "r:i"], fn="shift", flags_w=True, note="immediate count only; CF/OF after count>1 follow the SDM for CF, OF is left unchanged (documented undefined)")
_add("imul", "scalar_imul", ["rw:g", "r:gm"], fn="imul", flags_w=True, note="two-operand form; result truncated to operand width")
_add("movzx", "scalar_alu", ["w:g", "r:gm"], fn=None, note="timing only; functional not implemented")
_add("movsxd", "scalar_alu", ["w:g", "r:gm"], fn="movsxd", mem_size=4,
     note="AT&T movslq: sign-extends a 32-bit register or memory source into a 64-bit register; costed as movzx (scalar ALU, memory form a scalar load)")

# ---- branches ---------------------------------------------------------------------
_add("jmp", "branch", ["t"], fn="jmp")
for _n, _cond in (("jz", "zf"), ("je", "zf"), ("jnz", "nzf"), ("jne", "nzf"), ("jl", "lt"), ("jge", "ge"),
                  ("jg", "gt"), ("jle", "le"), ("jb", "cf"), ("jc", "cf"), ("jae", "ncf"), ("jnc", "ncf"),
                  ("js", "sf"), ("jns", "nsf"), ("jnb", "ncf"), ("jnae", "cf"),
                  ("jbe", "be"), ("jna", "be"), ("ja", "a"), ("jnbe", "a")):
    _add(_n, "branch", ["t"], fn="jcc", flags_r=True, cond=_cond)
_add("jkzd", "branch", ["r:k", "t"], fn="jk", cond="kz", note="branch if mask is zero")
_add("jknzd", "branch", ["r:k", "t"], fn="jk", cond="knz", note="branch if mask is nonzero")

# ---- mask ops ------------------------------------------------------------------------
_add("kmov", "mask_op", ["w:km", "r:km"], fn="kmov", note="k<-k, k<-gpr (low 16 bits), gpr<-k (zero-extended)")
for _n in ("kand", "kor", "kxor", "kxnor", "kandn", "kandnr"):
    _add(_n, "mask_op", ["rw:k", "r:k"], fn="klogic")
_add("knot", "mask_op", ["w:k", "r:k"], fn="knot")
_add("kortest", "mask_op", ["r:k", "r:k"], fn="kortest", flags_w=True, note="ZF = (k1|k2)==0, CF = (k1|k2)==0xffff")

# ---- vector FP32 ------------------------------------------------------------------------
_add("vaddps", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f32", opk="add", mem_size=64)
_add("vsubps", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f32", opk="sub", mem_size=64)
_add("vmulps", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f32", opk="mul", mem_size=64)
_add("vaddpd", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f64", opk="add", mem_size=64)
_add("vsubpd", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f64", opk="sub", mem_size=64)
_add("vmulpd", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vfp2", fmt="f64", opk="mul", mem_size=64)
for _fmtname, _suffix in (("f32", "ps"), ("f64", "pd")):
    for _base, _negp, _negc in (("vfmadd", False, False), ("vfmsub", False, True), ("vfnmadd", True, False), ("vfnmsub", True, True)):
        # 132: op1 = op1*op3 + op2 ; 213: op1 = op2*op1 + op3 ; 231: op1 = op2*op3 + op1
        _add("%s132%s" % (_base, _suffix), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmtname, form="132", negp=_negp, negc=_negc, mem_size=64)
        _add("%s213%s" % (_base, _suffix), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmtname, form="213", negp=_negp, negc=_negc, mem_size=64)
        _add("%s231%s" % (_base, _suffix), "vector_arith", ["rw:v", "r:v", "r:vm"], fn="vfma", fmt=_fmtname, form="231", negp=_negp, negc=_negc, mem_size=64)
_add("vcmpps", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vcmp", fmt="f32", mem_size=64, note="predicate immediate: 0 eq, 1 lt, 2 le, 3 unord, 4 neq, 5 nlt, 6 nle, 7 ord")
_add("vcmppd", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vcmp", fmt="f64", mem_size=64)
_add("vcvtfxpntdq2ps", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_i2f", mem_size=64, note="imm bits 1:0 rounding (0 rn,1 rd,2 ru,3 rz); exponent adjust bits must be 0")
_add("vcvtfxpntps2dq", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_f2i", signed=True, mem_size=64)
_add("vcvtfxpntps2udq", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_f2i", signed=False, mem_size=64)
_add("vcvtfxpntudq2ps", "vector_arith", ["w:v", "r:vm", "r:i"], fn="vcvt_u2f", mem_size=64)
_add("vcvtfxpntpd2dq", "vector_convert_df", ["w:v", "r:vm", "r:i"], fn=None, mem_size=64, note="timing only")
_add("vcvtfxpntpd2udq", "vector_convert_df", ["w:v", "r:vm", "r:i"], fn=None, mem_size=64, note="timing only")
_add("vrcp23ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only (23-bit approximate reciprocal; exact bit pattern not modeled)")
_add("vrsqrt23ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vlog2ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vexp223ps", "vector_long", ["w:v", "r:vm"], fn=None, mem_size=64, note="timing only")
_add("vpermd", "vector_long", ["w:v", "r:v", "r:vm"], fn="vpermd", mem_size=64, note="dword permute: dst[i] = src2[idx[i] & 15]")
_add("vpermf32x4", "vector_long", ["w:v", "r:vm", "r:i"], fn=None, mem_size=64, note="timing only")

# ---- vector int32 -----------------------------------------------------------------------
for _n, _k in (("vpaddd", "add"), ("vpsubd", "sub"), ("vpandd", "and"), ("vpord", "or"), ("vpxord", "xor"),
               ("vpmulld", "mullo"), ("vpminsd", "mins"), ("vpmaxsd", "maxs"), ("vpminud", "minu"), ("vpmaxud", "maxu"),
               ("vpsllvd", "shlv"), ("vpsrlvd", "shrv"), ("vpsravd", "sarv")):
    _add(_n, "vector_arith", ["w:v", "r:v", "r:vm"], fn="vint2", opk=_k, mem_size=64)
for _n, _k in (("vpslld", "shl"), ("vpsrld", "shr"), ("vpsrad", "sar")):
    _add(_n, "vector_arith", ["w:v", "r:vm", "r:i"], fn="vshift_imm", opk=_k, mem_size=64)
_add("vpandnd", "vector_arith", ["w:v", "r:v", "r:vm"], fn="vint2", opk="andn", mem_size=64)
_add("vpcmpd", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vpcmp", signed=True, mem_size=64, note="predicate: 0 eq, 1 lt, 2 le, 4 ne, 5 nlt, 6 nle")
_add("vpcmpud", "vector_arith", ["w:k", "r:v", "r:vm", "r:i"], fn="vpcmp", signed=False, mem_size=64)
_add("vpcmpeqd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=0, mem_size=64)
_add("vpcmpgtd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=6, mem_size=64)
_add("vpcmpltd", "vector_arith", ["w:k", "r:v", "r:vm"], fn="vpcmp", signed=True, fixed_pred=1, mem_size=64)
_add("vpbroadcastd", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=4, mem_size=4, note="dword broadcast from memory")
_add("vbroadcastss", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=4, mem_size=4)
_add("vbroadcastsd", "vector_load", ["w:v", "r:m"], fn="vbroadcast", elem=8, mem_size=8)

# ---- vector memory --------------------------------------------------------------------------
for _n in ("vmovaps", "vmovapd", "vmovdqa32", "vmovdqa64"):
    _add(_n, "vector_load", ["w:vm", "r:vm"], fn="vmov", mem_size=64, note="register<->aligned memory, masked merge; store forms take the vector_store class")
_add("vmovnrngoaps", "vector_store", ["w:m", "r:v"], fn="vstore_ngo", mem_size=64, note="no-read, non-globally-ordered store; functionally a store, timing as a store (no RFO modeled)")
_add("vmovnraps", "vector_store", ["w:m", "r:v"], fn="vstore_ngo", mem_size=64)
# The ps forms move the same 32-bit elements without conversion (R27 VLOADUNPACKLPS/HPS,
# VPACKSTORELPS/HPS); GCC-KNC emits them for unaligned float loads and stores.
_add("vloadunpackld", "vector_load", ["rw:v", "r:m"], fn=None, mem_size=64, note="timing only", aliases=("vloadunpacklps",))
_add("vloadunpackhd", "vector_load", ["rw:v", "r:m"], fn=None, mem_size=64, note="timing only", aliases=("vloadunpackhps",))
_add("vpackstoreld", "vector_packstore", ["w:m", "r:v"], fn=None, mem_size=64, note="timing only", aliases=("vpackstorelps",))
_add("vpackstorehd", "vector_packstore", ["w:m", "r:v"], fn=None, mem_size=64, note="timing only", aliases=("vpackstorehps",))
_add("vgatherdps", "vector_gather", ["w:v", "r:mi"], fn="vgather", elem=4, note="dword gather with masked completion: lanes gathered have their mask bit cleared")
_add("vgatherdpd", "vector_gather", ["w:v", "r:mi"], fn=None, elem=8, note="timing only")
_add("vscatterdps", "vector_gather", ["w:mi", "r:v"], fn=None, elem=4, note="timing only; same class as gather (per-line occupancy)")
for _n in ("vprefetch0", "vprefetche0"):
    _add(_n, "prefetch_l1", ["r:m"], fn="prefetch", level="l1", mem_size=64)
for _n in ("vprefetch1", "vprefetch2", "vprefetchnta", "vprefetche1", "vprefetche2", "vprefetchenta"):
    _add(_n, "prefetch_l2", ["r:m"], fn="prefetch", level="l2", mem_size=64)

# ---- x87 (timing only; dependencies given explicitly or serialized) ----------------------------
for _n in ("fadd", "faddp", "fsub", "fsubp", "fsubr", "fsubrp"):
    _add(_n, "x87_add", ["x87"], fn=None, note="timing only; x87 instructions are treated as serially dependent within a context unless deps are given")
for _n in ("fmul", "fmulp"):
    _add(_n, "x87_mul", ["x87"], fn=None)
for _n in ("fdiv", "fdivp", "fdivr", "fdivrp"):
    _add(_n, "x87_div", ["x87"], fn=None)
for _n in ("fld", "fstp", "fst", "fxch", "fldz", "fld1", "fild", "fistp"):
    _add(_n, "x87_move", ["x87"], fn=None)

# ---- fences ------------------------------------------------------------------------------------
_add("lock_add", "fence", ["rw:m", "r:gi"], fn=None, note="lock addl used as a publication fence; latency.fence must be known")
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
