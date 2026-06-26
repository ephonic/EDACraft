"""
rtlgen.reference_extractor — Extract Structured Summaries from Reference DSL

Extracts structured ReferenceSummary objects from ReferenceCards returned
by SkillRetriever. Primary source is skills_index.yaml metadata; optionally
inspects actual DSL classes for port/parameter verification.

This avoids stuffing raw DSL code into agent prompts — instead provides
structured abstractions: design intent, interface patterns, state patterns,
logic patterns, and adaptation notes.

Reference: skills/plan_0525.md Section 4
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from rtlgen.gen_requirement import ReferenceSummary

try:
    from rtlgen.pattern_extractor import PatternExtractor, ModulePattern
    _PATTERN_EXTRACTOR_AVAILABLE = True
except ImportError:
    PatternExtractor = None
    ModulePattern = None
    _PATTERN_EXTRACTOR_AVAILABLE = False


class ReferenceExtractor:
    """Extract structured summaries from reference DSL modules in skills.

    Usage:
        extractor = ReferenceExtractor(skill_retriever)
        summaries = extractor.extract(reference_cards, task=task_dict)
    """

    def __init__(self, skill_retriever=None):
        self.skill_retriever = skill_retriever
        self._pattern_extractor = None
        if _PATTERN_EXTRACTOR_AVAILABLE and PatternExtractor is not None:
            self._pattern_extractor = PatternExtractor()
        # Cache of extracted code patterns: key -> ModulePattern
        self._pattern_cache: Dict[str, "ModulePattern"] = {}

    def extract(
        self,
        reference_cards: list,
        task: Optional[Dict[str, Any]] = None,
    ) -> List[ReferenceSummary]:
        """Extract summaries from a list of reference cards.

        Args:
            reference_cards: List[ReferenceCard] from SkillRetriever.retrieve()
            task: Optional task dict for context-aware adaptation notes

        Returns:
            List[ReferenceSummary] ordered by relevance score
        """
        summaries = []
        for card in reference_cards:
            summary = self.extract_from_card(card, task)
            summaries.append(summary)

        # Sort by relevance score (highest first)
        summaries.sort(key=lambda s: s.relevance_score, reverse=True)
        return summaries

    def extract_from_card(
        self,
        card,
        task: Optional[Dict[str, Any]] = None,
    ) -> ReferenceSummary:
        """Extract a single summary from one reference card.

        Maps ReferenceCard fields to ReferenceSummary fields:
        - behavior_tags + why_relevant → design_intent
        - interface_patterns → interface_pattern
        - control_patterns → logic_pattern["control"]
        - datapath_patterns → logic_pattern["datapath"]
        - summary → pseudo_dsl (first 4 sentences)
        - task context → adaptation_notes
        """
        # Design intent: why relevant + capability summary
        design_intent = list(card.why_relevant) if card.why_relevant else []

        if hasattr(card, "behavior_tags") and card.behavior_tags:
            design_intent.append(
                f"Capabilities: {', '.join(card.behavior_tags[:6])}"
            )

        if hasattr(card, "summary") and card.summary:
            # Add first sentence of summary as design intent
            first_sentence = card.summary.split(".")[0].strip()
            if first_sentence and first_sentence not in design_intent:
                design_intent.insert(0, first_sentence)

        # Interface pattern
        interface_pattern: Dict[str, List[str]] = {}
        if hasattr(card, "interface_patterns") and card.interface_patterns:
            interface_pattern["documented"] = card.interface_patterns

        if hasattr(card, "source_class") and card.source_class:
            interface_pattern["source_class"] = [card.source_class]

        # State pattern
        state_pattern: List[str] = []
        if hasattr(card, "state_patterns") and card.state_patterns:
            state_pattern = list(card.state_patterns)

        if not state_pattern and hasattr(card, "summary") and card.summary:
            state_pattern = self._infer_state_from_summary(card.summary)

        # Logic pattern
        logic_pattern: Dict[str, List[str]] = {}
        if hasattr(card, "control_patterns"):
            logic_pattern["control"] = card.control_patterns[:5]
        if hasattr(card, "datapath_patterns"):
            logic_pattern["datapath"] = card.datapath_patterns[:5]

        # Pseudo-DSL: extract key sentences from summary
        pseudo_dsl = []
        if hasattr(card, "summary") and card.summary:
            sentences = [s.strip() for s in card.summary.split(".") if s.strip()]
            pseudo_dsl = sentences[:4]

        # Add structural hints from control patterns
        for ctrl in logic_pattern.get("control", []):
            if "round_robin" in ctrl.lower():
                pseudo_dsl.append("round-robin pointer register with wrap-around update")
            elif "fifo" in ctrl.lower():
                pseudo_dsl.append("FIFO with head/tail pointers and full/empty detection")
            elif "scoreboard" in ctrl.lower() or "busy" in ctrl.lower():
                pseudo_dsl.append("busy-bit table with set/clear per operation")
            elif "arbiter" in ctrl.lower():
                pseudo_dsl.append("priority encoder or round-robin arbiter")
            elif "fsm" in ctrl.lower() or "state machine" in ctrl.lower():
                pseudo_dsl.append("FSM with idle/active/done states")

        # Adaptation notes
        adaptation_notes = self._build_adaptation_notes(card, task)

        # Caution
        caution = []
        if hasattr(card, "caution") and card.caution:
            caution = list(card.caution)
        caution.append("Reference only — generate fresh implementation for current ports")

        # Extract code patterns from actual DSL source if available
        code_patterns = self._extract_code_patterns(card)

        # Extract actual code snippets from DSL source
        code_snippets = self._extract_code_snippets(card)

        # Enrich state_pattern from code extraction
        if code_patterns and not state_pattern:
            for sv in code_patterns.get("state_vars", []):
                state_pattern.append(
                    f"{sv['kind']} {sv['name']} (width={sv['width']})"
                )

        # Enrich logic_pattern from code extraction
        if code_patterns:
            if code_patterns.get("summary_patterns"):
                logic_pattern["extracted_summary"] = code_patterns["summary_patterns"]
            if code_patterns.get("has_fsm"):
                logic_pattern["fsm"] = code_patterns["fsm_summary"]
            if code_patterns.get("handshake_summary"):
                logic_pattern["handshakes"] = code_patterns["handshake_summary"]
            # Derived boolean flags for generation guidance
            logic_pattern["derived_flags"] = [
                k for k, v in code_patterns.items()
                if k.startswith("has_") and v
            ]

        return ReferenceSummary(
            module_name=getattr(card, "name", "unknown"),
            source_file=getattr(card, "source_file", ""),
            relevance_score=getattr(card, "relevance", 0.0),
            kind=getattr(card, "kind", "module"),
            design_intent=design_intent,
            interface_pattern=interface_pattern,
            state_pattern=state_pattern,
            logic_pattern=logic_pattern,
            pseudo_dsl=pseudo_dsl,
            adaptation_notes=adaptation_notes,
            caution=caution,
            code_patterns=code_patterns,
            code_snippets=code_snippets,
        )

    @staticmethod
    def _infer_state_from_summary(summary: str) -> List[str]:
        """Infer state patterns from summary text."""
        patterns = []
        summary_lower = summary.lower()

        state_keywords = {
            "register": "register-based state",
            "mask": "bitmask state",
            "pointer": "pointer/counter state",
            "counter": "counter state",
            "fifo": "FIFO queue state",
            "queue": "queue state",
            "buffer": "buffer state",
            "table": "table/lookup state",
            "array": "array state",
            "pc": "program counter state",
            "active": "active/inactive state tracking",
        }

        for keyword, pattern in state_keywords.items():
            if keyword in summary_lower:
                patterns.append(pattern)

        return patterns

    @staticmethod
    def _build_adaptation_notes(
        card, task: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Build adaptation notes from card and task context."""
        notes = []

        if task:
            task_name = task.get("name", "")
            card_name = getattr(card, "name", "")
            if task_name and card_name:
                notes.append(
                    f"Reference '{card_name}' may be adapted for task '{task_name}'"
                )

            # Note keyword mismatches
            task_keywords = task.get("behavior_tags", []) + task.get("keywords", [])
            card_behaviors = getattr(card, "behavior_tags", [])
            matched = set(task_keywords) & set(card_behaviors)
            unmatched = set(task_keywords) - set(card_behaviors)

            if unmatched:
                notes.append(
                    f"Current task requires: {', '.join(list(unmatched)[:3])} "
                    f"(not present in reference)"
                )

        # Always warn about interface differences
        notes.append("Verify signal names match current skeleton port definitions")
        notes.append("Adapt parameter names and widths to current ModuleRequirement")
        notes.append("Do not copy code verbatim; adapt to current context")

        return notes

    def _extract_code_patterns(self, card) -> Dict[str, Any]:
        """Extract structural code patterns from actual DSL source.

        Uses PatternExtractor to parse the DSL module class from the
        source file, then returns a simplified dict for generation.

        Returns empty dict if source extraction is not available.
        """
        if not _PATTERN_EXTRACTOR_AVAILABLE or self._pattern_extractor is None:
            return {}

        # Get source class name and file from the card
        source_class = getattr(card, "source_class", None)
        source_file = getattr(card, "source_file", "")

        if not source_class or not source_file:
            return {}

        # Check cache first
        cache_key = f"{source_file}:{source_class}"
        if cache_key in self._pattern_cache:
            mp = self._pattern_cache[cache_key]
        else:
            mp = self._pattern_extractor.extract_from_file(source_file, source_class)
            if mp:
                self._pattern_cache[cache_key] = mp

        if mp is None:
            return {}

        # Convert ModulePattern to a generation-friendly dict
        result: Dict[str, Any] = {}

        # Port list with widths
        result["ports"] = [
            {"name": p.name, "width": p.width, "direction": p.direction}
            for p in mp.ports
        ]

        # State variables
        result["state_vars"] = [
            {"name": s.name, "kind": s.kind, "width": s.width, "size": s.size}
            for s in mp.state_vars
        ]

        # Combinational logic summaries
        result["comb_assignments"] = []
        for block in mp.comb_blocks:
            result["comb_assignments"].extend(block.assignments[:10])

        # Sequential logic summaries
        result["seq_assignments"] = []
        for block in mp.seq_blocks:
            result["seq_assignments"].extend(block.assignments[:10])

        # Derived boolean flags
        result["has_round_robin"] = mp.has_round_robin
        result["has_fifo"] = mp.has_fifo
        result["has_scoreboard"] = mp.has_scoreboard
        result["has_pipeline"] = mp.has_pipeline
        result["has_fsm"] = mp.has_fsm
        result["has_valid_ready"] = mp.has_valid_ready

        # FSM summary
        if mp.fsm:
            result["fsm_summary"] = {
                "state_reg": mp.fsm.state_reg,
                "num_transitions": mp.fsm.num_states,
            }

        # Handshake summary
        result["handshake_summary"] = [
            {"valid": h.valid_signal, "ready": h.ready_signal,
             "fire": h.fire_condition}
            for h in mp.handshakes
        ]

        # Summary patterns
        result["summary_patterns"] = mp.summary_patterns

        # Docstring as design intent
        if mp.docstring:
            result["docstring"] = mp.docstring

        return result

    def _extract_code_snippets(self, card) -> Dict[str, str]:
        """Extract actual DSL code snippets from reference source file.

        Returns a dict of named code snippets (e.g., 'comb_logic', 'seq_logic',
        'state_decl', 'port_decl') as actual Python DSL source text.

        Returns empty dict if source is not available or parsing fails.
        """
        source_file = getattr(card, "source_file", "")
        source_class = getattr(card, "source_class", "")
        if not source_file or not source_class:
            return {}

        if not os.path.isfile(source_file):
            return {}

        try:
            with open(source_file, "r") as f:
                source_lines = f.readlines()
        except Exception:
            return {}

        # Find the class definition and extract key sections
        snippets: Dict[str, str] = {}
        class_start = -1
        class_indent = 0

        for i, line in enumerate(source_lines):
            stripped = line.rstrip()
            if f"class {source_class}" in stripped or f"class {source_class}(" in stripped:
                class_start = i
                class_indent = len(line) - len(line.lstrip())
                break

        if class_start < 0:
            return snippets

        # Extract state variable declarations (Reg/Wire/Array declarations)
        state_lines = []
        comb_lines = []
        seq_lines = []
        in_comb = False
        in_seq = False
        in_init = False
        base_indent = class_indent + 4  # typical class body indent

        for i in range(class_start + 1, len(source_lines)):
            line = source_lines[i]
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            # Detect section context managers
            if "with self.comb" in stripped:
                in_comb = True
                in_seq = False
                comb_lines.append(stripped)
                continue
            elif "with self.seq" in stripped:
                in_seq = True
                in_comb = False
                seq_lines.append(stripped)
                continue
            elif stripped.startswith("def __init__"):
                in_init = True
                in_comb = False
                in_seq = False
                continue
            elif stripped.startswith("def ") and indent <= base_indent:
                in_init = False
                in_comb = False
                in_seq = False
                continue
            elif indent <= class_indent and stripped:
                # End of class
                break

            # Collect lines by context
            if in_init and stripped and not stripped.startswith("#"):
                # State declarations: Reg/Wire/Array assignments
                if any(kw in stripped for kw in ["Reg(", "Wire(", "Array("]):
                    state_lines.append(stripped)
            elif in_comb and stripped:
                comb_lines.append(stripped)
            elif in_seq and stripped:
                seq_lines.append(stripped)

        # Store snippets (limit to avoid excessive prompt size)
        if state_lines:
            snippets["state_decl"] = "\n".join(state_lines[:12])
        if comb_lines:
            snippets["comb_logic"] = "\n".join(comb_lines[:20])
        if seq_lines:
            snippets["seq_logic"] = "\n".join(seq_lines[:20])

        return snippets

    def extract_for_task(
        self,
        pe_type: str,
        task: Dict[str, Any],
        behavior_req: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[ReferenceSummary]:
        """Convenience method: retrieve and extract in one call.

        Args:
            pe_type: PE type string (e.g., "sm_wrapper")
            task: Task dict from _TEMPLATE_STEPS
            behavior_req: Optional behavior requirements dict
            top_k: Number of references to retrieve

        Returns:
            List[ReferenceSummary] for the task
        """
        if self.skill_retriever is None:
            return []

        cards = self.skill_retriever.retrieve_for_task(
            pe_type=pe_type,
            task=task,
            behavior_req=behavior_req,
            top_k=top_k,
        )

        return self.extract(cards, task)
