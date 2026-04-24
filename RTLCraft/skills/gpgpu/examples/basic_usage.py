"""
GPGPU Core — Basic Usage Example

Demonstrates:
  1. Instantiate GPGPUCore with custom parameters
  2. Generate Verilog RTL
  3. Run Python simulation on individual units
  4. Configure kernel launch and execute a simple ALU op
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import VerilogEmitter
from rtlgen.sim import Simulator

from skills.gpgpu.common.params import GPGPUParams
from skills.gpgpu.common import isa
from skills.gpgpu.core.gpgpu_core import GPGPUCore
from skills.gpgpu.core.alu_lane import ALULane
from skills.gpgpu.core.register_file import RegisterFile
from skills.gpgpu.core.tensor_core import TensorCore


def example_generate_verilog():
    """Generate synthesizable Verilog for the full GPGPU core."""
    print("=" * 60)
    print("Example 1: Verilog Generation")
    print("=" * 60)

    params = GPGPUParams()
    core = GPGPUCore(params)

    emitter = VerilogEmitter()
    verilog = emitter.emit_design(core)

    print(f"Generated {len(verilog)} characters of Verilog")
    print(f"Top module: {core.name}")
    print(f"Sub-modules: {len(core._submodules)}")

    # Save to file
    out_path = "gpgpu_core_generated.v"
    with open(out_path, "w") as f:
        f.write(verilog)
    print(f"Saved to: {out_path}")
    print()


def example_simulate_alu():
    """Simulate a single ALU lane executing ADD and MUL."""
    print("=" * 60)
    print("Example 2: ALU Lane Simulation")
    print("=" * 60)

    alu = ALULane(data_width=32)
    sim = Simulator(alu)
    sim.reset("rst_n")

    # ADD: 10 + 20 = 30
    sim.poke("valid", 1)
    sim.poke("op", isa.ALU_ADD)
    sim.poke("src_a", 10)
    sim.poke("src_b", 20)
    sim.step()
    print(f"ADD: result = {sim.peek('result')} (expected 30)")

    # MUL: 7 * 6 = 42
    sim.poke("op", isa.ALU_MUL)
    sim.poke("src_a", 7)
    sim.poke("src_b", 6)
    sim.step()
    print(f"MUL: result = {sim.peek('result')} (expected 42)")

    # MIN: min(5, 8) = 5
    sim.poke("op", isa.ALU_MIN)
    sim.poke("src_a", 5)
    sim.poke("src_b", 8)
    sim.step()
    print(f"MIN: result = {sim.peek('result')} (expected 5)")
    print()


def example_simulate_register_file():
    """Simulate register file read/write across multiple lanes."""
    print("=" * 60)
    print("Example 3: Register File Simulation")
    print("=" * 60)

    params = GPGPUParams()
    rf = RegisterFile(params)
    sim = Simulator(rf)
    sim.reset("rst_n")

    # Write 0xDEADBEEF to register 5, lane 0..3
    sim.poke("wr_en", 0x0000000F)  # lanes 0-3
    sim.poke("wr_addr", 5)
    for i in range(4):
        sim.poke(f"wr_data_{i}", 0xDEADBEEF)
    sim.step()

    # Read register 5 on port A
    sim.poke("rd_addr_a", 5)
    sim.step()

    for i in range(4):
        val = sim.peek(f"rd_data_a_{i}")
        print(f"Lane {i} rd_data_a = 0x{val:08x}")
    print()


def example_simulate_tensor_core():
    """Simulate a 4x4x4 matrix multiply-accumulate."""
    print("=" * 60)
    print("Example 4: Tensor Core MMA Simulation")
    print("=" * 60)

    params = GPGPUParams()
    tc = TensorCore(params)
    sim = Simulator(tc)
    sim.reset("rst_n")

    # A = identity matrix
    for i in range(16):
        sim.poke_memory("buf_a", i, 1 if i in [0, 5, 10, 15] else 0)
    # B = all ones
    for i in range(16):
        sim.poke_memory("buf_b", i, 1)
    # C = all zeros
    for i in range(16):
        sim.poke_memory("buf_c", i, 0)

    # Start MMA
    sim.poke("start", 1)
    sim.step()
    sim.poke("start", 0)
    sim.step()

    # D = I @ 1 + 0 => all ones
    print("TensorCore D results:")
    for i in range(4):
        row = [sim.peek_memory("buf_d", i * 4 + j) for j in range(4)]
        print(f"  Row {i}: {row}")
    print()


def example_custom_params():
    """Show how to customize micro-architecture parameters."""
    print("=" * 60)
    print("Example 5: Custom Parameters")
    print("=" * 60)

    params = GPGPUParams(
        warp_size=32,
        num_warps=8,
        num_regs=64,
        data_width=64,
        tensor_dim=8,
        shared_mem_size=32768,
        icache_sets=32,
        l1_sets=32,
    )
    core = GPGPUCore(params)
    vlog = VerilogEmitter().emit_design(core)
    print(f"Custom core: {len(vlog)} chars of Verilog")
    print(f"  warps={params.num_warps}, regs={params.num_regs}, data_width={params.data_width}")
    print()


if __name__ == "__main__":
    example_generate_verilog()
    example_simulate_alu()
    example_simulate_register_file()
    example_simulate_tensor_core()
    example_custom_params()
    print("All examples completed successfully!")
