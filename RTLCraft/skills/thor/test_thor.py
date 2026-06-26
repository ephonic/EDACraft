"""
Thor GPGPU — Verification Tests.

Tests all three layers with a simple workload.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from skills.thor.models import ThorSM_Model, ThorGPU_Model
from skills.thor.functional import FUNCTIONAL_MODELS



def test_l1_functional_models():
    """Test L1 functional models for correctness."""
    from skills.thor.functional import (
        vector_alu_functional, warp_scheduler_functional,
        sm_wrapper_functional, lsu_functional,
    )
    from skills.thor import OP_VADD, OP_VMUL, NLANE, XLEN, VLEN

    # Test Vector ALU: VADD
    alu_fn = vector_alu_functional()
    mask = (1 << XLEN) - 1
    op1 = 5; op2 = 3
    vec1 = sum((op1 & mask) << (lane * XLEN) for lane in range(NLANE))
    vec2 = sum((op2 & mask) << (lane * XLEN) for lane in range(NLANE))
    r = alu_fn(opcode=OP_VADD, op1=vec1, op2=vec2, pred_mask=0xFFFF)
    expected = sum(((op1 + op2) & mask) << (lane * XLEN) for lane in range(NLANE))
    assert r["result"] == expected, f"VADD fail: {r['result']} != {expected}"
    print("  L1 Vector ALU VADD: PASS")

    # Test L1 SM Wrapper: SLOAD
    from skills.thor import OP_SLOAD as OP_SL
    sm_fn = sm_wrapper_functional()
    imm = 5
    inst = (OP_SL << 28) | (imm & 0x1FFF)
    r2 = sm_fn(inst=inst, pc=0, warp_id=0)
    assert r2["wb_valid"] == 1, "SLOAD should produce writeback"
    print("  L1 SM Wrapper SLOAD: PASS")
    return True


def test_l2_cycle_models():
    """Test L2 cycle-accurate models via ArchSimulator."""
    from skills.thor.arch_templates import build_thor_arch
    from rtlgen.arch_sim import ArchSimulator
    arch = build_thor_arch()
    sim = ArchSimulator(arch)
    sim.run(num_cycles=3, init_inputs={"rst": 1})
    sim.run(num_cycles=5, init_inputs={"rst": 0})
    report = sim._build_report()
    print(f"  L2 simulation: {report['total_cycles']} cycles, IPC={report['ipc']}")
    return True


def test_l3_dsl_module():
    """Test L3 DSL module instantiation and simulation."""
    from skills.thor.layer3_dsl.warp_scheduler import WarpScheduler
    from skills.thor.layer3_dsl.vector_alu import VectorALU
    from skills.thor.layer3_dsl.sm_wrapper import SMWrapper
    from skills.thor.layer3_dsl.gpu_top import GPUTop
    from rtlgen.codegen import VerilogEmitter

    ws = WarpScheduler()
    alu = VectorALU()
    sm = SMWrapper()
    top = GPUTop()

    emitter = VerilogEmitter(disable_cse=True)
    ws_v = emitter.emit(ws)
    assert len(ws_v) > 0, "WarpScheduler emit failed"
    print(f"  L3 WarpScheduler: {len(ws_v.splitlines())} lines")

    alu_v = emitter.emit(alu)
    assert len(alu_v) > 0, "VectorALU emit failed"
    print(f"  L3 VectorALU: {len(alu_v.splitlines())} lines")

    sm_v = emitter.emit(sm)
    assert len(sm_v) > 0, "SM emit failed"
    print(f"  L3 SM: {len(sm_v.splitlines())} lines")

    top_v = emitter.emit(top)
    assert len(top_v) > 0, "Top emit failed"
    print(f"  L3 Top: {len(top_v.splitlines())} lines")
    return True


def test_golden_model():
    """Test golden reference model with compute workload."""
    from skills.thor import OP_SLOAD, OP_VADD, OP_VMUL, OP_DONE

    def inst(op, rd=0, rs1=0, rs2=0, imm=0):
        return (op << 28) | (rd << 23) | (rs1 << 18) | (rs2 << 13) | (imm & 0x1FFF)

    from skills.thor import XLEN, NLANE
    nwarp = 4
    vregs = 8
    sm = ThorSM_Model(nwarp=nwarp, vregs=vregs)
    prog = [
        inst(OP_SLOAD, 0, imm=5),
        inst(OP_SLOAD, 1, imm=3),
        inst(OP_VADD, 2, 0, 1),
        inst(OP_VMUL, 3, 0, 1),
        inst(OP_DONE),
    ]
    for addr, data in enumerate(prog):
        sm.load_imem(addr, data)

    started = False
    for _ in range(100):
        result = sm.step(start=int(not started))
        started = True
        if result["sm_done"]:
            break

    mask = (1 << XLEN) - 1
    add_expected = sum(((5 + 3) & mask) << (lane * XLEN) for lane in range(NLANE))
    mul_expected = sum(((5 * 3) & mask) << (lane * XLEN) for lane in range(NLANE))
    vrf_v2 = sm.vrf[0 * vregs + 2]
    vrf_v3 = sm.vrf[0 * vregs + 3]
    assert vrf_v2 == add_expected, f"VADD golden: {vrf_v2:#x} != {add_expected:#x}"
    assert vrf_v3 == mul_expected, f"VMUL golden: {vrf_v3:#x} != {mul_expected:#x}"
    print(f"  Golden SM: VADD={vrf_v2:#x}, VMUL={vrf_v3:#x} — PASS")
    return True


def test_full_gpu():
    """Test full GPU with 2 SMs."""
    from skills.thor import OP_SLOAD, OP_VMUL, OP_DONE

    def inst(op, rd=0, rs1=0, rs2=0, imm=0):
        return (op << 28) | (rd << 23) | (rs1 << 18) | (rs2 << 13) | (imm & 0x1FFF)

    gpu = ThorGPU_Model(n_sm=2, nwarp=2)

    gpu.load_imem(0, 0, inst(OP_SLOAD, 0, imm=7))
    gpu.load_imem(0, 1, inst(OP_SLOAD, 1, imm=2))
    gpu.load_imem(0, 2, inst(OP_VMUL, 2, 0, 1))
    gpu.load_imem(0, 3, inst(OP_DONE))
    gpu.load_imem(1, 0, inst(OP_DONE))

    result = gpu.run(num_cycles=200)
    assert result["all_done"], "GPU should complete"
    print(f"  Full GPU: done at cycle {result['cycle']} — PASS")
    return True


def main():
    print("=" * 60)
    print("Thor GPGPU — Verification Suite")
    print("=" * 60)
    tests = [
        ("L1 Functional Models", test_l1_functional_models),
        ("L2 Cycle-Accurate Models", test_l2_cycle_models),
        ("L3 DSL Module Instantiation", test_l3_dsl_module),
        ("Golden Reference Model", test_golden_model),
        ("Full GPU Model", test_full_gpu),
    ]
    passed = 0
    for name, fn in tests:
        try:
            print(f"\n[{name}]")
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
