"""
skills.gpgpu.models — GPGPU Behavioral Models

SIMT (Single Instruction Multiple Thread) execution model,
warp/thread state management, and GPGPU behavioral model container.
Moved from rtlgen.processor_models to be domain-local to the GPGPU skill.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# =====================================================================
# Thread / Warp / GPU State
# =====================================================================

@dataclass
class GPUThread:
    """Single SIMT thread state."""
    thread_id: int        # Global thread ID
    block_id: int         # Thread block ID
    lane_id: int          # Lane index within warp
    pc: int = 0
    regs: Dict[str, int] = field(default_factory=dict)
    active: bool = True
    done: bool = False


@dataclass
class GPUWarp:
    """A warp (32 threads)."""
    warp_id: int
    threads: List[GPUThread] = field(default_factory=list)
    active_mask: int = (1 << 32) - 1  # 32-bit bitmask

    @property
    def active_count(self) -> int:
        return bin(self.active_mask).count('1')


@dataclass
class GPUState:
    """GPGPU global state."""
    grid_dim: Tuple[int, int, int] = (1, 1, 1)
    block_dim: Tuple[int, int, int] = (1, 1, 1)
    warps: List[GPUWarp] = field(default_factory=list)

    global_mem: Dict[int, int] = field(default_factory=dict)
    shared_mem: Dict[int, Dict[int, int]] = field(default_factory=dict)

    active_warps: List[int] = field(default_factory=list)
    cycle_count: int = 0

    barrier_count: Dict[int, int] = field(default_factory=dict)
    barrier_target: Dict[int, int] = field(default_factory=dict)

    def total_threads(self) -> int:
        gx, gy, gz = self.grid_dim
        bx, by, bz = self.block_dim
        return gx * gy * gz * bx * by * bz

    def total_blocks(self) -> int:
        gx, gy, gz = self.grid_dim
        return gx * gy * gz

    def threads_per_block(self) -> int:
        bx, by, bz = self.block_dim
        return bx * by * bz


# =====================================================================
# GPGPU Behavioral Model — SIMT Execution
# =====================================================================

class GPGPUModel:
    """GPGPU behavioral model.

    Supports SIMT execution with:
    - Thread block/grid hierarchy
    - Warp-level scheduling (32 threads/warp)
    - Branch divergence
    - Shared memory and barrier sync
    - Global memory read/write

    Usage:
        gpu = GPGPUModel()
        gpu.configure(grid_dim=(4,1,1), block_dim=(32,1,1))
        gpu.load_kernel(vector_add_kernel)
        gpu.set_global_mem(0, input_data)
        gpu.run(max_cycles=1000)
        result = gpu.get_global_mem(0, len(output))
    """

    WARP_SIZE = 32

    def __init__(self, name: str = "GPGPU"):
        self.name = name
        self.state = GPUState()
        self._kernel: Optional[Callable] = None
        self._kernel_code: Optional[List[dict]] = None

    def configure(
        self,
        grid_dim: Tuple[int, int, int] = (1, 1, 1),
        block_dim: Tuple[int, int, int] = (1, 1, 1),
        num_warps: Optional[int] = None,
    ):
        self.state.grid_dim = grid_dim
        self.state.block_dim = block_dim
        self._init_warps()

    def _init_warps(self):
        self.state.warps.clear()
        self.state.active_warps.clear()

        total_threads = self.state.total_threads()
        tpb = self.state.threads_per_block()
        num_warps = (tpb + self.WARP_SIZE - 1) // self.WARP_SIZE

        warp_id = 0
        for block_id in range(self.state.total_blocks()):
            for warp_in_block in range(num_warps):
                threads = []
                active_mask = 0
                base_tid = block_id * tpb + warp_in_block * self.WARP_SIZE

                for lane in range(self.WARP_SIZE):
                    tid = base_tid + lane
                    if tid < total_threads:
                        t = GPUThread(
                            thread_id=tid, block_id=block_id, lane_id=lane,
                        )
                        threads.append(t)
                        active_mask |= (1 << lane)

                warp = GPUWarp(warp_id=warp_id, threads=threads, active_mask=active_mask)
                self.state.warps.append(warp)
                if warp.active_count > 0:
                    self.state.active_warps.append(warp_id)
                warp_id += 1

            self.state.shared_mem[block_id] = {}

    def load_kernel(self, kernel_func: Callable):
        """Load Python kernel function.

        kernel_func signature:
            (thread_id, block_id, lane_id, regs, global_mem, shared_mem) -> None
        """
        self._kernel = kernel_func

    def load_kernel_instructions(self, instructions: List[dict]):
        """Load compiled instruction list.

        Each instruction is a dict with:
            op: str — "add", "load", "store", "mul", "br", "sync", "barrier", "exit"
            dst, src1, src2, addr, target, mask as needed
        """
        self._kernel_code = instructions

    def set_global_mem(self, base_addr: int, data: List[int]):
        for i, val in enumerate(data):
            self.state.global_mem[base_addr + i] = val

    def get_global_mem(self, base_addr: int, count: int) -> List[int]:
        return [self.state.global_mem.get(base_addr + i, 0) for i in range(count)]

    def set_shared_mem(self, block_id: int, addr: int, val: int):
        if block_id not in self.state.shared_mem:
            self.state.shared_mem[block_id] = {}
        self.state.shared_mem[block_id][addr] = val

    def get_shared_mem(self, block_id: int, addr: int) -> int:
        return self.state.shared_mem.get(block_id, {}).get(addr, 0)

    def run(self, max_cycles: int = 100000):
        for _ in range(max_cycles):
            if not self.state.active_warps:
                break
            self._step()

    def _step(self):
        if not self.state.active_warps:
            return

        warp_id = self.state.active_warps.pop(0)
        if warp_id >= len(self.state.warps):
            return

        warp = self.state.warps[warp_id]
        if warp.active_count == 0:
            return

        self.state.cycle_count += 1

        if self._kernel_code is not None:
            self._execute_warp_instructions(warp)
        elif self._kernel is not None:
            self._execute_kernel_on_warp(warp)

        if warp.active_count > 0:
            self.state.active_warps.append(warp_id)

    def _execute_warp_instructions(self, warp: GPUWarp):
        kernel_code = self._kernel_code or []
        pcs = [t.pc for t in warp.threads if t.active and not t.done]
        if not pcs:
            return

        current_pc = pcs[0]
        if current_pc >= len(kernel_code):
            for t in warp.threads:
                if t.active:
                    t.done = True
                    t.active = False
                    warp.active_mask &= ~(1 << t.lane_id)
            return

        instr = kernel_code[current_pc]

        for t in warp.threads:
            if not t.active or t.done or t.pc != current_pc:
                continue
            self._exec_instruction(t, instr)

    def _exec_instruction(self, thread: GPUThread, instr: dict):
        op = instr.get("op", "nop")
        regs = thread.regs

        if op == "add":
            dst = instr.get("dst", "r0")
            s1 = regs.get(instr.get("src1", "r0"), 0)
            s2 = regs.get(instr.get("src2", "r0"), 0)
            regs[dst] = s1 + s2
        elif op == "mul":
            dst = instr.get("dst", "r0")
            s1 = regs.get(instr.get("src1", "r0"), 0)
            s2 = regs.get(instr.get("src2", "r0"), 0)
            regs[dst] = s1 * s2
        elif op == "sub":
            dst = instr.get("dst", "r0")
            s1 = regs.get(instr.get("src1", "r0"), 0)
            s2 = regs.get(instr.get("src2", "r0"), 0)
            regs[dst] = s1 - s2
        elif op == "and":
            regs[instr.get("dst", "r0")] = regs.get(instr.get("src1", "r0"), 0) & regs.get(instr.get("src2", "r0"), 0)
        elif op == "or":
            regs[instr.get("dst", "r0")] = regs.get(instr.get("src1", "r0"), 0) | regs.get(instr.get("src2", "r0"), 0)
        elif op == "xor":
            regs[instr.get("dst", "r0")] = regs.get(instr.get("src1", "r0"), 0) ^ regs.get(instr.get("src2", "r0"), 0)
        elif op == "mov":
            regs[instr.get("dst", "r0")] = instr.get("imm", 0)
        elif op == "load":
            dst = instr.get("dst", "r0")
            addr = regs.get(instr.get("addr", "r0"), 0) + instr.get("offset", 0)
            thread.regs[dst] = self.state.global_mem.get(addr, 0)
        elif op == "load_shared":
            dst = instr.get("dst", "r0")
            addr = regs.get(instr.get("addr", "r0"), 0)
            thread.regs[dst] = self.get_shared_mem(thread.block_id, addr)
        elif op == "store":
            addr = regs.get(instr.get("addr", "r0"), 0) + instr.get("offset", 0)
            val = regs.get(instr.get("src1", "r0"), 0)
            self.state.global_mem[addr] = val
        elif op == "store_shared":
            addr = regs.get(instr.get("addr", "r0"), 0)
            val = regs.get(instr.get("src1", "r0"), 0)
            self.set_shared_mem(thread.block_id, addr, val)
        elif op in ("barrier", "sync"):
            self._handle_barrier(thread)
        elif op == "br":
            cond = regs.get(instr.get("cond", "r0"), 0)
            target = instr.get("target", thread.pc + 1)
            if cond:
                thread.pc = target
                return
        elif op == "exit":
            thread.done = True
            thread.active = False

        thread.pc += 1

    def _handle_barrier(self, thread: GPUThread):
        bid = thread.block_id
        tpb = self.state.threads_per_block()
        if bid not in self.state.barrier_count:
            self.state.barrier_count[bid] = 0
        self.state.barrier_count[bid] += 1
        if self.state.barrier_count[bid] >= tpb:
            self.state.barrier_count[bid] = 0

    def _execute_kernel_on_warp(self, warp: GPUWarp):
        if self._kernel is None:
            return
        for t in warp.threads:
            if not t.active or t.done:
                continue
            try:
                self._kernel(
                    t.thread_id, t.block_id, t.lane_id,
                    t.regs, self.state.global_mem,
                    self.state.shared_mem.get(t.block_id, {}),
                )
                t.done = True
                t.active = False
                warp.active_mask &= ~(1 << t.lane_id)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_threads": self.state.total_threads(),
            "total_blocks": self.state.total_blocks(),
            "threads_per_block": self.state.threads_per_block(),
            "total_warps": len(self.state.warps),
            "active_warps": len(self.state.active_warps),
            "cycle_count": self.state.cycle_count,
        }
