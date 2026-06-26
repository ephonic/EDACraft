#!/usr/bin/env python3
"""
generate_hetero_riscv4_real.py — Emit FULL Verilog from complete DSL modules.

Uses the real implementations in skills.hetero_riscv4.dsl_modules:
  - PerformanceCore (5-stage RV64I, ~290 lines DSL)
  - EfficiencyCore  (3-stage RV64I, ~328 lines DSL)
  - L1CacheBig      (64KB 8-way, ~146 lines DSL)
  - L1CacheSmall    (16KB 2-way, ~157 lines DSL)
  - CoherenceDir    (MSI directory, ~122 lines DSL)
  - NoCRouter       (5-port XY router, ~360 lines DSL)
  - HeteroMeshTop   (2x2 mesh top, ~480 lines DSL)

These are NOT skeletons — they contain full pipeline logic.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtlgen.codegen import VerilogEmitter

from skills.hetero_riscv4.dsl_modules import (
    PerformanceCore,
    EfficiencyCore,
    L1CacheBig,
    L1CacheSmall,
    CoherenceDir,
    NoCRouter,
    HeteroMeshTop,
)

OUTPUT_DIR = "generated_hetero_riscv4"

print("=" * 70)
print("Heterogeneous 4-Core RISC-V SoC — FULL Verilog Emission")
print("=" * 70)

all_modules = [
    ("performance_core_0", PerformanceCore()),
    ("performance_core_1", PerformanceCore()),
    ("efficiency_core_0", EfficiencyCore()),
    ("efficiency_core_1", EfficiencyCore()),
    ("l1_cache_big_0", L1CacheBig()),
    ("l1_cache_big_1", L1CacheBig()),
    ("l1_cache_small_0", L1CacheSmall()),
    ("l1_cache_small_1", L1CacheSmall()),
    ("coherence_dir", CoherenceDir()),
    ("noc_router_0", NoCRouter()),
    ("noc_router_1", NoCRouter()),
    ("noc_router_2", NoCRouter()),
    ("noc_router_3", NoCRouter()),
    ("hetero_mesh_top", HeteroMeshTop()),
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
emitter = VerilogEmitter(disable_cse=True)

total_lines = 0
emitted_types = set()
modules = []
for name, mod in all_modules:
    mod_type = type(mod).__name__
    if mod_type not in emitted_types:
        emitted_types.add(mod_type)
        verilog = emitter.emit(mod)
        out_path = os.path.join(OUTPUT_DIR, f"{name}.v")
        with open(out_path, "w") as f:
            f.write(verilog)
        lines = len(verilog.splitlines())
        total_lines += lines
        print(f"  {out_path:50s} {lines:5d} lines")
        modules.append((name, mod))

print(f"\n  Total: {total_lines:,} lines in {len(modules)} unique files")

# Verify
print("\n" + "=" * 70)
print("Verification")
print("=" * 70)

errors = []
for name, mod in modules:
    path = os.path.join(OUTPUT_DIR, f"{name}.v")
    with open(path) as f:
        content = f.read()
    mod_name = getattr(mod, '_type_name', mod.name)
    has_module = f"module {mod_name}" in content
    has_clk = "input clk" in content
    has_rst = "input rst_n" in content
    if not has_module:
        errors.append(f"{name}.v missing module {mod_name}")
    if not has_clk:
        errors.append(f"{name}.v missing clk")
    if not has_rst:
        errors.append(f"{name}.v missing rst_n")
    print(f"  {name:25s} module={has_module} clk={has_clk} rst={has_rst}")

if errors:
    print("\nFAIL")
    for e in errors:
        print(f"  ❌ {e}")
    sys.exit(1)
else:
    print(f"\nPASS — All {len(modules)} full modules emitted correctly")
    print("=" * 70)
