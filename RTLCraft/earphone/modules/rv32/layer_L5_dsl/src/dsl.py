"""L5 DSL module for the EarphoneRV32 core.

RTL-ready rtlgen description of the RV32IM 3-stage in-order processor.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Reg, Const, Array
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Elif, SRA
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template
from earphone.constraints import (
    attach_earphone_constraints,
    FunctionalConstraint,
    PowerConstraint,
)
from earphone.modules.rv32.layer_L1_behavior.src.behavior import (
    OPCODE_LOAD,
    OPCODE_STORE,
    OPCODE_IMM,
    OPCODE_REG,
    OPCODE_LUI,
    OPCODE_AUIPC,
    OPCODE_BRANCH,
    OPCODE_JAL,
    OPCODE_JALR,
    OPCODE_SYSTEM,
    FUNCT3_LB,
    FUNCT3_LH,
    FUNCT3_LW,
    FUNCT3_LBU,
    FUNCT3_LHU,
    FUNCT3_SB,
    FUNCT3_SH,
    FUNCT3_SW,
    FUNCT3_ADDI,
    FUNCT3_SLTI,
    FUNCT3_XORI,
    FUNCT3_ORI,
    FUNCT3_ANDI,
    FUNCT3_SLLI,
    FUNCT3_SRXI,
    FUNCT3_ADD,
    FUNCT3_SUB,
    FUNCT3_SLL,
    FUNCT3_SLT,
    FUNCT3_SLTU,
    FUNCT3_XOR,
    FUNCT3_SRL,
    FUNCT3_SRA,
    FUNCT3_OR,
    FUNCT3_AND,
    FUNCT3_BEQ,
    FUNCT3_BNE,
    FUNCT3_BLT,
    FUNCT3_BGE,
    FUNCT3_BLTU,
    FUNCT3_BGEU,
    FUNCT7_DEFAULT,
    FUNCT7_SUB,
    FUNCT7_SRA,
    FUNCT7_SRAI,
    FUNCT7_MULDIV,
)


class EarphoneRV32(Module):
    """3-stage RV32IM core for the smart earphone SoC.

    Stages: IF -> ID/EX -> WB
    Interfaces: simple memory bus (no cache), byte write enable.
    M-extension multiplier/divider is multi-cycle (iterative divider).
    """

    def __init__(self):
        super().__init__("earphone_rv32")
        XLEN = 32

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Instruction memory interface
        self.imem_addr = Output(XLEN, "imem_addr")
        self.imem_rdata = Input(XLEN, "imem_rdata")
        self.imem_req = Output(1, "imem_req")
        self.imem_gnt = Input(1, "imem_gnt")

        # Data memory interface
        self.dmem_addr = Output(XLEN, "dmem_addr")
        self.dmem_wdata = Output(XLEN, "dmem_wdata")
        self.dmem_rdata = Input(XLEN, "dmem_rdata")
        self.dmem_we = Output(4, "dmem_we")
        self.dmem_req = Output(1, "dmem_req")
        self.dmem_gnt = Input(1, "dmem_gnt")
        self.dmem_valid = Input(1, "dmem_valid")

        # Status
        self.retire_valid = Output(1, "retire_valid")
        self.retire_rd = Output(5, "retire_rd")
        self.retire_result = Output(XLEN, "retire_result")

        # Pipeline registers
        self.pc_reg = Reg(XLEN, "pc_reg", init_value=0x1000)
        self.fetch_valid = Reg(1, "fetch_valid", init_value=0)
        self.fetch_instr = Reg(XLEN, "fetch_instr", init_value=0)
        self.exec_valid = Reg(1, "exec_valid", init_value=0)
        self.exec_instr = Reg(XLEN, "exec_instr", init_value=0)
        self.exec_pc = Reg(XLEN, "exec_pc", init_value=0)
        self.wb_valid = Reg(1, "wb_valid", init_value=0)
        self.wb_wb_en = Reg(1, "wb_wb_en", init_value=0)
        self.wb_rd = Reg(5, "wb_rd", init_value=0)
        self.wb_result = Reg(XLEN, "wb_result", init_value=0)

        # Register file
        self.rf = Array(XLEN, 32, "rf")

        # M-extension state
        self.muldiv_busy = Reg(1, "muldiv_busy", init_value=0)
        self.muldiv_count = Reg(6, "muldiv_count", init_value=0)
        self.muldiv_result = Wire(XLEN, "muldiv_result")
        self.muldiv_rd = Reg(5, "muldiv_rd", init_value=0)
        self.muldiv_wb_en = Reg(1, "muldiv_wb_en", init_value=0)

        # Iterative divider state (area-optimized DIV/DIVU/REM/REMU)
        self.div_dividend = Reg(XLEN, "div_dividend", init_value=0)
        self.div_dividend_orig = Reg(XLEN, "div_dividend_orig", init_value=0)
        self.div_divisor = Reg(XLEN, "div_divisor", init_value=0)
        self.div_quotient = Reg(XLEN, "div_quotient", init_value=0)
        self.div_remainder = Reg(XLEN, "div_remainder", init_value=0)
        self.div_dividend_sign = Reg(1, "div_dividend_sign", init_value=0)
        self.div_divisor_sign = Reg(1, "div_divisor_sign", init_value=0)
        self.div_is_rem = Reg(1, "div_is_rem", init_value=0)
        self.div_result = Wire(XLEN, "div_result")
        self.div_done = Reg(1, "div_done", init_value=0)
        self.div_restart_block = Reg(1, "div_restart_block", init_value=0)

        # Combinational decode wires (declared first so seq can reference)
        self.exec_alu_result = Wire(XLEN, "exec_alu_result")
        self.exec_wb_en = Wire(1, "exec_wb_en")
        self.exec_rd = Wire(5, "exec_rd")
        self.exec_mem_read = Wire(1, "exec_mem_read")
        self.exec_mem_write = Wire(1, "exec_mem_write")
        self.exec_mem_addr = Wire(XLEN, "exec_mem_addr")
        self.exec_mem_wdata = Wire(XLEN, "exec_mem_wdata")
        self.branch_taken = Wire(1, "branch_taken")
        self.branch_target = Wire(XLEN, "branch_target")
        self.core_stall = Wire(1, "core_stall")
        self.is_divrem = Wire(1, "is_divrem")
        self.is_mul_only = Wire(1, "is_mul_only")
        self.diff = Wire(XLEN, "diff")
        self.div_overflow = Wire(1, "div_overflow")
        self.div_by_zero = Wire(1, "div_by_zero")
        self.shifted_rem = Wire(XLEN + 1, "shifted_rem")
        self.mul_full = Wire(XLEN * 2, "mul_full")
        self.mul_hsu_full = Wire(XLEN * 2, "mul_hsu_full")
        self.mul_hu_full = Wire(XLEN * 2, "mul_hu_full")

        # Decode current execute instruction
        instr = self.exec_instr
        opcode = instr[6:0]
        funct3 = instr[14:12]
        funct7 = instr[31:25]
        rs1 = instr[19:15]
        rs2 = instr[24:20]
        rd_d = instr[11:7]

        # Immediates
        imm_i = Cat(Rep(instr[31], XLEN - 12), instr[31:20])
        imm_s = Cat(Rep(instr[31], XLEN - 12), instr[31:25], instr[11:7])
        imm_b = Cat(Rep(instr[31], XLEN - 13), instr[31], instr[7], instr[30:25], instr[11:8], Const(0, 1))
        imm_u = Cat(instr[31:12], Const(0, 12))
        imm_j = Cat(Rep(instr[31], XLEN - 21), instr[31], instr[19:12], instr[20], instr[30:21], Const(0, 1))

        with self.comb:
            # Forwarding from writeback stage
            wb_fwd_valid = self.wb_valid & self.wb_wb_en
            wb_fwd_result = self.wb_result
            wb_fwd_rd = self.wb_rd
            ra = Mux((rs1 == wb_fwd_rd) & wb_fwd_valid, wb_fwd_result, self.rf[rs1])
            rb = Mux((rs2 == wb_fwd_rd) & wb_fwd_valid, wb_fwd_result, self.rf[rs2])

            # Control signals
            is_op_imm = (opcode == Const(OPCODE_IMM, 7))
            is_op = (opcode == Const(OPCODE_REG, 7))
            is_muldiv = is_op & (funct7 == Const(FUNCT7_MULDIV, 7))
            self.is_divrem <<= is_muldiv & (funct3[2] == 1)
            self.is_mul_only <<= is_muldiv & (funct3[2] == 0)
            is_load = (opcode == Const(OPCODE_LOAD, 7))
            is_store = (opcode == Const(OPCODE_STORE, 7))
            is_lui = (opcode == Const(OPCODE_LUI, 7))
            is_auipc = (opcode == Const(OPCODE_AUIPC, 7))
            is_jal = (opcode == Const(OPCODE_JAL, 7))
            is_jalr = (opcode == Const(OPCODE_JALR, 7))
            is_branch = (opcode == Const(OPCODE_BRANCH, 7))

            # ALU op decode
            add_sel = (funct3 == Const(FUNCT3_ADD, 3)) & (is_op_imm | (is_op & (funct7 == Const(FUNCT7_DEFAULT, 7))))
            sub_sel = (funct3 == Const(FUNCT3_SUB, 3)) & is_op & (funct7 == Const(FUNCT7_SUB, 7))
            xor_sel = (funct3 == Const(FUNCT3_XOR, 3)) & (is_op_imm | is_op)
            or_sel = (funct3 == Const(FUNCT3_OR, 3)) & (is_op_imm | is_op)
            and_sel = (funct3 == Const(FUNCT3_AND, 3)) & (is_op_imm | is_op)
            sll_sel = (funct3 == Const(FUNCT3_SLL, 3)) & (is_op_imm | is_op)
            srl_sel = (funct3 == Const(FUNCT3_SRL, 3)) & (is_op_imm | is_op) & (funct7 == Const(FUNCT7_DEFAULT, 7))
            sra_sel = (funct3 == Const(FUNCT3_SRA, 3)) & (is_op_imm | is_op) & (funct7 == Const(FUNCT7_SRA, 7))
            slt_sel = (funct3 == Const(FUNCT3_SLT, 3)) & (is_op_imm | is_op)
            sltu_sel = (funct3 == Const(FUNCT3_SLTU, 3)) & (is_op_imm | is_op)

            imm_shamt = imm_i[4:0]
            rb_shamt = rb[4:0]

            # R-type / I-type ALU result
            alu_in2 = Mux(is_op_imm, imm_i, rb)
            shamt = Mux(is_op_imm, imm_shamt, rb_shamt)

            alu_result = Mux(add_sel | sub_sel, Mux(sub_sel, ra - rb, ra + alu_in2),
                     Mux(xor_sel, ra ^ alu_in2,
                     Mux(or_sel, ra | alu_in2,
                     Mux(and_sel, ra & alu_in2,
                     Mux(sll_sel, ra << shamt,
                     Mux(srl_sel, ra >> shamt,
                     Mux(sra_sel, SRA(ra, shamt),
                     Mux(slt_sel, Mux(SRA(ra - alu_in2, XLEN - 1), Const(1, XLEN), Const(0, XLEN)),
                     Mux(sltu_sel, Mux((ra < alu_in2), Const(1, XLEN), Const(0, XLEN)),
                     Const(0, XLEN))))))))))

            self.exec_alu_result <<= Mux(is_lui, imm_u,
                            Mux(is_auipc, self.exec_pc + imm_u,
                            Mux(is_jal, self.exec_pc + Const(4, XLEN),
                            Mux(is_jalr, ra + imm_i,
                            Mux(is_branch, self.exec_pc + imm_b,
                            Mux(is_load | is_store, self.exec_mem_addr,
                            Mux(is_muldiv, self.muldiv_result,
                            alu_result)))))))

            # Memory address / data
            self.exec_mem_addr <<= Mux(is_store, ra + imm_s, ra + imm_i)
            self.exec_mem_wdata <<= rb
            self.exec_mem_read <<= is_load
            self.exec_mem_write <<= is_store

            # Branch resolution (use wire for diff to avoid slice-on-binop)
            self.diff <<= ra - rb
            sign_diff = self.diff[XLEN - 1]
            beq_taken = is_branch & (funct3 == Const(FUNCT3_BEQ, 3)) & (ra == rb)
            bne_taken = is_branch & (funct3 == Const(FUNCT3_BNE, 3)) & (ra != rb)
            blt_taken = is_branch & (funct3 == Const(FUNCT3_BLT, 3)) & sign_diff
            bge_taken = is_branch & (funct3 == Const(FUNCT3_BGE, 3)) & ~sign_diff
            bltu_taken = is_branch & (funct3 == Const(FUNCT3_BLTU, 3)) & (ra < rb)
            bgeu_taken = is_branch & (funct3 == Const(FUNCT3_BGEU, 3)) & (ra >= rb)

            self.branch_taken <<= is_jal | is_jalr | beq_taken | bne_taken | blt_taken | bge_taken | bltu_taken | bgeu_taken
            self.branch_target <<= Mux(is_jalr, (ra + imm_i) & ~Const(1, XLEN),
                           Mux(is_branch, self.exec_pc + imm_b,
                           self.exec_pc + imm_j))

            # Writeback enable / destination
            self.exec_wb_en <<= (is_op_imm | (is_op & ~self.is_divrem) | is_load | is_lui | is_auipc | is_jal | is_jalr) & self.exec_valid
            self.exec_rd <<= rd_d

            # Stall on memory not ready, on muldiv, and while DIV/REM is in EX.
            # div_done temporarily releases the stall so the pipeline can advance.
            imem_stall = self.fetch_valid & ~self.imem_gnt
            dmem_stall = self.exec_valid & (self.exec_mem_read | self.exec_mem_write) & ~self.dmem_valid
            div_stall = self.exec_valid & self.is_divrem & ~self.div_done
            self.core_stall <<= imem_stall | dmem_stall | self.muldiv_busy | div_stall

            # Outputs
            self.imem_req <<= ~self.fetch_valid
            self.imem_addr <<= self.pc_reg
            self.dmem_req <<= self.exec_valid & (self.exec_mem_read | self.exec_mem_write) & ~dmem_stall
            self.dmem_addr <<= self.exec_mem_addr
            self.dmem_wdata <<= self.exec_mem_wdata
            self.dmem_we <<= Mux(self.exec_mem_write,
                                 Mux(funct3 == Const(FUNCT3_SB, 3), Const(0b0001, 4),
                                 Mux(funct3 == Const(FUNCT3_SH, 3), Const(0b0011, 4),
                                 Const(0b1111, 4))),
                                 Const(0, 4))
            self.retire_valid <<= (self.wb_valid & self.wb_wb_en) | self.div_done
            self.retire_rd <<= Mux(self.div_done, self.muldiv_rd, self.wb_rd)
            self.retire_result <<= Mux(self.div_done, self.div_result, self.wb_result)

        # core_clk_en disables pipeline register updates during stalls -> dynamic power reduction.
        # Declared here so the divider FSM can reference it for restart blocking.
        self.core_clk_en = Wire(1, "core_clk_en")
        with self.comb:
            self.core_clk_en <<= ~self.core_stall & ~self.muldiv_busy

        # Iterative divider FSM (area-optimized DIV/DIVU/REM/REMU)
        with self.comb:
            self.div_by_zero <<= (self.div_divisor == 0)
            # Signed overflow: MIN / -1
            self.div_overflow <<= self.div_dividend_sign & self.div_divisor_sign & \
                             (self.div_dividend == Const(0x80000000, XLEN)) & \
                             (self.div_divisor == Const(0xFFFFFFFF, XLEN))
            self.shifted_rem <<= (self.div_remainder << 1) | self.div_dividend[XLEN - 1]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.muldiv_busy <<= 0
                self.muldiv_count <<= 0
                self.muldiv_rd <<= 0
                self.muldiv_wb_en <<= 0
                self.div_dividend <<= 0
                self.div_dividend_orig <<= 0
                self.div_divisor <<= 0
                self.div_quotient <<= 0
                self.div_remainder <<= 0
                self.div_dividend_sign <<= 0
                self.div_divisor_sign <<= 0
                self.div_is_rem <<= 0
                self.div_done <<= 0
                self.div_restart_block <<= 0
            with Else():
                self.div_done <<= 0
                with If(self.muldiv_busy == 0):
                    with If(self.div_restart_block):
                        # Hold block until pipeline can advance (avoids re-starting same DIV)
                        self.div_restart_block <<= ~self.core_clk_en
                    with Elif(self.exec_valid & self.is_divrem):
                        # Capture operands and start iterative division
                        self.muldiv_busy <<= 1
                        self.muldiv_count <<= Const(31, 6)
                        self.muldiv_rd <<= rd_d
                        self.muldiv_wb_en <<= 1
                        self.div_is_rem <<= (funct3 == Const(6, 3)) | (funct3 == Const(7, 3))
                        is_signed = (funct3 == Const(4, 3)) | (funct3 == Const(6, 3))
                        self.div_dividend_sign <<= is_signed & ra[XLEN - 1]
                        self.div_divisor_sign <<= is_signed & rb[XLEN - 1]
                        # Keep original dividend for REM/REMU by-zero result.
                        self.div_dividend_orig <<= ra
                        # Absolute values for signed inputs
                        with If(is_signed & ra[XLEN - 1]):
                            self.div_dividend <<= (~ra + 1).as_uint()[XLEN - 1:0]
                        with Else():
                            self.div_dividend <<= ra
                        with If(is_signed & rb[XLEN - 1]):
                            self.div_divisor <<= (~rb + 1).as_uint()[XLEN - 1:0]
                        with Else():
                            self.div_divisor <<= rb
                        self.div_quotient <<= 0
                        self.div_remainder <<= 0
                with Else():
                    # Restoring division step (shifted_rem computed combinationally)
                    with If(self.shifted_rem >= self.div_divisor):
                        self.div_remainder <<= (self.shifted_rem - self.div_divisor)[XLEN - 1:0]
                        self.div_quotient <<= Cat(self.div_quotient[XLEN - 2:0], Const(1, 1))
                    with Else():
                        self.div_remainder <<= self.shifted_rem[XLEN - 1:0]
                        self.div_quotient <<= Cat(self.div_quotient[XLEN - 2:0], Const(0, 1))
                    self.div_dividend <<= self.div_dividend << 1
                    self.muldiv_count <<= self.muldiv_count - Const(1, 6)
                    with If(self.muldiv_count == 0):
                        self.muldiv_busy <<= 0
                        self.div_done <<= 1
                        self.div_restart_block <<= 1
                        # Direct RF writeback for divide instructions
                        with If(self.muldiv_rd != 0):
                            self.rf[self.muldiv_rd] <<= self.div_result

        # RV32M multiply/divide result
        # MUL* is combinational single-cycle; DIV/REM is iterative for area.
        # Operand isolation on multiplier when not executing M-extension.
        with self.comb:
            with If(is_muldiv):
                self.mul_full <<= ra * rb
                self.mul_hsu_full <<= ra.as_sint() * rb.as_uint()
                self.mul_hu_full <<= ra.as_uint() * rb.as_uint()
            with Else():
                self.mul_full <<= Const(0, XLEN * 2)
                self.mul_hsu_full <<= Const(0, XLEN * 2)
                self.mul_hu_full <<= Const(0, XLEN * 2)

            mul_lo = self.mul_full[XLEN - 1:0]
            mul_hi = self.mul_full[XLEN * 2 - 1:XLEN]
            mul_hsu = self.mul_hsu_full[XLEN * 2 - 1:XLEN]
            mul_hu = self.mul_hu_full[XLEN * 2 - 1:XLEN]

            div_res_signed = Mux(self.div_dividend_sign ^ self.div_divisor_sign,
                                 (~self.div_quotient + 1).as_uint()[XLEN - 1:0],
                                 self.div_quotient)
            rem_res_signed = Mux(self.div_dividend_sign,
                                 (~self.div_remainder + 1).as_uint()[XLEN - 1:0],
                                 self.div_remainder)

            self.div_result <<= Mux(self.div_by_zero,
                                    Mux(self.div_is_rem, self.div_dividend_orig, Const(0xFFFFFFFF, XLEN)),
                              Mux(self.div_overflow & ~self.div_is_rem,
                                    Const(0x80000000, XLEN),
                                    Mux(self.div_is_rem, rem_res_signed, div_res_signed)))

            muldiv_res = Mux(funct3 == Const(0, 3), mul_lo,
                       Mux(funct3 == Const(1, 3), mul_hi,
                       Mux(funct3 == Const(2, 3), mul_hsu,
                       Mux(funct3 == Const(3, 3), mul_hu,
                       Mux(self.div_is_rem, rem_res_signed, div_res_signed)))))
            self.muldiv_result <<= muldiv_res

        # Main pipeline sequential logic with clock-gating on stall
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.pc_reg <<= Const(0x1000, XLEN)
                self.fetch_valid <<= 0
                self.fetch_instr <<= 0
                self.exec_valid <<= 0
                self.exec_instr <<= 0
                self.exec_pc <<= 0
                self.wb_valid <<= 0
                self.wb_wb_en <<= 0
                self.wb_rd <<= 0
                self.wb_result <<= 0
            with Else():
                with If(self.core_clk_en):
                    with If(self.branch_taken & self.exec_valid):
                        self.pc_reg <<= self.branch_target
                        self.fetch_valid <<= 0
                        self.exec_valid <<= 0
                        self.wb_valid <<= 0
                    with Else():
                        self.pc_reg <<= self.pc_reg + Const(4, XLEN)
                        self.fetch_valid <<= self.imem_gnt
                        with If(self.imem_gnt):
                            self.fetch_instr <<= self.imem_rdata
                        self.exec_valid <<= self.fetch_valid
                        with If(self.fetch_valid):
                            self.exec_instr <<= self.fetch_instr
                            self.exec_pc <<= self.pc_reg
                        self.wb_valid <<= self.exec_valid
                        with If(self.exec_valid):
                            # DIV/REM write back later from divider FSM
                            self.wb_wb_en <<= self.exec_wb_en & ~self.is_divrem
                            self.wb_rd <<= self.exec_rd
                            self.wb_result <<= self.exec_alu_result
                with Else():
                    # During stalls, clear wb_valid so retire_valid remains a one-cycle pulse
                    self.wb_valid <<= 0

                # Register file writeback (non-DIV/REM instructions)
                with If(self.wb_valid & self.wb_wb_en & (self.wb_rd != 0)):
                    self.rf[self.wb_rd] <<= self.wb_result

        tpl = ModuleDocTemplate(
            source="earphone/modules/rv32/layer_L5_dsl/src/dsl.py",
            description="RV32IM 3-stage in-order core for smart earphone SoC.",
            author="RTLCraft Agent", version="0.1",
            timing="3-stage pipeline with stall clock-gating; MUL* single-cycle, DIV/REM 32-cycle iterative.",
        )
        fill_doc_template(tpl, self)

        # Attach cross-layer constraints (SpecIR layer)
        attach_earphone_constraints(
            self,
            FunctionalConstraint(
                uid="EARP-RV32-001",
                name="RV32M_DIV_ZERO",
                layer="SpecIR",
                expr="DIV/REM by zero -> -1; DIVU/REMU by zero -> MAX/dvd",
                target="EarphoneRV32",
                source_ref="earphone/design_spec.md#RV32M",
            ),
        )
        attach_earphone_constraints(
            self,
            PowerConstraint(
                uid="EARP-RV32-002",
                name="CPU_ACTIVE_POWER",
                layer="SpecIR",
                expr="< 0.5",
                unit="mW/MHz",
                target="EarphoneRV32",
                source_ref="earphone/design_spec.md#power",
            ),
        )
        # Artificially aggressive constraint to demonstrate backward feedback loop.
        attach_earphone_constraints(
            self,
            PowerConstraint(
                uid="EARP-RV32-003",
                name="CPU_POWER_BUDGET_STRICT",
                layer="SpecIR",
                expr="< 0.1",
                unit="mW/MHz",
                target="EarphoneRV32",
                source_ref="earphone/design_spec.md#power",
                metadata={"demo": "unachievable_without_power_domain"},
            ),
        )


__all__ = ["EarphoneRV32"]
