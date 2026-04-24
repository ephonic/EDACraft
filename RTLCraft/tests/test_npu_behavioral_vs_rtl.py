"""RTL vs Behavioral Model comparison tests.

These tests run the same program on both the fast Python behavioral model
and the full RTL simulator, then compare final SRAM states.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import torch
import torch.nn as nn

from rtlgen.sim import Simulator
from skills.cpu.npu.sim.behavioral_model import NPUBehavioralModel
from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams


def _remove_load_store_instructions(instructions):
    """Remove LOAD/STORE instructions and their preceding DMA CONFIGs."""
    result = []
    for instr in instructions:
        opcode = (instr >> 28) & 0xF
        if opcode in (0x1, 0x2):  # LOAD or STORE
            while result:
                prev = result[-1]
                prev_opcode = (prev >> 28) & 0xF
                prev_func = (prev >> 24) & 0xF
                if prev_opcode == 0x8 and prev_func in (0, 1, 2, 3):
                    result.pop()
                else:
                    break
        else:
            result.append(instr)
    return result


def _load_program(sim, instructions):
    for addr, instr in enumerate(instructions):
        sim.poke("prog_load_valid", 1)
        sim.poke("prog_load_addr", addr)
        sim.poke("prog_load_data", instr)
        sim.poke("prog_load_we", 1)
        sim.step()
    sim.poke("prog_load_valid", 0)
    sim.poke("prog_load_we", 0)


def _write_jit_mem(sim, mem_name, data_dict):
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    for addr, val in data_dict.items():
        mem[addr] = int(val) & mask


def _read_jit_mem(sim, mem_name, addr, count=1):
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    if count == 1:
        return mem[addr] & mask
    return [mem[addr + i] & mask for i in range(count)]


def _write_tensor_to_sram_jit(sim, buf_name, data, array_size):
    """Write a 2-D tensor into JIT SRAM with array_size row stride."""
    flat = data.flatten()
    shape = data.shape
    if len(shape) == 2:
        rows, cols = shape
        for r in range(rows):
            for c in range(cols):
                val = int(flat[r * cols + c])
                addr = r * array_size + c
                _write_jit_mem(sim, buf_name, {addr: val})
    elif len(shape) == 4:
        out_c, in_c, kh, kw = shape
        cols = in_c * kh * kw
        for r in range(out_c):
            for c in range(cols):
                val = int(flat[r * cols + c])
                addr = r * array_size + c
                _write_jit_mem(sim, buf_name, {addr: val})
    else:
        for i, val in enumerate(flat):
            _write_jit_mem(sim, buf_name, {i: int(val)})


def _read_tensor_from_sram_jit(sim, buf_name, shape, array_size):
    """Read a tensor from JIT SRAM with array_size row stride, handling signedness."""
    if len(shape) == 2:
        rows, cols = shape
        flat = []
        for r in range(rows):
            for c in range(cols):
                addr = r * array_size + c
                val = _read_jit_mem(sim, buf_name, addr)
                if val > 32767:
                    val -= 65536
                flat.append(val)
        return np.array(flat, dtype=np.int16).reshape(shape)
    elif len(shape) == 4:
        out_c, in_c, kh, kw = shape
        cols = in_c * kh * kw
        flat = []
        for r in range(out_c):
            for c in range(cols):
                addr = r * array_size + c
                val = _read_jit_mem(sim, buf_name, addr)
                if val > 32767:
                    val -= 65536
                flat.append(val)
        return np.array(flat, dtype=np.int16).reshape(shape)
    else:
        count = np.prod(shape)
        flat = _read_jit_mem(sim, buf_name, 0, count)
        flat = [(v - 65536 if v > 32767 else v) for v in flat]
        return np.array(flat, dtype=np.int16).reshape(shape)


def run_rtl_simulation(instructions, buffer_writes, array_size=32, max_cycles=5000):
    """Run program on RTL simulator and return final buffer states.
    
    Args:
        instructions: list of binary instructions
        buffer_writes: dict of {buf_id: (buf_name, numpy_array)}
        array_size: systolic array size
        max_cycles: simulation timeout
    
    Returns:
        dict of {buf_id: numpy_array} with final SRAM contents
    """
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    buf_id_to_name = {0: "sram_a_bank0", 1: "sram_b_bank0", 2: "sram_c_bank0", 3: "sram_c_bank0"}

    for buf_id, (buf_name, data) in buffer_writes.items():
        _write_tensor_to_sram_jit(sim, buf_name, data, array_size)

    _load_program(sim, instructions)
    sim.poke("prog_length", len(instructions))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    for i in range(max_cycles):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break

    if not completed:
        raise TimeoutError(f"RTL simulation did not complete within {max_cycles} cycles")

    # Read back all buffers
    results = {}
    for buf_id, (buf_name, data) in buffer_writes.items():
        # For result buffer (buf_id=2), use the shape from the original data
        # For input buffers, just read back what was written
        results[buf_id] = _read_tensor_from_sram_jit(sim, buf_name, data.shape, array_size)

    # Also read SRAM_C if it wasn't in buffer_writes
    if 2 not in buffer_writes:
        # Can't determine shape, skip
        pass

    return results, sim


def run_behavioral_model(instructions, buffer_writes, array_size=32):
    """Run program on behavioral model and return final buffer states."""
    bm = NPUBehavioralModel()
    bm.params.ARRAY_SIZE = array_size
    bm.array_size = array_size

    for buf_id, (buf_name, data) in buffer_writes.items():
        bm.write_buffer(buf_id, data, array_size=array_size)

    bm.load_program(instructions)
    bm.run()

    results = {}
    for buf_id, (buf_name, data) in buffer_writes.items():
        results[buf_id] = bm.read_buffer(buf_id, data.shape, array_size=array_size)

    return results


def compare_buffers(buffers_rtl, buffers_bm, rtol=0, atol=0):
    """Compare RTL and behavioral model buffer contents."""
    for buf_id in sorted(set(buffers_rtl.keys()) | set(buffers_bm.keys())):
        rtl = buffers_rtl.get(buf_id)
        bm = buffers_bm.get(buf_id)
        if rtl is None or bm is None:
            continue
        try:
            np.testing.assert_allclose(rtl.astype(np.float32), bm.astype(np.float32),
                                       rtol=rtol, atol=atol)
        except AssertionError as e:
            diff = rtl.astype(np.int32) - bm.astype(np.int32)
            mismatch = np.where(diff != 0)
            first_idx = tuple(m[0] for m in mismatch) if len(mismatch[0]) > 0 else None
            details = f""
            if first_idx is not None:
                details = f"  First mismatch at {first_idx}: RTL={rtl[first_idx]}, BM={bm[first_idx]}"
            raise AssertionError(f"Buffer {buf_id} mismatch. {e}\n{details}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_identity_gemm_behavioral_only():
    """Quick sanity: behavioral model identity GEMM matches PyTorch."""
    model = nn.Sequential(nn.Linear(4, 4, bias=False))
    x = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x)

    w_int = np.eye(4, dtype=np.int16)
    x_int = np.array([[1, 2, 3, 4]], dtype=np.int16)

    stripped = _remove_load_store_instructions(compiled.instructions)

    buffer_writes = {
        0: ("sram_a_bank0", w_int),
        1: ("sram_b_bank0", x_int),
    }

    bm_results = run_behavioral_model(stripped, buffer_writes)
    y_bm = bm_results[1]  # read back from buffer 1 (SRAM_B was input, but result is in SRAM_C)
    # Actually result is in SRAM_C (buf_id=2), which wasn't in buffer_writes
    # Let's read it manually
    bm = NPUBehavioralModel()
    bm.write_buffer(0, w_int)
    bm.write_buffer(1, x_int)
    bm.load_program(stripped)
    bm.run()
    y_bm = bm.read_buffer(2, (1, 4))

    with torch.no_grad():
        model[0].weight.copy_(torch.from_numpy(w_int.astype(np.float32)))
        y_ref = model(torch.from_numpy(x_int.astype(np.float32)))

    np.testing.assert_array_equal(y_bm, y_ref.numpy().astype(np.int16))


def test_linear_relu_behavioral_only():
    """Behavioral model Linear+ReLU matches PyTorch."""
    model = nn.Sequential(nn.Linear(4, 4, bias=False), nn.ReLU())
    x = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x)

    w_int = np.diag([1, -1, 1, -1]).astype(np.int16)
    x_int = np.array([[5, 3, 2, 4]], dtype=np.int16)

    stripped = _remove_load_store_instructions(compiled.instructions)

    bm = NPUBehavioralModel()
    bm.write_buffer(0, w_int)
    bm.write_buffer(1, x_int)
    bm.load_program(stripped)
    bm.run()
    y_bm = bm.read_buffer(2, (1, 4))

    with torch.no_grad():
        model[0].weight.copy_(torch.from_numpy(w_int.astype(np.float32)))
        y_ref = model(torch.from_numpy(x_int.astype(np.float32)))

    np.testing.assert_array_equal(y_bm, y_ref.numpy().astype(np.int16))


def test_linear_identity_rtl_vs_behavioral():
    """Compare RTL and behavioral model for identity Linear."""
    model = nn.Sequential(nn.Linear(4, 4, bias=False))
    x = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x)

    w_int = np.eye(4, dtype=np.int16)
    x_int = np.array([[1, 2, 3, 4]], dtype=np.int16)

    stripped = _remove_load_store_instructions(compiled.instructions)

    buffer_writes = {
        0: ("sram_a_bank0", w_int),
        1: ("sram_b_bank0", x_int),
    }

    bm_results = run_behavioral_model(stripped, buffer_writes)
    # Manually read result from SRAM_C
    bm = NPUBehavioralModel()
    bm.write_buffer(0, w_int)
    bm.write_buffer(1, x_int)
    bm.load_program(stripped)
    bm.run()
    y_bm = bm.read_buffer(2, (1, 4))

    rtl_results, sim = run_rtl_simulation(stripped, buffer_writes, max_cycles=5000)
    y_rtl = _read_tensor_from_sram_jit(sim, "sram_c_bank0", (1, 4), 32)

    np.testing.assert_array_equal(y_rtl, y_bm,
        err_msg=f"RTL vs Behavioral mismatch.\nRTL:\n{y_rtl}\nBM:\n{y_bm}")


def test_linear_relu_rtl_vs_behavioral():
    """Compare RTL and behavioral model for Linear+ReLU."""
    model = nn.Sequential(nn.Linear(4, 4, bias=False), nn.ReLU())
    x = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x)

    w_int = np.diag([1, -1, 1, -1]).astype(np.int16)
    x_int = np.array([[5, 3, 2, 4]], dtype=np.int16)

    stripped = _remove_load_store_instructions(compiled.instructions)

    buffer_writes = {
        0: ("sram_a_bank0", w_int),
        1: ("sram_b_bank0", x_int),
    }

    bm = NPUBehavioralModel()
    bm.write_buffer(0, w_int)
    bm.write_buffer(1, x_int)
    bm.load_program(stripped)
    bm.run()
    y_bm = bm.read_buffer(2, (1, 4))

    rtl_results, sim = run_rtl_simulation(stripped, buffer_writes, max_cycles=5000)
    y_rtl = _read_tensor_from_sram_jit(sim, "sram_c_bank0", (1, 4), 32)

    np.testing.assert_array_equal(y_rtl, y_bm,
        err_msg=f"RTL vs Behavioral mismatch.\nRTL:\n{y_rtl}\nBM:\n{y_bm}")
