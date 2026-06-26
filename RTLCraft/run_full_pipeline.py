"""
Complete pipeline: behavioral sim → skeleton → specs → DSL generation → verification.
"""
import os
import sys

# ── Step 1: Behavioral simulation ──
print("=" * 60)
print("Step 1: Behavioral Simulation")
print("=" * 60)
from rtlgen.skill_ppa import SkillPPARunner
runner = SkillPPARunner("riscv64_soc")

beh_result = runner._run_behaviors()
print(f"  Behaviors: {'PASS' if beh_result.passed else 'FAIL'}")

arch_result = runner._run_arch()
print(f"  Arch: {'PASS' if arch_result.passed else 'FAIL'}")

skel_result = runner._run_skeleton()
print(f"  Skeleton: {'PASS' if skel_result.passed else 'FAIL'}")

spec_result = runner._run_spec_gen("generated_skill_ppa")
print(f"  Specs: {'PASS' if spec_result.passed else 'FAIL'}")
for k, v in spec_result.metrics.items():
    if 'spec_lines' in k or 'instances' in k or 'spec_success' in k or 'spec_by_type' in k:
        print(f"    {k}: {v}")

# ── Step 2: Generate DSL from all spec files ──
print()
print("=" * 60)
print("Step 2: DSL Generation from Specs")
print("=" * 60)

from rtlgen.dsl_generator import generate_all_from_specs

specs_dir = "generated_skill_ppa/riscv64_soc/specs"
dsl_dir = "generated_skill_ppa/riscv64_soc/generated_dsl"
generated = generate_all_from_specs(specs_dir, dsl_dir)
print(f"  Generated {len(generated)} DSL files")

# Only the types with explicit generators produce output
generator_types = {'rv64_core', 'noc_router', 'l1_cache', 'ifu', 'idu'}
print(f"  Generator coverage: {len(generated)}/{len(generator_types)} spec types with generators")

# ── Step 3: Verify generated DSL with Simulator ──
print()
print("=" * 60)
print("Step 3: DSL Verification with Simulator")
print("=" * 60)

# Try to import and test each generated DSL module
for fpath in generated:
    mod_name = os.path.basename(fpath).replace(".py", "")
    try:
        # Dynamic import
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod_name, fpath)
        if spec is None or spec.loader is None:
            print(f"  [SKIP] {mod_name}: cannot load spec")
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)

        # Find Module class
        cls = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, type(mod.Module if hasattr(mod, 'Module') else object)):
                if attr_name in (mod_name.capitalize(), mod_name, 'NoCBuffer', 'NoCRouter', 'L1Cache', 'IFU', 'IDU'):
                    cls = attr
                    break
        if cls is None:
            # Just try the only Module subclass
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                from rtlgen.core import Module as CoreModule
                if isinstance(attr, type) and issubclass(attr, CoreModule) and attr is not CoreModule:
                    cls = attr
                    break

        if cls is None:
            print(f"  [SKIP] {mod_name}: no Module class found")
            continue

        # Instantiate and quick sim
        inst = cls()
        from rtlgen.sim import Simulator
        sim = Simulator(inst, use_xz=False)
        sim.reset(rst="rst_n", cycles=3)
        # Check outputs are zero after reset
        all_zero = True
        for out_name in getattr(inst, "_outputs", {}):
            val = int(sim.get(out_name))
            if val != 0:
                all_zero = False
        if all_zero:
            print(f"  [PASS] {mod_name}: reset OK ({len(getattr(inst, '_outputs', {}))} outputs zero)")
        else:
            print(f"  [FAIL] {mod_name}: reset failed (outputs not zero)")

    except Exception as e:
        print(f"  [FAIL] {mod_name}: {e}")

print()
print("=" * 60)
print("Pipeline Complete")
print(f"  Specs: {specs_dir}/")
print(f"  DSL:   {dsl_dir}/")
print("=" * 60)
