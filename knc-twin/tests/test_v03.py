"""0.3.0: code layout and the front end, calls and stubs, the binary adapter, measured-run inputs,
store and gather rules, the program roll-up, the decision bar. Synthetic model tests unless a
test names a measured row."""
import json
import os
import struct
import sys
import tempfile
import unittest

import helpers
from helpers import issue_cycles, kernel, profile, simulate, FIXTURES, ROOT, SCRIPTS
from knc_model import asm, functional, layout, rollup, timing
from knc_model.errors import InvalidInput, MissingParameter, Unsupported
from knc_model.kernel import Kernel

sys.path.insert(0, SCRIPTS)
import from_binary  # noqa: E402
import validate_heldout  # noqa: E402


def run(k):
    interp, steps, check = functional.run_functional(k)
    return interp, check


def asm_kernel(text, init=None, **extra):
    return kernel(None, init=init or {}, streams=[{"context": 0, "asm": text}], **extra)


class TestParserForms(unittest.TestCase):
    def test_symbolic_immediate_resolves_to_the_symbol_address(self):
        k = asm_kernel("movq $.LC0+8, %rax", init={"symbols": {".LC0": "0x5000"}})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].gpr["rax"], 0x5008)

    def test_symbolic_immediate_needs_its_symbol(self):
        with self.assertRaises(InvalidInput):
            asm_kernel("movq $.LC0, %rax")

    def test_thread_local_access_through_fs(self):
        k = asm_kernel("movq %fs:0, %rax\nmovq tls_var@gottpoff(%rip), %rdx\nmovl %fs:(%rdx), %ecx",
                       init={"registers": {"fs_base": "0x700000"}, "symbols": {"tls_var@gottpoff": "0x6000"},
                             "memory": [{"addr": "0x700000", "u64": ["0x700000"]}, {"addr": "0x6000", "i64": [-64]}, {"addr": "0x6fffc0", "u32": [77]}]})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].gpr["rax"], 0x700000)
        self.assertEqual(interp.contexts[0].gpr["rcx"], 77)

    def test_other_segments_are_rejected(self):
        with self.assertRaises(Unsupported):
            asm.parse_gas("movq %es:0(%rax), %rdx")

    def test_disassembler_spellings(self):
        recs, _ = asm.parse_gas("nopw %cs:0x0(%rax,%rax,1)\ndata16 nopw %cs:0x0(%rax,%rax,1)\nxchg %ax,%ax\nnopl 0x0(%rax)\nretq")
        self.assertEqual([r["op"] for r in recs], ["nop", "nop", "nop", "nop", "ret"])

    def test_indirect_jump_is_explicitly_unsupported(self):
        with self.assertRaises(Unsupported) as cm:
            asm.parse_gas("jmpq *%rax")
        self.assertIn("indirect", cm.exception.message)

    def test_lock_family(self):
        recs, _ = asm.parse_gas("lock xaddl %eax, (%rdi)\nlock cmpxchgq %rcx, (%rdi)\nlock incl (%rdi)\nlock orq $0, (%rsp)")
        self.assertEqual([r["op"] for r in recs], ["lock_xadd", "lock_cmpxchg", "lock_inc", "lock_or"])
        with self.assertRaises(Unsupported):
            asm.parse_gas("lock movq %rax, (%rdi)")


