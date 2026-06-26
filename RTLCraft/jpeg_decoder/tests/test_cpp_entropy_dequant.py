"""Test entropy->dequant with C++ backend."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from rtlgen_x.dsl import build_compiled_simulator_from_dsl, lower_dsl_module_to_sim
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


from rtlgen_x.dsl import Module, Input, Output, Wire


class Chain(Module):
    def __init__(self):
        super().__init__("Chain")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.s_axis_tdata = Input(8, "s_axis_tdata")
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tready = Output(1, "s_axis_tready")
        self.out_data = Output(12, "out_data", signed=True)
        self.out_valid = Output(1, "out_valid")
        self.out_ready = Input(1, "out_ready")

        e = JpegEntropyDecoder(name="entropy")
        dq = JpegDequantZigzag(name="dequant")

        coeff = Wire(12, "coeff", signed=True)
        coeff_valid = Wire(1, "coeff_valid")
        block_valid = Wire(1, "block_valid")
        block_ready = Wire(1, "block_ready")
        block_ready <<= 1
        coeff_ready = Wire(1, "coeff_ready")
        coeff_ready <<= 1

        self.instantiate(e, "u_e", port_map={
            "clk": self.clk, "rst": self.rst,
            "s_axis_tdata": self.s_axis_tdata,
            "s_axis_tvalid": self.s_axis_tvalid,
            "s_axis_tready": self.s_axis_tready,
            "s_axis_tlast": Wire(1, "tlast"),
            "coeff_out": coeff, "coeff_valid": coeff_valid,
            "coeff_ready": coeff_ready,
            "block_valid": block_valid, "block_ready": block_ready,
        })
        self.instantiate(dq, "u_dq", port_map={
            "clk": self.clk, "rst": self.rst,
            "in_data": coeff, "in_valid": coeff_valid, "in_ready": Wire(1, "dq_in_ready"),
            "out_data": self.out_data, "out_valid": self.out_valid, "out_ready": self.out_ready,
        })


def run(sim, bytes_stream):
    byte_idx = 0
    outputs = []
    for cyc in range(300):
        if byte_idx < len(bytes_stream):
            tdata = bytes_stream[byte_idx]
            tvalid = 1
        else:
            tdata = 0
            tvalid = 0
        r = sim.step({"clk": 0, "rst": 0, "s_axis_tdata": tdata, "s_axis_tvalid": tvalid, "out_ready": 1})
        if r.get("s_axis_tready") and tvalid:
            byte_idx += 1
        if r.get("out_valid"):
            v = r["out_data"]
            if v >= 2048:
                v -= 4096
            outputs.append(v)
        if len(outputs) >= 64:
            break
    return outputs


def main():
    coeffs = np.zeros((8, 8), dtype=np.int16)
    coeffs[0, 0] = 128
    coeffs[0, 1] = 64
    coeffs[1, 0] = -32

    zz = np.zeros(64, dtype=np.int16)
    for i, ri in enumerate(ZIGZAG_ORDER):
        zz[i] = coeffs.flat[ri]

    tokens = encode_block(zz)
    bytes_stream = []
    for t in tokens:
        bytes_stream.append(t & 0xFF)
        bytes_stream.append((t >> 8) & 0xFF)

    expected = coeffs

    print("Python:")
    py_sim = PythonSimulator(lower_dsl_module_to_sim(Chain()).module)
    py_sim.reset()
    py_out = np.array(run(py_sim, bytes_stream)[:64], dtype=np.int16).reshape(8, 8)
    print(py_out)
    print("Match:", np.array_equal(py_out, expected))

    print("C++:")
    with build_compiled_simulator_from_dsl(Chain(), build_dir="jpeg_decoder/build/cpp_ed") as cpp_sim:
        cpp_sim.reset()
        cpp_out = np.array(run(cpp_sim, bytes_stream)[:64], dtype=np.int16).reshape(8, 8)
        print(cpp_out)
        print("Match:", np.array_equal(cpp_out, expected))


if __name__ == "__main__":
    main()
