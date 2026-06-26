"""L5 DSL module for the ThorCluster (top-level GPGPU compute cluster).

Instantiates two ThorGpuSM cores and a 1-bit round-robin L2 arbiter over the
shared global memory port. This is the cluster top-level of the design.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Reg, Const
from rtlgen import Mux
from rtlgen.logic import If
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

from thor_gpu.modules.gpu_sm.layer_L5_dsl.src.dsl import ThorGpuSM

NSM = 2
VLEN = 256
ACCW = 64


class ThorCluster(Module):
    """2-SM GPGPU compute cluster with a round-robin L2 arbiter."""

    def __init__(self, name="thor_cluster"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")

        # Per-SM IMEM write ports.
        self.sm0_imem_wr_en = Input(1, "sm0_imem_wr_en")
        self.sm0_imem_wr_addr = Input(5, "sm0_imem_wr_addr")
        self.sm0_imem_wr_data = Input(32, "sm0_imem_wr_data")
        self.sm1_imem_wr_en = Input(1, "sm1_imem_wr_en")
        self.sm1_imem_wr_addr = Input(5, "sm1_imem_wr_addr")
        self.sm1_imem_wr_data = Input(32, "sm1_imem_wr_data")

        # Global memory interface.
        self.mem_req = Output(1, "mem_req")
        self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(32, "mem_addr")
        self.mem_wdata = Output(VLEN, "mem_wdata")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(VLEN, "mem_rdata")
        self.mem_ready = Input(1, "mem_ready")

        self.all_done = Output(1, "all_done")
        self.sm0_w0_acc0 = Output(ACCW, "sm0_w0_acc0")
        self.sm1_w0_acc0 = Output(ACCW, "sm1_w0_acc0")

        sms = [ThorGpuSM(f"sm_{i}") for i in range(NSM)]

        # Per-SM memory interface wires.
        sm_mem_req = [Wire(1, f"sm{i}_mem_req") for i in range(NSM)]
        sm_mem_wen = [Wire(1, f"sm{i}_mem_wen") for i in range(NSM)]
        sm_mem_addr = [Wire(32, f"sm{i}_mem_addr") for i in range(NSM)]
        sm_mem_wdata = [Wire(VLEN, f"sm{i}_mem_wdata") for i in range(NSM)]
        sm_mem_rdata = [Wire(VLEN, f"sm{i}_mem_rdata") for i in range(NSM)]
        sm_mem_valid = [Wire(1, f"sm{i}_mem_valid") for i in range(NSM)]

        sm_done = [Wire(1, f"sm{i}_done") for i in range(NSM)]
        sm_acc = [Wire(ACCW, f"sm{i}_w0_acc0") for i in range(NSM)]

        self.rr_grant = Reg(1, "rr_grant", init_value=0)
        any_req = Wire(1, "any_req")

        with self.comb:
            any_req <<= sm_mem_req[0] | sm_mem_req[1]

        with self.seq(self.clk, ~self.rst_n):
            with If(any_req & self.mem_ready):
                self.rr_grant <<= self.rr_grant + 1

        # Arbitrate the request onto the global port (grant==0 -> sm0).
        with self.comb:
            self.mem_req <<= Mux(self.rr_grant == 0, sm_mem_req[0], sm_mem_req[1])
            self.mem_wen <<= Mux(self.rr_grant == 0, sm_mem_wen[0], sm_mem_wen[1])
            self.mem_addr <<= Mux(self.rr_grant == 0, sm_mem_addr[0], sm_mem_addr[1])
            self.mem_wdata <<= Mux(self.rr_grant == 0, sm_mem_wdata[0], sm_mem_wdata[1])

        # Response steering: only the granted SM sees mem_valid; rdata broadcast.
        for i in range(NSM):
            with self.comb:
                sm_mem_valid[i] <<= self.mem_valid & (self.rr_grant == Const(i, 1))
                sm_mem_rdata[i] <<= self.mem_rdata

        imem_ports = [
            (self.sm0_imem_wr_en, self.sm0_imem_wr_addr, self.sm0_imem_wr_data),
            (self.sm1_imem_wr_en, self.sm1_imem_wr_addr, self.sm1_imem_wr_data),
        ]

        for i in range(NSM):
            self.instantiate(sms[i], f"sm_{i}", port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "start": self.start,
                "imem_wr_en": imem_ports[i][0],
                "imem_wr_addr": imem_ports[i][1],
                "imem_wr_data": imem_ports[i][2],
                "mem_req": sm_mem_req[i],
                "mem_wen": sm_mem_wen[i],
                "mem_addr": sm_mem_addr[i],
                "mem_wdata": sm_mem_wdata[i],
                "mem_valid": sm_mem_valid[i],
                "mem_rdata": sm_mem_rdata[i],
                "mem_ready": self.mem_ready,
                "sm_done": sm_done[i],
                "debug_w0_acc0": sm_acc[i],
            })

        with self.comb:
            self.all_done <<= sm_done[0] & sm_done[1]
            self.sm0_w0_acc0 <<= sm_acc[0]
            self.sm1_w0_acc0 <<= sm_acc[1]

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/gpu_cluster/layer_L5_dsl/src/dsl.py",
            description="2-SM compute cluster with round-robin L2 arbiter over global memory.",
            author="RTLCraft Agent", version="0.1",
            timing="Round-robin arbitration; all_done when both SMs report sm_done.",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorCluster",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready 2-SM cluster with round-robin L2 arbiter (cluster top).",
        "dsl_class": "ThorCluster",
        "ports": "clk, rst_n, start, sm{0,1}_imem_wr_*, mem_* -> all_done, sm{0,1}_w0_acc0",
    }


__all__ = ["ThorCluster", "describe"]