class TestNewSemantics(unittest.TestCase):
    def test_locked_operations_are_exact(self):
        k = asm_kernel("lock xaddl %eax, (%rdi)\nmovl $5, %eax\nlock cmpxchgl %ecx, (%rdi)\nlock incl 4(%rdi)",
                       init={"registers": {"rax": 3, "rdi": "0x1000", "rcx": 99}, "memory": [{"addr": "0x1000", "u32": [2, 10]}]},
                       expected={"memory": [{"addr": "0x1000", "u32": [99, 11]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check)
        self.assertEqual(interp.contexts[0].flags["ZF"], 0)   # inc result 11

    def test_locked_instructions_need_the_fence_latency(self):
        k = asm_kernel("lock addl $0, (%rsp)", init={"registers": {"rsp": "0x2000"}, "memory": [{"addr": "0x2000", "u32": [0]}]})
        with self.assertRaises(MissingParameter) as cm:
            simulate(k)
        self.assertIn("latency.fence", cm.exception.message)

    def test_fxam_classes_and_sahf(self):
        def c(setup):
            k = asm_kernel(setup + "\nfxam\nfnstsw %ax\nsahf", init={"registers": {"rsi": "0x1000"}, "memory": [
                {"addr": "0x1000", "f64": [0.0, 1.5, "inf", "nan", "-2.0"]}]})
            interp, _ = run(k)
            ax = interp.contexts[0].gpr["rax"]
            return (ax >> 14) & 1, (ax >> 10) & 1, (ax >> 8) & 1, (ax >> 9) & 1, interp.contexts[0].flags
        self.assertEqual(c("fldl 0(%rsi)")[:3], (1, 0, 0))    # zero
        self.assertEqual(c("fldl 8(%rsi)")[:3], (0, 1, 0))    # normal
        self.assertEqual(c("fldl 16(%rsi)")[:3], (0, 1, 1))   # infinity
        self.assertEqual(c("fldl 24(%rsi)")[:3], (0, 0, 1))   # NaN
        c3, c2, c0, c1, flags = c("fldl 32(%rsi)")
        self.assertEqual((c3, c2, c0, c1), (0, 1, 0, 1))      # negative normal: C1 = sign
        self.assertEqual((flags["ZF"], flags["PF"], flags["CF"]), (0, 1, 0))   # sahf: ZF=C3, PF=C2, CF=C0

    def test_vpmadd231d(self):
        k = kernel([{"op": "vpmadd231d", "ops": ["zmm0", "zmm1", "zmm2"]}],
                   init={"registers": {"zmm0": {"u32_broadcast": 10}, "zmm1": {"u32_broadcast": 3}, "zmm2": {"u32_broadcast": "0xfffffffe"}}})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].zmm["zmm0"], [4] * 16)   # 10 + 3 * (-2)

    def test_gather_completes_one_cache_line_per_execution(self):
        # sixteen lanes on four lines: the loop runs the gather four times (hardware behaviour, R05)
        idx = [0, 1, 2, 3, 16, 17, 18, 19, 32, 33, 34, 35, 48, 49, 50, 51]
        text = "kmov %eax, %k1\n1:\nvgatherdps (%rsi,%zmm30,4), %zmm0{%k1}\njknzd 1b, %k1"
        k = asm_kernel(text, init={"registers": {"rax": 0xFFFF, "rsi": "0x4000", "zmm30": {"u32": idx}},
                                   "memory": [{"addr": "0x4000", "u32": list(range(64))}]},
                       expected={"registers": {"0": {"zmm0": {"u32": idx}, "k1": 0}}})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok", check)
        gathers = [e for e in interp.traces[0] if e.insn.op == "vgatherdps"]
        self.assertEqual(len(gathers), 4)
        self.assertTrue(all(len(e.lines) == 1 for e in gathers))

    def test_gather_completion_all_is_an_explicit_policy(self):
        idx = [0, 16, 32, 48] * 4
        k = asm_kernel("vgatherdps (%rsi,%zmm30,4), %zmm0{%k1}", numerical_policy={"gather_completion": "all"},
                       init={"registers": {"k1": 0xFFFF, "rsi": "0x4000", "zmm30": {"u32": idx}}, "memory": [{"addr": "0x4000", "u32": list(range(64))}]})
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].k["k1"], 0)


