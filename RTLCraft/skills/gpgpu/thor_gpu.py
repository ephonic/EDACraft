"""
Thor-class GPGPU design for RTLCraft.

Architecture:
  - 2 SMs (Streaming Multiprocessors)
  - 4 warps per SM, 8-wide SIMD lanes per warp
  - Per-warp vector register file (8 regs x 8 lanes x 32b)
  - Per-SM shared instruction memory (32 entries)
  - Sticky round-robin warp scheduler (advances only when current warp is idle/done/barrier)
  - Warp-level barrier synchronization
  - Global memory with round-robin SM arbiter
"""

from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Elif, Else, Switch, Mux, Cat, Rep, Const

XLEN  = 32
NLANE = 8
VLEN  = XLEN * NLANE       # 256
VREGS = 8                  # vector regs per warp
NWARP = 4                  # warps per SM
NSM   = 2                  # number of SMs
IMEM_DEPTH = 32
ACCW  = 64

OP_NOP     = 0x0
OP_VLOAD   = 0x1
OP_VSTORE  = 0x2
OP_VADD    = 0x3
OP_VMUL    = 0x4
OP_VMAC    = 0x5
OP_BARRIER = 0x6
OP_SLOAD   = 0x7
OP_DONE    = 0xF


class GpuSM(Module):
    def __init__(self, name="gpu_sm"):
        super().__init__(name)

        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.imem_wr_en   = Input(1, "imem_wr_en")
        self.imem_wr_addr = Input(5, "imem_wr_addr")
        self.imem_wr_data = Input(32, "imem_wr_data")

        self.mem_req   = Output(1, "mem_req")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.sm_done = Output(1, "sm_done")
        self.debug_w0_acc0 = Output(ACCW, "debug_w0_acc0")

        self.warp_pc    = Array(32, NWARP, "warp_pc")
        self.warp_state = Array(4, NWARP, "warp_state")
        self.warp_done  = Array(1, NWARP, "warp_done")
        self.warp_acc   = Array(ACCW, NWARP, "warp_acc")
        self.barrier_mask = Array(1, NWARP, "barrier_mask")
        self.imem = Array(32, IMEM_DEPTH, "imem")
        self.vrf = Array(VLEN, VREGS * NWARP, "vrf")

        self.warp_sel = Reg(2, "warp_sel")
        self.inst_reg = Reg(32, "inst_reg")
        self.running  = Reg(1, "running")

        opcode = Wire(4, "opcode")
        rd     = Wire(4, "rd")
        rs1    = Wire(4, "rs1")
        rs2    = Wire(4, "rs2")
        imm    = Wire(16, "imm")

        with self.comb:
            opcode <<= self.inst_reg[31:28]
            rd     <<= self.inst_reg[27:24]
            rs1    <<= self.inst_reg[23:20]
            rs2    <<= self.inst_reg[19:16]
            imm    <<= self.inst_reg[15:0]

        vrf_base = Wire(5, "vrf_base")
        vrf_rs1  = Wire(5, "vrf_rs1")
        vrf_rs2  = Wire(5, "vrf_rs2")
        vrf_rd   = Wire(5, "vrf_rd")

        with self.comb:
            vrf_base <<= self.warp_sel * Const(VREGS, 4)
            vrf_rs1  <<= vrf_base + rs1
            vrf_rs2  <<= vrf_base + rs2
            vrf_rd   <<= vrf_base + rd

        with self.comb:
            self.sm_done <<= self.warp_done[0] & self.warp_done[1] & self.warp_done[2] & self.warp_done[3]
            self.debug_w0_acc0 <<= self.warp_acc[0]

        # Scheduler: advance only when currently selected warp is idle/done/barrier
        next_warp = Wire(2, "next_warp")
        with self.comb:
            next_warp <<= self.warp_sel + 1

        current_warp_idle = Wire(1, "current_warp_idle")
        warp_idle = [Wire(1, f"warp_idle_{i}") for i in range(NWARP)]
        with self.comb:
            for w in range(NWARP):
                warp_idle[w] <<= (self.warp_state[w] == 0) | (self.warp_state[w] == 0xF) | (self.warp_state[w] == 6)
            current_warp_idle <<= Mux(self.warp_sel == 0, warp_idle[0],
                                  Mux(self.warp_sel == 1, warp_idle[1],
                                  Mux(self.warp_sel == 2, warp_idle[2], warp_idle[3])))

        all_at_barrier_or_done = Wire(1, "all_at_barrier_or_done")
        with self.comb:
            all_at_barrier_or_done <<= (
                (self.barrier_mask[0] | self.warp_done[0]) &
                (self.barrier_mask[1] | self.warp_done[1]) &
                (self.barrier_mask[2] | self.warp_done[2]) &
                (self.barrier_mask[3] | self.warp_done[3])
            )

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.warp_sel <<= 0
                self.inst_reg <<= 0
                self.running  <<= 0
                for w in range(NWARP):
                    self.warp_pc[w]    <<= 0
                    self.warp_state[w] <<= 0
                    self.warp_done[w]  <<= 0
                    self.warp_acc[w]   <<= 0
                    self.barrier_mask[w] <<= 0
            with Else():
                with If(self.imem_wr_en):
                    self.imem[self.imem_wr_addr] <<= self.imem_wr_data

                with If(self.start & ~self.running):
                    self.running <<= 1
                    for w in range(NWARP):
                        self.warp_pc[w]    <<= 0
                        self.warp_state[w] <<= 0
                        self.warp_done[w]  <<= 0
                        self.warp_acc[w]   <<= 0
                        self.barrier_mask[w] <<= 0

                with If(all_at_barrier_or_done):
                    for w in range(NWARP):
                        self.barrier_mask[w] <<= 0
                        with If(self.warp_state[w] == 6):
                            self.warp_state[w] <<= 0

                for w in range(NWARP):
                    with If(self.warp_sel == w):
                        with Switch(self.warp_state[w]) as sw:
                            with sw.case(0):
                                with If(self.running & ~self.warp_done[w] & ~self.barrier_mask[w]):
                                    self.warp_state[w] <<= 1
                            with sw.case(1):
                                self.inst_reg <<= self.imem[self.warp_pc[w]]
                                self.warp_pc[w] <<= self.warp_pc[w] + 1
                                self.warp_state[w] <<= 2
                            with sw.case(2):
                                with If(opcode == OP_NOP):
                                    self.warp_state[w] <<= 0
                                with Elif(opcode == OP_DONE):
                                    self.warp_done[w] <<= 1
                                    self.warp_state[w] <<= 0xF
                                with Elif((opcode == OP_VLOAD) | (opcode == OP_VSTORE)):
                                    self.warp_state[w] <<= 3
                                with Elif(opcode == OP_BARRIER):
                                    self.barrier_mask[w] <<= 1
                                    self.warp_state[w] <<= 6
                                with Else():
                                    self.warp_state[w] <<= 4
                            with sw.case(3):
                                self.warp_state[w] <<= 5
                            with sw.case(5):
                                with If(self.mem_valid & self.mem_ready):
                                    with If(opcode == OP_VLOAD):
                                        self.vrf[vrf_rd] <<= self.mem_rdata
                                    self.warp_state[w] <<= 0
                                with Else():
                                    self.warp_state[w] <<= 5
                            with sw.case(4):
                                with If(opcode == OP_VADD):
                                    self.vrf[vrf_rd] <<= self.vrf[vrf_rs1] + self.vrf[vrf_rs2]
                                with If(opcode == OP_VMUL):
                                    self.vrf[vrf_rd] <<= self.vrf[vrf_rs1] * self.vrf[vrf_rs2]
                                with If(opcode == OP_VMAC):
                                    self.warp_acc[w] <<= self.warp_acc[w] + (
                                        self.vrf[vrf_rs1][1*XLEN-1:0*XLEN] *
                                        self.vrf[vrf_rs2][1*XLEN-1:0*XLEN]
                                    )
                                with If(opcode == OP_SLOAD):
                                    self.vrf[vrf_rd] <<= Cat(
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                        Cat(Rep(imm[15], XLEN-16), imm),
                                    )
                                self.warp_state[w] <<= 0
                            with sw.case(0xF):
                                self.warp_state[w] <<= 0xF

                with If(current_warp_idle):
                    self.warp_sel <<= next_warp

        mem_req_c   = Wire(1, "mem_req_c")
        mem_wen_c   = Wire(1, "mem_wen_c")
        mem_addr_c  = Wire(32, "mem_addr_c")
        mem_wdata_c = Wire(VLEN, "mem_wdata_c")

        with self.comb:
            mem_req_c   <<= 0
            mem_wen_c   <<= 0
            mem_addr_c  <<= 0
            mem_wdata_c <<= 0
            for w in range(NWARP):
                with If(self.warp_state[w] == 3):
                    mem_req_c <<= 1
                    mem_addr_c <<= Cat(Const(0, 16), imm)
                    mem_wen_c <<= (opcode == OP_VSTORE)
                    with If(opcode == OP_VSTORE):
                        mem_wdata_c <<= self.vrf[vrf_rd]
            self.mem_req   <<= mem_req_c
            self.mem_wen    <<= mem_wen_c
            self.mem_addr   <<= mem_addr_c
            self.mem_wdata  <<= mem_wdata_c


