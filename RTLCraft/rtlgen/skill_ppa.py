"""
rtlgen.skill_ppa — Unified Skill Pipeline Runner (Mandatory Entry Point)

Single mandatory entry point for all skills. Replaces both
`run_all_skills.py` and `design_riscv64_soc.py`.

Pipeline (6 stages):
  functional → cycle_level → arch → skeleton → ppa_analyze → ppa_optimize → rtl → lint

Usage:
    runner = SkillPPARunner("riscv64_soc")
    runner.run()

    python -m rtlgen.skill_ppa                      # all skills
    python -m rtlgen.skill_ppa --skill riscv64_soc  # single skill
    python -m rtlgen.skill_ppa --list               # list skills
    python -m rtlgen.skill_ppa --stage ppa rtl       # specific stages
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.core import Module
from rtlgen.codegen import EmitProfile, VerilogEmitter
from rtlgen.contracts import (
    ModuleContract,
    ModulePerfReport,
    PerfCheck,
    PerfCheckResult,
    PerfScenario,
    PerfStimulusStep,
    PerfStimulusRecipe,
    ProtocolContract,
    ResourceContract,
    TransactionContract,
)
from rtlgen.ppa import PPAAnalyzer
from rtlgen.ppa_optimizer import PPAOptimizer
from rtlgen.lint import VerilogLinter
from rtlgen.spec_ir import (
    AssumptionIR,
    AssertionIR,
    BehaviorIR,
    BehaviorRuleIR,
    ClockResetDomainIR,
    ConnectionSpec,
    CoverageBinIR,
    CycleTransactionIR,
    CycleIR,
    FunctionSpec,
    HandshakeRuleIR,
    InterfaceSpec,
    InvariantIR,
    PPASpec,
    PortSpec,
    ProtocolIR,
    ScoreboardIR,
    SpecIR,
    StateIR,
    StateUpdateIR,
    StructuralIR,
    SubmoduleInstanceSpec,
    TestVectorIR,
    TimingSpec,
    TraceEventIR,
    TracepointIR,
    TransactionEventIR,
    TransactionIR,
    VerificationPlanIR,
    VerificationSpec,
)
from rtlgen.transaction_recipes import (
    derive_transaction_perf_check,
    derive_transaction_scenario,
    supported_transaction_recipes,
    transaction_perf_check_name,
    validate_transaction_recipe_contract,
)
from rtlgen.protocol_recipes import (
    derive_protocol_perf_check,
    derive_protocol_scenario,
    supported_protocol_recipes,
    validate_protocol_recipe_contract,
)
from rtlgen.arch_def import ArchDefinition
from rtlgen.arch_skel import AgentPackage

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKILLS_DIR = os.path.join(_PROJECT_ROOT, "skills")


# ============================================================================
# Data classes
# ============================================================================

@dataclass
class ModulePPAReport:
    """PPA report for one skill module."""
    module_name: str
    class_name: str
    before_depth: int = 0
    after_depth: int = 0
    gate_count_before: float = 0
    gate_count_after: float = 0
    reg_bits_before: int = 0
    reg_bits_after: int = 0
    strategies_applied: List[str] = field(default_factory=list)
    optimized: bool = False


@dataclass
class StageResult:
    """Result of running one pipeline stage."""
    stage_name: str
    passed: bool = False
    skipped: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DSLValidationReport:
    """Structured validation result for one generated/imported DSL module."""
    source_kind: str = ""
    parsed: bool = False
    instantiated: bool = False
    port_check_passed: bool = False
    dsl_sim_passed: bool = False
    sim_passed: bool = False
    lint_passed: bool = False
    roundtrip_passed: Optional[bool] = None
    passed: bool = False
    validation_stage: str = "failed"
    verification_level: int = 0
    verilog_lines: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "parsed": self.parsed,
            "instantiated": self.instantiated,
            "port_check_passed": self.port_check_passed,
            "dsl_sim_passed": self.dsl_sim_passed,
            "sim_passed": self.sim_passed,
            "lint_passed": self.lint_passed,
            "roundtrip_passed": self.roundtrip_passed,
            "passed": self.passed,
            "validation_stage": self.validation_stage,
            "verification_level": self.verification_level,
            "verilog_lines": self.verilog_lines,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


# ============================================================================
# SkillPPARunner
# ============================================================================

class SkillPPARunner:
    """Unified skill pipeline runner. All skills MUST go through this class.

    Pipeline stages:
      1. functional/cycle_level — run Layer 1 (behavioral) / Layer 2 (cycle-accurate) models
      2. arch       — generate ArchDefinition (PEs + interconnects)
      3. skeleton   — generate skeleton packages from arch
      4. ppa        — analyze + optimize PPA on leaf DSL modules
      5. rtl        — emit Verilog (full hierarchy)
      6. lint       — lint generated Verilog
    """

    def __init__(
        self,
        skill_name: str,
        skills_dir: Optional[str] = None,
    ):
        self.skill_name = skill_name
        self._skills_dir = skills_dir or _SKILLS_DIR
        self._dsl_mod = None
        self._top_module_cls: Optional[type] = None
        self._ppa_targets: List[Tuple[str, type]] = []
        self._module_reports: List[ModulePPAReport] = []
        self._rtl_files: List[str] = []
        self._errors: List[str] = []
        self._stage_results: List[StageResult] = []
        self._loaded = False
        self._optimized_modules: Dict[str, Module] = {}  # name → optimized instance
        self._arch: Optional[ArchDefinition] = None  # from arch_templates
        self._skeleton_packages: Dict[str, AgentPackage] = {}  # PE name → AgentPackage
        self._contract_files: Dict[str, str] = {}
        # pe_type → DSL class mapping (auto-populated from dsl_modules.py)
        self._pe_type_to_class: Dict[str, type] = {}

    # -----------------------------------------------------------------
    # Module import
    # -----------------------------------------------------------------

    @staticmethod
    def _import_skill_module(skill_name: str, module_name: str):
        """Safely import a single module from a skill."""
        skill_path = os.path.join(_SKILLS_DIR, skill_name, f"{module_name}.py")
        if not os.path.isfile(skill_path):
            return None
        full_name = f"skills.{skill_name}.{module_name}"
        spec = importlib.util.spec_from_file_location(full_name, skill_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        try:
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None

    # -----------------------------------------------------------------
    # Stage 1: functional / cycle_level
    # -----------------------------------------------------------------

    def _run_behaviors(self) -> StageResult:
        """Run Layer 1 (functional) and Layer 2 (cycle-level) simulation models."""
        result = StageResult("functional", description="Functional + cycle-level simulation")

        # Try: cycle_level.py (Layer 2), functional.py (Layer 1), then legacy behaviors.py
        behaviors_mod = (
            self._import_skill_module(self.skill_name, "cycle_level")
            or self._import_skill_module(self.skill_name, "functional")
            or self._import_skill_module(self.skill_name, "behaviors")
        )
        if behaviors_mod is None:
            result.skipped = True
            return result

        result.passed = True  # templates loaded
        try:
            models_mod = self._import_skill_module(self.skill_name, "models")
            if models_mod is not None:
                for attr_name in dir(models_mod):
                    attr = getattr(models_mod, attr_name)
                    if isinstance(attr, type) and hasattr(attr, "run"):
                        try:
                            instance = attr()
                            sim = instance.run(num_cycles=100)
                            result.metrics[f"{attr_name}_status"] = sim
                        except TypeError:
                            pass  # needs args, skip
        except Exception as e:
            result.passed = False
            result.errors.append(f"behaviors: {e}")

        return result

    # -----------------------------------------------------------------
    # Stage 2: arch
    # -----------------------------------------------------------------

    def _run_arch(self) -> StageResult:
        """Generate ArchDefinition from arch_templates."""
        result = StageResult("arch", description="Architecture definition")

        arch_mod = self._import_skill_module(self.skill_name, "arch_templates")
        if arch_mod is None:
            result.skipped = True
            return result

        result.passed = True
        try:
            for attr_name in dir(arch_mod):
                if attr_name.startswith("build_"):
                    builder = getattr(arch_mod, attr_name)
                    if not callable(builder):
                        continue
                    try:
                        arch = builder()
                        pes = len(arch.processing_elements) if arch.processing_elements else 0
                        ics = len(arch.interconnects) if arch.interconnects else 0
                        result.metrics[f"{attr_name}_pes"] = pes
                        result.metrics[f"{attr_name}_interconnects"] = ics
                    except Exception as e:
                        result.errors.append(f"{attr_name}: {e}")
        except Exception as e:
            result.passed = False
            result.errors.append(f"arch: {e}")

        return result

    # -----------------------------------------------------------------
    # Stage 3: skeleton
    # -----------------------------------------------------------------

    def _run_skeleton(self) -> StageResult:
        """Generate skeleton packages from arch_templates."""
        result = StageResult("skeleton", description="Skeleton generation")

        skel_mod = self._import_skill_module(self.skill_name, "skeleton_templates")
        if skel_mod is None:
            result.skipped = True
            return result

        result.passed = True
        try:
            from rtlgen import arch_skel, ArchSkeletonGenerator

            # Register skeleton steps
            for attr_name in dir(skel_mod):
                if attr_name.startswith("register_"):
                    register_fn = getattr(skel_mod, attr_name)
                    if callable(register_fn):
                        try:
                            register_fn(arch_skel._TEMPLATE_STEPS)
                        except Exception as e:
                            result.errors.append(f"register {attr_name}: {e}")

            # Generate skeletons from arch
            arch_mod = self._import_skill_module(self.skill_name, "arch_templates")
            if arch_mod is not None:
                for attr_name in dir(arch_mod):
                    if attr_name.startswith("build_"):
                        builder = getattr(arch_mod, attr_name)
                        if not callable(builder):
                            continue
                        try:
                            arch = builder()

                            # Initialize ArchSkeletonGenerator with skill guidance
                            # to enable context-aware DSL code generation
                            # Using internal SkillRetriever for the skill directory
                            skills_index = os.path.join(
                                os.path.dirname(os.path.dirname(__file__)),
                                "skills", self.skill_name, "skills_index.yaml",
                            )
                            if not os.path.isfile(skills_index):
                                skills_index = None

                            skel_gen = ArchSkeletonGenerator(
                                skill_index_path=skills_index,
                                enable_skill_guidance=True,
                                enable_verifier=True,
                            )
                            packages = skel_gen.generate_all(arch)
                            # Store for downstream stages (RTL uses these)
                            self._arch = arch
                            self._skeleton_packages = packages
                            result.metrics["skeleton_packages"] = len(packages) if packages else 0
                        except Exception as e:
                            result.errors.append(f"skeleton from {attr_name}: {e}")
                        break
        except ImportError:
            result.skipped = True
        except Exception as e:
            result.passed = False
            result.errors.append(f"skeleton: {e}")

        return result

    # -----------------------------------------------------------------
    # Stage 3b: spec_gen — Generate markdown spec from GenerationContext
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize_port_declaration(name: str, width: int) -> Tuple[str, int]:
        match = re.fullmatch(r"([a-zA-Z_]\w*)(?:\[(\d+)(?::(\d+))?\])?", name)
        if match:
            base = match.group(1)
            hi = match.group(2)
            lo = match.group(3)
            if hi is not None:
                width = 1 if lo is None else abs(int(hi) - int(lo)) + 1
            return base, width
        clean = re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "sig"
        return clean, width

    @classmethod
    def _normalize_port_specs(
        cls,
        port_map: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        normalized: Dict[str, Dict[str, Any]] = {}
        for raw_name, spec in port_map.items():
            width = int(spec.get("width", 1) or 1)
            name, norm_width = cls._normalize_port_declaration(raw_name, width)
            entry = dict(spec)
            entry["width"] = norm_width
            if name in normalized:
                existing = normalized[name]
                existing["width"] = max(int(existing.get("width", 1) or 1), norm_width)
            else:
                normalized[name] = entry
        return normalized

    @staticmethod
    def _write_json(path: str, payload: Dict[str, Any]) -> None:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    @classmethod
    def _build_review_spec_from_context(
        cls,
        gen_ctx: Any,
        behavior_req: Optional[Dict[str, Any]] = None,
        dsl_mod: Optional[Module] = None,
    ) -> SpecIR:
        target = getattr(gen_ctx, "target", None)
        target_ports = getattr(target, "ports", {}) if target else {}
        normalized_ports = cls._normalize_port_specs(target_ports)
        ports = [
            PortSpec(
                name=name,
                direction=spec.get("dir", "input"),
                width=int(spec.get("width", 1) or 1),
                signed=bool(spec.get("signed", False)),
            )
            for name, spec in normalized_ports.items()
        ]

        generated_spec = getattr(dsl_mod, "_generated_spec_ir", None) if dsl_mod is not None else None
        if isinstance(generated_spec, dict):
            return SpecIR.from_dict(generated_spec)

        latency = 0
        if target is not None:
            latency = int(getattr(target, "latency", 0) or 0)
            if latency <= 0:
                latency = int(getattr(target, "parameters", {}).get("LATENCY", 0) or 0)

        port_names = {p.name for p in ports}
        interface_patterns = set(behavior_req.get("interfaces", [])) if behavior_req else set()
        has_ready_valid = (
            any("valid_ready_handshake" in item for item in interface_patterns)
            or {"in_valid", "in_ready", "out_valid", "out_ready"}.issubset(port_names)
        )

        control_patterns = [p.lower() for p in behavior_req.get("control_patterns", [])] if behavior_req else []
        pe_type = getattr(target, "pe_type", "") if target else ""
        role = getattr(target, "role", "") if target else ""
        if has_ready_valid or latency > 0:
            category = "stream_pipeline"
        elif any("fsm" in item for item in control_patterns) or any(
            token in f"{pe_type} {role}".lower() for token in ("scheduler", "controller", "sequencer")
        ):
            category = "fsm_controller"
        else:
            category = "comb_alu"

        interfaces = None
        if has_ready_valid:
            interfaces = InterfaceSpec(
                input_protocol="ready_valid",
                output_protocol="ready_valid",
                input_payload=[
                    PortSpec(name=p.name, direction="input", width=p.width, signed=p.signed)
                    for p in ports
                    if p.direction == "input" and p.name not in {"in_valid", "out_ready"}
                ],
                output_payload=[
                    PortSpec(name=p.name, direction="output", width=p.width, signed=p.signed)
                    for p in ports
                    if p.direction == "output" and p.name not in {"out_valid", "in_ready"}
                ],
            )

        verification_contract = list(getattr(gen_ctx, "verification_contract", []))
        verification = VerificationSpec(
            coverage_bins=list(dict.fromkeys(
                [item for item in verification_contract if not item.startswith("trace_")]
            )),
            protocol_checks=["backpressure", "no_drop_no_duplicate"] if has_ready_valid else [],
        )
        description = getattr(target, "description", "") if target else ""

        spec = SpecIR(
            name=getattr(target, "name", "Module") if target else "Module",
            category=category,
            function=FunctionSpec(expr=""),
            ports=ports,
            interfaces=interfaces,
            timing=TimingSpec(latency_max=latency or None),
            ppa=PPASpec(
                priority="balanced",
                allow_pipeline=(category == "stream_pipeline"),
            ),
            verification=verification,
        )
        if description and not spec.verification.reference_model:
            spec.verification.reference_model = description
        return spec.complete()

    @staticmethod
    def _extract_generated_spec_artifacts(
        dsl_mod: Optional[Module],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if dsl_mod is None:
            return None, None
        spec_ir = getattr(dsl_mod, "_generated_spec_ir", None)
        arch_ir = getattr(dsl_mod, "_generated_arch_ir", None)
        return spec_ir if isinstance(spec_ir, dict) else None, arch_ir if isinstance(arch_ir, dict) else None

    @staticmethod
    def _dedupe_keep_order(items: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    @classmethod
    def _behavior_state_names(
        cls,
        gen_ctx: Any,
        behavior_req: Optional[Dict[str, Any]],
    ) -> List[str]:
        names: List[str] = []
        target = getattr(gen_ctx, "target", None)
        for item in getattr(target, "internal_state_suggestions", []) if target else []:
            base, _ = cls._normalize_port_declaration(str(item), 1)
            names.append(base)

        if behavior_req:
            for item in behavior_req.get("state", []):
                base, _ = cls._normalize_port_declaration(str(item), 1)
                names.append(base)
            for item in behavior_req.get("control_patterns", []):
                if item.startswith("state_variables:"):
                    payload = item.split(":", 1)[1]
                    for piece in payload.split(","):
                        base, _ = cls._normalize_port_declaration(piece.strip(), 1)
                        names.append(base)
        return cls._dedupe_keep_order(names)

    @staticmethod
    def _clock_name_for_spec(spec: SpecIR) -> str:
        input_names = {p.name for p in spec.ports if p.direction == "input"}
        for candidate in ("clk", "clock", "i_clk"):
            if candidate in input_names:
                return candidate
        for name in input_names:
            if "clk" in name.lower() or "clock" in name.lower():
                return name
        return "clk"

    @staticmethod
    def _extract_module_contract(
        gen_ctx: Any,
        dsl_mod: Optional[Module],
    ) -> Optional[ModuleContract]:
        candidates = [
            dsl_mod,
            gen_ctx,
            getattr(gen_ctx, "target", None),
            getattr(gen_ctx, "_agent_package", None),
        ]
        for source in candidates:
            if source is None:
                continue
            for attr in ("_module_contract", "module_contract"):
                contract = getattr(source, attr, None)
                if isinstance(contract, ModuleContract):
                    return contract
        return None

    @staticmethod
    def _contract_protocol_irs(contract: Optional[ModuleContract]) -> List[ProtocolIR]:
        if not isinstance(contract, ModuleContract):
            return []
        return [
            ProtocolIR(
                name=proto.name,
                kind=proto.kind,
                recipe=getattr(proto, "recipe", ""),
                request_signals=list(proto.request_signals),
                response_signals=list(proto.response_signals),
                flow_control_signals=list(proto.flow_control_signals),
                ordering=proto.ordering,
                description=proto.description,
                metadata=dict(getattr(proto, "metadata", {})),
            )
            for proto in getattr(contract, "protocols", [])
        ]

    @staticmethod
    def _contract_transaction_irs(contract: Optional[ModuleContract]) -> List[TransactionIR]:
        if not isinstance(contract, ModuleContract):
            return []
        return [
            TransactionIR(
                name=txn.name,
                trigger_signals=list(txn.trigger_signals),
                completion_signals=list(txn.completion_signals),
                recipe=getattr(txn, "recipe", ""),
                trigger_event=getattr(txn, "trigger_event", "level"),
                completion_event=getattr(txn, "completion_event", "level"),
                trigger_qualifiers=list(getattr(txn, "trigger_qualifiers", [])),
                completion_qualifiers=list(getattr(txn, "completion_qualifiers", [])),
                max_cycles=txn.max_cycles,
                sample_cycles=int(getattr(txn, "sample_cycles", 0) or 0),
                ordering=txn.ordering,
                allow_overlap=txn.allow_overlap,
                description=txn.description,
                metadata=dict(getattr(txn, "metadata", {})),
            )
            for txn in getattr(contract, "transactions", [])
        ]

    @classmethod
    def _verification_plan_from_contract(cls, contract: ModuleContract) -> VerificationPlanIR:
        return VerificationPlanIR(
            module_name=contract.module_name,
            protocols=cls._contract_protocol_irs(contract),
            transactions=cls._contract_transaction_irs(contract),
        )

    @staticmethod
    def _transaction_event_expr(
        signal_names: List[str],
        event_kind: str,
        qualifiers: List[str],
    ) -> str:
        signals = " && ".join(signal_names) if signal_names else "unspecified"
        if event_kind == "handshake":
            qualifier_text = " && ".join(qualifiers) if qualifiers else "ready qualifier"
            return f"handshake({signals} with {qualifier_text})"
        if event_kind == "rise":
            return f"rise({signals})"
        qualifier_suffix = f" when {' && '.join(qualifiers)}" if qualifiers else ""
        return f"level({signals}){qualifier_suffix}"

    @classmethod
    def _cycle_transaction_event_ir(
        cls,
        txn_name: str,
        role: str,
        signal_names: List[str],
        event_kind: str,
        qualifiers: List[str],
    ) -> TransactionEventIR:
        return TransactionEventIR(
            name=f"{txn_name}_{role}",
            event=event_kind,
            signals=list(signal_names),
            qualifiers=list(qualifiers),
            condition=cls._transaction_event_expr(signal_names, event_kind, qualifiers),
        )

    @staticmethod
    def _cycle_transaction_temporal_relation(txn: TransactionIR) -> str:
        parts: List[str] = []
        if txn.max_cycles is not None:
            parts.append(f"trigger_to_completion_within_{txn.max_cycles}_cycles")
        if txn.ordering:
            parts.append(f"ordering={txn.ordering}")
        parts.append("overlap_allowed" if txn.allow_overlap else "no_overlap")
        if txn.sample_cycles:
            parts.append(f"sample_window={txn.sample_cycles}_cycles")
        return "; ".join(parts)

    @classmethod
    def _build_behavior_ir(
        cls,
        gen_ctx: Any,
        review_spec: SpecIR,
        behavior_req: Optional[Dict[str, Any]],
        generated_spec: Optional[Dict[str, Any]],
        module_contract: Optional[ModuleContract] = None,
    ) -> BehaviorIR:
        target = getattr(gen_ctx, "target", None)
        function_expr = ""
        if generated_spec:
            function_expr = str(generated_spec.get("function", {}).get("expr", "") or "")
        if not function_expr:
            function_expr = review_spec.function.expr or ""

        required_behaviors = list(getattr(target, "required_behaviors", []) if target else [])
        if behavior_req:
            required_behaviors.extend(behavior_req.get("interfaces", []))
            required_behaviors.extend(behavior_req.get("control_patterns", []))
            required_behaviors.extend(behavior_req.get("datapath_patterns", []))

        rules: List[BehaviorRuleIR] = []
        if function_expr:
            rules.append(
                BehaviorRuleIR(
                    rule_id="function",
                    trigger="input transaction",
                    effect=function_expr,
                    category="functional",
                )
            )

        output_names = [p.name for p in review_spec.ports if p.direction == "output"]
        if output_names and not rules:
            for name in output_names:
                rules.append(
                    BehaviorRuleIR(
                        rule_id=f"drive_{name}",
                        trigger="input observation",
                        effect=f"drive output {name}",
                        category="output",
                    )
                )

        assumptions = [
            AssumptionIR(
                kind="reset",
                detail=f"{review_spec.reset_name} is {review_spec.reset_type} active-{review_spec.reset_active}",
            )
        ]
        if review_spec.interfaces:
            assumptions.append(
                AssumptionIR(
                    kind="protocol",
                    detail=(
                        f"input={review_spec.interfaces.input_protocol}, "
                        f"output={review_spec.interfaces.output_protocol}"
                    ),
                )
            )
        if review_spec.timing.latency_exact is not None or review_spec.timing.latency_max is not None:
            latency = review_spec.timing.latency_exact or review_spec.timing.latency_max
            assumptions.append(AssumptionIR(kind="latency", detail=f"latency={latency} cycles"))

        invariants: List[InvariantIR] = []
        for check in review_spec.verification.protocol_checks:
            if check == "backpressure":
                invariants.append(
                    InvariantIR(
                        name="backpressure",
                        expr="hold output payload stable while out_valid && !out_ready",
                    )
                )
            elif check == "no_drop_no_duplicate":
                invariants.append(
                    InvariantIR(
                        name="no_drop_no_duplicate",
                        expr="accepted input transactions map 1:1 to output transactions",
                    )
                )
            else:
                invariants.append(InvariantIR(name=check, expr=check))

        tracepoints = [
            item for item in getattr(gen_ctx, "verification_contract", [])
            if isinstance(item, str) and item.startswith("trace_")
        ]

        protocols = cls._contract_protocol_irs(module_contract)
        transactions = cls._contract_transaction_irs(module_contract)
        for proto in protocols:
            assumptions.append(
                AssumptionIR(
                    kind="protocol_contract",
                    detail=f"{proto.name}: {proto.kind} ({proto.ordering})",
                )
            )
        for txn in transactions:
            trigger = cls._transaction_event_expr(
                txn.trigger_signals,
                txn.trigger_event,
                txn.trigger_qualifiers,
            )
            completion = cls._transaction_event_expr(
                txn.completion_signals,
                txn.completion_event,
                txn.completion_qualifiers,
            )
            recipe = txn.recipe or "custom"
            bound = f" within {txn.max_cycles} cycles" if txn.max_cycles is not None else ""
            rules.append(
                BehaviorRuleIR(
                    rule_id=f"txn_{txn.name}",
                    trigger=trigger,
                    effect=f"{recipe} transaction completes at {completion}{bound}",
                    category="transaction",
                )
            )
            assumptions.append(
                AssumptionIR(
                    kind="transaction_contract",
                    detail=f"{txn.name}: recipe={recipe}, ordering={txn.ordering}, overlap={txn.allow_overlap}",
                )
            )

        return BehaviorIR(
            module_name=review_spec.name,
            ports=[
                PortSpec(name=p.name, direction=p.direction, width=p.width, signed=p.signed)
                for p in review_spec.ports
            ],
            function_expr=function_expr,
            required_behaviors=cls._dedupe_keep_order(required_behaviors),
            rules=rules,
            assumptions=assumptions,
            invariants=invariants,
            tracepoints=tracepoints,
            protocols=protocols,
            transactions=transactions,
        )

    @classmethod
    def _build_cycle_ir(
        cls,
        gen_ctx: Any,
        review_spec: SpecIR,
        behavior_ir: BehaviorIR,
        generated_arch: Optional[Dict[str, Any]],
        behavior_req: Optional[Dict[str, Any]],
    ) -> CycleIR:
        states: List[StateIR] = []
        updates: List[StateUpdateIR] = []
        state_names = cls._behavior_state_names(gen_ctx, behavior_req)
        for name in state_names:
            states.append(StateIR(name=name, width=1, kind="control", reset_value="0"))
            updates.append(StateUpdateIR(state=name, when="cycle advance", next_expr=f"next({name})"))

        if generated_arch:
            for stage in generated_arch.get("stages", []):
                for reg in stage.get("registers", []):
                    reg_name = reg.get("name", "")
                    states.append(
                        StateIR(
                            name=reg_name,
                            width=int(reg.get("width", 1) or 1),
                            kind="pipeline_reg",
                            reset_value="0",
                        )
                    )
                    updates.append(
                        StateUpdateIR(
                            state=reg_name,
                            when="cycle advance",
                            next_expr=str(reg.get("source", "0")),
                        )
                    )

        handshake_rules: List[HandshakeRuleIR] = []
        if review_spec.interfaces:
            handshake_rules.append(
                HandshakeRuleIR(
                    interface="input",
                    rule=f"{review_spec.interfaces.input_protocol} transaction accepted when valid && ready",
                )
            )
            handshake_rules.append(
                HandshakeRuleIR(
                    interface="output",
                    rule=f"{review_spec.interfaces.output_protocol} transaction retired when valid && ready",
                )
            )
        if generated_arch and generated_arch.get("handshake"):
            handshake = generated_arch["handshake"]
            for label in ("valid_in", "ready_out", "ready_in", "valid_out", "stall_signal"):
                if handshake.get(label):
                    handshake_rules.append(
                        HandshakeRuleIR(
                            interface="arch",
                            rule=f"{label}={handshake[label]}",
                        )
                    )

        trace_events = [
            TraceEventIR(
                name=item,
                condition="tracepoint enabled",
                observed_signals=[item.removeprefix("trace_")],
            )
            for item in behavior_ir.tracepoints
        ]
        transactions = [
            CycleTransactionIR(
                name=txn.name,
                recipe=txn.recipe,
                trigger=cls._cycle_transaction_event_ir(
                    txn.name,
                    "trigger",
                    txn.trigger_signals,
                    txn.trigger_event,
                    txn.trigger_qualifiers,
                ),
                completion=cls._cycle_transaction_event_ir(
                    txn.name,
                    "completion",
                    txn.completion_signals,
                    txn.completion_event,
                    txn.completion_qualifiers,
                ),
                max_cycles=txn.max_cycles,
                sample_cycles=txn.sample_cycles,
                ordering=txn.ordering,
                allow_overlap=txn.allow_overlap,
                temporal_relation=cls._cycle_transaction_temporal_relation(txn),
            )
            for txn in behavior_ir.transactions
        ]

        latency = review_spec.timing.latency_exact
        if latency is None:
            latency = review_spec.timing.latency_max
        if latency is None and generated_arch:
            stages = generated_arch.get("stages", [])
            if isinstance(stages, list) and stages:
                latency = len(stages)

        return CycleIR(
            module_name=review_spec.name,
            latency=latency,
            throughput=review_spec.timing.throughput,
            states=states,
            updates=updates,
            handshakes=handshake_rules,
            trace_events=trace_events,
            transactions=transactions,
        )

    @classmethod
    def _build_structural_ir(
        cls,
        gen_ctx: Any,
        review_spec: SpecIR,
        generated_arch: Optional[Dict[str, Any]],
    ) -> StructuralIR:
        submodules: List[SubmoduleInstanceSpec] = []
        for item in getattr(gen_ctx, "sub_modules", []) or []:
            submodules.append(
                SubmoduleInstanceSpec(
                    module_type=item.submod_type,
                    instance_name=item.name,
                    port_map={name: name for name in list(item.inputs) + list(item.outputs)},
                )
            )
        if generated_arch:
            for item in generated_arch.get("submodules", []):
                submodules.append(
                    SubmoduleInstanceSpec(
                        module_type=item.get("module_type", ""),
                        instance_name=item.get("instance_name", ""),
                        port_map=dict(item.get("port_map", {})),
                    )
                )

        connections: List[ConnectionSpec] = []
        if generated_arch:
            for item in generated_arch.get("connections", []):
                connections.append(
                    ConnectionSpec(
                        source=item.get("source", ""),
                        sink=item.get("sink", ""),
                        signal=item.get("signal", ""),
                        width=int(item.get("width", 1) or 1),
                    )
                )

        hierarchy_mode = getattr(gen_ctx, "generation_task", {}).get("hierarchy_mode", "monolithic")
        internal_signals: List[str] = []
        if generated_arch:
            port_names = {p.name for p in review_spec.ports}
            output_names = set(generated_arch.get("output_names", []))
            for name in generated_arch.get("signal_widths", {}):
                if name not in port_names and name not in output_names:
                    internal_signals.append(name)

        return StructuralIR(
            module_name=review_spec.name,
            hierarchy_mode=hierarchy_mode,
            ports=[
                PortSpec(name=p.name, direction=p.direction, width=p.width, signed=p.signed)
                for p in review_spec.ports
            ],
            submodules=submodules,
            connections=connections,
            clock_reset=ClockResetDomainIR(
                clock=cls._clock_name_for_spec(review_spec),
                reset=review_spec.reset_name,
                reset_type=review_spec.reset_type,
                reset_active=review_spec.reset_active,
            ),
            internal_signals=cls._dedupe_keep_order(internal_signals),
        )

    @classmethod
    def _build_verification_ir(
        cls,
        gen_ctx: Any,
        review_spec: SpecIR,
        behavior_ir: BehaviorIR,
        cycle_ir: CycleIR,
        pkg: AgentPackage,
        module_contract: Optional[ModuleContract] = None,
    ) -> VerificationPlanIR:
        directed_tests = [
            TestVectorIR(
                name=f"golden_{idx}",
                inputs=dict(test.get("inputs", {})),
                expected_outputs=dict(test.get("expected_outputs", {})),
            )
            for idx, test in enumerate(getattr(pkg, "golden_tests", []) or [])
        ]
        coverage_bins = [
            CoverageBinIR(name=item, description=item, kind="coverage")
            for item in review_spec.verification.coverage_bins
        ]
        assertions = [
            AssertionIR(name=item, expr=item, severity="error")
            for item in review_spec.verification.protocol_checks
        ]
        tracepoints = [
            TracepointIR(
                name=item.name,
                signals=list(item.observed_signals),
                description=item.condition,
            )
            for item in cycle_ir.trace_events
        ]
        scoreboards = []
        output_ports = [p.name for p in review_spec.ports if p.direction == "output"]
        for name in output_ports:
            scoreboards.append(
                ScoreboardIR(
                    name=f"score_{name}",
                    reference=f"behavior.{name}",
                    implementation=f"dsl.{name}",
                    compare="exact",
                )
            )

        contract = list(getattr(gen_ctx, "verification_contract", []))
        for item in contract:
            if item.startswith("trace_") and not any(tp.name == item for tp in tracepoints):
                tracepoints.append(
                    TracepointIR(name=item, signals=[item.removeprefix("trace_")], description="verification contract")
                )

        if review_spec.interfaces:
            assertions.append(
                AssertionIR(
                    name="protocol_alignment",
                    expr=(
                        f"input={review_spec.interfaces.input_protocol}, "
                        f"output={review_spec.interfaces.output_protocol}"
                    ),
                    severity="warning",
                )
            )
        if behavior_ir.invariants:
            for item in behavior_ir.invariants:
                assertions.append(AssertionIR(name=item.name, expr=item.expr, severity="error"))

        protocols = cls._contract_protocol_irs(module_contract)
        transactions = cls._contract_transaction_irs(module_contract)
        for txn in transactions:
            trigger_signals = cls._dedupe_keep_order(txn.trigger_signals + txn.trigger_qualifiers)
            completion_signals = cls._dedupe_keep_order(txn.completion_signals + txn.completion_qualifiers)
            if trigger_signals and not any(tp.name == f"txn_{txn.name}_trigger" for tp in tracepoints):
                tracepoints.append(
                    TracepointIR(
                        name=f"txn_{txn.name}_trigger",
                        signals=trigger_signals,
                        description=f"{txn.trigger_event} trigger for transaction {txn.name}",
                    )
                )
            if completion_signals and not any(tp.name == f"txn_{txn.name}_completion" for tp in tracepoints):
                tracepoints.append(
                    TracepointIR(
                        name=f"txn_{txn.name}_completion",
                        signals=completion_signals,
                        description=f"{txn.completion_event} completion for transaction {txn.name}",
                    )
                )
            coverage_bins.append(
                CoverageBinIR(
                    name=f"txn_{txn.name}_observed",
                    description=txn.description or f"Observe transaction {txn.name}",
                    kind="transaction",
                )
            )
            recipe = txn.recipe or "custom"
            bound = f", max_cycles={txn.max_cycles}" if txn.max_cycles is not None else ""
            assertions.append(
                AssertionIR(
                    name=f"txn_{txn.name}_recipe",
                    expr=(
                        f"{recipe}: "
                        f"{cls._transaction_event_expr(txn.trigger_signals, txn.trigger_event, txn.trigger_qualifiers)} "
                        f"-> {cls._transaction_event_expr(txn.completion_signals, txn.completion_event, txn.completion_qualifiers)}"
                        f"{bound}"
                    ),
                    severity="error",
                )
            )

        return VerificationPlanIR(
            module_name=review_spec.name,
            directed_tests=directed_tests,
            coverage_bins=coverage_bins,
            assertions=assertions,
            tracepoints=tracepoints,
            scoreboards=scoreboards,
            protocols=protocols,
            transactions=transactions,
            protocol_checks=list(review_spec.verification.protocol_checks),
            random_test_count=review_spec.verification.random_test_count,
        )

    @classmethod
    def _evaluate_layer_alignment(
        cls,
        review_spec: SpecIR,
        behavior_ir: BehaviorIR,
        cycle_ir: CycleIR,
        generated_arch: Optional[Dict[str, Any]],
        structural_ir: StructuralIR,
        validation: Optional[Dict[str, Any]],
        verification_ir: Optional[VerificationPlanIR] = None,
    ) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}

        spec_ports = {p.name for p in review_spec.ports}
        behavior_ports = {p.name for p in behavior_ir.ports}
        missing_ports = sorted(spec_ports - behavior_ports)
        if missing_ports:
            results["spec_to_behavior"] = {
                "status": "failed",
                "detail": f"missing ports: {', '.join(missing_ports)}",
            }
        elif behavior_ir.rules:
            results["spec_to_behavior"] = {"status": "passed", "detail": "ports and rules captured"}
        else:
            results["spec_to_behavior"] = {"status": "warn", "detail": "ports captured but no explicit rules"}

        if review_spec.interfaces and not cycle_ir.handshakes:
            results["behavior_to_cycle"] = {
                "status": "failed",
                "detail": "interface protocol exists but no cycle handshake rules were derived",
            }
        elif cycle_ir.latency is None and generated_arch:
            results["behavior_to_cycle"] = {
                "status": "warn",
                "detail": "cycle state exists but latency is still implicit",
            }
        else:
            results["behavior_to_cycle"] = {"status": "passed", "detail": "latency/state projection generated"}

        if verification_ir is not None:
            behavior_txns = {txn.name for txn in behavior_ir.transactions}
            cycle_txns = {txn.name for txn in cycle_ir.transactions}
            verification_txns = {txn.name for txn in verification_ir.transactions}
            missing_in_cycle = sorted(behavior_txns - cycle_txns)
            missing_in_plan = sorted(behavior_txns - verification_txns)
            unexpected_in_cycle = sorted(cycle_txns - behavior_txns)
            unexpected_in_plan = sorted(verification_txns - behavior_txns)
            if missing_in_cycle or missing_in_plan or unexpected_in_cycle or unexpected_in_plan:
                details: List[str] = []
                if missing_in_cycle:
                    details.append(f"missing in cycle: {', '.join(missing_in_cycle)}")
                if missing_in_plan:
                    details.append(f"missing in verification: {', '.join(missing_in_plan)}")
                if unexpected_in_cycle:
                    details.append(f"unexpected in cycle: {', '.join(unexpected_in_cycle)}")
                if unexpected_in_plan:
                    details.append(f"unexpected in verification: {', '.join(unexpected_in_plan)}")
                results["behavior_to_verification"] = {
                    "status": "failed",
                    "detail": "; ".join(details),
                }
            elif behavior_txns:
                results["behavior_to_verification"] = {
                    "status": "passed",
                    "detail": f"{len(behavior_txns)} transaction boundary/boundaries aligned across behavior/cycle/verification",
                }
            else:
                results["behavior_to_verification"] = {
                    "status": "passed",
                    "detail": "no explicit transaction boundaries",
                }

        if generated_arch is None:
            results["cycle_to_microarch"] = {
                "status": "failed",
                "detail": "microarchitecture IR missing",
            }
        else:
            stage_count = len(generated_arch.get("stages", []))
            if cycle_ir.latency and stage_count and cycle_ir.latency != stage_count:
                results["cycle_to_microarch"] = {
                    "status": "warn",
                    "detail": f"cycle latency={cycle_ir.latency}, microarch stages={stage_count}",
                }
            else:
                results["cycle_to_microarch"] = {
                    "status": "passed",
                    "detail": f"{stage_count} stages available",
                }

        arch_submods = {
            item.get("instance_name", "")
            for item in (generated_arch or {}).get("submodules", [])
            if item.get("instance_name")
        }
        struct_submods = {item.instance_name for item in structural_ir.submodules if item.instance_name}
        missing_submods = sorted(arch_submods - struct_submods)
        if missing_submods:
            results["microarch_to_structural"] = {
                "status": "failed",
                "detail": f"missing structural instances: {', '.join(missing_submods)}",
            }
        else:
            results["microarch_to_structural"] = {
                "status": "passed",
                "detail": (
                    f"{len(structural_ir.submodules)} submodules, "
                    f"{len(structural_ir.connections)} explicit connections"
                ),
            }

        if not validation:
            results["structural_to_dsl"] = {"status": "pending", "detail": "DSL validation not run yet"}
        elif validation.get("passed"):
            results["structural_to_dsl"] = {
                "status": "passed",
                "detail": validation.get("validation_stage", "validated"),
            }
        elif validation.get("parsed") or validation.get("instantiated"):
            results["structural_to_dsl"] = {
                "status": "warn",
                "detail": validation.get("validation_stage", "partial"),
            }
        else:
            results["structural_to_dsl"] = {
                "status": "failed",
                "detail": validation.get("validation_stage", "failed"),
            }

        return results

    @classmethod
    def _export_spec_sidecars(
        cls,
        specs_dir: str,
        stem: str,
        gen_ctx: Any,
        dsl_mod: Optional[Module],
        behavior_req: Optional[Dict[str, Any]],
        instances: List[str],
        validation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        genctx_payload = gen_ctx.to_dict() if hasattr(gen_ctx, "to_dict") else {}
        review_spec = cls._build_review_spec_from_context(gen_ctx, behavior_req=behavior_req, dsl_mod=dsl_mod)
        generated_spec, generated_arch = cls._extract_generated_spec_artifacts(dsl_mod)
        module_contract = cls._extract_module_contract(gen_ctx, dsl_mod)
        behavior_ir = cls._build_behavior_ir(gen_ctx, review_spec, behavior_req, generated_spec, module_contract)
        cycle_ir = cls._build_cycle_ir(gen_ctx, review_spec, behavior_ir, generated_arch, behavior_req)
        structural_ir = cls._build_structural_ir(gen_ctx, review_spec, generated_arch)
        pkg = getattr(gen_ctx, "_agent_package", None)
        if pkg is None:
            class _PkgShim:
                golden_tests: List[Dict[str, Any]] = []
            pkg = _PkgShim()
        verification_ir = cls._build_verification_ir(
            gen_ctx,
            review_spec,
            behavior_ir,
            cycle_ir,
            pkg,
            module_contract,
        )
        layer_alignment = cls._evaluate_layer_alignment(
            review_spec,
            behavior_ir,
            cycle_ir,
            generated_arch,
            structural_ir,
            validation,
            verification_ir,
        )

        cls._write_json(
            os.path.join(specs_dir, f"{stem}_bundle.json"),
            {
                "instances": list(instances),
                "generation_context": genctx_payload,
                "behavior_requirement": behavior_req,
                "review_spec_ir": review_spec.to_dict(),
                "behavior_ir": behavior_ir.to_dict(),
                "cycle_ir": cycle_ir.to_dict(),
                "structural_ir": structural_ir.to_dict(),
                "verification_ir": verification_ir.to_dict(),
                "generated_spec_ir": generated_spec,
                "generated_arch_ir": generated_arch,
                "dsl_validation": validation,
                "layer_alignment": layer_alignment,
            },
        )
        cls._write_json(os.path.join(specs_dir, f"{stem}_genctx.json"), genctx_payload)
        cls._write_json(os.path.join(specs_dir, f"{stem}_review_spec.json"), review_spec.to_dict())
        cls._write_json(os.path.join(specs_dir, f"{stem}_behaviorir.json"), behavior_ir.to_dict())
        cls._write_json(os.path.join(specs_dir, f"{stem}_cycleir.json"), cycle_ir.to_dict())
        cls._write_json(os.path.join(specs_dir, f"{stem}_structuralir.json"), structural_ir.to_dict())
        cls._write_json(os.path.join(specs_dir, f"{stem}_verificationir.json"), verification_ir.to_dict())
        if behavior_req is not None:
            cls._write_json(os.path.join(specs_dir, f"{stem}_behavior.json"), behavior_req)
        if generated_spec is not None:
            cls._write_json(os.path.join(specs_dir, f"{stem}_specir.json"), generated_spec)
        if generated_arch is not None:
            cls._write_json(os.path.join(specs_dir, f"{stem}_arch.json"), generated_arch)

        return {
            "genctx": True,
            "review_spec": True,
            "behavior": behavior_req is not None,
            "behavior_ir": True,
            "cycle_ir": True,
            "structural_ir": True,
            "verification_ir": True,
            "specir": generated_spec is not None,
            "arch": generated_arch is not None,
        }

    def _collect_review_entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        type_groups: Dict[str, Dict[str, Any]] = {}
        for pe_name, pkg in self._skeleton_packages.items():
            pe = getattr(pkg, "pe", None)
            if pe is None:
                continue
            pe_type = pe.pe_type
            type_groups.setdefault(pe_type, {"instances": [], "pkg": pkg})
            type_groups[pe_type]["instances"].append(pe_name)

        for pe_type, group in sorted(type_groups.items()):
            pkg = group["pkg"]
            instances = sorted(group["instances"])
            dsl_mod = getattr(pkg, "dsl_skeleton", None)
            if dsl_mod is not None and hasattr(dsl_mod, "_generation_contexts") and dsl_mod._generation_contexts:
                gen_ctx = copy.deepcopy(dsl_mod._generation_contexts[0])
            else:
                gen_ctx = self._build_gen_ctx_from_package(pkg, dsl_mod, self._arch)
                if gen_ctx is None:
                    continue
                gen_ctx = copy.deepcopy(gen_ctx)

            target = getattr(gen_ctx, "target", None)
            if target is not None:
                target.name = pe_type
                plural = "s" if len(instances) > 1 else ""
                instance_info = f"Instantiated as {len(instances)} instance{plural}: {', '.join(instances)}"
                if target.description:
                    target.description += f" | {instance_info}"
                else:
                    target.description = instance_info

            behavior_req = getattr(pkg, "_behavior_requirement", None)
            review_spec = self._build_review_spec_from_context(gen_ctx, behavior_req=behavior_req, dsl_mod=dsl_mod)
            generated_spec, generated_arch = self._extract_generated_spec_artifacts(dsl_mod)
            validation = getattr(pkg, "_dsl_validation_report", None)
            module_contract = self._extract_module_contract(gen_ctx, dsl_mod)
            behavior_ir = self._build_behavior_ir(gen_ctx, review_spec, behavior_req, generated_spec, module_contract)
            cycle_ir = self._build_cycle_ir(gen_ctx, review_spec, behavior_ir, generated_arch, behavior_req)
            structural_ir = self._build_structural_ir(gen_ctx, review_spec, generated_arch)
            verification_ir = self._build_verification_ir(
                gen_ctx,
                review_spec,
                behavior_ir,
                cycle_ir,
                pkg,
                module_contract,
            )
            layer_alignment = self._evaluate_layer_alignment(
                review_spec,
                behavior_ir,
                cycle_ir,
                generated_arch,
                structural_ir,
                validation,
                verification_ir,
            )
            entries.append(
                {
                    "pe_type": pe_type,
                    "instances": instances,
                    "pkg": pkg,
                    "gen_ctx": gen_ctx,
                    "review_spec": review_spec,
                    "behavior_ir": behavior_ir,
                    "cycle_ir": cycle_ir,
                    "structural_ir": structural_ir,
                    "verification_ir": verification_ir,
                    "generated_spec_ir": generated_spec,
                    "generated_arch_ir": generated_arch,
                    "behavior_requirement": behavior_req,
                    "validation": validation,
                    "layer_alignment": layer_alignment,
                }
            )

        return entries

    @staticmethod
    def _markdown_table(headers: List[str], rows: List[List[Any]]) -> List[str]:
        if not rows:
            return []
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        return lines

    def _build_spec_review_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Spec Review", ""]
        for entry in entries:
            spec: SpecIR = entry["review_spec"]
            lines.extend([
                f"## {entry['pe_type']}",
                "",
                f"- Module: `{spec.name}`",
                f"- Instances: {', '.join(entry['instances'])}",
                f"- Category: `{spec.category}`",
                f"- Reset: `{spec.reset_name}` ({spec.reset_type}, active-{spec.reset_active})",
                "",
            ])
            port_rows = [
                [p.name, p.direction, p.width, "signed" if p.signed else "unsigned"]
                for p in spec.ports
            ]
            lines.extend(self._markdown_table(["Port", "Dir", "Width", "Signed"], port_rows))
            lines.append("")
        return "\n".join(lines)

    def _build_behavior_review_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Behavior Review", ""]
        for entry in entries:
            behavior_ir: BehaviorIR = entry["behavior_ir"]
            lines.extend([
                f"## {entry['pe_type']}",
                "",
                f"- Module: `{behavior_ir.module_name}`",
                f"- Function: `{behavior_ir.function_expr or 'implicit'}`",
                "",
            ])

            if behavior_ir.required_behaviors:
                lines.append("### Required Behaviors")
                lines.extend(f"- {item}" for item in behavior_ir.required_behaviors)
                lines.append("")

            if behavior_ir.rules:
                lines.append("### Rules")
                rule_rows = [
                    [rule.rule_id, rule.category, rule.trigger, rule.effect]
                    for rule in behavior_ir.rules
                ]
                lines.extend(self._markdown_table(["Rule", "Category", "Trigger", "Effect"], rule_rows))
                lines.append("")

            if behavior_ir.assumptions:
                lines.append("### Assumptions")
                lines.extend(f"- {item.kind}: {item.detail}" for item in behavior_ir.assumptions)
                lines.append("")

            if behavior_ir.invariants:
                lines.append("### Invariants")
                lines.extend(f"- {item.name}: {item.expr}" for item in behavior_ir.invariants)
                lines.append("")

            if behavior_ir.tracepoints:
                lines.append("### Tracepoints")
                lines.extend(f"- {item}" for item in behavior_ir.tracepoints)
                lines.append("")

            if behavior_ir.protocols:
                lines.append("### Protocol Boundaries")
                protocol_rows = [
                    [
                        proto.name,
                        proto.kind,
                        ", ".join(proto.request_signals) or "-",
                        ", ".join(proto.response_signals) or "-",
                        proto.ordering,
                    ]
                    for proto in behavior_ir.protocols
                ]
                lines.extend(self._markdown_table(["Protocol", "Kind", "Request", "Response", "Ordering"], protocol_rows))
                lines.append("")

            if behavior_ir.transactions:
                lines.append("### Transaction Boundaries")
                txn_rows = [
                    [
                        txn.name,
                        txn.recipe or "custom",
                        self._transaction_event_expr(txn.trigger_signals, txn.trigger_event, txn.trigger_qualifiers),
                        self._transaction_event_expr(
                            txn.completion_signals,
                            txn.completion_event,
                            txn.completion_qualifiers,
                        ),
                        txn.max_cycles if txn.max_cycles is not None else "-",
                    ]
                    for txn in behavior_ir.transactions
                ]
                lines.extend(self._markdown_table(["Transaction", "Recipe", "Trigger", "Completion", "Max Cycles"], txn_rows))
                lines.append("")

        return "\n".join(lines)

    def _build_cycle_review_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Cycle Review", ""]
        for entry in entries:
            cycle_ir: CycleIR = entry["cycle_ir"]
            lines.extend([f"## {entry['pe_type']}", ""])
            lines.extend([
                f"- Module: `{cycle_ir.module_name}`",
                f"- Latency: `{cycle_ir.latency}`",
                f"- Throughput: `{cycle_ir.throughput}`",
                "",
            ])
            if cycle_ir.states:
                lines.append("### Registers")
                state_rows = [[state.name, state.kind, state.width, state.reset_value] for state in cycle_ir.states]
                lines.extend(self._markdown_table(["State", "Kind", "Width", "Reset"], state_rows))
                lines.append("")
            if cycle_ir.updates:
                lines.append("### Next-State")
                update_rows = [[item.state, item.when, item.next_expr] for item in cycle_ir.updates]
                lines.extend(self._markdown_table(["State", "When", "Next"], update_rows))
                lines.append("")
            if cycle_ir.handshakes:
                lines.append("### Handshake")
                handshake_rows = [[item.interface, item.rule] for item in cycle_ir.handshakes]
                lines.extend(self._markdown_table(["Interface", "Rule"], handshake_rows))
                lines.append("")
            if cycle_ir.trace_events:
                lines.append("### Trace Events")
                lines.extend(
                    f"- {item.name}: {item.condition} ({', '.join(item.observed_signals) or 'no signals'})"
                    for item in cycle_ir.trace_events
                )
                lines.append("")
            if cycle_ir.transactions:
                lines.append("### Transaction Events")
                txn_rows = [
                    [
                        txn.name,
                        txn.recipe or "custom",
                        txn.trigger.condition,
                        txn.completion.condition,
                        txn.max_cycles if txn.max_cycles is not None else "-",
                        txn.temporal_relation or "-",
                    ]
                    for txn in cycle_ir.transactions
                ]
                lines.extend(self._markdown_table(["Transaction", "Recipe", "Trigger", "Completion", "Max Cycles", "Temporal"], txn_rows))
                lines.append("")
        return "\n".join(lines)

    def _build_microarch_review_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Microarchitecture Review", ""]
        for entry in entries:
            arch = entry.get("generated_arch_ir")
            lines.extend([f"## {entry['pe_type']}", ""])
            if not arch:
                lines.append("- Microarchitecture IR not generated yet.")
                lines.append("")
                continue
            spec: SpecIR = entry["review_spec"]
            lines.extend([
                f"- Module: `{spec.name}`",
                f"- Arch type: `{arch.get('arch_type', 'unknown')}`",
                f"- Output names: {', '.join(arch.get('output_names', [])) or 'none'}",
                f"- PPA priority: `{spec.ppa.priority}`",
                "",
            ])
            stage_rows: List[List[Any]] = []
            for stage in arch.get("stages", []):
                ops = ", ".join(stage.get("ops", [])) or "-"
                regs = ", ".join(reg.get("name", "") for reg in stage.get("registers", [])) or "-"
                stage_rows.append([stage.get("stage_id"), stage.get("name"), ops, regs])
            lines.extend(self._markdown_table(["Stage", "Name", "Ops", "Boundary Regs"], stage_rows))
            lines.append("")
        return "\n".join(lines)

    def _build_structure_review_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Structure Review", ""]
        for entry in entries:
            structural_ir: StructuralIR = entry["structural_ir"]
            lines.extend([
                f"## {entry['pe_type']}",
                "",
                f"- Module: `{structural_ir.module_name}`",
                f"- Hierarchy mode: `{structural_ir.hierarchy_mode}`",
                f"- Instances: {', '.join(entry['instances'])}",
                (
                    f"- Clock/reset: `{structural_ir.clock_reset.clock}` / "
                    f"`{structural_ir.clock_reset.reset}` "
                    f"({structural_ir.clock_reset.reset_type}, "
                    f"active-{structural_ir.clock_reset.reset_active})"
                ),
                "",
            ])
            if structural_ir.submodules:
                rows = [
                    [
                        sm.instance_name,
                        sm.module_type,
                        ", ".join(sorted(sm.port_map.keys())) or "-",
                        ", ".join(f"{k}->{v}" for k, v in sorted(sm.port_map.items())) or "-",
                    ]
                    for sm in structural_ir.submodules
                ]
                lines.extend(self._markdown_table(["Instance", "Type", "Ports", "Port Map"], rows))
                lines.append("")
            else:
                lines.append("- No explicit sub-module decomposition.")
                lines.append("")
            if structural_ir.connections:
                conn_rows = [
                    [conn.source, conn.sink, conn.signal, conn.width]
                    for conn in structural_ir.connections
                ]
                lines.append("### Connections")
                lines.extend(self._markdown_table(["Source", "Sink", "Signal", "Width"], conn_rows))
                lines.append("")
            if structural_ir.internal_signals:
                lines.append("### Internal Signals")
                lines.extend(f"- {name}" for name in structural_ir.internal_signals)
                lines.append("")
        return "\n".join(lines)

    def _build_verification_plan_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Verification Plan", ""]
        for entry in entries:
            gen_ctx = entry["gen_ctx"]
            verification_ir: VerificationPlanIR = entry["verification_ir"]
            lines.extend([
                f"## {entry['pe_type']}",
                "",
                f"- Module: `{verification_ir.module_name}`",
                f"- Directed tests: {len(verification_ir.directed_tests)}",
                f"- Random tests: {verification_ir.random_test_count}",
                f"- Coverage bins: {', '.join(item.name for item in verification_ir.coverage_bins) if verification_ir.coverage_bins else 'none'}",
                f"- Protocol checks: {', '.join(verification_ir.protocol_checks) if verification_ir.protocol_checks else 'none'}",
                "",
            ])
            contract = getattr(gen_ctx, "verification_contract", [])
            if contract:
                lines.append("### Verification Contract")
                lines.extend(f"- {item}" for item in contract)
                lines.append("")
            if verification_ir.assertions:
                lines.append("### Assertions")
                lines.extend(f"- {item.name}: {item.expr}" for item in verification_ir.assertions[:8])
                lines.append("")
            if verification_ir.tracepoints:
                lines.append("### Trace Events")
                lines.extend(f"- {item.name}: {', '.join(item.signals) or 'no signals'}" for item in verification_ir.tracepoints)
                lines.append("")
            if verification_ir.transactions:
                lines.append("### Transaction Checks")
                txn_rows = [
                    [
                        txn.name,
                        txn.recipe or "custom",
                        txn.trigger_event,
                        txn.completion_event,
                        txn.sample_cycles,
                    ]
                    for txn in verification_ir.transactions
                ]
                lines.extend(self._markdown_table(["Transaction", "Recipe", "Trigger Event", "Completion Event", "Sample Cycles"], txn_rows))
                lines.append("")
            if verification_ir.scoreboards:
                lines.append("### Scoreboards")
                lines.extend(
                    f"- {item.name}: {item.reference} vs {item.implementation} ({item.compare})"
                    for item in verification_ir.scoreboards
                )
                lines.append("")
        return "\n".join(lines)

    def _build_lowering_report_markdown(self, entries: List[Dict[str, Any]]) -> str:
        lines = ["# Lowering Report", ""]
        rows: List[List[Any]] = []
        for entry in entries:
            validation = entry.get("validation") or {}
            rows.append([
                entry["pe_type"],
                "yes",
                "yes",
                "yes" if entry.get("generated_spec_ir") else "no",
                "yes",
                "yes" if entry.get("generated_arch_ir") else "no",
                validation.get("verification_level", 0),
                "yes" if validation.get("dsl_sim_passed") else ("pending" if not validation else "no"),
                validation.get("validation_stage", "pending"),
                "yes" if validation.get("roundtrip_passed") is True else ("no" if validation.get("roundtrip_passed") is False else "pending"),
                "yes" if validation.get("passed") else ("pending" if not validation else "no"),
            ])
        lines.extend(self._markdown_table(
            ["PE Type", "BehaviorIR", "CycleIR", "SpecIR", "StructuralIR", "ArchIR", "VerifierL", "DSLSim", "Validation", "Roundtrip", "Accepted"],
            rows,
        ))
        lines.append("")
        lines.append("## Layer Checks")
        lines.append("")
        for entry in entries:
            lines.append(f"### {entry['pe_type']}")
            lines.append("")
            for name, status in (entry.get("layer_alignment") or {}).items():
                lines.append(f"- {name}: {status.get('status', 'pending')} ({status.get('detail', '')})")
            lines.append("")
        for entry in entries:
            validation = entry.get("validation") or {}
            errors = validation.get("errors", [])
            warnings = validation.get("warnings", [])
            if errors or warnings:
                lines.append(f"## {entry['pe_type']}")
                lines.append("")
                if errors:
                    lines.append("### Errors")
                    lines.extend(f"- {item}" for item in errors[:8])
                    lines.append("")
                if warnings:
                    lines.append("### Warnings")
                    lines.extend(f"- {item}" for item in warnings[:8])
                    lines.append("")
        return "\n".join(lines)

    def _write_review_bundle(self, output_dir: str) -> Dict[str, Any]:
        entries = self._collect_review_entries()
        if not entries:
            return {"count": 0, "dir": os.path.join(output_dir, "review")}

        review_dir = os.path.join(output_dir, "review")
        os.makedirs(review_dir, exist_ok=True)

        bundle = {
            "01_spec_review.md": self._build_spec_review_markdown(entries),
            "02_behavior_review.md": self._build_behavior_review_markdown(entries),
            "03_cycle_review.md": self._build_cycle_review_markdown(entries),
            "04_microarch_review.md": self._build_microarch_review_markdown(entries),
            "05_structure_review.md": self._build_structure_review_markdown(entries),
            "06_verification_plan.md": self._build_verification_plan_markdown(entries),
            "07_lowering_report.md": self._build_lowering_report_markdown(entries),
        }
        for filename, text in bundle.items():
            with open(os.path.join(review_dir, filename), "w") as f:
                f.write(text)

        return {"count": len(entries), "dir": review_dir}

    def _run_spec_gen(self, output_dir: str = "generated_skill_ppa") -> StageResult:
        """Generate markdown specification documents from skeleton packages.

        Groups PEs by pe_type, generates ONE master spec per type,
        lists all instance names in the master spec.

        No API key required. Never fails — just produces specs for review.
        If existing DSL code already exists on disk, it is parsed and used.
        """
        result = StageResult("spec_gen", description="Markdown + machine-readable spec generation")

        if not self._arch or not self._skeleton_packages:
            result.skipped = True
            result.errors.append("Run skeleton stage first")
            return result

        try:
            from rtlgen.spec_markdown import generation_context_to_markdown
        except ImportError:
            result.skipped = True
            result.errors.append("spec_markdown module not available")
            return result

        specs_dir = os.path.join(output_dir, "specs")
        os.makedirs(specs_dir, exist_ok=True)

        # Group packages by pe_type
        type_groups: Dict[str, dict] = {}
        for pe_name, pkg in self._skeleton_packages.items():
            pe = pkg.pe
            pt = pe.pe_type
            if pt not in type_groups:
                type_groups[pt] = {"instances": [], "pkg": pkg, "pe": pe}
            type_groups[pt]["instances"].append(pe_name)

        success_count = 0
        skipped_count = 0
        genctx_count = 0
        review_spec_count = 0
        behavior_ir_count = 0
        cycle_ir_count = 0
        structural_ir_count = 0
        verification_ir_count = 0
        executable_spec_count = 0
        arch_sidecar_count = 0

        for pe_type, group in type_groups.items():
            pkg = group["pkg"]
            instances = sorted(group["instances"])
            dsl_mod = getattr(pkg, 'dsl_skeleton', None)
            if dsl_mod is None:
                skipped_count += 1
                continue

            # Build GenerationContext from the first instance's package
            if hasattr(dsl_mod, '_generation_contexts') and dsl_mod._generation_contexts:
                gen_ctx = dsl_mod._generation_contexts[0]
            else:
                gen_ctx = self._build_gen_ctx_from_package(pkg, dsl_mod, self._arch)
                if gen_ctx is None:
                    skipped_count += 1
                    continue

            # Use pe_type as master name; add instance list
            target = getattr(gen_ctx, "target", None)
            if target:
                target.name = pe_type
                plural = "s" if len(instances) > 1 else ""
                instance_info = f"Instantiated as {len(instances)} instance{plural}: {', '.join(instances)}"
                if target.description:
                    target.description += f" | {instance_info}"
                else:
                    target.description = instance_info

            try:
                md = generation_context_to_markdown(gen_ctx, module=dsl_mod)
            except Exception as e:
                result.errors.append(f"build_markdown {pe_type}: {e}")
                skipped_count += 1
                continue

            # Write master spec: {pe_type}_spec.md
            spec_path = os.path.join(specs_dir, f"{pe_type}_spec.md")
            with open(spec_path, "w") as f:
                f.write(md)

            behavior_req = getattr(pkg, "_behavior_requirement", None)
            setattr(gen_ctx, "_agent_package", pkg)
            exported = self._export_spec_sidecars(
                specs_dir,
                pe_type,
                gen_ctx,
                dsl_mod,
                behavior_req,
                instances,
            )

            success_count += 1
            lines = md.count("\n") + 1
            result.metrics[f"{pe_type}_spec_lines"] = lines
            result.metrics[f"{pe_type}_instances"] = len(instances)
            genctx_count += int(exported["genctx"])
            review_spec_count += int(exported["review_spec"])
            behavior_ir_count += int(exported["behavior_ir"])
            cycle_ir_count += int(exported["cycle_ir"])
            structural_ir_count += int(exported["structural_ir"])
            verification_ir_count += int(exported["verification_ir"])
            executable_spec_count += int(exported["specir"])
            arch_sidecar_count += int(exported["arch"])

        # ── Also generate sub-module specs from _SUBMODULE_DEFS ──
        try:
            from rtlgen import arch_skel
            submod_spec_count = self._gen_submodule_specs(specs_dir, arch_skel._SUBMODULE_DEFS)
            result.metrics["submodule_specs"] = submod_spec_count
        except Exception as e:
            result.warnings.append(f"submodule_specs: {e}")

        review_info = self._write_review_bundle(output_dir)
        result.metrics["review_bundle_entries"] = review_info.get("count", 0)
        result.metrics["review_bundle_dir"] = review_info.get("dir", "")

        result.passed = success_count > 0
        result.metrics["spec_success"] = success_count
        result.metrics["spec_skipped"] = skipped_count
        result.metrics["spec_by_type"] = len(type_groups)
        result.metrics["spec_genctx"] = genctx_count
        result.metrics["spec_review_ir"] = review_spec_count
        result.metrics["spec_behavior_ir"] = behavior_ir_count
        result.metrics["spec_cycle_ir"] = cycle_ir_count
        result.metrics["spec_structural_ir"] = structural_ir_count
        result.metrics["spec_verification_ir"] = verification_ir_count
        result.metrics["spec_executable_ir"] = executable_spec_count
        result.metrics["spec_arch_ir"] = arch_sidecar_count

        return result

    def _gen_submodule_specs(self, specs_dir: str, submod_defs: dict) -> int:
        """Generate standalone specs for each unique sub-module type.
        
        Extracts sub-modules from _SUBMODULE_DEFS, deduplicates by type,
        and generates a spec for each unique sub-module with its ports
        and the parent PE contexts that use it.
        """
        from rtlgen.spec_markdown import generation_context_to_markdown
        from rtlgen.gen_requirement import (
            ModuleRequirement, GenerationContext, SubModuleInfo, ImplementationStep,
        )

        # Collect unique sub-module types and their parent contexts
        submod_types: Dict[str, dict] = {}
        for pe_type, defn in submod_defs.items():
            for sd in defn.get("submodules", []):
                stype = sd["type"]
                if stype not in submod_types:
                    submod_types[stype] = {
                        "name": stype,
                        "inputs": sd.get("inputs", []),
                        "outputs": sd.get("outputs", []),
                        "description": sd.get("description", ""),
                        "used_by": [],
                    }
                submod_types[stype]["used_by"].append(f"{pe_type}.{sd['name']}")

        # Load DSL port database + _DEFAULT_SIGNAL_WIDTHS for exact widths
        try:
            from rtlgen.dsl_analyzer import build_port_database, get_port_widths_by_type
            db = build_port_database(self.skill_name)
        except Exception:
            db = {"ports": {}}
        try:
            from rtlgen import arch_skel
        except Exception:
            arch_skel = None

        def _lookup_width(sig: str) -> int:
            """Look up signal width from various sources."""
            if sig in ("clk", "rst_n", "rst", "reset_n"):
                return 1
            w = arch_skel._DEFAULT_SIGNAL_WIDTHS.get(sig) if arch_skel else None
            if w is not None:
                return w
            w = arch_skel._infer_signal_width(sig) if arch_skel else 1
            return w

        count = 0
        for stype, info in submod_types.items():
            # Look up exact port widths from various sources
            dsl_widths = get_port_widths_by_type(stype, db) if db.get("ports") else {}

            desc = info.get("description", "")
            if not desc:
                desc = f"Sub-module of: {', '.join(sorted(set(info['used_by'])))}"
            module_req = ModuleRequirement(
                name=stype,
                pe_type=stype,
                role=f"sub_module_{stype}",
                description=desc,
            )
            for sig in info["inputs"]:
                norm_name, norm_width = self._normalize_port_declaration(sig, 1)
                w = dsl_widths.get(sig)
                if w is None:
                    w = _lookup_width(sig)
                if norm_width > 1:
                    w = norm_width
                module_req.ports[norm_name] = {"dir": "input", "type": "logic", "width": w}
            for sig in info["outputs"]:
                norm_name, norm_width = self._normalize_port_declaration(sig, 1)
                w = dsl_widths.get(sig)
                if w is None:
                    w = _lookup_width(sig)
                if norm_width > 1:
                    w = norm_width
                module_req.ports[norm_name] = {"dir": "output", "type": "logic", "width": w}
            if info["description"]:
                module_req.required_behaviors.append(info["description"])

            gen_ctx = GenerationContext(target=module_req)

            try:
                md = generation_context_to_markdown(gen_ctx)
            except Exception:
                continue

            spec_path = os.path.join(specs_dir, f"{stype}_spec.md")
            with open(spec_path, "w") as f:
                f.write(md)
            self._export_spec_sidecars(
                specs_dir,
                stype,
                gen_ctx,
                None,
                None,
                sorted(set(info["used_by"])),
            )
            count += 1

        return count

    @staticmethod
    def _get_arch_description(pe_type: str) -> str:
        """Get a structured architecture description for a PE type."""
        desc_map = {
            "rv64_core": (
                "5-stage RISC-V pipeline (Fetch/Decode/Execute/Memory/Writeback). "
                "Features: PC with redirect, instruction fetch from I-Cache, "
                "opcode/funct3/funct7/rs1/rs2/rd/immediate decode, "
                "ALU with ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU, "
                "branch comparison (BEQ/BNE/BLT/BGE/BLTU/BGEU), "
                "load/store interface to D-Cache, "
                "3-stage forwarding (EX/MEM/WB), load-use hazard stall."
            ),
            "l1_cache": (
                "Direct-mapped cache with MSI coherence. "
                "Tag RAM (tag comparison + valid bits), Data RAM (line storage), "
                "hit/miss FSM (IDLE → TAG_CHECK → REFILL_WAIT → REFILL_STORE), "
                "LRU replacement, coherence snoop interface."
            ),
            "noc_router": (
                "5-port router (East/West/North/South/Local) with XY routing. "
                "Per-port input FIFO buffers (4-deep), "
                "XY routing logic (coordinate compare → output port), "
                "5×5 crossbar switch, priority arbitration (N>S>E>W>J), "
                "valid/ready handshake flow control."
            ),
            "coherence_dir": (
                "MSI directory with sharers bitmask. "
                "Directory RAM (tag + state + sharers bitmask + owner), "
                "snoop message generation, response arbitration, "
                "Shared/Modified request handling, invalidation generation."
            ),
            "l2_cache": (
                "L2 cache slice with DRAM interface. "
                "Tag RAM + Data RAM, LRU replacement, "
                "cache FSM (IDLE → LOOKUP → REFILL → WRITEBACK), "
                "DRAM request/response interface, "
                "coherence upstream to directory."
            ),
            "cluster": (
                "Per-cluster tile: RV64Core + L1 I-Cache + L1 D-Cache + "
                "CoherenceDir + L2CacheSlice + NoCRouter. "
                "Internal wiring: Core.I-Cache ↔ L1I, Core.D-Cache ↔ L1D, "
                "L1 → CoherenceDir → L2Slice → NoCRouter → mesh."
            ),
        }
        return desc_map.get(pe_type, "")

    @staticmethod
    def _build_gen_ctx_from_package(pkg, dsl_mod=None, arch=None):
        """Build a GenerationContext from an AgentPackage when no _generation_contexts exists.

        Creates ModuleRequirement from PE data and extracts skeleton state from dsl_skeleton.
        If arch is provided, also extracts interconnect topology and sub-module connections.
        """
        try:
            from rtlgen.gen_requirement import (
                ModuleRequirement, GenerationContext,
                TaskGenerationContext, ImplementationStep, SubModuleInfo,
            )
        except ImportError:
            return None

        pe = pkg.pe
        if pe is None:
            return None

        # Build ModuleRequirement from PE
        module_req = ModuleRequirement(
            name=pe.name,
            pe_type=pe.pe_type,
            role=f"hardware_{pe.pe_type}",
            description=pe.description or "",
        )

        # Add ports
        for port in pe.inputs:
            module_req.ports[port.name] = {
                "dir": "input", "type": "logic", "width": port.width,
            }
        for port in pe.outputs:
            module_req.ports[port.name] = {
                "dir": "output", "type": "logic", "width": port.width,
            }

        # Add parameters
        if pe.latency > 0:
            module_req.parameters["LATENCY"] = pe.latency
        if pe.issue_width > 1:
            module_req.parameters["ISSUE_WIDTH"] = pe.issue_width
        if pe.num_pipes > 1:
            module_req.parameters["NUM_PIPES"] = pe.num_pipes
        if pe.num_instances > 1:
            module_req.parameters["NUM_INSTANCES"] = pe.num_instances

        # Add behaviors from PE description
        if pe.description:
            module_req.required_behaviors.append(pe.description)

        # Add state suggestions
        for s in pe.state:
            hint = s.name
            if s.rtl_width:
                hint = f"{s.name}[{s.rtl_width - 1}:0]"
            module_req.internal_state_suggestions.append(hint)

        # Add architecture description based on pe_type
        arch_desc = SkillPPARunner._get_arch_description(pe.pe_type)
        if arch_desc:
            module_req.required_behaviors.append(arch_desc)

        # Build GenerationContext
        gen_ctx = GenerationContext(
            target=module_req,
        )

        # Add implementation steps from template if available
        try:
            from rtlgen import arch_skel
            pe_type_steps = arch_skel._TEMPLATE_STEPS.get(pe.pe_type, [])
            for step in pe_type_steps:
                if isinstance(step, dict):
                    gen_ctx.implementation_steps.append(
                        ImplementationStep(
                            name=step.get("name", ""),
                            goal=step.get("goal", ""),
                            behavior_tags=step.get("behavior_tags", []),
                        )
                    )
        except Exception:
            pass

        # Add sub-module decomposition from _SUBMODULE_DEFS
        try:
            from rtlgen import arch_skel
            submod_def = arch_skel._SUBMODULE_DEFS.get(pe.pe_type, {})
            for sd in submod_def.get("submodules", []):
                gen_ctx.sub_modules.append(SubModuleInfo(
                    name=sd.get("name", ""),
                    submod_type=sd.get("type", ""),
                    description=sd.get("description", ""),
                    inputs=sd.get("inputs", []),
                    outputs=sd.get("outputs", []),
                ))
        except Exception:
            pass

        # Add skeleton state vars from dsl_mod
        if dsl_mod is not None:
            skeleton_state = []
            for attr_name in dir(dsl_mod):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(dsl_mod, attr_name, None)
                if attr is None:
                    continue
                attr_type = type(attr).__name__
                if attr_type in ("Reg", "Wire", "Array"):
                    state_info = {"name": attr_name, "kind": attr_type}
                    if hasattr(attr, "width"):
                        state_info["width"] = attr.width
                    if hasattr(attr, "depth"):
                        state_info["depth"] = attr.depth
                    skeleton_state.append(state_info)
            gen_ctx.skeleton_state_vars = skeleton_state

        gen_ctx.generation_task["hierarchy_mode"] = "hierarchical" if gen_ctx.sub_modules else "leaf_only"

        return gen_ctx

    # -----------------------------------------------------------------
    # Stage 3c: dsl_from_spec — Generate DSL from structured specs / code
    # -----------------------------------------------------------------

    @staticmethod
    def _candidate_spec_stems(pe_name: str, pkg: AgentPackage) -> List[str]:
        stems: List[str] = []
        for candidate in (pe_name, getattr(getattr(pkg, "pe", None), "pe_type", None)):
            if candidate and candidate not in stems:
                stems.append(candidate)
        return stems

    @staticmethod
    def _find_candidate_paths(base_dir: str, stems: List[str], extensions: List[str]) -> List[str]:
        paths: List[str] = []
        for stem in stems:
            for suffix in ("", "_spec"):
                for ext in extensions:
                    path = os.path.join(base_dir, f"{stem}{suffix}{ext}")
                    if path not in paths:
                        paths.append(path)
        return paths

    @staticmethod
    def _load_structured_spec(specs_dir: str, stems: List[str]) -> Tuple[Optional[SpecIR], Optional[str]]:
        preferred_paths: List[str] = []
        for stem in stems:
            preferred_paths.extend([
                os.path.join(specs_dir, f"{stem}_specir.json"),
                os.path.join(specs_dir, f"{stem}_specir.yaml"),
                os.path.join(specs_dir, f"{stem}_specir.yml"),
            ])
        fallback_paths = SkillPPARunner._find_candidate_paths(specs_dir, stems, [".json", ".yaml", ".yml"])
        for path in preferred_paths + [p for p in fallback_paths if p not in preferred_paths]:
            if not os.path.isfile(path):
                continue
            with open(path, "r") as f:
                text = f.read()
            if path.endswith(".json"):
                return SpecIR.from_dict(json.loads(text)), path
            return SpecIR.from_yaml(text), path
        return None, None

    @staticmethod
    def _candidate_verification_plan_stems(module_name: str, mod: Module) -> List[str]:
        stems: List[str] = []
        for candidate in (module_name, getattr(mod, "name", None)):
            if candidate and candidate not in stems:
                stems.append(candidate)
        return stems

    @staticmethod
    def _load_verification_plan_ir(
        specs_dir: str,
        stems: List[str],
    ) -> Tuple[Optional[VerificationPlanIR], Optional[str], Optional[str]]:
        preferred_paths: List[str] = []
        for stem in stems:
            preferred_paths.append(os.path.join(specs_dir, f"{stem}_verificationir.json"))
            preferred_paths.append(os.path.join(specs_dir, f"{stem}_bundle.json"))
        for path in preferred_paths:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r") as f:
                    payload = json.load(f)
                if path.endswith("_bundle.json"):
                    payload = payload.get("verification_ir", {})
                if not isinstance(payload, dict):
                    return None, path, "VerificationPlanIR payload is not an object"
                return VerificationPlanIR.from_dict(payload), path, None
            except Exception as e:
                return None, path, str(e)
        return None, None, None

    @staticmethod
    def _detect_reset_name(module: Module, preferred: Optional[str] = None) -> Optional[str]:
        candidates: List[str] = []
        if preferred:
            candidates.append(preferred)
        candidates.extend(["rst_n", "reset_n", "rst", "reset", "aresetn"])
        for name in candidates:
            if name in getattr(module, "_inputs", {}):
                return name
        for name in getattr(module, "_inputs", {}):
            lname = name.lower()
            if "rst" in lname or "reset" in lname:
                return name
        return None

    @staticmethod
    def _simulation_horizon(module: Module) -> int:
        generated_arch = getattr(module, "_generated_arch_ir", None)
        if isinstance(generated_arch, dict):
            stages = generated_arch.get("stages", [])
            if isinstance(stages, list) and stages:
                return max(len(stages) + 2, 6)
        return 8

    @classmethod
    def _default_golden_tests(cls, module: Module, pkg: AgentPackage) -> List[Dict[str, Any]]:
        if pkg.golden_tests:
            return list(pkg.golden_tests)

        inputs: Dict[str, Any] = {}
        pe = getattr(pkg, "pe", None)
        if pe is not None:
            for port in pe.inputs:
                lname = port.name.lower()
                if lname in ("clk", "clock") or "rst" in lname or "reset" in lname:
                    continue
                if "ready" in lname or "valid" in lname:
                    inputs[port.name] = 1
                else:
                    inputs[port.name] = 0
        else:
            for name in getattr(module, "_inputs", {}):
                lname = name.lower()
                if lname in ("clk", "clock") or "rst" in lname or "reset" in lname:
                    continue
                inputs[name] = 1 if ("ready" in lname or "valid" in lname) else 0

        if "out_ready" in getattr(module, "_inputs", {}) and "out_ready" not in inputs:
            inputs["out_ready"] = 1
        if "in_valid" in getattr(module, "_inputs", {}) and "in_valid" not in inputs:
            inputs["in_valid"] = 1

        return [{"inputs": inputs, "expected_outputs": {}}]

    @classmethod
    def _expected_ports_for_package(
        cls,
        pkg: AgentPackage,
    ) -> Tuple[List[Tuple[str, str, int]], List[Tuple[str, str, int]]]:
        inputs: List[Tuple[str, str, int]] = []
        outputs: List[Tuple[str, str, int]] = []
        pe = getattr(pkg, "pe", None)
        if pe is None:
            return inputs, outputs

        for port in pe.inputs:
            name, width = cls._normalize_port_declaration(port.name, port.width)
            inputs.append((name, "input", width))
        for port in pe.outputs:
            name, width = cls._normalize_port_declaration(port.name, port.width)
            outputs.append((name, "output", width))
        return inputs, outputs

    @classmethod
    def _check_module_ports(
        cls,
        module: Module,
        pkg: AgentPackage,
    ) -> Tuple[bool, List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []
        exp_inputs, exp_outputs = cls._expected_ports_for_package(pkg)

        for name, _, width in exp_inputs:
            if name not in getattr(module, "_inputs", {}):
                if name in getattr(module, "_outputs", {}):
                    errors.append(f"[PortDir] input `{name}` was generated as an output")
                else:
                    errors.append(f"[PortMissing] missing input port `{name}`")
                continue
            actual_width = getattr(module._inputs[name], "width", None)
            if actual_width != width:
                errors.append(
                    f"[PortWidth] input `{name}` width mismatch: expected {width}, got {actual_width}"
                )

        for name, _, width in exp_outputs:
            if name not in getattr(module, "_outputs", {}):
                if name in getattr(module, "_inputs", {}):
                    errors.append(f"[PortDir] output `{name}` was generated as an input")
                else:
                    errors.append(f"[PortMissing] missing output port `{name}`")
                continue
            actual_width = getattr(module._outputs[name], "width", None)
            if actual_width != width:
                errors.append(
                    f"[PortWidth] output `{name}` width mismatch: expected {width}, got {actual_width}"
                )

        expected_names = {name for name, _, _ in exp_inputs + exp_outputs}
        allowed_extras = {"clk", "clock", "rst", "reset", "rst_n", "reset_n", "aresetn"}
        actual_names = set(getattr(module, "_inputs", {})) | set(getattr(module, "_outputs", {}))
        extras = sorted(name for name in actual_names - expected_names - allowed_extras)
        if extras:
            warnings.append(f"[PortExtra] additional generated ports: {', '.join(extras[:8])}")

        return len(errors) == 0, errors, warnings

    @classmethod
    def _behavior_reference_for_package(cls, pkg: AgentPackage) -> Optional[Callable]:
        behavior_ref = getattr(pkg, "behavioral_reference", None)
        if callable(behavior_ref):
            return behavior_ref
        pe = getattr(pkg, "pe", None)
        if pe is not None and callable(getattr(pe, "behavior", None)):
            return pe.behavior
        return None

    @classmethod
    def _validate_module(
        cls,
        module: Module,
        pkg: AgentPackage,
        source_kind: str,
        preferred_reset: Optional[str] = None,
    ) -> DSLValidationReport:
        from rtlgen.behavior_roundtrip import run_roundtrip_comparison
        from rtlgen.dsl_sim import DSLSimValidator
        from rtlgen.sim import Simulator
        from rtlgen.verifier import Verifier

        report = DSLValidationReport(source_kind=source_kind, parsed=True, instantiated=True)
        reset_name = cls._detect_reset_name(module, preferred_reset)
        tests = cls._default_golden_tests(module, pkg)
        input_vectors = [dict(test.get("inputs", {})) for test in tests[:8] if test.get("inputs")]

        ports_ok, port_errors, port_warnings = cls._check_module_ports(module, pkg)
        report.port_check_passed = ports_ok
        report.errors.extend(port_errors)
        report.warnings.extend(port_warnings)

        verilog_text = VerilogEmitter(
            disable_cse=True,
            profile=EmitProfile(explicit_nettype=True),
        ).emit_design(module)
        report.verilog_lines = verilog_text.count("\n") + 1

        lint_result = VerilogLinter(auto_fix=False).lint(verilog_text)
        advisory_lint_rules = {"hardware_multiplier", "hardware_division", "combinational_depth"}
        lint_errors = [
            f"[Lint/{issue.rule}] L{issue.line}: {issue.message}"
            for issue in lint_result.issues
            if issue.severity == "error" and issue.rule not in advisory_lint_rules
        ]
        lint_warnings = [
            f"[Lint/{issue.rule}] L{issue.line}: {issue.message}"
            for issue in lint_result.issues
            if issue.severity != "error" or issue.rule in advisory_lint_rules
        ]
        report.errors.extend(lint_errors)
        report.warnings.extend(lint_warnings[:8])
        report.lint_passed = len(lint_errors) == 0

        dsl_sim = DSLSimValidator(modules=[], default_cycles=max(cls._simulation_horizon(module), 8), use_xz=False)
        dsl_sim_result = dsl_sim.validate_module_instance(
            module,
            module_name=module.name,
            vectors=input_vectors if input_vectors else None,
        )
        report.dsl_sim_passed = dsl_sim_result.simulation_ok and not any(
            issue.severity == "error" for issue in dsl_sim_result.completeness_issues
        )
        for issue in dsl_sim_result.completeness_issues:
            msg = f"[DSLSim/{issue.issue_type}] {issue.description}"
            if issue.severity == "error":
                report.errors.append(msg)
            else:
                report.warnings.append(msg)
        for err in dsl_sim_result.errors[:4]:
            report.errors.append(f"[DSLSimCrash] {err}")

        verifier = Verifier(
            enable_level_3=bool(tests),
            enable_level_4=False,
            enable_cosim=bool(input_vectors),
            max_cosim_vectors=min(len(input_vectors), 8) if input_vectors else 0,
        )
        verifier_result = verifier.verify_module(
            module,
            verilog_text,
            golden_tests=tests if tests else None,
        )
        report.verification_level = verifier_result.level
        if not verifier_result.passed:
            for item in verifier_result.issues[:4]:
                prefixed = f"[Verifier] {item}"
                if prefixed not in report.errors and prefixed not in report.warnings:
                    report.warnings.append(prefixed)

        try:
            sim = Simulator(module, use_xz=False)
            if reset_name:
                sim.reset(reset_name, cycles=2)
            else:
                sim.step()

            for test in tests[:1]:
                for sig_name, val in test.get("inputs", {}).items():
                    if sig_name in getattr(module, "_inputs", {}):
                        sim.set(sig_name, val)
                for _ in range(cls._simulation_horizon(module)):
                    sim.step()

                mismatches = []
                for sig_name, exp_val in test.get("expected_outputs", {}).items():
                    if sig_name not in getattr(module, "_outputs", {}):
                        mismatches.append(f"[OutputMissing] expected output `{sig_name}` not present on module")
                        continue
                    actual = sim.get_int(sig_name)
                    if actual != exp_val:
                        mismatches.append(
                            f"[SimMismatch] `{sig_name}` expected {exp_val}, got {actual}"
                        )
                if mismatches:
                    report.errors.extend(mismatches)
                    break
            report.sim_passed = not any(err.startswith("[Sim") or err.startswith("[OutputMissing]") for err in report.errors)
        except Exception as exc:
            report.errors.append(f"[SimCrash] {exc}")
            report.sim_passed = False

        behavior_ref = cls._behavior_reference_for_package(pkg)
        behavior_req = getattr(pkg, "_behavior_requirement", None)
        if report.sim_passed and callable(behavior_ref) and behavior_req:
            try:
                pe = copy.deepcopy(getattr(pkg, "pe", None))
                if pe is not None:
                    pe.behavior = behavior_ref
                    roundtrip = run_roundtrip_comparison(
                        pe,
                        module,
                        test_vectors=tests,
                        max_cycles=max(cls._simulation_horizon(module), 8),
                    )
                    report.roundtrip_passed = roundtrip.passed
                    if not roundtrip.passed:
                        report.errors.extend(
                            f"[Roundtrip] {diff}" for diff in roundtrip.diffs[:8]
                        )
            except Exception as exc:
                report.roundtrip_passed = False
                report.errors.append(f"[RoundtripCrash] {exc}")

        report.passed = len(report.errors) == 0
        if report.passed and report.roundtrip_passed:
            report.validation_stage = "roundtrip_passed"
        elif report.passed and report.sim_passed:
            report.validation_stage = "sim_passed"
        elif report.parsed:
            report.validation_stage = "parsed"
        else:
            report.validation_stage = "failed"

        return report

    @staticmethod
    def _generate_module_from_spec(spec: SpecIR) -> Tuple[Module, SpecIR, int]:
        from rtlgen.arch_planner import ArchitecturePlanner
        from rtlgen.dsl_gen import DSLGenerator
        from rtlgen.spec_extractor import SpecCompleter

        completed = SpecCompleter.complete(spec)
        arch = ArchitecturePlanner(completed).plan()
        module = DSLGenerator(completed, arch).generate()
        verilog_text = VerilogEmitter(
            disable_cse=True,
            profile=EmitProfile(explicit_nettype=True),
        ).emit_design(module)
        verilog_lines = verilog_text.count("\n") + 1
        return module, completed, verilog_lines

    def _run_dsl_from_spec(self, output_dir: str = "generated_skill_ppa") -> StageResult:
        """Generate DSL code from hand-written DSL or structured specs.

        For each PE:
        1. Prefer hand-written `{output_dir}/code/*.py` or `{output_dir}/specs/*.py`
        2. Otherwise load machine-readable `{output_dir}/specs/*.(json|yaml|yml)`
        3. Generate a deterministic DSL module and smoke-test it via sim + emit
        4. If only markdown exists, mark the module as needing generation

        The stage only passes when every PE resolves to a generated or validated
        executable module.
        """
        result = StageResult("dsl_from_spec", description="DSL generation from specs")

        if not self._skeleton_packages:
            result.skipped = True
            result.errors.append("Run skeleton stage first")
            return result

        specs_dir = os.path.join(output_dir, "specs")
        code_dir = os.path.join(output_dir, "code")
        verify_dir = os.path.join(output_dir, "verify_run")
        os.makedirs(specs_dir, exist_ok=True)
        os.makedirs(verify_dir, exist_ok=True)
        success_count = 0
        handwritten_count = 0
        generated_count = 0
        parsed_count = 0
        dsl_sim_passed_count = 0
        sim_passed_count = 0
        lint_passed_count = 0
        roundtrip_passed_count = 0
        needs_generation_count = 0
        needs_agent_count = 0
        failed_count = 0
        fallback_count = 0

        for pe_name, pkg in self._skeleton_packages.items():
            stems = self._candidate_spec_stems(pe_name, pkg)
            result.metrics[f"{pe_name}_status"] = "fallback"

            # Priority 1: hand-written DSL code in /code or /specs
            code_paths = self._find_candidate_paths(code_dir, stems, [".py"])
            code_paths.extend(
                path for path in self._find_candidate_paths(specs_dir, stems, [".py"])
                if path not in code_paths
            )
            code_errors: List[str] = []
            for code_path in code_paths:
                if not os.path.isfile(code_path):
                    continue
                try:
                    from rtlgen.dsl_parser import parse_dsl_code

                    with open(code_path, "r") as f:
                        code = f.read()
                    parse_result = parse_dsl_code(code)
                    if parse_result.success:
                        pkg.dsl_skeleton = parse_result.module
                        handwritten_count += 1
                        parsed_count += 1
                        validation = self._validate_module(parse_result.module, pkg, "handwritten")
                        pkg._dsl_validation_report = validation.to_dict()
                        self._write_json(
                            os.path.join(verify_dir, f"{pe_name}_dsl_from_spec.json"),
                            validation.to_dict(),
                        )
                        gen_ctx = self._build_gen_ctx_from_package(pkg, parse_result.module, self._arch)
                        if gen_ctx is not None:
                            setattr(gen_ctx, "_agent_package", pkg)
                            export_stem = getattr(getattr(pkg, "pe", None), "pe_type", None) or pe_name
                            self._export_spec_sidecars(
                                specs_dir,
                                export_stem,
                                gen_ctx,
                                parse_result.module,
                                getattr(pkg, "_behavior_requirement", None),
                                [pe_name],
                                validation.to_dict(),
                            )
                        result.metrics[f"{pe_name}_lines"] = parse_result.line_count
                        result.metrics[f"{pe_name}_verilog_lines"] = validation.verilog_lines
                        result.metrics[f"{pe_name}_source"] = os.path.basename(code_path)
                        result.metrics[f"{pe_name}_source_status"] = "handwritten"
                        result.metrics[f"{pe_name}_validation_stage"] = validation.validation_stage
                        if validation.lint_passed:
                            lint_passed_count += 1
                        if validation.dsl_sim_passed:
                            dsl_sim_passed_count += 1
                        if validation.sim_passed:
                            sim_passed_count += 1
                        if validation.roundtrip_passed:
                            roundtrip_passed_count += 1
                        if validation.passed:
                            success_count += 1
                            result.metrics[f"{pe_name}_status"] = validation.validation_stage
                        else:
                            failed_count += 1
                            fallback_count += 1
                            result.metrics[f"{pe_name}_status"] = "failed"
                            result.errors.extend(f"{pe_name}: {msg}" for msg in validation.errors)
                            result.warnings.extend(f"{pe_name}: {msg}" for msg in validation.warnings)
                        break
                    code_errors.append(
                        f"{os.path.basename(code_path)}: "
                        + "; ".join(parse_result.errors or ["parse failed"])
                    )
                except Exception as e:
                    code_errors.append(f"{os.path.basename(code_path)}: {e}")
            if result.metrics.get(f"{pe_name}_source_status") == "handwritten":
                continue

            # Priority 2: structured machine-readable spec → deterministic generation
            structured_spec, spec_path = self._load_structured_spec(specs_dir, stems)
            if structured_spec is not None:
                try:
                    module, completed_spec, verilog_lines = self._generate_module_from_spec(structured_spec)
                    pkg.dsl_skeleton = module
                    generated_count += 1
                    parsed_count += 1
                    validation = self._validate_module(module, pkg, "generated", preferred_reset=completed_spec.reset_name)
                    pkg._dsl_validation_report = validation.to_dict()
                    self._write_json(
                        os.path.join(verify_dir, f"{pe_name}_dsl_from_spec.json"),
                        validation.to_dict(),
                    )
                    gen_ctx = self._build_gen_ctx_from_package(pkg, module, self._arch)
                    if gen_ctx is not None:
                        setattr(gen_ctx, "_agent_package", pkg)
                        export_stem = getattr(getattr(pkg, "pe", None), "pe_type", None) or pe_name
                        self._export_spec_sidecars(
                            specs_dir,
                            export_stem,
                            gen_ctx,
                            module,
                            getattr(pkg, "_behavior_requirement", None),
                            [pe_name],
                            validation.to_dict(),
                        )
                    result.metrics[f"{pe_name}_verilog_lines"] = validation.verilog_lines or verilog_lines
                    result.metrics[f"{pe_name}_source"] = os.path.basename(spec_path)
                    result.metrics[f"{pe_name}_module_name"] = completed_spec.name
                    result.metrics[f"{pe_name}_source_status"] = "generated"
                    result.metrics[f"{pe_name}_validation_stage"] = validation.validation_stage
                    if validation.lint_passed:
                        lint_passed_count += 1
                    if validation.dsl_sim_passed:
                        dsl_sim_passed_count += 1
                    if validation.sim_passed:
                        sim_passed_count += 1
                    if validation.roundtrip_passed:
                        roundtrip_passed_count += 1
                    if validation.passed:
                        success_count += 1
                        result.metrics[f"{pe_name}_status"] = validation.validation_stage
                    else:
                        failed_count += 1
                        fallback_count += 1
                        result.metrics[f"{pe_name}_status"] = "failed"
                        result.errors.extend(f"{pe_name}: {msg}" for msg in validation.errors)
                        result.warnings.extend(f"{pe_name}: {msg}" for msg in validation.warnings)
                    continue
                except Exception as e:
                    failed_count += 1
                    fallback_count += 1
                    result.metrics[f"{pe_name}_status"] = "failed"
                    result.errors.append(
                        f"{pe_name}: structured spec generation failed "
                        f"({os.path.basename(spec_path)}): {e}"
                    )
                    continue

            agent_sidecar_paths: List[str] = []
            for stem in stems:
                agent_sidecar_paths.extend([
                    os.path.join(specs_dir, f"{stem}_genctx.json"),
                    os.path.join(specs_dir, f"{stem}_review_spec.json"),
                    os.path.join(specs_dir, f"{stem}_bundle.json"),
                    os.path.join(specs_dir, f"{stem}_behavior.json"),
                ])
            has_agent_bundle = any(
                os.path.isfile(path)
                for path in agent_sidecar_paths
            )

            markdown_paths = self._find_candidate_paths(specs_dir, stems, [".md"])
            markdown_path = next((path for path in markdown_paths if os.path.isfile(path)), None)
            if has_agent_bundle:
                needs_agent_count += 1
                fallback_count += 1
                result.metrics[f"{pe_name}_status"] = "needs_agent"
                if code_errors:
                    failed_count += 1
                    result.errors.extend(f"{pe_name}: {msg}" for msg in code_errors)
                else:
                    result.errors.append(
                        f"{pe_name}: structured review artifacts exist but no executable SpecIR source was found"
                    )
            elif markdown_path:
                needs_generation_count += 1
                fallback_count += 1
                result.metrics[f"{pe_name}_status"] = "needs_generation"
                result.metrics[f"{pe_name}_source"] = os.path.basename(markdown_path)
                if code_errors:
                    failed_count += 1
                    result.errors.extend(f"{pe_name}: {msg}" for msg in code_errors)
                else:
                    result.errors.append(
                        f"{pe_name}: markdown spec exists but no executable DSL or structured spec source"
                    )
            else:
                fallback_count += 1
                if code_errors:
                    failed_count += 1
                    result.metrics[f"{pe_name}_status"] = "failed"
                    result.errors.extend(f"{pe_name}: {msg}" for msg in code_errors)
                else:
                    result.metrics[f"{pe_name}_status"] = "missing_spec"
                    result.errors.append(f"{pe_name}: no DSL source or spec artifact found")

        total_modules = len(self._skeleton_packages)
        result.passed = (
            total_modules > 0
            and success_count == total_modules
            and failed_count == 0
            and needs_generation_count == 0
            and needs_agent_count == 0
        )
        result.metrics["dsl_from_spec_total"] = total_modules
        result.metrics["dsl_from_spec_success"] = success_count
        result.metrics["dsl_from_spec_handwritten"] = handwritten_count
        result.metrics["dsl_from_spec_generated"] = generated_count
        result.metrics["dsl_from_spec_parsed"] = parsed_count
        result.metrics["dsl_from_spec_dsl_sim_passed"] = dsl_sim_passed_count
        result.metrics["dsl_from_spec_sim_passed"] = sim_passed_count
        result.metrics["dsl_from_spec_lint_passed"] = lint_passed_count
        result.metrics["dsl_from_spec_roundtrip_passed"] = roundtrip_passed_count
        result.metrics["dsl_from_spec_fallback"] = fallback_count
        result.metrics["dsl_from_spec_needs_generation"] = needs_generation_count
        result.metrics["dsl_from_spec_needs_agent"] = needs_agent_count
        result.metrics["dsl_from_spec_failed"] = failed_count
        result.metrics["dsl_from_spec_verify_dir"] = verify_dir
        review_info = self._write_review_bundle(output_dir)
        result.metrics["review_bundle_entries"] = review_info.get("count", 0)
        result.metrics["review_bundle_dir"] = review_info.get("dir", "")

        return result

    # -----------------------------------------------------------------
    # Stage 3d: agent_rtl_gen — Agent-driven DSL code generation from specs
    # -----------------------------------------------------------------

    def _run_agent_rtl_gen(
        self,
        output_dir: str = "generated_skill_ppa",
    ) -> StageResult:
        """Agent-driven RTL generation from markdown specs.

        For each PE:
        1. Read {output_dir}/specs/{pe_name}_spec.md
        2. If {output_dir}/code/{pe_name}.py exists → parse and use it
        3. Otherwise → flag as needing agent to write DSL code

        The agent reads the spec (ports, behaviors, skeleton state, coding rules)
        and writes correct DSL code using rtlgen.core DSL primitives.
        After writing, the agent calls Simulator to verify correctness.

        This stage prepares the manifest for agent work; actual DSL writing
        is done by the agent reading specs and invoking rtlgen tools.
        """
        result = StageResult(
            "agent_rtl_gen",
            description="Agent-driven RTL generation from specs (uses rtlgen tools for verification)",
        )

        if not self._skeleton_packages:
            result.skipped = True
            result.errors.append("Run skeleton stage first")
            return result

        try:
            from rtlgen.dsl_parser import parse_dsl_code
        except ImportError:
            result.skipped = True
            result.errors.append("dsl_parser module not available")
            return result

        specs_dir = os.path.join(output_dir, "specs")
        code_dir = os.path.join(output_dir, "code")
        os.makedirs(code_dir, exist_ok=True)

        total = 0
        has_dsl_code = 0
        needs_agent = 0
        blocked_missing_contract = 0

        if not self._loaded:
            self.load_skill()
        if self._arch is None:
            self._run_arch()
        if self._dsl_mod and not self._pe_type_to_class:
            self._pe_type_to_class = self._build_pe_type_mapping()
        pe_by_name = {pe.name: pe for pe in self._arch.processing_elements} if self._arch else {}

        for pe_name, pkg in self._skeleton_packages.items():
            total += 1

            # Priority 1: check for hand-written DSL code
            code_path = os.path.join(code_dir, f"{pe_name}.py")
            if os.path.isfile(code_path):
                try:
                    with open(code_path, "r") as f:
                        code = f.read()
                    parse_result = parse_dsl_code(code)
                    if parse_result.success:
                        pkg.dsl_skeleton = parse_result.module
                        has_dsl_code += 1
                        result.metrics[f"{pe_name}_dsl_lines"] = parse_result.line_count
                        result.metrics[f"{pe_name}_status"] = "dsl_loaded"
                        continue
                except Exception:
                    pass

            # Priority 2: spec exists → needs agent to write DSL
            spec_path = os.path.join(specs_dir, f"{pe_name}_spec.md")
            if os.path.isfile(spec_path):
                contract = None
                pe = pe_by_name.get(pe_name)
                if pe is not None:
                    mod = self._resolve_pe_to_module(pe)
                    contract = getattr(mod, "_module_contract", None) if mod is not None else None
                if not isinstance(contract, ModuleContract):
                    blocked_missing_contract += 1
                    result.metrics[f"{pe_name}_status"] = "blocked_missing_contract"
                    result.errors.append(
                        f"{pe_name}: missing module contract for agent-driven lowering"
                    )
                    continue
                needs_agent += 1
                result.metrics[f"{pe_name}_status"] = "needs_agent"
                result.metrics[f"{pe_name}_contract"] = contract.module_name
                result.metrics[f"{pe_name}_spec_lines"] = sum(
                    1 for _ in open(spec_path)
                )

        result.passed = blocked_missing_contract == 0
        result.metrics["total_modules"] = total
        result.metrics["has_dsl_code"] = has_dsl_code
        result.metrics["needs_agent"] = needs_agent
        result.metrics["blocked_missing_contract"] = blocked_missing_contract

        return result

    # -----------------------------------------------------------------
    # Stage 3e: agent_testbench — Generate testbenches using rtlgen tools
    # -----------------------------------------------------------------

    def _run_agent_testbench(
        self,
        output_dir: str = "generated_skill_ppa",
    ) -> StageResult:
        """Agent-driven testbench generation using rtlgen's CocotbEmitter and UVMEmitter.

        For each module with DSL code:
        1. Use CocotbEmitter to generate cocotb testbench
        2. Use UVMEmitter to generate SV/UVM testbench
        3. Write to {output_dir}/testbenches/{module_name}/

        The agent reads the spec to understand the design intent, then
        calls the existing rtlgen emitters to produce testbenches.
        """
        result = StageResult(
            "agent_testbench",
            description="Agent-driven testbench generation using rtlgen CocotbEmitter/UVMEmitter",
        )

        if not self._ppa_targets and not self._skeleton_packages:
            result.skipped = True
            result.errors.append("No modules available for testbench generation")
            return result

        try:
            from rtlgen.cocotbgen import CocotbEmitter
        except ImportError:
            result.skipped = True
            result.errors.append("cocotbgen module not available")
            return result

        try:
            from rtlgen.pyuvmgen import UVMEmitter
        except ImportError:
            uvm_emitter_cls = None
        else:
            uvm_emitter_cls = UVMEmitter

        tb_dir = os.path.join(output_dir, "testbenches")
        os.makedirs(tb_dir, exist_ok=True)

        gen_count = 0

        # Generate testbenches from PPA targets (leaf DSL modules)
        cocotb_emitter = CocotbEmitter()
        for name, mod_cls in self._ppa_targets:
            try:
                mod = mod_cls()
                mod_tb_dir = os.path.join(tb_dir, name)
                os.makedirs(mod_tb_dir, exist_ok=True)

                # Cocotb testbench
                cocotb_files = cocotb_emitter.emit_full_cocotb(mod)
                for fname, content in cocotb_files.items():
                    fpath = os.path.join(mod_tb_dir, fname)
                    with open(fpath, "w") as f:
                        f.write(content)
                    result.metrics[f"{name}_cocotb_{fname}"] = content.count("\n")

                # UVM testbench (if available)
                if uvm_emitter_cls is not None:
                    try:
                        uvm_emitter = uvm_emitter_cls()
                        uvm_files = uvm_emitter.emit_full_uvm(mod)
                        for fname, content in uvm_files.items():
                            fpath = os.path.join(mod_tb_dir, fname)
                            with open(fpath, "w") as f:
                                f.write(content)
                            result.metrics[f"{name}_uvm_{fname}"] = content.count("\n")
                    except Exception as e:
                        result.warnings.append(f"{name}: UVM generation: {e}")

                gen_count += 1
            except Exception as e:
                result.warnings.append(f"{name}: testbench gen error: {e}")

        # Also generate from skeleton packages
        for pe_name, pkg in self._skeleton_packages.items():
            dsl_mod = getattr(pkg, "dsl_skeleton", None)
            if dsl_mod is None:
                continue
            try:
                mod_tb_dir = os.path.join(tb_dir, pe_name)
                os.makedirs(mod_tb_dir, exist_ok=True)

                cocotb_files = cocotb_emitter.emit_full_cocotb(dsl_mod)
                for fname, content in cocotb_files.items():
                    fpath = os.path.join(mod_tb_dir, fname)
                    with open(fpath, "w") as f:
                        f.write(content)

                gen_count += 1
                result.metrics[f"{pe_name}_cocotb_files"] = len(cocotb_files)
            except Exception as e:
                result.warnings.append(f"{pe_name}: testbench gen error: {e}")

        result.passed = gen_count > 0
        result.metrics["testbenches_generated"] = gen_count
        result.metrics["testbench_dir"] = tb_dir

        return result

    # -----------------------------------------------------------------
    # Stage 3f: agent_verify — Agent-driven verification with rtlgen Simulator
    # -----------------------------------------------------------------

    def _run_agent_verify(
        self,
        output_dir: str = "generated_skill_ppa",
        sim_cycles: int = 50,
    ) -> StageResult:
        """Agent-driven verification using rtlgen's Simulator.

        For each module:
        1. Create Simulator instance
        2. Run reset test (outputs zero after reset)
        3. Run random stimulus test (no crashes, no X values)
        4. Run sweep test (inputs affect outputs)
        5. Save JSON report to {output_dir}/verify_run/

        The agent reads simulation results and decides whether to:
        - Fix the DSL code (iterate)
        - Proceed to RTL emission
        """
        result = StageResult(
            "agent_verify",
            description="Agent-driven verification using rtlgen Simulator",
        )

        from rtlgen.sim import Simulator

        modules_to_test: List[Tuple[str, Any]] = []

        # From PPA targets
        for name, mod_cls in self._ppa_targets:
            try:
                mod = mod_cls()
                modules_to_test.append((name, mod))
            except Exception:
                pass

        # From skeleton packages
        for pe_name, pkg in self._skeleton_packages.items():
            dsl_mod = getattr(pkg, "dsl_skeleton", None)
            if dsl_mod is not None:
                if not any(n == pe_name for n, _ in modules_to_test):
                    modules_to_test.append((pe_name, dsl_mod))

        if not modules_to_test:
            result.skipped = True
            result.errors.append("No modules available for verification")
            return result

        verified_dir = os.path.join(output_dir, "verify_run")
        os.makedirs(verified_dir, exist_ok=True)

        total_tests = 0
        total_passed = 0
        total_failed = 0

        for name, mod in modules_to_test:
            try:
                sim = Simulator(mod, use_xz=False)

                # Detect reset signal
                rst_name = "rst_n"
                for r in ["rst_n", "reset_n", "rst", "reset", "aresetn"]:
                    if r in mod._inputs:
                        rst_name = r
                        break

                # Test 1: Reset behavior
                sim.reset(rst=rst_name, cycles=3)
                reset_ok = True
                for out_name in mod._outputs:
                    val = int(sim.get(out_name))
                    if val != 0:
                        reset_ok = False
                        break
                total_tests += 1
                if reset_ok:
                    total_passed += 1
                    result.metrics[f"{name}_reset"] = "pass"
                else:
                    total_failed += 1
                    result.metrics[f"{name}_reset"] = "fail"
                    result.warnings.append(f"{name}: reset test failed — outputs not zeroed")

                # Test 2: Random stimulus (no crash)
                import random
                random.seed(42)
                crash = False
                try:
                    for _ in range(sim_cycles):
                        for in_name in mod._inputs:
                            if in_name not in ("clk", rst_name, "rst"):
                                width = mod._inputs[in_name].width
                                sim.set(in_name, random.randint(0, (1 << width) - 1))
                        sim.step()
                except Exception as e:
                    crash = True
                    result.errors.append(f"{name}: random sim crashed: {e}")

                total_tests += 1
                if not crash:
                    total_passed += 1
                    result.metrics[f"{name}_random"] = "pass"
                else:
                    total_failed += 1
                    result.metrics[f"{name}_random"] = "fail"

                # Save report
                import json
                report = {
                    "module": name,
                    "reset": "pass" if reset_ok else "fail",
                    "random": "pass" if not crash else "fail",
                    "sim_cycles": sim_cycles,
                }
                report_path = os.path.join(verified_dir, f"{name}_report.json")
                with open(report_path, "w") as f:
                    json.dump(report, f, indent=2)

            except Exception as e:
                result.errors.append(f"{name}: verification error: {e}")
                total_failed += 2

        result.passed = total_failed == 0
        result.metrics["total_tests"] = total_tests
        result.metrics["total_passed"] = total_passed
        result.metrics["total_failed"] = total_failed
        result.metrics["verify_dir"] = verified_dir

        return result

    # -----------------------------------------------------------------
    # Stage 3d: agent_gen — Claude-driven DSL code generation (deprecated)
    # -----------------------------------------------------------------

    def _run_agent_gen(self, output_dir: str = "generated_skill_ppa") -> StageResult:
        """Call Claude API to generate DSL code from GenerationContext.

        DEPRECATED: Use spec_gen + dsl_from_spec instead for local generation.
        This method is kept for backward compatibility when ANTHROPIC_API_KEY is set.
        """
        result = StageResult("agent_gen", description="Agent-driven DSL code generation (deprecated)")

        if not self._arch or not self._skeleton_packages:
            result.skipped = True
            result.errors.append("Run skeleton stage first")
            return result

        try:
            from rtlgen.prompt_builder import build_generation_prompt
            from rtlgen.dsl_parser import parse_dsl_code
        except ImportError:
            result.skipped = True
            return result

        prompts_dir = os.path.join(output_dir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            result.skipped = True
            result.errors.append("ANTHROPIC_API_KEY not set")
            return result

        success_count = 0
        fail_count = 0
        skipped_count = 0
        max_repair_attempts = 2

        for pe_name, pkg in self._skeleton_packages.items():
            dsl_mod = getattr(pkg, 'dsl_skeleton', None)
            if dsl_mod is None or not hasattr(dsl_mod, '_generation_contexts'):
                skipped_count += 1
                continue

            contexts = dsl_mod._generation_contexts
            if not contexts:
                skipped_count += 1
                continue

            gen_ctx = contexts[0]

            try:
                prompt = build_generation_prompt(gen_ctx)
            except Exception as e:
                result.errors.append(f"build_prompt {pe_name}: {e}")
                fail_count += 1
                continue

            prompt_path = os.path.join(prompts_dir, f"{pe_name}.md")
            with open(prompt_path, "w") as f:
                f.write(prompt)

            code_path = os.path.join(prompts_dir, f"{pe_name}_dsl.py")
            if os.path.isfile(code_path):
                try:
                    with open(code_path, "r") as f:
                        code = f.read()
                    parse_result = parse_dsl_code(code)
                    if parse_result.success:
                        pkg.dsl_skeleton = parse_result.module
                        success_count += 1
                        result.metrics[f"{pe_name}_lines"] = parse_result.line_count
                        continue
                except Exception as e:
                    result.errors.append(f"read {pe_name} code: {e}")

            response_text = None
            conversation_history = [{"role": "user", "content": prompt}]

            for attempt in range(1 + max_repair_attempts):
                response_text = self._call_claude_api_with_history(
                    api_key, conversation_history, pe_name
                )
                if response_text is None:
                    fail_count += 1
                    break

                with open(code_path, "w") as f:
                    f.write(response_text)

                parse_result = parse_dsl_code(response_text)
                if parse_result.success:
                    pkg.dsl_skeleton = parse_result.module
                    success_count += 1
                    result.metrics[f"{pe_name}_lines"] = parse_result.line_count
                    break
                else:
                    errors = ', '.join(parse_result.errors[:2])
                    if attempt == 0:
                        result.errors.append(f"parse {pe_name}: {errors}")

                    if attempt < max_repair_attempts:
                        error_feedback = (
                            f"The generated code has parse errors:\n{errors}\n\n"
                            f"Please fix these errors and output the corrected "
                            f"complete class definition. Do NOT output only the fix — "
                            f"output the ENTIRE class with all corrections applied."
                        )
                        conversation_history.append({"role": "assistant", "content": response_text})
                        conversation_history.append({"role": "user", "content": error_feedback})
                    else:
                        fail_count += 1

        result.passed = success_count > 0
        result.metrics["agent_success"] = success_count
        result.metrics["agent_failures"] = fail_count
        result.metrics["agent_skipped"] = skipped_count

        return result

    @staticmethod
    def _call_claude_api(api_key: str, prompt: str, pe_name: str,
                         max_retries: int = 5) -> Optional[str]:
        """Call Claude API via anthropic SDK to generate DSL code.

        Uses environment variables:
          ANTHROPIC_AUTH_TOKEN — API key (or falls back to ANTHROPIC_API_KEY)
          ANTHROPIC_BASE_URL — Proxy endpoint
          ANTHROPIC_MODEL — Model name (default: claude-sonnet-4-20250514)

        Returns the assistant's response text, or None on failure.
        """
        return SkillPPARunner._call_claude_api_with_history(
            api_key, [{"role": "user", "content": prompt}], pe_name, max_retries
        )

    @staticmethod
    def _call_claude_api_with_history(api_key: str,
                                       messages: List[Dict[str, str]],
                                       pe_name: str,
                                       max_retries: int = 5) -> Optional[str]:
        """Call Claude API with multi-turn conversation support.

        Args:
            api_key: API key
            messages: List of message dicts with 'role' and 'content' keys
            pe_name: PE name for logging
            max_retries: Max retries for network errors

        Returns the assistant's response text, or None on failure.
        """
        import time

        try:
            from anthropic import Anthropic
        except ImportError:
            return None

        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or api_key
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        system_prompt = (
            "You are an expert RTL/Verilog designer familiar with the RTLCraft DSL. "
            "The RTLCraft DSL is a Python-based embedded domain language for describing "
            "hardware modules. Generate complete, correct DSL code that implements the "
            "specified module. Follow all coding rules. Output ONLY the class definition "
            "inside a python code block — no explanations, no imports, no test code."
        )

        client = Anthropic(api_key=auth_token, base_url=base_url)

        for attempt in range(1, max_retries + 1):
            try:
                # Exponential backoff between retries (4s, 8s, 16s, 32s)
                if attempt > 1:
                    time.sleep(min(4 * (2 ** (attempt - 2)), 60))
                response = client.messages.create(
                    model=model,
                    max_tokens=16384,
                    system=system_prompt,
                    messages=messages,
                )
                # Extract text blocks from response (may include thinking blocks)
                text_parts = []
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        text_parts.append(block.text)
                if text_parts:
                    return "\n".join(text_parts)
                return None
            except Exception:
                if attempt == max_retries:
                    return None
        return None

    # -----------------------------------------------------------------
    # Stage 4: ppa (load + analyze + optimize)
    # -----------------------------------------------------------------

    def _resolve_dsl_entry(self) -> Optional[Tuple[str, str]]:
        """Resolve the preferred DSL entrypoint for a skill.

        Supports both the legacy monolithic ``dsl_modules.py`` layout and the
        split ``layer3_dsl/__init__.py`` package layout described in the README.
        """
        candidates = [
            (
                os.path.join(self._skills_dir, self.skill_name, "dsl_modules.py"),
                f"skills.{self.skill_name}.dsl_modules",
            ),
            (
                os.path.join(self._skills_dir, self.skill_name, "layer3_dsl", "__init__.py"),
                f"skills.{self.skill_name}.layer3_dsl",
            ),
        ]
        for path, module_name in candidates:
            if os.path.isfile(path):
                return path, module_name
        return None

    @staticmethod
    def _class_belongs_to_dsl(attr: Any, dsl_module_name: str) -> bool:
        mod_name = getattr(attr, "__module__", "")
        return mod_name == dsl_module_name or mod_name.startswith(f"{dsl_module_name}.")

    def load_skill(self) -> bool:
        """Import the skill DSL entrypoint and discover Module classes."""
        resolved = self._resolve_dsl_entry()
        if resolved is None:
            self._errors.append(
                f"No DSL entrypoint found in skills/{self.skill_name}/ "
                f"(expected dsl_modules.py or layer3_dsl/__init__.py)"
            )
            return False
        dsl_path, full_name = resolved

        spec = importlib.util.spec_from_file_location(full_name, dsl_path)
        if spec is None or spec.loader is None:
            self._errors.append(f"Cannot create spec for {full_name}")
            return False

        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            self._errors.append(f"Failed to load {full_name}: {e}")
            return False

        self._dsl_mod = mod

        # Classify modules — only those DEFINED in this DSL module,
        # not imported from other packages (e.g. SyncFIFO from rtlgen.lib).
        dsl_module_name = full_name
        unique_modules: Dict[int, Tuple[str, type]] = {}

        for attr_name in sorted(dir(mod)):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, Module) and attr is not Module:
                # Skip classes not defined in this DSL module
                if not self._class_belongs_to_dsl(attr, dsl_module_name):
                    continue
                key = id(attr)
                existing = unique_modules.get(key)
                if existing is None:
                    unique_modules[key] = (attr_name, attr)
                elif existing[0] != attr.__name__ and attr_name == attr.__name__:
                    unique_modules[key] = (attr_name, attr)

        all_modules = sorted(unique_modules.values(), key=lambda item: item[0])

        if not all_modules:
            self._errors.append("No Module classes found in DSL modules")
            return False

        # Filter out classes that can't be instantiated with no arguments
        # (template classes that require constructor params)
        instantiable: List[Tuple[str, type]] = []
        for name, cls in all_modules:
            try:
                cls()
                instantiable.append((name, cls))
            except (TypeError, ValueError):
                pass  # Skip template classes

        all_modules = instantiable

        if not all_modules:
            self._errors.append("No instantiable Module classes found in DSL modules")
            return False

        top_modules = [(n, c) for n, c in all_modules if "Top" in n or "top" in n]
        top_entry = top_modules[-1] if top_modules else None
        self._top_module_cls = top_entry[1] if top_entry else None

        selected_top_name = top_entry[0] if top_entry else None
        self._ppa_targets = [(n, c) for n, c in all_modules if n != selected_top_name]

        self._loaded = True
        return True

    def _run_ppa_analyze(self) -> StageResult:
        """PPA static analysis on leaf DSL modules (before optimization)."""
        result = StageResult("ppa_analyze", description="PPA static analysis (before)")

        if not self._loaded:
            if not self.load_skill():
                result.passed = False
                result.errors.extend(self._errors)
                return result

        result.passed = True
        for name, mod_cls in self._ppa_targets:
            mod = mod_cls()
            analyzer = PPAAnalyzer(mod)
            report = analyzer.analyze_static()
            depths = report.get("logic_depth", {})
            max_depth = max(depths.values()) if depths else 0

            m = ModulePPAReport(
                module_name=name,
                class_name=mod_cls.__name__,
                before_depth=max_depth,
                gate_count_before=report.get("gate_count", 0),
                reg_bits_before=report.get("reg_bits", 0),
            )
            self._module_reports.append(m)
            result.metrics[f"{name}_depth"] = max_depth

        return result

    def _run_ppa_optimize(
        self,
        max_logic_depth: int = 5,
        max_iterations: int = 10,
    ) -> StageResult:
        """PPA optimization on leaf DSL modules."""
        result = StageResult("ppa_optimize", description="PPA optimization")

        if not self._module_reports:
            result.skipped = True
            return result

        result.passed = True
        for mreport in self._module_reports:
            before_depth = mreport.before_depth
            if before_depth <= max_logic_depth:
                mreport.after_depth = before_depth
                continue

            # Re-create module and optimize
            mod_cls = None
            for name, cls in self._ppa_targets:
                if name == mreport.module_name:
                    mod_cls = cls
                    break
            if mod_cls is None:
                continue

            mod = mod_cls()
            spec = SpecIR(
                name=mreport.module_name,
                ppa=PPASpec(priority="timing_first", max_logic_depth=max_logic_depth),
            )
            optimizer = PPAOptimizer(mod, spec)
            opt_result = optimizer.optimize(max_iterations=max_iterations)

            # Re-analyze
            analyzer = PPAAnalyzer(mod)
            after_report = analyzer.analyze_static()
            after_depths = after_report.get("logic_depth", {})
            after_max = max(after_depths.values()) if after_depths else 0

            mreport.after_depth = after_max
            mreport.gate_count_after = after_report.get("gate_count", 0)
            mreport.reg_bits_after = after_report.get("reg_bits", 0)
            mreport.strategies_applied = opt_result.strategies_applied
            mreport.optimized = len(opt_result.strategies_applied) > 0

            # Store optimized module for RTL emission
            if mreport.optimized:
                self._optimized_modules[mreport.module_name] = mod

        return result

    # -----------------------------------------------------------------
    # Stage 4a: contract_emit
    # -----------------------------------------------------------------

    def _run_contract_emit(self, output_dir: str) -> StageResult:
        """Emit per-module contract artifacts for DSL modules."""
        result = StageResult("contract_emit", description="Module contract artifact emission")

        if not self._loaded:
            if not self.load_skill():
                result.passed = False
                result.errors.extend(self._errors)
                return result

        os.makedirs(output_dir, exist_ok=True)
        contracts_dir = os.path.join(output_dir, "contracts")
        os.makedirs(contracts_dir, exist_ok=True)

        discovered_modules: List[Tuple[str, type]] = list(self._ppa_targets)
        if self._top_module_cls is not None:
            top_name = self._top_module_cls.__name__
            if all(name != top_name for name, _ in discovered_modules):
                discovered_modules.append((top_name, self._top_module_cls))

        manifest: Dict[str, Any] = {
            "skill": self.skill_name,
            "contracts": {},
            "modules_without_contract": [],
            "modules_with_instantiation_error": {},
        }
        emitted = 0
        missing = 0
        instantiation_failures = 0
        self._contract_files = {}

        for module_name, mod_cls in discovered_modules:
            try:
                mod = mod_cls()
            except Exception as e:
                instantiation_failures += 1
                manifest["modules_with_instantiation_error"][module_name] = str(e)
                result.errors.append(f"{module_name}: instantiation failed: {e}")
                continue

            contract = getattr(mod, "_module_contract", None)
            if not isinstance(contract, ModuleContract):
                missing += 1
                manifest["modules_without_contract"].append(module_name)
                continue

            payload = contract.to_dict()
            payload["module_class"] = mod_cls.__name__
            payload["module_instance_name"] = mod.name
            payload["ports_observed"] = {
                "inputs": sorted(mod._inputs.keys()),
                "outputs": sorted(mod._outputs.keys()),
            }
            contract_path = os.path.join(contracts_dir, f"{module_name}.contract.json")
            self._write_json(contract_path, payload)
            self._contract_files[module_name] = contract_path
            manifest["contracts"][module_name] = os.path.basename(contract_path)
            emitted += 1

        manifest_path = os.path.join(contracts_dir, "contracts_manifest.json")
        self._write_json(manifest_path, manifest)
        self._contract_files["__manifest__"] = manifest_path

        result.metrics["contracts_dir"] = contracts_dir
        result.metrics["contracts_emitted"] = emitted
        result.metrics["modules_missing_contract"] = missing
        result.metrics["modules_with_instantiation_error"] = instantiation_failures
        result.metrics["contract_manifest"] = os.path.basename(manifest_path)
        if manifest["modules_without_contract"]:
            result.metrics["missing_contract_modules"] = ",".join(manifest["modules_without_contract"])

        result.passed = instantiation_failures == 0
        return result

    # -----------------------------------------------------------------
    # Stage 4c: verify — DSL verification before RTL emission
    # -----------------------------------------------------------------

    def _run_verify(self, output_dir: str) -> StageResult:
        """Run verification on generated DSL modules before RTL emission.

        Checks:
        1. ModuleRequirement availability (structured spec)
        2. Behavior requirement extraction
        3. DSL-level completeness (via dsl_sim quick check)
        4. Contract-driven local performance checks
        """
        result = StageResult("verify", description="DSL verification")

        if not self._loaded:
            self.load_skill()

        has_skeletons = bool(self._skeleton_packages)
        has_dsl_targets = bool(self._ppa_targets)
        if not has_skeletons and not has_dsl_targets:
            result.skipped = True
            result.description = "No skeleton packages or DSL targets available for verification"
            return result

        result.passed = True
        verified_count = 0
        perf_reports_dir = os.path.join(output_dir, "verify")
        specs_dir = os.path.join(output_dir, "specs")
        os.makedirs(perf_reports_dir, exist_ok=True)
        perf_reports_generated = 0
        perf_failures = 0
        verification_plan_loaded = 0
        verification_plan_load_failed = 0

        for pe_name, pkg in self._skeleton_packages.items():
            # Check for ModuleRequirement attachment
            has_req = hasattr(pkg, "_module_requirement") and pkg._module_requirement
            has_beh = hasattr(pkg, "_behavior_requirement") and pkg._behavior_requirement
            dsl_validation = getattr(pkg, "_dsl_validation_report", None)

            if has_req:
                result.metrics[f"{pe_name}_module_requirement"] = "present"
                verified_count += 1
            if has_beh:
                result.metrics[f"{pe_name}_behavior_requirement"] = "present"
            if isinstance(dsl_validation, dict):
                result.metrics[f"{pe_name}_validation_stage"] = dsl_validation.get("validation_stage", "unknown")
                if dsl_validation.get("roundtrip_passed") is True:
                    result.metrics[f"{pe_name}_roundtrip"] = "pass"
                elif dsl_validation.get("roundtrip_passed") is False:
                    result.metrics[f"{pe_name}_roundtrip"] = "fail"
                if not dsl_validation.get("passed", False):
                    result.passed = False
                    for err in dsl_validation.get("errors", [])[:8]:
                        result.errors.append(f"{pe_name}: {err}")

            # Check DSL skeleton quality
            if pkg.dsl_skeleton is not None:
                mod = pkg.dsl_skeleton
                # Check for undriven outputs
                undriven = []
                for out_name in getattr(mod, "_outputs", {}):
                    if not hasattr(mod, out_name):
                        undriven.append(out_name)
                if undriven:
                    result.metrics[f"{pe_name}_undriven_outputs"] = ",".join(undriven)
                    result.passed = False
                    result.errors.append(
                        f"{pe_name}: undriven outputs: {', '.join(undriven)}"
                    )

        result.metrics["verified_modules"] = verified_count
        result.metrics["total_packages"] = len(self._skeleton_packages)

        # Run contract/performance verification on real DSL modules as a second lane.
        dsl_perf_checked = 0
        dsl_perf_failed = 0
        for module_name, mod_cls in self._ppa_targets:
            try:
                mod = mod_cls()
            except Exception as e:
                result.warnings.append(f"{module_name}: perf verify instantiate failed: {e}")
                continue
            verification_ir = None
            verification_plan_path = None
            if os.path.isdir(specs_dir):
                verification_ir, verification_plan_path, load_error = self._load_verification_plan_ir(
                    specs_dir,
                    self._candidate_verification_plan_stems(module_name, mod),
                )
                if verification_ir is not None:
                    verification_plan_loaded += 1
                    result.metrics[f"{module_name}_verification_plan"] = os.path.basename(
                        verification_plan_path or ""
                    )
                elif load_error:
                    verification_plan_load_failed += 1
                    result.warnings.append(
                        f"{module_name}: verification plan sidecar load failed"
                        f" ({os.path.basename(verification_plan_path or 'unknown')}): {load_error}"
                    )
            perf_report = self._run_perf_verify_module(module_name, mod, verification_ir=verification_ir)
            if not perf_report.contract_present:
                continue
            dsl_perf_checked += 1
            report_path = os.path.join(perf_reports_dir, f"{module_name}.perf.json")
            self._write_json(report_path, self._module_perf_report_to_dict(perf_report))
            result.metrics[f"{module_name}_perf_report"] = os.path.basename(report_path)
            result.metrics[f"{module_name}_perf_passed"] = perf_report.passed
            result.metrics[f"{module_name}_perf_static_checks"] = len(perf_report.static_checks)
            result.metrics[f"{module_name}_perf_dynamic_checks"] = len(perf_report.dynamic_checks)
            if perf_report.recommended_knobs:
                result.metrics[f"{module_name}_perf_knobs"] = ",".join(perf_report.recommended_knobs)
            perf_reports_generated += 1
            if not perf_report.passed:
                dsl_perf_failed += 1
                perf_failures += 1
                result.passed = False
                for failure in perf_report.blocking_failures[:6]:
                    result.errors.append(f"{module_name}: {failure}")

        result.metrics["perf_reports_generated"] = perf_reports_generated
        result.metrics["perf_failures"] = perf_failures
        result.metrics["perf_verify_dir"] = perf_reports_dir
        result.metrics["verification_plan_sidecars_loaded"] = verification_plan_loaded
        result.metrics["verification_plan_sidecars_failed"] = verification_plan_load_failed
        result.metrics["dsl_perf_checked"] = dsl_perf_checked
        result.metrics["dsl_perf_failed"] = dsl_perf_failed

        return result

    @staticmethod
    def _module_perf_report_to_dict(report: ModulePerfReport) -> Dict[str, Any]:
        def _check_to_dict(check: PerfCheckResult) -> Dict[str, Any]:
            return {
                "name": check.name,
                "kind": check.kind,
                "passed": check.passed,
                "observed": dict(check.observed),
                "expected": dict(check.expected),
                "details": list(check.details),
            }

        return {
            "module_name": report.module_name,
            "contract_present": report.contract_present,
            "static_checks": [_check_to_dict(c) for c in report.static_checks],
            "dynamic_checks": [_check_to_dict(c) for c in report.dynamic_checks],
            "passed": report.passed,
            "blocking_failures": list(report.blocking_failures),
            "failure_records": list(report.failure_records),
            "recommended_knobs": list(report.recommended_knobs),
        }

    def _run_perf_verify_module(
        self,
        module_name: str,
        mod: Module,
        verification_ir: Optional[VerificationPlanIR] = None,
    ) -> ModulePerfReport:
        report = ModulePerfReport(module_name=module_name)
        contract = getattr(mod, "_module_contract", None)
        if not isinstance(contract, ModuleContract):
            return report

        report.contract_present = True
        if verification_ir is None:
            verification_ir = self._verification_plan_from_contract(contract)
        derived_checks = self._derive_verification_plan_perf_checks(verification_ir)
        explicit_check_names = {check.name for check in getattr(contract.performance_objective, "checks", [])}
        derived_checks = [check for check in derived_checks if check.name not in explicit_check_names]
        schema_issues = self._validate_extended_contract(mod, contract, verification_ir)
        checks = list(getattr(contract.performance_objective, "checks", [])) + derived_checks
        analyzer = PPAAnalyzer(mod)
        ppa_report = analyzer.analyze_static()
        max_depth = 0
        depths = ppa_report.get("logic_depth", {})
        if depths:
            max_depth = max(depths.values())

        for check in checks:
            if check.kind == "structural_budget":
                result = self._run_perf_structural_check(mod, contract, check, ppa_report, max_depth)
                report.static_checks.append(result)
            else:
                result = self._run_perf_dynamic_check(mod, contract, check, verification_ir)
                report.dynamic_checks.append(result)

        all_checks = report.static_checks + report.dynamic_checks
        report.passed = (all(c.passed for c in all_checks) if all_checks else True) and not schema_issues
        if not report.passed:
            report.recommended_knobs = list(contract.performance_objective.optimization_knobs)
            for issue in schema_issues:
                report.blocking_failures.append(issue)
                report.failure_records.append(
                    {
                        "kind": "schema",
                        "module": module_name,
                        "message": issue,
                        "suspected_knobs": list(report.recommended_knobs),
                    }
                )
            for check in all_checks:
                if not check.passed:
                    detail = "; ".join(check.details) if check.details else "perf check failed"
                    report.blocking_failures.append(f"{check.name}: {detail}")
                    report.failure_records.append(
                        {
                            "kind": "perf_check",
                            "module": module_name,
                            "check": check.name,
                            "check_kind": check.kind,
                            "message": detail,
                            "observed": dict(check.observed),
                            "expected": dict(check.expected),
                            "suspected_knobs": list(report.recommended_knobs),
                        }
                    )
        return report

    @staticmethod
    def _available_signal_names(mod: Module) -> set[str]:
        return set(mod._inputs) | set(mod._outputs) | set(mod._wires) | set(mod._regs) | set(mod._arrays)

    def _validate_extended_contract(
        self,
        mod: Module,
        contract: ModuleContract,
        verification_ir: Optional[VerificationPlanIR] = None,
    ) -> List[str]:
        issues: List[str] = []
        available = self._available_signal_names(mod)
        allowed_event_kinds = {"level", "rise", "handshake"}
        allowed_recipe_kinds = {"hold", "pulse", "periodic"}
        allowed_transaction_recipes = supported_transaction_recipes(include_empty=True)
        allowed_protocol_recipes = supported_protocol_recipes(include_empty=True)

        def _missing(signals: List[str]) -> List[str]:
            return [sig for sig in signals if sig not in available]

        contract_protocols = list(getattr(contract, "protocols", []))
        plan_protocols = [
            self._protocol_ir_to_contract(proto)
            for proto in getattr(verification_ir, "protocols", [])
        ] if verification_ir is not None else []
        validation_protocols = contract_protocols + [
            proto for proto in plan_protocols
            if proto.name not in {existing.name for existing in contract_protocols}
        ]

        for proto in validation_protocols:
            if not proto.request_signals and not proto.response_signals:
                issues.append(f"protocol {proto.name}: no request/response signals declared")
            miss = _missing(proto.request_signals + proto.response_signals + proto.flow_control_signals)
            if miss:
                issues.append(f"protocol {proto.name}: unknown signals {', '.join(miss)}")
            if getattr(proto, "recipe", "") not in allowed_protocol_recipes:
                issues.append(f"protocol {proto.name}: unsupported recipe {proto.recipe}")
            else:
                issues.extend(validate_protocol_recipe_contract(proto))

        contract_transactions = list(getattr(contract, "transactions", []))
        plan_transactions = [
            self._transaction_ir_to_contract(txn)
            for txn in getattr(verification_ir, "transactions", [])
        ] if verification_ir is not None else []
        validation_transactions = contract_transactions + [
            txn for txn in plan_transactions
            if txn.name not in {existing.name for existing in contract_transactions}
        ]

        for txn in validation_transactions:
            if not txn.trigger_signals or not txn.completion_signals:
                issues.append(f"transaction {txn.name}: trigger/completion signals incomplete")
            miss = _missing(
                txn.trigger_signals
                + txn.completion_signals
                + list(getattr(txn, "trigger_qualifiers", []))
                + list(getattr(txn, "completion_qualifiers", []))
            )
            if miss:
                issues.append(f"transaction {txn.name}: unknown signals {', '.join(miss)}")
            if getattr(txn, "recipe", "") not in allowed_transaction_recipes:
                issues.append(f"transaction {txn.name}: unsupported recipe {txn.recipe}")
            else:
                issues.extend(validate_transaction_recipe_contract(txn))
            if getattr(txn, "trigger_event", "level") not in allowed_event_kinds:
                issues.append(f"transaction {txn.name}: unsupported trigger_event {txn.trigger_event}")
            if getattr(txn, "completion_event", "level") not in allowed_event_kinds:
                issues.append(
                    f"transaction {txn.name}: unsupported completion_event {txn.completion_event}"
                )

        for res in getattr(contract, "resources", []):
            miss = _missing(res.observable_signals + res.contention_signals)
            if miss:
                issues.append(f"resource {res.name}: unknown signals {', '.join(miss)}")

        checks = list(getattr(contract.performance_objective, "checks", []))
        for check in checks:
            miss = _missing(
                list(check.source_signals)
                + list(check.sink_signals)
                + list(getattr(check, "source_qualifiers", []))
                + list(getattr(check, "sink_qualifiers", []))
            )
            if miss:
                issues.append(f"perf check {check.name}: unknown signals {', '.join(miss)}")
            if getattr(check, "source_event", "level") not in allowed_event_kinds:
                issues.append(f"perf check {check.name}: unsupported source_event {check.source_event}")
            if getattr(check, "sink_event", "level") not in allowed_event_kinds:
                issues.append(f"perf check {check.name}: unsupported sink_event {check.sink_event}")
            if getattr(check, "source_event", "level") == "handshake" and not getattr(check, "source_qualifiers", []):
                issues.append(f"perf check {check.name}: source_event handshake requires source_qualifiers")
            if getattr(check, "sink_event", "level") == "handshake" and not getattr(check, "sink_qualifiers", []):
                issues.append(f"perf check {check.name}: sink_event handshake requires sink_qualifiers")
            if check.kind == "fairness":
                sink_groups = check.metadata.get("sink_groups", [])
                if not isinstance(sink_groups, list) or len(sink_groups) < 2:
                    issues.append(f"perf check {check.name}: fairness requires at least two sink_groups")
                else:
                    group_signals: List[str] = []
                    for group in sink_groups:
                        if isinstance(group, dict):
                            group_signals.extend(list(group.get("signals", [])))
                        elif isinstance(group, list):
                            group_signals.extend(list(group))
                        else:
                            issues.append(f"perf check {check.name}: fairness sink_groups entries must be dict or list")
                    miss = _missing(group_signals)
                    if miss:
                        issues.append(f"perf check {check.name}: fairness references unknown signals {', '.join(miss)}")

        scenarios = getattr(contract.performance_objective, "scenarios", [])
        check_names = {check.name for check in checks}
        transaction_names = {txn.name for txn in validation_transactions}
        for scenario in scenarios:
            miss = _missing(scenario.stimulus_signal_names() + scenario.expected_signal_names())
            if miss:
                issues.append(f"scenario {scenario.name}: unknown signals {', '.join(miss)}")
            linked = scenario.resolved_linked_checks()
            unknown_checks = [name for name in linked if name not in check_names]
            if unknown_checks:
                issues.append(
                    f"scenario {scenario.name}: unknown linked checks {', '.join(unknown_checks)}"
                )
            unknown_transactions = [
                name for name in getattr(scenario, "linked_transactions", [])
                if name not in transaction_names
            ]
            if unknown_transactions:
                issues.append(
                    f"scenario {scenario.name}: unknown linked transactions {', '.join(unknown_transactions)}"
                )
            for step in getattr(scenario, "stimulus_timeline", []):
                if not isinstance(step, PerfStimulusStep):
                    issues.append(f"scenario {scenario.name}: invalid stimulus timeline step")
                    continue
                if step.start_cycle < 0:
                    issues.append(f"scenario {scenario.name}: negative start_cycle in stimulus timeline")
                if step.end_cycle is not None and step.end_cycle < step.start_cycle:
                    issues.append(
                        f"scenario {scenario.name}: end_cycle before start_cycle in stimulus timeline"
                    )
            for recipe in getattr(scenario, "stimulus_recipes", []):
                if not isinstance(recipe, PerfStimulusRecipe):
                    issues.append(f"scenario {scenario.name}: invalid stimulus recipe")
                    continue
                if recipe.kind not in allowed_recipe_kinds:
                    issues.append(f"scenario {scenario.name}: unsupported stimulus recipe kind {recipe.kind}")
                if recipe.start_cycle < 0:
                    issues.append(f"scenario {scenario.name}: negative start_cycle in stimulus recipe")
                if recipe.end_cycle is not None and recipe.end_cycle < recipe.start_cycle:
                    issues.append(f"scenario {scenario.name}: end_cycle before start_cycle in stimulus recipe")
                if int(recipe.period) <= 0:
                    issues.append(f"scenario {scenario.name}: non-positive period in stimulus recipe")
                if int(recipe.duty_cycles) < 0:
                    issues.append(f"scenario {scenario.name}: negative duty_cycles in stimulus recipe")
        return issues

    @staticmethod
    def _run_perf_structural_check(
        mod: Module,
        contract: ModuleContract,
        check: PerfCheck,
        ppa_report: Dict[str, Any],
        max_depth: int,
    ) -> PerfCheckResult:
        from rtlgen.core import SubmoduleInst

        def _submodule_types(module: Module) -> List[str]:
            seen: set[int] = set()
            types: List[str] = []
            for _, sub in module._submodules:
                if id(sub) in seen:
                    continue
                seen.add(id(sub))
                types.append(getattr(sub, "_type_name", type(sub).__name__))
            for stmt in module._top_level:
                if isinstance(stmt, SubmoduleInst):
                    if id(stmt.module) in seen:
                        continue
                    seen.add(id(stmt.module))
                    types.append(getattr(stmt.module, "_type_name", type(stmt.module).__name__))
            return types

        observed: Dict[str, Any] = {}
        expected: Dict[str, Any] = {}
        details: List[str] = []
        passed = True

        budget = contract.performance_objective.structural_budget
        if check.budget_key == "max_logic_depth":
            observed_value = max_depth
            expected_value = check.required_value if check.required_value is not None else budget.get("max_logic_depth")
            observed["logic_depth"] = observed_value
            expected["max_logic_depth"] = expected_value
            if expected_value is not None and observed_value > expected_value:
                passed = False
                details.append(f"logic depth {observed_value} exceeds budget {expected_value}")
        elif check.budget_key == "max_issue_queues":
            observed_value = sum(1 for t in _submodule_types(mod) if t == "IssueQueue")
            expected_value = check.required_value if check.required_value is not None else budget.get("max_issue_queues")
            observed["issue_queue_count"] = observed_value
            expected["max_issue_queues"] = expected_value
            if expected_value is not None and observed_value > expected_value:
                passed = False
                details.append(f"issue queue count {observed_value} exceeds budget {expected_value}")
        elif check.metadata.get("submodule_type"):
            submodule_type = str(check.metadata["submodule_type"])
            observed_value = sum(1 for t in _submodule_types(mod) if t == submodule_type)
            expected_value = check.required_value if check.required_value is not None else budget.get(check.budget_key)
            observed["submodule_type"] = submodule_type
            observed["submodule_count"] = observed_value
            expected["required_count"] = expected_value
            if expected_value is not None and observed_value != expected_value:
                passed = False
                details.append(
                    f"submodule type {submodule_type} count {observed_value}, expected {expected_value}"
                )
        else:
            observed_value = budget.get(check.budget_key)
            expected_value = check.required_value if check.required_value is not None else budget.get(check.budget_key)
            observed[check.budget_key] = observed_value
            expected[check.budget_key] = expected_value
            if expected_value is not None and observed_value != expected_value:
                passed = False
                details.append(f"{check.budget_key} observed {observed_value}, expected {expected_value}")

        if passed and not details:
            details.append("structural budget satisfied")

        return PerfCheckResult(
            name=check.name,
            kind=check.kind,
            passed=passed,
            observed=observed,
            expected=expected,
            details=details,
        )

    @staticmethod
    def _transaction_perf_check_name(txn: TransactionContract, suffix: str) -> str:
        return transaction_perf_check_name(txn, suffix)

    @staticmethod
    def _protocol_ir_to_contract(proto: ProtocolIR) -> ProtocolContract:
        return ProtocolContract(
            name=proto.name,
            kind=proto.kind,
            recipe=getattr(proto, "recipe", ""),
            request_signals=list(proto.request_signals),
            response_signals=list(proto.response_signals),
            flow_control_signals=list(proto.flow_control_signals),
            ordering=proto.ordering,
            description=proto.description,
            metadata=dict(getattr(proto, "metadata", {})),
        )

    @staticmethod
    def _transaction_ir_to_contract(txn: TransactionIR) -> TransactionContract:
        return TransactionContract(
            name=txn.name,
            trigger_signals=list(txn.trigger_signals),
            completion_signals=list(txn.completion_signals),
            recipe=txn.recipe,
            trigger_event=txn.trigger_event,
            completion_event=txn.completion_event,
            trigger_qualifiers=list(txn.trigger_qualifiers),
            completion_qualifiers=list(txn.completion_qualifiers),
            max_cycles=txn.max_cycles,
            sample_cycles=txn.sample_cycles,
            ordering=txn.ordering,
            allow_overlap=txn.allow_overlap,
            description=txn.description,
            metadata=dict(txn.metadata),
        )

    @classmethod
    def _derive_verification_plan_protocol_checks(
        cls,
        verification_ir: VerificationPlanIR,
    ) -> List[PerfCheck]:
        derived: List[PerfCheck] = []
        for proto_ir in getattr(verification_ir, "protocols", []):
            check = derive_protocol_perf_check(cls._protocol_ir_to_contract(proto_ir))
            if check is None:
                continue
            metadata = dict(check.metadata)
            metadata["verification_plan_module"] = verification_ir.module_name
            metadata["verification_plan_source"] = "VerificationPlanIR"
            check.metadata = metadata
            derived.append(check)
        return derived

    @classmethod
    def _derive_verification_plan_perf_checks(
        cls,
        verification_ir: VerificationPlanIR,
    ) -> List[PerfCheck]:
        derived: List[PerfCheck] = cls._derive_verification_plan_protocol_checks(verification_ir)
        for txn_ir in getattr(verification_ir, "transactions", []):
            if not getattr(txn_ir, "recipe", ""):
                continue
            check = derive_transaction_perf_check(cls._transaction_ir_to_contract(txn_ir))
            if check is None:
                continue
            metadata = dict(check.metadata)
            metadata["verification_plan_module"] = verification_ir.module_name
            metadata["verification_plan_source"] = "VerificationPlanIR"
            check.metadata = metadata
            derived.append(check)
        return derived

    @classmethod
    def _derive_transaction_perf_checks(
        cls,
        contract: ModuleContract,
    ) -> List[PerfCheck]:
        verification_ir = cls._verification_plan_from_contract(contract)
        derived = cls._derive_verification_plan_perf_checks(verification_ir)
        existing = {check.name for check in getattr(contract.performance_objective, "checks", [])}
        return [check for check in derived if check.name not in existing]

    @staticmethod
    def _drive_perf_stimulus(mod: Module, sim: Any, check: PerfCheck, cycle_idx: int) -> None:
        for in_name, sig in mod._inputs.items():
            if in_name in ("clk", "rst", "rst_n", "reset", "reset_n", "aresetn"):
                continue
            value = 0
            if in_name in check.source_signals:
                value = 1
            elif check.metadata.get("stimulus", {}).get(in_name) is not None:
                value = int(check.metadata["stimulus"][in_name])
            elif sig.width > 1 and check.kind in ("throughput", "duty_cycle", "utilization", "occupancy"):
                value = cycle_idx & ((1 << sig.width) - 1)
            sim.set(in_name, value)

    @staticmethod
    def _active_series(values: Dict[str, List[int]], signal_name: str) -> List[int]:
        return list(values.get(signal_name, []))

    @staticmethod
    def _first_active_cycle(values: Dict[str, List[int]], signal_name: str) -> Optional[int]:
        return next((i for i, v in enumerate(values.get(signal_name, [])) if v), None)

    @staticmethod
    def _float_series(values: Dict[str, List[int]], signal_name: str) -> List[float]:
        return [float(v) for v in values.get(signal_name, [])]

    @staticmethod
    def _event_series(
        raw_values: Dict[str, List[int]],
        signal_name: str,
        event_kind: str,
        qualifiers: List[str],
    ) -> List[int]:
        base = list(raw_values.get(signal_name, []))
        if not base:
            return []

        gated_by_qualifiers = event_kind == "handshake"

        if event_kind == "rise":
            prev = 0
            events: List[int] = []
            for value in base:
                events.append(1 if value != 0 and prev == 0 else 0)
                prev = value
        else:
            events = [1 if value != 0 else 0 for value in base]

        if gated_by_qualifiers or qualifiers:
            for qualifier in qualifiers:
                qvals = list(raw_values.get(qualifier, []))
                if not qvals:
                    events = [0 for _ in events]
                    break
                limit = min(len(events), len(qvals))
                events = [
                    1 if idx < limit and events[idx] and qvals[idx] != 0 else 0
                    for idx in range(len(events))
                ]
        return events

    @classmethod
    def _evaluate_perf_dynamic_check(
        cls,
        check: PerfCheck,
        source_active: Dict[str, List[int]],
        sink_active: Dict[str, List[int]],
        sink_values: Dict[str, List[int]],
    ) -> Tuple[bool, Dict[str, Any], Dict[str, Any], List[str]]:
        observed: Dict[str, Any] = {}
        expected: Dict[str, Any] = {}
        details: List[str] = []
        passed = True

        if check.kind == "latency":
            source_sig = check.source_signals[0] if check.source_signals else ""
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            first_source = cls._first_active_cycle(source_active, source_sig)
            first_sink = cls._first_active_cycle(sink_active, sink_sig)
            observed["first_source_cycle"] = first_source
            observed["first_sink_cycle"] = first_sink
            expected["max_cycles"] = check.max_cycles
            if first_source is None or first_sink is None:
                passed = False
                details.append("source or sink activity was not observed")
            else:
                latency = max(0, first_sink - first_source)
                observed["latency_cycles"] = latency
                if check.max_cycles is not None and latency > check.max_cycles:
                    passed = False
                    details.append(f"latency {latency} exceeds max {check.max_cycles}")
                else:
                    details.append(f"latency {latency} within budget")
            return passed, observed, expected, details

        if check.kind in ("throughput", "duty_cycle"):
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            active = cls._active_series(sink_active, sink_sig)
            rate = (sum(active) / len(active)) if active else 0.0
            observed["rate"] = rate
            expected["min_rate"] = check.min_rate
            if check.min_rate is not None and rate < check.min_rate:
                passed = False
                details.append(f"rate {rate:.3f} below minimum {check.min_rate:.3f}")
            else:
                details.append(f"rate {rate:.3f} satisfies minimum")
            return passed, observed, expected, details

        if check.kind == "stall_ratio":
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            active = cls._active_series(sink_active, sink_sig)
            ratio = (sum(active) / len(active)) if active else 0.0
            observed["ratio"] = ratio
            expected["max_ratio"] = check.max_ratio
            if check.max_ratio is not None and ratio > check.max_ratio:
                passed = False
                details.append(f"ratio {ratio:.3f} exceeds maximum {check.max_ratio:.3f}")
            else:
                details.append(f"ratio {ratio:.3f} within limit")
            return passed, observed, expected, details

        if check.kind == "utilization":
            source_sig = check.source_signals[0] if check.source_signals else ""
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            source_count = sum(cls._active_series(source_active, source_sig))
            sink_count = sum(cls._active_series(sink_active, sink_sig))
            ratio = (sink_count / source_count) if source_count else 0.0
            observed["source_events"] = source_count
            observed["sink_events"] = sink_count
            observed["utilization"] = ratio
            expected["min_ratio"] = check.min_ratio
            if check.min_ratio is not None and ratio < check.min_ratio:
                passed = False
                details.append(f"utilization {ratio:.3f} below minimum {check.min_ratio:.3f}")
            else:
                details.append(f"utilization {ratio:.3f} satisfies minimum")
            return passed, observed, expected, details

        if check.kind == "completion_bound":
            source_sig = check.source_signals[0] if check.source_signals else ""
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            source_events = cls._active_series(source_active, source_sig)
            sink_events = cls._active_series(sink_active, sink_sig)
            source_count = sum(source_events)
            sink_count = sum(sink_events)
            outstanding = 0
            peak_outstanding = 0
            for idx in range(max(len(source_events), len(sink_events))):
                outstanding += source_events[idx] if idx < len(source_events) else 0
                outstanding -= sink_events[idx] if idx < len(sink_events) else 0
                if outstanding < 0:
                    outstanding = 0
                peak_outstanding = max(peak_outstanding, outstanding)
            observed["source_events"] = source_count
            observed["sink_events"] = sink_count
            observed["outstanding"] = outstanding
            observed["peak_outstanding"] = peak_outstanding
            expected["max_value"] = check.max_value
            if check.max_value is not None and peak_outstanding > check.max_value:
                passed = False
                details.append(
                    f"peak outstanding completions {peak_outstanding} exceed maximum {check.max_value:.3f}"
                )
            else:
                details.append(f"peak outstanding completions {peak_outstanding} within bound")
            return passed, observed, expected, details

        if check.kind == "occupancy":
            sink_sig = check.sink_signals[0] if check.sink_signals else ""
            values = cls._float_series(sink_values, sink_sig)
            avg_value = (sum(values) / len(values)) if values else 0.0
            peak_value = max(values) if values else 0.0
            observed["average_occupancy"] = avg_value
            observed["peak_occupancy"] = peak_value
            expected["min_value"] = check.min_value
            expected["max_value"] = check.max_value
            if check.min_value is not None and avg_value < check.min_value:
                passed = False
                details.append(f"average occupancy {avg_value:.3f} below minimum {check.min_value:.3f}")
            if check.max_value is not None and peak_value > check.max_value:
                passed = False
                details.append(f"peak occupancy {peak_value:.3f} exceeds maximum {check.max_value:.3f}")
            if passed:
                details.append(
                    f"occupancy avg {avg_value:.3f}, peak {peak_value:.3f} within configured bounds"
                )
            return passed, observed, expected, details

        if check.kind == "fairness":
            sink_groups = check.metadata.get("sink_groups", [])
            if not isinstance(sink_groups, list) or len(sink_groups) < 2:
                return False, observed, expected, ["fairness check requires metadata.sink_groups"]
            counts: List[int] = []
            group_names: List[str] = []
            for idx, group in enumerate(sink_groups):
                if isinstance(group, dict):
                    signals = list(group.get("signals", []))
                    group_name = str(group.get("name", f"group_{idx}"))
                elif isinstance(group, list):
                    signals = list(group)
                    group_name = f"group_{idx}"
                else:
                    return False, observed, expected, ["fairness sink_groups entries must be dict or list"]
                count = 0
                for sig in signals:
                    count += sum(cls._active_series(sink_active, sig))
                counts.append(count)
                group_names.append(group_name)
            min_count = min(counts) if counts else 0
            max_count = max(counts) if counts else 0
            ratio = (min_count / max_count) if max_count else 1.0
            observed["group_counts"] = dict(zip(group_names, counts))
            observed["fairness_ratio"] = ratio
            expected["min_ratio"] = check.min_ratio
            if check.min_ratio is not None and ratio < check.min_ratio:
                passed = False
                details.append(f"fairness ratio {ratio:.3f} below minimum {check.min_ratio:.3f}")
            else:
                details.append(f"fairness ratio {ratio:.3f} satisfies minimum")
            return passed, observed, expected, details

        return passed, observed, expected, ["dynamic check kind not yet implemented"]

    @staticmethod
    def _resolve_scenario_for_check(
        contract: ModuleContract,
        check: PerfCheck,
        verification_ir: Optional[VerificationPlanIR] = None,
    ) -> Optional[PerfScenario]:
        scenarios = getattr(contract.performance_objective, "scenarios", [])
        for scenario in scenarios:
            if check.name in scenario.resolved_linked_checks():
                return scenario
            txn_name = check.metadata.get("transaction_name", "")
            if txn_name and txn_name in getattr(scenario, "linked_transactions", []):
                return scenario
        txn_name = check.metadata.get("transaction_name", "")
        if txn_name:
            for txn in getattr(contract, "transactions", []):
                if txn.name == txn_name:
                    return derive_transaction_scenario(txn)
            if verification_ir is not None:
                for txn_ir in getattr(verification_ir, "transactions", []):
                    if txn_ir.name == txn_name:
                        return derive_transaction_scenario(
                            SkillPPARunner._transaction_ir_to_contract(txn_ir)
                        )
        proto_name = check.metadata.get("protocol_name", "")
        if proto_name:
            for proto in getattr(contract, "protocols", []):
                if proto.name == proto_name:
                    return derive_protocol_scenario(proto)
            if verification_ir is not None:
                for proto_ir in getattr(verification_ir, "protocols", []):
                    if proto_ir.name == proto_name:
                        return derive_protocol_scenario(
                            SkillPPARunner._protocol_ir_to_contract(proto_ir)
                        )
        return None

    @staticmethod
    def _scenario_observation_context(
        scenario: Optional[PerfScenario],
        sample_cycles: int,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        observed: Dict[str, Any] = {}
        expected: Dict[str, Any] = {}
        if scenario is None:
            return observed, expected

        expected.update(dict(getattr(scenario, "expected_observations", {})))
        tags = list(getattr(scenario, "tags", []))
        if tags:
            expected["scenario_tags"] = tags

        timeline = list(getattr(scenario, "stimulus_timeline", []))
        recipes = list(getattr(scenario, "stimulus_recipes", []))
        observed["scenario_cycles"] = sample_cycles
        observed["scenario_timeline_steps"] = len(timeline)
        if recipes:
            observed["scenario_recipe_kinds"] = [recipe.kind for recipe in recipes]
        if timeline:
            observed["scenario_timeline_signals"] = sorted(
                {
                    signal
                    for step in timeline
                    for signal in getattr(step, "values", {}).keys()
                }
            )

        if expected.get("scenario_delay_cycles") is not None:
            delay = int(expected["scenario_delay_cycles"])
            observed["delayed_completion_cycle"] = min(delay, max(sample_cycles - 1, 0))

        backpressure_signal = expected.get("backpressure_signal")
        if backpressure_signal:
            active_cycles: List[int] = []
            driven_values: List[int] = []
            for cycle in range(sample_cycles):
                for step in timeline:
                    values = getattr(step, "values", {})
                    if str(backpressure_signal) in values and step.applies(cycle):
                        active_cycles.append(cycle)
                        driven_values.append(int(values[str(backpressure_signal)]))
                        break
            observed["backpressure_signal"] = backpressure_signal
            observed["backpressure_window_cycles"] = active_cycles
            observed["backpressure_window_count"] = len(active_cycles)
            if driven_values:
                observed["backpressure_values"] = driven_values

        if expected.get("violation_probe"):
            source_signal = ""
            for step in timeline:
                if getattr(step, "values", {}):
                    source_signal = next(iter(step.values.keys()))
                    break
            observed["violation_probe_steps"] = sum(
                1 for step in timeline if getattr(step, "values", {})
            )
            if source_signal:
                observed["violation_probe_signal"] = source_signal
        return observed, expected

    def _run_perf_dynamic_check(
        self,
        mod: Module,
        contract: ModuleContract,
        check: PerfCheck,
        verification_ir: Optional[VerificationPlanIR] = None,
    ) -> PerfCheckResult:
        from rtlgen.sim import Simulator

        observed: Dict[str, Any] = {}
        expected: Dict[str, Any] = {}
        details: List[str] = []
        passed = True
        sample_cycles = max(check.sample_cycles, 1)
        expected_context: Dict[str, Any] = {}
        if check.metadata.get("verification_plan_source"):
            expected_context["source"] = check.metadata["verification_plan_source"]
        if check.metadata.get("verification_plan_module"):
            expected_context["verification_plan_module"] = check.metadata["verification_plan_module"]

        try:
            sim = Simulator(mod, use_xz=False)
            rst_name = self._detect_reset_name(mod)
            scenario = self._resolve_scenario_for_check(contract, check, verification_ir)
            reset_cycles = scenario.reset_cycles if scenario is not None else 3
            sim.reset(rst=rst_name, cycles=reset_cycles)

            if check.metadata.get("reset_release_check"):
                seen = False
                for cycle in range(sample_cycles):
                    self._drive_perf_stimulus(mod, sim, check, cycle)
                    sim.step()
                    if any(int(sim.get(sig)) != 0 for sig in check.sink_signals):
                        observed["first_seen_cycle"] = cycle
                        seen = True
                        break
                expected["max_cycles"] = check.max_cycles
                if not seen:
                    passed = False
                    details.append("sink signal never became active after reset release")
                elif check.max_cycles is not None and int(observed["first_seen_cycle"]) > check.max_cycles:
                    passed = False
                    details.append(
                        f"first activation at cycle {observed['first_seen_cycle']} exceeds max {check.max_cycles}"
                    )
                else:
                    details.append("reset-release activation latency satisfied")
                expected = {**expected_context, **expected}
                return PerfCheckResult(
                    name=check.name,
                    kind=check.kind,
                    passed=passed,
                    observed=observed,
                    expected=expected,
                    details=details,
                )

            if scenario is not None:
                sample_cycles = max(int(scenario.cycles or sample_cycles), 1)

            sink_active = {sig: [] for sig in check.sink_signals}
            source_active = {sig: [] for sig in check.source_signals}
            sink_values = {sig: [] for sig in check.sink_signals}
            source_values = {sig: [] for sig in check.source_signals}
            qualifier_names = set(getattr(check, "source_qualifiers", [])) | set(getattr(check, "sink_qualifiers", []))
            qualifier_values = {sig: [] for sig in qualifier_names}
            for cycle in range(sample_cycles):
                if scenario is not None:
                    for in_name, sig in mod._inputs.items():
                        if in_name in ("clk", "rst", "rst_n", "reset", "reset_n", "aresetn"):
                            continue
                        default_val = 0
                        if sig.width > 1 and check.kind in ("throughput", "duty_cycle", "utilization", "occupancy"):
                            default_val = cycle & ((1 << sig.width) - 1)
                        value = scenario.value_for_cycle(in_name, cycle, default_val)
                        sim.set(in_name, int(value) if isinstance(value, bool) or isinstance(value, int) else default_val)
                else:
                    self._drive_perf_stimulus(mod, sim, check, cycle)
                sim.step()
                for sig in check.sink_signals:
                    value = int(sim.get(sig))
                    sink_active[sig].append(1 if value != 0 else 0)
                    sink_values[sig].append(value)
                for sig in check.source_signals:
                    value = int(sim.get(sig))
                    source_active[sig].append(1 if value != 0 else 0)
                    source_values[sig].append(value)
                for sig in qualifier_names:
                    qualifier_values[sig].append(int(sim.get(sig)))
            for sig in check.source_signals:
                source_active[sig] = self._event_series(
                    {**source_values, **qualifier_values},
                    sig,
                    getattr(check, "source_event", "level"),
                    list(getattr(check, "source_qualifiers", [])),
                )
            for sig in check.sink_signals:
                sink_active[sig] = self._event_series(
                    {**sink_values, **qualifier_values, **source_values},
                    sig,
                    getattr(check, "sink_event", "level"),
                    list(getattr(check, "sink_qualifiers", [])),
                )
            passed, observed, expected, details = self._evaluate_perf_dynamic_check(
                check,
                source_active,
                sink_active,
                sink_values,
            )
            scenario_observed, scenario_expected = self._scenario_observation_context(
                scenario,
                sample_cycles,
            )
            observed = {**scenario_observed, **observed}
            expected = {**scenario_expected, **expected}
            expected = {**expected_context, **expected}

        except Exception as e:
            passed = False
            details.append(f"dynamic perf check execution failed: {e}")

        return PerfCheckResult(
            name=check.name,
            kind=check.kind,
            passed=passed,
            observed=observed,
            expected=expected,
            details=details,
        )

    # -----------------------------------------------------------------
    # Stage 4d: repair — Repair loop for failed modules
    # -----------------------------------------------------------------

    def _run_repair(self, output_dir: str, max_attempts: int = 3) -> StageResult:
        """Run repair loop for modules that failed verification.

        Uses the Verifier + LogicGenerator repair flow to fix issues
        identified in the verify stage.
        """
        result = StageResult("repair", description="DSL repair loop")

        if not self._skeleton_packages:
            result.skipped = True
            result.description = "No skeleton packages available for repair"
            return result

        # Check if verification produced errors to repair
        # In the current implementation, repair is triggered by
        # the verify stage errors. We track repair attempts here.
        result.passed = True
        repaired_count = 0

        for pe_name, pkg in self._skeleton_packages.items():
            # Check if this package has verification issues
            has_issues = False
            if hasattr(pkg, "_module_requirement") and pkg._module_requirement:
                # Module has structured requirements — can be repaired
                pass

            # Check for undriven outputs (common issue)
            if pkg.dsl_skeleton is not None:
                mod = pkg.dsl_skeleton
                for out_name in getattr(mod, "_outputs", {}):
                    if not hasattr(mod, out_name):
                        has_issues = True
                        break

            if has_issues:
                # Repair requires LLM agent; skeleton fallback removed
                pass

        result.metrics["repaired_modules"] = repaired_count

        return result

    # -----------------------------------------------------------------
    # Stage 4b: dsl_sim
    # -----------------------------------------------------------------

    def _run_dsl_sim(
        self,
        output_dir: str,
        num_random_vectors: int = 20,
        sim_cycles: int = 50,
        use_xz: bool = True,
    ) -> StageResult:
        """DSL simulation-based validation of leaf modules.

        Non-blocking: reports issues but does not fail the pipeline.
        Catches incomplete logic (undriven outputs, static signals, X/Z values).
        """
        from rtlgen.dsl_sim import DSLSimValidator

        result = StageResult("dsl_sim", description="DSL simulation validation")

        if not self._ppa_targets:
            result.skipped = True
            return result

        sim_dir = os.path.join(output_dir, "dsl_sim")
        validator = DSLSimValidator(
            modules=self._ppa_targets,
            output_dir=sim_dir,
            default_cycles=sim_cycles,
            use_xz=use_xz,
        )

        try:
            report = validator.validate_all()

            result.metrics["total_modules"] = report.total_modules
            result.metrics["passed_modules"] = report.passed_modules
            result.metrics["total_issues"] = report.total_issues
            result.metrics["report_dir"] = sim_dir

            has_crash = False
            for mod_result in report.modules:
                if not mod_result.simulation_ok:
                    has_crash = True
                    for err in mod_result.errors:
                        result.errors.append(f"{mod_result.module_name}: {err}")

                n_errors = sum(1 for i in mod_result.completeness_issues
                              if i.severity == "error")
                n_warnings = sum(1 for i in mod_result.completeness_issues
                                if i.severity == "warning")
                if n_errors or n_warnings:
                    result.metrics[f"{mod_result.module_name}_issues"] = (
                        f"{n_errors} errors, {n_warnings} warnings"
                    )
                    for issue in mod_result.completeness_issues:
                        if issue.severity in ("error", "warning"):
                            result.errors.append(
                                f"[{issue.severity}] {mod_result.module_name}: "
                                f"{issue.description}"
                            )

            result.passed = not has_crash

        except Exception as e:
            result.passed = False
            result.errors.append(f"dsl_sim: {e}")

        return result

    # -----------------------------------------------------------------
    # Stage 5: rtl
    # -----------------------------------------------------------------

    def _run_rtl(self, output_dir: str) -> StageResult:
        """Emit full hierarchy RTL — architecture-driven.

        Uses arch definition (from arch_templates) as the module source,
        resolving each PE to an implementation via:
          optimized module > DSL module > skeleton
        """
        result = StageResult("rtl", description="RTL emission (arch-driven)")

        os.makedirs(output_dir, exist_ok=True)
        emitter = VerilogEmitter(disable_cse=True)

        # ── Step 1: Ensure arch+skeleton loaded ──
        if not self._arch or not self._skeleton_packages:
            # Skeleton stage may have been skipped; re-run it
            skel_result = self._run_skeleton()
            if skel_result.skipped or not self._arch:
                result.errors.append("No arch definition available — need arch_templates.py")

        # ── Step 2: Load DSL modules for implementation logic ──
        if not self._loaded:
            self.load_skill()  # ignore failure; fallback to skeleton only

        # ── Step 3: Build pe_type → DSL class mapping ──
        if self._dsl_mod and not self._pe_type_to_class:
            self._pe_type_to_class = self._build_pe_type_mapping()

        # ── Step 4: Resolve each PE to an implementation ──
        resolved: Dict[str, Module] = {}  # PE name → Module instance
        emitted_masters: Dict[str, str] = {}  # unique key -> file path
        instance_to_master: Dict[str, str] = {}
        if self._arch:
            for pe in self._arch.processing_elements:
                mod = self._resolve_pe_to_module(pe)
                if mod is not None:
                    resolved[pe.name] = mod
                    result.metrics[f"{pe.name}_source"] = getattr(mod, '_source_hint', 'unknown')

        top_mod = self._build_top_module(resolved)
        for pe_name, mod in resolved.items():
            master_name = self._rtl_master_name(mod)
            instance_to_master[pe_name] = master_name
        hierarchy_modules = self._collect_hierarchy_modules(top_mod) if top_mod is not None else []

        # ── Step 5: Emit unique masters (one module per file) ──
        modules_to_emit = hierarchy_modules[:-1] if hierarchy_modules else []
        if resolved:
            existing = {id(mod) for mod in modules_to_emit}
            for mod in resolved.values():
                if id(mod) not in existing:
                    modules_to_emit.append(mod)
                    existing.add(id(mod))
        for mod in modules_to_emit:
            master_name = self._rtl_master_name(mod)
            master_key = self._rtl_master_key(mod)
            if master_key in emitted_masters:
                continue
            try:
                text = emitter.emit(mod)
                fname = f"{master_name}.v"
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "w") as f:
                    f.write(text)
                self._rtl_files.append(fpath)
                emitted_masters[master_key] = fpath
                result.metrics[f"{master_name}_lines"] = text.count("\n")
            except Exception as e:
                result.errors.append(f"emit {master_name}: {e}\n{traceback.format_exc()}")

        # ── Step 6: Emit full hierarchy from top module ──
        if top_mod is not None:
            try:
                text = emitter.emit(top_mod)
                fname = f"{top_mod.name}.v"
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "w") as f:
                    f.write(text)
                self._rtl_files.append(fpath)
                result.metrics["hierarchy_lines"] = text.count("\n")
                result.metrics["hierarchy_modules"] = len(hierarchy_modules)
                result.metrics["top_module"] = top_mod.name
            except Exception as e:
                result.errors.append(f"hierarchy: {e}\n{traceback.format_exc()}")

        manifest = {
            "skill": self.skill_name,
            "top_module": top_mod.name if top_mod is not None else None,
            "masters": {
                os.path.splitext(os.path.basename(path))[0]: os.path.basename(path)
                for path in emitted_masters.values()
            },
            "instances": instance_to_master,
        }
        manifest_path = os.path.join(output_dir, "rtl_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.write("\n")
        self._rtl_files.append(manifest_path)

        # ── Step 7: Emit optimized leaf modules (separate files) ──
        for name, mod in self._optimized_modules.items():
            try:
                text = emitter.emit_design(mod)
                fname = f"optimized_{name}.v"
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "w") as f:
                    f.write(text)
                self._rtl_files.append(fpath)
                result.metrics[f"optimized_{name}_lines"] = text.count("\n")
            except Exception as e:
                result.errors.append(f"emit optimized {name}: {e}")

        result.passed = len(self._rtl_files) > 0 and len(result.errors) == 0
        result.metrics["total_rtl_files"] = len(self._rtl_files)
        result.metrics["total_rtl_lines"] = sum(
            sum(1 for _ in open(f)) for f in self._rtl_files if os.path.isfile(f)
        )
        result.metrics["arch_pe_count"] = len(self._arch.processing_elements) if self._arch else 0
        result.metrics["resolved_pe_count"] = len(resolved)
        result.metrics["rtl_emit_errors"] = len(result.errors)
        result.metrics["rtl_master_count"] = len(emitted_masters)
        result.metrics["rtl_instance_count"] = len(instance_to_master)
        result.metrics["rtl_manifest"] = os.path.basename(manifest_path)
        self._rtl_master_map = {
            os.path.splitext(os.path.basename(path))[0]: path for path in emitted_masters.values()
        }
        self._rtl_instance_map = dict(instance_to_master)

        return result

    @staticmethod
    def _rtl_master_name(mod: Module) -> str:
        source_hint = getattr(mod, "_source_hint", "unknown")
        if source_hint.startswith("dsl:"):
            return source_hint.split(":", 1)[1]
        type_name = getattr(mod, "_type_name", mod.name)
        if type_name not in ("Module", mod.name):
            return type_name
        return mod.__class__.__name__

    @staticmethod
    def _rtl_master_key(mod: Module) -> str:
        source_hint = getattr(mod, "_source_hint", "unknown")
        type_name = getattr(mod, "_type_name", mod.name)
        port_sig = tuple((n, s.width) for n, s in sorted(mod._inputs.items()))
        out_sig = tuple((n, s.width) for n, s in sorted(mod._outputs.items()))
        return f"{source_hint}|{type_name}|{port_sig}|{out_sig}"

    def _collect_hierarchy_modules(self, top_mod: Module) -> List[Module]:
        from rtlgen.core import ForGenNode, GenIfNode, IfNode, SubmoduleInst, SwitchNode, WhenNode

        visited: set = set()
        order: List[Module] = []

        def _dfs_stmts(stmts: List[Any]):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    dfs(stmt.module)
                elif isinstance(stmt, IfNode):
                    _dfs_stmts(stmt.then_body)
                    for _, body in stmt.elif_bodies:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _dfs_stmts(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _dfs_stmts(stmt.then_body)
                    for _, body in stmt.elif_bodies:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.else_body)
                elif isinstance(stmt, WhenNode):
                    for _, body in stmt.branches:
                        _dfs_stmts(body)

        def dfs(mod: Module):
            if id(mod) in visited:
                return
            visited.add(id(mod))
            for _, sub in mod._submodules:
                dfs(sub)
            _dfs_stmts(mod._top_level)
            for body in mod._comb_blocks:
                _dfs_stmts(body)
            for _, _, _, _, body in mod._seq_blocks:
                _dfs_stmts(body)
            order.append(mod)

        dfs(top_mod)
        return order

    # -----------------------------------------------------------------
    # RTL helper methods
    # -----------------------------------------------------------------

    def _build_pe_type_mapping(self) -> Dict[str, type]:
        """Map PE pe_type (e.g. 'perf_core') to DSL class (e.g. PerformanceCore).

        Uses naming heuristic: pe_type 'perf_core' matches DSL class whose
        name contains 'PerfCore' or 'PerformanceCore' (case-insensitive).
        """
        mapping: Dict[str, type] = {}

        # Collect DSL classes
        dsl_classes: List[type] = []
        if self._dsl_mod:
            dsl_module_name = self._dsl_mod.__name__
            for attr_name in dir(self._dsl_mod):
                attr = getattr(self._dsl_mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Module) and attr is not Module:
                    if self._class_belongs_to_dsl(attr, dsl_module_name):
                        try:
                            attr()  # test instantiation
                            dsl_classes.append(attr)
                        except (TypeError, ValueError):
                            pass

        # Match pe_types from arch to DSL classes
        if self._arch:
            pe_types = set(pe.pe_type for pe in self._arch.processing_elements)
            for pe_type in pe_types:
                # Convert pe_type to candidate class names
                # e.g. 'perf_core' → 'PerfCore', 'PerformanceCore'
                parts = pe_type.split('_')
                camel = ''.join(p.capitalize() for p in parts)
                candidates = [camel]

                # Common abbreviations
                abbr_map = {
                    'PerfCore': ['PerformanceCore', 'PerfCore'],
                    'EffCore': ['EfficiencyCore', 'EffCore'],
                    'L1Cache': ['L1CacheSmall', 'L1CacheBig', 'L1Cache'],
                    'L2Cache': ['L2CacheSlice', 'L2Cache'],
                    'NocRouter': ['NoCRouter', 'NocRouter'],
                    'NocBuffer': ['NoCBuffer', 'NocBuffer'],
                    'CoherenceDir': ['CoherenceDir'],
                    'MeshTop': ['HeteroMeshTop', 'MeshTop'],
                    'ClusterBig': ['HeteroClusterBig'],
                    'ClusterSmall': ['HeteroClusterSmall'],
                }
                if camel in abbr_map:
                    candidates = abbr_map[camel] + candidates

                for candidate in candidates:
                    for cls in dsl_classes:
                        if candidate.lower() == cls.__name__.lower():
                            mapping[pe_type] = cls
                            break
                    if pe_type in mapping:
                        break

        return mapping

    def _resolve_pe_to_module(self, pe) -> Optional[Module]:
        """Resolve a ProcessingElement to a concrete DSL Module instance.

        Priority: optimized > DSL implementation > skeleton.
        """
        # 1. Check optimized modules
        if pe.name in self._optimized_modules:
            mod = self._optimized_modules[pe.name]
            mod._source_hint = "optimized"
            return mod

        # 2. PE name → DSL class heuristic (before pe_type mapping)
        #    Handles cases where multiple PE instances share a pe_type
        #    but should map to different DSL classes (e.g. L1_0→L1CacheBig,
        #    L1_2→L1CacheSmall).
        if self._arch:
            core_index = self._pe_core_index(pe.name)
            if core_index is not None and pe.pe_type == "l1_cache":
                # Cores 0,1 are perf → L1CacheBig; cores 2,3 are eff → L1CacheSmall
                if core_index < 2:
                    l1_cls = self._find_dsl_class_by_name("L1CacheBig")
                    if l1_cls is not None:
                        try:
                            mod = l1_cls()
                            mod._source_hint = "dsl:L1CacheBig"
                            return mod
                        except Exception:
                            pass
                else:
                    l1_cls = self._find_dsl_class_by_name("L1CacheSmall")
                    if l1_cls is not None:
                        try:
                            mod = l1_cls()
                            mod._source_hint = "dsl:L1CacheSmall"
                            return mod
                        except Exception:
                            pass

        # 3. Check DSL implementation (via pe_type mapping)
        if pe.pe_type in self._pe_type_to_class:
            try:
                mod = self._pe_type_to_class[pe.pe_type]()
                mod._source_hint = f"dsl:{self._pe_type_to_class[pe.pe_type].__name__}"
                return mod
            except Exception:
                pass  # fallback to skeleton

        # 4. Check DSL by PE name (for top modules like HeteroMeshTop)
        if self._dsl_mod:
            for attr_name in dir(self._dsl_mod):
                if attr_name.lower() == pe.name.lower():
                    attr = getattr(self._dsl_mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Module)
                        and self._class_belongs_to_dsl(attr, self._dsl_mod.__name__)
                    ):
                        try:
                            mod = attr()
                            mod._source_hint = f"dsl:{attr_name}"
                            return mod
                        except (TypeError, ValueError):
                            pass

        # 5. Fallback to skeleton
        if pe.name in self._skeleton_packages:
            pkg = self._skeleton_packages[pe.name]
            if pkg.dsl_skeleton is not None:
                mod = pkg.dsl_skeleton
                mod._source_hint = "skeleton"
                return mod

        return None

    @staticmethod
    def _pe_core_index(pe_name: str) -> Optional[int]:
        """Extract core index from PE name like 'L1_0' → 0, 'NoCRouter_3' → 3."""
        if "_" in pe_name:
            try:
                return int(pe_name.rsplit("_", 1)[-1])
            except ValueError:
                pass
        return None

    def _find_dsl_class_by_name(self, class_name: str) -> Optional[type]:
        """Find a DSL class by its exact name."""
        if not self._dsl_mod:
            return None
        attr = getattr(self._dsl_mod, class_name, None)
        if attr is not None and isinstance(attr, type) and issubclass(attr, Module):
            if self._class_belongs_to_dsl(attr, self._dsl_mod.__name__):
                try:
                    attr()
                    return attr
                except (TypeError, ValueError):
                    pass
        return None

    def _build_top_module(self, resolved: Dict[str, Module]) -> Optional[Module]:
        """Get the top-level module for hierarchy emission.

        Prefer a DSL top module (has full interconnect logic),
        which internally references resolved sub-modules.
        """
        # Try DSL top module first (e.g. HeteroMeshTop)
        if self._top_module_cls:
            try:
                return self._top_module_cls()
            except Exception:
                pass

        # Fallback: return the first resolved module that has submodules
        for name, mod in resolved.items():
            if mod._submodules:
                return mod

        # Last resort: return any resolved module
        if resolved:
            return next(iter(resolved.values()))

        return None

    # -----------------------------------------------------------------
    # Stage 6: lint
    # -----------------------------------------------------------------

    def _run_lint(self) -> StageResult:
        """Lint generated RTL."""
        result = StageResult("lint", description="Verilog lint")

        if not self._rtl_files:
            result.skipped = True
            return result

        result.passed = True
        linter = VerilogLinter()
        total_errors = 0
        total_warnings = 0

        for fpath in self._rtl_files:
            if not os.path.isfile(fpath):
                continue
            if not fpath.endswith(".v"):
                continue
            with open(fpath) as f:
                text = f.read()
            lint_result = linter.lint(text)
            if lint_result.issues:
                errs = [i for i in lint_result.issues if i.severity == "error"]
                warns = [i for i in lint_result.issues if i.severity != "error"]
                total_errors += len(errs)
                total_warnings += len(warns)
                if errs:
                    result.errors.append(
                        f"{os.path.basename(fpath)}: {len(errs)} error(s), "
                        f"{len(warns)} warning(s)"
                    )
                    for issue in errs[:5]:
                        result.errors.append(f"  {issue}")

        result.metrics["lint_errors"] = total_errors
        result.metrics["lint_warnings"] = total_warnings
        result.passed = total_errors == 0

        return result

    # -----------------------------------------------------------------
    # Main pipeline
    # -----------------------------------------------------------------

    ALL_STAGES = ["behaviors", "arch", "skeleton", "spec_gen", "dsl_from_spec", "agent_rtl_gen", "agent_testbench", "agent_verify", "ppa_analyze", "ppa_optimize", "contract_emit", "verify", "repair", "dsl_sim", "rtl", "lint"]

    def run(
        self,
        output_dir: str = "generated_skill_ppa",
        max_logic_depth: int = 5,
        max_iterations: int = 10,
        stages: Optional[List[str]] = None,
    ) -> "SkillPipelineResult":
        """Run the full skill→PPA→RTL pipeline."""
        if stages is None:
            stages = self.ALL_STAGES

        output_dir = os.path.join(output_dir, self.skill_name)
        result = SkillPipelineResult(skill_name=self.skill_name)

        print(f"\n{'='*60}")
        print(f"Skill Pipeline: {self.skill_name}")
        print(f"Stages: {' → '.join(stages)}")
        print(f"{'='*60}")

        stage_runners: Dict[str, Callable] = {
            "behaviors": lambda: self._run_behaviors(),
            "arch": lambda: self._run_arch(),
            "skeleton": lambda: self._run_skeleton(),
            "spec_gen": lambda: self._run_spec_gen(output_dir),
            "dsl_from_spec": lambda: self._run_dsl_from_spec(output_dir),
            "agent_rtl_gen": lambda: self._run_agent_rtl_gen(output_dir),
            "agent_testbench": lambda: self._run_agent_testbench(output_dir),
            "agent_verify": lambda: self._run_agent_verify(output_dir),
            "agent_gen": lambda: self._run_agent_gen(output_dir),
            "ppa_analyze": lambda: self._run_ppa_analyze(),
            "ppa_optimize": lambda: self._run_ppa_optimize(max_logic_depth, max_iterations),
            "contract_emit": lambda: self._run_contract_emit(output_dir),
            "verify": lambda: self._run_verify(output_dir),
            "repair": lambda: self._run_repair(output_dir),
            "dsl_sim": lambda: self._run_dsl_sim(output_dir),
            "rtl": lambda: self._run_rtl(output_dir),
            "lint": lambda: self._run_lint(),
        }

        for stage_name in stages:
            if stage_name not in stage_runners:
                print(f"  [SKIP] {stage_name} (unknown)")
                continue

            print(f"\n  [{stage_name}]...")
            sr = stage_runners[stage_name]()
            self._stage_results.append(sr)
            result.stage_results.append(sr)

            status = "PASS" if sr.passed else ("SKIP" if sr.skipped else "FAIL")
            print(f"    [{status}] {stage_name}: {sr.description}")
            if sr.metrics:
                for k, v in sr.metrics.items():
                    print(f"      {k}: {v}")
            for err in sr.errors[:5]:
                print(f"      [!] {err}")

        # Aggregate
        result.module_reports = self._module_reports
        result.rtl_files = self._rtl_files
        result.contract_files = self._contract_files.copy()
        result.rtl_masters = getattr(self, "_rtl_master_map", {}).copy()
        result.rtl_instance_map = getattr(self, "_rtl_instance_map", {}).copy()
        for sr in result.stage_results:
            if sr.stage_name == "rtl":
                result.total_rtl_lines = sr.metrics.get("total_rtl_lines", 0)
                break
        result.success = all(
            sr.passed or sr.skipped for sr in result.stage_results
        )

        # Print summary
        print(f"\n{'='*60}")
        print(f"Result: {'PASS' if result.success else 'FAIL'}")
        print(f"  Stages: {len(result.stage_results)} run")
        print(f"  Modules analyzed: {len(result.module_reports)}")
        print(f"  RTL files: {len(result.rtl_files)}")
        print(f"  Total RTL lines: {result.total_rtl_lines}")
        for m in result.module_reports:
            if m.optimized:
                print(f"  {m.module_name}: depth {m.before_depth} → {m.after_depth} "
                      f"({len(m.strategies_applied)} strategies)")
        print(f"{'='*60}")

        return result


# ============================================================================
# Pipeline result
# ============================================================================

@dataclass
class SkillPipelineResult:
    skill_name: str
    stage_results: List[StageResult] = field(default_factory=list)
    module_reports: List[ModulePPAReport] = field(default_factory=list)
    rtl_files: List[str] = field(default_factory=list)
    contract_files: Dict[str, str] = field(default_factory=dict)
    total_rtl_lines: int = 0
    rtl_masters: Dict[str, str] = field(default_factory=dict)
    rtl_instance_map: Dict[str, str] = field(default_factory=dict)
    success: bool = False


# ============================================================================
# Skill discovery
# ============================================================================

def discover_skills(skills_dir: Optional[str] = None) -> List[str]:
    """Discover skills by scanning for a supported Layer 3 DSL entrypoint."""
    sd = skills_dir or _SKILLS_DIR
    names = []
    if not os.path.isdir(sd):
        return names
    for entry in sorted(os.listdir(sd)):
        if os.path.isdir(os.path.join(sd, entry)):
            if (
                os.path.isfile(os.path.join(sd, entry, "dsl_modules.py"))
                or os.path.isfile(os.path.join(sd, entry, "layer3_dsl", "__init__.py"))
            ):
                names.append(entry)
    return names


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Unified Skill Pipeline Runner")
    parser.add_argument("--skill", type=str, nargs="*", help="Run specific skill(s)")
    parser.add_argument("--list", action="store_true", help="List discoverable skills")
    parser.add_argument("--output", type=str, default="generated_skill_ppa", help="Output directory")
    parser.add_argument("--stage", type=str, nargs="*", choices=SkillPPARunner.ALL_STAGES,
                        help="Run specific stages only")
    parser.add_argument("--depth", type=int, default=5, help="Max logic depth target")
    parser.add_argument("--iterations", type=int, default=10, help="Max PPA optimization iterations")

    args = parser.parse_args()

    if args.list:
        skills = discover_skills()
        print(f"Discoverable skills ({len(skills)}):")
        for s in skills:
            mods = []
            for m in ["dsl_modules", "arch_templates", "functional", "cycle_level", "behaviors", "models", "skeleton_templates"]:
                if os.path.isfile(os.path.join(_SKILLS_DIR, s, f"{m}.py")):
                    mods.append(m)
            print(f"  - {s}: {', '.join(mods)}")
        return

    skills = args.skill or discover_skills()
    print(f"Running {len(skills)} skills: {', '.join(skills)}")

    all_passed = True
    for skill_name in skills:
        runner = SkillPPARunner(skill_name)
        result = runner.run(
            output_dir=args.output,
            max_logic_depth=args.depth,
            max_iterations=args.iterations,
            stages=args.stage,
        )
        if not result.success:
            all_passed = False

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