class TestCallsAndStubs(unittest.TestCase):
    TEXT = """
        movq $5, %rdi
        call twice
        addq $1, %rax
        ret
    twice:
        leaq (%rdi,%rdi), %rax
        ret
    """

    def test_call_and_return_inside_the_region(self):
        k = asm_kernel(self.TEXT, entry="function")
        interp, _ = run(k)
        self.assertEqual(interp.contexts[0].gpr["rax"], 11)
        ops = [e.insn.op for e in interp.traces[0]]
        self.assertEqual(ops, ["mov", "call", "lea", "ret", "add", "ret"])
        res, sim, _ = simulate(k)
        self.assertGreater(res["completion_cycles"], 0)

    def test_ret_without_an_entry_sentinel_is_an_error(self):
        k = asm_kernel("ret", init={"registers": {"rsp": "0x3000"}, "memory": [{"addr": "0x3000", "u64": [1234]}]})
        with self.assertRaises(InvalidInput):
            run(k)

    def test_external_call_needs_a_declared_stub(self):
        with self.assertRaises(Unsupported) as cm:
            asm_kernel("call exp\nret", entry="function")
        self.assertIn("calls", cm.exception.message)

    def test_stub_without_a_cost_stops_the_timing(self):
        k = asm_kernel("call helper\nret", entry="function", calls={"helper": {"model": "none"}})
        with self.assertRaises(MissingParameter) as cm:
            simulate(k)
        self.assertIn("calls.helper.cycles", cm.exception.message)

    def test_stub_cost_is_charged_and_reported_as_inexact(self):
        k = asm_kernel("call helper\nret", entry="function", calls={"helper": {"model": "none", "cycles": 100}})
        res, sim, _ = simulate(k)
        base = simulate(asm_kernel("nop\nret", entry="function"))[0]["completion_cycles"]
        self.assertGreaterEqual(res["completion_cycles"], base + 98)
        interp, _ = run(k)
        self.assertEqual(interp.stub_calls, {"helper": 1})
        self.assertEqual(interp.approximate_stubs, {"helper"})

    def test_noreturn_stub_reached_is_an_error(self):
        k = asm_kernel("call __assert_fail\nret", entry="function", calls={"__assert_fail": {"model": "noreturn"}})
        with self.assertRaises(Unsupported) as cm:
            run(k)
        self.assertIn("noreturn", cm.exception.message)

    def test_memcpy_stub_is_exact_and_sqrt_is_correctly_rounded(self):
        k = asm_kernel("call memcpy\ncall sqrt\nret", entry="function",
                       calls={"memcpy": {"model": "memcpy", "cycles": 10, "cycles_per_byte": 0.5}, "sqrt": {"model": "libm.f64.sqrt", "cycles": 70}},
                       init={"registers": {"rdi": "0x2000", "rsi": "0x1000", "rdx": 16, "zmm0": {"u64": ["0x4000000000000000"] + [0] * 7}},
                             "memory": [{"addr": "0x1000", "u64": [7, 9]}, {"addr": "0x2000", "u64": [0, 0]}]},
                       expected={"memory": [{"addr": "0x2000", "u64": [7, 9]}]})
        interp, check = run(k)
        self.assertEqual(check["status"], "ok")
        lanes = interp.contexts[0].zmm["zmm0"]
        self.assertEqual(lanes[0] | (lanes[1] << 32), 0x3FF6A09E667F3BCD)   # sqrt(2) correctly rounded
        self.assertEqual(interp.approximate_stubs, set())
        res, sim, _ = simulate(k)
        self.assertGreaterEqual(res["per_context"]["0"]["stall_cycles"]["stub_call"], 10 + 8 + 70 - 3)   # stall cycles exclude the issue cycles themselves


