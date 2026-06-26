"""Basic smoke test for JpegIdct8x8."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
import numpy as np

from rtlgen_x.dsl import lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegIdct8x8, COEFF_WIDTH


def build_idct_matrix():
    """Reference floating-point 2D iDCT matrix."""
    N = 8
    mat = np.zeros((N, N), dtype=float)
    for u in range(N):
        alpha = 1.0 / math.sqrt(N) if u == 0 else math.sqrt(2.0 / N)
        for x in range(N):
            mat[u, x] = alpha * math.cos((2 * x + 1) * u * math.pi / (2 * N))
    return mat


def reference_idct2(coeffs):
    """Reference 2D iDCT on an 8x8 block."""
    T = build_idct_matrix()
    temp = T.T @ coeffs @ T
    return np.clip(np.rint(temp + 128), 0, 255).astype(np.uint8)


def main():
    module = JpegIdct8x8()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    # Test block: only DC coefficient.
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    expected = reference_idct2(coeffs)

    # Flatten in raster order.
    block = coeffs.flatten().tolist()

    outputs = []
    # Feed 64 coefficients.
    for i in range(64):
        inputs = {"clk": 0, "rst": 0, "in_data": block[i] & ((1 << COEFF_WIDTH) - 1), "in_valid": 1, "out_ready": 1}
        result = sim.step(inputs)

    # Continue until no more outputs.
    for cyc in range(1200):
        inputs = {"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1}
        result = sim.step(inputs)
        if result.get("out_valid"):
            outputs.append(result["out_data"])

    print(f"outputs collected: {len(outputs)}")
    if outputs:
        got = np.array(outputs[:64], dtype=np.uint8).reshape(8, 8)
        print("Expected:")
        print(expected)
        print("Got:")
        print(got)
        print("Match:", np.array_equal(got, expected))
    else:
        print("No outputs")


if __name__ == "__main__":
    main()
