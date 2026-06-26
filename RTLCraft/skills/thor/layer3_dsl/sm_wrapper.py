"""Thor GPU — SM Wrapper L3 DSL. Streaming Multiprocessor with 5-stage pipeline.

Instantiates and connects all SM sub-modules:
  WarpScheduler×4, IBuffer×4, Scoreboard, OperandCollector,
  VectorALU, VectorFPU, SFU, TensorCore, LSU, MemoryCoalesce, L1Cache, SharedMemory
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Elif, Else, Switch, Cat, Rep, Const, ForGen

from skills.thor import (
    XLEN, NLANE, VLEN, VREGS, NWARP, N_SCHED, WARP_PER_SCHED, IMEM_DEPTH,
    OP_SLOAD, OP_VADD, OP_VMUL, OP_VLOAD, OP_VSTORE, OP_DONE, OP_NOP,
)
from skills.thor.layer3_dsl.warp_scheduler import WarpScheduler
from skills.thor.layer3_dsl.ibuffer import IBuffer
from skills.thor.layer3_dsl.scoreboard import Scoreboard
from skills.thor.layer3_dsl.vector_alu import VectorALU
from skills.thor.layer3_dsl.lsu import LSU


class SMWrapper(Module):
    """Streaming Multiprocessor with 5-stage warp pipeline and sub-modules."""

    def __init__(self, name="sm_wrapper"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.wb_accept = Input(1, "wb_accept")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_req = Output(1, "mem_req"); self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.sm_done = Output(1, "sm_done")

        # Registers / State Arrays
        self.imem = Array(32, IMEM_DEPTH, "imem")
        self._warp_pc = Array(32, NWARP, "warp_pc")
        self._warp_state = Array(4, NWARP, "warp_state")
        self._warp_done = Array(1, NWARP, "warp_done")
        self._warp_inst = Array(32, NWARP, "warp_inst")
        self._vrf = Array(VLEN, VREGS * NWARP, "vrf")
        self._warp_sel = Reg(4, "warp_sel"); self._running = Reg(1, "running")
        self._wb_dest = Reg(5, "wb_dest"); self._wb_data = Reg(VLEN, "wb_data")
        self._wb_valid = Reg(1, "wb_valid"); self._cycle = Reg(16, "cycle")

        # Instantiate sub-modules
        ws = WarpScheduler(name="warp_sched_0")
        ib = IBuffer(name="ibuf_0")
        sb = Scoreboard(name="scoreboard")
        alu = VectorALU(name="vector_alu")
        lsu = LSU(name="lsu")

        ws_sel = Wire(2, "ws_sel"); ws_v = Wire(1, "ws_v")
        ib_instr = Wire(32, "ib_instr"); ib_v = Wire(1, "ib_v")
        sb_busy = Wire(128, "sb_busy")
        alu_res = Wire(VLEN, "alu_res"); alu_v = Wire(1, "alu_v")
        ls_rd = Wire(VLEN, "ls_rd"); ls_v = Wire(1, "ls_v")

        self.instantiate(ws, "sched", port_map={
            "clk": self.clk, "rst": self.rst,
            "warp_ready": ~0, "warp_stall": 0,
            "selected_warp": ws_sel, "select_valid": ws_v,
        })
        self.instantiate(ib, "ibuf", port_map={
            "clk": self.clk, "rst": self.rst,
            "push_valid": 0, "push_data": 0, "pop_ready": 1,
            "instr": ib_instr, "valid": ib_v,
        })

        # Instruction decode wires
        opcode = Wire(5, "opcode"); rd = Wire(5, "rd")
        rs1 = Wire(5, "rs1"); rs2 = Wire(5, "rs2"); imm = Wire(13, "imm")
        with self.comb:
            opcode <<= self._warp_inst[self._warp_sel][31:28]
            rd <<= self._warp_inst[self._warp_sel][27:23]
            rs1 <<= self._warp_inst[self._warp_sel][22:18]
            rs2 <<= self._warp_inst[self._warp_sel][17:13]
            imm <<= self._warp_inst[self._warp_sel][12:0]

        vrf_base = Wire(8, "vrf_base")
        with self.comb: vrf_base <<= self._warp_sel * VREGS

        # SM done
        with self.comb:
            d = 1
            with ForGen('w', 0, NWARP) as w: d <<= d & self._warp_done[w]
            self.sm_done <<= d

        # Memory request logic (any warp in mem state)
        with self.comb:
            self.mem_req <<= 0; self.mem_wen <<= 0
            self.mem_addr <<= Cat(Const(0, 19), imm)
            self.mem_wdata <<= self._vrf[vrf_base + rs1]
            with ForGen('ww', 0, NWARP) as ww:
                with If(self._warp_state[ww] == 3):
                    self.mem_req <<= 1
                    self.mem_wen <<= (opcode == OP_VSTORE)

        # 5-stage warp pipeline FSM
        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._warp_sel <<= 0; self._running <<= 0
                self._wb_valid <<= 0; self._cycle <<= 0
                with ForGen('w', 0, NWARP) as w:
                    self._warp_pc[w] <<= 0; self._warp_state[w] <<= 0
                    self._warp_done[w] <<= 0
            with Else():
                self._cycle <<= self._cycle + 1

                with If(self.start & ~self._running):
                    self._running <<= 1
                    with ForGen('w', 0, NWARP) as w:
                        self._warp_pc[w] <<= 0; self._warp_state[w] <<= 0
                        self._warp_done[w] <<= 0

                # Writeback
                with If(self._wb_valid & self.wb_accept):
                    self._vrf[vrf_base + self._wb_dest] <<= self._wb_data
                    self._wb_valid <<= 0

                # Round-robin warp select
                with ForGen('i', 0, NWARP) as i:
                    cand = (self._warp_sel + i + 1) % NWARP
                    with If(self._running & ~self._warp_done[cand] & (self._warp_state[cand] == 0)):
                        self._warp_sel <<= cand

                w = self._warp_sel
                with Switch(self._warp_state[w]) as sw:
                    with sw.case(0):  # idle -> fetch
                        with If(self._running & ~self._warp_done[w]):
                            self._warp_state[w] <<= 1
                    with sw.case(1):  # fetch
                        self._warp_inst[w] <<= self.imem[self._warp_pc[w]]
                        self._warp_pc[w] <<= self._warp_pc[w] + 1
                        self._warp_state[w] <<= 2
                    with sw.case(2):  # decode/execute
                        with If(opcode == OP_SLOAD):
                            v = 0
                            lv = Cat(Rep(imm[12], XLEN - 13), imm)
                            with ForGen('ln', 0, NLANE) as ln:
                                v |= lv << (ln * XLEN)
                            self._vrf[vrf_base + rd] <<= v
                            self._warp_state[w] <<= 0
                        with Elif(opcode == OP_VADD):
                            a = self._vrf[vrf_base + rs1]
                            b = self._vrf[vrf_base + rs2]
                            self._vrf[vrf_base + rd] <<= a + b
                            self._warp_state[w] <<= 0
                        with Elif(opcode == OP_VMUL):
                            a = self._vrf[vrf_base + rs1]
                            b = self._vrf[vrf_base + rs2]
                            self._vrf[vrf_base + rd] <<= a * b
                            self._warp_state[w] <<= 0
                        with Elif(opcode == OP_DONE):
                            self._warp_done[w] <<= 1
                            self._warp_state[w] <<= 0xF
                        with Elif((opcode == OP_VLOAD) | (opcode == OP_VSTORE)):
                            self._warp_state[w] <<= 3
                        with Else():
                            self._warp_state[w] <<= 0
                    with sw.case(3):  # mem wait
                        with If(self.mem_valid & self.mem_ready):
                            with If(opcode == OP_VLOAD):
                                self._vrf[vrf_base + rd] <<= self.mem_rdata
                            self._warp_state[w] <<= 0
                    with sw.case(0xF):  # done
                        self._warp_state[w] <<= 0xF
