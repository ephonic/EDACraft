"""
ResNet18-like NPU Compilation and Simulation Demo

This example demonstrates compiling a CNN with Conv2d layers,
residual connections, and batch normalization to NPU instructions,
then running cycle-accurate simulation.

Because the current MemoryPlanner allocates all tensors statically
without liveness-based reuse, a full ResNet18 with 224x224 input
requires more SRAM than the target 8192-word default.  We use a
reduced-width / reduced-resolution variant for demonstration.

Hardware params: ARRAY_SIZE=32, SRAM_DEPTH=65536, NUM_LANES=32
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import torch
import torch.nn as nn
from skills.cpu.npu.compiler import compile_model
from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.core import NeuralAccel
from rtlgen.sim import Simulator


class MiniResNetBlock(nn.Module):
    """A single ResNet block with two Conv2d + BN + ReLU branches."""
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


class MicroResNet(nn.Module):
    """Tiny ResNet-like topology that fits in 64K-word SRAM for demo."""
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.relu = nn.ReLU()

        # Two residual layers
        self.layer1 = self._make_layer(8, 8, 2, stride=1)
        self.layer2 = self._make_layer(8, 16, 2, stride=2)

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, num_classes)

    def _make_layer(self, in_ch, out_ch, num_blocks, stride):
        layers = [MiniResNetBlock(in_ch, out_ch, stride)]
        for _ in range(1, num_blocks):
            layers.append(MiniResNetBlock(out_ch, out_ch, stride=1))
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


def main():
    model = MicroResNet(num_classes=10)
    model.eval()

    # Small input to fit in SRAM without liveness-based memory reuse
    x = torch.randn(1, 3, 8, 8)

    # Reference PyTorch output
    with torch.no_grad():
        y_ref = model(x)
    print(f"PyTorch output shape: {y_ref.shape}")
    print(f"PyTorch output (first 5): {y_ref[0, :5].tolist()}")

    # Compile to NPU
    params = NeuralAccelParams(
        array_size=32,
        data_width=16,
        acc_width=32,
        sram_depth=65536,
        num_lanes=32,
    )
    compiled = compile_model(model, example_input=x, params=params)
    print(f"\nCompiled program length: {compiled.get_program_length()} instructions")
    print(f"Weight tensors: {len(compiled.weight_data)}")

    # Run simulation
    npu = NeuralAccel(params=params)
    sim = Simulator(npu)
    sim.reset("rst_n")

    # Load program into instruction memory
    for addr, instr in compiled.get_program_load_sequence():
        sim.poke("prog_load_valid", 1)
        sim.poke("prog_load_addr", addr)
        sim.poke("prog_load_data", instr)
        sim.poke("prog_load_we", 1)
        sim.step()
    sim.poke("prog_load_valid", 0)
    sim.poke("prog_load_we", 0)

    sim.poke("prog_length", compiled.get_program_length())
    sim.poke("run", 1)
    sim.step()
    sim.poke("run", 0)

    max_cycles = 50000
    completed = False
    for i in range(max_cycles):
        # Drive AXI slave interface (always ready)
        sim.poke("m_axi_arready", 1)
        sim.poke("m_axi_awready", 1)
        sim.poke("m_axi_wready", 1)
        sim.poke("m_axi_rvalid", 1)
        sim.poke("m_axi_rlast", 1)
        sim.poke("m_axi_bvalid", 1)
        sim.step()

        state = sim.peek("state")
        pc = sim.peek("pc")
        if state == 0 and pc >= compiled.get_program_length():
            print(f"\nNPU simulation completed at cycle {i + 1}")
            completed = True
            break

    if not completed:
        print(f"\nNPU simulation TIMEOUT after {max_cycles} cycles")
        print(f"Final state={state} pc={pc}")

    # Print first few ASM instructions for inspection
    print("\nFirst 10 instructions:")
    for line in compiled.to_asm().split("\n")[:10]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
