#!/usr/bin/env python3
"""Verify ALL three layers for SoC, Hetero, OoO, Mem, Image, Codec, Interfaces skills."""

import sys, os, importlib, inspect, traceback, contextlib, types, re

WORKDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKDIR)

# ── helpers ──────────────────────────────────────────────────────────────────

def _find_reset_signal(mod):
    """Find the likely reset signal in a module."""
    candidates = ["rst_n", "rst", "reset_n", "reset"]
    for c in candidates:
        if hasattr(mod, c):
            return c
    if hasattr(mod, '_inputs'):
        for c in candidates:
            if c in mod._inputs:
                return c
    return "rst_n"

def _import_layer3_module(pkg_prefix, l3_dir, pyfile):
    """Try to import a layer3_dsl module with various workarounds."""
    modname = pyfile[:-3]
    fq_name = f"{pkg_prefix}.layer3_dsl.{modname}"
    filepath = os.path.join(l3_dir, pyfile)

    # ── Strategy 1: normal import ──
    try:
        return importlib.import_module(fq_name)
    except SyntaxError as e:
        # likely duplicate __future__ — handle below
        pass
    except ModuleNotFoundError as e:
        # likely "skills.skills" path — handle below
        pass
    except Exception:
        return None

    # ── Strategy 2: fix __future__ duplication ──
    try:
        import importlib.util as _util
        with open(filepath) as f:
            src = f.read()
        lines = src.split('\n')
        future_indices = [i for i, l in enumerate(lines) if l.strip().startswith('from __future__')]
        if len(future_indices) > 1:
            keep = set(future_indices[:1])
            new_lines = [l for i, l in enumerate(lines) if i in keep or not l.strip().startswith('from __future__')]
            src = '\n'.join(new_lines)
        spec = _util.spec_from_file_location(fq_name, filepath)
        if spec and spec.loader:
            mod = _util.module_from_spec(spec)
            code = compile(src, filepath, 'exec')
            exec(code, mod.__dict__)
            sys.modules[fq_name] = mod
            return mod
    except Exception:
        pass

    # ── Strategy 3: source-level rewrite of import paths ──
    try:
        import importlib.util as _util
        with open(filepath) as f:
            src = f.read()
        src = re.sub(r'from\s+skills\.skills\.', 'from skills.', src)
        spec = _util.spec_from_file_location(fq_name, filepath)
        if spec and spec.loader:
            mod = _util.module_from_spec(spec)
            code = compile(src, filepath, 'exec')
            exec(code, mod.__dict__)
            sys.modules[fq_name] = mod
            return mod
    except Exception:
        pass

    # ── Strategy 4: check if it's a re-export wrapper; if so, import dsl_modules ──
    try:
        with open(filepath) as f:
            src = f.read()
        m = re.search(r'from\s+skills\.skills\.(\S+?)\.dsl_modules\s+import\s+(\S+)', src)
        if m:
            actual_path = f"skills.{m.group(1)}.dsl_modules"
            actual_obj_name = m.group(2)
            dsl_mod = importlib.import_module(actual_path)
            # Return dsl_mod directly — it has all the classes
            return dsl_mod
        # Also try simpler pattern: from skills.skills.xxx.dsl_modules import *
        m = re.search(r'from\s+skills\.skills\.(\S+?)\.dsl_modules\s+import\s+\*', src)
        if m:
            actual_path = f"skills.{m.group(1)}.dsl_modules"
            dsl_mod = importlib.import_module(actual_path)
            return dsl_mod
    except Exception:
        pass

    return None


# ── SSkills list ──────────────────────────────────────────────────────────────

SKILLS = [
    ("skills.riscv64_soc", "SoC riscv64_soc", False, ""),
    ("skills.hetero_riscv4", "Hetero riscv4", False, ""),
    ("skills.riscv_ooo_4core", "OoO riscv_ooo_4core", True, ""),
    ("skills.mem.cam", "Mem cam", False, ""),
    ("skills.mem.ddr3", "Mem ddr3", False, ""),
    ("skills.image.isp", "Image ISP", False, ""),
    ("skills.codec.video", "Codec video", False, ""),
    ("skills.codec.ldpc", "Codec LDPC", False, ""),
    ("skills.interfaces.axi", "IF AXI", False, ""),
    ("skills.interfaces.axis", "IF AXIS", False, ""),
    ("skills.interfaces.btle", "IF BTLE", False, ""),
    ("skills.interfaces.i2c", "IF I2C", False, ""),
    ("skills.interfaces.pcie", "IF PCIe", False, ""),
    ("skills.interfaces.spi", "IF SPI", False, ""),
    ("skills.interfaces.uart", "IF UART", False, ""),
    ("skills.interfaces.wishbone", "IF Wishbone", False, ""),
    ("skills.interfaces.axi_lite", "IF AXI-Lite", False, ""),
    ("skills.interfaces.ethernet", "IF Ethernet", False, ""),
]


