"""
rtlgen.agent_dsl_generator — Agent-Oriented DSL Generation Wrapper

Bridges the deterministic SpecIR/ArchitectureIR -> DSL generator with the
existing logic repair flow so agent-driven stages have a stable entry point.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rtlgen.arch_planner import ArchitecturePlanner
from rtlgen.core import Module
from rtlgen.dsl_gen import DSLGenerator
from rtlgen.logic_generator import LogicGenerator
from rtlgen.spec_extractor import SpecCompleter
from rtlgen.spec_ir import ArchitectureIR, SpecIR


@dataclass
class AgentDSLGenerationResult:
    """Result bundle for agent-oriented DSL generation."""
    module: Optional[Module]
    spec: Optional[SpecIR] = None
    arch: Optional[ArchitectureIR] = None
    used_deterministic_generator: bool = False
    issues: List[str] = field(default_factory=list)
    repair_attempts: int = 0


class AgentDSLGenerator:
    """Stable entry point for agent-guided DSL generation.

    The current implementation always starts from the deterministic generator.
    Future agent passes can then repair or enrich the generated module.
    """

    def __init__(self, logic_generator: Optional[LogicGenerator] = None):
        self.logic_generator = logic_generator or LogicGenerator()

    def generate(
        self,
        spec: SpecIR,
        arch: Optional[ArchitectureIR] = None,
    ) -> AgentDSLGenerationResult:
        completed = SpecCompleter.complete(copy.deepcopy(spec))
        planned = copy.deepcopy(arch) if arch is not None else ArchitecturePlanner(completed).plan()
        module = DSLGenerator(completed, planned).generate()
        return AgentDSLGenerationResult(
            module=module,
            spec=completed,
            arch=planned,
            used_deterministic_generator=True,
        )

    def generate_from_context(
        self,
        gen_ctx: Any,
        spec: SpecIR,
        arch: Optional[ArchitectureIR] = None,
    ) -> AgentDSLGenerationResult:
        """Generate a deterministic module using explicit context + spec."""
        result = self.generate(spec, arch=arch)
        if result.module is not None:
            contexts = list(getattr(result.module, "_generation_contexts", []))
            contexts.append(gen_ctx)
            result.module._generation_contexts = contexts
        return result

    def repair(self, module: Module, repair_context: Any) -> Dict[str, Any]:
        """Delegate repair generation to the existing LogicGenerator."""
        if self.logic_generator is None:
            return {}
        try:
            return self.logic_generator.repair(module, repair_context) or {}
        except Exception as exc:
            return {"errors": [str(exc)]}
