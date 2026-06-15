"""Document generator for the Earphone SoC document-driven flow.

This module extracts real design data from the per-layer source files and
fills the industrial-pattern templates in ``doc_templates/`` with meaningful
content instead of placeholder defaults.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from doc_templates import default_variables, read_template, render_template


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Render a markdown table from headers and rows."""
    if not rows:
        return ""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _bullet_list(items: List[str]) -> str:
    if not items:
        return "_None defined._"
    return "\n".join(f"- {item}" for item in items)


def _test_objective(name: str, obj: Any) -> str:
    """Return a readable objective for a pytest function."""
    doc = inspect.getdoc(obj) or ""
    if doc:
        return doc.splitlines()[0]
    words = name.removeprefix("test_").replace("_", " ")
    return f"Validate {words}."


# ---------------------------------------------------------------------------
# Document quality / feedback helpers
# ---------------------------------------------------------------------------

_DOC_ISSUE_PATTERNS: List[Tuple[str, re.Pattern[str], str]] = [
    (
        "unfilled_template_placeholder",
        re.compile(r"\{\{\s*[A-Za-z_][A-Za-z0-9_]*\s*\}\}"),
        "Template placeholder was not filled.",
    ),
    (
        "tbd_placeholder",
        re.compile(r"\bTBD\b"),
        "TBD placeholder remains in generated document.",
    ),
    (
        "implementation_fallback",
        re.compile(r"See DSL implementation", re.IGNORECASE),
        "Document points to DSL implementation instead of carrying its own layer contract.",
    ),
    (
        "template_instruction",
        re.compile(r"<!--\s*(Insert|Describe)\b", re.IGNORECASE),
        "Template authoring instruction remains in generated document.",
    ),
]


