"""
NeuralAccel NPU Top-Level Module

Integrates instruction decode, compute units (systolic array, vector ALU, SFU),
SRAM buffers, crossbar data movement, and AXI4 DMA into a complete NPU accelerator.

Execution model: sequential instruction fetch from on-chip instruction memory.
  IDLE → (run) → DECODE → DISPATCH → WAIT → DONE → (next instr or IDLE)

External interfaces:
  - Program load (write instructions into on-chip instruction memory)
  - Program control (run / prog_length / prog_done)
  - AXI4 master (for external DRAM access via DMA)
  - Status: busy, done, interrupt
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Memory
from rtlgen.logic import If, Else, Mux

from skills.cpu.npu.common.npu_params import NeuralAccelParams
from skills.cpu.npu.frontend.instruction_decode import (
    InstructionDecode, OP_NOP, OP_GEMM, OP_VEC_ALU, OP_SFU, OP_CROSSBAR, OP_SYNC,
    OP_LOAD, OP_STORE, OP_CONFIG, OP_IM2COL, OP_POOL,
)
from skills.cpu.npu.memory.ping_pong_sram import PingPongSRAM
from skills.cpu.npu.memory.scratchpad import Scratchpad
from skills.cpu.npu.memory.axi_dma import AXI4DMA
from skills.cpu.npu.memory.inst_sram import InstructionMemory
from skills.cpu.npu.compute.systolic_array import SystolicArray
from skills.cpu.npu.compute.systolic_adapter import SystolicDataAdapter
from skills.cpu.npu.compute.vector_alu import VectorALU
from skills.cpu.npu.compute.sfu import SFU
from skills.cpu.npu.compute.im2col import Im2Col
from skills.cpu.npu.compute.pool_unit import PoolEngine
from skills.cpu.npu.datapath.crossbar import Crossbar


# Controller FSM states
ST_IDLE = 0
ST_FETCH = 1
ST_ISSUE = 2

# VPU FSM states
VPU_IDLE = 0
VPU_READ = 1
VPU_COMPUTE = 2
VPU_WRITE = 3
VPU_DONE = 4


class NeuralAccel(Module):
    """Top-level NPU accelerator with AXI4 DMA and instruction memory."""

    def __init__(self, params: NeuralAccelParams = None, inst_depth: int = 1024, name: str = "NeuralAccel"):
        super().__init__(name)
        if params is None:
            params = NeuralAccelParams()
        self.params = params
        self.inst_depth = inst_depth
        self.inst_addr_width = max((inst_depth - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # =====================================================================
        # Program Control Interface
        # =====================================================================
        # Program loading
        self.prog_load_valid = Input(1, "prog_load_valid")
        self.prog_load_addr = Input(self.inst_addr_width, "prog_load_addr")
        self.prog_load_data = Input(32, "prog_load_data")
        self.prog_load_we = Input(1, "prog_load_we")

        # Execution control
        self.run = Input(1, "run")
        self.prog_length = Input(self.inst_addr_width, "prog_length")
        self.prog_done = Output(1, "prog_done")

        # Status
        self.busy = Output(1, "busy")
        self.done = Output(1, "done")
        self.interrupt = Output(1, "interrupt")

        # =====================================================================
        # AXI4 Master Interface (to external DRAM)
        # =====================================================================
        # Read Address
        self.m_axi_arid = Output(4, "m_axi_arid")
        self.m_axi_araddr = Output(32, "m_axi_araddr")
        self.m_axi_arlen = Output(8, "m_axi_arlen")
        self.m_axi_arsize = Output(3, "m_axi_arsize")
        self.m_axi_arburst = Output(2, "m_axi_arburst")
        self.m_axi_arvalid = Output(1, "m_axi_arvalid")
        self.m_axi_arready = Input(1, "m_axi_arready")
        # Read Data
        self.m_axi_rid = Input(4, "m_axi_rid")
        self.m_axi_rdata = Input(64, "m_axi_rdata")
        self.m_axi_rresp = Input(2, "m_axi_rresp")
        self.m_axi_rlast = Input(1, "m_axi_rlast")
        self.m_axi_rvalid = Input(1, "m_axi_rvalid")
        self.m_axi_rready = Output(1, "m_axi_rready")
        # Write Address
        self.m_axi_awid = Output(4, "m_axi_awid")
        self.m_axi_awaddr = Output(32, "m_axi_awaddr")
        self.m_axi_awlen = Output(8, "m_axi_awlen")
        self.m_axi_awsize = Output(3, "m_axi_awsize")
        self.m_axi_awburst = Output(2, "m_axi_awburst")
        self.m_axi_awvalid = Output(1, "m_axi_awvalid")
        self.m_axi_awready = Input(1, "m_axi_awready")
        # Write Data
        self.m_axi_wdata = Output(64, "m_axi_wdata")
        self.m_axi_wstrb = Output(8, "m_axi_wstrb")
        self.m_axi_wlast = Output(1, "m_axi_wlast")
        self.m_axi_wvalid = Output(1, "m_axi_wvalid")
        self.m_axi_wready = Input(1, "m_axi_wready")
        # Write Response
        self.m_axi_bid = Input(4, "m_axi_bid")
        self.m_axi_bresp = Input(2, "m_axi_bresp")
        self.m_axi_bvalid = Input(1, "m_axi_bvalid")
        self.m_axi_bready = Output(1, "m_axi_bready")

        # =====================================================================
        # Submodules
        # =====================================================================
        self.decode = InstructionDecode(name="InstrDecode")
        self.inst_mem = InstructionMemory(inst_depth, name="InstMem")
        self.sram_a = PingPongSRAM(params.DATA_WIDTH, params.SRAM_DEPTH, name="SRAM_A")
        self.sram_b = PingPongSRAM(params.DATA_WIDTH, params.SRAM_DEPTH, name="SRAM_B")
        self.sram_c = PingPongSRAM(params.DATA_WIDTH, params.SRAM_DEPTH, name="SRAM_C")
        self.scratch = Scratchpad(params.DATA_WIDTH, params.SRAM_DEPTH, name="Scratchpad")
        self.systolic = SystolicArray(params.ARRAY_SIZE, params.DATA_WIDTH, params.ACC_WIDTH, name="SystolicArray")
        self.systolic_adapter = SystolicDataAdapter(
            params.ARRAY_SIZE, params.DATA_WIDTH, params.ACC_WIDTH, params.ADDR_WIDTH, name="SystolicAdapter"
        )
        self.v_alu = VectorALU(params.NUM_LANES, params.DATA_WIDTH, name="VectorALU")
        self.sfu = SFU(params.NUM_LANES, params.DATA_WIDTH, name="SFU")
        self.im2col = Im2Col(params.DATA_WIDTH, params.ADDR_WIDTH, params.ARRAY_SIZE, name="Im2Col")
        self.pool = PoolEngine(params.DATA_WIDTH, params.ADDR_WIDTH, name="PoolEngine")
        self.crossbar = Crossbar(params.NUM_BUFFERS, params.DATA_WIDTH, params.ADDR_WIDTH, name="Crossbar")
        self.dma = AXI4DMA(
            data_width=params.DATA_WIDTH,
            axi_data_width=64,
            addr_width=32,
            sram_addr_width=params.ADDR_WIDTH,
            id_width=4,
            name="AXI4DMA",
        )

        # =====================================================================
        # Clock / Reset Distribution
        # =====================================================================
        for mod in [self.decode, self.inst_mem, self.sram_a, self.sram_b, self.sram_c,
                    self.scratch, self.systolic, self.systolic_adapter, self.v_alu, self.sfu, self.im2col, self.pool, self.crossbar, self.dma]:
            mod.clk <<= self.clk
            mod.rst_n <<= self.rst_n

        # =====================================================================
        # Instruction Memory Connections
        # =====================================================================
        self.inst_mem.load_valid <<= self.prog_load_valid
        self.inst_mem.load_addr <<= self.prog_load_addr
        self.inst_mem.load_data <<= self.prog_load_data
        self.inst_mem.load_we <<= self.prog_load_we

        # =====================================================================
        # Program Counter & Execution Control
        # =====================================================================
        self.pc = Reg(self.inst_addr_width, "pc")
        self.run_r = Reg(1, "run_r")
        self.run_pulse = Wire(1, "run_pulse")
        self.run_pulse <<= self.run & ~self.run_r

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _run_edge():
            with If(self.rst_n == 0):
                self.run_r <<= 0
            with Else():
                self.run_r <<= self.run

        # Instruction fetch from memory (combinational)
        self.inst_mem.fetch_addr <<= self.pc
        self.fetched_instr = Wire(32, "fetched_instr")
        self.fetched_valid = Wire(1, "fetched_valid")
        self.fetched_instr <<= self.inst_mem.fetch_data
        self.fetched_valid <<= self.inst_mem.fetch_valid

        # =====================================================================
        # DMA Configuration Registers
        # =====================================================================
        self.dma_ext_addr = Reg(32, "dma_ext_addr")
        self.dma_len = Reg(16, "dma_len")
        self.dma_sram_addr = Reg(params.ADDR_WIDTH, "dma_sram_addr")
        self.dma_target = Reg(2, "dma_target")  # 0=A, 1=B, 2=C, 3=Scratch

        # =====================================================================
        # Im2Col Configuration Registers
        # =====================================================================
        self.im2col_kh = Reg(4, "im2col_kh")
        self.im2col_kw = Reg(4, "im2col_kw")
        self.im2col_stride_h = Reg(4, "im2col_stride_h")
        self.im2col_stride_w = Reg(4, "im2col_stride_w")
        self.im2col_pad_h = Reg(4, "im2col_pad_h")
        self.im2col_pad_w = Reg(4, "im2col_pad_w")
        self.im2col_in_h = Reg(16, "im2col_in_h")
        self.im2col_in_w = Reg(16, "im2col_in_w")
        self.im2col_in_c = Reg(16, "im2col_in_c")
        self.im2col_out_h = Reg(16, "im2col_out_h")
        self.im2col_out_w = Reg(16, "im2col_out_w")
        self.im2col_src_addr = Reg(params.ADDR_WIDTH, "im2col_src_addr")
        self.im2col_dst_addr = Reg(params.ADDR_WIDTH, "im2col_dst_addr")
        self.im2col_src_target = Reg(2, "im2col_src_target")  # 0=A, 1=B, 2=C, 3=Scratch
        self.im2col_dst_target = Reg(2, "im2col_dst_target")

        # Full 16-bit IM2COL addresses (set via CONFIG)
        self.im2col_full_src_addr = Reg(params.ADDR_WIDTH, "im2col_full_src_addr")
        self.im2col_full_dst_addr = Reg(params.ADDR_WIDTH, "im2col_full_dst_addr")

        # GEMM base address registers (set via CONFIG)
        self.gemm_weight_base_addr = Reg(params.ADDR_WIDTH, "gemm_weight_base_addr")
        self.gemm_act_base_addr = Reg(params.ADDR_WIDTH, "gemm_act_base_addr")
        self.gemm_result_base_addr = Reg(params.ADDR_WIDTH, "gemm_result_base_addr")

        # =====================================================================
        # Pool Configuration Registers
        # =====================================================================
        self.pool_type_r = Reg(1, "pool_type_r")  # 0=MAX, 1=AVG
        self.pool_div_shift_r = Reg(4, "pool_div_shift_r")
        self.pool_src_target = Reg(2, "pool_src_target")
        self.pool_dst_target = Reg(2, "pool_dst_target")
        self.pool_src_addr_r = Reg(params.ADDR_WIDTH, "pool_src_addr_r")
        self.pool_dst_addr_r = Reg(params.ADDR_WIDTH, "pool_dst_addr_r")

        # =====================================================================
        # VPU (Vector Pipeline Unit) Registers
        # =====================================================================
        self.vpu_state = Reg(3, "vpu_state")
        self.vpu_rd_ptr = Reg(3, "vpu_rd_ptr")      # 0-7, read position within vector
        self.vpu_wr_ptr = Reg(3, "vpu_wr_ptr")      # 0-7, write position within vector
        self.vpu_total_cnt = Reg(8, "vpu_total_cnt") # total elements processed so far
        self.vpu_len = Reg(8, "vpu_len")            # total vector length
        self.vpu_op = Reg(4, "vpu_op")              # ALU opcode
        self.vpu_buf = Reg(2, "vpu_buf")            # target buffer ID (0=A,1=B,2=C,3=Scratch)
        self.vpu_rd_addr = Reg(params.ADDR_WIDTH, "vpu_rd_addr")
        self.vpu_wr_addr = Reg(params.ADDR_WIDTH, "vpu_wr_addr")
        self.vpu_vec_a = Memory(params.DATA_WIDTH, params.NUM_LANES, "vpu_vec_a")
        self.vpu_vec_res = Memory(params.DATA_WIDTH, params.NUM_LANES, "vpu_vec_res")
        self.va_done = Wire(1, "va_done")

        # VecALU SRAM request signals (routed to target buffer)
        self.va_req_valid = Wire(1, "va_req_valid")
        self.va_req_addr = Wire(params.ADDR_WIDTH, "va_req_addr")
        self.va_req_we = Wire(1, "va_req_we")
        self.va_req_wdata = Wire(params.DATA_WIDTH, "va_req_wdata")

        # VecALU SRAM response routing
        self.va_sram_rdata = Wire(params.DATA_WIDTH, "va_sram_rdata")
        self.va_sram_rvalid = Wire(1, "va_sram_rvalid")

        # =====================================================================
        # Submodule Status Wires (for simulation port-map visibility)
        # =====================================================================
        self.systolic_done = Wire(1, "systolic_done")
        self.systolic_adapter_done = Wire(1, "systolic_adapter_done")
        self.v_alu_out_valid = Wire(1, "v_alu_out_valid")
        self.sfu_out_valid = Wire(1, "sfu_out_valid")
        self.crossbar_busy = Wire(1, "crossbar_busy")
        self.dma_done = Wire(1, "dma_done")
        self.im2col_done = Wire(1, "im2col_done")
        self.pool_done = Wire(1, "pool_done")

        # =====================================================================
        # Controller FSM
        # =====================================================================
        self.state = Reg(3, "state")

        # Feed fetched instruction to decoder (after state is defined)
        self.decode.instr_valid <<= (self.state == ST_FETCH) | (self.state == ST_ISSUE)
        self.decode.instr_data <<= self.fetched_instr
        self.dec_opcode_r = Reg(4, "dec_opcode_r")
        self.dec_func_r = Reg(4, "dec_func_r")
        self.dec_rd_r = Reg(6, "dec_rd_r")
        self.dec_rs1_r = Reg(6, "dec_rs1_r")
        self.dec_rs2_imm_r = Reg(6, "dec_rs2_imm_r")
        self.dec_set_fence_r = Reg(3, "dec_set_fence_r")
        self.dec_wait_fence_r = Reg(3, "dec_wait_fence_r")

        # =====================================================================
        # Fence Counter Registers (8 fences, bit i = busy)
        # =====================================================================
        self.fence_busy = Reg(8, "fence_busy")
        self.gemm_fence = Reg(3, "gemm_fence")
        self.vec_alu_fence = Reg(3, "vec_alu_fence")
        self.sfu_fence = Reg(3, "sfu_fence")
        self.dma_fence = Reg(3, "dma_fence")
        self.crossbar_fence = Reg(3, "crossbar_fence")
        self.im2col_fence = Reg(3, "im2col_fence")
        self.pool_fence = Reg(3, "pool_fence")

        # =====================================================================
        # Unit Busy Registers (1-deep queue per execution unit)
        # =====================================================================
        self.gemm_busy = Reg(1, "gemm_busy")
        self.vec_alu_busy = Reg(1, "vec_alu_busy")
        self.sfu_busy = Reg(1, "sfu_busy")
        self.dma_busy = Reg(1, "dma_busy")
        self.crossbar_busy_r = Reg(1, "crossbar_busy_r")
        self.im2col_busy = Reg(1, "im2col_busy")
        self.pool_busy = Reg(1, "pool_busy")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                self.dec_opcode_r <<= 0
                self.dec_func_r <<= 0
                self.dec_rd_r <<= 0
                self.dec_rs1_r <<= 0
                self.dec_rs2_imm_r <<= 0
                self.dec_set_fence_r <<= 0
                self.dec_wait_fence_r <<= 0
                self.fence_busy <<= 0
                self.gemm_fence <<= 0
                self.vec_alu_fence <<= 0
                self.sfu_fence <<= 0
                self.dma_fence <<= 0
                self.crossbar_fence <<= 0
                self.im2col_fence <<= 0
                self.pool_fence <<= 0
                self.gemm_busy <<= 0
                self.vec_alu_busy <<= 0
                self.sfu_busy <<= 0
                self.dma_busy <<= 0
                self.crossbar_busy_r <<= 0
                self.im2col_busy <<= 0
                self.pool_busy <<= 0
                self.dma_ext_addr <<= 0
                self.dma_len <<= 0
                self.dma_sram_addr <<= 0
                self.dma_target <<= 0
                self.pc <<= 0
                self.vpu_state <<= VPU_IDLE
                self.vpu_rd_ptr <<= 0
                self.vpu_wr_ptr <<= 0
                self.vpu_total_cnt <<= 0
                self.vpu_len <<= 0
                self.vpu_op <<= 0
                self.vpu_buf <<= 0
                self.vpu_rd_addr <<= 0
                self.vpu_wr_addr <<= 0
            with Else():
                # -----------------------------------------------------------------
                # Clear fence & unit_busy when units complete
                # -----------------------------------------------------------------
                with If(self.systolic_adapter_done):
                    self.gemm_busy <<= 0
                    with If(self.gemm_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.gemm_fence)
                        self.gemm_fence <<= 0
                with If(self.va_done):
                    self.vec_alu_busy <<= 0
                    with If(self.vec_alu_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.vec_alu_fence)
                        self.vec_alu_fence <<= 0
                with If(self.sfu_out_valid):
                    self.sfu_busy <<= 0
                    with If(self.sfu_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.sfu_fence)
                        self.sfu_fence <<= 0
                with If(self.dma_done):
                    self.dma_busy <<= 0
                    with If(self.dma_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.dma_fence)
                        self.dma_fence <<= 0
                with If(~self.crossbar_busy):
                    self.crossbar_busy_r <<= 0
                    with If(self.crossbar_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.crossbar_fence)
                        self.crossbar_fence <<= 0
                with If(self.im2col_done):
                    self.im2col_busy <<= 0
                    with If(self.im2col_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.im2col_fence)
                        self.im2col_fence <<= 0
                with If(self.pool_done):
                    self.pool_busy <<= 0
                    with If(self.pool_fence != 0):
                        self.fence_busy <<= self.fence_busy & ~(1 << self.pool_fence)
                        self.pool_fence <<= 0

                with If(self.state == ST_IDLE):
                    with If(self.run_pulse):
                        self.pc <<= 0
                        with If(self.prog_length > 0):
                            self.state <<= ST_FETCH

                with If(self.state == ST_FETCH):
                    # Latch decoded instruction from combinational fetch
                    self.dec_opcode_r <<= self.decode.dec_opcode
                    self.dec_func_r <<= self.decode.dec_func
                    self.dec_rd_r <<= self.decode.dec_rd
                    self.dec_rs1_r <<= self.decode.dec_rs1
                    self.dec_rs2_imm_r <<= self.decode.dec_rs2_imm
                    self.dec_set_fence_r <<= self.decode.dec_set_fence
                    self.dec_wait_fence_r <<= self.decode.dec_wait_fence
                    self.state <<= ST_ISSUE

                with If(self.state == ST_ISSUE):
                    with If(self.pc < self.prog_length):
                        # There is a valid instruction waiting to be issued
                        wait_id = self.dec_wait_fence_r
                        fence_ok = (wait_id == 0) | (((self.fence_busy >> wait_id) & 1) == 0)

                        unit_ready = (
                            ((self.dec_opcode_r == OP_GEMM) & ~self.gemm_busy) |
                            ((self.dec_opcode_r == OP_VEC_ALU) & ~self.vec_alu_busy) |
                            ((self.dec_opcode_r == OP_SFU) & ~self.sfu_busy) |
                            ((self.dec_opcode_r == OP_CROSSBAR) & ~self.crossbar_busy_r) |
                            ((self.dec_opcode_r == OP_LOAD) & ~self.dma_busy) |
                            ((self.dec_opcode_r == OP_STORE) & ~self.dma_busy) |
                            ((self.dec_opcode_r == OP_IM2COL) & ~self.im2col_busy) |
                            ((self.dec_opcode_r == OP_POOL) & ~self.pool_busy) |
                            ((self.dec_opcode_r == OP_NOP) | (self.dec_opcode_r == OP_SYNC) | (self.dec_opcode_r == OP_CONFIG))
                        )

                        with If(fence_ok & unit_ready):
                            # Mark unit busy
                            with If(self.dec_opcode_r == OP_GEMM):
                                self.gemm_busy <<= 1
                            with If(self.dec_opcode_r == OP_VEC_ALU):
                                self.vec_alu_busy <<= 1
                                self.vpu_state <<= VPU_READ
                                self.vpu_rd_ptr <<= 0
                                self.vpu_wr_ptr <<= 0
                                self.vpu_total_cnt <<= 0
                                self.vpu_len <<= self.dec_rs2_imm_r
                                self.vpu_op <<= self.dec_func_r
                                self.vpu_buf <<= self.dec_rd_r[1:0]
                                self.vpu_rd_addr <<= 0
                                self.vpu_wr_addr <<= 0
                            with If(self.dec_opcode_r == OP_SFU):
                                self.sfu_busy <<= 1
                            with If((self.dec_opcode_r == OP_LOAD) | (self.dec_opcode_r == OP_STORE)):
                                self.dma_busy <<= 1
                            with If(self.dec_opcode_r == OP_CROSSBAR):
                                self.crossbar_busy_r <<= 1
                            with If(self.dec_opcode_r == OP_IM2COL):
                                self.im2col_busy <<= 1
                            with If(self.dec_opcode_r == OP_POOL):
                                self.pool_busy <<= 1

                            # Set fence if requested
                            set_id = self.dec_set_fence_r
                            with If(set_id != 0):
                                self.fence_busy <<= self.fence_busy | (1 << set_id)
                                with If(self.dec_opcode_r == OP_GEMM):
                                    self.gemm_fence <<= set_id
                                with If(self.dec_opcode_r == OP_VEC_ALU):
                                    self.vec_alu_fence <<= set_id
                                with If(self.dec_opcode_r == OP_SFU):
                                    self.sfu_fence <<= set_id
                                with If((self.dec_opcode_r == OP_LOAD) | (self.dec_opcode_r == OP_STORE)):
                                    self.dma_fence <<= set_id
                                with If(self.dec_opcode_r == OP_CROSSBAR):
                                    self.crossbar_fence <<= set_id
                                with If(self.dec_opcode_r == OP_IM2COL):
                                    self.im2col_fence <<= set_id
                                with If(self.dec_opcode_r == OP_POOL):
                                    self.pool_fence <<= set_id

                            # Advance PC
                            self.pc <<= self.pc + 1

                            # If more instructions remain, go fetch next; otherwise stay in ISSUE to drain
                            with If(self.pc + 1 < self.prog_length):
                                self.state <<= ST_FETCH

                    with Else():
                        # All instructions issued; wait for everything to finish
                        all_idle = (
                            (self.fence_busy == 0) &
                            ~self.gemm_busy &
                            ~self.vec_alu_busy &
                            ~self.sfu_busy &
                            ~self.dma_busy &
                            ~self.crossbar_busy_r &
                            ~self.im2col_busy &
                            ~self.pool_busy
                        )
                        with If(all_idle):
                            self.state <<= ST_IDLE


        # =====================================================================
        # Dispatch Logic (combinational)
        # =====================================================================
        @self.comb
        def _dispatch():
            # Defaults: all units idle
            self.systolic_adapter.start <<= 0
            self.systolic_adapter.k_dim <<= 0
            self.systolic_adapter.weight_base_addr <<= 0
            self.systolic_adapter.act_base_addr <<= 0
            self.systolic_adapter.result_base_addr <<= 0
            # v_alu.valid and v_alu.op are driven by VPU FSM
            self.sfu.valid <<= 0
            self.crossbar.cfg_valid <<= 0
            self.im2col.start <<= 0
            self.pool.start <<= 0
            # DMA start is a single-cycle pulse in ISSUE
            self.dma.dma_start <<= (
                (self.state == ST_ISSUE) &
                ((self.dec_opcode_r == OP_LOAD) | (self.dec_opcode_r == OP_STORE))
            )

            with If(self.state == ST_ISSUE):
                # CONFIG instruction: write DMA or Im2Col config registers
                with If(self.dec_opcode_r == OP_CONFIG):
                    cfg_data = (self.dec_rd_r << 8) | self.dec_rs2_imm_r
                    # func[3:2] selects config target: DMA(00), Pool(01), Im2Col(1x)
                    with If(self.dec_func_r[3:2] == 0):
                        # DMA config (func = 0x0..0x3)
                        with If(self.dec_rs1_r == 0):
                            with If(self.dec_func_r[1:0] == 0):
                                self.dma_ext_addr[15:0] <<= cfg_data
                            with If(self.dec_func_r[1:0] == 1):
                                self.dma_ext_addr[31:16] <<= cfg_data
                            with If(self.dec_func_r[1:0] == 2):
                                self.dma_len <<= cfg_data
                            with If(self.dec_func_r[1:0] == 3):
                                self.dma_sram_addr <<= self.dec_rs2_imm_r
                        with Else():
                            with If(self.dec_rs1_r == 1):
                                self.gemm_weight_base_addr <<= cfg_data
                            with Else():
                                with If(self.dec_rs1_r == 2):
                                    self.gemm_act_base_addr <<= cfg_data
                                with Else():
                                    with If(self.dec_rs1_r == 3):
                                        self.gemm_result_base_addr <<= cfg_data
                                    with Else():
                                        with If(self.dec_rs1_r == 4):
                                            self.im2col_full_src_addr <<= cfg_data
                                        with Else():
                                            with If(self.dec_rs1_r == 5):
                                                self.im2col_full_dst_addr <<= cfg_data
                    with Else():
                        with If(self.dec_func_r[3:2] == 1):
                            # Pool config (func = 0x4..0x7)
                            with If(self.dec_func_r[1:0] == 0):
                                # pool_type[0] in rs2[0], div_shift[3:0] in rs2[4:1]
                                self.pool_type_r <<= self.dec_rs2_imm_r[0]
                                self.pool_div_shift_r <<= self.dec_rs2_imm_r[4:1]
                            with If(self.dec_func_r[1:0] == 1):
                                self.pool_src_addr_r <<= self.dec_rs1_r
                                self.pool_dst_addr_r <<= self.dec_rd_r
                            # func=6,7 reserved for future pool config
                        with Else():
                            # Im2Col config (func = 0x8..0xF)
                            with If(self.dec_func_r[2:0] == 0):
                                self.im2col_kh <<= self.dec_rs2_imm_r[3:0]
                                self.im2col_kw <<= self.dec_rd_r[3:0]
                            with If(self.dec_func_r[2:0] == 1):
                                self.im2col_stride_h <<= self.dec_rs2_imm_r[3:0]
                                self.im2col_stride_w <<= self.dec_rd_r[3:0]
                            with If(self.dec_func_r[2:0] == 2):
                                self.im2col_pad_h <<= self.dec_rs2_imm_r[3:0]
                                self.im2col_pad_w <<= self.dec_rd_r[3:0]
                            with If(self.dec_func_r[2:0] == 3):
                                self.im2col_in_h <<= cfg_data
                            with If(self.dec_func_r[2:0] == 4):
                                self.im2col_in_w <<= cfg_data
                            with If(self.dec_func_r[2:0] == 5):
                                self.im2col_in_c <<= cfg_data
                            with If(self.dec_func_r[2:0] == 6):
                                self.im2col_out_h <<= cfg_data
                            with If(self.dec_func_r[2:0] == 7):
                                self.im2col_out_w <<= cfg_data

                with If(self.dec_opcode_r == OP_IM2COL):
                    # IM2COL instruction encodes src/dst targets in func field
                    self.im2col_src_target <<= self.dec_func_r[1:0]
                    self.im2col_dst_target <<= self.dec_func_r[3:2]
                    self.im2col_src_addr <<= self.im2col_full_src_addr
                    self.im2col_dst_addr <<= self.im2col_full_dst_addr

                with If(self.dec_opcode_r == OP_POOL):
                    # POOL instruction encodes src/dst targets in func field
                    self.pool_src_target <<= self.dec_func_r[1:0]
                    self.pool_dst_target <<= self.dec_func_r[3:2]
                    self.pool_src_addr_r <<= self.dec_rs1_r
                    self.pool_dst_addr_r <<= self.dec_rd_r

                with If(self.dec_opcode_r == OP_LOAD):
                    self.dma.dma_dir <<= 0  # LOAD = read from AXI
                    self.dma_target <<= self.dec_rd_r[1:0]
                    with If(self.dec_rs2_imm_r != 0):
                        self.dma_len <<= self.dec_rs2_imm_r

                with If(self.dec_opcode_r == OP_STORE):
                    self.dma.dma_dir <<= 1  # STORE = write to AXI
                    self.dma_target <<= self.dec_rs1_r[1:0]
                    with If(self.dec_rs2_imm_r != 0):
                        self.dma_len <<= self.dec_rs2_imm_r

                with If(self.dec_opcode_r == OP_GEMM):
                    self.systolic_adapter.start <<= 1
                    self.systolic_adapter.k_dim <<= self.dec_rs2_imm_r
                    self.systolic_adapter.weight_base_addr <<= self.gemm_weight_base_addr
                    self.systolic_adapter.act_base_addr <<= self.gemm_act_base_addr
                    self.systolic_adapter.result_base_addr <<= self.gemm_result_base_addr

                # VEC_ALU handled by VPU FSM

                with If(self.dec_opcode_r == OP_SFU):
                    self.sfu.valid <<= 1
                    self.sfu.func <<= self.dec_func_r[2:0]

                with If(self.dec_opcode_r == OP_CROSSBAR):
                    self.crossbar.cfg_valid <<= 1
                    self.crossbar.cfg_mode <<= self.dec_func_r[1:0]
                    self.crossbar.cfg_src <<= self.dec_rs1_r[1:0]
                    self.crossbar.cfg_dst <<= self.dec_rd_r[1:0]
                    self.crossbar.cfg_len <<= self.dec_rs2_imm_r

                with If(self.dec_opcode_r == OP_IM2COL):
                    self.im2col.start <<= 1
                    self.crossbar.cfg_src_addr <<= 0
                    self.crossbar.cfg_dst_addr <<= 0
                    self.crossbar.cfg_stride <<= 1

                with If(self.dec_opcode_r == OP_POOL):
                    self.pool.start <<= 1

        # =====================================================================
        # VPU (Vector Pipeline Unit) Execution Control
        # =====================================================================
        # Route SRAM response to VPU based on target buffer
        self.va_sram_rdata <<= Mux(
            self.vpu_buf == 1, self.sram_b.resp_data,
            Mux(self.vpu_buf == 2, self.sram_c.resp_data,
                Mux(self.vpu_buf == 3, self.scratch.resp_data,
                    self.sram_a.resp_data)))
        self.va_sram_rvalid <<= Mux(
            self.vpu_buf == 1, self.sram_b.resp_valid,
            Mux(self.vpu_buf == 2, self.sram_c.resp_valid,
                Mux(self.vpu_buf == 3, self.scratch.resp_valid,
                    self.sram_a.resp_valid)))

        # VecALU data connections (vector mode: all 8 lanes)
        for i in range(params.NUM_LANES):
            self.v_alu.a[i] <<= self.vpu_vec_a[i]
            self.v_alu.b[i] <<= 0
        self.v_alu.op <<= self.vpu_op
        self.v_alu.valid <<= (self.vpu_state == VPU_COMPUTE)

        # In COMPUTE->WRITE transition, capture ALU result into result buffer
        @self.comb
        def _capture_vpu_result():
            for i in range(params.NUM_LANES):
                with If(self.vpu_state == VPU_WRITE):
                    self.vpu_vec_res[i] <<= self.v_alu.result[i]

        # SRAM request routing
        @self.comb
        def _vpu_sram_req():
            self.va_req_valid <<= 0
            self.va_req_addr <<= 0
            self.va_req_we <<= 0
            self.va_req_wdata <<= 0
            self.va_done <<= (self.vpu_state == VPU_DONE)

            with If(self.vpu_state == VPU_READ):
                self.va_req_valid <<= 1
                self.va_req_addr <<= self.vpu_rd_addr
                self.va_req_we <<= 0

            with If(self.vpu_state == VPU_WRITE):
                self.va_req_valid <<= 1
                self.va_req_addr <<= self.vpu_wr_addr
                self.va_req_we <<= 1
                self.va_req_wdata <<= self.vpu_vec_res[self.vpu_wr_ptr]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _vpu_fsm():
            with If(self.rst_n == 0):
                self.vpu_state <<= VPU_IDLE
                self.vpu_rd_ptr <<= 0
                self.vpu_wr_ptr <<= 0
                self.vpu_total_cnt <<= 0
            with Else():
                with If(self.vpu_state == VPU_READ):
                    self.vpu_vec_a[self.vpu_rd_ptr] <<= self.va_sram_rdata
                    self.vpu_rd_ptr <<= self.vpu_rd_ptr + 1
                    self.vpu_rd_addr <<= self.vpu_rd_addr + 1
                    with If(self.vpu_rd_ptr + 1 >= 8):
                        self.vpu_state <<= VPU_COMPUTE

                with If(self.vpu_state == VPU_COMPUTE):
                    self.vpu_state <<= VPU_WRITE

                with If(self.vpu_state == VPU_WRITE):
                    self.vpu_wr_ptr <<= self.vpu_wr_ptr + 1
                    self.vpu_total_cnt <<= self.vpu_total_cnt + 1
                    self.vpu_wr_addr <<= self.vpu_wr_addr + 1
                    with If(self.vpu_wr_ptr + 1 >= 8):
                        with If(self.vpu_total_cnt + 1 >= self.vpu_len):
                            self.vpu_state <<= VPU_DONE
                        with Else():
                            self.vpu_state <<= VPU_READ
                            self.vpu_rd_ptr <<= 0
                            self.vpu_wr_ptr <<= 0

                with If(self.vpu_state == VPU_DONE):
                    self.vpu_state <<= VPU_IDLE

        # =====================================================================
        # Status Outputs
        # =====================================================================
        self.prog_done <<= (self.state == ST_IDLE) & (self.pc == self.prog_length) & (self.prog_length > 0)
        self.busy <<= (self.state != ST_IDLE)
        self.done <<= (self.state == ST_IDLE) & (self.pc == self.prog_length) & (self.prog_length > 0)
        self.interrupt <<= (self.state == ST_IDLE) & (self.pc == self.prog_length) & (self.prog_length > 0)

        # Submodule status connections (for simulation port-map visibility)
        self.systolic_done <<= self.systolic.done
        self.systolic_adapter_done <<= self.systolic_adapter.done
        self.v_alu_out_valid <<= self.v_alu.out_valid
        self.sfu_out_valid <<= self.sfu.out_valid
        self.crossbar_busy <<= self.crossbar.busy
        self.dma_done <<= self.dma.dma_done
        self.im2col_done <<= self.im2col.done
        self.pool_done <<= self.pool.done

        # =====================================================================
        # DMA <-> AXI4 Connection
        # =====================================================================
        self.m_axi_arid <<= self.dma.arid
        self.m_axi_araddr <<= self.dma.araddr
        self.m_axi_arlen <<= self.dma.arlen
        self.m_axi_arsize <<= self.dma.arsize
        self.m_axi_arburst <<= self.dma.arburst
        self.m_axi_arvalid <<= self.dma.arvalid
        self.dma.arready <<= self.m_axi_arready

        self.dma.rid <<= self.m_axi_rid
        self.dma.rdata <<= self.m_axi_rdata
        self.dma.rresp <<= self.m_axi_rresp
        self.dma.rlast <<= self.m_axi_rlast
        self.dma.rvalid <<= self.m_axi_rvalid
        self.m_axi_rready <<= self.dma.rready

        self.m_axi_awid <<= self.dma.awid
        self.m_axi_awaddr <<= self.dma.awaddr
        self.m_axi_awlen <<= self.dma.awlen
        self.m_axi_awsize <<= self.dma.awsize
        self.m_axi_awburst <<= self.dma.awburst
        self.m_axi_awvalid <<= self.dma.awvalid
        self.dma.awready <<= self.m_axi_awready

        self.m_axi_wdata <<= self.dma.wdata
        self.m_axi_wstrb <<= self.dma.wstrb
        self.m_axi_wlast <<= self.dma.wlast
        self.m_axi_wvalid <<= self.dma.wvalid
        self.dma.wready <<= self.m_axi_wready

        self.dma.bid <<= self.m_axi_bid
        self.dma.bresp <<= self.m_axi_bresp
        self.dma.bvalid <<= self.m_axi_bvalid
        self.m_axi_bready <<= self.dma.bready

        # =====================================================================
        # DMA Configuration Connections
        # =====================================================================
        self.dma.cfg_ext_addr <<= self.dma_ext_addr
        self.dma.cfg_len <<= self.dma_len
        self.dma.cfg_sram_addr <<= self.dma_sram_addr

        # =====================================================================
        # Im2Col Configuration Connections
        # =====================================================================
        self.im2col.cfg_kh <<= self.im2col_kh
        self.im2col.cfg_kw <<= self.im2col_kw
        self.im2col.cfg_stride_h <<= self.im2col_stride_h
        self.im2col.cfg_stride_w <<= self.im2col_stride_w
        self.im2col.cfg_pad_h <<= self.im2col_pad_h
        self.im2col.cfg_pad_w <<= self.im2col_pad_w
        self.im2col.cfg_in_h <<= self.im2col_in_h
        self.im2col.cfg_in_w <<= self.im2col_in_w
        self.im2col.cfg_in_c <<= self.im2col_in_c
        self.im2col.cfg_out_h <<= self.im2col_out_h
        self.im2col.cfg_out_w <<= self.im2col_out_w
        self.im2col.cfg_src_addr <<= self.im2col_src_addr
        self.im2col.cfg_dst_addr <<= self.im2col_dst_addr

        # =====================================================================
        # Pool Configuration Connections (reuses Im2Col spatial config)
        # =====================================================================
        self.pool.cfg_pool_type <<= self.pool_type_r
        self.pool.cfg_kh <<= self.im2col_kh
        self.pool.cfg_kw <<= self.im2col_kw
        self.pool.cfg_stride_h <<= self.im2col_stride_h
        self.pool.cfg_stride_w <<= self.im2col_stride_w
        self.pool.cfg_pad_h <<= self.im2col_pad_h
        self.pool.cfg_pad_w <<= self.im2col_pad_w
        self.pool.cfg_in_h <<= self.im2col_in_h
        self.pool.cfg_in_w <<= self.im2col_in_w
        self.pool.cfg_in_c <<= self.im2col_in_c
        self.pool.cfg_out_h <<= self.im2col_out_h
        self.pool.cfg_out_w <<= self.im2col_out_w
        self.pool.cfg_div_shift <<= self.pool_div_shift_r
        self.pool.cfg_src_addr <<= self.pool_src_addr_r
        self.pool.cfg_dst_addr <<= self.pool_dst_addr_r

        # =====================================================================
        # SRAM / Crossbar / DMA Multiplexed Connections
        # =====================================================================
        self.dma_local_req_valid = Wire(1, "dma_local_req_valid")
        self.dma_local_req_addr = Wire(params.ADDR_WIDTH, "dma_local_req_addr")
        self.dma_local_req_wdata = Wire(params.DATA_WIDTH, "dma_local_req_wdata")
        self.dma_local_req_we = Wire(1, "dma_local_req_we")

        self.dma_local_req_valid <<= self.dma.local_req_valid
        self.dma_local_req_addr <<= self.dma.local_req_addr
        self.dma_local_req_wdata <<= self.dma.local_req_wdata
        self.dma_local_req_we <<= self.dma.local_req_we

        # =====================================================================
        # SRAM Request MUX Helpers (DMA > Im2Col > Pool > Crossbar)
        # =====================================================================
        sram_a_dma = self.dma_local_req_valid & (self.dma_target == 0)
        sram_a_im2col_src = self.im2col.src_req_valid & (self.im2col_src_target == 0) & ~sram_a_dma
        sram_a_im2col_dst = self.im2col.dst_req_valid & (self.im2col_dst_target == 0) & ~sram_a_dma & ~sram_a_im2col_src
        sram_a_pool_src = self.pool.src_req_valid & (self.pool_src_target == 0) & ~sram_a_dma & ~sram_a_im2col_src & ~sram_a_im2col_dst
        sram_a_pool_dst = self.pool.dst_req_valid & (self.pool_dst_target == 0) & ~sram_a_dma & ~sram_a_im2col_src & ~sram_a_im2col_dst & ~sram_a_pool_src
        sram_a_crossbar = self.crossbar.port_valid[0] & ~sram_a_dma & ~sram_a_im2col_src & ~sram_a_im2col_dst & ~sram_a_pool_src & ~sram_a_pool_dst
        sram_a_systolic = self.systolic_adapter.weight_req_valid & ~sram_a_dma & ~sram_a_im2col_src & ~sram_a_im2col_dst & ~sram_a_pool_src & ~sram_a_pool_dst & ~sram_a_crossbar
        sram_a_vec_alu = self.va_req_valid & (self.vpu_buf == 0) & ~sram_a_dma & ~sram_a_im2col_src & ~sram_a_im2col_dst & ~sram_a_pool_src & ~sram_a_pool_dst & ~sram_a_crossbar & ~sram_a_systolic

        sram_b_dma = self.dma_local_req_valid & (self.dma_target == 1)
        sram_b_im2col_src = self.im2col.src_req_valid & (self.im2col_src_target == 1) & ~sram_b_dma
        sram_b_im2col_dst = self.im2col.dst_req_valid & (self.im2col_dst_target == 1) & ~sram_b_dma & ~sram_b_im2col_src
        sram_b_pool_src = self.pool.src_req_valid & (self.pool_src_target == 1) & ~sram_b_dma & ~sram_b_im2col_src & ~sram_b_im2col_dst
        sram_b_pool_dst = self.pool.dst_req_valid & (self.pool_dst_target == 1) & ~sram_b_dma & ~sram_b_im2col_src & ~sram_b_im2col_dst & ~sram_b_pool_src
        sram_b_crossbar = self.crossbar.port_valid[1] & ~sram_b_dma & ~sram_b_im2col_src & ~sram_b_im2col_dst & ~sram_b_pool_src & ~sram_b_pool_dst
        sram_b_systolic = self.systolic_adapter.act_req_valid & ~sram_b_dma & ~sram_b_im2col_src & ~sram_b_im2col_dst & ~sram_b_pool_src & ~sram_b_pool_dst & ~sram_b_crossbar
        sram_b_vec_alu = self.va_req_valid & (self.vpu_buf == 1) & ~sram_b_dma & ~sram_b_im2col_src & ~sram_b_im2col_dst & ~sram_b_pool_src & ~sram_b_pool_dst & ~sram_b_crossbar & ~sram_b_systolic

        sram_c_dma = self.dma_local_req_valid & (self.dma_target == 2)
        sram_c_im2col_src = self.im2col.src_req_valid & (self.im2col_src_target == 2) & ~sram_c_dma
        sram_c_im2col_dst = self.im2col.dst_req_valid & (self.im2col_dst_target == 2) & ~sram_c_dma & ~sram_c_im2col_src
        sram_c_pool_src = self.pool.src_req_valid & (self.pool_src_target == 2) & ~sram_c_dma & ~sram_c_im2col_src & ~sram_c_im2col_dst
        sram_c_pool_dst = self.pool.dst_req_valid & (self.pool_dst_target == 2) & ~sram_c_dma & ~sram_c_im2col_src & ~sram_c_im2col_dst & ~sram_c_pool_src
        sram_c_crossbar = self.crossbar.port_valid[2] & ~sram_c_dma & ~sram_c_im2col_src & ~sram_c_im2col_dst & ~sram_c_pool_src & ~sram_c_pool_dst
        sram_c_systolic = self.systolic_adapter.result_wr_valid & ~sram_c_dma & ~sram_c_im2col_src & ~sram_c_im2col_dst & ~sram_c_pool_src & ~sram_c_pool_dst & ~sram_c_crossbar
        sram_c_vec_alu = self.va_req_valid & (self.vpu_buf == 2) & ~sram_c_dma & ~sram_c_im2col_src & ~sram_c_im2col_dst & ~sram_c_pool_src & ~sram_c_pool_dst & ~sram_c_crossbar & ~sram_c_systolic

        scratch_dma = self.dma_local_req_valid & (self.dma_target == 3)
        scratch_im2col_src = self.im2col.src_req_valid & (self.im2col_src_target == 3) & ~scratch_dma
        scratch_im2col_dst = self.im2col.dst_req_valid & (self.im2col_dst_target == 3) & ~scratch_dma & ~scratch_im2col_src
        scratch_pool_src = self.pool.src_req_valid & (self.pool_src_target == 3) & ~scratch_dma & ~scratch_im2col_src & ~scratch_im2col_dst
        scratch_pool_dst = self.pool.dst_req_valid & (self.pool_dst_target == 3) & ~scratch_dma & ~scratch_im2col_src & ~scratch_im2col_dst & ~scratch_pool_src
        scratch_crossbar = self.crossbar.port_valid[3] & ~scratch_dma & ~scratch_im2col_src & ~scratch_im2col_dst & ~scratch_pool_src & ~scratch_pool_dst
        scratch_vec_alu = self.va_req_valid & (self.vpu_buf == 3) & ~scratch_dma & ~scratch_im2col_src & ~scratch_im2col_dst & ~scratch_pool_src & ~scratch_pool_dst & ~scratch_crossbar

        # SRAM A (target = 0)
        self.sram_a.req_valid <<= sram_a_dma | sram_a_im2col_src | sram_a_im2col_dst | sram_a_pool_src | sram_a_pool_dst | sram_a_crossbar | sram_a_systolic | sram_a_vec_alu
        self.sram_a.req_addr <<= Mux(sram_a_systolic, self.systolic_adapter.weight_req_addr,
                                      Mux(sram_a_dma, self.dma_local_req_addr,
                                          Mux(sram_a_im2col_src | sram_a_im2col_dst, self.im2col.src_req_addr,
                                              Mux(sram_a_pool_src | sram_a_pool_dst, self.pool.src_req_addr,
                                                  Mux(sram_a_crossbar, self.crossbar.port_addr[0],
                                                      self.va_req_addr)))))
        self.sram_a.req_wdata <<= Mux(sram_a_systolic, 0,
                                       Mux(sram_a_dma, self.dma_local_req_wdata,
                                           Mux(sram_a_im2col_dst, self.im2col.dst_req_wdata,
                                               Mux(sram_a_pool_dst, self.pool.dst_req_wdata,
                                                   Mux(sram_a_crossbar, self.crossbar.port_wdata[0],
                                                       self.va_req_wdata)))))
        self.sram_a.req_we <<= Mux(sram_a_systolic, 0,
                                    Mux(sram_a_dma, self.dma_local_req_we,
                                        Mux(sram_a_im2col_dst, self.im2col.dst_req_we,
                                            Mux(sram_a_pool_dst, self.pool.dst_req_we,
                                                Mux(sram_a_crossbar, self.crossbar.port_we[0],
                                                    self.va_req_we)))))
        self.crossbar.port_rdata[0] <<= self.sram_a.resp_data

        # SRAM B (target = 1)
        self.sram_b.req_valid <<= sram_b_dma | sram_b_im2col_src | sram_b_im2col_dst | sram_b_pool_src | sram_b_pool_dst | sram_b_crossbar | sram_b_systolic | sram_b_vec_alu
        self.sram_b.req_addr <<= Mux(sram_b_systolic, self.systolic_adapter.act_req_addr,
                                      Mux(sram_b_dma, self.dma_local_req_addr,
                                          Mux(sram_b_im2col_src | sram_b_im2col_dst, self.im2col.src_req_addr,
                                              Mux(sram_b_pool_src | sram_b_pool_dst, self.pool.src_req_addr,
                                                  Mux(sram_b_crossbar, self.crossbar.port_addr[1],
                                                      self.va_req_addr)))))
        self.sram_b.req_wdata <<= Mux(sram_b_systolic, 0,
                                       Mux(sram_b_dma, self.dma_local_req_wdata,
                                           Mux(sram_b_im2col_dst, self.im2col.dst_req_wdata,
                                               Mux(sram_b_pool_dst, self.pool.dst_req_wdata,
                                                   Mux(sram_b_crossbar, self.crossbar.port_wdata[1],
                                                       self.va_req_wdata)))))
        self.sram_b.req_we <<= Mux(sram_b_systolic, 0,
                                    Mux(sram_b_dma, self.dma_local_req_we,
                                        Mux(sram_b_im2col_dst, self.im2col.dst_req_we,
                                            Mux(sram_b_pool_dst, self.pool.dst_req_we,
                                                Mux(sram_b_crossbar, self.crossbar.port_we[1],
                                                    self.va_req_we)))))
        self.crossbar.port_rdata[1] <<= self.sram_b.resp_data

        # SRAM C (target = 2)
        self.sram_c.req_valid <<= sram_c_dma | sram_c_im2col_src | sram_c_im2col_dst | sram_c_pool_src | sram_c_pool_dst | sram_c_crossbar | sram_c_systolic | sram_c_vec_alu
        self.sram_c.req_addr <<= Mux(sram_c_systolic, self.systolic_adapter.result_wr_addr,
                                      Mux(sram_c_dma, self.dma_local_req_addr,
                                          Mux(sram_c_im2col_src | sram_c_im2col_dst, self.im2col.src_req_addr,
                                              Mux(sram_c_pool_src | sram_c_pool_dst, self.pool.src_req_addr,
                                                  Mux(sram_c_crossbar, self.crossbar.port_addr[2],
                                                      self.va_req_addr)))))
        self.sram_c.req_wdata <<= Mux(sram_c_systolic, self.systolic_adapter.result_wr_data,
                                       Mux(sram_c_dma, self.dma_local_req_wdata,
                                           Mux(sram_c_im2col_dst, self.im2col.dst_req_wdata,
                                               Mux(sram_c_pool_dst, self.pool.dst_req_wdata,
                                                   Mux(sram_c_crossbar, self.crossbar.port_wdata[2],
                                                       self.va_req_wdata)))))
        self.sram_c.req_we <<= sram_c_systolic | Mux(sram_c_dma, self.dma_local_req_we,
                                                       Mux(sram_c_im2col_dst, self.im2col.dst_req_we,
                                                           Mux(sram_c_pool_dst, self.pool.dst_req_we,
                                                               Mux(sram_c_crossbar, self.crossbar.port_we[2],
                                                                   self.va_req_we))))
        self.crossbar.port_rdata[2] <<= self.sram_c.resp_data

        # Scratchpad (target = 3)
        self.scratch.req_valid <<= scratch_dma | scratch_im2col_src | scratch_im2col_dst | scratch_pool_src | scratch_pool_dst | scratch_crossbar | scratch_vec_alu
        self.scratch.req_addr <<= Mux(scratch_dma, self.dma_local_req_addr,
                                       Mux(scratch_im2col_src | scratch_im2col_dst, self.im2col.src_req_addr,
                                           Mux(scratch_pool_src | scratch_pool_dst, self.pool.src_req_addr,
                                               Mux(scratch_crossbar, self.crossbar.port_addr[3],
                                                   self.va_req_addr))))
        self.scratch.req_wdata <<= Mux(scratch_dma, self.dma_local_req_wdata,
                                        Mux(scratch_im2col_dst, self.im2col.dst_req_wdata,
                                            Mux(scratch_pool_dst, self.pool.dst_req_wdata,
                                                Mux(scratch_crossbar, self.crossbar.port_wdata[3],
                                                    self.va_req_wdata))))
        self.scratch.req_we <<= Mux(scratch_dma, self.dma_local_req_we,
                                     Mux(scratch_im2col_dst, self.im2col.dst_req_we,
                                         Mux(scratch_pool_dst, self.pool.dst_req_we,
                                             Mux(scratch_crossbar, self.crossbar.port_we[3],
                                                 self.va_req_we))))
        self.crossbar.port_rdata[3] <<= self.scratch.resp_data

        # =====================================================================
        # Im2Col SRAM Response Routing
        # =====================================================================
        self.im2col.src_resp_valid <<= (
            (self.im2col_src_target == 0) & self.sram_a.resp_valid |
            (self.im2col_src_target == 1) & self.sram_b.resp_valid |
            (self.im2col_src_target == 2) & self.sram_c.resp_valid |
            (self.im2col_src_target == 3) & self.scratch.resp_valid
        )
        self.im2col.src_resp_data <<= Mux(
            self.im2col_src_target == 1, self.sram_b.resp_data,
            Mux(self.im2col_src_target == 2, self.sram_c.resp_data,
                Mux(self.im2col_src_target == 3, self.scratch.resp_data,
                    self.sram_a.resp_data)))

        # =====================================================================
        # Pool SRAM Response Routing
        # =====================================================================
        self.pool.src_resp_valid <<= (
            (self.pool_src_target == 0) & self.sram_a.resp_valid |
            (self.pool_src_target == 1) & self.sram_b.resp_valid |
            (self.pool_src_target == 2) & self.sram_c.resp_valid |
            (self.pool_src_target == 3) & self.scratch.resp_valid
        )
        self.pool.src_resp_data <<= Mux(
            self.pool_src_target == 1, self.sram_b.resp_data,
            Mux(self.pool_src_target == 2, self.sram_c.resp_data,
                Mux(self.pool_src_target == 3, self.scratch.resp_data,
                    self.sram_a.resp_data)))

        # =====================================================================
        # DMA Local Response Multiplexer
        # =====================================================================
        self.dma_local_resp_data = Wire(params.DATA_WIDTH, "dma_local_resp_data")
        self.dma_local_resp_valid = Wire(1, "dma_local_resp_valid")

        @self.comb
        def _dma_resp_mux():
            self.dma_local_resp_data <<= self.sram_a.resp_data
            self.dma_local_resp_valid <<= self.sram_a.resp_valid & (self.dma_target == 0)

            with If(self.dma_target == 1):
                self.dma_local_resp_data <<= self.sram_b.resp_data
                self.dma_local_resp_valid <<= self.sram_b.resp_valid
            with If(self.dma_target == 2):
                self.dma_local_resp_data <<= self.sram_c.resp_data
                self.dma_local_resp_valid <<= self.sram_c.resp_valid
            with If(self.dma_target == 3):
                self.dma_local_resp_data <<= self.scratch.resp_data
                self.dma_local_resp_valid <<= self.scratch.resp_valid

        self.dma.local_resp_data <<= self.dma_local_resp_data
        self.dma.local_resp_valid <<= self.dma_local_resp_valid

        # =====================================================================
        # Systolic Adapter SRAM Response Routing
        # =====================================================================
        self.systolic_adapter.weight_resp_valid <<= self.sram_a.resp_valid
        self.systolic_adapter.weight_resp_data <<= self.sram_a.resp_data
        self.systolic_adapter.act_resp_valid <<= self.sram_b.resp_valid
        self.systolic_adapter.act_resp_data <<= self.sram_b.resp_data

        # =====================================================================
        # Systolic Adapter <-> Systolic Array Data Path
        # =====================================================================
        self.systolic.weight_load_en <<= self.systolic_adapter.weight_load_en
        self.systolic.act_valid <<= self.systolic_adapter.act_valid
        for i in range(params.ARRAY_SIZE):
            self.systolic.weight_in[i] <<= self.systolic_adapter.weight_out[i]
            self.systolic.act_in[i] <<= self.systolic_adapter.act_out[i]
            self.systolic_adapter.result_in[i] <<= self.systolic.result_out[i]
        self.systolic_adapter.result_valid <<= self.systolic.result_valid
        self.systolic.start <<= self.systolic_adapter.systolic_start
        self.systolic.k_dim <<= self.systolic_adapter.systolic_k_dim
