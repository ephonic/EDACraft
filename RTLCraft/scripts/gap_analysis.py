"""
Gap analysis: compare generated framework against C910 reference RTL.

Outputs a structured report showing:
  - What modules exist in C910 but not in our framework
  - What features are missing or incomplete
  - Estimated effort to close each gap
"""
import os, re, sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REF_DIR = os.path.join(PROJECT, "ref_rtl", "cpu", "C910_RTL_FACTORY", "gen_rtl")
SKILL_DIR = os.path.join(PROJECT, "skills", "cpu")

def scan_c910_modules():
    """Scan C910 RTL directory for all module names."""
    modules = {}
    for root, dirs, files in os.walk(REF_DIR):
        for f in files:
            if not f.endswith(".v"): continue
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            # Find module declarations
            for m in re.finditer(r'module\s+(\w+)\s*\(', content):
                name = m.group(1)
                lines = content.count("\n") + 1
                ports = content[:content.find(";")].count(",") + 1 if ";" in content[:200] else 0
                if name not in modules:
                    modules[name] = {"file": f, "path": path, "lines": lines, "ports": ports}
    return modules

def scan_skill_modules():
    """Scan skill's dsl_modules.py for all Module classes."""
    dsl_path = os.path.join(SKILL_DIR, "dsl_modules.py")
    if not os.path.isfile(dsl_path):
        return {}
    with open(dsl_path) as f:
        content = f.read()
    classes = re.findall(r'class\s+(\w+)\(Module\)', content)
    return {c: {"lines": content.count("\n") + 1} for c in classes}

def generate_report():
    c910 = scan_c910_modules()
    skill = scan_skill_modules()
    
    print("=" * 70)
    print("C910 Reference RTL vs RTLCraft CPU Skill — Gap Analysis")
    print("=" * 70)
    
    # Group C910 modules by subsystem
    subsystems = {}
    for name, info in c910.items():
        prefix = name.split("_")[0] if "_" in name else "other"
        sub = {"ifu": "IFU", "idu": "IDU", "iu": "IU", "lsu": "LSU",
               "rtu": "RTU", "mmu": "MMU", "l2c": "L2C", "biu": "BIU",
               "cp0": "CP0", "clk": "CLK", "rst": "RST", "pmp": "PMP",
               "pmu": "PMU", "plic": "PLIC", "had": "HAD", "vf": "VFPU",
               "ciu": "CIU", "clint": "CLINT", "fpga": "FPGA"}.get(prefix, "OTHER")
        if sub not in subsystems:
            subsystems[sub] = {"count": 0, "lines": 0, "modules": []}
        subsystems[sub]["count"] += 1
        subsystems[sub]["lines"] += info["lines"]
        subsystems[sub]["modules"].append(name)
    
    print(f"\n{'Subsystem':15s} {'C910 RTL':>10s} {'Skill DSL':>10s} {'Coverage':>10s}")
    print("-" * 50)
    
    total_c910 = 0
    total_skill = 0
    
    for sub in sorted(subsystems.keys()):
        c = subsystems[sub]
        s_count = sum(1 for sk in skill if sk.upper().startswith(sub[:3]))
        pct = min(100, int(s_count / max(c["count"], 1) * 100)) if c["count"] > 0 else 0
        print(f"{sub:15s} {c['count']:4d} mods/{c['lines']//1000:3d}K {s_count:4d} mods       {pct:3d}%")
        total_c910 += c["lines"]
        total_skill += s_count * 300  # rough estimate
    
    print("-" * 50)
    print(f"{'TOTAL':15s} {sum(s['count'] for s in subsystems.values()):4d} mods/{total_c910//1000:3d}K {len(skill):4d} mods")
    print()
    
    # Cross-reference: which C910 modules have matching DSL classes?
    c910_names_lower = {n.lower(): n for n in c910}
    skill_names_lower = {n.lower(): n for n in skill}
    
    missing = []
    partial = []
    
    for cname_lower, cname in sorted(c910_names_lower.items()):
        if cname_lower in skill_names_lower:
            partial.append(cname)
        elif any(sk_lower in cname_lower or cname_lower in sk_lower for sk_lower in skill_names_lower):
            partial.append(cname)
        else:
            missing.append(cname)
    
    print(f"\n{'='*70}")
    print(f"Key C910 Modules NOT in DSL ({len(missing)} total)")
    print(f"{'='*70}")
    for m in missing[:30]:
        info = c910[m]
        print(f"  {m:40s} ({info['lines']:5d} lines, {info['file']:30s})")
    if len(missing) > 30:
        print(f"  ... and {len(missing)-30} more")
    
    print(f"\n{'='*70}")
    print("Recommended Next Modules to Build (by gap size)")
    print(f"{'='*70}")
    
    # Prioritize modules that are large and central to pipeline
    priority = ["ct_ifu_top", "ct_idu_top", "ct_iu_top", "ct_lsu_top", "ct_rtu_top",
                "ct_ifu_pcgen", "ct_ifu_bht", "ct_ifu_btb", "ct_ifu_ras",
                "ct_idu_ir_rt", "ct_idu_is_aiq0", "ct_idu_is_aiq1",
                "ct_iu_alu", "ct_iu_bju", "ct_iu_mult",
                "ct_lsu_lq", "ct_lsu_sq", "ct_lsu_dc",
                "ct_rtu_rob", "ct_rtu_retire",
                "ct_mmu_iutlb", "ct_mmu_jtlb", "ct_mmu_ptw",
                "ct_l2c_top", "ct_biu_top"]
    
    for m in priority:
        if m in c910:
            info = c910[m]
            print(f"  {m:40s} ({info['lines']:5d} lines, {info['ports']:3d} ports)")


if __name__ == "__main__":
    generate_report()