class TestInputBinding(unittest.TestCase):
    def test_file_blocks_and_file_expected(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "idx.bin"), "wb") as f:
                f.write(struct.pack("<4i", 3, 1, 2, 0))
            with open(os.path.join(d, "vals.txt"), "w") as f:
                f.write("1.5, 2.5\n3.5 4.5\n")
            with open(os.path.join(d, "want.bin"), "wb") as f:
                f.write(struct.pack("<d", 4.5))
            raw = {"schema": helpers.SCHEMA, "name": "bind", "unit_of_work": {"description": "t", "count": 1},
                   "init": {"registers": {"rsi": "0x1000", "rdi": "0x2000", "rdx": "0x3000"},
                            "memory": [{"addr": "0x1000", "file": "idx.bin"}, {"addr": "0x2000", "file": "vals.txt", "format": "f64"}]},
                   "expected": {"memory": [{"addr": "0x3000", "file": "want.bin"}]},
                   "streams": [{"context": 0, "asm": "movslq 0(%rsi), %rax\nfldl (%rdi,%rax,8)\nfstpl (%rdx)"}]}
            path = os.path.join(d, "k.json")
            with open(path, "w") as f:
                json.dump(raw, f)
            k = Kernel(raw, path)
            interp, check = run(k)
            self.assertEqual(check["status"], "ok", check)
            self.assertEqual([r["file"] for r in interp.input_files], ["idx.bin", "vals.txt"])
            self.assertEqual(len(interp.input_files[0]["sha256"]), 64)
            raw["expected"] = {"memory": [{"addr": "0x3000", "hex": struct.pack("<d", 1.5).hex()}]}
            self.assertEqual(run(Kernel(raw, path))[1]["status"], "mismatch")

    def test_missing_file_is_invalid_input(self):
        raw = {"schema": helpers.SCHEMA, "name": "bind", "unit_of_work": {"description": "t", "count": 1},
               "init": {"memory": [{"addr": "0x1000", "file": "no-such.bin"}]}, "streams": [{"context": 0, "asm": "nop"}]}
        with self.assertRaises(InvalidInput):
            run(Kernel(raw, None))


def row_loop(order, enc=None):
    """The S12-31 row loop body with the given order of the last four instructions."""
    body = {"fmul": "fmull (%rcx,%rax,8)", "add": "addq $1, %rax", "cmp": "cmpl %eax, %esi", "faddp": "faddp %st, %st(1)", "mov": "movl %eax, %r11d"}
    text = "fldz\n1:\nmovslq (%r8,%rax,4), %rdx\nfldl (%rdx,%rdx,1)\n" + "\n".join(body[o] for o in order) + "\njg 1b\nfstpl (%r9)"
    n = 12
    return asm_kernel(text, init={"registers": {"rsi": n, "rcx": "0x1000", "r8": "0x2000", "r9": "0x3000", "rax": 0},
                                  "memory": [{"addr": "0x1000", "f64": [1.0] * n}, {"addr": "0x2000", "i32": [0x2000] * n}, {"addr": "0x4000", "f64": [2.0]}]},
                      scenario={"memory": {"type": "fixed_level", "level": "l1"}})


