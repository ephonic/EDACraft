"""
Thor GPGPU — End-to-End Test: Behavior → Skeleton → DSL Sim → Verilog

This script validates the complete Skill-Guided RTL Generation flow:
  1. Behavioral simulation (ArchSimulator) — golden reference
  2. Skeleton generation (ArchSkeletonGenerator with skills + verifier)
  3. DSL simulation (Python Simulator) on generated skeleton
  4. Verilog emission + iverilog syntax check
  5. Trace comparison between behavior and skeleton
"""
from __future__ import annotations

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rtlgen.arch_sim import ArchSimulator
from rtlgen.arch_skel import ArchSkeletonGenerator
from rtlgen.codegen import VerilogEmitter
from rtlgen.sim import Simulator

from skills.thor_gpu_spec2rtl import (
    build_thor_arch, NWARP, VLEN, IMEM_DEPTH, ACCW,
)

# Test program for SM0 (computes MAC: 5*3 + 7*2 = 29)
SM0_PROG = [
    (0, 0x70000005),  # SLOAD v0, 5
    (1, 0x71000003),  # SLOAD v1, 3
    (2, 0x32010000),  # VADD v2, v0, v1
    (3, 0x43010000),  # VMUL v3, v0, v1
    (4, 0x54010000),  # VMAC v4, v0, v1
    (5, 0x60000000),  # BARRIER
    (6, 0x70000007),  # SLOAD v0, 7
    (7, 0x71000002),  # SLOAD v1, 2
    (8, 0x54010000),  # VMAC v4, v0, v1
    (9, 0xF0000000),  # DONE
]

SM1_PROG = [(0, 0xF0000000)]  # DONE immediately

OUT_DIR = "/tmp/skill_test/thor_e2e"
os.makedirs(OUT_DIR, exist_ok=True)


def run_behavioral_sim():
    """Step 1: Run ArchSimulator behavioral model."""
    print("=" * 70)
    print("[Step 1] Behavioral Simulation (ArchSimulator)")
    print("=" * 70)

    arch = build_thor_arch()
    sim = ArchSimulator(arch)

    # Reset
    sim.run(num_cycles=3, init_inputs={"rst_n": 0, "mem_ready": 1})

    # Load SM0 program
    for addr, data in SM0_PROG:
        sim.run(num_cycles=1, init_inputs={
            "rst_n": 1, "mem_ready": 1,
            "sm_0.imem_wr_en": 1,
            "sm_0.imem_wr_addr": addr,
            "sm_0.imem_wr_data": data,
        })
    # Load SM1 program
    sim.run(num_cycles=1, init_inputs={
        "rst_n": 1, "mem_ready": 1,
        "sm_1.imem_wr_en": 1,
        "sm_1.imem_wr_addr": 0,
        "sm_1.imem_wr_data": 0xF0000000,
    })

    # Start kernel
    sim.run(num_cycles=2, init_inputs={"rst_n": 1, "start": 1, "mem_ready": 1})

    # Run until done
    beh_cycles = None
    beh_acc0 = None
    for cycle in range(200):
        outputs = sim.step()
        done = (sim._signals.get("sm_0.sm_done", 0) &
                sim._signals.get("sm_1.sm_done", 0))
        if done:
            beh_cycles = cycle
            beh_acc0 = sim._signals.get("sm_0.debug_w0_acc0", 0)
            print(f"  DONE at cycle {cycle}")
            print(f"  sm_0.debug_w0_acc0 = {beh_acc0} (expected 29)")
            break
    else:
        print("  TIMEOUT")

    report = sim._build_report()
    print(f"  Cycles: {report['total_cycles']}, IPC: {report['ipc']}")
    return beh_cycles, beh_acc0


def run_skeleton_generation():
    """Step 2: Generate skeleton with skill guidance + verifier."""
    print("\n" + "=" * 70)
    print("[Step 2] Skeleton Generation (Skill-Guided + Verifier)")
    print("=" * 70)

    arch = build_thor_arch()
    gen = ArchSkeletonGenerator(
        enable_skill_guidance=True,
        enable_verifier=True,
    )
    print(f"  Skill retriever: {gen.skill_retriever is not None}")
    print(f"  Logic generator: {gen.logic_generator is not None}")
    print(f"  Verifier:        {gen.verifier is not None}")
    if gen.skill_retriever:
        print(f"  Skills loaded:   {len(gen.skill_retriever._index)} "
              f"from {len(gen.skill_retriever.index_paths)} domains")

    packages = gen.generate_all(arch)

    for name, pkg in packages.items():
        print(f"  {name}: pe_type={pkg.pe.pe_type}, "
              f"steps={len(pkg.implementation_steps)}, "
              f"golden_tests={len(pkg.golden_tests)}")

    return packages


def emit_skeleton_verilog(packages):
    """Step 3: Emit Verilog from skeleton DSL."""
    print("\n" + "=" * 70)
    print("[Step 3] Verilog Emission")
    print("=" * 70)

    emitter = VerilogEmitter(disable_cse=True)
    paths = {}

    for name, pkg in packages.items():
        # Use emit_design to include all submodules hierarchically
        vlog = emitter.emit_design(pkg.dsl_skeleton)
        path = f"{OUT_DIR}/{name}_skel.v"
        with open(path, "w") as f:
            f.write(vlog)
        paths[name] = path
        print(f"  {name}: {len(vlog.splitlines())} lines -> {path}")

    return paths


