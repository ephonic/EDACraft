"""
GPGPU Warp Scheduler —SIMT thread block scheduling

Maintains per-warp state (PC, active mask, predicate registers) and
implements round-robin scheduling with branch divergence / reconvergence.

Reconvergence uses a per-warp stack:
  - Entry: {pc, active_mask}
  - On divergent branch: push not-taken path, continue with taken path
  - At reconvergence PC: pop stack and resume saved path
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Memory, Array, Const
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common.params import GPGPUParams


class WarpScheduler(Module):
    """Warp scheduler with divergence/reconvergence support."""

    def __init__(self, params: GPGPUParams = None, name: str = "WarpScheduler"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.num_warps = params.num_warps
        self.warp_size = params.warp_size
        self.num_regs = params.num_regs
        self.max_depth = params.max_divergence_depth
        self.pc_width = 16  # supports 64K instructions
        self.stack_ptr_width = max((self.max_depth - 1).bit_length(), 1)
        self.warp_id_width = max((self.num_warps - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Kernel launch interface
        # -----------------------------------------------------------------
        self.launch_valid = Input(1, "launch_valid")
        self.launch_warps = Input(self.warp_id_width, "launch_warps")
        self.launch_pc = Input(self.pc_width, "launch_pc")
        self.kernel_done = Output(1, "kernel_done")

        # -----------------------------------------------------------------
        # Instruction fetch interface
        # -----------------------------------------------------------------
        self.fetch_ready = Input(1, "fetch_ready")
        self.fetch_warp = Output(self.warp_id_width, "fetch_warp")
        self.fetch_pc = Output(self.pc_width, "fetch_pc")
        self.fetch_valid = Output(1, "fetch_valid")

        # -----------------------------------------------------------------
        # Decode / issue interface
        # -----------------------------------------------------------------
        self.issue_ready = Input(1, "issue_ready")  # scoreboard says OK
        self.issue_warp = Output(self.warp_id_width, "issue_warp")
        self.issue_pc = Output(self.pc_width, "issue_pc")
        self.issue_mask = Output(self.warp_size, "issue_mask")
        self.issue_valid = Output(1, "issue_valid")

        # Branch feedback from execution unit
        self.branch_valid = Input(1, "branch_valid")
        self.branch_warp = Input(self.warp_id_width, "branch_warp")
        self.branch_taken_mask = Input(self.warp_size, "branch_taken_mask")
        self.branch_not_taken_mask = Input(self.warp_size, "branch_not_taken_mask")
        self.branch_taken_pc = Input(self.pc_width, "branch_taken_pc")
        self.branch_not_taken_pc = Input(self.pc_width, "branch_not_taken_pc")
        self.branch_reconverge_pc = Input(self.pc_width, "branch_reconverge_pc")

        # Barrier sync interface
        self.barrier_valid = Input(1, "barrier_valid")
        self.barrier_warp = Input(self.warp_id_width, "barrier_warp")

        # Writeback interface (for tracking completion)
        self.wb_valid = Input(1, "wb_valid")
        self.wb_warp = Input(self.warp_id_width, "wb_warp")
        self.wb_mask = Input(self.warp_size, "wb_mask")

        # -----------------------------------------------------------------
        # Per-warp state
        # -----------------------------------------------------------------
        self.warp_pc = [Reg(self.pc_width, f"warp_pc_{i}") for i in range(self.num_warps)]
        self.warp_active = [Reg(self.warp_size, f"warp_active_{i}") for i in range(self.num_warps)]
        self.warp_valid = [Reg(1, f"warp_valid_{i}") for i in range(self.num_warps)]
        self.warp_done = [Reg(1, f"warp_done_{i}") for i in range(self.num_warps)]
        self.barrier_wait = [Reg(1, f"barrier_wait_{i}") for i in range(self.num_warps)]

        # Reconvergence stack per warp
        self.stack_ptr = [Reg(self.stack_ptr_width, f"stack_ptr_{i}") for i in range(self.num_warps)]
        self.stack_pc = [
            [Reg(self.pc_width, f"stack_pc_{i}_{d}") for d in range(self.max_depth)]
            for i in range(self.num_warps)
        ]
        self.stack_mask = [
            [Reg(self.warp_size, f"stack_mask_{i}_{d}") for d in range(self.max_depth)]
            for i in range(self.num_warps)
        ]

        # -----------------------------------------------------------------
        # Round-robin scheduler
        # -----------------------------------------------------------------
        self.rr_ptr = Reg(self.warp_id_width, "rr_ptr")

        # Find next ready warp
        self.next_warp = Wire(self.warp_id_width, "next_warp")
        self.next_valid = Wire(1, "next_valid")

        def _mux_list(items, sel):
            """Mux select from a list of signals."""
            result = items[0]
            for i in range(1, len(items)):
                result = Mux(sel == i, items[i], result)
            return result

        @self.comb
        def _select_warp():
            # Priority encoder: lowest warp ID wins (MVP simplification)
            sel = Const(0, self.warp_id_width)
            found = Const(0, 1)
            for w in range(self.num_warps):
                warp_valid_w = _mux_list(self.warp_valid, w)
                warp_done_w = _mux_list(self.warp_done, w)
                warp_active_w = _mux_list(self.warp_active, w)
                barrier_wait_w = _mux_list(self.barrier_wait, w)
                match = warp_valid_w & ~warp_done_w & (warp_active_w != 0) & ~barrier_wait_w
                sel = Mux(match & ~found, w, sel)
                found = Mux(match & ~found, Const(1, 1), found)
            self.next_warp <<= sel
            self.next_valid <<= found

        # Barrier completion detection
        self.all_at_barrier = Wire(1, "all_at_barrier")

        @self.comb
        def _barrier_detect():
            all_wait = 1
            for i in range(self.num_warps):
                with If(self.warp_valid[i] & ~self.warp_done[i]):
                    all_wait = all_wait & self.barrier_wait[i]
            self.all_at_barrier <<= all_wait

        # -----------------------------------------------------------------
        # Sequential: schedule, branch, launch
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _sched():
            with If(self.rst_n == 0):
                self.rr_ptr <<= 0
                for i in range(self.num_warps):
                    self.warp_valid[i] <<= 0
                    self.warp_done[i] <<= 0
                    self.warp_active[i] <<= 0
                    self.stack_ptr[i] <<= 0
            with Else():
                # --- Barrier release ---
                with If(self.all_at_barrier):
                    for i in range(self.num_warps):
                        self.barrier_wait[i] <<= 0

                # --- Kernel launch ---
                with If(self.launch_valid):
                    for i in range(self.num_warps):
                        with If(i < self.launch_warps):
                            self.warp_valid[i] <<= 1
                            self.warp_done[i] <<= 0
                            self.warp_pc[i] <<= self.launch_pc
                            self.warp_active[i] <<= (1 << self.warp_size) - 1
                            self.stack_ptr[i] <<= 0
                            self.barrier_wait[i] <<= 0
                        with Else():
                            self.warp_valid[i] <<= 0
                            self.barrier_wait[i] <<= 0

                # --- Barrier arrival ---
                with If(self.barrier_valid):
                    for i in range(self.num_warps):
                        with If(self.barrier_warp == i):
                            self.barrier_wait[i] <<= 1

                # --- Normal issue / advance PC ---
                with If(self.issue_ready & self.next_valid & self.fetch_ready):
                    w = self.next_warp
                    self.rr_ptr <<= w
                    # Advance PC (unrolled to avoid Signal indexing)
                    for i in range(self.num_warps):
                        with If(w == i):
                            self.warp_pc[i] <<= self.warp_pc[i] + 1

                # --- Branch divergence handling ---
                with If(self.branch_valid):
                    w = self.branch_warp
                    taken = self.branch_taken_mask
                    not_taken = self.branch_not_taken_mask
                    for i in range(self.num_warps):
                        with If(w == i):
                            sp = self.stack_ptr[i]
                            with If((taken != 0) & (not_taken != 0)):
                                # Divergent: push not-taken, execute taken
                                with If(sp < self.max_depth):
                                    for d in range(self.max_depth):
                                        with If(sp == d):
                                            self.stack_pc[i][d] <<= self.branch_not_taken_pc
                                            self.stack_mask[i][d] <<= not_taken
                                    self.stack_ptr[i] <<= sp + 1
                                self.warp_pc[i] <<= self.branch_taken_pc
                                self.warp_active[i] <<= taken
                            with Else():
                                with If(taken != 0):
                                    self.warp_pc[i] <<= self.branch_taken_pc
                                    self.warp_active[i] <<= taken
                                with Else():
                                    self.warp_pc[i] <<= self.branch_not_taken_pc
                                    self.warp_active[i] <<= not_taken

                # --- Reconvergence check ---
                for i in range(self.num_warps):
                    with If(self.warp_valid[i] & ~self.warp_done[i] &
                            (self.warp_pc[i] == self.branch_reconverge_pc)):
                        sp = self.stack_ptr[i]
                        with If(sp > 0):
                            # Pop stack and resume
                            for d in range(self.max_depth):
                                with If(sp - 1 == d):
                                    self.warp_pc[i] <<= self.stack_pc[i][d]
                                    self.warp_active[i] <<= self.stack_mask[i][d]
                            self.stack_ptr[i] <<= sp - 1
                        with Else():
                            # All paths reconverged, check if warp is done
                            with If(self.warp_active[i] == 0):
                                self.warp_done[i] <<= 1

                # --- Mark warp done on EXIT instruction ---
                # (handled externally via branch_reconverge_pc = 0 with active=0)

        # -----------------------------------------------------------------
        # Output assignments (combinational from current state)
        # -----------------------------------------------------------------
        self.fetch_valid <<= self.next_valid & self.fetch_ready
        self.fetch_warp <<= self.next_warp
        self.fetch_pc <<= _mux_list(self.warp_pc, self.next_warp)

        self.issue_valid <<= self.next_valid & self.issue_ready
        self.issue_warp <<= self.next_warp
        self.issue_pc <<= _mux_list(self.warp_pc, self.next_warp)
        self.issue_mask <<= _mux_list(self.warp_active, self.next_warp)

        # Kernel done when all launched warps are done
        all_done = 1
        for i in range(self.num_warps):
            all_done = all_done & (~self.warp_valid[i] | self.warp_done[i])
        self.kernel_done <<= all_done
