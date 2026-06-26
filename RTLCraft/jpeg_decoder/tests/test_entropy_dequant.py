"""Test entropy -> dequant chain manually."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen_x.dsl import lower_dsl_module_to_sim
from rtlgen_x.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegEntropyDecoder, JpegDequantZigzag, ZIGZAG_ORDER


def encode_block(coeffs):
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
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32

    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = coeffs.flat[ri]

    tokens = encode_block(zz)
    print("Tokens:", [hex(t) for t in tokens])
    bytes_stream = []
    for t in tokens:
        bytes_stream.append(t & 0xFF)
        bytes_stream.append((t >> 8) & 0xFF)

    # Run entropy decoder.
    ent_module = JpegEntropyDecoder()
    ent_sim = PythonSimulator(lower_dsl_module_to_sim(ent_module).module)
    ent_sim.reset()

    entropy_outputs = []
    byte_idx = 0
    block_done = False
    for cyc in range(300):
        if byte_idx < len(bytes_stream):
            tdata = bytes_stream[byte_idx]
            tvalid = 1
            tlast = 1 if byte_idx == len(bytes_stream) - 1 else 0
        else:
            tdata = 0
            tvalid = 0
            tlast = 0
        r = ent_sim.step({
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
            entropy_outputs.append(v)
        if r.get("block_valid"):
            block_done = True
        if block_done and len(entropy_outputs) >= 64:
            break

    print(f"Entropy outputs: {len(entropy_outputs)}")
    print(np.array(entropy_outputs[:64], dtype=np.int16).reshape(8, 8))

    # Run dequant decoder with entropy outputs.
    dq_module = JpegDequantZigzag()
    dq_sim = PythonSimulator(lower_dsl_module_to_sim(dq_module).module)
    dq_sim.reset()

    dq_outputs = []
    in_idx = 0
    for cyc in range(300):
        if in_idx < len(entropy_outputs):
            ind = entropy_outputs[in_idx] & 0xFFF
            inv = 1
        else:
            ind = 0
            inv = 0
        r = dq_sim.step({"clk": 0, "rst": 0, "in_data": ind, "in_valid": inv, "out_ready": 1})
        if r.get("in_ready") and inv:
            in_idx += 1
        if r.get("out_valid"):
            v = r["out_data"]
            if v >= 2048:
                v -= 4096
            dq_outputs.append(v)
        if len(dq_outputs) >= 64:
            break

    got = np.array(dq_outputs[:64], dtype=np.int16).reshape(8, 8)
    print("Expected raster:")
    print(coeffs)
    print("Got:")
    print(got)
    print("Match:", np.array_equal(got, coeffs))


if __name__ == "__main__":
    main()