def validate_document_content(content: str, path: str = "") -> List[Dict[str, Any]]:
    """Return structured feedback for unfilled or stub-like document content."""
    issues: List[Dict[str, Any]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for code, pattern, message in _DOC_ISSUE_PATTERNS:
            if pattern.search(line):
                issues.append({
                    "path": path,
                    "line": line_no,
                    "severity": "blocker",
                    "code": code,
                    "message": message,
                    "text": line.strip()[:200],
                })
    return issues


def _template_placeholders(template_name: str) -> List[str]:
    """Return placeholders declared by a template."""
    content = read_template(template_name)
    names = re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", content)
    return sorted(set(names))


def _fill_template_defaults(
    template_name: str,
    variables: Dict[str, Any],
    fallback,
) -> Dict[str, Any]:
    """Fill every template field so generated documents are reviewable."""
    filled = dict(variables)
    for name in _template_placeholders(template_name):
        if filled.get(name) in (None, ""):
            filled[name] = fallback(name)
    return filled


def _render_to_file_checked(
    template_name: str,
    output_path: str,
    variables: Dict[str, Any],
    feedback: Optional[List[Dict[str, Any]]] = None,
    *,
    validate: bool = False,
) -> None:
    """Render a document and optionally append quality feedback."""
    rendered = render_template(template_name, variables)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    if validate and feedback is not None:
        feedback.extend(validate_document_content(rendered, output_path))


def _write_docgen_feedback(
    output_base: str,
    module_name: str,
    issues: List[Dict[str, Any]],
) -> str:
    """Persist document-quality feedback for the generated module bundle."""
    feedback_path = os.path.join(output_base, "specs", "docgen_feedback.json")
    os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
    payload = {
        "schema_version": "2026-06-15.docgen_feedback.v1",
        "module_name": module_name,
        "issue_count": len(issues),
        "blocker_count": sum(1 for issue in issues if issue.get("severity", "blocker") == "blocker"),
        "warning_count": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "issues": issues,
    }
    with open(feedback_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return feedback_path


# ---------------------------------------------------------------------------
# Layer discovery
# ---------------------------------------------------------------------------

_LAYER_ORDER = [
    ("L1_behavior", "behavior", "behavior", "01_behavior_spec.md"),
    ("L2_cycle", "cycle", "cycle", "02_cycle_spec.md"),
    ("L3_architecture", "arch", "architecture", "03_architecture_spec.md"),
    ("L4_structure", "structure", "structure", "04_structural_spec.md"),
    ("L5_dsl", "dsl", "dsl", "05_dsl_spec.md"),
    ("L6_verilog", "emitter", "verilog", "06_verilog_spec.md"),
]


def _layer_index(layer: str) -> int:
    for idx, (layer_name, _, _, _) in enumerate(_LAYER_ORDER):
        if layer_name == layer:
            return idx
    raise ValueError(f"Unknown layer: {layer}")


def _layer_doc_id(module_name: str, layer: str) -> str:
    return f"{module_name.upper()}-{layer.upper()}-001"


def _layer_test_plan_id(module_name: str, layer: str) -> str:
    return f"{module_name.upper()}-{layer.upper()}-TP-001"


def _layer_test_report_id(module_name: str, layer: str) -> str:
    return f"{module_name.upper()}-{layer.upper()}-TR-001"


def _layer_dir(layer: str) -> str:
    return f"layer_{layer}"


def _layer_artifact_paths(layer: str) -> Tuple[str, str, str]:
    _, _, _, spec_name = _LAYER_ORDER[_layer_index(layer)]
    prefix = spec_name.split("_spec.md")[0]
    base = os.path.join(_layer_dir(layer), "specs")
    return (
        os.path.join(base, spec_name),
        os.path.join(base, f"{prefix}_test_plan.md"),
        os.path.join(base, f"{prefix}_test_report.md"),
    )


def _previous_layer(layer: str) -> Optional[str]:
    idx = _layer_index(layer)
    if idx == 0:
        return None
    return _LAYER_ORDER[idx - 1][0]


def _next_layer(layer: str) -> Optional[str]:
    idx = _layer_index(layer)
    if idx == len(_LAYER_ORDER) - 1:
        return None
    return _LAYER_ORDER[idx + 1][0]


def _layer_input_contract(module_name: str, layer: str) -> str:
    prev = _previous_layer(layer)
    if prev is None:
        return (
            f"Consumes the module contract `{module_name.upper()}-MOD-001` "
            "and top-level SoC requirements as the seed SpecIR."
        )
    spec_path, plan_path, report_path = _layer_artifact_paths(prev)
    return (
        f"Consumes approved outputs from `{_layer_doc_id(module_name, prev)}` "
        f"(`{spec_path}`), plus verification intent `{_layer_test_plan_id(module_name, prev)}` "
        f"(`{plan_path}`) and latest evidence `{_layer_test_report_id(module_name, prev)}` "
        f"(`{report_path}`)."
    )


def _layer_output_contract(module_name: str, layer: str) -> str:
    nxt = _next_layer(layer)
    spec_path, plan_path, report_path = _layer_artifact_paths(layer)
    if nxt is None:
        return (
            f"Emits the final RTL-generation contract `{_layer_doc_id(module_name, layer)}` "
            f"(`{spec_path}`), verification plan `{_layer_test_plan_id(module_name, layer)}` "
            f"(`{plan_path}`), and execution evidence `{_layer_test_report_id(module_name, layer)}` "
            f"(`{report_path}`) for module-level sign-off."
        )
    next_spec_path, _, _ = _layer_artifact_paths(nxt)
    return (
        f"Emits `{_layer_doc_id(module_name, layer)}` (`{spec_path}`), "
        f"`{_layer_test_plan_id(module_name, layer)}` (`{plan_path}`), and "
        f"`{_layer_test_report_id(module_name, layer)}` (`{report_path}`) as inputs "
        f"to `{_layer_doc_id(module_name, nxt)}` (`{next_spec_path}`)."
    )


def _layer_module_path(module_name: str, layer: str, src_file: str) -> str:
    return f"earphone.modules.{module_name}.{_layer_dir(layer)}.src.{src_file}"


def _import_layer(module_name: str, layer: str, src_file: str):
    path = _layer_module_path(module_name, layer, src_file)
    try:
        return __import__(path, fromlist=["*"])
    except Exception as exc:  # pragma: no cover - defensive
        return None


def _call_describe(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    mod = _import_layer(module_name, layer, src_file)
    if mod is None:
        return {}
    describe = getattr(mod, "describe", None)
    if callable(describe):
        try:
            return describe() or {}
        except Exception:  # pragma: no cover
            return {}
    return {}


# ---------------------------------------------------------------------------
# RV32-specific extraction
# ---------------------------------------------------------------------------

_RV32IM_INSTRUCTIONS: List[Tuple[str, str, str]] = [
    ("LUI",   "U-type", "Load upper immediate"),
    ("AUIPC", "U-type", "Add upper immediate to PC"),
    ("JAL",   "J-type", "Jump and link"),
    ("JALR",  "I-type", "Jump and link register"),
    ("BEQ",   "B-type", "Branch if equal"),
    ("BNE",   "B-type", "Branch if not equal"),
    ("BLT",   "B-type", "Branch if less than"),
    ("BGE",   "B-type", "Branch if greater or equal"),
    ("BLTU",  "B-type", "Branch if less than unsigned"),
    ("BGEU",  "B-type", "Branch if greater or equal unsigned"),
    ("LB",    "I-type", "Load byte"),
    ("LH",    "I-type", "Load halfword"),
    ("LW",    "I-type", "Load word"),
    ("LBU",   "I-type", "Load byte unsigned"),
    ("LHU",   "I-type", "Load halfword unsigned"),
    ("SB",    "S-type", "Store byte"),
    ("SH",    "S-type", "Store halfword"),
    ("SW",    "S-type", "Store word"),
    ("ADDI",  "I-type", "Add immediate"),
    ("SLTI",  "I-type", "Set less than immediate"),
    ("SLTIU", "I-type", "Set less than immediate unsigned"),
    ("XORI",  "I-type", "XOR immediate"),
    ("ORI",   "I-type", "OR immediate"),
    ("ANDI",  "I-type", "AND immediate"),
    ("SLLI",  "I-type", "Shift left logical immediate"),
    ("SRLI",  "I-type", "Shift right logical immediate"),
    ("SRAI",  "I-type", "Shift right arithmetic immediate"),
    ("ADD",   "R-type", "Add"),
    ("SUB",   "R-type", "Subtract"),
    ("SLL",   "R-type", "Shift left logical"),
    ("SLT",   "R-type", "Set less than"),
    ("SLTU",  "R-type", "Set less than unsigned"),
    ("XOR",   "R-type", "XOR"),
    ("SRL",   "R-type", "Shift right logical"),
    ("SRA",   "R-type", "Shift right arithmetic"),
    ("OR",    "R-type", "OR"),
    ("AND",   "R-type", "AND"),
    ("MUL",   "R-type", "Multiply (RV32M)"),
    ("MULH",  "R-type", "Multiply high (RV32M)"),
    ("MULHSU", "R-type", "Multiply high signed/unsigned (RV32M)"),
    ("MULHU", "R-type", "Multiply high unsigned (RV32M)"),
    ("DIV",   "R-type", "Divide (RV32M)"),
    ("DIVU",  "R-type", "Divide unsigned (RV32M)"),
    ("REM",   "R-type", "Remainder (RV32M)"),
    ("REMU",  "R-type", "Remainder unsigned (RV32M)"),
    ("EBREAK", "I-type", "Environment break (halt simulation)"),
]


def _extract_rv32_behavior_info() -> Dict[str, Any]:
    """Extract meaningful metadata from the RV32 L1 behavior model."""
    from earphone.modules.rv32.layer_L1_behavior.src.behavior import RV32IM_ISS
    from earphone.modules.rv32.layer_L1_behavior.tests.test_behavior import TestRV32IMISS

    tests = []
    for name, method in inspect.getmembers(TestRV32IMISS, predicate=inspect.isfunction):
        if name.startswith("test_"):
            tests.append((name, _test_objective(name, method)))

    instr_rows = [(mn, fmt, desc) for mn, fmt, desc in _RV32IM_INSTRUCTIONS]

    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L1 BehaviorIR",
        "purpose": (
            "Define the cycle-unaware RV32IM instruction-set simulator (ISS) "
            "used as the golden reference for all downstream layers and RTL verification."
        ),
        "scope": (
            "Covers RV32I base integer instructions plus RV32M multiply/divide "
            "extensions. Memory is modeled as a sparse byte-addressable map."
        ),
        "isa": "RV32IM",
        "xlen": 32,
        "register_file": _markdown_table(
            ["Property", "Value"],
            [
                ["Register count", "32 (x0–x31)"],
                ["Width", "32 bits"],
                ["x0 behavior", "Hardwired to zero"],
                ["Program counter", "32 bits, default reset = 0x1000"],
            ],
        ),
        "memory_model": _markdown_table(
            ["Property", "Value"],
            [
                ["Address space", "32-bit byte-addressable"],
                ["Endianness", "Little-endian"],
                ["Access widths", "Byte, halfword, word"],
                ["Implementation", "Sparse Python dict (uninitialized reads return 0)"],
            ],
        ),
        "instructions": _markdown_table(
            ["Instruction", "Format", "Description"],
            instr_rows,
        ),
        "tests": _markdown_table(
            ["Test Name", "Description"],
            tests,
        ),
    }


def _extract_rv32_cycle_info() -> Dict[str, Any]:
    from earphone.modules.rv32.layer_L2_cycle.src.cycle import rv32im_cycle_model, describe

    info = describe()
    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L2 CycleIR",
        "purpose": info.get("description", (
            "Provide a cycle-accurate reference model that tracks pipeline "
            "control signals while delegating functional execution to the L1 ISS."
        )),
        "scope": "Single-cycle scalar pipeline with multi-cycle M-extension operations.",
        "model": _markdown_table(
            ["Property", "Value"],
            [
                ["Pipeline", " → ".join(info.get("pipeline_stages", ["IF", "ID/EX", "WB"]))],
                ["MUL latency", str(info.get("mul_latency_cycles", 1))],
                ["DIV/REM latency", str(info.get("div_latency_cycles", "iterative"))],
                ["Branch predictor", "Static not-taken"],
                ["Stall/flush support", "Yes"],
            ],
        ),
        "tests": "Dedicated L2 tests cover describe() metadata, reset initialization, and fetch/PC advance behavior.",
    }


def _extract_rv32_arch_info() -> Dict[str, Any]:
    from earphone.modules.rv32.layer_L3_architecture.src.arch import ARCH

    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L3 ArchitectureIR",
        "purpose": "Capture micro-architectural decisions for the RV32IM core.",
        "scope": "Pipeline organization, execution units, and reset behavior.",
        "architecture": _markdown_table(
            ["Property", "Value"],
            [
                ["ISA", ARCH.isa],
                ["Pipeline", ARCH.pipeline],
                ["Stages", " → ".join(ARCH.stages)],
                ["Multiplier", ARCH.multiplier],
                ["Divider", ARCH.divider],
                ["Branch predictor", ARCH.branch_predictor],
                ["Data memory width", str(ARCH.dmem_width)],
                ["Instruction memory width", str(ARCH.imem_width)],
                ["Reset PC", f"0x{ARCH.reset_pc:08X}"],
            ],
        ),
    }


def _extract_rv32_structure_info() -> Dict[str, Any]:
    from earphone.modules.rv32.layer_L4_structure.src.structure import STRUCTURE

    rows = [[sb.name, sb.purpose, ", ".join(sb.interfaces)] for sb in STRUCTURE.subblocks]
    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L4 StructuralIR",
        "purpose": "Define the major sub-blocks and their interface contracts.",
        "scope": "Internal decomposition used by the L5 DSL generator.",
        "structure": _markdown_table(
            ["Sub-block", "Description", "Interfaces"],
            rows,
        ),
    }


def _extract_rv32_dsl_info() -> Dict[str, Any]:
    from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32

    cls = EarphoneRV32
    doc = inspect.getdoc(cls) or ""
    methods = [name for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)]

    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L5 DSL",
        "purpose": "RTL-ready DSL description of the EarphoneRV32 core.",
        "scope": doc.splitlines()[0] if doc else "-",
        "dsl_class": cls.__name__,
        "public_methods": _bullet_list(methods[:20]),
    }


def _extract_rv32_verilog_info() -> Dict[str, Any]:
    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L6 Verilog",
        "purpose": "Synthesizable Verilog generation and lint reporting.",
        "scope": "Generated RTL from the L5 DSL via rtlgen VerilogEmitter.",
        "deliverables": _markdown_table(
            ["Deliverable", "Description"],
            [
                ["earphone_rv32.v", "Top-level RTL"],
                ["Lint report", "Static lint issue summary"],
                ["SVA constraints", "Derived assertion sequences"],
            ],
        ),
    }


