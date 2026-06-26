"""
Fix template name mismatches between arch_templates.py and behaviors.py.

For each skill:
  1. Read arch_templates.py → find all imported _template names
  2. Read behaviors.py → find all defined function names
  3. Add missing aliases so imports work
"""
import glob
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(PROJECT, "skills")


def get_expected_templates(skill_key: str) -> list:
    """Read arch_templates.py and extract all imported template names."""
    at_path = os.path.join(SKILLS, skill_key, "arch_templates.py")
    if not os.path.isfile(at_path):
        return []
    
    with open(at_path) as f:
        content = f.read()
    
    # Find `from skills.X.behaviors import (...)`
    m = re.search(r'from skills\.\S+\.behaviors import \((.*?)\)', content, re.DOTALL)
    if not m:
        m = re.search(r'from skills\.\S+\.behaviors import (\w+)', content)
        if m:
            return [m.group(1)]
        return []
    
    names = re.findall(r'(\w+_template)', m.group(1))
    return names


def get_available_names(skill_key: str) -> dict:
    """Read behaviors.py and extract all defined function/alias names."""
    bh_path = os.path.join(SKILLS, skill_key, "behaviors.py")
    if not os.path.isfile(bh_path):
        return {}
    
    with open(bh_path) as f:
        lines = f.readlines()
    
    names = {}
    for line in lines:
        # def name(...)
        m = re.match(r'^def (\w+)\(', line)
        if m:
            names[m.group(1)] = "def"
        # name = expression (alias)
        m = re.match(r'^(\w+)\s*=\s*(\w+)', line)
        if m:
            names[m.group(1)] = f"alias:{m.group(2)}"
        # _template_map registration
        m = re.match(r'^\s*"(\w+)":\s*(\w+),?\s*(#.*)?$', line)
        if m:
            names[m.group(1)] = f"reg:{m.group(2)}"
    
    return names


def find_closest_match(expected: str, available: dict) -> str:
    """Find the closest matching function in available names."""
    base = expected.replace("_template", "").replace("_", "")
    base_lower = base.lower()
    
    # Direct match (without _template suffix)
    if base in available:
        return base
    if base_lower in available:
        return base_lower
    
    # Fuzzy: find any def whose name contains the base or vice versa
    for name, kind in available.items():
        if kind != "def":
            continue
        n_clean = name.replace("_", "").lower()
        if base_lower in n_clean or n_clean in base_lower:
            return name
    
    # Fuzzy: check aliases too
    for name, kind in available.items():
        if not kind.startswith("alias:"):
            continue
        target = kind.split(":")[1]
        n_clean = name.replace("_", "").lower()
        t_clean = target.replace("_", "").lower()
        if base_lower in n_clean or n_clean in base_lower:
            return name
        if base_lower in t_clean:
            return name
    
    return None


def fix_skill(skill_key: str, dry_run: bool = False):
    """Fix template aliases for one skill. Returns None if no arch_templates, True if fixed, False if already OK."""
    bh_path = os.path.join(SKILLS, skill_key, "behaviors.py")
    if not os.path.isfile(bh_path):
        return None
    
    expected = get_expected_templates(skill_key)
    if not expected:
        return None  # no arch_templates
    
    available = get_available_names(skill_key)
    
    with open(bh_path) as f:
        content = f.read()
    
    # Check which expected names are already defined
    already = set()
    for line in content.split("\n"):
        for n in expected:
            if line.startswith(n + " =") or line.startswith("def " + n):
                already.add(n)
    
    missing = [n for n in expected if n not in already]
    
    if not missing:
        return False  # all good
    
    # For each missing name, find the closest available function
    new_lines = []
    new_lines.append("\n\n# === Auto-fixed aliases for arch_templates ===\n")
    for name in missing:
        match = find_closest_match(name, available)
        if match:
            new_lines.append(f"{name} = {match}\n")
    
    if not new_lines:
        return False
    
    if dry_run:
        print(f"  {skill_key}: would add {len(missing)} aliases: {', '.join(missing)}")
        return True
    
    # Append to end of file
    with open(bh_path, "a") as f:
        f.writelines(new_lines)
    
    print(f"  [FIX] {skill_key}: added {len(missing)} aliases: {', '.join(missing)}")
    return True


def main(dry_run: bool = False):
    all_skills = [
        "cpu", "dsp", "fft", "gpgpu", "hetero_riscv4", "noc", "npu", "riscv64_soc",
        "codec/ldpc", "codec/video", "image/isp",
        "interfaces/axi", "interfaces/axi_lite", "interfaces/axis",
        "interfaces/btle", "interfaces/ethernet", "interfaces/i2c",
        "interfaces/pcie", "interfaces/spi", "interfaces/uart", "interfaces/wishbone",
        "mem/cam", "mem/ddr3",
    ]
    
    fixed = 0
    ok = 0
    skipped = 0
    
    for sk in all_skills:
        try:
            result = fix_skill(sk, dry_run)
            if result is None:
                skipped += 1
            elif result:
                fixed += 1
            else:
                ok += 1
        except Exception as e:
            print(f"  [ERR] {sk}: {e}")
    
    action = "Dry run" if dry_run else "Fixed"
    print(f"\n{action}: {fixed} skills, {ok} already OK, {skipped} skipped")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
