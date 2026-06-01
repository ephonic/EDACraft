"""
Simple 4-Core NPU design for RTLCraft.
"""

from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Elif, Else, Switch, Mux, Cat, Rep, Const

XLEN       = 32
NLANE      = 8
VREGS      = 16
VLEN       = XLEN * NLANE
ACCW       = 64
INST_FIFO_DEPTH = 8

OP_NOP         = 0x0
OP_VLOAD       = 0x1
OP_VSTORE      = 0x2
OP_VMAC        = 0x3
OP_VADD        = 0x4
OP_VMAX0       = 0x5
OP_VMOV        = 0x6
OP_ACC_STORE   = 0x7
OP_SCALAR_LOAD = 0x8
OP_DONE        = 0xF


class NpuCore(Module):
    def __init__(self, name="npu_core"):
        super().__init__(name)

        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.inst_wr_en     = Input(1, "inst_wr_en")
        self.inst_wr_data   = Input(32, "inst_wr_data")
        self.inst_fifo_full = Output(1, "inst_fifo_full")

        self.mem_req   = Output(1, "mem_req")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.busy = Output(1, "busy")
        self.done = Output(1, "done")
        self.debug_acc0 = Output(ACCW, "debug_acc0")

        self.state    = Reg(4, "state")
        self.inst_reg = Reg(32, "inst_reg")
        self.acc      = Array(ACCW, NLANE, "acc")
        self.vrf      = Array(VLEN, VREGS, "vrf")

        self.ififo_wr_ptr = Reg(4, "ififo_wr_ptr")
        self.ififo_rd_ptr = Reg(4, "ififo_rd_ptr")
        self.ififo_count  = Reg(4, "ififo_count")
        self.ififo_mem    = Array(32, INST_FIFO_DEPTH, "ififo_mem")

        self.running = Reg(1, "running")

        opcode = Wire(4,  "opcode")
        rd     = Wire(4,  "rd")
        rs1    = Wire(4,  "rs1")
        rs2    = Wire(4,  "rs2")
        imm    = Wire(16, "imm")

        with self.comb:
            opcode <<= self.inst_reg[31:28]
            rd     <<= self.inst_reg[27:24]
            rs1    <<= self.inst_reg[23:20]
            rs2    <<= self.inst_reg[19:16]
            imm    <<= self.inst_reg[15:0]

        with self.comb:
            self.inst_fifo_full <<= (self.ififo_count == INST_FIFO_DEPTH)
            self.busy <<= (self.state != 0)
            self.done <<= (self.state == 0xF)
            self.debug_acc0 <<= self.acc[0]

        vmax0_result = Wire(VLEN, "vmax0_result")
        with self.comb:
            vmax0_result <<= Cat(
                Mux(self.vrf[rs1][8*XLEN-1], Const(0, XLEN), self.vrf[rs1][8*XLEN-1:7*XLEN]),
                Mux(self.vrf[rs1][7*XLEN-1], Const(0, XLEN), self.vrf[rs1][7*XLEN-1:6*XLEN]),
                Mux(self.vrf[rs1][6*XLEN-1], Const(0, XLEN), self.vrf[rs1][6*XLEN-1:5*XLEN]),
                Mux(self.vrf[rs1][5*XLEN-1], Const(0, XLEN), self.vrf[rs1][5*XLEN-1:4*XLEN]),
                Mux(self.vrf[rs1][4*XLEN-1], Const(0, XLEN), self.vrf[rs1][4*XLEN-1:3*XLEN]),
                Mux(self.vrf[rs1][3*XLEN-1], Const(0, XLEN), self.vrf[rs1][3*XLEN-1:2*XLEN]),
                Mux(self.vrf[rs1][2*XLEN-1], Const(0, XLEN), self.vrf[rs1][2*XLEN-1:1*XLEN]),
                Mux(self.vrf[rs1][1*XLEN-1], Const(0, XLEN), self.vrf[rs1][1*XLEN-1:0*XLEN]),
            )

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.state <<= 0
                self.inst_reg <<= 0
                self.ififo_wr_ptr <<= 0
                self.ififo_rd_ptr <<= 0
                self.ififo_count <<= 0
                self.running <<= 0
                self.acc[0] <<= 0; self.acc[1] <<= 0; self.acc[2] <<= 0; self.acc[3] <<= 0
                self.acc[4] <<= 0; self.acc[5] <<= 0; self.acc[6] <<= 0; self.acc[7] <<= 0
            with Else():
                with If(self.inst_wr_en & ~self.inst_fifo_full):
                    self.ififo_mem[self.ififo_wr_ptr] <<= self.inst_wr_data
                    self.ififo_wr_ptr <<= self.ififo_wr_ptr + 1
                    self.ififo_count  <<= self.ififo_count + 1

                with If(self.start & (self.state == 0) & (self.ififo_count != 0)):
                    self.running <<= 1

                with Switch(self.state) as sw:
                    with sw.case(0):
                        with If(self.running & (self.ififo_count != 0)):
                            self.state <<= 1
                    with sw.case(1):
                        self.inst_reg <<= self.ififo_mem[self.ififo_rd_ptr]
                        self.ififo_rd_ptr <<= self.ififo_rd_ptr + 1
                        self.ififo_count  <<= self.ififo_count - 1
                        self.state <<= 2
                    with sw.case(2):
                        with If(opcode == OP_NOP):
                            self.state <<= 0
                        with Elif(opcode == OP_DONE):
                            self.state <<= 0xF
                        with Elif((opcode == OP_VLOAD) | (opcode == OP_VSTORE)):
                            self.state <<= 3
                        with Else():
                            self.state <<= 4
                    with sw.case(3):
                        self.state <<= 5
                    with sw.case(5):
                        with If(self.mem_valid & self.mem_ready):
                            with If(opcode == OP_VLOAD):
                                self.vrf[rd] <<= self.mem_rdata
                            self.state <<= 0
                        with Else():
                            self.state <<= 5
                    with sw.case(4):
                        with If(opcode == OP_VMAC):
                            self.acc[0] <<= self.acc[0] + (self.vrf[rs1][1*XLEN-1:0*XLEN] * self.vrf[rs2][1*XLEN-1:0*XLEN])
                            self.acc[1] <<= self.acc[1] + (self.vrf[rs1][2*XLEN-1:1*XLEN] * self.vrf[rs2][2*XLEN-1:1*XLEN])
                            self.acc[2] <<= self.acc[2] + (self.vrf[rs1][3*XLEN-1:2*XLEN] * self.vrf[rs2][3*XLEN-1:2*XLEN])
                            self.acc[3] <<= self.acc[3] + (self.vrf[rs1][4*XLEN-1:3*XLEN] * self.vrf[rs2][4*XLEN-1:3*XLEN])
                            self.acc[4] <<= self.acc[4] + (self.vrf[rs1][5*XLEN-1:4*XLEN] * self.vrf[rs2][5*XLEN-1:4*XLEN])
                            self.acc[5] <<= self.acc[5] + (self.vrf[rs1][6*XLEN-1:5*XLEN] * self.vrf[rs2][6*XLEN-1:5*XLEN])
                            self.acc[6] <<= self.acc[6] + (self.vrf[rs1][7*XLEN-1:6*XLEN] * self.vrf[rs2][7*XLEN-1:6*XLEN])
                            self.acc[7] <<= self.acc[7] + (self.vrf[rs1][8*XLEN-1:7*XLEN] * self.vrf[rs2][8*XLEN-1:7*XLEN])
                        with If(opcode == OP_VADD):
                            self.vrf[rd] <<= self.vrf[rs1] + self.vrf[rs2]
                        with If(opcode == OP_VMAX0):
                            self.vrf[rd] <<= vmax0_result
                        with If(opcode == OP_VMOV):
                            self.vrf[rd] <<= self.vrf[rs1]
                        with If(opcode == OP_SCALAR_LOAD):
                            self.vrf[rd] <<= Cat(
                                Cat(Rep(imm[15], XLEN-16), imm), Cat(Rep(imm[15], XLEN-16), imm),
                                Cat(Rep(imm[15], XLEN-16), imm), Cat(Rep(imm[15], XLEN-16), imm),
                                Cat(Rep(imm[15], XLEN-16), imm), Cat(Rep(imm[15], XLEN-16), imm),
                                Cat(Rep(imm[15], XLEN-16), imm), Cat(Rep(imm[15], XLEN-16), imm),
                            )
                        self.state <<= 0
                    with sw.case(0xF):
                        self.running <<= 0
                        self.state <<= 0xF

        mem_req_c   = Wire(1, "mem_req_c")
        mem_wen_c   = Wire(1, "mem_wen_c")
        mem_addr_c  = Wire(32, "mem_addr_c")
        mem_wdata_c = Wire(VLEN, "mem_wdata_c")

        with self.comb:
            mem_req_c <<= 0
            mem_wen_c <<= 0
            mem_addr_c <<= 0
            mem_wdata_c <<= 0
            with If(self.state == 3):
                mem_req_c <<= 1
                mem_addr_c <<= Cat(Const(0, 16), imm)
                mem_wen_c <<= (opcode == OP_VSTORE)
                with If(opcode == OP_VSTORE):
                    mem_wdata_c <<= self.vrf[rd]
            self.mem_req  <<= mem_req_c
            self.mem_wen   <<= mem_wen_c
            self.mem_addr  <<= mem_addr_c
            self.mem_wdata <<= mem_wdata_c


