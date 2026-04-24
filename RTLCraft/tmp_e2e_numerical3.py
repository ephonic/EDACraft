"""Prototype for numerical end-to-end ResNet18 test with AXI slave stub."""
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

    for m in model.modules():
        if isinstance(m, nn.BatchNorm2d):
            m.weight.data.fill_(1.0)
            m.bias.data.fill_(0.0)
            m.running_mean.fill_(0.0)
            m.running_var.fill_(1.0)

    for m in model.modules():
        if isinstance(m, (nn.Conv2d, nn.Linear)):
            m.weight.data = torch.randint(-2, 3, m.weight.shape).float()
            if m.bias is not None:
                m.bias.data = torch.randint(-2, 3, m.bias.shape).float()

    x = torch.randint(-2, 3, (1, 3, 8, 8)).float()

    with torch.no_grad():
        y_ref = model(x)
    print(f"PyTorch reference: {y_ref.numpy().flatten()}")

    params = NeuralAccelParams(array_size=32, data_width=16, acc_width=32, sram_depth=65536, num_lanes=32)
    compiled = compile_model(model, example_input=x, params=params)

    weight_data_q = {}
    for name, tensor in model.named_parameters():
        qarr, _, _ = quantize_tensor(tensor.detach(), scale=1.0)
        weight_data_q[name] = qarr

    x_q, _, _ = quantize_tensor(x, scale=1.0)
    x_q_flat = x_q.flatten()

    dram_data = {}
    for name, t in compiled.graph.tensors.items():
        if name in weight_data_q:
            data = weight_data_q[name].flatten()
        elif name == "x":
            data = x_q_flat
        else:
            continue
        addr = t.external_addr
        if addr is None:
            continue
        for i in range(0, len(data), 4):
            beat_words = data[i:i+4]
            beat_val = 0
            for j in range(4):
                w = int(beat_words[j]) if j < len(beat_words) else 0
                if w > 32767:
                    w -= 65536
                beat_val |= (w & 0xFFFF) << (j * 16)
            dram_data[addr + i * 2] = beat_val

    print(f"DRAM data entries: {len(dram_data)}")
    print("x external_addr:", compiled.graph.tensors["x"].external_addr)

    npu = NeuralAccel(params=params)
    sim = Simulator(npu)
    sim.reset("rst_n")

    _load_program(sim, compiled.instructions)
    sim.poke("prog_length", len(compiled.instructions))
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    araddr = None
    arlen = 0
    beat_cnt = 0
    
    completed = False
    max_cycles = 50000
    last_pc = -1
    
    for i in range(max_cycles):
        # AXI Read Address Channel
        if sim.peek("m_axi_arvalid") == 1:
            araddr = sim.peek("m_axi_araddr")
            arlen = sim.peek("m_axi_arlen")
            beat_cnt = 0
            sim.poke("m_axi_arready", 1)
        else:
            sim.poke("m_axi_arready", 0)
        
        # AXI Read Data Channel
        rready = sim.peek("m_axi_rready")
        if araddr is not None and beat_cnt <= arlen:
            current_addr = araddr + beat_cnt * 8
            beat_base = (current_addr // 8) * 8
            rdata = dram_data.get(beat_base, 0)
            sim.poke("m_axi_rvalid", 1)
            sim.poke("m_axi_rdata", int(rdata) & 0xFFFFFFFFFFFFFFFF)
            sim.poke("m_axi_rlast", 1 if beat_cnt == arlen else 0)
            if rready == 1:
                beat_cnt += 1
        else:
            sim.poke("m_axi_rvalid", 0)
            sim.poke("m_axi_rdata", 0)
            sim.poke("m_axi_rlast", 0)
            if beat_cnt > arlen:
                araddr = None
        
        sim.poke("m_axi_awready", 1)
        sim.poke("m_axi_wready", 1)
        sim.poke("m_axi_bvalid", 1)
        sim.poke("m_axi_bresp", 0)
        sim.poke("m_axi_rresp", 0)
        
        sim.step()
        
        pc = sim.peek("pc")
        
        if i % 2000 == 0 and i > 0:
            print(f"Cycle {i}: pc={pc} state={sim.peek('state')} dma_state={sim.peek('dma_state')} im2col_state={sim.peek('im2col_state')}")
        
        if sim.peek("prog_done"):
            completed = True
            print(f"Completed at cycle {i}")
            break
    
    if not completed:
        print(f"Did not complete within {max_cycles} cycles")
        print(f"Final: pc={sim.peek('pc')} state={sim.peek('state')} prog_done={sim.peek('prog_done')}")
        return

    # Read result from SRAM_C
    fc_tensor = compiled.graph.tensors.get("fc")
    if fc_tensor:
        buf_names = ["sram_c_bank0", "sram_c_bank1"]
        idx = sim._jit.mem_idx[buf_names[fc_tensor.buffer_id]]
        mem = sim._jit.memories[idx]
        width = sim._jit.mem_widths[idx]
        mask = (1 << width) - 1
        result = []
        for i in range(fc_tensor.numel()):
            val = mem[fc_tensor.addr + i] & mask
            if val > 32767:
                val -= 65536
            result.append(val)
        y_npu = np.array(result)
        print(f"NPU result: {y_npu}")
        print(f"PyTorch ref: {y_ref.numpy().flatten()}")
        print(f"Diff: {y_npu - y_ref.numpy().flatten()}")
        if np.allclose(y_npu, y_ref.numpy().flatten(), atol=2):
            print("PASS: Results match!")
        else:
            print("FAIL: Results do not match")


if __name__ == "__main__":
    main()
