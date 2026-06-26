"""Thor GPU — PipelineSM L3 DSL. 5-stage warp pipeline with valid/ready handshake.

Pipeline stages (all registered with backpressure):
  FS: Fetch — IMEM read, PC update
  DS: Decode — instruction decode, VRF read
  ES: Execute — dispatch to ALU/FPU/SFU/Tensor/LSU
  WS: Writeback — VRF write, warp done check

Multiple warps occupy different stages simultaneously (latency hiding).
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Elif, Else, Switch, Cat, Rep, Const, ForGen

from skills.thor import (
    XLEN, NLANE, VLEN, VREGS, NWARP, IMEM_DEPTH,
    OP_SLOAD, OP_VADD, OP_VMUL, OP_VLOAD, OP_VSTORE, OP_DONE, OP_NOP,
)


class PipelineSM(Module):
    """5-stage warp pipeline SM. One warp/cycle throughput, multi-cycle latency."""

    def __init__(self, name="pipeline_sm"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready"); self.mem_valid = Input(1, "mem_valid")
        self.mem_req = Output(1, "mem_req"); self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(32, "mem_addr"); self.mem_wdata = Output(VLEN, "mem_wdata")
        self.sm_done = Output(1, "sm_done")

        # === Per-warp state ===
        self.warp_pc = Array(32, NWARP, "warp_pc")
        self.warp_done = Array(1, NWARP, "warp_done")
        self.warp_mem_wait = Array(1, NWARP, "warp_mem_wait")
        self.imem = Array(32, IMEM_DEPTH, "imem")
        self.vrf = Array(VLEN, VREGS * NWARP, "vrf")

        self._running = Reg(1, "running")
        self._warp_sel = Reg(4, "warp_sel")  # for round-robin

        # === Pipeline stage registers ===
        # FS (Fetch Stage)
        self._fs_valid = Reg(1, "fs_v"); self._fs_warp = Reg(4, "fs_w")
        self._fs_instr = Reg(32, "fs_i")

        # DS (Decode Stage)
        self._ds_valid = Reg(1, "ds_v"); self._ds_warp = Reg(4, "ds_w")
        self._ds_opcode = Reg(5, "ds_op"); self._ds_rd = Reg(5, "ds_rd")
        self._ds_rs1 = Reg(5, "ds_rs1"); self._ds_rs2 = Reg(5, "ds_rs2")
        self._ds_imm = Reg(13, "ds_imm")
        self._ds_op1 = Reg(VLEN, "ds_op1"); self._ds_op2 = Reg(VLEN, "ds_op2")

        # ES (Execute Stage)
        self._es_valid = Reg(1, "es_v"); self._es_warp = Reg(4, "es_w")
        self._es_opcode = Reg(5, "es_op"); self._es_rd = Reg(5, "es_rd")
        self._es_result = Reg(VLEN, "es_r"); self._es_done = Reg(1, "es_done")

        # WS (Writeback Stage)
        self._ws_valid = Reg(1, "ws_v"); self._ws_warp = Reg(4, "ws_w")
        self._ws_rd = Reg(5, "ws_rd"); self._ws_data = Reg(VLEN, "ws_d")

        # === Handshake wires between stages ===
        fs_to_ds_ready = Wire(1, "fs_rdy")
        ds_to_es_ready = Wire(1, "ds_rdy")
        es_to_ws_ready = Wire(1, "es_rdy")

        # === Warp scheduler: round-robin select ===
        next_warp = Wire(4, "nw")
        with self.comb:
            next_warp <<= 0
            for i in range(NWARP):
                cand = (self._warp_sel + i + 1) % NWARP
                st = self.warp_done[cand]
                mw = self.warp_mem_wait[cand]
                with If(self._running & (st == 0) & (mw == 0)):
                    next_warp <<= cand

        # === FS: Fetch stage ===
        fs_fire = Wire(1, "fs_fire")
        with self.comb:
            fs_fire <<= (self._fs_valid == 0) | fs_to_ds_ready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._running <<= 0
                self._warp_sel <<= 0
                for w in range(NWARP):
                    self.warp_pc[w] <<= 0; self.warp_done[w] <<= 0
                    self.warp_mem_wait[w] <<= 0
                for f in ['_fs_valid','_ds_valid','_es_valid','_ws_valid']:
                    setattr(self, f, 0)
            with Else():
                with If(self.start & ~self._running):
                    self._running <<= 1
                    for w in range(NWARP):
                        self.warp_pc[w] <<= 0; self.warp_done[w] <<= 0
                        self.warp_mem_wait[w] <<= 0

                # === Writeback stage (WS) ===
                with If(self._ws_valid & 1):  # always accept WB
                    wr = self._ws_rd; ww = self._ws_warp
                    with If(wr != 0):
                        self.vrf[ww * VREGS + wr] <<= self._ws_data
                    self._ws_valid <<= 0

                # === Execute stage → WS ===
                es_to_ws = self._es_valid & es_to_ws_ready
                with If(es_to_ws):
                    self._ws_valid <<= 1
                    self._ws_warp <<= self._es_warp
                    self._ws_rd <<= self._es_rd
                    self._ws_data <<= self._es_result
                    self._es_valid <<= 0

                # === Decode stage → ES ===
                ds_to_es = self._ds_valid & ds_to_es_ready
                with If(ds_to_es):
                    self._es_valid <<= 1
                    self._es_warp <<= self._ds_warp
                    self._es_opcode <<= self._ds_opcode
                    self._es_rd <<= self._ds_rd
                    # Execute logic
                    with Switch(self._ds_opcode) as sw:
                        with sw.case(OP_SLOAD):
                            v = 0
                            lv = Cat(Rep(self._ds_imm[12], XLEN - 13), self._ds_imm)
                            for ln in range(NLANE):
                                v |= lv << (ln * XLEN)
                            self._es_result <<= v; self._es_done <<= 1
                        with sw.case(OP_VADD):
                            self._es_result <<= self._ds_op1 + self._ds_op2
                            self._es_done <<= 1
                        with sw.case(OP_VMUL):
                            self._es_result <<= self._ds_op1 * self._ds_op2
                            self._es_done <<= 1
                        with sw.case(OP_DONE):
                            self._es_done <<= 1
                        with sw.case(OP_VLOAD):
                            self._es_done <<= 0  # wait for memory
                        with sw.case(OP_VSTORE):
                            self._es_done <<= 0
                        with sw.default():
                            self._es_done <<= 1
                    self._ds_valid <<= 0

                # === Fetch stage → DS ===
                fs_to_ds = self._fs_valid & fs_to_ds_ready
                with If(fs_to_ds):
                    op = self._fs_instr[31:28]
                    rd = self._fs_instr[27:23]
                    rs1 = self._fs_instr[22:18]
                    rs2 = self._fs_instr[17:13]
                    imm = self._fs_instr[12:0]
                    fw = self._fs_warp
                    self._ds_valid <<= 1
                    self._ds_warp <<= fw
                    self._ds_opcode <<= op
                    self._ds_rd <<= rd
                    self._ds_rs1 <<= rs1; self._ds_rs2 <<= rs2
                    self._ds_imm <<= imm
                    self._ds_op1 <<= self.vrf[fw * VREGS + rs1]
                    self._ds_op2 <<= self.vrf[fw * VREGS + rs2]
                    self._fs_valid <<= 0

                # === Warp select → FS ===
                ws_sel = next_warp
                w = ws_sel
                ws_fire = self._running & (self.warp_done[w] == 0) & (self.warp_mem_wait[w] == 0)
                ws_fire = ws_fire & fs_fire
                with If(ws_fire):
                    self._fs_valid <<= 1
                    self._fs_warp <<= w
                    self._fs_instr <<= self.imem[self.warp_pc[w]]
                    self.warp_pc[w] <<= self.warp_pc[w] + 1
                    self._warp_sel <<= (w + 1) % NWARP

        # === Memory request (combinatorial from any warp in mem wait) ===
        with self.comb:
            self.mem_req <<= 0; self.mem_wen <<= 0
            self.mem_addr <<= 0; self.mem_wdata <<= 0
            for w in range(NWARP):
                with If(self.warp_mem_wait[w]):
                    self.mem_req <<= 1

        # === Memory response handling ===
        with self.seq(self.clk, self.rst):
            with If(self.mem_valid & self.mem_ready):
                for w in range(NWARP):
                    with If(self.warp_mem_wait[w]):
                        self.warp_mem_wait[w] <<= 0

        # SM done
        with self.comb:
            d = 1
            for w in range(NWARP): d = d & self.warp_done[w]
            self.sm_done <<= d
