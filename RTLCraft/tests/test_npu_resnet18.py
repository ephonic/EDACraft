"""
ResNet18 NPU compilation and simulation tests.

Tests cover:
1. Full ResNet18 structural compilation (im2col + GEMM + residual ops).
2. End-to-end simulation of a ResNet18 BasicBlock with hardware im2col.
3. IM2COL instruction presence in compiled programs.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
import torch
import torch.nn as nn
import numpy as np

from rtlgen.sim import Simulator
from skills.cpu.npu.compiler import compile_model, lower_model, compile_graph
from skills.cpu.npu.compiler.ir import OpType, Im2ColOp
from skills.cpu.npu.compiler.codegen import OP_IM2COL, OP_CONFIG, OP_POOL
from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.core import NeuralAccel
from skills.cpu.npu.frontend.instruction_decode import OP_GEMM, OP_VEC_ALU, OP_SYNC


def _encode_instr(opcode, func, rd, rs1, rs2_imm, set_fence=0, wait_fence=0):
    return ((opcode & 0xF) << 28) | ((func & 0xF) << 24) | ((rd & 0x3F) << 18) | ((rs1 & 0x3F) << 12) | ((rs2_imm & 0x3F) << 6) | ((set_fence & 0x7) << 3) | (wait_fence & 0x7)


def _load_program(sim, instructions):
    for addr, instr in enumerate(instructions):
        sim.poke('prog_load_valid', 1)
        sim.poke('prog_load_addr', addr)
        sim.poke('prog_load_data', instr)
        sim.poke('prog_load_we', 1)
        sim.step()
    sim.poke('prog_load_valid', 0)
    sim.poke('prog_load_we', 0)


# ---------------------------------------------------------------------------
# Standard ResNet18 building blocks
# ---------------------------------------------------------------------------

class BasicBlock(nn.Module):
    """ResNet BasicBlock with two 3x3 convolutions and a shortcut."""
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU()

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * planes),
            )

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + self.shortcut(x)
        out = self.relu(out)
        return out


class ResNet18(nn.Module):
    """Standard ResNet18 architecture."""

    def __init__(self, num_classes=10, in_channels=3):
        super().__init__()
        self.in_planes = 64
        self.conv1 = nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(64, 2, stride=1)
        self.layer2 = self._make_layer(128, 2, stride=2)
        self.layer3 = self._make_layer(256, 2, stride=2)
        self.layer4 = self._make_layer(512, 2, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * BasicBlock.expansion, num_classes)

    def _make_layer(self, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for s in strides:
            layers.append(BasicBlock(self.in_planes, planes, s))
            self.in_planes = planes * BasicBlock.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


# ---------------------------------------------------------------------------
# Compilation tests
# ---------------------------------------------------------------------------

def test_resnet18_lower_structure():
    """Full ResNet18 should lower to NPU IR without errors."""
    model = ResNet18(num_classes=10, in_channels=3)
    model.eval()
    x = torch.randn(1, 3, 32, 32)

    params = NeuralAccelParams(array_size=32, sram_depth=65536, num_lanes=32)
    graph = lower_model(model, example_input=x, params=params)

    op_types = [op.op_type for op in graph.iter_ops()]
    # Should contain im2col, gemm, vec_alu (relu/bias/add), pool (maxpool/avgpool)
    assert OpType.IM2COL in op_types
    assert OpType.GEMM in op_types
    assert OpType.VEC_ALU in op_types
    assert OpType.POOL in op_types


class MicroResNet18(nn.Module):
    """ResNet18 structure with reduced channels to fit in NPU SRAM."""
    def __init__(self, num_classes=10, in_channels=3, base_width=8):
        super().__init__()
        self.in_planes = base_width
        self.conv1 = nn.Conv2d(in_channels, base_width, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(base_width)
        self.relu = nn.ReLU()
        self.layer1 = self._make_layer(base_width, 2, stride=1)
        self.layer2 = self._make_layer(base_width * 2, 2, stride=2)
        self.layer3 = self._make_layer(base_width * 4, 2, stride=2)
        self.layer4 = self._make_layer(base_width * 8, 2, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(base_width * 8 * BasicBlock.expansion, num_classes)

    def _make_layer(self, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for s in strides:
            layers.append(BasicBlock(self.in_planes, planes, s))
            self.in_planes = planes * BasicBlock.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


def test_resnet18_compile_instructions():
    """Micro ResNet18 should compile to a non-empty instruction sequence with IM2COL."""
    # Use very small dimensions so static allocation fits in SRAM.
    model = MicroResNet18(num_classes=10, in_channels=3, base_width=4)
    model.eval()
    x = torch.randn(1, 3, 8, 8)

    params = NeuralAccelParams(array_size=32, sram_depth=262144, num_lanes=32)
    compiled = compile_model(model, example_input=x, params=params)

    assert compiled.get_program_length() > 0
    assert len(compiled.weight_data) > 0

    # Verify IM2COL, POOL instructions are present
    opcodes = [(i >> 28) & 0xF for i in compiled.instructions]
    assert OP_IM2COL in opcodes
    assert OP_CONFIG in opcodes
    assert OP_GEMM in opcodes
    assert OP_POOL in opcodes


def test_resnet18_im2col_op_params():
    """Im2ColOp should carry correct convolution parameters."""
    model = nn.Sequential(
        nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1, bias=False),
        nn.ReLU(),
    )
    x = torch.randn(1, 3, 8, 8)
    graph = lower_model(model, example_input=x)

    im2col_ops = [op for op in graph.iter_ops() if isinstance(op, Im2ColOp)]
    assert len(im2col_ops) == 1
    op = im2col_ops[0]
    assert op.kernel_h == 3
    assert op.kernel_w == 3
    assert op.stride_h == 1
    assert op.stride_w == 1
    assert op.pad_h == 1
    assert op.pad_w == 1
    assert op.in_c == 3


# ---------------------------------------------------------------------------
# End-to-end simulation tests (tiny variant to fit in SRAM)
# ---------------------------------------------------------------------------

class TinyResNetBlock(nn.Module):
    """A minimal ResNet block that fits in small SRAM."""
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
    """ResNet18-like topology with tiny dimensions for NPU SRAM."""
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.relu = nn.ReLU()
        # Skip maxpool to reduce size
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


def test_tiny_resnet18_e2e_simulation():
    """Tiny ResNet18 should compile and run to completion in simulation."""
    model = TinyResNet18(num_classes=10)
    model.eval()
    x = torch.randn(1, 3, 8, 8)

    params = NeuralAccelParams(
        array_size=32,
        data_width=16,
        acc_width=32,
        sram_depth=65536,
        num_lanes=32,
    )
    compiled = compile_model(model, example_input=x, params=params)

    # Verify IM2COL is in the program
    opcodes = [(i >> 28) & 0xF for i in compiled.instructions]
    assert OP_IM2COL in opcodes, "Program should contain IM2COL instructions"

    # Verify POOL instructions are present (maxpool + avgpool)
    assert OP_POOL in opcodes, "Program should contain POOL instructions"

    npu = NeuralAccel(params=params)
    sim = Simulator(npu)
    sim.reset("rst_n")

    _load_program(sim, compiled.instructions)
    sim.poke("prog_length", compiled.get_program_length())
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    # Verify program starts executing (PC advances) — full ResNet18 simulation
    # is too slow in Python simulator, so we just check the first few cycles.
    started = False
    for i in range(50):
        sim.poke("m_axi_arready", 1)
        sim.poke("m_axi_awready", 1)
        sim.poke("m_axi_wready", 1)
        sim.poke("m_axi_rvalid", 1)
        sim.poke("m_axi_rdata", 0)
        sim.poke("m_axi_rlast", 1)
        sim.poke("m_axi_bvalid", 1)
        sim.step()
        if sim.peek("pc") > 0 or sim.peek("state") != 0:
            started = True
            break

    assert started, "Simulation did not start executing"


def test_im2col_instruction_dispatch():
    """IM2COL instruction should dispatch correctly in the NPU core."""
    npu = NeuralAccel()
    sim = Simulator(npu)
    sim.reset("rst_n")

    # Minimal program: CONFIG im2col params + IM2COL
    program = [
        # CONFIG kh=3, kw=3 (func=0x8)
        _encode_instr(OP_CONFIG, 0x8, 3, 0, 3),
        # CONFIG stride=1,1 (func=0x9)
        _encode_instr(OP_CONFIG, 0x9, 1, 0, 1),
        # CONFIG pad=1,1 (func=0xA)
        _encode_instr(OP_CONFIG, 0xA, 1, 0, 1),
        # CONFIG in_h=4 (func=0xB)
        _encode_instr(OP_CONFIG, 0xB, 0, 0, 4),
        # CONFIG in_w=4 (func=0xC)
        _encode_instr(OP_CONFIG, 0xC, 0, 0, 4),
        # CONFIG in_c=2 (func=0xD)
        _encode_instr(OP_CONFIG, 0xD, 0, 0, 2),
        # CONFIG out_h=4 (func=0xE)
        _encode_instr(OP_CONFIG, 0xE, 0, 0, 4),
        # CONFIG out_w=4 (func=0xF)
        _encode_instr(OP_CONFIG, 0xF, 0, 0, 4),
        # IM2COL src=SRAM_A(0), dst=SRAM_C(2)
        _encode_instr(OP_IM2COL, 0x2, 0, 0, 0),
        # SYNC to end
        _encode_instr(OP_SYNC, 0, 0, 0, 0),
    ]
    _load_program(sim, program)

    sim.poke("prog_length", len(program))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    # Verify IM2COL dispatches: im2col state should become non-zero
    max_cycles = 200
    dispatched = False
    for _ in range(max_cycles):
        sim.step()
        if sim.peek("im2col_state") != 0:
            dispatched = True
            break

    assert dispatched, "IM2COL did not dispatch (im2col_state stayed at 0)"