class Npu4CoreTop(Module):
    def __init__(self):
        super().__init__("npu_4core_top")

        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.core0_inst_wr_en   = Input(1, "core0_inst_wr_en")
        self.core0_inst_wr_data = Input(32, "core0_inst_wr_data")
        self.core1_inst_wr_en   = Input(1, "core1_inst_wr_en")
        self.core1_inst_wr_data = Input(32, "core1_inst_wr_data")
        self.core2_inst_wr_en   = Input(1, "core2_inst_wr_en")
        self.core2_inst_wr_data = Input(32, "core2_inst_wr_data")
        self.core3_inst_wr_en   = Input(1, "core3_inst_wr_en")
        self.core3_inst_wr_data = Input(32, "core3_inst_wr_data")

        self.mem_req   = Output(1, "mem_req")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.all_done = Output(1, "all_done")
        self.core0_debug_acc0 = Output(ACCW, "core0_debug_acc0")
        self.core1_debug_acc0 = Output(ACCW, "core1_debug_acc0")
        self.core2_debug_acc0 = Output(ACCW, "core2_debug_acc0")
        self.core3_debug_acc0 = Output(ACCW, "core3_debug_acc0")

        cores = [NpuCore(f"core_{i}") for i in range(4)]

        core_mem_req   = [Wire(1, f"c{i}_mem_req")   for i in range(4)]
        core_mem_addr  = [Wire(32, f"c{i}_mem_addr")  for i in range(4)]
        core_mem_wen   = [Wire(1, f"c{i}_mem_wen")   for i in range(4)]
        core_mem_wdata = [Wire(VLEN, f"c{i}_mem_wdata") for i in range(4)]
        core_mem_rdata = [Wire(VLEN, f"c{i}_mem_rdata") for i in range(4)]
        core_mem_valid = [Wire(1, f"c{i}_mem_valid") for i in range(4)]

        core0_done = Wire(1, "core0_done")
        core1_done = Wire(1, "core1_done")
        core2_done = Wire(1, "core2_done")
        core3_done = Wire(1, "core3_done")

        self.rr_grant = Reg(2, "rr_grant")
        any_req = Wire(1, "any_req")

        with self.comb:
            any_req <<= core_mem_req[0] | core_mem_req[1] | core_mem_req[2] | core_mem_req[3]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.rr_grant <<= 0
            with Else():
                with If(any_req & self.mem_ready):
                    self.rr_grant <<= self.rr_grant + 1

        with self.comb:
            self.mem_req <<= Mux(self.rr_grant == 0, core_mem_req[0],
                           Mux(self.rr_grant == 1, core_mem_req[1],
                           Mux(self.rr_grant == 2, core_mem_req[2], core_mem_req[3])))
            self.mem_addr <<= Mux(self.rr_grant == 0, core_mem_addr[0],
                            Mux(self.rr_grant == 1, core_mem_addr[1],
                            Mux(self.rr_grant == 2, core_mem_addr[2], core_mem_addr[3])))
            self.mem_wen <<= Mux(self.rr_grant == 0, core_mem_wen[0],
                           Mux(self.rr_grant == 1, core_mem_wen[1],
                           Mux(self.rr_grant == 2, core_mem_wen[2], core_mem_wen[3])))
            self.mem_wdata <<= Mux(self.rr_grant == 0, core_mem_wdata[0],
                             Mux(self.rr_grant == 1, core_mem_wdata[1],
                             Mux(self.rr_grant == 2, core_mem_wdata[2], core_mem_wdata[3])))

        for i in range(4):
            with self.comb:
                core_mem_valid[i] <<= self.mem_valid & (self.rr_grant == i)
                core_mem_rdata[i] <<= self.mem_rdata

        inst_ports = [
            (self.core0_inst_wr_en, self.core0_inst_wr_data),
            (self.core1_inst_wr_en, self.core1_inst_wr_data),
            (self.core2_inst_wr_en, self.core2_inst_wr_data),
            (self.core3_inst_wr_en, self.core3_inst_wr_data),
        ]
        debug_ports = [
            self.core0_debug_acc0,
            self.core1_debug_acc0,
            self.core2_debug_acc0,
            self.core3_debug_acc0,
        ]
        done_ports = [core0_done, core1_done, core2_done, core3_done]

        for i in range(4):
            self.instantiate(cores[i], f"core_{i}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "start": self.start,
                "inst_wr_en": inst_ports[i][0],
                "inst_wr_data": inst_ports[i][1],
                "mem_req": core_mem_req[i],
                "mem_addr": core_mem_addr[i],
                "mem_wen": core_mem_wen[i],
                "mem_wdata": core_mem_wdata[i],
                "mem_valid": core_mem_valid[i],
                "mem_rdata": core_mem_rdata[i],
                "mem_ready": self.mem_ready,
                "debug_acc0": debug_ports[i],
                "done": done_ports[i],
            })

        with self.comb:
            self.all_done <<= core0_done & core1_done & core2_done & core3_done


print("  - SimpleNPU modules defined (NpuCore, Npu4CoreTop)")