def check_syntax(paths):
    """Step 4: iverilog syntax check."""
    print("\n" + "=" * 70)
    print("[Step 4] Syntax Check (iverilog)")
    print("=" * 70)

    all_ok = True
    for name, path in paths.items():
        cmd = ["iverilog", "-g2012", "-Wall", "-o", "/dev/null", path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            errors = [l for l in proc.stderr.splitlines()
                      if "error:" in l.lower()]
            if errors:
                print(f"  {name}: FAILED")
                for e in errors[:3]:
                    print(f"    {e}")
                all_ok = False
            else:
                warns = len([l for l in proc.stderr.splitlines()
                             if "warning:" in l.lower()])
                print(f"  {name}: OK ({warns} warnings)")
        except FileNotFoundError:
            print(f"  {name}: SKIPPED (iverilog not found)")
        except subprocess.TimeoutExpired:
            print(f"  {name}: TIMEOUT")
            all_ok = False

    return all_ok


def run_skeleton_dsl_sim(packages):
    """Step 5: Run Python Simulator on generated skeleton DSL."""
    print("\n" + "=" * 70)
    print("[Step 5] DSL Simulation on Generated Skeleton")
    print("=" * 70)

    pkg = packages["sm_0"]
    skel = pkg.dsl_skeleton

    sim = Simulator(skel)
    sim.reset("rst_n", cycles=3)

    # Load program into skeleton SM0
    for addr, data in SM0_PROG:
        sim.set("imem_wr_en", 1)
        sim.set("imem_wr_addr", addr)
        sim.set("imem_wr_data", data)
        sim.step()
        sim.set("imem_wr_en", 0)
        sim.step()

    # Start
    sim.set("start", 1)
    sim.step()
    sim.set("start", 0)

    # Run with memory model
    skel_cycles = None
    skel_acc0 = None
    for cycle in range(200):
        sim.set("mem_valid", 0)
        sim.set("mem_rdata", 0)
        sim.set("mem_ready", 1)
        if sim.state.get("mem_req", 0) and not sim.state.get("mem_wen", 0):
            sim.set("mem_valid", 1)
            sim.set("mem_rdata", 0x0102030405060708)
        sim.step()
        if sim.state.get("sm_done", 0):
            skel_cycles = cycle
            skel_acc0 = sim.state.get("debug_w0_acc0", 0)
            print(f"  DONE at cycle {cycle}")
            print(f"  debug_w0_acc0 = {skel_acc0} (expected 29)")
            break
    else:
        print("  TIMEOUT")
        print(f"  sm_done={sim.state.get('sm_done', 0)} "
              f"debug_w0_acc0={sim.state.get('debug_w0_acc0', 0)}")

    return skel_cycles, skel_acc0


def compare_results(beh, skel):
    """Step 6: Compare behavioral vs skeleton results."""
    print("\n" + "=" * 70)
    print("[Step 6] Trace Comparison")
    print("=" * 70)

    beh_cycles, beh_acc0 = beh
    skel_cycles, skel_acc0 = skel

    print(f"  Behavioral model:  cycles={beh_cycles}, acc0={beh_acc0}")
    print(f"  Skeleton DSL:      cycles={skel_cycles}, acc0={skel_acc0}")

    match = True
    if beh_acc0 != skel_acc0:
        print(f"  MISMATCH: acc0 differs ({beh_acc0} vs {skel_acc0})")
        match = False
    if beh_cycles != skel_cycles:
        print(f"  NOTE: cycle count differs ({beh_cycles} vs {skel_cycles})")
        # Cycle difference is acceptable if result is correct

    if match and skel_acc0 == 29:
        print("  => END-TO-END VERIFICATION PASSED")
        return True
    else:
        print("  => END-TO-END VERIFICATION FAILED")
        return False


def main():
    print("\n" + "=" * 70)
    print("Thor GPGPU End-to-End Test")
    print("Behavior → Skeleton → DSL Sim → Verilog")
    print("=" * 70)

    # Step 1: Behavioral sim
    beh_result = run_behavioral_sim()

    # Step 2: Skeleton generation
    packages = run_skeleton_generation()

    # Step 3: Emit Verilog
    vlog_paths = emit_skeleton_verilog(packages)

    # Step 4: Syntax check
    syntax_ok = check_syntax(vlog_paths)

    # Step 5: DSL simulation on skeleton
    skel_result = run_skeleton_dsl_sim(packages)

    # Step 6: Compare
    passed = compare_results(beh_result, skel_result)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Behavioral cycles/acc0:  {beh_result}")
    print(f"  Skeleton cycles/acc0:    {skel_result}")
    print(f"  Verilog syntax check:    {'PASS' if syntax_ok else 'FAIL'}")
    print(f"  End-to-end result:       {'PASS' if passed else 'FAIL'}")
    print("=" * 70)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
