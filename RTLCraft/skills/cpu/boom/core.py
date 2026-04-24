"""
BOOM-style Out-of-Order RISC-V Core

Top-level integration of:
  - Fetch Unit + Branch Predictor
  - Decode Unit (RV32I + CSR)
  - Rename Unit
  - Distributed Reservation Stations (ALU / MEM / MUL)
  - Physical Register File
  - ALU / MUL / LSU Execution Units
  - CSR File
  - Reorder Buffer

This is a simplified educational microarchitecture demonstrating
out-of-order execution concepts using the rtlgen framework.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux

# Frontend
from skills.cpu.boom.frontend.fetch_unit import FetchUnit
from skills.cpu.boom.frontend.branch_predictor import BranchPredictor
from skills.cpu.boom.frontend.decode_unit import DecodeUnit

# Backend
from skills.cpu.boom.backend.rename import RenameUnit
from skills.cpu.boom.backend.reservation_station import ReservationStation
from skills.cpu.boom.backend.physical_regfile import PhysicalRegFile
from skills.cpu.boom.backend.execution_units import ALU, Multiplier
from skills.cpu.boom.backend.reorder_buffer import ReorderBuffer
from skills.cpu.boom.backend.lsu import LSU
from skills.cpu.boom.backend.csr_file import CSRFile
from skills.cpu.boom.backend.dcache import DCache


class BOOMCore(Module):
    """Top-level BOOM-style OoO core."""

    def __init__(
        self,
        xlen: int = 32,
        fetch_width: int = 2,
        rob_entries: int = 16,
        rs_entries: int = 8,
        num_pregs: int = 64,
        name: str = "BOOMCore",
    ):
        super().__init__(name)
        self.xlen = xlen
        self.fetch_width = fetch_width
        self.preg_bits = max(num_pregs.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Memory interface (unified I$/D$ for simplicity)
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(xlen, "mem_req_addr")
        self.mem_req_wdata = Output(xlen, "mem_req_wdata")
        self.mem_req_we = Output(1, "mem_req_we")
        self.mem_resp_valid = Input(1, "mem_resp_valid")
        self.mem_resp_data = Input(xlen, "mem_resp_data")

        # External interrupt
        self.irq = Input(1, "irq")

        # Debug / status
        self.commit_valid = Output(fetch_width, "commit_valid")
        self.commit_pc = Vector(xlen, fetch_width, "commit_pc", vtype=Output)

        # =====================================================================
        # Submodules
        # =====================================================================
        self.fetch_unit = FetchUnit(xlen=xlen, fetch_width=fetch_width, name="FetchUnit")
        self.bp = BranchPredictor(bht_entries=64, btb_entries=16, ras_depth=8, xlen=xlen, name="BranchPredictor")
        self.decode = DecodeUnit(xlen=xlen, width=fetch_width, name="DecodeUnit")
        self.rename = RenameUnit(num_pregs=num_pregs, width=fetch_width, name="RenameUnit")
        self.rob = ReorderBuffer(num_entries=rob_entries, num_enq=fetch_width, preg_bits=self.preg_bits, xlen=xlen, name="ROB")
        # Distributed reservation stations
        self.rs_alu = ReservationStation(num_entries=rs_entries, num_wakeup=4, preg_bits=self.preg_bits, xlen=xlen, name="RS_ALU")
        self.rs_mem = ReservationStation(num_entries=rs_entries, num_wakeup=4, preg_bits=self.preg_bits, xlen=xlen, name="RS_MEM")
        self.rs_mul = ReservationStation(num_entries=rs_entries, num_wakeup=4, preg_bits=self.preg_bits, xlen=xlen, name="RS_MUL")
        self.prf = PhysicalRegFile(num_pregs=num_pregs, num_read=6, num_write=4, xlen=xlen, name="PRF")
        self.alu = ALU(xlen=xlen, name="ALU")
        self.mul = Multiplier(xlen=xlen, name="Multiplier")
        self.lsu = LSU(xlen=xlen, lq_entries=8, sq_entries=8, name="LSU")
        self.dcache = DCache(xlen=xlen, num_sets=4, name="DCache")
        self.csr = CSRFile(xlen=xlen, name="CSRFile")

        # =====================================================================
        # Frontend: Fetch + Branch Predictor
        # =====================================================================
        # LSU -> DCache -> Memory
        self.dcache.clk <<= self.clk
        self.dcache.rst_n <<= self.rst_n
        self.dcache.req_valid <<= self.lsu.mem_req_valid
        self.dcache.req_addr <<= self.lsu.mem_req_addr
        self.dcache.req_we <<= self.lsu.mem_req_we
        self.dcache.req_wdata <<= self.lsu.mem_req_wdata
        self.lsu.mem_resp_valid <<= self.dcache.resp_valid
        self.lsu.mem_resp_data <<= self.dcache.resp_data

        self.mem_req_valid <<= self.dcache.mem_req_valid
        self.mem_req_addr <<= self.dcache.mem_req_addr
        self.mem_req_wdata <<= self.dcache.mem_req_wdata
        self.mem_req_we <<= self.dcache.mem_req_we
        self.dcache.mem_resp_valid <<= self.mem_resp_valid
        self.dcache.mem_resp_data <<= self.mem_resp_data

        self.fetch_unit.clk <<= self.clk
        self.fetch_unit.rst_n <<= self.rst_n
        self.fetch_unit.icache_resp_valid <<= self.mem_resp_valid
        self.fetch_unit.icache_resp_data <<= self.mem_resp_data
        self.fetch_unit.fetch_ready <<= self.rename.ready_out
        # Exception redirect: ROB flush / CSR trap / MRET all redirect fetch
        self.redirect_valid_mux = Wire(1, "redirect_valid_mux")
        self.redirect_pc_mux = Wire(xlen, "redirect_pc_mux")

        @self.comb
        def _redirect_mux():
            self.redirect_valid_mux <<= self.rob.redirect_valid
            self.redirect_pc_mux <<= self.rob.redirect_pc
            with If(self.csr.trap_valid):
                self.redirect_valid_mux <<= 1
                self.redirect_pc_mux <<= self.csr.trap_vector
            with If(self.csr.mret_valid):
                self.redirect_valid_mux <<= 1
                self.redirect_pc_mux <<= self.csr.mepc_out

        self.fetch_unit.redirect_valid <<= self.redirect_valid_mux
        self.fetch_unit.redirect_pc <<= self.redirect_pc_mux
        self.rob.exception_valid <<= self.csr.trap_valid | self.csr.mret_valid
        self.rob.exception_rob_idx <<= 0  # simplified: flush all

        self.bp.clk <<= self.clk
        self.bp.rst_n <<= self.rst_n
        self.bp.pc <<= self.fetch_unit.bp_pc
        self.bp.predict_valid <<= self.fetch_unit.bp_valid
        self.fetch_unit.bp_taken <<= self.bp.predict_taken
        self.fetch_unit.bp_target <<= self.bp.predict_target

        # =====================================================================
        # Decode
        # =====================================================================
        self.decode.clk <<= self.clk
        self.decode.rst_n <<= self.rst_n

        for i in range(fetch_width):
            self.decode.fetch_valid[i] <<= self.fetch_unit.fetch_valid & (self.fetch_unit.fetch_instrs[i] != 0)
            self.decode.fetch_instr[i] <<= self.fetch_unit.fetch_instrs[i]
        self.decode.fetch_pc <<= self.fetch_unit.fetch_pc

        # =====================================================================
        # Rename
        # =====================================================================
        self.rename.clk <<= self.clk
        self.rename.rst_n <<= self.rst_n

        for i in range(fetch_width):
            self.rename.dec_valid[i] <<= self.decode.dec_valid[i]
            self.rename.dec_rs1[i] <<= self.decode.dec_rs1[i]
            self.rename.dec_rs2[i] <<= self.decode.dec_rs2[i]
            self.rename.dec_rd[i] <<= self.decode.dec_rd[i]
            self.rename.dec_need_rs1[i] <<= self.decode.dec_need_rs1[i]
            self.rename.dec_need_rs2[i] <<= self.decode.dec_need_rs2[i]
            self.rename.dec_need_rd[i] <<= self.decode.dec_need_rd[i]

        for i in range(fetch_width):
            self.rename.commit_valid[i] <<= self.rob.commit_valid[i]
            self.rename.commit_prd_old[i] <<= self.rob.commit_prd_old[i]
        self.rename.rollback_valid <<= self.rob.redirect_valid

        # =====================================================================
        # ROB Enqueue (Dispatch)
        # =====================================================================
        self.rob.clk <<= self.clk
        self.rob.rst_n <<= self.rst_n

        for i in range(fetch_width):
            self.rob.enq_valid[i] <<= self.rename.ren_valid[i]
            self.rob.enq_prd[i] <<= self.rename.prd[i]
            self.rob.enq_prd_old[i] <<= self.rename.prd_old[i]
            self.rob.enq_pc[i] <<= self.decode.dec_pc[i]
            self.rob.enq_is_branch[i] <<= self.decode.dec_is_branch[i]

        # ROB Writeback: track which FU wrote back
        self.rob.wb_valid[0] <<= self.alu.out_valid
        self.rob.wb_valid[1] <<= self.mul.out_valid
        self.rob.wb_valid[2] <<= self.lsu.wb_valid

        self.commit_valid <<= self.rob.commit_valid
        for i in range(fetch_width):
            self.commit_pc[i] <<= self.rob.commit_pc[i]

        # =====================================================================
        # CSR File connections
        # =====================================================================
        self.csr.clk <<= self.clk
        self.csr.rst_n <<= self.rst_n
        self.csr.irq <<= self.irq
        self.csr.timer_irq <<= 0
        self.csr.sw_irq <<= 0

        # =====================================================================
        # CSR / Exception handling at commit
        # =====================================================================
        self.any_ecall = Wire(1, "any_ecall")
        self.any_ebreak = Wire(1, "any_ebreak")
        self.any_mret = Wire(1, "any_mret")
        self.any_csr = Wire(1, "any_csr")
        self.csr_wdata_val = Wire(xlen, "csr_wdata_val")
        self.csr_op_val = Wire(2, "csr_op_val")
        self.csr_addr_val = Wire(12, "csr_addr_val")

        @self.comb
        def _trap_detect():
            self.any_ecall <<= 0
            self.any_ebreak <<= 0
            self.any_mret <<= 0
            self.any_csr <<= 0
            self.csr_wdata_val <<= 0
            self.csr_op_val <<= 0
            self.csr_addr_val <<= 0
            for i in range(fetch_width):
                with If(self.rob.commit_valid[i]):
                    with If(self.decode.dec_is_ecall[i]):
                        self.any_ecall <<= 1
                    with If(self.decode.dec_is_ebreak[i]):
                        self.any_ebreak <<= 1
                    with If(self.decode.dec_is_mret[i]):
                        self.any_mret <<= 1
                    with If(self.decode.dec_is_csr[i]):
                        self.any_csr <<= 1
                        # For CSRRxI, data is in dec_imm (zimm)
                        # For CSRRW/S/C, simplified: use dec_imm if use_imm is set,
                        # otherwise use rd value (simplified for demo)
                        self.csr_wdata_val <<= self.decode.dec_imm[i]
                        self.csr_op_val <<= self.decode.dec_alu_op[i][1:0]
                        self.csr_addr_val <<= self.decode.dec_csr_addr[i]

        self.csr.trap_valid <<= self.any_ecall | self.any_ebreak
        self.csr.trap_pc <<= self.rob.commit_pc[0]
        self.csr.trap_cause <<= Mux(self.any_ebreak, 3, 11)
        self.csr.mret_valid <<= self.any_mret

        self.csr.csr_we <<= self.any_csr
        self.csr.csr_wdata <<= self.csr_wdata_val
        self.csr.csr_op <<= self.csr_op_val

        # CSR read/write address mux (must be in one comb block to avoid assign+always conflict)
        self.csr_re_wire = Wire(1, "csr_re_wire")
        self.csr_addr_wire = Wire(12, "csr_addr_wire")

        @self.comb
        def _csr_access():
            self.csr_re_wire <<= 0
            self.csr_addr_wire <<= 0
            for i in range(fetch_width):
                with If(self.decode.dec_is_csr[i]):
                    self.csr_re_wire <<= 1
                    self.csr_addr_wire <<= self.decode.dec_csr_addr[i]
            # CSR write at commit overrides address
            with If(self.any_csr):
                self.csr_addr_wire <<= self.csr_addr_val

        self.csr.csr_re <<= self.csr_re_wire
        self.csr.csr_addr <<= self.csr_addr_wire

        # =====================================================================
        # Dispatch to distributed Reservation Stations
        # =====================================================================
        for rs in [self.rs_alu, self.rs_mem, self.rs_mul]:
            rs.clk <<= self.clk
            rs.rst_n <<= self.rst_n

        # Dispatch wires for each RS
        self.disp_alu_valid = Wire(1, "disp_alu_valid")
        self.disp_alu_prs1 = Wire(self.preg_bits, "disp_alu_prs1")
        self.disp_alu_prs2 = Wire(self.preg_bits, "disp_alu_prs2")
        self.disp_alu_prd = Wire(self.preg_bits, "disp_alu_prd")
        self.disp_alu_op = Wire(4, "disp_alu_op")

        self.disp_mem_valid = Wire(1, "disp_mem_valid")
        self.disp_mem_prs1 = Wire(self.preg_bits, "disp_mem_prs1")
        self.disp_mem_prs2 = Wire(self.preg_bits, "disp_mem_prs2")
        self.disp_mem_prd = Wire(self.preg_bits, "disp_mem_prd")
        self.disp_mem_op = Wire(4, "disp_mem_op")

        self.disp_mul_valid = Wire(1, "disp_mul_valid")
        self.disp_mul_prs1 = Wire(self.preg_bits, "disp_mul_prs1")
        self.disp_mul_prs2 = Wire(self.preg_bits, "disp_mul_prs2")
        self.disp_mul_prd = Wire(self.preg_bits, "disp_mul_prd")
        self.disp_mul_op = Wire(4, "disp_mul_op")

        # Multi-instruction dispatch: scan all fetch_width slots and
        # route each valid instruction to its corresponding RS if space available.
        # Simplified: each RS accepts at most 1 instruction per cycle.
        @self.comb
        def _dispatch():
            # Defaults
            self.disp_alu_valid <<= 0
            self.disp_alu_prs1 <<= 0
            self.disp_alu_prs2 <<= 0
            self.disp_alu_prd <<= 0
            self.disp_alu_op <<= 0
            self.disp_mem_valid <<= 0
            self.disp_mem_prs1 <<= 0
            self.disp_mem_prs2 <<= 0
            self.disp_mem_prd <<= 0
            self.disp_mem_op <<= 0
            self.disp_mul_valid <<= 0
            self.disp_mul_prs1 <<= 0
            self.disp_mul_prs2 <<= 0
            self.disp_mul_prd <<= 0
            self.disp_mul_op <<= 0

            alu_taken = 0
            mem_taken = 0
            mul_taken = 0

            for i in range(fetch_width):
                valid = (
                    self.rename.ren_valid[i]
                    & ~self.decode.dec_is_csr[i]
                    & ~self.decode.dec_is_ecall[i]
                    & ~self.decode.dec_is_ebreak[i]
                    & ~self.decode.dec_is_mret[i]
                )
                is_alu = self.decode.dec_is_alu[i] | self.decode.dec_is_branch[i] | self.decode.dec_is_jump[i]
                is_mem = self.decode.dec_is_load[i] | self.decode.dec_is_store[i]
                is_mul = self.decode.dec_is_mul[i]

                with If(valid & is_alu & ~alu_taken & self.rs_alu.enq_ready):
                    self.disp_alu_valid <<= 1
                    self.disp_alu_prs1 <<= self.rename.prs1[i]
                    self.disp_alu_prs2 <<= self.rename.prs2[i]
                    self.disp_alu_prd <<= self.rename.prd[i]
                    self.disp_alu_op <<= self.decode.dec_alu_op[i]
                    alu_taken = 1

                with If(valid & is_mem & ~mem_taken & self.rs_mem.enq_ready):
                    self.disp_mem_valid <<= 1
                    self.disp_mem_prs1 <<= self.rename.prs1[i]
                    self.disp_mem_prs2 <<= self.rename.prs2[i]
                    self.disp_mem_prd <<= self.rename.prd[i]
                    self.disp_mem_op <<= self.decode.dec_alu_op[i]
                    mem_taken = 1

                with If(valid & is_mul & ~mul_taken & self.rs_mul.enq_ready):
                    self.disp_mul_valid <<= 1
                    self.disp_mul_prs1 <<= self.rename.prs1[i]
                    self.disp_mul_prs2 <<= self.rename.prs2[i]
                    self.disp_mul_prd <<= self.rename.prd[i]
                    self.disp_mul_op <<= self.decode.dec_alu_op[i]
                    mul_taken = 1

        # Connect dispatch to ALU RS
        self.rs_alu.enq_valid <<= self.disp_alu_valid
        self.rs_alu.enq_prs1 <<= self.disp_alu_prs1
        self.rs_alu.enq_prs2 <<= self.disp_alu_prs2
        self.rs_alu.enq_prd <<= self.disp_alu_prd
        self.rs_alu.enq_prs1_busy <<= 0
        self.rs_alu.enq_prs2_busy <<= 0
        self.rs_alu.enq_op <<= self.disp_alu_op
        self.rs_alu.enq_fu_type <<= 0

        # Connect dispatch to MEM RS
        self.rs_mem.enq_valid <<= self.disp_mem_valid
        self.rs_mem.enq_prs1 <<= self.disp_mem_prs1
        self.rs_mem.enq_prs2 <<= self.disp_mem_prs2
        self.rs_mem.enq_prd <<= self.disp_mem_prd
        self.rs_mem.enq_prs1_busy <<= 0
        self.rs_mem.enq_prs2_busy <<= 0
        self.rs_mem.enq_op <<= self.disp_mem_op
        self.rs_mem.enq_fu_type <<= 0

        # Connect dispatch to MUL RS
        self.rs_mul.enq_valid <<= self.disp_mul_valid
        self.rs_mul.enq_prs1 <<= self.disp_mul_prs1
        self.rs_mul.enq_prs2 <<= self.disp_mul_prs2
        self.rs_mul.enq_prd <<= self.disp_mul_prd
        self.rs_mul.enq_prs1_busy <<= 0
        self.rs_mul.enq_prs2_busy <<= 0
        self.rs_mul.enq_op <<= self.disp_mul_op
        self.rs_mul.enq_fu_type <<= 0

        # =====================================================================
        # Wakeup from writeback (broadcast to all RS)
        # =====================================================================
        # Capture issued PRD for each FU
        self.issued_prd_alu = Reg(self.preg_bits, "issued_prd_alu")
        self.issued_prd_mem = Reg(self.preg_bits, "issued_prd_mem")
        self.issued_prd_mul = Reg(self.preg_bits, "issued_prd_mul")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _capture_issued():
            with If(self.rst_n == 0):
                self.issued_prd_alu <<= 0
                self.issued_prd_mem <<= 0
                self.issued_prd_mul <<= 0
            with Else():
                with If(self.rs_alu.issue_valid & self.rs_alu.issue_ready):
                    self.issued_prd_alu <<= self.rs_alu.issue_prd
                with If(self.rs_mem.issue_valid & self.rs_mem.issue_ready):
                    self.issued_prd_mem <<= self.rs_mem.issue_prd
                with If(self.rs_mul.issue_valid & self.rs_mul.issue_ready):
                    self.issued_prd_mul <<= self.rs_mul.issue_prd

        # Wakeup connections for ALU RS
        self.rs_alu.wakeup_valid[0] <<= self.alu.out_valid
        self.rs_alu.wakeup_valid[1] <<= self.mul.out_valid
        self.rs_alu.wakeup_valid[2] <<= self.lsu.wb_valid
        self.rs_alu.wakeup_valid[3] <<= self.lsu.forward_valid
        self.rs_alu.wakeup_prd[0] <<= self.issued_prd_alu
        self.rs_alu.wakeup_prd[1] <<= self.issued_prd_mul
        self.rs_alu.wakeup_prd[2] <<= self.issued_prd_mem
        self.rs_alu.wakeup_prd[3] <<= self.issued_prd_mem

        # Wakeup connections for MEM RS
        self.rs_mem.wakeup_valid[0] <<= self.alu.out_valid
        self.rs_mem.wakeup_valid[1] <<= self.mul.out_valid
        self.rs_mem.wakeup_valid[2] <<= self.lsu.wb_valid
        self.rs_mem.wakeup_valid[3] <<= self.lsu.forward_valid
        self.rs_mem.wakeup_prd[0] <<= self.issued_prd_alu
        self.rs_mem.wakeup_prd[1] <<= self.issued_prd_mul
        self.rs_mem.wakeup_prd[2] <<= self.issued_prd_mem
        self.rs_mem.wakeup_prd[3] <<= self.issued_prd_mem

        # Wakeup connections for MUL RS
        self.rs_mul.wakeup_valid[0] <<= self.alu.out_valid
        self.rs_mul.wakeup_valid[1] <<= self.mul.out_valid
        self.rs_mul.wakeup_valid[2] <<= self.lsu.wb_valid
        self.rs_mul.wakeup_valid[3] <<= self.lsu.forward_valid
        self.rs_mul.wakeup_prd[0] <<= self.issued_prd_alu
        self.rs_mul.wakeup_prd[1] <<= self.issued_prd_mul
        self.rs_mul.wakeup_prd[2] <<= self.issued_prd_mem
        self.rs_mul.wakeup_prd[3] <<= self.issued_prd_mem

        self.rs_alu.issue_ready <<= 1
        self.rs_mem.issue_ready <<= 1
        self.rs_mul.issue_ready <<= 1

        # =====================================================================
        # Physical Register File
        # =====================================================================
        self.prf.clk <<= self.clk
        self.prf.rst_n <<= self.rst_n

        # Read ports: ALU uses 0,1; MEM uses 2,3; MUL uses 4,5
        self.prf.raddr[0] <<= self.rs_alu.issue_prs1
        self.prf.raddr[1] <<= self.rs_alu.issue_prs2
        self.prf.raddr[2] <<= self.rs_mem.issue_prs1
        self.prf.raddr[3] <<= self.rs_mem.issue_prs2
        self.prf.raddr[4] <<= self.rs_mul.issue_prs1
        self.prf.raddr[5] <<= self.rs_mul.issue_prs2

        # Write ports
        self.prf.wen[0] <<= self.alu.out_valid
        self.prf.waddr[0] <<= self.issued_prd_alu
        self.prf.wdata[0] <<= self.alu.result
        self.prf.wen[1] <<= self.mul.out_valid
        self.prf.waddr[1] <<= self.issued_prd_mul
        self.prf.wdata[1] <<= self.mul.result
        self.prf.wen[2] <<= self.lsu.wb_valid
        self.prf.waddr[2] <<= self.issued_prd_mem
        self.prf.wdata[2] <<= self.lsu.wb_data
        self.prf.wen[3] <<= 0

        # =====================================================================
        # ALU
        # =====================================================================
        self.alu.clk <<= self.clk
        self.alu.rst_n <<= self.rst_n

        self.alu.valid <<= self.rs_alu.issue_valid & self.rs_alu.issue_ready
        self.alu.op <<= self.rs_alu.issue_op
        self.alu.rs1 <<= self.prf.rdata[0]
        self.alu.rs2 <<= self.prf.rdata[1]
        self.alu.imm <<= 0
        self.alu.use_imm <<= 0
        self.alu.pc <<= self.decode.dec_pc[0]  # simplified
        self.alu.is_branch <<= (self.rs_alu.issue_op >= 0b1010)

        # =====================================================================
        # Multiplier
        # =====================================================================
        self.mul.clk <<= self.clk
        self.mul.rst_n <<= self.rst_n

        self.mul.valid <<= self.rs_mul.issue_valid & self.rs_mul.issue_ready
        self.mul.rs1 <<= self.prf.rdata[4]
        self.mul.rs2 <<= self.prf.rdata[5]
        self.mul.is_signed <<= 0
        self.mul.high <<= 0

        # =====================================================================
        # LSU
        # =====================================================================
        self.lsu.clk <<= self.clk
        self.lsu.rst_n <<= self.rst_n

        self.lsu.issue_valid <<= self.rs_mem.issue_valid & self.rs_mem.issue_ready
        self.lsu.issue_is_load <<= ~self.decode.dec_is_store[0]  # simplified
        self.lsu.issue_addr <<= self.alu.result  # AGU result (simplified: reuse ALU)
        self.lsu.issue_wdata <<= self.prf.rdata[3]  # store data
        self.lsu.issue_size <<= self.decode.dec_mem_size[0]
        self.lsu.issue_signed <<= self.decode.dec_mem_signed[0]
        self.lsu.issue_sq_idx <<= 0

        self.lsu.commit_valid <<= self.rob.commit_valid[0] & self.decode.dec_is_store[0]
        self.lsu.commit_sq_idx <<= 0

        self.lsu.mem_resp_valid <<= self.mem_resp_valid
        self.lsu.mem_resp_data <<= self.mem_resp_data

        # =====================================================================
        # Branch mispredict update to BP
        # =====================================================================
        self.bp.update_valid <<= self.alu.out_valid & self.alu.br_taken_r
        self.bp.update_pc <<= self.decode.dec_pc[0]
        self.bp.update_taken <<= self.alu.br_taken_r
        self.bp.update_target <<= self.alu.br_target_r
        self.bp.update_is_branch <<= 0
        self.bp.update_is_ret <<= 0
        self.bp.update_is_call <<= 0
        self.bp.update_mispredict <<= 0
