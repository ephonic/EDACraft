"""
Post-DSL-generation verification pipeline:
  1. Load each generated DSL module
  2. Simulate with rtlgen Simulator (reset test, random stimulus)
  3. Generate cocotb testbenches
  4. Report coverage and fix issues
"""
import importlib.util
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from rtlgen.core import Module as CoreModule
from rtlgen.sim import Simulator


def load_dsl_module(filepath: str) -> Optional[type]:
    """Dynamically load a generated DSL .py file and return the Module class."""
    mod_name = os.path.basename(filepath).replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, filepath)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"    [IMPORT FAIL] {mod_name}: {e}")
        return None

    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and issubclass(attr, CoreModule) and attr is not CoreModule:
            return attr
    return None


def test_reset(cls: type, rst_name: str = "rst_n") -> Tuple[bool, List[str]]:
    """Test that all outputs are zero after reset."""
    issues = []
    try:
        inst = cls()
    except Exception as e:
        return False, [f"Instantiation failed: {e}"]

    sim = Simulator(inst, use_xz=False)
    sim.reset(rst=rst_name, cycles=3)

    for out_name in inst._outputs:
        val = int(sim.get(out_name))
        if val != 0:
            issues.append(f"  output '{out_name}' = {val} after reset (expected 0)")

    return len(issues) == 0, issues


def test_random_stimulus(cls: type, num_cycles: int = 20, rst_name: str = "rst_n") -> Tuple[bool, List[str], Dict]:
    """Run random stimulus and check for crashes + toggle coverage."""
    issues = []
    coverage = {"inputs": set(), "outputs": set(), "toggled": set()}

    import random
    random.seed(42)

    try:
        inst = cls()
    except Exception as e:
        return False, [f"Instantiation failed: {e}"], coverage

    sim = Simulator(inst, use_xz=False)
    sim.reset(rst=rst_name, cycles=3)

    prev_outs = {}
    try:
        for cycle in range(num_cycles):
            for in_name in inst._inputs:
                if in_name in ("clk", rst_name, "rst"):
                    continue
                width = inst._inputs[in_name].width
                val = random.randint(0, (1 << min(width, 16)) - 1)
                sim.set(in_name, val)
                coverage["inputs"].add(in_name)

            sim.step()

            for out_name in inst._outputs:
                val = int(sim.get(out_name))
                coverage["outputs"].add(out_name)
                if out_name in prev_outs and prev_outs[out_name] != val:
                    coverage["toggled"].add(out_name)
                prev_outs[out_name] = val

    except Exception as e:
        return False, [f"Random sim crashed at cycle {cycle}: {e}"], coverage

    return True, issues, coverage


def fix_common_issues(filepath: str) -> bool:
    """Auto-fix common code generation issues."""
    with open(filepath) as f:
        content = f.read()

    fixes_applied = 0

    # Fix: Reg declarations that have output names conflicting (e.g. self.xxx = Reg and self.xxx = Output)
    # Find registers that are also declared as ports
    reg_lines = re.findall(r'^\s+(\w+)\s*=\s*Reg\(', content, re.MULTILINE)
    port_lines = set(re.findall(r'^\s+self\.(\w+)\s*=\s*(Input|Output)\(', content, re.MULTILINE))

    for rname in reg_lines:
        if rname in port_lines:
            # This register shadows a port - rename with _reg suffix
            content = content.replace(f"        {rname} = Reg(", f"        {rname}_reg = Reg(")
            content = content.replace(f"                {rname} <<=", f"                {rname}_reg <<=")
            fixes_applied += 1

    # Fix: Const(001, 3) leading zeros
    content = re.sub(r'Const\(0+(\d+),', lambda m: f'Const({int(m.group(1))},', content)

    # Fix: pc <<= Const(0x1000, XX) for non-PC registers
    # (leave as-is, it's valid)

    # Write back if changed
    if fixes_applied > 0:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


def run_verification(specs_dir: str, dsl_dir: str, output_dir: str):
    """Run complete verification on generated DSL modules."""
    print("=" * 60)
    print("DSL Verification Pipeline")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # Collect all generated DSL files
    dsl_files = sorted([
        os.path.join(dsl_dir, f) for f in os.listdir(dsl_dir)
        if f.endswith(".py") and not f.startswith("_")
    ])

    results = {}
    all_pass = True

    for fpath in dsl_files:
        mod_name = os.path.basename(fpath).replace(".py", "")
        print(f"\n  [{mod_name}]")

        # Step 1: Auto-fix common issues
        if fix_common_issues(fpath):
            print(f"    [FIX] Auto-fixed {mod_name}")

        # Step 2: Load module
        cls = load_dsl_module(fpath)
        if cls is None:
            results[mod_name] = {"status": "import_fail"}
            all_pass = False
            continue

        # Step 3: Reset test
        reset_ok, reset_issues = test_reset(cls)
        for issue in reset_issues:
            print(f"    [RESET FAIL] {issue}")

        # Step 4: Random stimulus test
        stim_ok, stim_issues, coverage = test_random_stimulus(cls, num_cycles=20)
        for issue in stim_issues:
            print(f"    [STIM FAIL] {issue}")

        # Step 5: Coverage metrics
        toggle_pct = 0
        if coverage["outputs"]:
            toggle_pct = round(len(coverage["toggled"]) / len(coverage["outputs"]) * 100, 1)

        status = "PASS" if (reset_ok and stim_ok) else "FAIL"
        if not reset_ok:
            status = "FAIL"
            all_pass = False

        print(f"    [{status}] reset={'OK' if reset_ok else 'FAIL'} "
              f"stim={'OK' if stim_ok else 'FAIL'} "
              f"toggle={toggle_pct}% ({len(coverage['toggled'])}/{len(coverage['outputs'])})")

        results[mod_name] = {
            "status": status,
            "reset_pass": reset_ok,
            "stim_pass": stim_ok,
            "toggle_pct": toggle_pct,
            "toggle_count": len(coverage["toggled"]),
            "output_count": len(coverage["outputs"]),
        }

    # Summary
    print(f"\n{'=' * 60}")
    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    print(f"Summary: {passed}/{total} modules passed")

    for name, r in sorted(results.items()):
        print(f"  {name:25s} [{r['status']:4s}] toggle={r.get('toggle_pct', 0)}%")

    # Save report
    report = {
        "summary": {"total": total, "passed": passed},
        "modules": results,
    }
    report_path = os.path.join(output_dir, "verification_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {report_path}")

    return report


if __name__ == "__main__":
    skill = sys.argv[1] if len(sys.argv) > 1 else "riscv_ooo_4core"
    base = os.path.join("generated_skill_ppa", skill)
    spec_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base, "specs")
    dsl_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(base, "hand_generated")
    out_dir = sys.argv[4] if len(sys.argv) > 4 else os.path.join(base, "verify_run")
    run_verification(spec_dir, dsl_dir, out_dir)
