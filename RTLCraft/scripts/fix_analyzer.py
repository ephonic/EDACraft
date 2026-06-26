"""Fix and test the C910 analyzer."""
import re, os, json
from rtlgen.rtl_analyzer import analyze_verilog

base = 'ref_rtl/cpu/C910_RTL_FACTORY/gen_rtl'

# Analyze ALL IFU modules (not just top)
all_modules = {}
for root, dirs, files in os.walk(os.path.join(base, 'ifu/rtl')):
    for f in files:
        if not f.endswith('.v'): continue
        fp = os.path.join(root, f)
        info = analyze_verilog(fp)
        all_modules[info['module_name']] = info

# Extract IFU sub-module hierarchy from ct_ifu_top
top = all_modules.get('ct_ifu_top', {})
subs = top.get('submodules', [])

# Generate _SUBMODULE_DEFS entry
print("=== IFU sub-module hierarchy ===")
submod_defs = []
for sm in subs:
    mtype = sm['type']
    minfo = all_modules.get(mtype, {})
    ports_in = [p['name'] for p in minfo.get('ports', []) if p['direction'] == 'input']
    ports_out = [p['name'] for p in minfo.get('ports', []) if p['direction'] == 'output']
    n_regs = len(minfo.get('regs', []))
    print(f"  {mtype:35s} in={len(ports_in):3d} out={len(ports_out):3d} regs={n_regs:3d} ports={len(minfo.get('ports',[])):3d}")
    
    # Build submod_def for _SUBMODULE_DEFS
    # Only include significant modules (not SRAM wrappers)
    if 'spsram' not in mtype and ports_in:
        submod_defs.append({
            "name": sm['name'].replace('x_ct_ifu_', ''),
            "type": mtype.replace('ct_ifu_', ''),
            "inputs": [f"{p}[63:0]" if any(w in p.lower() for w in ['addr','data','rdata','wdata','target','pc']) else p 
                      for p in ports_in[:8]],
            "outputs": [f"{p}[63:0]" if any(w in p.lower() for w in ['addr','data','rdata','wdata','target','pc']) else p 
                       for p in ports_out[:8]],
        })

print(f"\nGenerated {len(submod_defs)} sub-module definitions")
print(f"\nSample _SUBMODULE_DEFS entry:")
for sd in submod_defs[:3]:
    print(f"  {sd['type']}: {len(sd['inputs'])} inputs, {len(sd['outputs'])} outputs")
