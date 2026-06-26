"""Test JpegDequantZigzag."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

from jpeg_decoder.dsl_modules import JpegDequantZigzag, ZIGZAG_ORDER


def main():
    module = JpegDequantZigzag()
    lowered = lower_dsl_module_to_sim(module)
    sim = PythonSimulator(lowered.module)
    sim.reset()

    # Create an 8x8 block in raster order.
    raster = np.zeros((8, 8), dtype=np.int16)
    raster[0, 0] = 128
    raster[0, 1] = 64
    raster[1, 0] = -32

    # Convert to zig-zag order.
    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = raster.flat[ri]

    # Feed zig-zag coefficients.
    for i in range(64):
        sim.step({"clk": 0, "rst": 0, "in_data": int(zz[i]) & 0xFFF, "in_valid": 1, "out_ready": 1})

    # Collect outputs.
    outputs = []
    for _ in range(80):
        r = sim.step({"clk": 0, "rst": 0, "in_data": 0, "in_valid": 0, "out_ready": 1})
        if r.get("out_valid"):
            outputs.append(r["out_data"])
        if len(outputs) >= 64:
            break

    raw = np.array(outputs[:64], dtype=np.int16)
    # Sign-extend from 12-bit to 16-bit.
    raw = np.where(raw >= 2048, raw - 4096, raw)
    got = raw.reshape(8, 8)
    print("Expected raster:")
    print(raster)
    print("Got:")
    print(got)
    print("Match:", np.array_equal(got, raster))


if __name__ == "__main__":
    main()
