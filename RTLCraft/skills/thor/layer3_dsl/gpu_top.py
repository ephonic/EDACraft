"""Thor GPU — Top-Level GPU L3 DSL. CTA scheduler + SM×4 + RR arbiter."""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else

from skills.thor import NSM, VLEN
from skills.thor.layer3_dsl.sm_wrapper import SMWrapper


class GPUTop(Module):
    def __init__(self):
        super().__init__("gpu_top")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.start = Input(1, "start")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_req = Output(1, "mem_req"); self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.all_done = Output(1, "all_done")

        sms = [SMWrapper(name=f"sm_{i}") for i in range(NSM)]
        sm_req = [Wire(1, f"sm{i}_mem_req") for i in range(NSM)]
        sm_wen = [Wire(1, f"sm{i}_mem_wen") for i in range(NSM)]
        sm_addr = [Wire(32, f"sm{i}_mem_addr") for i in range(NSM)]
        sm_wdata = [Wire(VLEN, f"sm{i}_mem_wdata") for i in range(NSM)]
        sm_done = [Wire(1, f"sm{i}_done") for i in range(NSM)]

        self._rr = Reg(4, "rr_grant")
        any_req = Wire(1, "any_req")
        with self.comb:
            any_req <<= 0
            for i in range(NSM):
                any_req <<= any_req | sm_req[i]

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1): self._rr <<= 0
            with Else():
                with If(any_req & self.mem_ready): self._rr <<= self._rr + 1

        with self.comb:
            self.mem_req <<= 0; self.mem_wen <<= 0
            self.mem_addr <<= 0; self.mem_wdata <<= 0
            for i in range(NSM):
                with If(self._rr == i):
                    self.mem_req <<= sm_req[i]; self.mem_wen <<= sm_wen[i]
                    self.mem_addr <<= sm_addr[i]; self.mem_wdata <<= sm_wdata[i]

        for i in range(NSM):
            sm_mv = Wire(1, f"sm{i}_mem_v"); sm_mr = Wire(VLEN, f"sm{i}_mem_r")
            with self.comb:
                sm_mv <<= self.mem_valid & (self._rr == i); sm_mr <<= self.mem_rdata
            self.instantiate(sms[i], f"sm_{i}", port_map={
                "clk": self.clk, "rst": self.rst, "start": self.start,
                "wb_accept": 1, "mem_valid": sm_mv, "mem_rdata": sm_mr,
                "mem_ready": self.mem_ready,
                "mem_req": sm_req[i], "mem_wen": sm_wen[i],
                "mem_addr": sm_addr[i], "mem_wdata": sm_wdata[i],
                "sm_done": sm_done[i],
            })

        with self.comb:
            done_and = 1
            for i in range(NSM):
                done_and = done_and & sm_done[i]
            self.all_done <<= done_and