class TestFrontEndAndPairing(unittest.TestCase):
    def per_iteration(self, order):
        res, sim, _ = simulate(row_loop(order))
        ic = issue_cycles(sim)
        loads = sorted(c for (ctx, i, n), c in ic.items() if sim.kernel.streams[0].by_id[i].op == "movslq")
        return loads[6] - loads[5]

    def test_x87_issues_alone_so_compare_next_to_jump_saves_one_issue(self):
        # measured (S12-31, card windows 3 and 5): gas order 488.9, adj and mid 433.5/432.5 cycles per 27 products (2.07 per product)
        gas = self.per_iteration(["fmul", "add", "cmp", "faddp"])
        adj = self.per_iteration(["fmul", "faddp", "add", "cmp"])
        mid = self.per_iteration(["fmul", "add", "faddp", "cmp"])
        self.assertEqual(gas - adj, 2)
        self.assertEqual(mid, adj)

    def test_instruction_before_the_compare_takes_it_as_partner(self):
        adj = self.per_iteration(["fmul", "faddp", "add", "cmp"])
        self.assertEqual(self.per_iteration(["fmul", "faddp", "add", "mov", "cmp"]), adj + 2)

    def test_slow_prefix_decode(self):
        def cycles(prefixes):
            recs = [{"id": "a", "op": "add", "ops": ["rax", {"imm": 1}], "encoding": {"addr": 0x400000, "bytes": 4, "slow_prefixes": 0}},
                    {"id": "n", "op": "nop", "ops": [], "encoding": {"addr": 0x400004, "bytes": 5 + prefixes, "slow_prefixes": prefixes}},
                    {"id": "b", "op": "add", "ops": ["rbx", {"imm": 1}], "encoding": {"addr": 0x400010, "bytes": 4, "slow_prefixes": 0}}]
            res, sim, _ = simulate(kernel(recs))
            return issue_cycles(sim)[(0, "n", 0)]
        self.assertEqual(cycles(0), 2)
        self.assertEqual(cycles(1), 2, "one two-cycle prefix is hidden by the two-cycle spacing")
        self.assertEqual(cycles(3), 6, "two cycles per prefix after the previous issue")

    def test_nops_never_pair(self):
        recs = [{"id": "n%d" % i, "op": "nop", "ops": []} for i in range(5)]
        res, sim, _ = simulate(kernel(recs))
        self.assertEqual(res["per_context"]["0"]["pairs"], 0)
        self.assertEqual(issue_cycles(sim)[(0, "n4", 0)], 8)

    def test_forward_taken_branch_costs_the_core_a_cycle_only_with_several_threads(self):
        # a loop back-edge pays nothing (S8-01 C9 at two threads); a taken forward branch refills the prefetch buffer
        back = "1:\naddq $1, %rax\ncmpq $40, %rax\njne 1b"
        self.assertEqual(simulate(kernel(None, streams=[{"context": c, "asm": back} for c in range(4)]))[0]["frontend"]["taken_branch_bubbles"], 0)
        text = "1:\naddq $1, %rax\ntestq %rax, %rax\njns 2f\nnop\n2:\ncmpq $40, %rax\njne 1b"
        one = simulate(asm_kernel(text))[0]["completion_cycles"]
        self.assertEqual(one, simulate(asm_kernel(text), prof=profile(overlays=[os.path.join(ROOT, "profiles", "overlay-no-branch-bubble.json")]))[0]["completion_cycles"])
        streams = [{"context": c, "asm": text} for c in range(4)]
        four = simulate(kernel(None, streams=streams))[0]["completion_cycles"]
        four0 = simulate(kernel(None, streams=streams), prof=profile(overlays=[os.path.join(ROOT, "profiles", "overlay-no-branch-bubble.json")]))[0]["completion_cycles"]
        self.assertGreater(four, four0 * 1.2)

    def test_icache_cold_code_stalls_once_per_line(self):
        recs = [{"id": "i%d" % i, "op": "add", "ops": ["rax", {"imm": 1}], "encoding": {"addr": 0x400000 + 40 * i, "bytes": 4, "slow_prefixes": 0}} for i in range(4)]
        warm = simulate(kernel(recs))[0]
        cold = simulate(kernel(recs, scenario={"frontend": {"icache": "cold_l2"}}))[0]
        self.assertEqual(cold["frontend"]["icache_misses"], 2)     # the four instructions lie on two 64-byte lines
        self.assertGreater(cold["completion_cycles"], warm["completion_cycles"] + 2 * 20)
        with self.assertRaises(Unsupported):
            simulate(kernel([{"op": "nop", "ops": []}], scenario={"frontend": {"icache": "cold_l2"}}))


