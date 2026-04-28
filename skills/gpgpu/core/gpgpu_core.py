"""
GPGPU Core —?Top-level streaming processor

Integrates warp scheduler, frontend, register file, ALU array, SFU,
tensor core, scoreboard, and memory subsystem into a complete SIMT core.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Memory
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common import isa
from skills.gpgpu.common.params import GPGPUParams
from skills.gpgpu.core.register_file import RegisterFile
from skills.gpgpu.core.alu_array import ALUArray
from skills.gpgpu.core.sfu import SFUArray
from skills.gpgpu.core.tensor_core import TensorCore
from skills.gpgpu.core.warp_scheduler import WarpScheduler
from skills.gpgpu.core.scoreboard import Scoreboard
from skills.gpgpu.core.frontend import Frontend
from skills.gpgpu.core.memory_unit import MemoryCoalescer, L1Cache, SharedMemory


class GPGPUCore(Module):
    """Top-level GPGPU streaming processor."""

    def __init__(self, params: GPGPUParams = None, name: str = "GPGPUCore"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.num_warps = params.num_warps
        self.warp_size = params.warp_size
        self.num_regs = params.num_regs
        self.reg_width = params.reg_width
        self.data_width = params.data_width
        self.addr_width = 32
        self.pc_width = 16
        self.warp_id_width = max((self.num_warps - 1).bit_length(), 1)
        self.reg_addr_width = max((self.num_regs - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Kernel launch interface
        # -----------------------------------------------------------------
        self.launch_valid = Input(1, "launch_valid")
        self.launch_warps = Input(self.warp_id_width, "launch_warps")
        self.launch_pc = Input(self.pc_width, "launch_pc")
        self.kernel_done = Output(1, "kernel_done")
        self.busy = Output(1, "busy")

        # -----------------------------------------------------------------
        # Program loading interface
        # -----------------------------------------------------------------
        self.prog_load_valid = Input(1, "prog_load_valid")
        self.prog_load_addr = Input(self.pc_width, "prog_load_addr")
        self.prog_load_data = Input(64, "prog_load_data")
        self.prog_load_we = Input(1, "prog_load_we")

        # -----------------------------------------------------------------
        # Global memory interface
        # -----------------------------------------------------------------
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_is_store = Output(1, "mem_req_is_store")
        self.mem_req_addr = Output(self.addr_width, "mem_req_addr")
        self.mem_req_data = Output(self.data_width, "mem_req_data")
        self.mem_req_mask = Output(self.data_width // 8, "mem_req_mask")
        self.mem_resp_valid = Input(1, "mem_resp_valid")
        self.mem_resp_data = Input(self.data_width, "mem_resp_data")

        # -----------------------------------------------------------------
        # Instantiate submodules
        # -----------------------------------------------------------------
        self.regfile = RegisterFile(params, name="RegFile")
        self.alu = ALUArray(params, name="ALUArray")
        self.sfu = SFUArray(params, name="SFUArray")
        self.tensor = TensorCore(params, name="TensorCore")
        self.scheduler = WarpScheduler(params, name="WarpSched")
        self.scoreboard = Scoreboard(params, name="Scoreboard")
        self.frontend = Frontend(params, name="Frontend")
        self.coalescer = MemoryCoalescer(params, name="Coalescer")
        self.l1cache = L1Cache(params, name="L1Cache")
        self.smem = SharedMemory(params, name="SharedMem")

        # -----------------------------------------------------------------
        # Connect clocks
        # -----------------------------------------------------------------
        for mod in [self.regfile, self.alu, self.sfu, self.tensor,
                    self.scheduler, self.scoreboard, self.frontend,
                    self.coalescer, self.l1cache, self.smem]:
            mod.clk <<= self.clk
            mod.rst_n <<= self.rst_n

        # -----------------------------------------------------------------
        # Scheduler <-> Frontend
        # -----------------------------------------------------------------
        self.scheduler.launch_valid <<= self.launch_valid
        self.scheduler.launch_warps <<= self.launch_warps
        self.scheduler.launch_pc <<= self.launch_pc
        self.kernel_done <<= self.scheduler.kernel_done

        self.frontend.fetch_valid <<= self.scheduler.fetch_valid
        self.frontend.fetch_warp <<= self.scheduler.fetch_warp
        self.frontend.fetch_pc <<= self.scheduler.fetch_pc
        self.scheduler.fetch_ready <<= self.frontend.fetch_ready

        self.scheduler.issue_ready <<= self.scoreboard.issue_ready
        self.scheduler.issue_warp <<= self.frontend.dec_warp
        self.scheduler.issue_pc <<= self.frontend.dec_pc
        self.scheduler.issue_mask <<= self.frontend.dec_pred_use

        # Barrier sync wiring
        self.scheduler.barrier_valid <<= self.frontend.dec_valid & (self.frontend.dec_opcode == isa.OP_CTRL) & (self.frontend.dec_func == isa.CTRL_SYNC)
        self.scheduler.barrier_warp <<= self.frontend.dec_warp

        # EXIT instruction handling: zero active mask, reconverge at current PC
        self.scheduler.branch_valid <<= self.frontend.dec_valid & (self.frontend.dec_opcode == isa.OP_CTRL) & (self.frontend.dec_func == isa.CTRL_EXIT)
        self.scheduler.branch_warp <<= self.frontend.dec_warp
        self.scheduler.branch_taken_mask <<= 0
        self.scheduler.branch_not_taken_mask <<= 0
        self.scheduler.branch_taken_pc <<= self.frontend.dec_pc
        self.scheduler.branch_not_taken_pc <<= self.frontend.dec_pc
        self.scheduler.branch_reconverge_pc <<= self.frontend.dec_pc

        # -----------------------------------------------------------------
        # Frontend -> Scoreboard / Issue logic
        # -----------------------------------------------------------------
        # Control instructions (NOP/EXIT/SYNC) bypass scoreboard
        self.ctrl_inst = (self.frontend.dec_opcode == isa.OP_CTRL)
        self.scoreboard.issue_valid <<= self.frontend.dec_valid & ~self.ctrl_inst
        self.scoreboard.issue_warp <<= self.frontend.dec_warp
        self.scoreboard.issue_dst <<= self.frontend.dec_dst
        self.scoreboard.issue_src_a <<= self.frontend.dec_src_a
        self.scoreboard.issue_src_b <<= self.frontend.dec_src_b
        self.scoreboard.issue_src_c <<= self.frontend.dec_src_c

        # Writeback to scoreboard (from ALU / SFU / Tensor / Mem)
        self.scoreboard.wb_valid <<= self.alu.out_valid | self.sfu.out_valid | self.tensor.done
        # Simplified: use ALU warp as wb warp (need arbitration in full design)
        self.scoreboard.wb_warp <<= self.frontend.dec_warp
        self.scoreboard.wb_dst <<= self.frontend.dec_dst

        # -----------------------------------------------------------------
        # Register File read (decode stage)
        # -----------------------------------------------------------------
        self.regfile.rd_addr_a <<= self.frontend.dec_src_a
        self.regfile.rd_addr_b <<= self.frontend.dec_src_b

        # -----------------------------------------------------------------
        # Register File writeback (from ALU / SFU / Tensor)
        # -----------------------------------------------------------------
        # Write-back mux: prioritize ALU, then SFU, then Tensor
        self.wb_sel = Wire(2, "wb_sel")
        self.wb_sel <<= Mux(self.alu.out_valid, 0, Mux(self.sfu.out_valid, 1, 2))

        self.regfile.wr_addr <<= Mux(self.wb_sel == 0, self.frontend.dec_dst, 0)
        for i in range(self.warp_size):
            alu_data = self.alu.result[i]
            sfu_data = self.sfu.result[i]
            tensor_data = self.tensor.store_data[i] if i < 16 else 0
            self.regfile.wr_data[i] <<= Mux(self.wb_sel == 0, alu_data,
                                            Mux(self.wb_sel == 1, sfu_data, tensor_data))
            # Write enable gated by predicate mask from scheduler
            alu_wb = (self.wb_sel == 0) & self.alu.out_valid
            sfu_wb = (self.wb_sel == 1) & self.sfu.out_valid
            tensor_wb = (self.wb_sel == 2) & self.tensor.store_valid
            self.regfile.wr_en[i] <<= (alu_wb | sfu_wb | tensor_wb) & self.scheduler.issue_mask[i]

        # -----------------------------------------------------------------
        # ALU connections
        # -----------------------------------------------------------------
        self.alu.valid <<= self.frontend.dec_valid & (self.frontend.dec_unit == isa.UNIT_ALU)
        self.alu.op <<= self.frontend.dec_func
        self.alu.shift_amt <<= self.frontend.dec_imm[4:0]
        for i in range(self.warp_size):
            self.alu.src_a[i] <<= self.regfile.rd_data_a[i]
            self.alu.src_b[i] <<= self.regfile.rd_data_b[i]
            self.alu.src_c[i] <<= 0  # src_c not used in MVP for ALU
        self.alu.pred_mask <<= self.scheduler.issue_mask

        # -----------------------------------------------------------------
        # SFU connections
        # -----------------------------------------------------------------
        self.sfu.valid <<= self.frontend.dec_valid & (self.frontend.dec_unit == isa.UNIT_SFU)
        self.sfu.op <<= self.frontend.dec_func
        for i in range(self.warp_size):
            self.sfu.src[i] <<= self.regfile.rd_data_a[i]

        # -----------------------------------------------------------------
        # Tensor Core connections
        # -----------------------------------------------------------------
        self.tensor.start <<= self.frontend.dec_valid & (self.frontend.dec_unit == isa.UNIT_TENSOR)
        self.tensor.op <<= self.frontend.dec_func

        # Tensor load/store controller (3-phase auto-load: A, B, C)
        self.tensor_cmd = Reg(1, "tensor_cmd")
        self.tensor_phase = Reg(2, "tensor_phase")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _tensor_ctrl():
            with If(self.rst_n == 0):
                self.tensor_cmd <<= 0
                self.tensor_phase <<= 0
            with Else():
                with If(self.frontend.dec_valid & (self.frontend.dec_unit == isa.UNIT_TENSOR)):
                    self.tensor_cmd <<= 1
                    self.tensor_phase <<= 0
                with If(self.tensor_cmd):
                    with If(self.tensor_phase < 3):
                        self.tensor_phase <<= self.tensor_phase + 1
                    with Else():
                        self.tensor_cmd <<= 0

        self.tensor.load_valid <<= self.tensor_cmd
        self.tensor.load_done <<= self.tensor_cmd
        self.tensor.store_ready <<= 1
        for i in range(self.warp_size):
            self.tensor.load_data[i] <<= self.regfile.rd_data_a[i]

        # -----------------------------------------------------------------
        # Memory Coalescer connections
        # -----------------------------------------------------------------
        self.coalescer.req_valid <<= self.frontend.dec_valid & (self.frontend.dec_unit == isa.UNIT_MEM)
        self.coalescer.req_is_store <<= (self.frontend.dec_func == isa.MEM_ST)
        for i in range(self.warp_size):
            self.coalescer.req_addr[i] <<= self.regfile.rd_data_a[i]
            self.coalescer.req_data[i] <<= self.regfile.rd_data_b[i]
        self.coalescer.req_mask <<= self.scheduler.issue_mask

        # -----------------------------------------------------------------
        # L1 Cache connections
        # -----------------------------------------------------------------
        self.l1cache.req_valid <<= self.coalescer.out_valid
        self.l1cache.req_is_store <<= self.coalescer.out_is_store
        self.l1cache.req_addr <<= self.coalescer.out_addr
        # Simplified: only first data word
        self.l1cache.req_data <<= self.coalescer.out_data[0]
        self.l1cache.req_mask <<= self.coalescer.out_mask

        # L1 miss -> global memory
        self.mem_req_valid <<= self.l1cache.miss_valid
        self.mem_req_is_store <<= self.l1cache.req_is_store
        self.mem_req_addr <<= self.l1cache.miss_addr
        self.mem_req_data <<= self.l1cache.req_data
        self.mem_req_mask <<= self.l1cache.req_mask

        self.l1cache.fill_valid <<= self.mem_resp_valid
        self.l1cache.fill_addr <<= self.mem_req_addr
        self.l1cache.fill_data[0] <<= self.mem_resp_data

        # -----------------------------------------------------------------
        # Instruction memory interface (exposed to runtime for simulation)
        # -----------------------------------------------------------------
        self.frontend_imem_req_valid = Output(1, "frontend_imem_req_valid")
        self.frontend_imem_req_addr = Output(self.pc_width, "frontend_imem_req_addr")
        self.frontend_imem_resp_valid = Input(1, "frontend_imem_resp_valid")
        self.frontend_imem_resp_data = Input(64, "frontend_imem_resp_data")

        self.frontend_imem_req_valid <<= self.frontend.imem_req_valid
        self.frontend_imem_req_addr <<= self.frontend.imem_req_addr
        self.frontend.imem_resp_valid <<= self.frontend_imem_resp_valid
        self.frontend.imem_resp_data <<= self.frontend_imem_resp_data

        # -----------------------------------------------------------------
        # Busy signal
        # -----------------------------------------------------------------
        self.busy <<= ~self.kernel_done
