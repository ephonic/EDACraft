"""Document generator for the Thor-GPGPU document-driven flow.

This module extracts real design data from the per-layer source files (via each
layer's ``describe()`` function) and renders the industrial-pattern templates in
``doc_templates/`` with meaningful content. It also runs each layer's pytest
suite to fill the test reports with real pass/fail counts, and emits Verilog
for every module via the L6 emitter.

It is a project-aware adaptation of ``earphone/docgen.py``: it discovers
modules under ``thor_gpu/modules``, calls each layer's ``describe()``, and
fills the layer_spec / test_plan / test_report templates.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from doc_templates import default_variables, read_template, render_template


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return ""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _bullet_list(items: List[str]) -> str:
    if not items:
        return "_None defined._"
    return "\n".join(f"- {it}" for it in items)


def _test_objective(name: str, obj: Any) -> str:
    doc = inspect.getdoc(obj) or ""
    if doc:
        return doc.splitlines()[0]
    return f"Validate {name.removeprefix('test_').replace('_', ' ')}."


_LAYER_ORDER = [
    ("L1_behavior", "behavior", "01_behavior_spec.md"),
    ("L2_cycle", "cycle", "02_cycle_spec.md"),
    ("L3_architecture", "arch", "03_architecture_spec.md"),
    ("L4_structure", "structure", "04_structural_spec.md"),
    ("L5_dsl", "dsl", "05_dsl_spec.md"),
    ("L6_verilog", "emitter", "06_verilog_spec.md"),
]

_MODULE_DISPLAY = {
    "vector_alu": "ThorVectorALU",
    "vector_fpu": "ThorVectorFPU",
    "tensor_core": "ThorTensorCore",
    "warp_scheduler": "ThorWarpScheduler",
    "simt_stack": "ThorSIMTStack",
    "lsu": "ThorLSU",
    "shared_memory": "ThorSharedMemory",
    "gpu_sm": "ThorGpuSM",
    "gpu_cluster": "ThorCluster",
}

_MODULE_BRIEF = {
    "vector_alu": "8-lane INT32 vector ALU with per-lane active-mask predication (1-cycle registered).",
    "vector_fpu": "8-lane IEEE-754 FP32 vector FPU (FADD/FMUL/FMADD) with per-lane predication.",
    "tensor_core": "8x8x8 INT8->INT32 matrix-multiply-accumulate (MMA) unit.",
    "warp_scheduler": "Sticky round-robin warp scheduler (4 warps) with barrier synchronization.",
    "simt_stack": "SIMT divergence/reconvergence stack for conditional branches.",
    "lsu": "Vector load/store unit with memory request/response handshake.",
    "shared_memory": "Per-SM single-port shared SRAM (256-bit word, 4096 deep, registered read).",
    "gpu_sm": "Streaming multiprocessor: scheduler + SIMT core + exec units + LSU + shared memory.",
    "gpu_cluster": "2-SM compute cluster with a round-robin L2 arbiter over global memory (cluster top).",
}


def _layer_dir(layer: str) -> str:
    return f"layer_{layer}"


def _layer_index(layer: str) -> int:
    return next(i for i, (n, _, _) in enumerate(_LAYER_ORDER) if n == layer)


def _layer_artifact(layer: str) -> Tuple[str, str]:
    spec_name = _LAYER_ORDER[_layer_index(layer)][2]
    prefix = spec_name.split("_spec.md")[0]
    base = os.path.join(_layer_dir(layer), "specs")
    return os.path.join(base, spec_name), prefix


def _previous_layer(layer: str) -> Optional[str]:
    idx = _layer_index(layer)
    return _LAYER_ORDER[idx - 1][0] if idx > 0 else None


def _next_layer(layer: str) -> Optional[str]:
    idx = _layer_index(layer)
    return _LAYER_ORDER[idx + 1][0] if idx < len(_LAYER_ORDER) - 1 else None


def _layer_doc_id(module_name: str, layer: str) -> str:
    return f"{module_name.upper()}-{layer.upper()}-001"


def _layer_input_contract(module_name: str, layer: str) -> str:
    prev = _previous_layer(layer)
    display = _MODULE_DISPLAY.get(module_name, module_name)
    if prev is None:
        return (f"Consumes the module contract `{module_name.upper()}-MOD-001` "
                f"and the Thor-GPGPU top-level SoC requirements as the seed SpecIR.")
    spec_path, _ = _layer_artifact(prev)
    return (f"Consumes approved outputs from `{_layer_doc_id(module_name, prev)}` "
            f"(`{spec_path}`) as input to `{_layer_doc_id(module_name, layer)}`.")


def _layer_output_contract(module_name: str, layer: str) -> str:
    nxt = _next_layer(layer)
    spec_path, _ = _layer_artifact(layer)
    display = _MODULE_DISPLAY.get(module_name, module_name)
    if nxt is None:
        return (f"Emits the final RTL-generation contract `{_layer_doc_id(module_name, layer)}` "
                f"(`{spec_path}`) for module-level sign-off.")
    next_spec_path, _ = _layer_artifact(nxt)
    return (f"Emits `{_layer_doc_id(module_name, layer)}` (`{spec_path}`) as input "
            f"to `{_layer_doc_id(module_name, nxt)}` (`{next_spec_path}`).")


def _import_describe(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    path = f"thor_gpu.modules.{module_name}.{_layer_dir(layer)}.src.{src_file}"
    try:
        mod = __import__(path, fromlist=["*"])
    except Exception:
        return {}
    describe = getattr(mod, "describe", None)
    if callable(describe):
        try:
            return describe() or {}
        except Exception:
            return {}
    return {}


def _describe_to_table(info: Dict[str, Any]) -> str:
    rows = []
    skip = {"name", "layer", "status", "description", "purpose", "scope",
            "ports_table", "detailed_table", "note"}
    for key, value in info.items():
        if key in skip:
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        rows.append([label, str(value)])
    return _markdown_table(["Property", "Value"], rows) if rows else ""


def discover_modules() -> List[str]:
    modules_root = os.path.join(os.path.dirname(__file__), "modules")
    out = []
    for entry in sorted(os.listdir(modules_root)):
        if entry.startswith(".") or entry in ("__pycache__", "common"):
            continue
        if os.path.isdir(os.path.join(modules_root, entry)) and \
           os.path.isdir(os.path.join(modules_root, entry, "specs")):
            out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Spec / plan / report variable builders
# ---------------------------------------------------------------------------

def _layer_scope(layer: str, display: str) -> str:
    return {
        "L1_behavior": f"Cycle-unaware functional behavior of {display}.",
        "L2_cycle": f"Cycle-accurate timing and protocol behavior of {display}.",
        "L3_architecture": f"Micro-architectural decisions for {display}.",
        "L4_structure": f"Structural decomposition of {display}.",
        "L5_dsl": f"RTL-ready DSL description of {display}.",
        "L6_verilog": f"Generated Verilog RTL and reports for {display}.",
    }.get(layer, "See detailed description below.")


def extract_layer_info(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    info = _import_describe(module_name, layer, src_file)
    display = _MODULE_DISPLAY.get(module_name, module_name)
    layer_label = layer.replace("_", " ")
    purpose = info.get("description") or f"{layer_label} for {display}."

    variables = default_variables()
    variables.update({
        "module_name": display,
        "layer_name": layer_label,
        "doc_id": f"{module_name.upper()}-{layer.upper()}-001",
        "purpose": purpose,
        "scope": info.get("scope", _layer_scope(layer, display)),
        "status": "Draft",
        "inputs_from_previous": _layer_input_contract(module_name, layer),
        "outputs_to_next": _layer_output_contract(module_name, layer),
        "decision_01": f"Implement {display} as specified in the Thor-GPGPU SoC spec",
        "rationale_01": "Matches the target GPGPU compute-cluster architecture",
        "impact_01": "Drives downstream implementation and verification",
    })
    table = _describe_to_table(info)
    if info.get("ports") or info.get("note"):
        extra = []
        if info.get("ports"):
            extra.append(f"### Ports\n\n`{info['ports']}`\n")
        if info.get("note"):
            extra.append(f"### Note\n\n{info['note']}\n")
        table = "\n\n".join([table] + extra) if table else "\n\n".join(extra)
    variables["detailed_description"] = table or "_No detailed description available._"

    defaults = {
        "L1_behavior": ("Python unit tests against the functional reference model.",
                         "Functional correctness of behavior model", "Directed pytest cases",
                         "All operations and corner cases exercised"),
        "L2_cycle": ("Cycle-accurate simulation and cross-layer equivalence with L1.",
                     "Cycle-level timing and protocol compliance", "Cycle-context simulation",
                     "All states and transitions exercised"),
        "L5_dsl": ("DSL simulation and cross-layer equivalence with L1/L2.",
                   "DSL implementation matches reference model", "rtlgen Simulator + LayerVerifier",
                   "All functional paths covered"),
        "L6_verilog": ("Verilog generation and lint.", "Generated RTL matches DSL semantics",
                       "VerilogEmitter + VerilogLinter", "Module-level RTL coverage"),
    }
    ds = defaults.get(layer, ("Python unit tests + cross-layer checks.",
                              "Functional correctness", "Directed tests",
                              "All operations exercised"))
    variables.update({
        "verification_strategy": info.get("verification_strategy", ds[0]),
        "verif_check_01": info.get("verif_check_01", ds[1]),
        "verif_method_01": info.get("verif_method_01", ds[2]),
        "verif_cov_01": info.get("verif_cov_01", ds[3]),
        "constraint_01": "Module specification compliance",
        "constraint_src_01": "Thor-GPGPU top-level SoC spec",
        "assumption_01": "Two's-complement integer / IEEE-754 FP semantics",
        "assumption_rationale_01": "Matches the Thor GPGPU datapath",
        "deliverable_01": f"{src_file}.py",
        "deliverable_fmt_01": "Python source",
        "deliverable_owner_01": "RTLCraft Agent",
    })
    return variables


def _render(template_name: str, output_path: str, variables: Dict[str, Any]) -> None:
    rendered = render_template(template_name, variables)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)


# ---------------------------------------------------------------------------
# Test discovery / execution
# ---------------------------------------------------------------------------

def _find_layer_tests(module_name: str, layer: str) -> List[Tuple[str, str]]:
    tests_dir = os.path.join(os.path.dirname(__file__), "modules", module_name,
                             _layer_dir(layer), "tests")
    out = []
    if not os.path.isdir(tests_dir):
        return out
    for fn in sorted(os.listdir(tests_dir)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        mod_name = f"thor_gpu.modules.{module_name}.{_layer_dir(layer)}.tests.{fn[:-3]}"
        try:
            m = __import__(mod_name, fromlist=["*"])
        except Exception:
            continue
        for name, obj in inspect.getmembers(m):
            if inspect.isfunction(obj) and name.startswith("test_"):
                out.append((name, _test_objective(name, obj)))
            if inspect.isclass(obj) and name.startswith("Test"):
                for mname, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if mname.startswith("test_"):
                        out.append((mname, _test_objective(mname, method)))
    return out


def run_layer_tests(module_name: str, layer: str) -> Dict[str, Any]:
    tests_dir = os.path.join(os.path.dirname(__file__), "modules", module_name,
                             _layer_dir(layer), "tests")
    if not os.path.isdir(tests_dir):
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0, "cmd": ""}
    cmd = [sys.executable, "-m", "pytest", tests_dir, "-q", "--tb=short"]
    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as exc:
        return {"total": 0, "passed": 0, "failed": 1, "skipped": 0, "duration": 0.0,
                "error": str(exc), "cmd": " ".join(cmd)}
    duration = time.time() - start
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": duration,
               "cmd": " ".join(cmd), "returncode": result.returncode,
               "stdout": result.stdout, "stderr": result.stderr}
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        line = line.strip()
        if any(tok in line for tok in ("passed", "failed", "skipped", "error")):
            parts = line.split()
            for i, p in enumerate(parts):
                if p in ("passed", "failed", "skipped"):
                    summary[p] = int(parts[i - 1])
                elif p == "error":
                    summary["failed"] += int(parts[i - 1])
    summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"]
    return summary


def _compact_log(text: str, limit: int = 800) -> str:
    text = (text or "").strip()
    if not text:
        return "No log output captured."
    return text if len(text) <= limit else text[:limit] + "\n... truncated ..."


# ---------------------------------------------------------------------------
# Test-plan / test-report variable builders (filled with real data)
# ---------------------------------------------------------------------------

def extract_test_plan_vars(module_name: str, layer: str) -> Dict[str, Any]:
    display = _MODULE_DISPLAY.get(module_name, module_name)
    layer_label = layer.replace("_", " ")
    spec_path, _ = _layer_artifact(layer)
    variables = default_variables()
    variables.update({
        "project_name": f"{display} — {layer_label}",
        "dut_name": display,
        "dut_version": "0.1",
        "doc_id": f"{module_name.upper()}-{layer.upper()}-TP-001",
        "purpose": f"Verification test plan for the {layer_label} of {display}.",
        "scope": f"Covers directed and cross-layer tests executed at {layer_label}.",
        "out_of_scope": "Cluster-level integration tests; see gpu_cluster specs.",
        "ref_id": _layer_doc_id(module_name, layer),
        "ref_title": f"{display} {layer_label} specification",
        "ref_version": "0.1",
        "term": "Layer contract",
        "definition": "Generated Markdown contract consumed by the next IR layer.",
    })
    tests = _find_layer_tests(module_name, layer)
    if tests:
        rows = [(f"TC-{i+1:03d}", name, "Directed", "P1", desc, "Planned")
                for i, (name, desc) in enumerate(tests)]
        variables["tc_name_01"] = tests[0][0]
        variables["tc_obj_01"] = tests[0][1]
        inv = _markdown_table(["TC ID", "Name", "Type", "Priority", "Objective", "Status"], rows)
    else:
        variables["tc_name_01"] = "missing_layer_tests"
        variables["tc_obj_01"] = "Strict sign-off must add at least one layer-local test."
        inv = "No layer-specific tests discovered."
    variables.update({
        "verification_approach": (f"Run the pytest cases under "
                                  f"`thor_gpu/modules/{module_name}/{_layer_dir(layer)}/tests`."),
        "test_case_inventory": inv,
        "unit_method": "Python pytest + model simulation",
        "int_method": "Cross-layer equivalence checks",
        "sys_method": "Full cluster regression",
    })
    return variables


def extract_test_report_vars(module_name: str, layer: str, result: Dict[str, Any]) -> Dict[str, Any]:
    display = _MODULE_DISPLAY.get(module_name, module_name)
    layer_label = layer.replace("_", " ")
    total = int(result.get("total", 0))
    passed = int(result.get("passed", 0))
    failed = int(result.get("failed", 0))
    skipped = int(result.get("skipped", 0))
    duration = float(result.get("duration", 0.0))
    overall = "PASS" if failed == 0 and total > 0 else ("FAIL" if failed > 0 else "NO TESTS")
    variables = default_variables()
    variables.update({
        "project_name": f"{display} — {layer_label} Test Report",
        "doc_id": f"{module_name.upper()}-{layer.upper()}-TR-001",
        "test_plan_ref": f"{module_name.upper()}-{layer.upper()}-TP-001",
        "dut_name": display,
        "dut_version": "0.1",
        "overall_result": overall,
        "target_total": str(total), "achieved_total": str(total), "status_total": "OK",
        "target_pass": str(total), "achieved_pass": str(passed),
        "status_pass": "OK" if passed == total else "NOK",
        "target_fail": "0", "achieved_fail": str(failed),
        "status_fail": "OK" if failed == 0 else "NOK",
        "target_skip": "0", "achieved_skip": str(skipped), "status_skip": "OK",
        "conclusion": (f"{layer_label} tests: {passed}/{total} passed in {duration:.2f}s."),
        "sign_off_recommendation": ("Proceed to next layer" if overall == "PASS"
                                    else "Investigate failures before sign-off"),
        "test_logs": _compact_log(result.get("stdout", "") + "\n" + result.get("stderr", "")),
    })
    return variables


# ---------------------------------------------------------------------------
# Top-level generation
# ---------------------------------------------------------------------------

def generate_module_docs(module_name: str) -> List[str]:
    output_base = os.path.join(os.path.dirname(__file__), "modules", module_name)
    written: List[str] = []
    display = _MODULE_DISPLAY.get(module_name, module_name)

    # Module-level spec (00).
    mv = default_variables()
    mv.update({
        "module_name": display,
        "module_id": module_name.upper(),
        "doc_id": f"{module_name.upper()}-MOD-001",
        "purpose": _MODULE_BRIEF.get(module_name, f"{display} module."),
        "scope": f"Module-level design specification for {display}.",
    })
    _render("module_spec", os.path.join(output_base, "specs", "00_module_spec.md"), mv)
    written.append(os.path.join(output_base, "specs", "00_module_spec.md"))

    # Per-layer spec / plan / report.
    for layer, src_file, spec_name in _LAYER_ORDER:
        spec_path, prefix = _layer_artifact(layer)
        layer_base = os.path.join(output_base, _layer_dir(layer), "specs")
        _render("layer_spec", os.path.join(layer_base, spec_name),
                extract_layer_info(module_name, layer, src_file))
        _render("test_plan", os.path.join(layer_base, f"{prefix}_test_plan.md"),
                extract_test_plan_vars(module_name, layer))
        result = run_layer_tests(module_name, layer)
        _render("test_report", os.path.join(layer_base, f"{prefix}_test_report.md"),
                extract_test_report_vars(module_name, layer, result))
        written.extend([
            os.path.join(layer_base, spec_name),
            os.path.join(layer_base, f"{prefix}_test_plan.md"),
            os.path.join(layer_base, f"{prefix}_test_report.md"),
        ])

    # Module-level rollup (07/08) using L1 results.
    rollup_plan = os.path.join(output_base, "specs", "07_module_test_plan.md")
    _render("test_plan", rollup_plan, extract_test_plan_vars(module_name, "L1_behavior"))
    rollup_res = run_layer_tests(module_name, "L1_behavior")
    _render("test_report", os.path.join(output_base, "specs", "08_module_test_report.md"),
            extract_test_report_vars(module_name, "L1_behavior", rollup_res))
    written.extend([rollup_plan, os.path.join(output_base, "specs", "08_module_test_report.md")])
    return written


def emit_all_verilog(output_dir: Optional[str] = None) -> Dict[str, int]:
    """Emit Verilog for every module's L6 layer into ``output_dir``."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "verilog")
    os.makedirs(output_dir, exist_ok=True)
    results: Dict[str, int] = {}
    for module_name in discover_modules():
        try:
            mod = __import__(
                f"thor_gpu.modules.{module_name}.layer_L6_verilog.src.emitter",
                fromlist=["emit_verilog"])
            _, lines = mod.emit_verilog(output_dir)
            results[module_name] = lines
        except Exception as exc:
            results[module_name] = -1
            print(f"  [warn] {module_name}: verilog emit failed: {exc}")
    return results


def generate_all_docs() -> Dict[str, List[str]]:
    paths: Dict[str, List[str]] = {}
    for mod in discover_modules():
        paths[mod] = generate_module_docs(mod)
    return paths


if __name__ == "__main__":
    print("=== Generating per-layer documents ===")
    doc_paths = generate_all_docs()
    for mod, files in doc_paths.items():
        print(f"  {mod}: {len(files)} documents")
    print("\n=== Emitting Verilog ===")
    vlog = emit_all_verilog()
    total_lines = 0
    for mod, lines in vlog.items():
        print(f"  {mod}.v: {lines} lines" if lines >= 0 else f"  {mod}: FAILED")
        total_lines += max(lines, 0)
    print(f"\nTotal Verilog: {total_lines} lines across {len(vlog)} modules")
    print(f"Documents: {sum(len(v) for v in doc_paths.values())} files")
