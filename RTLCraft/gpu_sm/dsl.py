"""Legacy-DSL implementation of a compact GPU Streaming Multiprocessor (SM).

Architecture
------------
* 2 warps, 4 lanes per warp
* 16 registers per warp (each register is 64 bits: 4 x 16-bit lanes)
* 256 x 16-bit shared memory
* One instruction issued per cycle to one warp
* SIMD unit: single-cycle, 4-lane integer ALU
* SFU unit: 4-cycle pipelined Q0.16 rsqrt LUT
* GEMM unit: 4-cycle pipelined 2x2 integer matrix multiply

The design avoids the known seq-multiplier simulator bug (audit0620 A1) by
keeping multipliers in combinational logic and registering only the wire result.
"""

from __future__ import annotations

from rtlgen_x.dsl import (
    Cat,
    Const,
    Else,
    If,
    Input,
    Memory,
    Module,
    Mux,
    Output,
    Reg,
    Wire,
)

from .reference import (
    DATA_WIDTH,
    INSTR_WIDTH,
    LANES,
    NUM_WARPS,
    REGS_PER_WARP,
    REG_ADDR_W,
    REG_WORD_WIDTH,
    SHARED_MEM_SIZE,
    SFU_RSQRT_LUT,
    WARP_ID_W,
    OP_GEMM_MATMUL,
    OP_LOAD_IMM,
    OP_LOAD_MEM,
    OP_SIMD_ADD,
    OP_SIMD_AND,
    OP_SIMD_MUL,
    OP_SIMD_OR,
    OP_SIMD_SUB,
    OP_SIMD_XOR,
    OP_SFU_RSQRT,
    OP_STORE_MEM,
    SIMD_OPS,
)


