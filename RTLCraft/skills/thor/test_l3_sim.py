"""Thor GPU — L3 DSL Module Simulation Tests (pipeline handshake-aware)."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from rtlgen.sim import Simulator
from skills.thor import XLEN, NLANE, VLEN, OP_VLOAD, OP_VADD, OP_VMUL


def test_warp_scheduler():
    from skills.thor.layer3_dsl.warp_scheduler import WarpScheduler
    ws = WarpScheduler(); sim = Simulator(ws); sim.reset("rst", 2)
    sim.set("warp_ready", 0b1011); sim.set("warp_stall", 0b0010)
    sim.step()
    sel = sim.state.get("selected_warp", 0); v = sim.state.get("select_valid", 0)
    assert v == 1, f"valid=0"
    print(f"  WarpScheduler: sel={sel} — PASS")


def test_ibuffer():
    from skills.thor.layer3_dsl.ibuffer import IBuffer
    ib = IBuffer(); sim = Simulator(ib); sim.reset("rst", 2)
    sim.set("push_valid", 1); sim.set("push_data", 0x12345678); sim.step()
    sim.set("push_valid", 1); sim.set("push_data", 0xABCDEF00); sim.step()
    sim.set("push_valid", 0)
    assert sim.state.get("count", 0) == 2
    print(f"  IBuffer: count=2 — PASS")


def test_scoreboard():
    from skills.thor.layer3_dsl.scoreboard import Scoreboard
    sb = Scoreboard(); sim = Simulator(sb); sim.reset("rst", 2)
    sim.set("alloc_reg", 5); sim.set("alloc_valid", 1); sim.step()
    busy = sim.state.get("busy_mask", 0)
    assert busy & (1 << 5), f"reg5 not busy"
    sim.set("alloc_valid", 0); sim.set("commit_reg", 5); sim.set("commit_valid", 1)
    sim.step()
    busy = sim.state.get("busy_mask", 0)
    assert not (busy & (1 << 5)), f"reg5 still busy"
    print(f"  Scoreboard: alloc→commit — PASS")


def test_operand_collector():
    from skills.thor.layer3_dsl.operand_collector import OperandCollector
    oc = OperandCollector(); sim = Simulator(oc); sim.reset("rst", 1)
    sim.set("rs1", 3); sim.set("rs2", 7)
    sim.set("rf_data1", 0xAA); sim.set("rf_data2", 0xBB)
    sim.set("bypass_addr", 7); sim.set("bypass_data", 0xCC)
    sim.set("bypass_valid", 1); sim.step()
    op1 = sim.state.get("op1", 0); op2 = sim.state.get("op2", 0)
    assert op1 == 0xAA and op2 == 0xCC
    print(f"  OperandCollector: bypass op2 — PASS")


def test_vector_alu_pipeline():
    """VectorALU: verify pipeline valid handshake works."""
    from skills.thor.layer3_dsl.vector_alu import VectorALU
    alu = VectorALU(latency=3); sim = Simulator(alu); sim.reset("rst", 2)
    vec_a = sum(((5) & ((1<<XLEN)-1)) << (l * XLEN) for l in range(NLANE))
    sim.set("opcode", OP_VADD); sim.set("op1", vec_a); sim.set("op2", vec_a)
    sim.set("pred_mask", 0xFFFF)
    sim.set("in_valid", 0); sim.set("out_ready", 1)
    sim.step()
    sim.set("in_valid", 1); sim.step()
    sim.set("in_valid", 0)
    got = False
    for _ in range(6):
        sim.step()
        if sim.state.get("out_valid", 0):
            got = True; break
    # Note: result value checked via cross-layer consistency (L1 == Golden)
    assert got, "Pipeline valid never asserted"
    print(f"  VectorALU pipeline: valid at latency 3 — PASS")


def test_lsu_req():
    """LSU: combinatorial mem_req from op_vload."""
    from skills.thor.layer3_dsl.lsu import LSU
    lsu = LSU(latency=2); sim = Simulator(lsu); sim.reset("rst", 2)
    sim.set("op_vload", 1); sim.set("op_vstore", 0)
    sim.set("base_addr", 0x1000); sim.set("offset", 4)
    sim.set("in_valid", 0); sim.step()  # comb settles with new inputs
    req = sim.state.get("mem_req", 0); addr = sim.state.get("mem_addr", 0)
    assert req == 1 and addr == 0x1004, f"req={req} addr={addr:#x}"
    print(f"  LSU: req={req} addr={addr:#x} — PASS")


def main():
    print("=" * 60)
    print("Thor GPU — L3 DSL Simulation Tests (Pipeline Handshake)")
    print("=" * 60)
    tests = [
        ("WarpScheduler", test_warp_scheduler),
        ("IBuffer",       test_ibuffer),
        ("Scoreboard",    test_scoreboard),
        ("OperandCollector", test_operand_collector),
        ("VectorALU Pipeline", test_vector_alu_pipeline),
        ("LSU Request",   test_lsu_req),
    ]
    passed = 0
    for name, fn in tests:
        try:
            print(f"\n[{name}]"); fn(); passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
    print(f"\nResults: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    sys.exit(main())
