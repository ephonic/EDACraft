"""Test iDCT with C++ backend."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen.dsl import build_compiled_simulator_from_dsl, lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegIdct8x8, COEFF_WIDTH, IDCT_TABLE, IDCT_FRAC


def reference_idct2(coeffs):
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


def run(sim, block):
    for i in range(64):
        sim.step({"clk": 0, "rst": 0, "in_data": block[i] & ((1 << COEFF_WIDTH) - 1), "in_valid": 1, "out_ready": 1})
    outputs = []
    for _ in range(1200):
        r = sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1})
        if r.get("out_valid"):
            outputs.append(r["out_data"])
        if len(outputs) >= 64:
            break
    return outputs


def run_cpp_idct_smoke(build_dir="jpeg_decoder/build/cpp_idct", *, verbose=False):
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32
    expected = reference_idct2(coeffs)
    block = coeffs.flatten().tolist()

    if verbose:
        print("Python:")
    py_sim = PythonSimulator(lower_dsl_module_to_sim(JpegIdct8x8()).module)
    py_sim.reset()
    py_y = np.array(run(py_sim, block)[:64], dtype=np.uint8).reshape(8, 8)
    if verbose:
        print(py_y)
        print("Match:", np.array_equal(py_y, expected))

    if verbose:
        print("C++:")
    with build_compiled_simulator_from_dsl(JpegIdct8x8(), build_dir=build_dir) as cpp_sim:
        cpp_sim.reset()
        cpp_y = np.array(run(cpp_sim, block)[:64], dtype=np.uint8).reshape(8, 8)
        if verbose:
            print(cpp_y)
            print("Match:", np.array_equal(cpp_y, expected))
    return py_y, cpp_y, expected


def test_cpp_idct_matches_python_and_reference(tmp_path):
    py_y, cpp_y, expected = run_cpp_idct_smoke(tmp_path / "cpp_idct")

    assert np.array_equal(py_y, expected)
    assert np.array_equal(cpp_y, expected)


def main():
    py_y, cpp_y, expected = run_cpp_idct_smoke(verbose=True)
    if not np.array_equal(py_y, expected) or not np.array_equal(cpp_y, expected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
