import sys
sys.path.insert(0, 'g:/code/rtlgen/rtlgen')
import torch
import torch.nn as nn
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams
from collections import Counter

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

opcodes = [(i >> 28) & 0xF for i in compiled.instructions]
counts = Counter(opcodes)
print('Instruction counts:')
for op, cnt in sorted(counts.items()):
    names = {0:'NOP', 1:'LOAD', 2:'STORE', 3:'GEMM', 4:'VEC_ALU', 5:'SFU', 6:'CROSSBAR', 7:'SYNC', 8:'CONFIG', 9:'IM2COL', 0xA:'POOL'}
    print(f'  {names.get(op, f"OP{op}")}: {cnt}')

has_store = any(op == 2 for op in opcodes)
print(f'Has STORE: {has_store}')

# Check liveness for key tensors
from skills.cpu.npu.compiler.ir import OpType
tensor_birth = {}
tensor_death = {}
for idx, op in enumerate(compiled.graph.ops):
    for out in op.outputs:
        if out.name not in tensor_birth:
            tensor_birth[out.name] = idx
    for inp in op.inputs:
        tensor_death[inp.name] = max(tensor_death.get(inp.name, -1), idx)

print('\nKey tensor liveness:')
for name in ['x', 'conv1', 'relu', 'fc']:
    t = compiled.graph.tensors.get(name)
    if t:
        birth = tensor_birth.get(name, -1)
        death = tensor_death.get(name, -1)
        print(f'  {name}: birth={birth} death={death} buf={t.buffer_id} addr={t.addr}')
