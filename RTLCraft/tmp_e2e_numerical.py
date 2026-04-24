"""Prototype for numerical end-to-end ResNet18 test."""
import sys
sys.path.insert(0, 'g:/code/rtlgen/rtlgen')

import torch
import torch.nn as nn
import numpy as np

from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.compiler.layout import quantize_tensor
from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.core import NeuralAccel
from rtlgen.sim import Simulator

print("Imports done")

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

print("Classes defined")

torch.manual_seed(42)
model = TinyResNet18(num_classes=10)
model.eval()
print("Model created")

for m in model.modules():
    if isinstance(m, nn.BatchNorm2d):
        m.weight.data.fill_(1.0)
        m.bias.data.fill_(0.0)
        m.running_mean.fill_(0.0)
        m.running_var.fill_(1.0)
print("BN identity set")

for m in model.modules():
    if isinstance(m, (nn.Conv2d, nn.Linear)):
        m.weight.data = torch.randint(-2, 3, m.weight.shape).float()
        if m.bias is not None:
            m.bias.data = torch.randint(-2, 3, m.bias.shape).float()
print("Weights set")

x = torch.randint(-2, 3, (1, 3, 8, 8)).float()
print(f"Input shape: {x.shape}")

with torch.no_grad():
    y_ref = model(x)
print(f"PyTorch reference: {y_ref.numpy().flatten()}")

params = NeuralAccelParams(array_size=32, data_width=16, acc_width=32, sram_depth=65536, num_lanes=32)
print("Compiling...")
compiled = compile_model(model, example_input=x, params=params)
print(f"Compiled: {len(compiled.instructions)} instructions")

# Filter out LOAD instructions
filtered_instr = []
for instr in compiled.instructions:
    opcode = (instr >> 28) & 0xF
    if opcode != 0x1:
        filtered_instr.append(instr)
print(f"Filtered: {len(filtered_instr)} instructions")

print("Creating NPU...")
npu = NeuralAccel(params=params)
print("Creating Simulator...")
sim = Simulator(npu)
print("Resetting...")
sim.reset("rst_n")
print("Simulator ready")
