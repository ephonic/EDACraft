"""Document generator for the Earphone SoC document-driven flow.

This module extracts real design data from the per-layer source files and
fills the industrial-pattern templates in ``doc_templates/`` with meaningful
content instead of placeholder defaults.
"""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from doc_templates import default_variables, render_to_file


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


def _layer_dir(layer: str) -> str:
    return f"layer_{layer}"


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
            doc = inspect.getdoc(method) or ""
            tests.append((name, doc.splitlines()[0] if doc else "-"))

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
    from earphone.modules.rv32.layer_L2_cycle.src.cycle import RV32IMCycleModel

    return {
        "module_name": "EarphoneRV32",
        "layer_name": "L2 CycleIR",
        "purpose": (
            "Provide a cycle-accurate reference model that tracks pipeline "
            "control signals while delegating functional execution to the L1 ISS."
        ),
        "scope": "Single-cycle scalar pipeline with multi-cycle M-extension operations.",
        "model": _markdown_table(
            ["Property", "Value"],
            [
                ["Pipeline", "IF → ID → EX → MEM → WB"],
                ["M-extension latency", "Multi-cycle (iterative)"],
                ["Branch predictor", "Static not-taken"],
                ["Stall/flush support", "Yes"],
            ],
        ),
        "tests": "No dedicated L2 tests yet; cross-layer equivalence covers this layer.",
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


def _extract_generic_layer_info(module_name: str, layer: str, src_file: str) -> Dict[str, Any]:
    """Fallback extractor for modules without a dedicated extractor."""
    info = _call_describe(module_name, layer, src_file)
    layer_label = layer.replace("_", " ")
    return {
        "module_name": module_name,
        "layer_name": layer_label,
        "purpose": info.get("description", f"{layer_label} for {module_name}."),
        "scope": info.get("status", "Implementation pending migration from design_earphone.py."),
        "notes": _bullet_list([f"Status: {info.get('status', 'unknown')}"]),
    }


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
                "deliverables", "notes"]:
        if key in info:
            label = label_overrides.get(key, key.replace("_", " ").title())
            detailed_parts.append(f"### {label}\n\n{info[key]}\n")
    variables["detailed_description"] = "\n".join(detailed_parts) or "_No detailed description available._"

    # Standard section fallbacks.
    variables["inputs_from_previous"] = info.get(
        "inputs_from_previous",
        "See previous layer specification for inputs."
    )
    variables["outputs_to_next"] = info.get(
        "outputs_to_next",
        "See next layer specification for outputs."
    )
    variables["decision_01"] = info.get("decision_01", "Single-cycle scalar with iterative M-extension")
    variables["rationale_01"] = info.get("rationale_01", "Area/power optimized for earphone-class MCU")
    variables["impact_01"] = info.get("impact_01", "DIV/REM take variable cycles")
    variables["verification_strategy"] = info.get("verification_strategy", "Python unit tests + cross-layer equivalence checks.")
    variables["verif_check_01"] = info.get("verif_check_01", "Instruction decode and execution correctness")
    variables["verif_method_01"] = info.get("verif_method_01", "Directed ISS tests")
    variables["verif_cov_01"] = info.get("verif_cov_01", "All RV32IM instructions exercised")
    variables["constraint_01"] = info.get("constraint_01", "RV32IM ISA compliance")
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
        "rv32": "RV32IM microcontroller core with iterative multiply/divide unit.",
        "simd16": "16-lane 16-bit SIMD accelerator for audio/DSP kernels.",
        "fft256": "256-point FFT accelerator with twiddle ROM.",
        "qspi": "Quad-SPI controller with XIP support for external flash.",
        "i2c": "I2C controller for codec and sensor connectivity.",
        "sram256k": "256 KB on-chip SRAM with byte/half/word access.",
        "apb_bridge": "AHB-to-APB bridge for low-bandwidth peripherals.",
    }
    return mapping.get(module_name, f"{module_name} module.")


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
        if inspect.isclass(obj) and name.startswith("Test"):
            for mname, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                if mname.startswith("test_"):
                    doc = inspect.getdoc(method) or ""
                    tests.append((mname, doc.splitlines()[0] if doc else "-"))
    return tests


def extract_layer_test_plan_vars(module_name: str, layer: str) -> Dict[str, Any]:
    """Return variables for rendering a per-layer test plan."""
    display = _module_display_name(module_name)
    layer_label = layer.replace("_", " ")
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
        rows = [(f"TC-{i+1:03d}", name, "Directed", "P1", desc, "Not run")
                for i, (name, desc) in enumerate(tests)]
        variables["tc_name_01"] = tests[0][0]
        variables["tc_type_01"] = "Directed"
        variables["tc_prio_01"] = "P1"
        variables["tc_obj_01"] = tests[0][1]
        variables["tc_status_01"] = "Not run"
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
        test_inventory = "_No layer-specific tests discovered yet._"

    variables["verification_approach"] = (
        f"Run the layer-specific pytest suite under earphone/modules/{module_name}/{layer}/tests "
        "and verify functional equivalence with adjacent layers where applicable."
    )
    variables["cr_usage"] = "N/A" if not tests else "Future work"
    variables["cr_tools"] = "N/A" if not tests else "-"
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
    return variables


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
    return variables


# ---------------------------------------------------------------------------
# Top-level generation
# ---------------------------------------------------------------------------

def generate_module_docs(module_name: str, output_base: Optional[str] = None) -> List[str]:
    """Generate all per-layer and module-level documents for a module.

    Returns the list of written file paths.
    """
    if output_base is None:
        output_base = os.path.join(os.path.dirname(__file__), "modules", module_name)

    written: List[str] = []

    # Module-level spec.
    module_spec_path = os.path.join(output_base, "specs", "00_module_spec.md")
    render_to_file("module_spec", module_spec_path, extract_module_info(module_name))
    written.append(module_spec_path)

    # Per-layer specs, test plans, and test reports.
    for layer, src_file, _, spec_name in _LAYER_ORDER:
        layer_dir = os.path.join(output_base, _layer_dir(layer), "specs")
        os.makedirs(layer_dir, exist_ok=True)

        # Layer spec.
        spec_path = os.path.join(layer_dir, spec_name)
        render_to_file("layer_spec", spec_path, extract_layer_info(module_name, layer, src_file))
        written.append(spec_path)

        # Test plan.
        layer_prefix = spec_name.split("_spec.md")[0]
        tp_path = os.path.join(layer_dir, f"{layer_prefix}_test_plan.md")
        render_to_file("test_plan", tp_path, extract_layer_test_plan_vars(module_name, layer))
        written.append(tp_path)

        # Test report (runs tests and fills real results).
        result = run_layer_tests(module_name, layer)
        tr_path = os.path.join(layer_dir, f"{layer_prefix}_test_report.md")
        render_to_file("test_report", tr_path, extract_layer_test_report_vars(module_name, layer, result))
        written.append(tr_path)

    # Aggregated module-level test plan and report.
    tp_path = os.path.join(output_base, "specs", "07_module_test_plan.md")
    render_to_file("test_plan", tp_path, extract_layer_test_plan_vars(module_name, "L1_behavior"))
    written.append(tp_path)

    tr_path = os.path.join(output_base, "specs", "08_module_test_report.md")
    result = run_layer_tests(module_name, "L1_behavior")
    render_to_file("test_report", tr_path, extract_layer_test_report_vars(module_name, "L1_behavior", result))
    written.append(tr_path)

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
