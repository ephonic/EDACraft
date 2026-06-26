"""End-to-end test of JpegDecoder top-level."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import math
import numpy as np

from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegDecoder, ZIGZAG_ORDER, IDCT_TABLE, IDCT_FRAC


def build_idct_matrix():
    N = 8
    mat = np.zeros((N, N), dtype=float)
    for u in range(N):
        alpha = 1.0 / math.sqrt(N) if u == 0 else math.sqrt(2.0 / N)
        for x in range(N):
            mat[u, x] = alpha * math.cos((2 * x + 1) * u * math.pi / (2 * N))
    return mat


def reference_decode(coeffs):
    """Reference: dequant (quant=1) + iDCT + level shift.

    Emulates the hardware pipeline: row transform with rounding to 16 bits,
    then column transform with rounding, then +128 and clip.
    """
    T = np.array(IDCT_TABLE, dtype=float).reshape(8, 8) / (1 << IDCT_FRAC)
    c = coeffs.astype(float)
    # Row transform: x'[v][col] = round( sum_u x[v][u] * T[u][col] )
    row_out = np.zeros((8, 8), dtype=float)
    for v in range(8):
        for col in range(8):
            s = sum(c[v][u] * T[u][col] for u in range(8))
            row_out[v][col] = np.floor(s + 0.5)
    # Column transform: y[row][col] = round( sum_u row_out[u][col] * T[u][row] )
    temp = np.zeros((8, 8), dtype=float)
    for row in range(8):
        for col in range(8):
            s = sum(row_out[u][col] * T[u][row] for u in range(8))
            temp[row][col] = np.floor(s + 0.5)
    return np.clip(temp + 128, 0, 255).astype(np.uint8)


def encode_block_rle(coeffs):
    """Simplified RLE token encoder."""
    tokens = []
    i = 0
    while i < 64:
        if coeffs[i] == 0:
            run = 0
            j = i
            while j < 64 and coeffs[j] == 0 and run < 14:
                run += 1
                j += 1
            if j >= 64:
                tokens.append(0xF000)
                break
            val = coeffs[j] & 0xFFF
            tokens.append((run << 12) | val)
            i = j + 1
        else:
            val = coeffs[i] & 0xFFF
            tokens.append(val)
            i += 1
    return tokens


def main():
    module = JpegDecoder()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    # Test block: DC=128, AC[1]=64, AC[1][0]=-32, rest 0.
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32
    expected = reference_decode(coeffs)

    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = coeffs.flat[ri]
    tokens = encode_block_rle(zz)
    bytes_stream = []
    for t in tokens:
        bytes_stream.append(t & 0xFF)
        bytes_stream.append((t >> 8) & 0xFF)

    pixels = []
    byte_idx = 0
    for cyc in range(3000):
        if byte_idx < len(bytes_stream):
            tdata = bytes_stream[byte_idx]
            tvalid = 1
            tlast = 1 if byte_idx == len(bytes_stream) - 1 else 0
        else:
            tdata = 0
            tvalid = 0
            tlast = 0

        r = sim.step({
            "clk": 0, "rst": 0,
            "s_axis_tdata": tdata,
            "s_axis_tvalid": tvalid,
            "s_axis_tlast": tlast,
            "m_axis_tready": 1,
        })

        if r.get("s_axis_tready") and tvalid:
            byte_idx += 1

        if r.get("m_axis_tvalid"):
            pixels.append(r["m_axis_tdata"])

        if len(pixels) >= 64:
            break

    # Extract R channel (bits [23:16]).
    got_y = np.array([(p >> 16) & 0xFF for p in pixels[:64]], dtype=np.uint8).reshape(8, 8)
    print(f"Pixels collected: {len(pixels)}")
    print("Expected Y:")
    print(expected)
    print("Got Y:")
    print(got_y)
    print("Match:", np.array_equal(got_y, expected))

    # Inspect internal state keys.
    print("Internal signal names:", sorted(sim._state.keys())[:40])


if __name__ == "__main__":
    main()
