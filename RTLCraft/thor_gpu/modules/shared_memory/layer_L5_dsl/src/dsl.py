"""L5 DSL module for the ThorSharedMemory.

RTL-ready rtlgen description of the per-SM shared SRAM. Single-port
synchronous-read array; write has priority over read at the same address.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Array, Const
from rtlgen import Mux
from rtlgen.logic import If
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

WORD = 256
ADDR = 12
DEPTH = 1 << ADDR  # 4096


class ThorSharedMemory(Module):
    """Per-SM shared SRAM: 4096x256-bit, single-port, registered read.

    Write has priority over read to the same address. The seq() reset clears
    the read register; array contents are memory (not reset).
    """

    def __init__(self):
        super().__init__("thor_shared_memory")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.addr = Input(ADDR, "addr")
        self.wdata = Input(WORD, "wdata")
        self.we = Input(1, "we")
        self.re = Input(1, "re")

        self.rdata = Output(WORD, "rdata")

        self.mem = Array(WORD, DEPTH, "mem")

        # Combinational read of the addressed word.
        comb_rdata = self.mem[self.addr]

        # Gate the access through Wires (framework seq() If() requirement).
        we_w = Wire(1, "we_w")
        re_w = Wire(1, "re_w")
        with self.comb:
            we_w <<= self.we
            re_w <<= self.re

        with self.seq(self.clk, ~self.rst_n):
            with If(we_w):
                self.mem[self.addr] <<= self.wdata
            # Registered read: latch the addressed word when reading.
            with If(re_w):
                self.rdata <<= comb_rdata

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/shared_memory/layer_L5_dsl/src/dsl.py",
            description="Per-SM shared SRAM (4096x256b), single-port, registered read, write priority.",
            author="RTLCraft Agent", version="0.1",
            timing="Registered read (1 cycle); write priority over read.",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorSharedMemory",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready per-SM shared SRAM (4096x256b, registered read).",
        "dsl_class": "ThorSharedMemory",
        "ports": "addr[12], wdata[256], we, re -> rdata[256]",
    }


__all__ = ["ThorSharedMemory", "describe"]
