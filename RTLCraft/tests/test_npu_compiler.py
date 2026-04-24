"""Tests for NeuralAccel PyTorch Compiler."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
import torch
import torch.nn as nn
import numpy as np

from skills.cpu.npu.compiler import compile_model, lower_model, compile_graph
from skills.cpu.npu.compiler.ir import (
    NPUGraph, NPUTensor, GemmOp, VecALUOp, SFUOp,
    LoadOp, StoreOp, SyncOp, VecALUFunc, SFUFunc, DataType,
)
from skills.cpu.npu.compiler.codegen import (
    OP_GEMM, OP_VEC_ALU, OP_SFU, OP_LOAD, OP_STORE, OP_CONFIG, OP_SYNC,
)


# ---------------------------------------------------------------------------
# IR Tests
# ---------------------------------------------------------------------------

def test_tensor_numel():
    """NPUTensor.numel should compute element count."""
    t = NPUTensor(name="x", shape=(2, 3, 4))
    assert t.numel() == 24


def test_tensor_size_bytes():
    """NPUTensor.size_bytes should compute byte size."""
    t = NPUTensor(name="x", shape=(8, 8), dtype=DataType.INT16)
    assert t.size_bytes() == 128  # 64 elements * 2 bytes


def test_npu_graph_construction():
    """NPUGraph should support adding ops."""
    graph = NPUGraph(name="test")
    a = NPUTensor(name="a", shape=(8, 8))
    b = NPUTensor(name="b", shape=(8, 8))
    c = NPUTensor(name="c", shape=(8, 8))

    op = GemmOp(name="gemm0", input_a=a, input_b=b, output=c, k_dim=8)
    graph.add_op(op)

    assert len(graph.ops) == 1
    assert "a" in graph.tensors
    assert "b" in graph.tensors
    assert "c" in graph.tensors


# ---------------------------------------------------------------------------
# Lowering Tests
# ---------------------------------------------------------------------------

def test_lower_linear():
    """Lowering should convert nn.Linear to GEMM + bias."""
    model = nn.Linear(8, 4, bias=True)
    graph = lower_model(model, example_input=torch.randn(1, 8))

    op_types = [op.op_type.name for op in graph.ops]
    assert "LOAD" in op_types
    assert "GEMM" in op_types
    assert "VEC_ALU" in op_types  # bias add


def test_lower_relu():
    """Lowering should convert nn.ReLU to VEC_ALU."""
    model = nn.Sequential(
        nn.Linear(8, 4),
        nn.ReLU(),
    )
    graph = lower_model(model, example_input=torch.randn(1, 8))

    op_types = [op.op_type.name for op in graph.ops]
    assert "GEMM" in op_types
    assert "VEC_ALU" in op_types


def test_lower_sigmoid():
    """Lowering should convert nn.Sigmoid to SFU."""
    model = nn.Sequential(
        nn.Linear(8, 4),
        nn.Sigmoid(),
    )
    graph = lower_model(model, example_input=torch.randn(1, 8))

    op_types = [op.op_type.name for op in graph.ops]
    assert "GEMM" in op_types
    assert "SFU" in op_types


def test_lower_mlp():
    """Lowering should handle a small MLP."""
    model = nn.Sequential(
        nn.Linear(16, 8),
        nn.ReLU(),
        nn.Linear(8, 4),
    )
    graph = lower_model(model, example_input=torch.randn(1, 16))

    op_types = [op.op_type.name for op in graph.ops]
    assert op_types.count("GEMM") == 2
    assert op_types.count("VEC_ALU") >= 1  # ReLU + bias adds


# ---------------------------------------------------------------------------
# CodeGen Tests
# ---------------------------------------------------------------------------

def test_codegen_load_store():
    """CodeGen should emit LOAD and STORE instructions."""
    graph = NPUGraph(name="test")
    src = NPUTensor(name="src", shape=(8,), external_addr=0x1000)
    dst = NPUTensor(name="dst", shape=(8,))

    graph.add_op(LoadOp(name="load0", src=src, dst=dst))
    graph.add_op(StoreOp(name="store0", src=dst, dst=src))

    instructions, _ = compile_graph(graph, sram_depth=256)

    assert len(instructions) > 0
    # Should have CONFIG instructions + LOAD + CONFIG + STORE
    opcodes = [(i >> 28) & 0xF for i in instructions]
    assert OP_CONFIG in opcodes
    assert OP_LOAD in opcodes
    assert OP_STORE in opcodes


def test_codegen_gemm():
    """CodeGen should emit GEMM instruction."""
    graph = NPUGraph(name="test")
    a = NPUTensor(name="a", shape=(8, 8))
    b = NPUTensor(name="b", shape=(8, 8))
    c = NPUTensor(name="c", shape=(8, 8))

    graph.add_op(GemmOp(name="gemm0", input_a=a, input_b=b, output=c, k_dim=8))

    instructions, _ = compile_graph(graph, sram_depth=256)
    opcodes = [(i >> 28) & 0xF for i in instructions]
    assert OP_GEMM in opcodes


def test_codegen_vec_alu():
    """CodeGen should emit VEC_ALU instruction."""
    graph = NPUGraph(name="test")
    a = NPUTensor(name="a", shape=(8,))
    b = NPUTensor(name="b", shape=(8,))
    c = NPUTensor(name="c", shape=(8,))

    graph.add_op(VecALUOp(name="add0", func=VecALUFunc.ADD, inputs=[a, b], output=c))

    instructions, _ = compile_graph(graph, sram_depth=256)
    opcodes = [(i >> 28) & 0xF for i in instructions]
    assert OP_VEC_ALU in opcodes


def test_codegen_sfu():
    """CodeGen should emit SFU instruction."""
    graph = NPUGraph(name="test")
    a = NPUTensor(name="a", shape=(8,))
    b = NPUTensor(name="b", shape=(8,))

    graph.add_op(SFUOp(name="sig0", func=SFUFunc.SIGMOID, input_t=a, output=b))

    instructions, _ = compile_graph(graph, sram_depth=256)
    opcodes = [(i >> 28) & 0xF for i in instructions]
    assert OP_SFU in opcodes


def test_codegen_asm_output():
    """CodeGen should produce readable assembly."""
    graph = NPUGraph(name="test")
    a = NPUTensor(name="a", shape=(8,))
    b = NPUTensor(name="b", shape=(8,))

    graph.add_op(SyncOp(name="sync0"))

    instructions, _ = compile_graph(graph, sram_depth=256)
    codegen = __import__("skills.cpu.npu.compiler.codegen", fromlist=["NPUCodeGen"]).NPUCodeGen()
    codegen.instructions = instructions
    asm = codegen.to_asm()
    assert "SYNC" in asm


# ---------------------------------------------------------------------------
# End-to-End Tests
# ---------------------------------------------------------------------------

def test_compile_model_e2e():
    """End-to-end compile a small model."""
    model = nn.Sequential(
        nn.Linear(8, 4),
        nn.ReLU(),
    )
    compiled = compile_model(model, example_input=torch.randn(1, 8))

    assert len(compiled.instructions) > 0
    assert len(compiled.weight_data) > 0
    assert compiled.to_asm() is not None
    assert compiled.to_binary() is not None


def test_compile_model_weights():
    """Compiled model should include quantized weights."""
    model = nn.Linear(4, 2, bias=False)
    # Initialize with known values
    with torch.no_grad():
        model.weight.copy_(torch.tensor([[1.0, 2.0, 3.0, 4.0],
                                          [5.0, 6.0, 7.0, 8.0]]))

    compiled = compile_model(model, example_input=torch.randn(1, 4))

    # Should have weight data
    weight_keys = [k for k in compiled.weight_data.keys() if "weight" in k]
    assert len(weight_keys) > 0

    # Quantized weights should be numpy int16 arrays
    wname = weight_keys[0]
    wdata = compiled.weight_data[wname]
    assert isinstance(wdata, np.ndarray)
    assert wdata.dtype == np.int16