class TestStoreAndGatherRules(unittest.TestCase):
    def test_load_waits_four_cycles_after_a_store_and_pairs_with_the_next_store(self):
        # S6-03 spill_reload.rt: 4.20 / 4.26 cycles per store plus reload at two / four threads
        text = "\n".join("vmovaps %%zmm%d, %d(%%rsp)\nvmovaps %d(%%rsp), %%zmm%d" % (i % 8, 128 * (i % 8), 128 * (i % 8), i % 8) for i in range(16))
        k = asm_kernel(text, init={"registers": {"rsp": "0x8000"}}, memory_default=0, scenario={"memory": {"type": "fixed_level", "level": "l1"}})
        res, sim, _ = simulate(k)
        loads = sorted(e["cycle"] for e in sim.issue_log if e["pipe"] == "U" and e["op"] == "vmovaps")
        self.assertEqual(loads[9] - loads[8], 4)
        self.assertGreater(res["per_context"]["0"]["pairs"], 10)

    def test_store_to_load_data_path_is_unchanged(self):
        # S6-03 spill_reload.lat 12.11: store, reload of the same register, repeated
        text = "\n".join(["vmovaps %zmm0, 0(%rsp)", "vmovaps 0(%rsp), %zmm0"] * 8)
        k = asm_kernel(text, init={"registers": {"rsp": "0x8000"}}, memory_default=0, scenario={"memory": {"type": "fixed_level", "level": "l1"}})
        res, sim, _ = simulate(k)
        stores = [e["cycle"] for e in sim.issue_log if e["id"] in ("L%d" % (2 * i + 1) for i in range(8))]
        self.assertEqual(stores[5] - stores[4], 12)

    def test_scattered_gather_costs_eleven_cycles_per_line_at_one_thread(self):
        # S6-03 gather_scattered.rt 175.14 for sixteen lines, gather_all.rt 7.08 for one
        idx = [16 * i for i in range(16)]
        text = "kmov %eax, %k1\n1:\nvgatherdps (%rsi,%zmm30,4), %zmm0{%k1}\njknzd 1b, %k1"
        k = asm_kernel(text, init={"registers": {"rax": 0xFFFF, "rsi": "0x4000", "zmm30": {"u32": idx}}, "memory": [{"addr": "0x4000", "u32": list(range(256))}]},
                       scenario={"memory": {"type": "fixed_level", "level": "l1"}})
        res, sim, _ = simulate(k)
        g = [e["cycle"] for e in sim.issue_log if e["op"] == "vgatherdps"]
        self.assertEqual(len(g), 16)
        self.assertEqual(g[9] - g[8], 11)

    def test_default_memory_domain_models_tlb_prefetcher_and_service(self):
        k = asm_kernel("vmovaps 0(%rsi), %zmm0", init={"registers": {"rsi": "0x100000"}}, memory_default=0,
                       scenario={"memory": {"type": "line_tracking"}})
        res, sim, _ = simulate(k)
        self.assertEqual(sorted(res["memory"]["submodels"]), ["hardware_prefetcher", "memory_service", "tlb"])
        k2 = asm_kernel("vmovaps 0(%rsi), %zmm0", init={"registers": {"rsi": "0x100000"}}, memory_default=0,
                        scenario={"memory": {"type": "line_tracking", "hardware_prefetcher": "off", "tlb": "off", "memory_service": "unlimited"}})
        self.assertEqual(simulate(k2)[0]["memory"]["submodels"], [])


