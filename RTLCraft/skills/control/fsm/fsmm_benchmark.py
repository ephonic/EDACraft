#!/usr/bin/env python3
"""
FSMM Benchmark — correctness & performance across all sparsity modes.

Tests FSMM Q=16 with modes 0..4 (1:16, 2:16, 4:16, 8:16, 16:16 dense).
For each mode we generate random sparse patterns, run the Python AST simulator,
and compare against the golden Python reference model.
"""

import sys
import time
import random

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from rtlgen.core import flatten_module
from examples.fsmm import FSMM

Q = 16
DW = 8
IDXW = max(2, Q.bit_length())


def flatten_matrix(mat):
    """Flatten QxQ matrix to integer (row-major)."""
    val = 0
    for r in range(Q):
        for c in range(Q):
            val |= (mat[r][c] & ((1 << DW) - 1)) << ((r * Q + c) * DW)
    return val


def expand_matrix(val):
    """Expand integer to QxQ matrix."""
    mat = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            mat[r][c] = (val >> ((r * Q + c) * DW)) & ((1 << DW) - 1)
    return mat


def ref_fsmm(f_mat, w_mat_compressed, reorder, mode):
    """Golden reference model."""
    max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[mode]
    o = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            s = 0
            for k in range(max_k):
                val, idx = w_mat_compressed[c][k]
                s += f_mat[r][idx] * val
            o[r][c] = s & ((1 << DW) - 1)
    o2 = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            src = reorder[c]
            o2[r][c] = o[r][src]
    return o2


def generate_random_testcase(mode, seed=None):
    """Generate one random testcase for the given sparsity mode."""
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[mode]

    # F matrix: dense random
    f_mat = [[rng.randint(0, (1 << DW) - 1) for _ in range(Q)] for _ in range(Q)]

    # W compressed matrix per column: (val, row_idx)
    w_mat_compressed = [[(0, 0)] * Q for _ in range(Q)]
    for c in range(Q):
        for k in range(max_k):
            val = rng.randint(0, (1 << DW) - 1)
            idx = rng.randint(0, Q - 1)
            w_mat_compressed[c][k] = (val, idx)

    # Pack w_data and w_idx flat
    w_data = 0
    w_idx = 0
    for c in range(Q):
        for k in range(Q):
            if k < max_k:
                val, idx = w_mat_compressed[c][k]
            else:
                val, idx = 0, 0
            w_data |= (val & ((1 << DW) - 1)) << ((c * Q + k) * DW)
            w_idx |= (idx & ((1 << IDXW) - 1)) << ((c * Q + k) * IDXW)

    # Reorder: random permutation
    reorder = list(range(Q))
    rng.shuffle(reorder)
    reorder_idx = 0
    for c in range(Q):
        reorder_idx |= (reorder[c] & ((1 << IDXW) - 1)) << (c * IDXW)

    f_data = flatten_matrix(f_mat)

    return {
        "f_mat": f_mat,
        "w_mat_compressed": w_mat_compressed,
        "reorder": reorder,
        "f_data": f_data,
        "w_data": w_data,
        "w_idx": w_idx,
        "reorder_idx": reorder_idx,
        "mode": mode,
    }


def run_simulation(tc, max_cycles=5000):
    """Run one testcase through the flattened FSMM simulator."""
    dut = flatten_module(FSMM(Q=Q, DW=DW))
    sim = Simulator(dut)

    # Reset
    sim.set("rst_n", 0)
    sim.step()
    sim.set("rst_n", 1)

    # Drive inputs
    sim.set("start", 1)
    sim.set("mode", tc["mode"])
    sim.set("f_data", tc["f_data"])
    sim.set("w_data", tc["w_data"])
    sim.set("w_idx", tc["w_idx"])
    sim.set("reorder_idx", tc["reorder_idx"])
    sim.step()
    sim.set("start", 0)

    # Wait for valid_out
    for cycle in range(max_cycles):
        sim.step()
        if sim.get_int("valid_out"):
            return sim.get_int("o_data"), cycle + 1

    raise RuntimeError("Timeout: valid_out never asserted")


def benchmark_mode(mode, num_tests=10):
    """Benchmark one sparsity mode with multiple random tests."""
    sparsity_label = {0: "1:16", 1: "2:16", 2: "4:16", 3: "8:16", 4: "16:16"}[mode]
    print(f"\n{'='*60}")
    print(f"Mode {mode} ({sparsity_label}) — {num_tests} random tests")
    print("=" * 60)

    passed = 0
    failed = 0
    total_cycles = 0
    total_time = 0.0

    for i in range(num_tests):
        tc = generate_random_testcase(mode, seed=1000 * mode + i)
        t0 = time.perf_counter()
        try:
            o_data, cycles = run_simulation(tc)
        except RuntimeError as e:
            print(f"  Test {i}: FAIL ({e})")
            failed += 1
            continue
        t1 = time.perf_counter()

        total_cycles += cycles
        total_time += (t1 - t0)

        # Compute reference
        exp_mat = ref_fsmm(tc["f_mat"], tc["w_mat_compressed"], tc["reorder"], tc["mode"])
        exp_val = flatten_matrix(exp_mat)

        if o_data == exp_val:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
            # Show first mismatching row
            act_mat = expand_matrix(o_data)
            for r in range(Q):
                for c in range(Q):
                    if act_mat[r][c] != exp_mat[r][c]:
                        print(f"    First mismatch at [{r}][{c}] exp={exp_mat[r][c]} act={act_mat[r][c]}")
                        break
                else:
                    continue
                break

        print(f"  Test {i}: {status}  cycles={cycles}  time={(t1-t0)*1000:.2f}ms")

    avg_cycles = total_cycles / max(passed, 1)
    avg_time_ms = (total_time / max(passed, 1)) * 1000
    print(f"  Summary: passed={passed}  failed={failed}  avg_cycles={avg_cycles:.1f}  avg_time={avg_time_ms:.2f}ms")
    return passed, failed


def main():
    print("FSMM Benchmark — Flattened Simulator vs Python Reference Model")
    print(f"Q={Q}, DW={DW}")

    total_passed = 0
    total_failed = 0
    for mode in range(5):
        p, f = benchmark_mode(mode, num_tests=10)
        total_passed += p
        total_failed += f

    print("\n" + "=" * 60)
    print(f"OVERALL: passed={total_passed}  failed={total_failed}")
    if total_failed == 0:
        print("All tests PASSED. FSMM is functionally correct across all sparsity modes.")
    else:
        print("Some tests FAILED. See details above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
