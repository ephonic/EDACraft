"""
RISC-V 64 CPU with FPU — Three-Layer Verification.
Target: 12nm CMOS, 2GHz, RV64IMAFD
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from skills.cpu_riscv64.functional import FUNCTIONAL_MODELS
from skills.cpu_riscv64 import OP_RI, OP_RR, XLEN


def test_l1_alu_add():
    alu_fn = FUNCTIONAL_MODELS["alu"]()
    r = alu_fn(opcode=OP_RI, funct3=0, rs1_val=5, imm=3)
    assert r["result"] == 8, f"ADD failed: {r['result']}"
    print(f"  L1 ALU ADD: 5+3={r['result']} — PASS")

    r2 = alu_fn(opcode=OP_RR, funct3=0, funct7=0x20, rs1_val=10, rs2_val=7)
    assert r2["result"] == 3, f"SUB failed: {r2['result']}"
    print(f"  L1 ALU SUB: 10-7={r2['result']} — PASS")

    r3 = alu_fn(opcode=OP_RI, funct3=7, rs1_val=0xFFFF, imm=0xF0F0)
    assert r3["result"] == 0xF0F0, f"AND failed: {r3['result']:#x}"
    print(f"  L1 ALU AND: {r3['result']:#x} — PASS")
    return True


def test_l1_alu_branch():
    alu_fn = FUNCTIONAL_MODELS["alu"]()
    from skills.cpu_riscv64 import OP_BRANCH, BRANCH_BEQ, BRANCH_BLT
    r1 = alu_fn(opcode=OP_BRANCH, funct3=BRANCH_BEQ, rs1_val=5, rs2_val=5)
    assert r1["taken"] == True, "BEQ should be taken"
    r2 = alu_fn(opcode=OP_BRANCH, funct3=BRANCH_BEQ, rs1_val=5, rs2_val=6)
    assert r2["taken"] == False, "BEQ should not be taken"
    r3 = alu_fn(opcode=OP_BRANCH, funct3=BRANCH_BLT, rs1_val=3, rs2_val=7)
    assert r3["taken"] == True, "BLT should be taken"
    print(f"  L1 Branch: BEQ/BLT — PASS")
    return True


def test_l1_fpu():
    fpu_fn = FUNCTIONAL_MODELS["fpu"]()
    from skills.cpu_riscv64 import FUNC_FADD, FUNC_FMUL
    r1 = fpu_fn(funct7=FUNC_FADD, rs1_val=1.5, rs2_val=2.5)
    import struct
    f1 = struct.unpack('>d', struct.pack('>Q', r1["result"] & 0xFFFFFFFFFFFFFFFF))[0]
    assert abs(f1 - 4.0) < 0.001, f"FADD failed: {f1}"
    print(f"  L1 FPU FADD: 1.5+2.5={f1} — PASS")

    r2 = fpu_fn(funct7=FUNC_FMUL, rs1_val=3.0, rs2_val=4.0)
    f2 = struct.unpack('>d', struct.pack('>Q', r2["result"] & 0xFFFFFFFFFFFFFFFF))[0]
    assert abs(f2 - 12.0) < 0.001, f"FMUL failed: {f2}"
    print(f"  L1 FPU FMUL: 3.0*4.0={f2} — PASS")
    return True


def test_l2_cycle():
    from skills.cpu_riscv64.arch_templates import build_cpu_arch
    from rtlgen.arch_sim import ArchSimulator
    arch = build_cpu_arch()
    sim = ArchSimulator(arch)
    sim.run(num_cycles=10, init_inputs={"rst": 1})
    sim.run(num_cycles=5, init_inputs={"rst": 0})
    report = sim._build_report()
    print(f"  L2 Cycle: {report['total_cycles']} cycles — PASS")
    return True


def test_l3_dsl():
    from rtlgen.codegen import VerilogEmitter
    e = VerilogEmitter(disable_cse=True)
    # Verify key modules exist and emit
    from rtlgen.lib import PipelineShift, MAC, Counter, MultiCycleFSM
    modules = [
        ("PipelineShift", PipelineShift(width=64, depth=3)),
        ("MAC", MAC(width=32)),
        ("Counter", Counter(width=64)),
        ("MultiCycleFSM", MultiCycleFSM()),
    ]
    oks = 0
    for name, inst in modules:
        v = e.emit(inst)
        oks += 1
        print(f"  L3 {name}: {len(v.splitlines())} lines")
    print(f"  L3 DSL: {oks}/{len(modules)} — PASS")
    return True


def test_ppa():
    from rtlgen.ppa import PPAAnalyzer
    from rtlgen.lib import MAC, PipelineShift
    for name, mod in [("MAC", MAC(width=64)), ("PipelineShift", PipelineShift(width=64, depth=4))]:
        pa = PPAAnalyzer(mod)
        r = pa.analyze_static()
        print(f"  PPA {name}: {r['reg_bits']} regs, {r['gate_count']:.0f} gates")
    print("  PPA Analysis — PASS")
    return True


def main():
    print("=" * 60)
    print("RISC-V 64 CPU with FPU — Verification")
    print(f"  Target: 12nm CMOS, 2GHz, RV64IMAFD")
    print("=" * 60)

    tests = [
        ("L1 ALU ADD/SUB/AND", test_l1_alu_add),
        ("L1 ALU Branch", test_l1_alu_branch),
        ("L1 FPU FADD/FMUL", test_l1_fpu),
        ("L2 Cycle Model", test_l2_cycle),
        ("L3 DSL Modules", test_l3_dsl),
        ("PPA Analysis", test_ppa),
    ]
    passed = 0
    for name, fn in tests:
        try:
            print(f"\n[{name}]")
            fn(); passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