class TestLayoutAndBinaryAdapter(unittest.TestCase):
    DIS = os.path.join(FIXTURES, "binary", "knc_spmv.dis")
    OBJ = os.path.join(FIXTURES, "binary", "knc_spmv.o")

    def test_encoding_facts(self):
        e = layout.encoding_of(bytes.fromhex("662e0f1f840000000000"), "nopw   %cs:0x0(%rax,%rax,1)", 0x66)
        self.assertEqual((e["bytes"], e["slow_prefixes"], e["prefixes"]), (10, 2, ["66", "cs"]))
        e = layout.encoding_of(bytes.fromhex("4883c001"), "add    $0x1,%rax")
        self.assertEqual((e["slow_prefixes"], e.get("imm"), e.get("disp")), (0, True, None))
        e = layout.encoding_of(bytes.fromhex("488b8610020000"), "mov    0x210(%rsi),%rax")
        self.assertTrue(e["disp32"])
        e = layout.encoding_of(bytes.fromhex("4a8b74cd00"), "mov    0x0(%rbp,%r9,8),%rsi")
        self.assertTrue(e["disp"] and not e.get("disp32"))

    def test_object_file_function_with_layout_calls_and_constants(self):
        with open(self.DIS) as f:
            conv = from_binary.Converter(self.OBJ, f.read())
        k, rows, summary = conv.convert("knc_spmv", profile=profile())
        self.assertTrue(all(summary["complete"][c] for c in ("parser", "isa", "functional", "timing")))
        prov = k["provenance"]
        self.assertEqual(prov["padding_nops"], 3)
        self.assertEqual(prov["slow_prefix_instructions"], 1)
        self.assertEqual(k["calls"]["__assert_fail"]["model"], "noreturn")
        self.assertEqual(k["entry"], "function")
        recs = k["streams"][0]["instructions"]
        self.assertTrue(all("encoding" in r for r in recs))
        self.assertIn("ret", [r["op"] for r in recs])
        sym_imm = [o for r in recs for o in r["ops"] if isinstance(o, dict) and o.get("imm_symbol")]
        self.assertTrue(sym_imm, "the assert path loads string addresses: symbolic immediates")
        self.assertTrue(all(s["imm_symbol"] in k["init"]["symbols"] for s in sym_imm))
        self.assertTrue(any("hex" in m for m in k["init"]["memory"]), "string constants copied from the object")
        Kernel(dict(k, init=dict(k["init"], registers={})), None)

    def test_missing_function_lists_what_is_there(self):
        with open(self.DIS) as f:
            conv = from_binary.Converter(self.OBJ, f.read())
        with self.assertRaises(InvalidInput) as cm:
            conv.convert("nope")
        self.assertIn("knc_spmv", cm.exception.message)


class TestRollupAndBar(unittest.TestCase):
    def test_combine(self):
        regs = [{"name": "a", "share": 0.4, "ratio": 0.5, "band_pct": 10.0}, {"name": "b", "share": 0.2, "ratio": 1.0, "band_pct": 0.0}]
        out = rollup.combine(regs, {"measured_per_unit": 10.0, "unit": "s/step"})
        self.assertAlmostEqual(out["predicted_time_ratio"], 0.8)
        self.assertAlmostEqual(out["predicted_candidate_per_unit"], 8.0)
        self.assertAlmostEqual(out["predicted_time_ratio_band"][0], 0.78)
        self.assertAlmostEqual(out["predicted_time_ratio_band"][1], 0.82)
        self.assertAlmostEqual(out["unmodeled_share_assumed_unchanged"], 0.4)

    def test_memory_floor_caps_the_prediction(self):
        regs = [{"name": "a", "share": 1.0, "ratio": 0.1, "band_pct": 0.0}]
        out = rollup.combine(regs, {"measured_per_unit": 1.0}, {"bytes_per_unit": 50e9, "traffic": "read_modify_write"}, 100.0)
        self.assertEqual(out["binding"], "card memory bandwidth")
        self.assertAlmostEqual(out["predicted_candidate_per_unit_capped"], 0.5)

    def test_shares_over_one_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.json")
            with open(p, "w") as f:
                json.dump({"schema": "knc-twin.rollup/1", "regions": [{"name": "a", "share": 0.7, "baseline": "x"}, {"name": "b", "share": 0.6, "baseline": "y"}]}, f)
            with self.assertRaises(InvalidInput):
                rollup.load_rollup(p)

    def test_decision_bar(self):
        def row(name, case, m, p, cls="held_out"):
            return {"name": name, "suite": "compiled", "case": case, "class": cls, "status": "ok", "measured": {"threads_1": m}, "predicted": {"A": {"threads_1": p}}}
        rows = [row("c-1/a", "c-1", 100.0, 104.0), row("c-1/b", "c-1", 120.0, 123.0), row("c-1/c", "c-1", 121.0, 119.0), row("c-1/cal", "c-1", 50.0, 500.0, "calibration")]
        bar = validate_heldout.decision_bar(rows, {"g": ["c-1/a", "c-1/b", "c-1/c"]})
        self.assertEqual(bar["held_out_compiled_rows"], 3)
        self.assertEqual((bar["pairs_over_5pct"], bar["right_winner"]), (2, 2))   # b against c is within 5%: not a decision pair
        self.assertTrue(bar["error_met"] and bar["ranking_met"])
        self.assertFalse(bar["met"], "three loops are not enough to rely on")
        rows[1] = row("c-1/b", "c-1", 120.0, 90.0)
        bar = validate_heldout.decision_bar(rows, {"g": ["c-1/a", "c-1/b", "c-1/c"]})
        self.assertEqual(bar["right_winner"], 1)
        self.assertFalse(bar["ranking_met"])

    def test_transferred_profiles_run_and_say_so(self):
        for pid in ("card-3120-documented", "card-5110p-literature"):
            prof = profile(pid)
            self.assertIn("transferred", prof.calibration["state"])
            res, sim, _ = simulate(kernel([{"op": "vaddps", "ops": ["zmm0", "zmm1", "zmm2"]}]), prof=prof)
            self.assertEqual(res["completion_cycles"], 4)


