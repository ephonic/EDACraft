"""
GPGPU Runtime / Driver

Python-based simulation runtime that:
  - Manages device memory (bump allocator)
  - Loads assembled kernels into instruction memory
  - Launches kernels with configurable warp counts
  - Runs rtlgen Simulator until completion
  - Provides memory copy (host <-> device)
  - Allows peek/poke of registers and device memory
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import List, Dict, Optional, Union

from rtlgen.sim import Simulator
from skills.gpgpu.common.params import GPGPUParams
from skills.gpgpu.core.gpgpu_core import GPGPUCore


class GPGPURuntime:
    """Simulation runtime for the GPGPU core."""

    def __init__(self, params: GPGPUParams = None):
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.core = GPGPUCore(params)
        self.sim = Simulator(self.core)

        # Device memory: simple bump allocator
        self._mem: Dict[int, int] = {}
        self._next_addr = 0x1000
        self._alloc_map: Dict[int, int] = {}  # addr -> size

        # Instruction memory
        self._imem: Dict[int, int] = {}

        # Find child simulators by name for direct access
        self._child_sims: Dict[str, Simulator] = {}
        for name, child, _ in self.sim._subsim_info:
            # Disable JIT for frontend to work around port-map sync issues
            if name == 'frontend':
                child._jit = None
            self._child_sims[name] = child

        # Reset device
        self.reset()

    def reset(self):
        """Reset the GPGPU device."""
        self.sim.reset("rst_n")
        self.sim.step()  # sync reset release to children
        self._mem.clear()
        self._next_addr = 0x1000
        self._alloc_map.clear()

    # -----------------------------------------------------------------
    # Memory management
    # -----------------------------------------------------------------
    def malloc(self, size: int, align: int = 4) -> int:
        """Allocate device memory. Returns device address."""
        addr = (self._next_addr + align - 1) // align * align
        self._alloc_map[addr] = size
        self._next_addr = addr + size
        return addr

    def free(self, addr: int):
        """Free device memory. (Simplified: no coalescing)"""
        if addr in self._alloc_map:
            del self._alloc_map[addr]

    def poke_mem(self, addr: int, value: int):
        """Write a word to device memory."""
        self._mem[addr] = value & 0xFFFFFFFF

    def peek_mem(self, addr: int) -> int:
        """Read a word from device memory."""
        return self._mem.get(addr, 0)

    def memcpy_h2d(self, device_addr: int, host_data: List[int]):
        """Copy host data (list of ints) to device memory."""
        for i, val in enumerate(host_data):
            self._mem[device_addr + i * 4] = val & 0xFFFFFFFF

    def memcpy_d2h(self, host_buf: List[int], device_addr: int, size: int):
        """Copy device memory to host list. size in bytes."""
        words = size // 4
        for i in range(words):
            host_buf[i] = self._mem.get(device_addr + i * 4, 0)

    # -----------------------------------------------------------------
    # Program loading
    # -----------------------------------------------------------------
    def load_program(self, code: List[int], base_addr: int = 0):
        """Load machine code into instruction memory."""
        for i, word in enumerate(code):
            addr = base_addr + i
            self._imem[addr] = word & 0xFFFFFFFFFFFFFFFF

    def _step_with_imem(self):
        """Step simulation, responding to frontend IMEM requests."""
        if self.sim.peek("frontend_imem_req_valid"):
            addr = self.sim.peek("frontend_imem_req_addr")
            data = self._imem.get(int(addr), 0)
            self.sim.poke("frontend_imem_resp_valid", 1)
            self.sim.poke("frontend_imem_resp_data", data)
        else:
            self.sim.poke("frontend_imem_resp_valid", 0)
            self.sim.poke("frontend_imem_resp_data", 0)
        self.sim.step()

    # -----------------------------------------------------------------
    # Kernel launch
    # -----------------------------------------------------------------
    def launch(self, kernel_pc: int, num_warps: int,
               args: Optional[Dict[int, int]] = None,
               max_cycles: int = 10000) -> int:
        """Launch a kernel and run until completion.

        Args:
            kernel_pc: Program counter of kernel entry point
            num_warps: Number of warps to launch
            args: Dict mapping register number -> initial value for all warps
            max_cycles: Simulation cycle limit (safety)

        Returns:
            Number of cycles executed
        """
        # Initialize argument registers if provided
        if args:
            self._init_regs(args, num_warps)

        # Launch kernel
        self.sim.poke("launch_valid", 1)
        self.sim.poke("launch_warps", num_warps)
        self.sim.poke("launch_pc", kernel_pc)
        self._step_with_imem()
        self.sim.poke("launch_valid", 0)

        # Run until kernel_done or max_cycles
        cycles = 0
        while cycles < max_cycles:
            self._step_with_imem()
            cycles += 1
            if self.sim.peek("kernel_done") == 1:
                break

        return cycles

    def _init_regs(self, args: Dict[int, int], num_warps: int):
        """Initialize argument registers across all lanes and warps."""
        # Use the RegisterFile child simulator directly
        rf = self._child_sims.get("regfile")
        if rf is None:
            return

        for reg, val in args.items():
            for lane in range(self.params.warp_size):
                # Write enable for this lane
                rf.poke("wr_en", 1 << lane)
                rf.poke("wr_addr", reg)
                rf.poke(f"wr_data_{lane}", val & 0xFFFFFFFF)
                rf.step()
        rf.poke("wr_en", 0)

    # -----------------------------------------------------------------
    # Register / state inspection
    # -----------------------------------------------------------------
    def peek_reg(self, warp: int, lane: int, reg: int) -> int:
        """Read a register value. (warp is ignored in MVP; RF is flat)"""
        rf = self._child_sims.get("regfile")
        if rf is None:
            return 0
        rf.poke("rd_addr_a", reg)
        rf.step()
        return rf.peek(f"rd_data_a_{lane}")

    def step(self, cycles: int = 1):
        """Advance simulation by N cycles."""
        for _ in range(cycles):
            self._step_with_imem()

    def is_done(self) -> bool:
        """Check if kernel has completed."""
        return self.sim.peek("kernel_done") == 1

    def get_cycle_count(self) -> int:
        """Return current simulation cycle count."""
        return self.sim._cycle_count
