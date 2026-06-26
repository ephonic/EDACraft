"""L5 DSL module for the ThorLSU.

RTL-ready rtlgen description of the vector load/store unit. The request is
generated combinationally from the op inputs; the response is captured into a
registered rdata/done.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Const
from rtlgen.logic import If
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

DATA_W = 256
ADDR_W = 32


class ThorLSU(Module):
    """Vector load/store unit with memory request/response handshake."""

    def __init__(self):
        super().__init__("thor_lsu")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.valid_in = Input(1, "valid_in")
        self.op = Input(1, "op")          # 0=load, 1=store
        self.addr = Input(ADDR_W, "addr")
        self.wdata = Input(DATA_W, "wdata")
        self.mem_ready = Input(1, "mem_ready")
        self.mem_valid = Input(1, "mem_valid")
        self.mem_rdata = Input(DATA_W, "mem_rdata")

        self.mem_req = Output(1, "mem_req")
        self.mem_wen = Output(1, "mem_wen")
        self.mem_addr = Output(ADDR_W, "mem_addr")
        self.mem_wdata = Output(DATA_W, "mem_wdata")
        self.rdata = Output(DATA_W, "rdata")
        self.done = Output(1, "done")

        # Combinational request generation.
        with self.comb:
            self.mem_req <<= self.valid_in & self.mem_ready
            self.mem_wen <<= self.op
            self.mem_addr <<= self.addr
            self.mem_wdata <<= self.wdata

        # Capture response through a Wire (framework seq() If() requirement).
        resp_w = Wire(1, "resp_w")
        with self.comb:
            resp_w <<= self.mem_valid

        with self.seq(self.clk, ~self.rst_n):
            with If(resp_w):
                self.rdata <<= self.mem_rdata
                self.done <<= 1

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/lsu/layer_L5_dsl/src/dsl.py",
            description="Vector LSU with combinational request and registered response capture.",
            author="RTLCraft Agent", version="0.1",
            timing="Request combinational; response registered (done on mem_valid).",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorLSU",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready vector LSU (combinational request, registered response).",
        "dsl_class": "ThorLSU",
        "ports": "valid_in, op, addr[32], wdata[256], mem_ready, mem_valid, mem_rdata -> mem_req, mem_wen, mem_addr, mem_wdata, rdata, done",
    }


__all__ = ["ThorLSU", "describe"]