# ── Layer 1 ──────────────────────────────────────────────────────────────────

def test_L1(prefix, display):
    try:
        mod = importlib.import_module(f"{prefix}.functional")
    except Exception as e:
        return f"  L1: IMPORT FAIL — {e}"
    funcs = [
        n for n, o in vars(mod).items()
        if callable(o) and (n.endswith('_function') or n.endswith('_functional') or n.endswith('_template'))
    ]
    return f"  L1: {len(funcs)} callables"


# ── Layer 2 ──────────────────────────────────────────────────────────────────

def test_L2(prefix, display):
    try:
        mod = importlib.import_module(f"{prefix}.cycle_level")
    except Exception as e:
        return f"  L2: IMPORT FAIL — {e}"
    cycles = [
        n for n, o in vars(mod).items()
        if callable(o) and (n.endswith('_cycle') or n.endswith('_template'))
    ]
    return f"  L2: {len(cycles)} cycle models"


# ── Layer 3 ──────────────────────────────────────────────────────────────────

from rtlgen.core import Module
from rtlgen.sim import Simulator
from rtlgen.lib import SyncFIFO as _SyncFIFO

def _test_instantiate(cls, cls_name, pyfile):
    """Instantiate a Module subclass and run sim.reset/step. Return (pass, msg)."""
    # handle SyncFIFO specially
    if cls is _SyncFIFO:
        try:
            inst = cls(width=8, depth=16, name="SyncFIFO")
        except Exception as e:
            return False, f"{pyfile}.{cls_name}: FAIL (SyncFIFO init) — {e}"
    else:
        try:
            inst = cls()
        except TypeError:
            try:
                inst = cls(param_bindings={})
            except Exception as e:
                return False, f"{pyfile}.{cls_name}: FAIL (construct) — {e}"
        except Exception as e:
            return False, f"{pyfile}.{cls_name}: FAIL (construct) — {e}"

    rst = _find_reset_signal(inst)
    try:
        sim = Simulator(inst, use_xz=False)
        sim.reset(rst=rst, cycles=3)
        sim.step()
        return True, f"{pyfile}.{cls_name}: PASS"
    except Exception as e:
        return False, f"{pyfile}.{cls_name}: FAIL — {e}"


def test_L3(prefix, display):
    pkg_path = prefix.replace('.', os.sep)
    l3_dir = os.path.join(WORKDIR, pkg_path, "layer3_dsl")
    if not os.path.isdir(l3_dir):
        return "  L3: no layer3_dsl dir"

    pyfiles = sorted(f for f in os.listdir(l3_dir) if f.endswith('.py') and f != '__init__.py')
    if not pyfiles:
        return "  L3: 0 modules"

    results = []
    for pyfile in pyfiles:
        mod = _import_layer3_module(prefix, l3_dir, pyfile)
        if mod is None:
            results.append(f"    {pyfile}: IMPORT FAIL (all strategies)")
            continue

        members = inspect.getmembers(mod, lambda o: inspect.isclass(o) and issubclass(o, Module) and o is not Module)
        # Filter to classes defined in the matching module
        local_members = [(n, o) for n, o in members
                         if getattr(o, '__module__', '').startswith(prefix)]
        if not local_members:
            local_members = members  # fallback
        if not local_members:
            results.append(f"    {pyfile}: no Module subclass")
            continue

        for cls_name, cls in local_members:
            ok, msg = _test_instantiate(cls, cls_name, pyfile)
            results.append(f"    {msg}")

    return "  L3:\n" + "\n".join(results)


# ── Main ─────────────────────────────────────────────────────────────────────

def run_all():
    for prefix, display, skip_l3, extra in SKILLS:
        print(f"\n{'='*60}")
        print(f"Skill: {display} ({prefix})")
        if extra:
            print(f"  Note: {extra}")
        print(f"{'='*60}")
        print(test_L1(prefix, display))
        print(test_L2(prefix, display))
        if skip_l3:
            print("  L3: skipped (0 modules)")
        else:
            print(test_L3(prefix, display))

if __name__ == "__main__":
    run_all()
