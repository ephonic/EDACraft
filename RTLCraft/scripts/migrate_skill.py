"""
Migrate a skill from four-layer (behaviors.py) to three-layer (functional.py + cycle_level.py + layer3_dsl/).

Usage: python3 scripts/migrate_skill.py <skill_name>
"""
import sys, os, importlib, inspect

def migrate_skill(skill_name: str, dry_run: bool = True):
    skill_dir = f"skills/{skill_name}"
    if not os.path.isdir(skill_dir):
        print(f"❌ skills/{skill_name}/ not found")
        return
    
    beh_path = os.path.join(skill_dir, "behaviors.py")
    dsl_path = os.path.join(skill_dir, "dsl_modules.py")
    func_path = os.path.join(skill_dir, "functional.py")
    cycle_path = os.path.join(skill_dir, "cycle_level.py")
    dsl_dir = os.path.join(skill_dir, "layer3_dsl")
    
    changes = []
    
    # Step 1: Extract L1 functional models → functional.py
    if os.path.exists(beh_path) and not os.path.exists(func_path):
        with open(beh_path) as f:
            beh_content = f.read()
        
        # Extract Layer 1 section (between "Layer 1" and "Layer 2" markers)
        l1_start = beh_content.find("Layer 1:")
        l2_start = beh_content.find("Layer 2:")

        import re
        # Find all function definitions between L1 and L2 markers
        l1_section = ""
        if l1_start >= 0 and l2_start > l1_start:
            l1_section = beh_content[l1_start:l2_start]
        
        # Extract all *_functional functions
        func_match = re.findall(r'(def \w+_functional\(.*?)(?=\n\ndef |\n# ===|\Z)', l1_section, re.DOTALL)
        
        if func_match:
            func_code = '\n\n'.join(f.strip() for f in func_match)
            func_content = f'''"""
skills.{skill_name}.functional — Layer 1: Behavioral models (no timing).
Auto-migrated from behaviors.py.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

{func_code}
'''
            if not dry_run:
                with open(func_path, 'w') as f:
                    f.write(func_content)
            changes.append(f"  functional.py: {len(func_match)} functions")
    
    # Step 2: Extract L2 cycle models → cycle_level.py
    if os.path.exists(beh_path) and not os.path.exists(cycle_path):
        with open(beh_path) as f:
            beh_content = f.read()
        
        # Find all *_cycle functions
        import re
        cycle_matches = re.findall(r'(def \w+_cycle\(.*?)(?=\n\ndef |\n# ===|\Z)', beh_content, re.DOTALL)
        
        if cycle_matches:
            cycle_code = '\n\n'.join(f.strip() for f in cycle_matches)
            # Add TemplateRegistry registrations
            func_names = re.findall(r'def (\w+_cycle)\(', '\n'.join(cycle_matches))
            registry_lines = []
            for fn in func_names:
                key = fn.replace('_cycle', '')
                registry_lines.append(f"TemplateRegistry.register('{key}', {fn})")
            
            cycle_content = f'''"""
skills.{skill_name}.cycle_level — Layer 2: Cycle-accurate models.
Auto-migrated from behaviors.py.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry
from rtlgen.behaviors import fifo_template, datapath_template

{cycle_code}

# Template registrations
{chr(10).join(registry_lines)}
'''
            if not dry_run:
                with open(cycle_path, 'w') as f:
                    f.write(cycle_content)
            changes.append(f"  cycle_level.py: {len(cycle_matches)} models + registrations")
    
    # Step 3: Split dsl_modules.py → layer3_dsl/ directory
    if os.path.exists(dsl_path):
        if not os.path.isdir(dsl_dir):
            if not dry_run:
                os.makedirs(dsl_dir, exist_ok=True)
            changes.append(f"  layer3_dsl/: created")
        
        # Read dsl_modules.py and find all Module subclasses
        spec = importlib.util.spec_from_file_location(f'skills.{skill_name}.dsl_modules', dsl_path)
        try:
            mod = importlib.util.module_from_spec(spec)
            if not dry_run:
                spec.loader.exec_module(mod)
            else:
                pass  # Can't exec in dry-run without loading
            
            from rtlgen.core import Module
            found = 0
            if not dry_run:
                spec.loader.exec_module(mod)
                for name, obj in inspect.getmembers(mod):
                    if inspect.isclass(obj) and issubclass(obj, Module) and obj is not Module:
                        # Write individual file
                        file_path = os.path.join(dsl_dir, f"{name.lower()}.py")
                        # Can't easily extract source from exec'd module
                        # Instead, create a simple import re-export
                        content = f'''"""
{name} — Auto-extracted from dsl_modules.py.
"""
from skills.{skill_name}.dsl_modules import {name}
'''
                        with open(file_path, 'w') as f:
                            f.write(content)
                        found += 1
                changes.append(f"  layer3_dsl/: {found} modules extracted")
        except Exception as e:
            changes.append(f"  layer3_dsl/: SKIP - {e}")
    
    # Step 4: Update behaviors.py to be a thin shim
    if os.path.exists(beh_path) and not dry_run:
        # Check if it already imports from functional/cycle_level
        with open(beh_path) as f:
            content = f.read()
        if 'functional' not in content and 'cycle_level' not in content:
            # Add imports at top
            new_beh = f'''"""
skills.{skill_name}.behaviors — Framework compatibility shim.
Layer 1 → functional.py, Layer 2 → cycle_level.py, Layer 3 → layer3_dsl/
"""
from skills.{skill_name}.functional import *
from skills.{skill_name}.cycle_level import *
'''
            with open(beh_path, 'w') as f:
                f.write(new_beh)
            changes.append(f"  behaviors.py: updated to thin shim")
    
    # Report
    print(f"\n=== skills/{skill_name}/ migration ===")
    for c in changes:
        print(c)
    if dry_run:
        print("\n(Dry run — use --apply to write files)")

if __name__ == '__main__':
    apply = '--apply' in sys.argv
    skills = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not skills:
        skills = ['dsp', 'fft', 'gpgpu', 'hetero_riscv4', 'noc', 'npu', 'riscv64_soc']
    
    for sk in skills:
        migrate_skill(sk, dry_run=not apply)
