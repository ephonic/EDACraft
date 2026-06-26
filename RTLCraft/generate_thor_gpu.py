#!/usr/bin/env python3
"""Generate RTL for Thor-class GPGPU."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtlgen.codegen import VerilogEmitter, EmitProfile
from skills.gpgpu.thor_gpu import GpuSM, Gpu2SMTop

OUTDIR = "generated_thor_gpu"
os.makedirs(OUTDIR, exist_ok=True)

# Use SystemVerilog always_comb to eliminate @* array-sensitivity warnings
profile = EmitProfile(
    style="sv",
    always_comb=True,
    always_ff=True,
    language="systemverilog",
)
emitter = VerilogEmitter(disable_cse=True, profile=profile, use_sv_always=True)

for mod in [GpuSM(), Gpu2SMTop()]:
    verilog = emitter.emit(mod)
    path = os.path.join(OUTDIR, f"{mod.name}.v")
    with open(path, "w") as f:
        f.write("`timescale 1ns / 1ps\n")
        f.write(verilog)
    print(f"  Written {path}")
