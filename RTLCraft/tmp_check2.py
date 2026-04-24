import sys
sys.path.insert(0, 'g:/code/rtlgen/rtlgen')
import torch
import torch.nn as nn
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams

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

model = TinyResNet18(num_classes=10)
model.eval()
x = torch.randn(1, 3, 8, 8)

params = NeuralAccelParams(array_size=32, data_width=16, acc_width=32, sram_depth=65536, num_lanes=32)
compiled = compile_model(model, example_input=x, params=params)

# Find STORE instructions and their config addresses
for i, instr in enumerate(compiled.instructions):
    opcode = (instr >> 28) & 0xF
    if opcode == 0x2:  # STORE
        # Find preceding CONFIG func=3 (sram_addr)
        sram_addr = 0
        for j in range(i-1, -1, -1):
            prev = compiled.instructions[j]
            prev_op = (prev >> 28) & 0xF
            prev_func = (prev >> 24) & 0xF
            if prev_op == 0x8 and prev_func == 3:
                sram_addr = prev & 0xFF
                break
        print(f'STORE at instr {i}, sram_addr={sram_addr}')
        # Find tensor with this addr
        for name, t in compiled.graph.tensors.items():
            if t.addr == sram_addr and t.buffer_id in (0, 1, 2):
                print(f'  -> tensor {name}: buf={t.buffer_id} addr={t.addr} shape={t.shape}')

# Check explicit stores
from skills.cpu.npu.compiler.ir import OpType
for op in compiled.graph.ops:
    if op.op_type == OpType.STORE:
        src = op.inputs[0]
        print(f'Explicit STORE: {src.name} buf={src.buffer_id} addr={src.addr}')