class GpuSm(Module):
    """Compact GPU SM with SIMD, SFU, GEMM, register file and warp scheduler."""

    SIMD_LATENCY = 1
    SFU_LATENCY = 4
    GEMM_LATENCY = 4

    def __init__(self):
        super().__init__("gpu_sm")

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.instr_valid = Input(1, "instr_valid")
        self.instr = Input(INSTR_WIDTH, "instr")

        self.out_valid = Output(1, "out_valid")
        self.out_warp = Output(WARP_ID_W, "out_warp")
        self.out_reg = Output(REG_ADDR_W, "out_reg")
        self.out_data = Output(REG_WORD_WIDTH, "out_data")
        self.busy = Output(1, "busy")

        self.out_valid_reg = Reg(1, "out_valid_reg", init_value=0)
        self.out_warp_reg = Reg(WARP_ID_W, "out_warp_reg", init_value=0)
        self.out_reg_reg = Reg(REG_ADDR_W, "out_reg_reg", init_value=0)
        self.out_data_reg = Reg(REG_WORD_WIDTH, "out_data_reg", init_value=0)

        # ------------------------------------------------------------------
        # Warp state
        # ------------------------------------------------------------------
        self.warp_busy: list[Reg] = []
        self.warp_active: list[Reg] = []
        for w in range(NUM_WARPS):
            wb = Reg(4, f"warp_busy_{w}", init_value=0)
            wa = Reg(1, f"warp_active_{w}", init_value=1)
            setattr(self, wb.name, wb)
            setattr(self, wa.name, wa)
            self.warp_busy.append(wb)
            self.warp_active.append(wa)

        # ------------------------------------------------------------------
        # Register files (one per warp)
        # ------------------------------------------------------------------
        self.reg_files: list[Memory] = []
        for w in range(NUM_WARPS):
            mem = self.add_memory(
                Memory(width=REG_WORD_WIDTH, depth=REGS_PER_WARP, name=f"reg_file_{w}", init_zero=True)
            )
            self.reg_files.append(mem)

        # Shared memory
        self.shared_mem = self.add_memory(
            Memory(width=DATA_WIDTH, depth=SHARED_MEM_SIZE, name="shared_mem", init_zero=True)
        )

        # ------------------------------------------------------------------
        # Issue stage pipeline registers
        # ------------------------------------------------------------------
        self.issue_valid = Reg(1, "issue_valid", init_value=0)
        self.issue_warp = Reg(WARP_ID_W, "issue_warp", init_value=0)
        self.issue_opcode = Reg(4, "issue_opcode", init_value=0)
        self.issue_dst = Reg(REG_ADDR_W, "issue_dst", init_value=0)
        self.issue_src0_data = Reg(REG_WORD_WIDTH, "issue_src0_data", init_value=0)
        self.issue_src1_data = Reg(REG_WORD_WIDTH, "issue_src1_data", init_value=0)
        self.issue_imm = Reg(10, "issue_imm", init_value=0)

        # ------------------------------------------------------------------
        # Combinational decode / scheduler wires
        # ------------------------------------------------------------------
        self.dec_opcode = Wire(4, "dec_opcode")
        self.dec_warp = Wire(WARP_ID_W, "dec_warp")
        self.dec_dst = Wire(REG_ADDR_W, "dec_dst")
        self.dec_src0 = Wire(REG_ADDR_W, "dec_src0")
        self.dec_src1 = Wire(REG_ADDR_W, "dec_src1")
        self.dec_src2 = Wire(REG_ADDR_W, "dec_src2")
        self.dec_imm = Wire(10, "dec_imm")

        self.warp_ready = Wire(1, "warp_ready")
        self.issue_accept = Wire(1, "issue_accept")

        self.rf_rd0_data = Wire(REG_WORD_WIDTH, "rf_rd0_data")
        self.rf_rd1_data = Wire(REG_WORD_WIDTH, "rf_rd1_data")

        # Per-lane SIMD operand / result wires
        self.simd_a = [Wire(DATA_WIDTH, f"simd_a_{i}") for i in range(LANES)]
        self.simd_b = [Wire(DATA_WIDTH, f"simd_b_{i}") for i in range(LANES)]
        self.simd_mul = [Wire(DATA_WIDTH * 2, f"simd_mul_{i}") for i in range(LANES)]
        self.simd_res = [Wire(DATA_WIDTH, f"simd_res_{i}") for i in range(LANES)]
        self.simd_result = Wire(REG_WORD_WIDTH, "simd_result")

        # GEMM wires (2x2 stored as 4 lanes)
        self.gemm_a = [Wire(DATA_WIDTH, f"gemm_a_{i}") for i in range(LANES)]
        self.gemm_b = [Wire(DATA_WIDTH, f"gemm_b_{i}") for i in range(LANES)]
        self.gemm_p00 = [Wire(32, f"gemm_p00_{i}") for i in range(LANES)]
        self.gemm_p01 = [Wire(32, f"gemm_p01_{i}") for i in range(LANES)]
        self.gemm_sum = [Wire(33, f"gemm_sum_{i}") for i in range(LANES)]
        self.gemm_shifted = [Wire(25, f"gemm_shifted_{i}") for i in range(LANES)]
        self.gemm_scaled = [Wire(DATA_WIDTH, f"gemm_scaled_{i}") for i in range(LANES)]
        self.gemm_result = Wire(REG_WORD_WIDTH, "gemm_result")

        # SFU wires
        self.sfu_a = [Wire(DATA_WIDTH, f"sfu_a_{i}") for i in range(LANES)]
        self.sfu_addr = [Wire(6, f"sfu_addr_{i}") for i in range(LANES)]
        self.sfu_lut_out = [Wire(DATA_WIDTH, f"sfu_lut_out_{i}") for i in range(LANES)]
        self.sfu_result = Wire(REG_WORD_WIDTH, "sfu_result")

        # Final writeback muxing
        self.wb_data = Wire(REG_WORD_WIDTH, "wb_data")
        self.wb_valid = Wire(1, "wb_valid")
        self.wb_warp = Wire(WARP_ID_W, "wb_warp")
        self.wb_reg = Wire(REG_ADDR_W, "wb_reg")
        self.wb_we = Wire(1, "wb_we")

        self.mem_addr_full = Wire(11, "mem_addr_full")
        self.shared_wr_addr = Wire(SHARED_MEM_SIZE.bit_length(), "shared_wr_addr")
        self.load_mem_addr = Wire(SHARED_MEM_SIZE.bit_length(), "load_mem_addr")
        self.shared_wr_data = Wire(DATA_WIDTH, "shared_wr_data")
        self.shared_wr_en = Wire(1, "shared_wr_en")

        # Long-latency pipeline valid bits / data
        self.sfu_v0 = Reg(1, "sfu_v0", init_value=0)
        self.sfu_v1 = Reg(1, "sfu_v1", init_value=0)
        self.sfu_v2 = Reg(1, "sfu_v2", init_value=0)
        self.sfu_v3 = Reg(1, "sfu_v3", init_value=0)
        self.sfu_warp0 = Reg(WARP_ID_W, "sfu_warp0", init_value=0)
        self.sfu_warp1 = Reg(WARP_ID_W, "sfu_warp1", init_value=0)
        self.sfu_warp2 = Reg(WARP_ID_W, "sfu_warp2", init_value=0)
        self.sfu_warp3 = Reg(WARP_ID_W, "sfu_warp3", init_value=0)
        self.sfu_dst0 = Reg(REG_ADDR_W, "sfu_dst0", init_value=0)
        self.sfu_dst1 = Reg(REG_ADDR_W, "sfu_dst1", init_value=0)
        self.sfu_dst2 = Reg(REG_ADDR_W, "sfu_dst2", init_value=0)
        self.sfu_dst3 = Reg(REG_ADDR_W, "sfu_dst3", init_value=0)
        self.sfu_data0 = Reg(REG_WORD_WIDTH, "sfu_data0", init_value=0)
        self.sfu_data1 = Reg(REG_WORD_WIDTH, "sfu_data1", init_value=0)
        self.sfu_data2 = Reg(REG_WORD_WIDTH, "sfu_data2", init_value=0)
        self.sfu_data3 = Reg(REG_WORD_WIDTH, "sfu_data3", init_value=0)

        self.gemm_v0 = Reg(1, "gemm_v0", init_value=0)
        self.gemm_v1 = Reg(1, "gemm_v1", init_value=0)
        self.gemm_v2 = Reg(1, "gemm_v2", init_value=0)
        self.gemm_v3 = Reg(1, "gemm_v3", init_value=0)
        self.gemm_warp0 = Reg(WARP_ID_W, "gemm_warp0", init_value=0)
        self.gemm_warp1 = Reg(WARP_ID_W, "gemm_warp1", init_value=0)
        self.gemm_warp2 = Reg(WARP_ID_W, "gemm_warp2", init_value=0)
        self.gemm_warp3 = Reg(WARP_ID_W, "gemm_warp3", init_value=0)
        self.gemm_dst0 = Reg(REG_ADDR_W, "gemm_dst0", init_value=0)
        self.gemm_dst1 = Reg(REG_ADDR_W, "gemm_dst1", init_value=0)
        self.gemm_dst2 = Reg(REG_ADDR_W, "gemm_dst2", init_value=0)
        self.gemm_dst3 = Reg(REG_ADDR_W, "gemm_dst3", init_value=0)
        self.gemm_data0 = Reg(REG_WORD_WIDTH, "gemm_data0", init_value=0)
        self.gemm_data1 = Reg(REG_WORD_WIDTH, "gemm_data1", init_value=0)
        self.gemm_data2 = Reg(REG_WORD_WIDTH, "gemm_data2", init_value=0)
        self.gemm_data3 = Reg(REG_WORD_WIDTH, "gemm_data3", init_value=0)

        # ------------------------------------------------------------------
        # Combinational decode / scheduler / register read
        # ------------------------------------------------------------------
        with self.comb:
            self.dec_opcode <<= self.instr[31:28]
            self.dec_warp <<= self.instr[27:26]  # bottom WARP_ID_W bits
            self.dec_dst <<= self.instr[25:22]
            self.dec_src0 <<= self.instr[21:18]
            self.dec_src1 <<= self.instr[17:14]
            self.dec_src2 <<= self.instr[13:10]
            self.dec_imm <<= self.instr[9:0]

            # Warp is ready if active and not busy.
            self.warp_ready <<= Mux(
                self.dec_warp == 0,
                self.warp_active[0] & (self.warp_busy[0] == 0),
                self.warp_active[1] & (self.warp_busy[1] == 0),
            )
            self.issue_accept <<= self.instr_valid & self.warp_ready

            # Read register file for the selected warp.
            self.rf_rd0_data <<= Mux(
                self.dec_warp == 0,
                self.reg_files[0][self.dec_src0],
                self.reg_files[1][self.dec_src0],
            )
            self.rf_rd1_data <<= Mux(
                self.dec_warp == 0,
                self.reg_files[0][self.dec_src1],
                self.reg_files[1][self.dec_src1],
            )

            self.busy <<= ~self.warp_ready

        # ------------------------------------------------------------------
        # Per-lane SIMD combinationals
        # ------------------------------------------------------------------
        @self.comb
        def _simd_comb():
            for lane in range(LANES):
                lo = lane * DATA_WIDTH
                hi = lo + DATA_WIDTH - 1
                self.simd_a[lane] <<= self.issue_src0_data[hi:lo]
                self.simd_b[lane] <<= self.issue_src1_data[hi:lo]

                add_r = self.simd_a[lane] + self.simd_b[lane]
                sub_r = self.simd_a[lane] - self.simd_b[lane]
                # comb multiplier -> wire, then masked to 16 bits
                self.simd_mul[lane] <<= self.simd_a[lane] * self.simd_b[lane]
                mul_r = self.simd_mul[lane][DATA_WIDTH - 1:0]
                and_r = self.simd_a[lane] & self.simd_b[lane]
                or_r = self.simd_a[lane] | self.simd_b[lane]
                xor_r = self.simd_a[lane] ^ self.simd_b[lane]

                op = self.issue_opcode
                self.simd_res[lane] <<= Mux(
                    op == OP_SIMD_ADD,
                    add_r,
                    Mux(
                        op == OP_SIMD_SUB,
                        sub_r,
                        Mux(
                            op == OP_SIMD_MUL,
                            mul_r,
                            Mux(
                                op == OP_SIMD_AND,
                                and_r,
                                Mux(
                                    op == OP_SIMD_OR,
                                    or_r,
                                    Mux(op == OP_SIMD_XOR, xor_r, Const(0, DATA_WIDTH)),
                                ),
                            ),
                        ),
                    ),
                )

            # Pack SIMD lanes
            self.simd_result <<= Cat(*self.simd_res)

        # ------------------------------------------------------------------
        # GEMM combinational (2x2 matmul)
        # ------------------------------------------------------------------
        @self.comb
        def _gemm_comb():
            for lane in range(LANES):
                lo = lane * DATA_WIDTH
                hi = lo + DATA_WIDTH - 1
                self.gemm_a[lane] <<= self.issue_src0_data[hi:lo]
                self.gemm_b[lane] <<= self.issue_src1_data[hi:lo]

            # a = [a00, a01, a10, a11], b = [b00, b01, b10, b11]
            # C00 = a00*b00 + a01*b10
            self.gemm_p00[0] <<= self.gemm_a[0] * self.gemm_b[0]
            self.gemm_p01[0] <<= self.gemm_a[1] * self.gemm_b[2]
            # C01 = a00*b01 + a01*b11
            self.gemm_p00[1] <<= self.gemm_a[0] * self.gemm_b[1]
            self.gemm_p01[1] <<= self.gemm_a[1] * self.gemm_b[3]
            # C10 = a10*b00 + a11*b10
            self.gemm_p00[2] <<= self.gemm_a[2] * self.gemm_b[0]
            self.gemm_p01[2] <<= self.gemm_a[3] * self.gemm_b[2]
            # C11 = a10*b01 + a11*b11
            self.gemm_p00[3] <<= self.gemm_a[2] * self.gemm_b[1]
            self.gemm_p01[3] <<= self.gemm_a[3] * self.gemm_b[3]

            for lane in range(LANES):
                self.gemm_sum[lane] <<= (self.gemm_p00[lane] + self.gemm_p01[lane])
                self.gemm_shifted[lane] <<= self.gemm_sum[lane] >> 8
                self.gemm_scaled[lane] <<= self.gemm_shifted[lane][DATA_WIDTH - 1:0]

            self.gemm_result <<= Cat(*self.gemm_scaled)

        # ------------------------------------------------------------------
        # SFU combinational (rsqrt LUT)
        # ------------------------------------------------------------------
        self.sfu_lut = self.add_memory(
            Memory(
                width=DATA_WIDTH,
                depth=len(SFU_RSQRT_LUT),
                name="sfu_lut",
                init_data=list(SFU_RSQRT_LUT),
            )
        )

        @self.comb
        def _sfu_comb():
            for lane in range(LANES):
                lo = lane * DATA_WIDTH
                hi = lo + DATA_WIDTH - 1
                self.sfu_a[lane] <<= self.issue_src0_data[hi:lo]
                self.sfu_addr[lane] <<= self.sfu_a[lane][DATA_WIDTH - 1:DATA_WIDTH - 6]
                self.sfu_lut_out[lane] <<= self.sfu_lut[self.sfu_addr[lane]]

            self.sfu_result <<= Cat(*self.sfu_lut_out)

        # ------------------------------------------------------------------
        # Writeback mux and shared-memory write address
        # ------------------------------------------------------------------
        @self.comb
        def _wb_comb():
            op = self.issue_opcode
            is_simd = (
                (op == OP_SIMD_ADD)
                | (op == OP_SIMD_SUB)
                | (op == OP_SIMD_MUL)
                | (op == OP_SIMD_AND)
                | (op == OP_SIMD_OR)
                | (op == OP_SIMD_XOR)
            )
            is_load_imm = op == OP_LOAD_IMM
            is_load_mem = op == OP_LOAD_MEM
            is_store_mem = op == OP_STORE_MEM
            is_sfu = op == OP_SFU_RSQRT
            is_gemm = op == OP_GEMM_MATMUL

            self.wb_valid <<= self.issue_valid & (is_simd | is_load_imm | is_load_mem | is_sfu | is_gemm)
            self.wb_warp <<= self.issue_warp
            self.wb_reg <<= self.issue_dst

            imm16 = Cat(Const(0, DATA_WIDTH - 10), self.issue_imm)
            load_imm_data = Cat(*[imm16 for _ in range(LANES)])

            self.mem_addr_full <<= self.issue_src0_data[DATA_WIDTH - 1:0] + self.issue_imm
            self.load_mem_addr <<= self.mem_addr_full[SHARED_MEM_SIZE.bit_length() - 1:0]
            load_mem_data = Cat(*[self.shared_mem[self.load_mem_addr] for _ in range(LANES)])

            self.wb_data <<= Mux(
                is_sfu,
                self.sfu_result,
                Mux(
                    is_gemm,
                    self.gemm_result,
                    Mux(
                        is_load_imm,
                        load_imm_data,
                        Mux(is_load_mem, load_mem_data, self.simd_result),
                    ),
                ),
            )

            self.wb_we <<= self.wb_valid & ~is_store_mem

            self.shared_wr_addr <<= self.mem_addr_full[SHARED_MEM_SIZE.bit_length() - 1:0]
            self.shared_wr_data <<= self.issue_src1_data[DATA_WIDTH - 1:0]
            self.shared_wr_en <<= self.issue_valid & is_store_mem

        # ------------------------------------------------------------------
        # Registered outputs (one-cycle pulse stretcher for verification)
        # ------------------------------------------------------------------
        @self.seq(self.clk, self.rst)
        def _output_seq():
            with If(self.rst == 1):
                self.out_valid_reg <<= 0
                self.out_warp_reg <<= 0
                self.out_reg_reg <<= 0
                self.out_data_reg <<= 0
            with Else():
                self.out_valid_reg <<= self.wb_valid
                self.out_warp_reg <<= self.wb_warp
                self.out_reg_reg <<= self.wb_reg
                self.out_data_reg <<= self.wb_data

        with self.comb:
            self.out_valid <<= self.out_valid_reg
            self.out_warp <<= self.out_warp_reg
            self.out_reg <<= self.out_reg_reg
            self.out_data <<= self.out_data_reg

        # ------------------------------------------------------------------
        # Sequential: issue stage, writeback, and long-latency pipelines
        # ------------------------------------------------------------------
        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.issue_valid <<= 0
                self.issue_warp <<= 0
                self.issue_opcode <<= 0
                self.issue_dst <<= 0
                self.issue_src0_data <<= 0
                self.issue_src1_data <<= 0
                self.issue_imm <<= 0

                for w in range(NUM_WARPS):
                    self.warp_busy[w] <<= 0
                    self.warp_active[w] <<= 1

                self.sfu_v0 <<= 0
                self.sfu_v1 <<= 0
                self.sfu_v2 <<= 0
                self.sfu_v3 <<= 0
                self.gemm_v0 <<= 0
                self.gemm_v1 <<= 0
                self.gemm_v2 <<= 0
                self.gemm_v3 <<= 0

            with Else():
                # Issue new instruction when accepted.
                self.issue_valid <<= self.issue_accept
                self.issue_warp <<= self.dec_warp
                self.issue_opcode <<= self.dec_opcode
                self.issue_dst <<= self.dec_dst
                self.issue_src0_data <<= self.rf_rd0_data
                self.issue_src1_data <<= self.rf_rd1_data
                self.issue_imm <<= self.dec_imm

                # Update warp busy: set to latency when a long-latency op is
                # issued, otherwise clear after the single-cycle execute.
                for w in range(NUM_WARPS):
                    with If(self.issue_accept & (self.dec_warp == w)):
                        op = self.dec_opcode
                        with If((op == OP_SFU_RSQRT) | (op == OP_GEMM_MATMUL)):
                            self.warp_busy[w] <<= self.SFU_LATENCY
                        with Else():
                            self.warp_busy[w] <<= 0
                    with Else():
                        with If(self.warp_busy[w] > 0):
                            self.warp_busy[w] <<= self.warp_busy[w] - 1

                # Advance long-latency pipelines.
                self.sfu_v3 <<= self.sfu_v2
                self.sfu_warp3 <<= self.sfu_warp2
                self.sfu_dst3 <<= self.sfu_dst2
                self.sfu_data3 <<= self.sfu_data2

                self.sfu_v2 <<= self.sfu_v1
                self.sfu_warp2 <<= self.sfu_warp1
                self.sfu_dst2 <<= self.sfu_dst1
                self.sfu_data2 <<= self.sfu_data1

                self.sfu_v1 <<= self.sfu_v0
                self.sfu_warp1 <<= self.sfu_warp0
                self.sfu_dst1 <<= self.sfu_dst0
                self.sfu_data1 <<= self.sfu_data0

                self.sfu_v0 <<= self.issue_valid & (self.issue_opcode == OP_SFU_RSQRT)
                self.sfu_warp0 <<= self.issue_warp
                self.sfu_dst0 <<= self.issue_dst
                self.sfu_data0 <<= self.sfu_result

                self.gemm_v3 <<= self.gemm_v2
                self.gemm_warp3 <<= self.gemm_warp2
                self.gemm_dst3 <<= self.gemm_dst2
                self.gemm_data3 <<= self.gemm_data2

                self.gemm_v2 <<= self.gemm_v1
                self.gemm_warp2 <<= self.gemm_warp1
                self.gemm_dst2 <<= self.gemm_dst1
                self.gemm_data2 <<= self.gemm_data1

                self.gemm_v1 <<= self.gemm_v0
                self.gemm_warp1 <<= self.gemm_warp0
                self.gemm_dst1 <<= self.gemm_dst0
                self.gemm_data1 <<= self.gemm_data0

                self.gemm_v0 <<= self.issue_valid & (self.issue_opcode == OP_GEMM_MATMUL)
                self.gemm_warp0 <<= self.issue_warp
                self.gemm_dst0 <<= self.issue_dst
                self.gemm_data0 <<= self.gemm_result

        # ------------------------------------------------------------------
        # Register file writeback and shared memory write
        # ------------------------------------------------------------------
        @self.seq(self.clk, self.rst)
        def _writeback_seq():
            with If(self.rst == 1):
                pass  # memories are initialized by init_zero
            with Else():
                for w in range(NUM_WARPS):
                    with If(self.wb_we & (self.wb_warp == w)):
                        self.reg_files[w][self.wb_reg] <<= self.wb_data

                with If(self.shared_wr_en):
                    self.shared_mem[self.shared_wr_addr] <<= self.shared_wr_data

                # Writeback long-latency pipeline tail.
                for w in range(NUM_WARPS):
                    with If(self.sfu_v3 & (self.sfu_warp3 == w)):
                        self.reg_files[w][self.sfu_dst3] <<= self.sfu_data3
                    with If(self.gemm_v3 & (self.gemm_warp3 == w)):
                        self.reg_files[w][self.gemm_dst3] <<= self.gemm_data3