class Gpu2SMTop(Module):
    def __init__(self):
        super().__init__("gpu_2sm_top")

        self.clk   = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        self.sm0_imem_wr_en   = Input(1, "sm0_imem_wr_en")
        self.sm0_imem_wr_addr = Input(5, "sm0_imem_wr_addr")
        self.sm0_imem_wr_data = Input(32, "sm0_imem_wr_data")
        self.sm1_imem_wr_en   = Input(1, "sm1_imem_wr_en")
        self.sm1_imem_wr_addr = Input(5, "sm1_imem_wr_addr")
        self.sm1_imem_wr_data = Input(32, "sm1_imem_wr_data")

        self.mem_req   = Output(1, "mem_req")
        self.mem_wen   = Output(1, "mem_wen")
        self.mem_addr  = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.all_done = Output(1, "all_done")
        self.sm0_w0_acc0 = Output(ACCW, "sm0_w0_acc0")
        self.sm1_w0_acc0 = Output(ACCW, "sm1_w0_acc0")

        sms = [GpuSM(f"sm_{i}") for i in range(NSM)]

        sm_mem_req   = [Wire(1, f"sm{i}_mem_req")   for i in range(NSM)]
        sm_mem_wen   = [Wire(1, f"sm{i}_mem_wen")   for i in range(NSM)]
        sm_mem_addr  = [Wire(32, f"sm{i}_mem_addr")  for i in range(NSM)]
        sm_mem_wdata = [Wire(VLEN, f"sm{i}_mem_wdata") for i in range(NSM)]
        sm_mem_rdata = [Wire(VLEN, f"sm{i}_mem_rdata") for i in range(NSM)]
        sm_mem_valid = [Wire(1, f"sm{i}_mem_valid") for i in range(NSM)]

        sm0_done = Wire(1, "sm0_done")
        sm1_done = Wire(1, "sm1_done")

        self.rr_grant = Reg(1, "rr_grant")
        any_req = Wire(1, "any_req")

        with self.comb:
            any_req <<= sm_mem_req[0] | sm_mem_req[1]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.rr_grant <<= 0
            with Else():
                with If(any_req & self.mem_ready):
                    self.rr_grant <<= self.rr_grant + 1

        with self.comb:
            self.mem_req   <<= Mux(self.rr_grant == 0, sm_mem_req[0],   sm_mem_req[1])
            self.mem_wen   <<= Mux(self.rr_grant == 0, sm_mem_wen[0],   sm_mem_wen[1])
            self.mem_addr  <<= Mux(self.rr_grant == 0, sm_mem_addr[0],  sm_mem_addr[1])
            self.mem_wdata <<= Mux(self.rr_grant == 0, sm_mem_wdata[0], sm_mem_wdata[1])

        for i in range(NSM):
            with self.comb:
                sm_mem_valid[i] <<= self.mem_valid & (self.rr_grant == i)
                sm_mem_rdata[i] <<= self.mem_rdata

        imem_ports = [
            (self.sm0_imem_wr_en, self.sm0_imem_wr_addr, self.sm0_imem_wr_data),
            (self.sm1_imem_wr_en, self.sm1_imem_wr_addr, self.sm1_imem_wr_data),
        ]
        done_ports = [sm0_done, sm1_done]
        debug_ports = [self.sm0_w0_acc0, self.sm1_w0_acc0]

        for i in range(NSM):
            self.instantiate(sms[i], f"sm_{i}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "start": self.start,
                "imem_wr_en":   imem_ports[i][0],
                "imem_wr_addr": imem_ports[i][1],
                "imem_wr_data": imem_ports[i][2],
                "mem_req":   sm_mem_req[i],
                "mem_wen":   sm_mem_wen[i],
                "mem_addr":  sm_mem_addr[i],
                "mem_wdata": sm_mem_wdata[i],
                "mem_valid": sm_mem_valid[i],
                "mem_rdata": sm_mem_rdata[i],
                "mem_ready": self.mem_ready,
                "sm_done": done_ports[i],
                "debug_w0_acc0": debug_ports[i],
            })

        with self.comb:
            self.all_done <<= sm0_done & sm1_done


print("  - ThorGPGPU modules defined (GpuSM, Gpu2SMTop)")
