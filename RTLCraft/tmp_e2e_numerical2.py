"""Prototype for numerical end-to-end ResNet18 test with base_width=1."""
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
    def __init__(self, num_classes=10, base_width=1):
        super().__init__()
        self.conv1 = nn.Conv2d(3, base_width, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(base_width)
        self.relu = nn.ReLU()
        self.layer1 = self._make_layer(base_width, base_width, 2, stride=1)
        self.layer2 = self._make_layer(base_width, base_width*2, 2, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(base_width*2, num_classes)
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


def _load_program(sim, instructions):
    for addr, instr in enumerate(instructions):
        sim.poke('prog_load_valid', 1)
        sim.poke('prog_load_addr', addr)
        sim.poke('prog_load_data', instr)
        sim.poke('prog_load_we', 1)
        sim.step()
    sim.poke('prog_load_valid', 0)
    sim.poke('prog_load_we', 0)


def main():
    torch.manual_seed(42)
    model = TinyResNet18(num_classes=10, base_width=1)
    model.eval()

    # Set BN to identity
    for m in model.modules():
        if isinstance(m, nn.BatchNorm2d):
            m.weight.data.fill_(1.0)
            m.bias.data.fill_(0.0)
            m.running_mean.fill_(0.0)
            m.running_var.fill_(1.0)

    # Set small integer weights
    for m in model.modules():
        if isinstance(m, (nn.Conv2d, nn.Linear)):
            m.weight.data = torch.randint(-2, 3, m.weight.shape).float()
            if m.bias is not None:
                m.bias.data = torch.randint(-2, 3, m.bias.shape).float()

    x = torch.randint(-2, 3, (1, 3, 8, 8)).float()

    # PyTorch reference
    with torch.no_grad():
        y_ref = model(x)
    print(f"PyTorch reference: {y_ref.numpy().flatten()}")

    # Compile
    params = NeuralAccelParams(array_size=32, data_width=16, acc_width=32, sram_depth=65536, num_lanes=32)
    compiled = compile_model(model, example_input=x, params=params)

    # Check all k_dim <= 32
    from skills.cpu.npu.compiler.ir import GemmOp
    for op in compiled.graph.ops:
        if isinstance(op, GemmOp):
            k = op.attrs.get("k_dim", 0)
            print(f"GEMM {op.name}: k_dim={k}")

    # Re-quantize all weights with scale=1.0
    weight_data_q = {}
    for name, tensor in model.named_parameters():
        qarr, _, _ = quantize_tensor(tensor.detach(), scale=1.0)
        weight_data_q[name] = qarr

    # Quantize input
    x_q, _, _ = quantize_tensor(x, scale=1.0)
    x_q_flat = x_q.flatten()

    # Filter out LOAD instructions
    filtered_instr = []
    for instr in compiled.instructions:
        opcode = (instr >> 28) & 0xF
        if opcode != 0x1:  # skip LOAD
            filtered_instr.append(instr)

    print(f"Instructions: {len(compiled.instructions)} -> {len(filtered_instr)}")

    npu = NeuralAccel(params=params)
    sim = Simulator(npu)
    sim.reset("rst_n")

    # Write input x to SRAM_A
    x_tensor = compiled.graph.tensors.get("x")
    if x_tensor:
        x_mem = {}
        for i, v in enumerate(x_q_flat):
            x_mem[x_tensor.addr + i] = int(v)
        buf_names = ["sram_a_bank0", "sram_a_bank1"]
        _write_jit_mem(sim, buf_names[x_tensor.buffer_id], x_mem)
        print(f"Wrote input x to {buf_names[x_tensor.buffer_id]} addr={x_tensor.addr}")

    # Write weights to SRAM_B
    for name, t in compiled.graph.tensors.items():
        if name in weight_data_q:
            w_q = weight_data_q[name].flatten()
            w_mem = {}
            for i, v in enumerate(w_q):
                w_mem[t.addr + i] = int(v)
            buf_names = ["sram_b_bank0", "sram_b_bank1"]
            _write_jit_mem(sim, buf_names[t.buffer_id], w_mem)
            print(f"Wrote weight {name} to {buf_names[t.buffer_id]} addr={t.addr}")

    _load_program(sim, filtered_instr)
    sim.poke("prog_length", len(filtered_instr))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    completed = False
    max_cycles = 20000
    last_pc = -1
    stall_count = 0
    for i in range(max_cycles):
        sim.poke("m_axi_arready", 1)
        sim.poke("m_axi_awready", 1)
        sim.poke("m_axi_wready", 1)
        sim.poke("m_axi_rvalid", 1)
        sim.poke("m_axi_rdata", 0)
        sim.poke("m_axi_rlast", 1)
        sim.poke("m_axi_bvalid", 1)
        sim.step()
        pc = sim.peek("pc")
        if pc == last_pc:
            stall_count += 1
        else:
            stall_count = 0
        last_pc = pc
        if stall_count > 1000:
            print(f"STALL DETECTED at cycle {i}, pc={pc}, state={sim.peek('state')}")
            break
        if sim.peek("prog_done"):
            completed = True
            print(f"Completed at cycle {i}")
            break

    if not completed:
        print("DID NOT COMPLETE")
        print(f"Final: pc={sim.peek('pc')} state={sim.peek('state')} prog_done={sim.peek('prog_done')}")
        return

    # Read result
    fc_tensor = compiled.graph.tensors.get("fc")
    if fc_tensor:
        buf_names = ["sram_c_bank0", "sram_c_bank1"]
        result = _read_jit_mem(sim, buf_names[fc_tensor.buffer_id], fc_tensor.addr, fc_tensor.numel())
        y_npu = np.array(result).astype(np.int16)
        y_npu = np.where(y_npu > 32767, y_npu - 65536, y_npu)
        print(f"NPU result: {y_npu}")
        print(f"PyTorch ref: {y_ref.numpy().flatten()}")
        print(f"Diff: {y_npu - y_ref.numpy().flatten()}")
        if np.allclose(y_npu, y_ref.numpy().flatten(), atol=2):
            print("PASS: Results match!")
        else:
            print("FAIL: Results do not match")


if __name__ == "__main__":
    main()
