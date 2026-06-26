"""Test iDCT with 2D coefficients."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
import numpy as np

from rtlgen_x.dsl import lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegIdct8x8, COEFF_WIDTH, IDCT_TABLE, IDCT_FRAC


def build_idct_matrix():
    N = 8
    mat = np.zeros((N, N), dtype=float)
    for u in range(N):
        alpha = 1.0 / math.sqrt(N) if u == 0 else math.sqrt(2.0 / N)
        for x in range(N):
            mat[u, x] = alpha * math.cos((2 * x + 1) * u * math.pi / (2 * N))
    return mat


def reference_idct2(coeffs):
    """Reference that emulates the hardware row/column rounding."""
    T = np.array(IDCT_TABLE, dtype=float).reshape(8, 8) / (1 << IDCT_FRAC)
    c = coeffs.astype(float)
    row_out = np.zeros((8, 8), dtype=float)
    for v in range(8):
        for col in range(8):
            s = sum(c[v][u] * T[u][col] for u in range(8))
            row_out[v][col] = np.floor(s + 0.5)
    temp = np.zeros((8, 8), dtype=float)
    for row in range(8):
        for col in range(8):
            s = sum(row_out[u][col] * T[u][row] for u in range(8))
            temp[row][col] = np.floor(s + 0.5)
    return np.clip(temp + 128, 0, 255).astype(np.uint8)


def main():
    module = JpegIdct8x8()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32
    expected = reference_idct2(coeffs)

    block = coeffs.flatten().tolist()
    for i in range(64):
        sim.step({"clk": 0, "rst": 0, "in_data": block[i] & ((1 << COEFF_WIDTH) - 1), "in_valid": 1, "out_ready": 1})

    outputs = []
    for _ in range(1200):
        r = sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1})
        if r.get("out_valid"):
            outputs.append(r["out_data"])
        if len(outputs) >= 64:
            break

    got = np.array(outputs[:64], dtype=np.uint8).reshape(8, 8)
    print("Expected:")
    print(expected)
    print("Got:")
    print(got)
    print("Match:", np.array_equal(got, expected))


if __name__ == "__main__":
    main()
