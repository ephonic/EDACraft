#!/usr/bin/env python3
"""Generate RTL for simple 4-core NPU."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtlgen.codegen import VerilogEmitter
from skills.npu.simple_npu import NpuCore, Npu4CoreTop

OUTDIR = "generated_npu4"
os.makedirs(OUTDIR, exist_ok=True)

emitter = VerilogEmitter(disable_cse=True)

for mod in [NpuCore(), Npu4CoreTop()]:
    verilog = emitter.emit(mod)
    path = os.path.join(OUTDIR, f"{mod.name}.v")
    with open(path, "w") as f:
        f.write(verilog)
    print(f"  Written {path}")