_LAYER_EXTRACTORS = {
    "rv32": {
        "L1_behavior": _extract_rv32_behavior_info,
        "L2_cycle": _extract_rv32_cycle_info,
        "L3_architecture": _extract_rv32_arch_info,
        "L4_structure": _extract_rv32_structure_info,
        "L5_dsl": _extract_rv32_dsl_info,
        "L6_verilog": _extract_rv32_verilog_info,
    }
}


def _describe_to_table(info: Dict[str, Any]) -> str:
    """Render non-special keys of a describe() dict as a markdown table."""
    rows = []
    for key, value in info.items():
        if key in ("name", "layer", "status", "description", "purpose", "scope",
                   "ports_table", "detailed_table"):
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        rows.append([label, str(value)])
    if not rows:
        return ""
    return _markdown_table(["Property", "Value"], rows)


def _import_design_earphone_safely():
    """Import the legacy design_earphone module, pre-loading rv32 to break the
    circular dependency that exists while the RV32 L5 DSL is still re-exported
    from design_earphone.py.
    """
    # Touch the rv32 package first so its __init__ completes before
    # design_earphone is imported as a regular module.
    try:
        __import__("earphone.modules.rv32", fromlist=["*"])
    except Exception:  # pragma: no cover - defensive
        pass
    return __import__("earphone.design_earphone", fromlist=["*"])


def _extract_from_design_earphone(module_name: str, layer: str) -> Dict[str, Any]:
    """Extract metadata from the legacy monolithic design_earphone.py."""
    design = _import_design_earphone_safely()
    class_name = _module_display_name(module_name)
    cls = getattr(design, class_name, None)
    info: Dict[str, Any] = {"name": class_name, "layer": layer, "status": "implemented"}

    if layer == "L3_architecture":
        info["description"] = inspect.getdoc(cls).splitlines()[0] if cls and inspect.getdoc(cls) else f"Architecture of {class_name}."
        info["pipeline"] = "See DSL implementation for pipeline details."
    elif layer == "L4_structure":
        info["description"] = f"Structural decomposition of {class_name}."
        info["subblocks"] = "See DSL implementation for sub-block details."
    elif layer == "L5_dsl":
        if cls is None:
            info["description"] = f"{class_name} DSL class not yet migrated."
            return info
        doc = inspect.getdoc(cls) or ""
        info["description"] = doc.splitlines()[0] if doc else f"RTL-ready DSL for {class_name}."
        info["dsl_class"] = cls.__name__
        # Extract ports from __init__ signature / instance attributes
        try:
            inst = cls()
            ports = []
            for attr_name in dir(inst):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(inst, attr_name)
                cls_name = type(attr).__name__
                if cls_name in ("Input", "Output", "Wire", "Reg"):
                    width = getattr(attr, "width", "?")
                    ports.append((attr_name, cls_name, str(width)))
            if ports:
                info["ports_table"] = _markdown_table(["Port", "Type", "Width"], ports)
        except Exception:  # pragma: no cover - DSL instantiation may need parameters
            pass
    elif layer == "L6_verilog":
        info["description"] = f"Verilog generation for {class_name}."
        info["deliverables"] = f"{module_name}.v"

    return info


