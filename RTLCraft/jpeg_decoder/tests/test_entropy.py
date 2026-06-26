"""Test JpegEntropyDecoder."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen_x.dsl import lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegEntropyDecoder


def encode_block(coeffs):
    """Encode a zig-zag coefficient list into tokens."""
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
                tokens.append(0xF000)  # EOB
                break
            # Insert run zeros then next coeff.
            val = coeffs[j]
            v = val & 0xFFF
            tokens.append((run << 12) | v)
            i = j + 1
        else:
            val = coeffs[i]
            v = val & 0xFFF
            tokens.append(v)
            i += 1
    return tokens


def main():
    module = JpegEntropyDecoder()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    # Zig-zag coefficients: DC=128, AC[1]=64, rest 0.
    coeffs = np.zeros(64, dtype=np.int16)
    coeffs[0] = 128
    coeffs[1] = 64
    tokens = encode_block(coeffs)
    print("Tokens:", [hex(t) for t in tokens])

    # Flatten tokens to bytes (little-endian).
    bytes_stream = []
    for t in tokens:
        bytes_stream.append(t & 0xFF)
        bytes_stream.append((t >> 8) & 0xFF)

    # Feed bytes.
    outputs = []
    block_done = False
    byte_idx = 0
    for cyc in range(300):
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
            "coeff_ready": 1,
            "block_ready": 1 if block_done else 0,
        })

        if r.get("s_axis_tready") and tvalid:
            byte_idx += 1

        if r.get("coeff_valid"):
            v = r["coeff_out"]
            if v >= 2048:
                v -= 4096
            outputs.append(v)

        if r.get("block_valid"):
            block_done = True

        if block_done and len(outputs) >= 64:
            break

    print(f"Outputs: {len(outputs)}")
    got = np.array(outputs[:64], dtype=np.int16)
    print("Expected:", coeffs)
    print("Got:", got)
    print("Match:", np.array_equal(got, coeffs))


if __name__ == "__main__":
    main()
