#!/usr/bin/env python3
"""
generate_hetero_riscv4.py — Generate RTL for heterogeneous 4-core RISC-V SoC.

Uses build_hetero_arch() from skills.hetero_riscv4.arch_templates to build
ArchDefinition, then runs skeleton generation, Verilog emission, and lint.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills.hetero_riscv4.arch_templates import build_hetero_arch
from rtlgen import ArchSimulator, ArchSkeletonGenerator, VerilogEmitter
from rtlgen.arch_def import ArchDefinition

print("=" * 70)
print("Heterogeneous 4-Core RISC-V SoC — RTL Generation")
print("=" * 70)

# Build architecture
arch = build_hetero_arch()
print(f"\nArchDefinition: {arch.name}")
print(f"  PEs: {len(arch.processing_elements)}")
for pe in arch.processing_elements:
    print(f"    - {pe.name} (type={pe.pe_type})")
print(f"  Interconnects: {len(arch.interconnects)}")

# Run behavioral simulation
print("\n" + "=" * 70)
print("Phase 1: Behavioral Simulation")
print("=" * 70)

sim = ArchSimulator(arch)
results = sim.run(num_cycles=20)
print(f"  Simulated {len(results)} cycles")
for r in results[:5]:
    print(f"    Cycle {r['cycle']}: {r['outputs']}")

# Generate skeletons
print("\n" + "=" * 70)
print("Phase 2: Skeleton Generation")
print("=" * 70)

gen = ArchSkeletonGenerator()
packages = gen.generate_all(arch)
print(f"  Packages: {len(packages)}")
for name, pkg in packages.items():
    print(f"    {name}: steps={len(pkg.implementation_steps)}")

# Generate Verilog
print("\n" + "=" * 70)
print("Phase 3: Verilog Generation")
print("=" * 70)

output_dir = "generated_hetero_riscv4"
os.makedirs(output_dir, exist_ok=True)

emitter = VerilogEmitter()
total_lines = 0
for pe_name, pkg in packages.items():
    verilog = emitter.emit(pkg.dsl_skeleton)
    out_path = os.path.join(output_dir, f"{pe_name}.v")
    with open(out_path, "w") as f:
        f.write(verilog)
    lines = len(verilog.splitlines())
    total_lines += lines
    print(f"  {out_path} ({lines} lines)")

print(f"\n  Total: {total_lines:,} lines in {len(packages)} files")

# Verify outputs
print("\n" + "=" * 70)
print("Phase 4: Verification")
print("=" * 70)

errors = []
expected_modules = ["PerfCore0", "PerfCore1", "EffCore0", "EffCore1",
                    "L1_0", "L1_1", "L1_2", "L1_3",
                    "NoCRouter_0", "NoCRouter_1", "NoCRouter_2", "NoCRouter_3",
                    "CoherenceDir", "HeteroMeshTop"]

for mod in expected_modules:
    path = os.path.join(output_dir, f"{mod}.v")
    if not os.path.exists(path):
        errors.append(f"MISSING: {mod}.v")
        continue
    with open(path) as f:
        content = f.read()
    has_module = f"module {mod}" in content
    has_clk = "input clk" in content
    has_rst = "input rst_n" in content
    if not has_module:
        errors.append(f"{mod}.v: missing 'module {mod}'")
    print(f"  {mod}: exists=True, module={has_module}, clk={has_clk}, rst={has_rst}")

if errors:
    print("\n  FAIL")
    for e in errors:
        print(f"    ❌ {e}")
    sys.exit(1)
else:
    print(f"\n  PASS — All {len(expected_modules)} modules generated correctly")
    print("=" * 70)
