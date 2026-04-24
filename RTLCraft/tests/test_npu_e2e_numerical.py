"""End-to-end numerical correctness tests for NPU vs PyTorch reference.

These tests compile a PyTorch model, run it on the NPU simulator, and compare
the output against a PyTorch reference computed with the same integer
weights/activations.

NOTE: The NPU systolic array expects weight/activation matrices stored with
`array_size` row stride.  Since the compiler's DMA LOAD only transfers
`tensor.numel()` contiguous words, we bypass DMA for numerical tests and write
JIT SRAM directly with the correct strided layout.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import torch
import torch.nn as nn
import numpy as np

from rtlgen.sim import Simulator
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.compiler.ir import NPUTensor, OpType
from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.common.npu_params import NeuralAccelParams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_jit_mem(sim, mem_name, data_dict):
    """Write data into a JIT-compiled memory region (same as test_npu_gemm_numerical)."""
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    for addr, val in data_dict.items():
        mem[addr] = int(val) & mask


def _read_jit_mem(sim, mem_name, addr, count=1):
    """Read data from a JIT-compiled memory region."""
    idx = sim._jit.mem_idx[mem_name]
    mem = sim._jit.memories[idx]
    width = sim._jit.mem_widths[idx]
    mask = (1 << width) - 1
    if count == 1:
        return mem[addr] & mask
    return [mem[addr + i] & mask for i in range(count)]


def _load_program(sim, instructions):
    for addr, instr in enumerate(instructions):
        sim.poke("prog_load_valid", 1)
        sim.poke("prog_load_addr", addr)
        sim.poke("prog_load_data", instr)
        sim.poke("prog_load_we", 1)
        sim.step()
    sim.poke("prog_load_valid", 0)
    sim.poke("prog_load_we", 0)


def _remove_load_store_instructions(instructions):
    """Remove LOAD/STORE instructions and their preceding DMA CONFIGs (func=0..3).

    Also clears orphaned wait_fences that referenced fences set by the
    removed LOAD/STORE instructions, preventing the core from deadlocking.
    """
    result = []
    removed_fences = set()
    for instr in instructions:
        opcode = (instr >> 28) & 0xF
        if opcode in (0x1, 0x2):  # LOAD or STORE
            removed_fences.add((instr >> 3) & 0x7)  # set_fence
            # Strip preceding DMA CONFIG func=0..3
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

    # Clear orphaned wait_fences
    cleared = []
    for instr in result:
        wf = instr & 0x7
        if wf in removed_fences:
            instr = instr & ~0x7  # clear wait_fence bits [2:0]
        cleared.append(instr)
    return cleared


def _write_tensor_to_sram(sim, tensor, data, array_size):
    """Write a 2-D tensor into JIT SRAM with array_size row stride.

    Layout expected by the systolic array: addr = row * array_size + col.
    """
    flat = data.flatten()
    shape = tensor.shape
    bank_names = {0: "sram_a_bank0", 1: "sram_b_bank0", 2: "sram_c_bank0"}
    mem_name = bank_names.get(tensor.buffer_id)
    assert mem_name is not None, f"Unsupported buffer_id {tensor.buffer_id}"

    if len(shape) == 2:
        rows, cols = shape
        for r in range(rows):
            for c in range(cols):
                val = int(flat[r * cols + c])
                addr = r * array_size + c
                _write_jit_mem(sim, mem_name, {addr: val})
    elif len(shape) == 4:
        if '.weight' in tensor.name:
            # Conv weight: (out_c, in_c, kh, kw) -> flatten to (out_c, in_c*kh*kw)
            out_c, in_c, kh, kw = shape
            cols = in_c * kh * kw
            for r in range(out_c):
                for c in range(cols):
                    val = int(flat[r * cols + c])
                    addr = r * array_size + c
                    _write_jit_mem(sim, mem_name, {addr: val})
        else:
            # Activation: (N, C, H, W) -> flatten to (N*H*W, C)
            n, c, h, w = shape
            rows = n * h * w
            cols = c
            for r in range(rows):
                for c_idx in range(cols):
                    val = int(flat[r * cols + c_idx])
                    addr = r * array_size + c_idx
                    _write_jit_mem(sim, mem_name, {addr: val})
    else:
        for i, val in enumerate(flat):
            _write_jit_mem(sim, mem_name, {i: int(val)})


def _read_tensor_from_sram(sim, tensor, array_size):
    """Read a 2-D tensor from JIT SRAM with array_size row stride."""
    shape = tensor.shape
    bank_names = {0: "sram_a_bank0", 1: "sram_b_bank0", 2: "sram_c_bank0"}
    mem_name = bank_names.get(tensor.buffer_id)
    assert mem_name is not None

    if len(shape) == 2:
        rows, cols = shape
        flat = []
        for r in range(rows):
            for c in range(cols):
                addr = r * array_size + c
                flat.append(_read_jit_mem(sim, mem_name, addr))
        return np.array(flat, dtype=np.int16).reshape(shape)
    elif len(shape) == 4:
        if '.weight' in tensor.name:
            out_c, in_c, kh, kw = shape
            cols = in_c * kh * kw
            flat = []
            for r in range(out_c):
                for c in range(cols):
                    addr = r * array_size + c
                    flat.append(_read_jit_mem(sim, mem_name, addr))
            return np.array(flat, dtype=np.int16).reshape(shape)
        else:
            n, c, h, w = shape
            rows = n * h * w
            cols = c
            flat = []
            for r in range(rows):
                for c_idx in range(cols):
                    addr = r * array_size + c_idx
                    flat.append(_read_jit_mem(sim, mem_name, addr))
            return np.array(flat, dtype=np.int16).reshape(shape)
    else:
        flat = _read_jit_mem(sim, mem_name, 0, tensor.numel())
        return np.array(flat, dtype=np.int16).reshape(shape)


# ---------------------------------------------------------------------------
# Test: Single Linear layer (identity weights)
# ---------------------------------------------------------------------------

def test_e2e_linear_identity():
    """A single Linear(4,4) with identity integer weights."""
    model = nn.Sequential(nn.Linear(4, 4, bias=False))
    x_torch = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x_torch)

    input_tensor = compiled.graph.tensors["input_1"]
    weight_tensor = compiled.graph.tensors["0.weight"]
    output_tensor = compiled.graph.tensors["_0"]

    # Small integer data
    w_int = np.eye(4, dtype=np.int16)
    x_int = np.array([[1, 2, 3, 4]], dtype=np.int16)

    # PyTorch reference (model has been fused/modified by compile_model)
    w_ref = torch.from_numpy(w_int.astype(np.float32))
    x_ref = torch.from_numpy(x_int.astype(np.float32))
    with torch.no_grad():
        model[0].weight.copy_(w_ref)
        y_ref = model(x_ref)

    # Run NPU with direct SRAM writes
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    array_size = npu.params.ARRAY_SIZE
    _write_tensor_to_sram(sim, weight_tensor, w_int, array_size)
    _write_tensor_to_sram(sim, input_tensor, x_int, array_size)

    stripped = _remove_load_store_instructions(compiled.instructions)
    _load_program(sim, stripped)

    sim.poke("prog_length", len(stripped))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    for i in range(5000):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break
    assert completed, f"NPU did not complete within 5000 cycles"

    y_npu = _read_tensor_from_sram(sim, output_tensor, array_size)
    y_ref_arr = y_ref.numpy().astype(np.int16)
    np.testing.assert_array_equal(y_npu, y_ref_arr,
        err_msg=f"NPU output mismatch.\nNPU:\n{y_npu}\nRef:\n{y_ref_arr}")


# ---------------------------------------------------------------------------
# Test: Linear + ReLU (diagonal weights)
# ---------------------------------------------------------------------------

def test_e2e_linear_relu():
    """Linear(4,4) + ReLU with diagonal integer weights."""
    model = nn.Sequential(
        nn.Linear(4, 4, bias=False),
        nn.ReLU(),
    )
    x_torch = torch.randn(1, 4)
    compiled = compile_model(model, example_input=x_torch)

    input_tensor = compiled.graph.tensors["input_1"]
    weight_tensor = compiled.graph.tensors["0.weight"]
    output_tensor = compiled.graph.tensors["_0"]

    # Diagonal weights: [1, -1, 1, -1] on diagonal
    w_int = np.diag([1, -1, 1, -1]).astype(np.int16)
    x_int = np.array([[5, 3, 2, 4]], dtype=np.int16)

    w_ref = torch.from_numpy(w_int.astype(np.float32))
    x_ref = torch.from_numpy(x_int.astype(np.float32))
    with torch.no_grad():
        model[0].weight.copy_(w_ref)
        y_ref = model(x_ref)

    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    array_size = npu.params.ARRAY_SIZE
    _write_tensor_to_sram(sim, weight_tensor, w_int, array_size)
    _write_tensor_to_sram(sim, input_tensor, x_int, array_size)

    stripped = _remove_load_store_instructions(compiled.instructions)
    _load_program(sim, stripped)

    sim.poke("prog_length", len(stripped))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    for i in range(5000):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break
    assert completed

    y_npu = _read_tensor_from_sram(sim, output_tensor, array_size)
    y_ref_arr = y_ref.numpy().astype(np.int16)
    np.testing.assert_array_equal(y_npu, y_ref_arr,
        err_msg=f"NPU output mismatch.\nNPU:\n{y_npu}\nRef:\n{y_ref_arr}")


# ---------------------------------------------------------------------------
# Test: Tiny ResNet18 end-to-end numerical
# ---------------------------------------------------------------------------

class TinyResNetBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU()
        self.shortcut = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_ch),
            )

    def forward(self, x):
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = out + self.shortcut(x)
        out = self.relu(out)
        return out


class TinyResNet18(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.relu = nn.ReLU()
        self.layer1 = self._make_layer(8, 8, 2, stride=1)
        self.layer2 = self._make_layer(8, 16, 2, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, num_classes)

    def _make_layer(self, in_ch, out_ch, num_blocks, stride):
        layers = [TinyResNetBlock(in_ch, out_ch, stride)]
        for _ in range(1, num_blocks):
            layers.append(TinyResNetBlock(out_ch, out_ch, stride=1))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


def test_tiled_conv_compile():
    """Verify compiler generates correct tiled instructions for K > ARRAY_SIZE."""
    torch.manual_seed(42)
    model = TinyResNet18(num_classes=10)
    model.eval()
    x_torch = torch.randn(1, 3, 8, 8)

    params = NeuralAccelParams(
        array_size=32,
        data_width=16,
        acc_width=32,
        sram_depth=65536,
        num_lanes=32,
    )

    compiled = compile_model(model, example_input=x_torch, params=params)

    # Count GEMM instructions and verify k_dim <= ARRAY_SIZE
    from skills.cpu.npu.compiler.codegen import OP_GEMM
    gemm_instrs = [i for i in compiled.instructions if ((i >> 28) & 0xF) == OP_GEMM]
    assert len(gemm_instrs) > 0, "No GEMM instructions generated"

    for instr in gemm_instrs:
        k_dim = (instr >> 6) & 0x3F
        assert k_dim <= params.ARRAY_SIZE, f"GEMM k_dim={k_dim} exceeds ARRAY_SIZE={params.ARRAY_SIZE}"

    # Verify group weights exist for layers with K > 32
    layer1_conv1_gemms = [i for i in gemm_instrs if ((i >> 6) & 0x3F) == 27]
    assert len(layer1_conv1_gemms) >= 2, "Expected multiple GEMM tiles for K=72 layer"

    # Verify IM2COL instructions exist for each tile
    from skills.cpu.npu.compiler.codegen import OP_IM2COL
    im2col_count = sum(1 for i in compiled.instructions if ((i >> 28) & 0xF) == OP_IM2COL)
    assert im2col_count >= len(layer1_conv1_gemms), "Expected IM2COL for each GEMM tile"


def test_e2e_tiny_resnet18_numerical():
    """End-to-end numerical test for a tiny ResNet18 on NPU.

    Uses identity-like integer weights. NOTE: RTL simulation of the full
    tiled model is very slow (~60 ms/cycle); this test may take 10+ minutes.
    """
    torch.manual_seed(42)
    model = TinyResNet18(num_classes=10)
    model.eval()
    x_torch = torch.randn(1, 3, 8, 8)

    params = NeuralAccelParams(
        array_size=32,
        data_width=16,
        acc_width=32,
        sram_depth=65536,
        num_lanes=32,
    )

    compiled = compile_model(model, example_input=x_torch, params=params)

    # Find input tensor from LOAD ops or fallback to graph heuristics
    input_tensor = None
    for op in compiled.graph.iter_ops():
        if hasattr(op, 'op_type') and str(op.op_type) == 'OpType.LOAD':
            if op.outputs:
                input_tensor = op.outputs[0]
                break
    if input_tensor is None:
        input_tensor = compiled.graph.tensors.get("x")
    assert input_tensor is not None, "Could not find input tensor"

    weight_tensors = {name: t for name, t in compiled.graph.tensors.items() if ".weight" in name}

    # Find output tensor (last non-LOAD/non-STORE op output)
    output_tensor = None
    for op in reversed(list(compiled.graph.iter_ops())):
        if hasattr(op, 'op_type') and str(op.op_type) not in ('OpType.LOAD', 'OpType.STORE'):
            if op.outputs:
                output_tensor = op.outputs[-1]
                break
    assert output_tensor is not None, "Could not find output tensor"

    array_size = params.ARRAY_SIZE

    # Replace all weights with small integer identity-like matrices
    w_int_map = {}
    with torch.no_grad():
        # First pass: generate original weights
        orig_weights = {}
        for pt_name, param in model.named_parameters():
            if '.weight' not in pt_name:
                continue
            if len(param.shape) == 4:
                out_c, in_c, kh, kw = param.shape
                w_4d = np.zeros(param.shape, dtype=np.int16)
                for oc in range(out_c):
                    ic = oc % in_c
                    w_4d[oc, ic, 0, 0] = 1
                orig_weights[pt_name] = w_4d
                param.data.copy_(torch.from_numpy(w_4d.astype(np.float32)))
            elif len(param.shape) == 2:
                rows, cols = param.shape
                w = np.zeros(param.shape, dtype=np.int16)
                for r in range(min(rows, cols)):
                    w[r, r] = 1
                orig_weights[pt_name] = w
                param.data.copy_(torch.from_numpy(w.astype(np.float32)))

        # Second pass: map to graph tensors (including group weights)
        for name, t in weight_tensors.items():
            base_name = name
            group_idx = None
            if '_g' in name:
                parts = name.rsplit('_g', 1)
                if parts[-1].isdigit():
                    base_name = parts[0]
                    group_idx = int(parts[-1])

            if base_name not in orig_weights:
                shape = t.shape
                if len(shape) == 2:
                    rows, cols = shape
                    w = np.zeros(shape, dtype=np.int16)
                    for r in range(min(rows, cols)):
                        w[r, r] = 1
                    w_int_map[name] = w
                else:
                    w_int_map[name] = np.ones(shape, dtype=np.int16)
                continue

            orig_w = orig_weights[base_name]
            if group_idx is not None and len(orig_w.shape) == 4:
                out_c, in_c, kh, kw = orig_w.shape
                max_in_c_per_group = array_size // (kh * kw)
                in_c_start = group_idx * max_in_c_per_group
                in_c_end = min(in_c, in_c_start + max_in_c_per_group)
                group_in_c = in_c_end - in_c_start
                if group_in_c > 0:
                    w_4d = orig_w[:, in_c_start:in_c_end, :, :]
                    w_int_map[name] = w_4d.reshape(t.shape)
                else:
                    w_int_map[name] = np.zeros(t.shape, dtype=np.int16)
            else:
                w_int_map[name] = orig_w.reshape(t.shape)

    x_int = np.ones(input_tensor.shape, dtype=np.int16)

    with torch.no_grad():
        x_ref = torch.from_numpy(x_int.astype(np.float32))
        y_ref = model(x_ref)
    y_ref_arr = y_ref.numpy().astype(np.int16)

    npu = NeuralAccel(params=params)
    sim = Simulator(npu)
    sim.reset("rst_n")

    # Write input tensor and any group input tensors
    input_tensors_to_write = {input_tensor.name: (input_tensor, x_int)}
    for name, t in compiled.graph.tensors.items():
        if '_input_g' in name and name.rsplit('_g', 1)[-1].isdigit():
            # Each group input gets independent ones data with its own shape
            input_tensors_to_write[name] = (t, np.ones(t.shape, dtype=np.int16))
    for name, (t, data) in input_tensors_to_write.items():
        _write_tensor_to_sram(sim, t, data, array_size)

    for name, t in weight_tensors.items():
        _write_tensor_to_sram(sim, t, w_int_map[name], array_size)

    stripped = _remove_load_store_instructions(compiled.instructions)
    _load_program(sim, stripped)

    sim.poke("prog_length", len(stripped))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    max_cycles = 50000
    for i in range(max_cycles):
        sim.step()
        if sim.peek("prog_done"):
            completed = True
            break
    assert completed, f"NPU did not complete within {max_cycles} cycles (stopped at {i})"

    y_npu = _read_tensor_from_sram(sim, output_tensor, array_size)
    np.testing.assert_allclose(y_npu.astype(np.float32), y_ref_arr.astype(np.float32),
                               rtol=0, atol=1,
                               err_msg="NPU output does not match PyTorch reference")