if __name__ == "__main__":
    unittest.main()


class TestDefectsReportedByPhiWeather(unittest.TestCase):
    """Study of 13 WRF routines, 2026-11-16 (STUDY.md section 9)."""

    def test_cold_level_l2_is_an_l2_fill_not_a_memory_fill(self):
        recs = [{"op": "vmovaps", "ops": ["zmm%d" % (i % 8), {"base": "rax", "disp": 64 * i}], "id": "ld%d" % i} for i in range(8)]
        base = {"registers": {"rax": "0x100000"}}
        off = {"tlb": "off", "hardware_prefetcher": "off", "memory_service": "unlimited"}
        mem = simulate(kernel(recs, init=base, memory_default=0, scenario={"memory": dict({"type": "line_tracking", "cold_level": "memory"}, **off)}))[0]
        l2 = simulate(kernel(recs, init=base, memory_default=0, scenario={"memory": dict({"type": "line_tracking", "cold_level": "l2"}, **off)}))[0]
        self.assertLess(l2["completion_cycles"], mem["completion_cycles"] / 3)
        self.assertEqual(l2["memory"]["stats"]["memory"], 0)
        self.assertEqual(l2["memory"]["stats"]["cold_l2_fills"], 8)

    def test_context_stalls_are_attributed_to_their_cause(self):
        text = "fldz\n" + "fmull 0(%rsi)\n" * 8 + "fstp %st(0)"
        k = asm_kernel(text, init={"registers": {"rsi": "0x1000"}, "memory": [{"addr": "0x1000", "f64": [1.5]}]},
                       scenario={"memory": {"type": "fixed_level", "level": "l1"}})
        res, sim, _ = simulate(k)
        st = res["per_context"]["0"]["stall_cycles"]
        self.assertGreater(st.get("x87_serial", 0), 0)
        self.assertEqual(st.get("miss_stall", 0), 0, "no cache miss: nothing is attributed to miss_stall")
        k2 = asm_kernel("call helper\nret", entry="function", calls={"helper": {"model": "none", "cycles": 50}})
        st2 = simulate(k2)[0]["per_context"]["0"]["stall_cycles"]
        self.assertGreaterEqual(st2.get("stub_call", 0), 48)
        self.assertEqual(st2.get("miss_stall", 0), 0)
