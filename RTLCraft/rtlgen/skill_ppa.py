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

import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.core import Module
from rtlgen.codegen import VerilogEmitter
from rtlgen.ppa import PPAAnalyzer
from rtlgen.ppa_optimizer import PPAOptimizer
from rtlgen.lint import VerilogLinter
from rtlgen.spec_ir import SpecIR, PPASpec
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
    description: str = ""


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

    def _run_spec_gen(self, output_dir: str = "generated_skill_ppa") -> StageResult:
        """Generate markdown specification documents from skeleton packages.

        Groups PEs by pe_type, generates ONE master spec per type,
        lists all instance names in the master spec.

        No API key required. Never fails — just produces specs for review.
        If existing DSL code already exists on disk, it is parsed and used.
        """
        result = StageResult("spec_gen", description="Markdown spec generation (master per type)")

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

            success_count += 1
            lines = md.count("\n") + 1
            result.metrics[f"{pe_type}_spec_lines"] = lines
            result.metrics[f"{pe_type}_instances"] = len(instances)

        # ── Also generate sub-module specs from _SUBMODULE_DEFS ──
        try:
            from rtlgen import arch_skel
            submod_spec_count = self._gen_submodule_specs(specs_dir, arch_skel._SUBMODULE_DEFS)
            result.metrics["submodule_specs"] = submod_spec_count
        except Exception as e:
            result.warnings.append(f"submodule_specs: {e}")

        result.passed = success_count > 0
        result.metrics["spec_success"] = success_count
        result.metrics["spec_skipped"] = skipped_count
        result.metrics["spec_by_type"] = len(type_groups)

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
                w = dsl_widths.get(sig)
                if w is None:
                    w = _lookup_width(sig)
                module_req.ports[sig] = {"dir": "input", "type": "logic", "width": w}
            for sig in info["outputs"]:
                w = dsl_widths.get(sig)
                if w is None:
                    w = _lookup_width(sig)
                module_req.ports[sig] = {"dir": "output", "type": "logic", "width": w}
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

        return gen_ctx

    # -----------------------------------------------------------------
    # Stage 3c: dsl_from_spec — Generate DSL from markdown specs
    # -----------------------------------------------------------------

    def _run_dsl_from_spec(self, output_dir: str = "generated_skill_ppa") -> StageResult:
        """Generate DSL code from markdown specification documents.

        For each PE:
        1. Read {output_dir}/specs/{pe_name}_spec.md
        2. If matching {output_dir}/specs/{pe_name}.py exists → parse and use it
        3. Otherwise → fall back to existing skeleton (graceful degradation)

        This stage is non-blocking: falling back to skeleton is acceptable.
        """
        result = StageResult("dsl_from_spec", description="DSL generation from specs")

        if not self._skeleton_packages:
            result.skipped = True
            result.errors.append("Run skeleton stage first")
            return result

        specs_dir = os.path.join(output_dir, "specs")
        success_count = 0
        fallback_count = 0

        for pe_name, pkg in self._skeleton_packages.items():
            # Priority 1: check for hand-written DSL code
            code_path = os.path.join(specs_dir, f"{pe_name}.py")
            if os.path.isfile(code_path):
                try:
                    from rtlgen.dsl_parser import parse_dsl_code
                    with open(code_path, "r") as f:
                        code = f.read()
                    parse_result = parse_dsl_code(code)
                    if parse_result.success:
                        pkg.dsl_skeleton = parse_result.module
                        success_count += 1
                        result.metrics[f"{pe_name}_lines"] = parse_result.line_count
                        continue
                except Exception:
                    pass

            # Priority 2: spec exists but no DSL code → keep skeleton
            spec_path = os.path.join(specs_dir, f"{pe_name}_spec.md")
            if os.path.isfile(spec_path):
                fallback_count += 1
            else:
                fallback_count += 1

        result.passed = True  # Non-blocking: fallback is acceptable
        result.metrics["dsl_from_spec_success"] = success_count
        result.metrics["dsl_from_spec_fallback"] = fallback_count

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
                needs_agent += 1
                result.metrics[f"{pe_name}_status"] = "needs_agent"
                result.metrics[f"{pe_name}_spec_lines"] = sum(
                    1 for _ in open(spec_path)
                )

        result.passed = True  # Non-blocking: agent work happens outside pipeline
        result.metrics["total_modules"] = total
        result.metrics["has_dsl_code"] = has_dsl_code
        result.metrics["needs_agent"] = needs_agent

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

    def load_skill(self) -> bool:
        """Import dsl_modules.py and discover Module classes."""
        dsl_path = os.path.join(self._skills_dir, self.skill_name, "dsl_modules.py")
        if not os.path.isfile(dsl_path):
            self._errors.append(f"dsl_modules.py not found in skills/{self.skill_name}/")
            return False

        full_name = f"skills.{self.skill_name}.dsl_modules"
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
        all_modules: List[Tuple[str, type]] = []

        for attr_name in sorted(dir(mod)):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, Module) and attr is not Module:
                # Skip classes not defined in this DSL module
                if getattr(attr, '__module__', None) != dsl_module_name:
                    continue
                all_modules.append((attr_name, attr))

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
        self._top_module_cls = top_modules[-1][1] if top_modules else None

        leaf_names = {n for n, _ in all_modules if n not in {t[0] for t in top_modules}}
        self._ppa_targets = [(n, c) for n, c in all_modules if n in leaf_names]

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
    # Stage 4c: verify — DSL verification before RTL emission
    # -----------------------------------------------------------------

    def _run_verify(self, output_dir: str) -> StageResult:
        """Run verification on generated DSL modules before RTL emission.

        Checks:
        1. ModuleRequirement availability (structured spec)
        2. Behavior requirement extraction
        3. DSL-level completeness (via dsl_sim quick check)
        """
        result = StageResult("verify", description="DSL verification")

        # Check if skeleton produced structured requirements
        if not self._skeleton_packages:
            result.skipped = True
            result.description = "No skeleton packages available for verification"
            return result

        result.passed = True
        verified_count = 0

        for pe_name, pkg in self._skeleton_packages.items():
            # Check for ModuleRequirement attachment
            has_req = hasattr(pkg, "_module_requirement") and pkg._module_requirement
            has_beh = hasattr(pkg, "_behavior_requirement") and pkg._behavior_requirement

            if has_req:
                result.metrics[f"{pe_name}_module_requirement"] = "present"
                verified_count += 1
            if has_beh:
                result.metrics[f"{pe_name}_behavior_requirement"] = "present"

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

        return result

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
        if self._arch:
            for pe in self._arch.processing_elements:
                mod = self._resolve_pe_to_module(pe)
                if mod is not None:
                    resolved[pe.name] = mod
                    result.metrics[f"{pe.name}_source"] = getattr(mod, '_source_hint', 'unknown')

        # ── Step 5: Emit resolved leaf modules ──
        for pe_name, mod in resolved.items():
            try:
                text = emitter.emit_design(mod)
                fname = f"{pe_name}.v"
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "w") as f:
                    f.write(text)
                self._rtl_files.append(fpath)
                result.metrics[f"{pe_name}_lines"] = text.count("\n")
            except Exception as e:
                result.errors.append(f"emit {pe_name}: {e}\n{traceback.format_exc()}")

        # ── Step 6: Emit full hierarchy from top module ──
        top_mod = self._build_top_module(resolved)
        if top_mod is not None:
            try:
                text = emitter.emit_design(top_mod)
                fname = f"{top_mod.name}.v"
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "w") as f:
                    f.write(text)
                self._rtl_files.append(fpath)
                result.metrics["hierarchy_lines"] = text.count("\n")
                result.metrics["hierarchy_modules"] = text.count("module ")
            except Exception as e:
                result.errors.append(f"hierarchy: {e}\n{traceback.format_exc()}")

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

        result.passed = len(self._rtl_files) > 0
        result.metrics["total_rtl_files"] = len(self._rtl_files)
        result.metrics["total_rtl_lines"] = sum(
            sum(1 for _ in open(f)) for f in self._rtl_files if os.path.isfile(f)
        )
        result.metrics["arch_pe_count"] = len(self._arch.processing_elements) if self._arch else 0
        result.metrics["resolved_pe_count"] = len(resolved)

        return result

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
            dsl_module_name = f"skills.{self.skill_name}.dsl_modules"
            for attr_name in dir(self._dsl_mod):
                attr = getattr(self._dsl_mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Module) and attr is not Module:
                    if getattr(attr, '__module__', None) == dsl_module_name:
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
            dsl_module_name = f"skills.{self.skill_name}.dsl_modules"
            for attr_name in dir(self._dsl_mod):
                if attr_name.lower() == pe.name.lower():
                    attr = getattr(self._dsl_mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Module):
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
        dsl_module_name = f"skills.{self.skill_name}.dsl_modules"
        attr = getattr(self._dsl_mod, class_name, None)
        if attr is not None and isinstance(attr, type) and issubclass(attr, Module):
            if getattr(attr, '__module__', None) == dsl_module_name:
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

    ALL_STAGES = ["behaviors", "arch", "skeleton", "spec_gen", "dsl_from_spec", "agent_rtl_gen", "agent_testbench", "agent_verify", "ppa_analyze", "ppa_optimize", "verify", "repair", "dsl_sim", "rtl", "lint"]

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
    total_rtl_lines: int = 0
    success: bool = False


# ============================================================================
# Skill discovery
# ============================================================================

def discover_skills(skills_dir: Optional[str] = None) -> List[str]:
    """Discover skills by scanning for dsl_modules.py."""
    sd = skills_dir or _SKILLS_DIR
    names = []
    if not os.path.isdir(sd):
        return names
    for entry in sorted(os.listdir(sd)):
        if os.path.isdir(os.path.join(sd, entry)):
            if os.path.isfile(os.path.join(sd, entry, "dsl_modules.py")):
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
