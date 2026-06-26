"""Test Dequant -> iDCT chain."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
import numpy as np

from rtlgen_x.dsl import EmitProfile, Input, Module, Output, VerilogEmitter, Wire, lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegDequantZigzag, JpegIdct8x8, COEFF_WIDTH, ZIGZAG_ORDER


class DequantIdctWrapper(Module):
    def __init__(self):
        super().__init__("DequantIdctWrapper")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.in_data = Input(12, "in_data", signed=True)
        self.in_valid = Input(1, "in_valid")
        self.in_ready = Output(1, "in_ready")
        self.out_data = Output(8, "out_data")
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")

        u_dq = JpegDequantZigzag(name="dq")
        u_idct = JpegIdct8x8(name="idct")

        self.dq_out = Wire(COEFF_WIDTH, "dq_out", signed=True)
        self.dq_out_valid = Wire(1, "dq_out_valid")
        self.dq_out_ready = Wire(1, "dq_out_ready")

        self.instantiate(u_dq, "u_dq", port_map={
            "clk": self.clk, "rst": self.rst,
            "in_data": self.in_data, "in_valid": self.in_valid, "in_ready": self.in_ready,
            "out_data": self.dq_out,
            "out_valid": self.dq_out_valid,
            "out_ready": self.dq_out_ready,
        })
        self.instantiate(u_idct, "u_idct", port_map={
            "clk": self.clk, "rst": self.rst,
            "in_data": self.dq_out,
            "in_valid": self.dq_out_valid,
            "in_ready": self.dq_out_ready,
            "out_data": self.out_data, "out_valid": self.out_valid, "out_ready": self.out_ready,
        })


def build_idct_matrix():
    N = 8
    mat = np.zeros((N, N), dtype=float)
    for u in range(N):
        alpha = 1.0 / math.sqrt(N) if u == 0 else math.sqrt(2.0 / N)
        for x in range(N):
            mat[u, x] = alpha * math.cos((2 * x + 1) * u * math.pi / (2 * N))
    return mat


def reference_idct2(coeffs):
    T = build_idct_matrix()
    temp = T.T @ coeffs @ T
    return np.clip(np.rint(temp + 128), 0, 255).astype(np.uint8)


def run_dequant_idct_chain(*, verbose=False):
    module = DequantIdctWrapper()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    expected = reference_idct2(coeffs)

    # Zig-zag order input.
    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = coeffs.flat[ri]

    # Feed dequant.
    for i in range(64):
        r = sim.step({"clk": 0, "rst": 0, "in_data": int(zz[i]) & 0xFFF, "in_valid": 1, "out_ready": 1})
        if verbose and i < 5:
            print(f"feed {i}: in_ready={r.get('in_ready')} zz={zz[i]}")

    # Collect outputs.
    outputs = []
    dq_outputs = []
    for cyc in range(2000):
        r = sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1})
        if r.get("out_valid"):
            outputs.append(r["out_data"])
        # Peek dequant output valid via internal state.
        if sim._state.get('u_dq__out_valid_reg') and cyc < 100:
            v = sim._state.get('u_dq__out_data_reg', 0)
            if v >= 2048:
                v -= 4096
            dq_outputs.append(v)
        if len(outputs) >= 64:
            break
    got = np.array(outputs[:64], dtype=np.uint8).reshape(8, 8)
    if verbose:
        print("First DQ outputs:", dq_outputs[:10])
        print("Quant[0]:", sim._state.get('u_dq__quant_dbg'))
        print("State keys with quant:", [k for k in sim._state.keys() if 'quant' in k])
        print("Expected:")
        print(expected)
        print("Got:")
        print(got)
        print("Match:", np.array_equal(got, expected))
        print("DQ out_data_reg:", sim._state.get('u_dq__out_data_reg'))
        print("DQ state:", sim._state.get('u_dq__state'))
        print("IDCT state:", sim._state.get('u_idct__state'))
        print("IDCT idx:", sim._state.get('u_idct__idx'))
    return got, expected


def test_dequant_idct_chain_matches_reference():
    got, expected = run_dequant_idct_chain()

    assert np.array_equal(got, expected)


def test_dequant_idct_wrapper_lowers_and_emits_parent_owned_handoff():
    module = DequantIdctWrapper()
    lowered = lower_dsl_module_to_sim(module)

    assignment_targets = {assignment.target for assignment in lowered.module.assignments}
    assert "u_dq_out_data" in assignment_targets
    assert "u_idct_in_data" in assignment_targets

    rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(module)
    assert "module DequantIdctWrapper" in rtl
    assert "dq u_dq (" in rtl
    assert "idct u_idct (" in rtl
    assert ".out_data(dq_out)" in rtl
    assert ".in_data($signed(dq_out))" in rtl


def main():
    got, expected = run_dequant_idct_chain(verbose=True)
    if not np.array_equal(got, expected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
