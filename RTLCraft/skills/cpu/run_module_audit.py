#!/usr/bin/env python3
"""
Comprehensive audit of every Module subclass in skills/cpu/.
Tests: instantiation, Simulator init, reset, step, output-signal read.
"""
import sys, os, traceback, inspect
import importlib.machinery
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from rtlgen.core import Module
from rtlgen.sim import Simulator

EXCLUDE = {"__init__.py", "behaviors.py", "arch_templates.py", "skeleton_templates.py", "run_module_audit.py"}
SKILL_DIR = os.path.join(os.path.dirname(__file__))

def try_default_instantiate(cls):
    """Try to instantiate cls with default args."""
    sig = inspect.signature(cls.__init__)
    params = list(sig.parameters.values())[1:]  # skip self
    kwargs = {}
    for p in params:
        if p.default is not inspect.Parameter.empty:
            kwargs[p.name] = p.default
        elif p.kind == inspect.Parameter.VAR_KEYWORD:
            pass
        else:
            # positional-without-default — inject best guess
            kwargs[p.name] = _guess_param(p.name, p.annotation)
    return cls(**kwargs)

def _guess_param(name, annotation):
    guesses = {
        "width": 64,
        "PC_WIDTH": 39,
        "pr_num": 64,
        "ar_num": 32,
        "entries": 8,
        "depth": 8,
        "n_src": 9,
        "reset_val": 0,
        "reset_vec": 0,
        "XLEN": 64,
        "tag_width": 20,
        "has_l0_btb": False,
        "has_way_pred": False,
    }
    if name in guesses:
        return guesses[name]
    if annotation is int or annotation == int:
        return 64
    if annotation is str or annotation == str:
        return ""
    if annotation is bool or annotation == bool:
        return False
    return 0

def collect_outputs(mod):
    """Return list of (attr_name, signal_name) for every Output signal on mod."""
    outs = []
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name, None)
        if attr is None:
            continue
        if hasattr(attr, "_expr") and hasattr(attr, "name"):
            signal = attr
        elif hasattr(attr, "signal"):
            signal = attr.signal
        else:
            continue
        if signal.name in mod._outputs:
            outs.append((attr_name, signal.name))
    return outs

def main():
    py_files = sorted(
        f for f in os.listdir(SKILL_DIR)
        if f.endswith(".py") and f not in EXCLUDE
    )

    results = []  # (file, class, status, detail)

    for fname in py_files:
        fpath = os.path.join(SKILL_DIR, fname)
        modname = "skills.cpu." + fname[:-3]

        try:
            loader = importlib.machinery.SourceFileLoader(modname, fpath)
            mod = types.ModuleType(modname)
            loader.exec_module(mod)
        except Exception as exc:
            tb = traceback.extract_tb(sys.exc_info()[2])
            last = tb[-1] if tb else None
            lineno = last.lineno if last is not None else "?"
            msg = str(exc).replace("\n", " | ")
            results.append((fname, "<module>", "FAIL-IMPORT", f"{type(exc).__name__}: {msg} (line {lineno})"))
            continue

        # Find all Module subclasses defined in THIS file
        classes = []
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Module) and obj is not Module:
                if obj.__module__ == mod.__name__:
                    classes.append((name, obj))

        if not classes:
            results.append((fname, "(no Module subclasses)", "SKIP", ""))
            continue

        for cls_name, cls in classes:
            # 1) Instantiate
            try:
                instance = try_default_instantiate(cls)
            except Exception as exc:
                tb = traceback.extract_tb(sys.exc_info()[2])
                last = tb[-1] if tb else None
                lineno = last.lineno if last is not None else "?"
                msg = str(exc).replace("\n", " | ")
                results.append((fname, cls_name, "FAIL-INSTANTIATE", f"{type(exc).__name__}: {msg} (line {lineno})"))
                continue

            # 2) Simulator init
            try:
                sim = Simulator(instance, use_xz=False)
            except Exception as exc:
                tb = traceback.extract_tb(sys.exc_info()[2])
                last = tb[-1] if tb else None
                lineno = last.lineno if last is not None else "?"
                msg = str(exc).replace("\n", " | ")
                results.append((fname, cls_name, "FAIL-SIM-INIT", f"{type(exc).__name__}: {msg} (line {lineno})"))
                continue

            # 3) check if module has clock/reset signals
            has_clk = "clk" in instance._inputs
            has_rst = "rst_n" in instance._inputs
            if has_clk and has_rst:
                try:
                    sim.reset(rst="rst_n", cycles=3)
                except Exception as exc:
                    tb = traceback.extract_tb(sys.exc_info()[2])
                    last = tb[-1] if tb else None
                    lineno = last.lineno if last is not None else "?"
                    msg = str(exc).replace("\n", " | ")
                    results.append((fname, cls_name, "FAIL-RESET", f"{type(exc).__name__}: {msg} (line {lineno})"))
                    continue
            else:
                # pure combinational or no clock — just run a step if possible
                pass

            # 4) step (only if clk present)
            if has_clk:
                try:
                    sim.step()
                except Exception as exc:
                    tb = traceback.extract_tb(sys.exc_info()[2])
                    last = tb[-1] if tb else None
                    lineno = last.lineno if last is not None else "?"
                    msg = str(exc).replace("\n", " | ")
                    results.append((fname, cls_name, "FAIL-STEP", f"{type(exc).__name__}: {msg} (line {lineno})"))
                    continue

            # 5) Read all output signals
            outs = collect_outputs(instance)
            read_ok = True
            for attr_name, sig_name in outs:
                try:
                    sim.get(sig_name)
                except Exception as exc:
                    tb = traceback.extract_tb(sys.exc_info()[2])
                    last = tb[-1] if tb else None
                    lineno = last.lineno if last is not None else "?"
                    msg = str(exc).replace("\n", " | ")
                    results.append((fname, cls_name, f"FAIL-READ-OUTPUT({sig_name})", f"{type(exc).__name__}: {msg} (line {lineno})"))
                    read_ok = False
            if read_ok:
                results.append((fname, cls_name, "PASS", ""))

    # Print failures
    passed = 0
    failed = 0
    skipped = 0
    for fname, cls_name, status, detail in results:
        if status == "SKIP":
            skipped += 1
            continue
        if status == "PASS":
            passed += 1
            continue
        failed += 1
        print(f"FAIL  {fname}.{cls_name}: {detail}")

    print()
    print("=" * 60)
    print(f"SUMMARY:  total classes tested = {passed + failed + skipped}")
    print(f"  PASSED  {passed}")
    print(f"  FAILED  {failed}")
    print(f"  SKIPPED {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    main()
