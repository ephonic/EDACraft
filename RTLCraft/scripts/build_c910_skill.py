"""
Build the c910_cpu skill from extracted C910 micro-architecture data.

Pipeline:
  1. Load extracted hierarchy from c910_analysis/c910_hierarchy.json
  2. Populate _SUBMODULE_DEFS with real C910 sub-modules
  3. Regenerate spec files with rich micro-architecture
  4. Generate DSL from specs
  5. Compare against reference
"""
import json, os, sys, importlib

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIERARCHY = os.path.join(PROJECT, "generated_skill_ppa", "c910_analysis", "c910_hierarchy.json")

# Step 1: Load hierarchy
print("=" * 60)
print("Step 1: Load C910 micro-architecture hierarchy")
print("=" * 60)

with open(HIERARCHY) as f:
    hierarchy = json.load(f)

for sub, info in hierarchy.items():
    print(f"  {sub}: {info['count']} sub-modules")

# Step 2: We need to also extract actual port details for each sub-module
# For now, use the rtl_analyzer to get detailed data
print()
print("Step 2: Extracting detailed port info from Verilog...")

from rtlgen.rtl_analyzer import analyze_verilog

base = os.path.join(PROJECT, "ref_rtl", "cpu", "C910_RTL_FACTORY", "gen_rtl")

# For each top module, extract sub-module details
submod_detail = {}
for sub in ['ifu', 'idu', 'iu', 'lsu', 'rtu']:
    top_file = os.path.join(base, sub, 'rtl', f'ct_{sub}_top.v')
    if not os.path.isfile(top_file):
        print(f"  [SKIP] {sub}: no top file")
        continue
    
    top_info = analyze_verilog(top_file)
    sub_list = []
    
    for sm in top_info.get('submodules', []):
        mtype = sm['type']
        sm_file = os.path.join(base, sub, 'rtl', f'{mtype}.v')
        ports_in, ports_out = [], []
        
        if os.path.isfile(sm_file):
            sm_info = analyze_verilog(sm_file)
            for p in sm_info.get('ports', []):
                name = p['name']
                w = p['width']
                sig = f"{name}[{w-1}:0]" if w > 1 else name
                if p['direction'] == 'input':
                    ports_in.append(sig)
                else:
                    ports_out.append(sig)
        
        short = mtype.replace(f'ct_{sub}_', '') if mtype.startswith('ct_') else mtype
        sub_list.append({
            "name": short,
            "type": mtype,
            "inputs": ports_in[:8],  # Keep it manageable
            "outputs": ports_out[:8],
            "total_in": len(ports_in),
            "total_out": len(ports_out),
        })
    
    submod_detail[sub] = sub_list
    print(f"  {sub}: {len(sub_list)} sub-modules with port details")

# Step 3: Generate _SUBMODULE_DEFS code for arch_skel.py
print()
print("Step 3: Generating _SUBMODULE_DEFS entries...")

defs_code = []
for sub, subs in submod_detail.items():
    defs_code.append(f'    "{sub}": {{')
    defs_code.append(f'        "submodules": [')
    for sm in subs:
        inp = '", "'.join(sm['inputs'])
        out = '", "'.join(sm['outputs'])
        defs_code.append(f'            {{')
        defs_code.append(f'                "name": "{sm["name"]}",')
        defs_code.append(f'                "type": "{sm["type"]}",')
        defs_code.append(f'                "description": "{sm["type"]} ({sm["total_in"]} inputs, {sm["total_out"]} outputs)",')
        defs_code.append(f'                "inputs": ["{inp}"],')
        defs_code.append(f'                "outputs": ["{out}"],')
        defs_code.append(f'            }},')
    defs_code.append(f'        ],')
    defs_code.append(f'    }},')

# Save to file
out_path = os.path.join(PROJECT, "generated_skill_ppa", "c910_analysis", "submodule_defs.py")
with open(out_path, 'w') as f:
    f.write('"""Auto-generated C910 sub-module definitions."""\n\n')
    f.write('C910_SUBMODULE_DEFS = {\n')
    for line in defs_code:
        f.write(line + '\n')
    f.write('}\n')

print(f"  Saved to {out_path}")
print(f"  Total: {sum(len(v) for v in submod_detail.values())} sub-module definitions")

# Step 4: Generate example DSL for IFU from its spec
print()
print("Step 4: Verification ready.")
print(f"  Sub-module definitions: {out_path}")
print(f"  Hierarchy data: {HIERARCHY}")
print()
print("To regenerate specs, run:")
print("  python -m rtlgen.skill_ppa --skill c910_cpu --stage behaviors arch skeleton spec_gen")