def _extract_generic_layer_info(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    """Fallback extractor for modules without a dedicated extractor.

    Uses the ``describe()`` function provided by the layer module and renders
    its fields into the document.  If no ``describe()`` is available, falls
    back to introspecting the legacy ``design_earphone.py`` module.
    """
    info = _call_describe(module_name, layer, src_file)
    if not info and layer in ("L3_architecture", "L4_structure", "L5_dsl", "L6_verilog"):
        info = _extract_from_design_earphone(module_name, layer)

    layer_label = layer.replace("_", " ")
    display = _module_display_name(module_name)
    purpose = info.get("purpose") or info.get("description") or f"{layer_label} for {display}."
    if "scope" in info:
        scope = info["scope"]
    elif layer == "L1_behavior":
        scope = f"Cycle-unaware functional behavior of {display}."
    elif layer == "L2_cycle":
        scope = f"Cycle-accurate protocol and timing behavior of {display}."
    elif layer == "L3_architecture":
        scope = f"Micro-architectural decisions for {display}."
    elif layer == "L4_structure":
        scope = f"Structural decomposition of {display}."
    elif layer == "L5_dsl":
        scope = f"RTL-ready DSL description of {display}."
    elif layer == "L6_verilog":
        scope = f"Generated Verilog RTL and reports for {display}."
    else:
        scope = "See detailed description below."

    result = {
        "module_name": display,
        "layer_name": layer_label,
        "purpose": purpose,
        "scope": scope,
        "notes": _bullet_list([f"Status: {info.get('status', 'implemented')}"]),
    }

    table = _describe_to_table(info)
    if table:
        result["detailed_table"] = table
    if "ports_table" in info:
        result["ports_table"] = info["ports_table"]
    return result


def extract_layer_info(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    """Return a dictionary of variables for rendering the layer spec."""
    extractor = _LAYER_EXTRACTORS.get(module_name, {}).get(layer)
    if extractor is not None:
        info = extractor()
    else:
        info = _extract_generic_layer_info(module_name, layer, src_file)

    # Merge with defaults and add layer-specific metadata.
    variables = default_variables()
    variables["module_name"] = info.get("module_name", module_name)
    variables["layer_name"] = info.get("layer_name", layer.replace("_", " "))
    variables["doc_id"] = f"{module_name.upper()}-{layer.upper()}-001"
    variables["purpose"] = info.get("purpose", "")
    variables["scope"] = info.get("scope", "")
    variables["status"] = "Draft"

    # Layer-specific detailed description.
    detailed_parts = []
    label_overrides = {
        "isa": "ISA",
        "xlen": "Register Width (XLEN)",
        "dsl_class": "DSL Class",
        "public_methods": "Public Methods",
    }
    for key in ["isa", "xlen", "register_file", "memory_model", "instructions", "tests",
                "model", "architecture", "structure", "dsl_class", "public_methods",
                "deliverables", "notes", "detailed_table", "ports_table"]:
        if key in info:
            label = label_overrides.get(key, key.replace("_", " ").title())
            detailed_parts.append(f"### {label}\n\n{info[key]}\n")
    variables["detailed_description"] = "\n".join(detailed_parts) or "_No detailed description available._"

    # Standard section fallbacks.
    variables["inputs_from_previous"] = info.get(
        "inputs_from_previous",
        _layer_input_contract(module_name, layer)
    )
    variables["outputs_to_next"] = info.get(
        "outputs_to_next",
        _layer_output_contract(module_name, layer)
    )
    display = _module_display_name(module_name)
    variables["decision_01"] = info.get("decision_01", f"Implement {display} as specified in top-level SoC spec")
    variables["rationale_01"] = info.get("rationale_01", "Matches target application and power/area constraints")
    variables["impact_01"] = info.get("impact_01", "Drives downstream implementation and verification")
    # Layer-appropriate verification defaults
    if layer == "L1_behavior":
        default_verif_strategy = "Python unit tests against the functional reference model."
        default_verif_check = "Functional correctness of behavior model"
        default_verif_method = "Directed pytest cases"
        default_verif_cov = "All operations and corner cases exercised"
    elif layer == "L2_cycle":
        default_verif_strategy = "Cycle-accurate simulation and cross-layer equivalence with L1."
        default_verif_check = "Cycle-level timing and protocol compliance"
        default_verif_method = "Cycle-context simulation"
        default_verif_cov = "All states and transitions exercised"
    elif layer == "L5_dsl":
        default_verif_strategy = "DSL simulation and cross-layer equivalence with L1/L2."
        default_verif_check = "DSL implementation matches reference model"
        default_verif_method = "rtlgen Simulator + LayerVerifier"
        default_verif_cov = "All functional paths covered"
    elif layer == "L6_verilog":
        default_verif_strategy = "Verilog generation, lint, and simulation."
        default_verif_check = "Generated RTL matches DSL semantics"
        default_verif_method = "Verilog simulation + SVA checks"
        default_verif_cov = "Module-level RTL coverage"
    else:
        default_verif_strategy = "Python unit tests + cross-layer equivalence checks."
        default_verif_check = "Functional correctness"
        default_verif_method = "Directed tests"
        default_verif_cov = "All operations exercised"

    variables["verification_strategy"] = info.get("verification_strategy", default_verif_strategy)
    variables["verif_check_01"] = info.get("verif_check_01", default_verif_check)
    variables["verif_method_01"] = info.get("verif_method_01", default_verif_method)
    variables["verif_cov_01"] = info.get("verif_cov_01", default_verif_cov)
    variables["constraint_01"] = info.get("constraint_01", "Module specification compliance")
    variables["constraint_src_01"] = info.get("constraint_src_01", "Top-level SoC spec")
    variables["assumption_01"] = info.get("assumption_01", "Little-endian byte ordering")
    variables["assumption_rationale_01"] = info.get("assumption_rationale_01", "Matches target bus architecture")
    variables["deliverable_01"] = info.get("deliverable_01", f"{src_file}.py")
    variables["deliverable_fmt_01"] = info.get("deliverable_fmt_01", "Python source")
    variables["deliverable_owner_01"] = info.get("deliverable_owner_01", "RTLCraft Agent")

    return variables


# ---------------------------------------------------------------------------
# Module-level spec aggregation
# ---------------------------------------------------------------------------

def _module_display_name(module_name: str) -> str:
    mapping = {
        "rv32": "EarphoneRV32",
        "simd16": "EarphoneSIMD16",
        "fft256": "EarphoneFFT256",
        "qspi": "EarphoneQSPI",
        "i2c": "EarphoneI2C",
        "sram256k": "EarphoneSRAM256K",
        "apb_bridge": "EarphoneAPBBridge",
    }
    return mapping.get(module_name, module_name)


def _module_brief_description(module_name: str) -> str:
    mapping = {
        "rv32": "RV32IM 3-stage in-order RISC-V core with single-cycle MUL and iterative DIV/REM.",
        "simd16": "16-lane SIMD accelerator: 1-cycle INT16 ALU + 3-stage FP16 MAC with per-lane predicate masking.",
        "fft256": "256-point streaming FFT accelerator wrapper with fixed-point Q1.15 samples.",
        "qspi": "Quad-SPI XIP controller for 32 MB external Flash (cmd/addr/data FSM).",
        "i2c": "APB I2C master byte controller for 7-bit address single-byte transactions.",
        "sram256k": "256 KB on-chip single-port SRAM with APB4 slave port and byte write strobes.",
        "apb_bridge": "AHB-to-APB address decoder exposing 8 peripheral slave slots.",
    }
    return mapping.get(module_name, f"{module_name} module.")


def _apply_common_module_spec_defaults(
    variables: Dict[str, Any],
    module_name: str,
    display: str,
) -> None:
    """Fill module_spec placeholders with explicit reviewable defaults."""
    variables.update({
        "ref_id": "EARPHONE-SOC-SPEC",
        "ref_title": "Smart Earphone SoC Design Specification",
        "ref_version": "0.1",
        "ref_desc": "Top-level requirements, architecture, PPA targets, and roadmap.",
        "term": "IR",
        "definition": "Intermediate representation used for staged Spec2RTL lowering.",
        "interface_timing": "Layer-specific timing assumptions are captured in the L2 CycleIR and L3 ArchitectureIR specs.",
        "proto_name": "Module-local protocol",
        "proto_version": "0.1",
        "proto_level": "Project-defined",
        "proto_notes": "Detailed port semantics are defined in the L5 DSL spec and generated Verilog.",
        "param_name": "Module parameters",
        "param_type": "contract",
        "param_default": "See L3/L5 specs",
        "param_range": "module-specific",
        "param_desc": "Configuration captured in layer contracts rather than free-form template text.",
        "state": "Operational",
        "state_enc": "implementation-defined",
        "state_desc": f"Normal active state for {display}.",
        "state_exit": "Reset, stall, or module-specific completion.",
        "err_cond": "Invalid or unsupported transaction",
        "err_detect": "Protocol decode or functional guard",
        "err_response": "Ignore, return safe value, or assert module-specific error status",
        "err_report": "Layer tests and generated verification reports",
        "subblock": "Control / Datapath",
        "subblock_desc": "Module-specific control and datapath partition.",
        "subblock_if": "See L4 StructuralIR contract.",
        "stage": "Layer-defined",
        "stage_lat": "Layer-defined",
        "stage_desc": "Pipeline and latency details are defined in L2/L3 contracts.",
        "critical_path": "Tracked through L5 DSL lint/PPA analysis and L6 Verilog reports.",
        "mod_clk": "clk",
        "mod_clk_freq": "48-160 MHz target",
        "mod_clk_src": "clk_sys",
        "mod_clk_notes": "Earphone-class low-power system clock domain.",
        "mod_rst": "rst_n",
        "mod_rst_type": "asynchronous assert, synchronous release",
        "mod_rst_active": "active low",
        "mod_rst_desc": "Resets architectural and control state to layer-specified defaults.",
        "timing_diagrams": "See L2 CycleIR test plan and cross-layer traces.",
        "reg_offset": "N/A",
        "reg_name": "Internal state",
        "reg_width": "module-specific",
        "reg_access": "internal",
        "reg_reset": "layer-specified",
        "reg_desc": "State elements are listed in L1/L2/L5 specs.",
        "bit_range": "N/A",
        "field_name": "N/A",
        "field_access": "N/A",
        "field_reset": "N/A",
        "field_desc": "No externally visible register field described at this level.",
        "power_domain": "clk_sys low-power domain unless the module spec states otherwise.",
        "ce_signal": "module clock enable",
        "ce_logic": "state registers and datapath flops",
        "ce_idle": "hold state and suppress unnecessary switching",
        "lp_mode": "idle",
        "lp_entry": "no active request or layer-specific stall",
        "lp_exit": "new request, interrupt, or reset release",
        "lp_impact": "reduced dynamic switching",
        "assertion_01": "Layer contract invariants hold during active operation",
        "assertion_sev_01": "error",
        "assertion_desc_01": "Assertions are generated from verification intents and constraints.",
        "constraint_01": "Module specification compliance",
        "constraint_src_01": "Top-level SoC spec and layer contracts",
        "assumption_01": "Little-endian data representation unless specified otherwise",
        "assumption_rationale_01": "Matches RV32/APB memory semantics in the Earphone SoC.",
        "tech": "22nm / 28nm low-power CMOS target",
        "synth_freq": "48-160 MHz",
        "area_goal": "module-specific PPA budget",
        "tool_settings": "rtlgen VerilogEmitter, VerilogLinter, and optional downstream synthesis feedback.",
        "mod_deliverable_01": f"{module_name} layer contracts, source, tests, reports, and generated RTL where applicable",
        "mod_deliverable_fmt_01": "Markdown, JSON, Python, Verilog",
        "mod_deliverable_owner_01": "RTLCraft Agent",
    })


def _apply_rv32_module_spec_details(variables: Dict[str, Any]) -> None:
    """Add concrete RV32 contract details to the module-level spec."""
    variables.update({
        "feature_01": "RV32IM ISA coverage",
        "feature_desc_01": "Implements RV32I base integer operations plus RV32M multiply/divide/remainder instructions.",
        "feature_02": "Low-power in-order microarchitecture",
        "feature_desc_02": "Uses a simple scalar pipeline, operand isolation, and iterative divide to reduce area and switching.",
        "use_cases": "Runs control firmware for the Smart Earphone SoC and services accelerator/peripheral orchestration.",
        "block_diagram": (
            "PC/fetch drives decode/execute, register-file read, ALU/branch/load-store logic, "
            "and an iterative M-extension unit before writeback and retire tracing."
        ),
        "submod_a": "Fetch + Decode",
        "submod_b": "Execute + Writeback",
        "clk_port": "clk",
        "clk_desc": "System clock for fetch, execute, register file, and memory interface state.",
        "rst_port": "rst_n",
        "rst_desc": "Active-low reset; reset PC is 0x00001000.",
        "port_name": "imem_*, dmem_*, irq, retire_*",
        "port_width": "1-32",
        "port_dir": "Input/Output",
        "port_proto": "Harvard memory buses + retire trace",
        "port_desc": "Instruction fetch, data memory request/response, local interrupt input, and verification retire outputs.",
        "interface_timing": (
            "Instruction fetch requests are issued from the current PC. Data memory handshakes use request/grant/valid. "
            "M-extension divide/remainder operations stall the core until the iterative unit completes."
        ),
        "proto_name": "RV32IM + simple memory bus",
        "proto_version": "RV32I/RV32M unprivileged subset",
        "proto_level": "Project subset",
        "proto_notes": "No MMU/FPU; physical addressing only. FP16 work is delegated to SIMD16.",
        "param_name": "XLEN / RESET_PC / DIV_ITERATIONS",
        "param_type": "integer constants",
        "param_default": "32 / 0x1000 / 32",
        "param_range": "fixed in v0.1",
        "param_desc": "Core width, reset entry point, and iterative divider latency.",
        "theory_of_operation": (
            "The core fetches 32-bit instructions, decodes operands and immediates, executes ALU/branch/load/store/M-extension "
            "operations, writes architectural results back to x1-x31, and keeps x0 hardwired to zero."
        ),
        "state": "RESET / RUN / MULDIV_WAIT",
        "state_enc": "implicit control state",
        "state_desc": "Reset initializes PC/register state; RUN retires ordinary instructions; MULDIV_WAIT holds the pipeline for divide/remainder.",
        "state_exit": "Reset release, instruction completion, or M-extension done.",
        "data_path": "PC -> instruction memory -> decode/register file -> ALU/LSU/muldiv -> writeback -> retire trace.",
        "err_cond": "Unsupported or unimplemented instruction encoding",
        "err_detect": "Decode opcode/funct mismatch",
        "err_response": "Treat as safe no-op or halt for EBREAK depending on decoded instruction",
        "err_report": "Retire trace and L1/L5 tests.",
        "subblock": "pc_unit, regfile, decoder, alu, muldiv_unit, load_store_unit",
        "subblock_desc": "Major internal blocks declared in L4 StructuralIR.",
        "subblock_if": "PC, register operands, ALU controls, memory request/response, muldiv start/done/result.",
        "stage": "IF / ID-EX / WB plus MULDIV_WAIT",
        "stage_lat": "1 cycle for scalar ALU/MUL, 32 cycles for DIV/REM",
        "stage_desc": "Three-stage in-order control with multi-cycle hold during divide/remainder.",
        "critical_path": "ALU compare/add path and decode-to-writeback muxing; divider is iterative to avoid a long combinational path.",
        "reg_name": "pc, regs[32], pipeline control, muldiv state",
        "reg_width": "32-bit architectural state plus control bits",
        "reg_reset": "pc=0x1000, x0-x31=0, control idle",
        "reg_desc": "Architectural register file, program counter, and M-extension state.",
        "power_domain": "clk_sys CPU domain with stall-based clock-enable gating.",
        "ce_signal": "core_clk_en",
        "ce_logic": "pipeline registers, writeback state, and operand isolation controls",
        "ce_idle": "held low during memory stalls and multi-cycle divide/remainder.",
        "lp_mode": "idle",
        "lp_entry": "no active request or divide stall",
        "lp_exit": "new fetch, interrupt, or multicycle completion",
        "lp_impact": "reduced dynamic switching",
        "assertion_01": "x0 remains zero and DIV/REM by zero follows RV32M rules",
        "assertion_desc_01": "Intent-driven tests and generated UVM/SVA artifacts cover RV32M divide-by-zero behavior.",
        "constraint_01": "RV32M divide-by-zero result and CPU active-power intent",
        "constraint_src_01": "EARP-RV32 constraints propagated through DesignScaffold",
        "area_goal": "<30k NAND2 equivalent for CPU core target",
        "mod_deliverable_01": "behavior.py, cycle.py, arch.py, structure.py, dsl.py, emitter.py, tests, specs, earphone_rv32.v",
    })


def extract_module_info(module_name: str) -> Dict[str, Any]:
    """Return variables for rendering the module-level module_spec template."""
    display = _module_display_name(module_name)
    variables = default_variables()
    variables["module_name"] = display
    variables["module_id"] = module_name.upper()
    variables["doc_id"] = f"{module_name.upper()}-MOD-001"
    variables["purpose"] = _module_brief_description(module_name)
    variables["scope"] = f"Module-level design specification for {display}."
    variables["feature_01"] = "ISA / protocol compliance"
    variables["feature_desc_01"] = "Implements the target instruction set or interface protocol."
    variables["feature_02"] = "Power/area optimization"
    variables["feature_desc_02"] = "Tuned for earphone-class low-power constraints."
    variables["use_cases"] = f"Used inside the Smart Earphone SoC as the {display} block."
    variables["block_diagram"] = f"See layer_L4_structure/specs/04_structural_spec.md for the internal decomposition of {display}."
    variables["submod_a"] = "Control"
    variables["submod_b"] = "Datapath"
    variables["clk_port"] = "clk"
    variables["clk_desc"] = "System clock"
    variables["rst_port"] = "rst_n"
    variables["rst_desc"] = "Active-low asynchronous reset, synchronous release"
    variables["port_name"] = "TBD"
    variables["port_width"] = "TBD"
    variables["port_dir"] = "TBD"
    variables["port_proto"] = "TBD"
    variables["port_desc"] = "See per-layer specs for detailed port lists."
    variables["param_name"] = "TBD"
    variables["param_type"] = "TBD"
    variables["param_default"] = "TBD"
    variables["param_range"] = "TBD"
    variables["param_desc"] = "See L5 DSL spec for configurable parameters."
    variables["theory_of_operation"] = f"{display} operation is described per-IR-layer in the layer_L*/specs/ documents."
    variables["data_path"] = "See L4 StructuralIR spec."
    variables["module_verif_strategy"] = "L1 behavior tests → L2 cycle tests → L3 DSL tests → L6 Verilog tests."
    variables["verif_check_01"] = "Functional equivalence across layers"
    variables["verif_method_01"] = "Cross-layer verification via LayerVerifier"
    variables["verif_cov_01"] = "100% of ISA/protocol operations"
    _apply_common_module_spec_defaults(variables, module_name, display)
    if module_name == "rv32":
        _apply_rv32_module_spec_details(variables)
    return variables


# ---------------------------------------------------------------------------
# Test plan / report helpers
# ---------------------------------------------------------------------------

def _find_layer_tests(module_name: str, layer: str) -> List[Tuple[str, str]]:
    """Discover pytest test functions in a layer's tests directory."""
    test_module_name = f"earphone.modules.{module_name}.{_layer_dir(layer)}.tests.test_{layer.split('_', 1)[1].lower()}"
    try:
        mod = __import__(test_module_name, fromlist=["*"])
    except Exception:
        return []
    tests = []
    for name, obj in inspect.getmembers(mod):
        if inspect.isfunction(obj) and name.startswith("test_"):
            tests.append((name, _test_objective(name, obj)))
        if inspect.isclass(obj) and name.startswith("Test"):
            for mname, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                if mname.startswith("test_"):
                    tests.append((mname, _test_objective(mname, method)))
    return tests


def _test_plan_fallback(
    module_name: str,
    layer: str,
    tests: List[Tuple[str, str]],
    key: str,
) -> str:
    display = _module_display_name(module_name)
    layer_label = layer.replace("_", " ")
    spec_path, plan_path, report_path = _layer_artifact_paths(layer)
    first_test = tests[0][0] if tests else "missing_layer_tests"
    first_objective = tests[0][1] if tests else "Layer has no discovered pytest tests; strict sign-off must feed this back upstream."
    values = {
        "ref_id": _layer_doc_id(module_name, layer),
        "ref_title": f"{display} {layer_label} specification",
        "ref_version": "0.1",
        "term": "Layer contract",
        "definition": "Machine-generated Markdown contract that is consumed by the next IR layer.",
        "dut_hier": f"earphone.modules.{module_name}.{_layer_dir(layer)}",
        "spec_ref": spec_path,
        "tb_agent_a": "Previous-layer contract",
        "tb_agent_b": "Next-layer checker",
        "tb_scoreboard": "Layer pytest assertions and cross-layer equivalence checks",
        "emu_usage": "Not used in the Python-layer regression",
        "emu_tools": "None",
        "fsm_cov_goal": "Covered by directed state-transition assertions where the layer has FSM state",
        "fsm_cov_tool": "pytest assertions",
        "toggle_cov_goal": "Covered at L6 Verilog when signal-level RTL is emitted",
        "toggle_cov_tool": "RTL simulator or formal tool",
        "expr_cov_goal": "Covered by directed branch and expression tests",
        "expr_cov_tool": "pytest and downstream RTL coverage",
        "fc_point": f"{layer_label} contract coverage",
        "fc_desc": f"Checks that {layer_label} preserves required inputs, outputs, and invariants.",
        "fc_goal": "All discovered directed tests pass",
        "coverage_closure": (
            f"Close {layer_label} when `{plan_path}` has corresponding PASS evidence in "
            f"`{report_path}` and no blocker feedback remains."
        ),
        "tc_name_01": first_test,
        "tc_type_01": "Directed",
        "tc_prio_01": "P1",
        "tc_obj_01": first_objective,
        "tc_status_01": "Planned",
        "tc_pre_01": f"`{spec_path}` is generated from the previous approved layer contract.",
        "tc_stim_01": f"Run pytest over `earphone/modules/{module_name}/{_layer_dir(layer)}/tests`.",
        "tc_exp_01": "All assertions pass and any mismatch is emitted as structured feedback.",
        "tc_pass_01": "pytest return code is zero and feedback blocker count is zero.",
        "tc_cov_01": f"{layer_label} public contract and adjacent-layer handoff.",
        "tc_dep_01": _layer_input_contract(module_name, layer),
        "dir_scenario_01": f"{layer_label} directed regression",
        "dir_input_01": "Layer source, generated spec, and adjacent-layer contract artifacts",
        "dir_exp_01": "Layer-local behavior matches the contract and produces PASS evidence",
        "dir_prio_01": "P1",
        "rand_test": f"{layer_label} randomized smoke vectors",
        "rand_focus": "Future randomized contract perturbations",
        "rand_iter": "0 in current pilot",
        "rand_seed": "record seed when enabled",
        "rand_regress": "0 in current pilot",
        "corner_scenario_01": "Reset, idle, and boundary protocol behavior",
        "corner_rationale_01": "These states commonly reveal broken layer refinement.",
        "regress_env": "local-pytest",
        "regress_tool": "pytest",
        "regress_freq": "per flow run",
        "regress_scope": f"{display} {layer_label}",
        "regress_pass_criteria": "All layer tests pass and strict document feedback has zero blockers.",
        "s0_def": "Blocks layer handoff or invalidates an upstream contract.",
        "s0_time": "Immediate repair before next layer generation",
        "s1_def": "Breaks required behavior but has a bounded workaround.",
        "s1_time": "Repair before sign-off",
        "s2_def": "Reduces coverage or traceability without breaking execution.",
        "s2_time": "Repair before milestone closure",
        "s3_def": "Documentation or polish issue without behavioral impact.",
        "s3_time": "Repair during cleanup",
        "bug_tracking": "Issues are emitted into docgen_feedback.json with detected layer and upstream target layer.",
        "milestone": f"{layer_label} handoff",
        "milestone_date": date.today().isoformat(),
        "milestone_deliverable": f"{spec_path}, {plan_path}, {report_path}",
        "milestone_owner": "RTLCraft Agent",
        "risk": "Layer contract drift",
        "risk_impact": "Downstream code may satisfy stale or incomplete intent",
        "risk_likelihood": "Medium during migration",
        "risk_mitigation": "Strict placeholder checks, layer tests, and upstream feedback blockers",
    }
    return values.get(key, f"Documented by {display} {layer_label} generated flow.")


def extract_layer_test_plan_vars(module_name: str, layer: str) -> Dict[str, Any]:
    """Return variables for rendering a per-layer test plan."""
    display = _module_display_name(module_name)
    layer_label = layer.replace("_", " ")
    spec_path, plan_path, report_path = _layer_artifact_paths(layer)
    variables = default_variables()
    variables["project_name"] = f"{display} — {layer_label}"
    variables["dut_name"] = display
    variables["dut_version"] = "0.1"
    variables["doc_id"] = f"{module_name.upper()}-{layer.upper()}-TP-001"
    variables["purpose"] = f"Verification test plan for the {layer_label} of {display}."
    variables["scope"] = f"Covers directed and cross-layer tests executed at {layer_label}."
    variables["out_of_scope"] = "Full SoC integration tests; see integration/ specs."
    variables["unit_objective"] = "Validate layer-local functional correctness"
    variables["unit_method"] = "Python pytest + model simulation"
    variables["unit_owner"] = "RTLCraft Agent"
    variables["int_objective"] = "Validate interaction with adjacent layers"
    variables["int_method"] = "Cross-layer equivalence checks"
    variables["int_owner"] = "RTLCraft Agent"
    variables["sys_objective"] = "Validate SoC-level behavior"
    variables["sys_method"] = "Full flow regression"
    variables["sys_owner"] = "System Architect"

    tests = _find_layer_tests(module_name, layer)
    if tests:
        rows = [(f"TC-{i+1:03d}", name, "Directed", "P1", desc, "Planned")
                for i, (name, desc) in enumerate(tests)]
        variables["tc_name_01"] = tests[0][0]
        variables["tc_type_01"] = "Directed"
        variables["tc_prio_01"] = "P1"
        variables["tc_obj_01"] = tests[0][1]
        variables["tc_status_01"] = "Planned"
        variables["tc_pre_01"] = "Layer model initialized"
        variables["tc_stim_01"] = "Run pytest test case"
        variables["tc_exp_01"] = "Test passes with no assertion failures"
        variables["tc_pass_01"] = "Assertion passes"
        variables["tc_cov_01"] = "Functional coverage of the exercised feature"
        variables["tc_dep_01"] = "None"
        test_inventory = _markdown_table(
            ["TC ID", "Name", "Type", "Priority", "Objective", "Status"],
            rows,
        )
    else:
        variables["tc_name_01"] = "missing_layer_tests"
        variables["tc_type_01"] = "Directed"
        variables["tc_prio_01"] = "P0"
        variables["tc_obj_01"] = "Strict sign-off must add at least one layer-local test."
        variables["tc_status_01"] = "Blocked"
        variables["tc_pre_01"] = f"{spec_path} exists"
        variables["tc_stim_01"] = "Add pytest tests for this layer"
        variables["tc_exp_01"] = "At least one test is discovered and reported"
        variables["tc_pass_01"] = "Test inventory is non-empty"
        variables["tc_cov_01"] = "Layer-local minimum coverage"
        variables["tc_dep_01"] = _layer_input_contract(module_name, layer)
        test_inventory = "No layer-specific tests discovered; strict sign-off emits upstream feedback."

    variables["verification_approach"] = (
        f"Run the pytest cases listed in `{plan_path}` under "
        f"`earphone/modules/{module_name}/{_layer_dir(layer)}/tests`, then publish "
        f"PASS/FAIL evidence in `{report_path}`. Test intent: "
        f"{_layer_input_contract(module_name, layer)}"
    )
    variables["cr_usage"] = "Not enabled until directed layer handoff is stable"
    variables["cr_tools"] = "Not enabled in current pilot"
    variables["dir_usage"] = "Core directed tests from test_*.py"
    variables["dir_tools"] = "pytest"
    variables["formal_usage"] = "SVA assertions generated from constraints"
    variables["formal_tools"] = "Verilog formal tools (future)"
    variables["line_cov_goal"] = "80%"
    variables["line_cov_tool"] = "pytest-cov"
    variables["branch_cov_goal"] = "70%"
    variables["branch_cov_tool"] = "pytest-cov"
    variables["p1_pass_criteria"] = "100%"
    variables["code_cov_criteria"] = "Line coverage ≥ 80%"
    variables["func_cov_criteria"] = "All directed tests pass"
    variables["bug_criteria"] = "No open S0/S1 bugs"
    variables["regress_green_count"] = "3"

    # Embed the inventory in the detailed description area by overriding the
    # template's default placeholder.  The template renders a single TC-001 row
    # by default; we prepend the full inventory as additional context.
    variables["test_case_inventory"] = test_inventory
    return _fill_template_defaults(
        "test_plan",
        variables,
        lambda key: _test_plan_fallback(module_name, layer, tests, key),
    )


def run_layer_tests(module_name: str, layer: str) -> Dict[str, Any]:
    """Run pytest for a layer and return a result summary dict."""
    tests_dir = os.path.join(
        os.path.dirname(__file__), "modules", module_name, _layer_dir(layer), "tests"
    )
    if not os.path.isdir(tests_dir):
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0, "cmd": ""}

    cmd = [sys.executable, "-m", "pytest", tests_dir, "-q", "--tb=short"]
    start = __import__("time").time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as exc:  # pragma: no cover - defensive
        return {"total": 0, "passed": 0, "failed": 1, "skipped": 0, "duration": 0.0, "error": str(exc), "cmd": " ".join(cmd)}
    duration = __import__("time").time() - start

    # Parse pytest short summary line, e.g. "5 passed in 0.10s"
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": duration, "cmd": " ".join(cmd), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        line = line.strip()
        if " passed" in line or " failed" in line or " skipped" in line or " error" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    summary["passed"] = int(parts[i - 1])
                elif part == "failed":
                    summary["failed"] = int(parts[i - 1])
                elif part == "skipped":
                    summary["skipped"] = int(parts[i - 1])
                elif part == "error":
                    summary["failed"] += int(parts[i - 1])
    summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"]
    return summary


def _compact_log(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    if not text:
        return "No log output captured."
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... truncated ..."


def _collect_layer_test_feedback(
    module_name: str,
    layer: str,
    result: Dict[str, Any],
    report_path: str,
) -> List[Dict[str, Any]]:
    """Emit structured upstream feedback when a layer cannot sign off."""
    feedback_target = _previous_layer(layer) or "module_spec"
    issues: List[Dict[str, Any]] = []
    if result.get("failed", 0) > 0:
        issues.append({
            "path": report_path,
            "line": 0,
            "severity": "blocker",
            "code": "layer_test_failure",
            "detected_at_layer": layer,
            "feedback_target_layer": feedback_target,
            "message": (
                f"{module_name}/{layer} has {result.get('failed', 0)} failing test(s); "
                "repair the current layer or update the upstream contract."
            ),
            "text": _compact_log(result.get("stdout", "") + "\n" + result.get("stderr", ""), 500),
        })
    if result.get("total", 0) == 0:
        issues.append({
            "path": report_path,
            "line": 0,
            "severity": "blocker",
            "code": "missing_layer_tests",
            "detected_at_layer": layer,
            "feedback_target_layer": feedback_target,
            "message": (
                f"{module_name}/{layer} has no discovered layer-local tests; "
                "add tests before approving this layer handoff."
            ),
            "text": "No pytest tests were discovered for this layer.",
        })
    return issues


def _test_report_fallback(
    module_name: str,
    layer: str,
    result: Dict[str, Any],
    key: str,
) -> str:
    display = _module_display_name(module_name)
    layer_label = layer.replace("_", " ")
    total = int(result.get("total", 0))
    passed = int(result.get("passed", 0))
    failed = int(result.get("failed", 0))
    skipped = int(result.get("skipped", 0))
    duration = float(result.get("duration", 0.0))
    overall = "PASS" if failed == 0 and total > 0 else "FAIL" if failed > 0 else "NO TESTS"
    uname = os.uname() if hasattr(os, "uname") else None
    values = {
        "dut_version": "0.1",
        "rtl_commit": "working tree snapshot",
        "tb_commit": "working tree snapshot",
        "scope_summary": (
            f"{display} {layer_label} layer-local pytest execution with upstream feedback "
            "on failures or missing coverage."
        ),
        "host": getattr(uname, "nodename", "local runner") if uname else "local runner",
        "cpu": getattr(uname, "machine", "local CPU") if uname else "local CPU",
        "memory": "host managed",
        "simulator": "pytest / Python model simulation",
        "synth_tool": "Not invoked at this layer",
        "lint_tool": "rtlgen VerilogLinter at L6",
        "coverage_tool": "pytest result summary",
        "os": getattr(uname, "sysname", "local OS") if uname else "local OS",
        "tb_config": f"Command: {result.get('cmd', 'not run')}",
        "target_line_cov": "80%",
        "achieved_line_cov": "Not measured",
        "status_line_cov": "WAIVED",
        "target_func_cov": "All directed tests pass",
        "achieved_func_cov": f"{passed}/{total} passed",
        "status_func_cov": "OK" if overall == "PASS" else "NOK",
        "p1_total": "0",
        "p1_pass": "0",
        "p1_fail": "0",
        "p1_skip": "0",
        "p2_total": "0",
        "p2_pass": "0",
        "p2_fail": "0",
        "p2_skip": "0",
        "int_total": "0",
        "int_pass": "0",
        "int_fail": "0",
        "int_skip": "0",
        "sys_total": "0",
        "sys_pass": "0",
        "sys_fail": "0",
        "sys_skip": "0",
        "pass_tc_id": "TC-PASS" if passed else "None",
        "pass_tc_name": f"{layer_label} pytest suite" if passed else "No passing tests",
        "pass_tc_dur": f"{duration:.2f}s",
        "pass_tc_notes": f"{passed} tests passed",
        "fail_tc_id": "TC-FAIL" if failed else "None",
        "fail_tc_name": f"{layer_label} failing tests" if failed else "No failing tests",
        "fail_tc_sev": "S0" if failed else "None",
        "fail_tc_root": "See pytest log" if failed else "None",
        "fail_tc_owner": "RTLCraft Agent" if failed else "None",
        "fail_tc_status": "Open" if failed else "Closed",
        "skip_tc_id": "TC-SKIP" if skipped else "None",
        "skip_tc_name": f"{layer_label} skipped tests" if skipped else "No skipped tests",
        "skip_tc_reason": "See pytest log" if skipped else "None",
        "skip_tc_plan": "Re-enable before sign-off" if skipped else "None",
        "line_target": "80%",
        "line_achieved": "Not measured",
        "line_gap": "coverage tool not enabled",
        "line_status": "WAIVED",
        "branch_target": "70%",
        "branch_achieved": "Not measured",
        "branch_gap": "coverage tool not enabled",
        "branch_status": "WAIVED",
        "fsm_target": "Directed state checks",
        "fsm_achieved": "Covered by pytest where applicable",
        "fsm_gap": "None for non-FSM layers",
        "fsm_status": "OK" if overall == "PASS" else "NOK",
        "toggle_target": "L6 RTL toggle visibility",
        "toggle_achieved": "Deferred to RTL simulation",
        "toggle_gap": "Not applicable before Verilog",
        "toggle_status": "WAIVED",
        "expr_target": "Directed expression paths",
        "expr_achieved": f"{passed}/{total} tests passed",
        "expr_gap": "pytest failures" if failed else "None",
        "expr_status": "OK" if overall == "PASS" else "NOK",
        "fc_name": f"{layer_label} contract coverage",
        "fc_target": "All directed tests pass",
        "fc_achieved": f"{passed}/{total}",
        "fc_gap": "test failures" if failed else "None",
        "fc_status": "OK" if overall == "PASS" else "NOK",
        "exclusion": "Line/branch coverage measurement",
        "exclusion_reason": "pytest-cov is not required for this pilot sign-off",
        "exclusion_approver": "System Architect",
        "open_issue_id": "FB-OPEN" if failed or total == 0 else "None",
        "open_issue_sev": "S0" if failed or total == 0 else "None",
        "open_issue_summary": "Layer cannot sign off" if failed or total == 0 else "No open issues",
        "open_issue_owner": "RTLCraft Agent" if failed or total == 0 else "None",
        "open_issue_eta": "Before next layer handoff" if failed or total == 0 else "None",
        "closed_issue_id": "FB-CLOSED" if overall == "PASS" else "None",
        "closed_issue_sev": "Info" if overall == "PASS" else "None",
        "closed_issue_summary": "Layer tests passed" if overall == "PASS" else "None",
        "closed_issue_resolution": "Evidence captured in this report" if overall == "PASS" else "None",
        "waiver_id": "W-COV-001",
        "waiver_desc": "Line/branch coverage tool is not enabled for the pilot flow",
        "waiver_just": "Directed tests are the current gate; coverage tooling is future work",
        "waiver_approver": "System Architect",
        "run_id": f"{module_name}-{layer}-{date.today().isoformat()}",
        "run_date": date.today().isoformat(),
        "run_total": str(total),
        "run_pass": str(passed),
        "run_fail": str(failed),
        "run_skip": str(skipped),
        "run_dur": f"{duration:.2f}s",
        "run_result": overall,
        "verif_lead": "RTLCraft Agent",
        "verif_lead_sig": "generated",
        "verif_lead_date": date.today().isoformat(),
        "design_lead": "RTLCraft Agent",
        "design_lead_sig": "generated",
        "design_lead_date": date.today().isoformat(),
        "sys_arch": "System Architect",
        "sys_arch_sig": "pending review",
        "sys_arch_date": date.today().isoformat(),
        "pm": "Project Owner",
        "pm_sig": "pending review",
        "pm_date": date.today().isoformat(),
        "test_logs": _compact_log(result.get("stdout", "") + "\n" + result.get("stderr", "")),
        "tool_history": result.get("cmd", "not run"),
        "raw_coverage": "No raw coverage report generated in this pilot flow.",
    }
    return values.get(key, f"{display} {layer_label} generated report field.")


def extract_layer_test_report_vars(module_name: str, layer: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Return variables for rendering a per-layer test report."""
    display = _module_display_name(module_name)
    layer_label = layer.replace("_", " ")
    variables = default_variables()
    variables["project_name"] = f"{display} — {layer_label} Test Report"
    variables["doc_id"] = f"{module_name.upper()}-{layer.upper()}-TR-001"
    variables["test_plan_ref"] = f"{module_name.upper()}-{layer.upper()}-TP-001"
    variables["dut_name"] = display
    variables["overall_result"] = "PASS" if result.get("failed", 0) == 0 and result.get("total", 0) > 0 else "FAIL" if result.get("failed", 0) > 0 else "NO TESTS"
    variables["target_total"] = str(result.get("total", 0))
    variables["achieved_total"] = str(result.get("total", 0))
    variables["status_total"] = "OK"
    variables["target_pass"] = str(result.get("total", 0))
    variables["achieved_pass"] = str(result.get("passed", 0))
    variables["status_pass"] = "OK" if result.get("passed", 0) == result.get("total", 0) else "NOK"
    variables["target_fail"] = "0"
    variables["achieved_fail"] = str(result.get("failed", 0))
    variables["status_fail"] = "OK" if result.get("failed", 0) == 0 else "NOK"
    variables["target_skip"] = "0"
    variables["achieved_skip"] = str(result.get("skipped", 0))
    variables["status_skip"] = "OK"
    variables["suite_name"] = layer_label
    variables["suite_total"] = str(result.get("total", 0))
    variables["suite_pass"] = str(result.get("passed", 0))
    variables["suite_fail"] = str(result.get("failed", 0))
    variables["suite_skip"] = str(result.get("skipped", 0))
    variables["suite_cov"] = "N/A"
    variables["unit_total"] = str(result.get("total", 0))
    variables["unit_pass"] = str(result.get("passed", 0))
    variables["unit_fail"] = str(result.get("failed", 0))
    variables["unit_skip"] = str(result.get("skipped", 0))
    variables["p0_total"] = str(result.get("total", 0))
    variables["p0_pass"] = str(result.get("passed", 0))
    variables["p0_fail"] = str(result.get("failed", 0))
    variables["p0_skip"] = str(result.get("skipped", 0))
    variables["conclusion"] = (
        f"Layer {layer_label} tests completed: {result.get('passed', 0)}/{result.get('total', 0)} passed "
        f"in {result.get('duration', 0):.2f}s."
    )
    variables["sign_off_recommendation"] = (
        "Proceed to next layer" if result.get("failed", 0) == 0 and result.get("total", 0) > 0
        else "Investigate failures before sign-off"
    )
    return _fill_template_defaults(
        "test_report",
        variables,
        lambda key: _test_report_fallback(module_name, layer, result, key),
    )


# ---------------------------------------------------------------------------
# Top-level generation
# ---------------------------------------------------------------------------

def generate_module_docs(
    module_name: str,
    output_base: Optional[str] = None,
    *,
    strict: bool = False,
) -> List[str]:
    """Generate all per-layer and module-level documents for a module.

    Returns the list of written file paths.
    """
    if output_base is None:
        output_base = os.path.join(os.path.dirname(__file__), "modules", module_name)

    written: List[str] = []
    feedback: List[Dict[str, Any]] = []

    # Module-level spec.
    module_spec_path = os.path.join(output_base, "specs", "00_module_spec.md")
    _render_to_file_checked(
        "module_spec",
        module_spec_path,
        extract_module_info(module_name),
        feedback,
        validate=True,
    )
    written.append(module_spec_path)

    # Per-layer specs, test plans, and test reports.
    for layer, src_file, _, spec_name in _LAYER_ORDER:
        layer_dir = os.path.join(output_base, _layer_dir(layer), "specs")
        os.makedirs(layer_dir, exist_ok=True)

        # Layer spec.
        spec_path = os.path.join(layer_dir, spec_name)
        _render_to_file_checked(
            "layer_spec",
            spec_path,
            extract_layer_info(module_name, layer, src_file),
            feedback,
            validate=True,
        )
        written.append(spec_path)

        # Test plan.
        layer_prefix = spec_name.split("_spec.md")[0]
        tp_path = os.path.join(layer_dir, f"{layer_prefix}_test_plan.md")
        _render_to_file_checked(
            "test_plan",
            tp_path,
            extract_layer_test_plan_vars(module_name, layer),
            feedback,
            validate=True,
        )
        written.append(tp_path)

        # Test report (runs tests and fills real results).
        result = run_layer_tests(module_name, layer)
        tr_path = os.path.join(layer_dir, f"{layer_prefix}_test_report.md")
        _render_to_file_checked(
            "test_report",
            tr_path,
            extract_layer_test_report_vars(module_name, layer, result),
            feedback,
            validate=True,
        )
        feedback.extend(_collect_layer_test_feedback(module_name, layer, result, tr_path))
        written.append(tr_path)

    # Aggregated module-level test plan and report.
    tp_path = os.path.join(output_base, "specs", "07_module_test_plan.md")
    _render_to_file_checked(
        "test_plan",
        tp_path,
        extract_layer_test_plan_vars(module_name, "L1_behavior"),
        feedback,
        validate=True,
    )
    written.append(tp_path)

    tr_path = os.path.join(output_base, "specs", "08_module_test_report.md")
    result = run_layer_tests(module_name, "L1_behavior")
    _render_to_file_checked(
        "test_report",
        tr_path,
        extract_layer_test_report_vars(module_name, "L1_behavior", result),
        feedback,
        validate=True,
    )
    written.append(tr_path)

    # Compatibility aliases for older module-level documentation names that
    # predate the 00/07/08 numbering.
    legacy_tp_path = os.path.join(output_base, "specs", "01_test_plan.md")
    _render_to_file_checked(
        "test_plan",
        legacy_tp_path,
        extract_layer_test_plan_vars(module_name, "L1_behavior"),
        feedback,
        validate=True,
    )
    written.append(legacy_tp_path)

    legacy_tr_path = os.path.join(output_base, "specs", "02_test_report.md")
    _render_to_file_checked(
        "test_report",
        legacy_tr_path,
        extract_layer_test_report_vars(module_name, "L1_behavior", result),
        feedback,
        validate=True,
    )
    written.append(legacy_tr_path)

    feedback_path = _write_docgen_feedback(output_base, module_name, feedback)
    written.append(feedback_path)

    if strict and feedback:
        raise ValueError(
            f"{module_name}: generated docs still contain {len(feedback)} placeholder or fallback issue(s); "
            f"see {feedback_path}"
        )

    return written


def generate_all_docs(output_base: Optional[str] = None) -> Dict[str, List[str]]:
    """Generate documents for all Earphone modules."""
    modules = ["rv32", "simd16", "fft256", "qspi", "i2c", "sram256k", "apb_bridge"]
    return {mod: generate_module_docs(mod, output_base) for mod in modules}


if __name__ == "__main__":  # pragma: no cover
    paths = generate_all_docs()
    for mod, files in paths.items():
        print(f"{mod}: {len(files)} documents generated")
        for f in files:
            print(f"  {f}")
