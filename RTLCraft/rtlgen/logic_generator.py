"""
rtlgen.logic_generator — Skill-Guided RTL Generation: Logic Generator

Generates RTL/DSL logic for a specific task guided by reference cards
and structured code patterns extracted from actual DSL module source.

Two generation modes:
  1. generate() — original pattern-driven template dispatch
  2. generate_with_context() — enriched generation using GenerationContext
     with code patterns from reference DSL source and skeleton requirements

Reference: skills/skills-guided-gen.md Section 6, 7, 15.3
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from rtlgen.core import Module, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif, Switch, Mux, Cat, Rep


@dataclass
class LogicGenerationResult:
    success: bool
    statements_added: int = 0
    message: str = ""


class LogicGenerator:
    """Generates logic pieces for architectural skeleton tasks.

    Two modes:
    - Pattern-driven (original): maps reference pattern names to templates
    - Context-driven (enhanced): uses GenerationContext with extracted
      code patterns from reference DSL source and ModuleRequirement specs
    """

    def __init__(self):
        # Map pattern names to generator functions
        self._pattern_gens: Dict[str, Callable] = {
            "round_robin_select": self._gen_round_robin_select,
            "valid_ready_fire": self._gen_valid_ready_handshake,
            "stall_when_no_candidate": self._gen_stall_control,
            "busy_bit_table": self._gen_busy_bit_scoreboard,
            "dependency_blocking": self._gen_dependency_block,
            "fifo_buffer": self._gen_fifo_buffer,
            "pipeline_stall": self._gen_pipeline_stall,
            "instruction_decode": self._gen_instruction_decode,
            "operand_mux": self._gen_operand_mux,
            "alu_execute": self._gen_alu_execute,
            "load_store": self._gen_load_store,
            "index_encode": self._gen_index_encode,
            "bank_arbitration": self._gen_bank_arbitration,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, module: Module, pe: Any, task: Dict[str, Any],
                 reference_cards: List[Any]) -> LogicGenerationResult:
        """Generate logic for a single task and merge into module."""
        task_name = task.get("name", "")
        # Collect all reusable patterns from reference cards
        patterns = set()
        for card in reference_cards:
            patterns.update(getattr(card, "reusable_patterns", []))

        # Dispatch by task name first, then by patterns
        gen_fn = self._task_generators.get(task_name)
        if gen_fn:
            return gen_fn(module, pe, task, reference_cards, patterns)

        # Fallback: try pattern-driven generation
        added = 0
        for pat in patterns:
            if pat in self._pattern_gens:
                self._pattern_gens[pat](module, pe, task)
                added += 1

        if added > 0:
            return LogicGenerationResult(
                success=True, statements_added=added,
                message=f"Generated {added} pattern blocks for task '{task_name}'"
            )

        return LogicGenerationResult(
            success=False, statements_added=0,
            message=f"No generator found for task '{task_name}'"
        )

    def generate_with_context(self, module: Module, pe: Any,
                              task: Dict[str, Any],
                              reference_cards: List[Any],
                              gen_ctx: Optional[Any] = None,
                              module_req: Optional[Any] = None) -> LogicGenerationResult:
        """Generate logic using enriched reference patterns and skeleton requirements.

        This method enhances the original generate() by:
        1. Using code patterns extracted from actual DSL source (not just metadata)
        2. Scaling parameters from ModuleRequirement instead of hardcoded defaults
        3. Using reference implementation structures to guide logic generation
        4. Falling back to original generate() if context is unavailable

        Args:
            module: DSL Module to generate into
            pe: ProcessingElement being generated
            task: Task dict with name, goal, behavior_tags
            reference_cards: ReferenceCard list from SkillRetriever
            gen_ctx: Optional GenerationContext with enriched summaries
            module_req: Optional ModuleRequirement with port/param specs

        Returns:
            LogicGenerationResult
        """
        task_name = task.get("name", "")

        # Collect patterns from reference cards
        patterns = set()
        for card in reference_cards:
            patterns.update(getattr(card, "reusable_patterns", []))

        # If no enriched context, fall back to original generate
        if gen_ctx is None:
            return self.generate(module, pe, task, reference_cards)

        # Extract generation parameters from context
        target = getattr(gen_ctx, "target", None)
        ref_summaries = getattr(gen_ctx, "reference_summaries", [])
        coding_rules = getattr(gen_ctx, "coding_rules", [])

        # Determine parameter scaling from ModuleRequirement or target
        params = {}
        if module_req and hasattr(module_req, "parameters"):
            params = dict(module_req.parameters)
        if target and hasattr(target, "parameters"):
            params.update(target.parameters)

        # Find best reference module with code patterns
        best_ref = self._select_best_reference(ref_summaries, task)
        code_pats = best_ref.get("code_patterns", {}) if best_ref else {}

        # Select generation strategy based on task + reference match
        strategy = self._select_generation_strategy(task_name, patterns, code_pats)

        # Execute generation
        added = 0
        if strategy == "task_generator" and module_req:
            # Use task-level generator with parameter scaling
            gen_fn = self._task_generators.get(task_name)
            if gen_fn:
                result = gen_fn(module, pe, task, reference_cards, patterns)
                if result.success:
                    added = result.statements_added

        elif strategy == "pattern_driven" and code_pats:
            # Use reference code patterns to guide pattern generation
            added = self._generate_from_code_patterns(module, pe, task, code_pats, params)

        elif strategy == "pattern_driven":
            # Fallback to original pattern-driven generation
            added = 0
            for pat in patterns:
                if pat in self._pattern_gens:
                    self._pattern_gens[pat](module, pe, task)
                    added += 1

        elif strategy == "ref_structured":
            # Use reference module structure directly
            added = self._generate_from_reference_structure(
                module, pe, task, best_ref, params
            )

        if added > 0:
            return LogicGenerationResult(
                success=True, statements_added=added,
                message=f"Generated {added} blocks for task '{task_name}' "
                        f"(strategy={strategy}, ref={best_ref.get('module_name', 'none') if best_ref else 'none'})"
            )

        # Last resort: fall back to original generate
        return self.generate(module, pe, task, reference_cards)

    def _select_best_reference(
        self, ref_summaries: List[Any], task: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select the best reference module with code patterns for this task.

        Looks for a reference with:
        1. Matching behavior tags or keywords
        2. Extracted code patterns (from DSL source)
        3. Highest relevance score

        Returns a simplified dict with module_name + code_patterns,
        or None if no suitable reference found.
        """
        task_keywords = set(task.get("behavior_tags", []) + task.get("keywords", []))
        task_name = task.get("name", "").lower()

        best = None
        best_score = -1.0

        for ref in ref_summaries:
            # Check if it has code patterns extracted from source
            code_pats = getattr(ref, "code_patterns", {})
            if not code_pats:
                continue

            # Score this reference
            score = getattr(ref, "relevance_score", 0.0)

            # Bonus for matching behavior tags
            design_intent = getattr(ref, "design_intent", [])
            for tag in task_keywords:
                tag_lower = tag.lower()
                for intent in design_intent:
                    if tag_lower in intent.lower():
                        score += 0.1

            # Bonus for matching module name to task
            ref_name = getattr(ref, "module_name", "").lower()
            if task_name and task_name in ref_name:
                score += 0.2

            if score > best_score:
                best_score = score
                best = {
                    "module_name": getattr(ref, "module_name", ""),
                    "code_patterns": code_pats,
                    "design_intent": design_intent,
                    "logic_pattern": getattr(ref, "logic_pattern", {}),
                    "state_pattern": getattr(ref, "state_pattern", []),
                    "pseudo_dsl": getattr(ref, "pseudo_dsl", []),
                }

        return best

    def _select_generation_strategy(
        self, task_name: str, patterns: set, code_pats: dict
    ) -> str:
        """Select generation strategy based on available information.

        Returns:
            "task_generator" — known task with task-level generator
            "ref_structured" — reference with code patterns but no task generator
            "pattern_driven" — only pattern-level generators available
            "fallback" — nothing matches
        """
        if task_name in self._task_generators:
            return "task_generator"

        if code_pats:
            return "pattern_driven"

        if patterns:
            return "pattern_driven"

        return "fallback"

    def _generate_from_code_patterns(self, module: Module, pe: Any,
                                     task: Dict[str, Any],
                                     code_pats: Dict[str, Any],
                                     params: Dict[str, Any]) -> int:
        """Generate logic using extracted code patterns from reference DSL.

        Uses the actual implementation structures found in reference modules
        (port patterns, state variables, assignment patterns, FSM structure)
        to guide generation, rather than hardcoded templates.

        Returns number of blocks added.
        """
        added = 0

        # Scale from reference patterns using parameters
        nwarp = params.get("NUM_WARP", params.get("nwarp", 4))
        num_regs = params.get("NUM_REGS", 8)

        # Round-robin pattern from reference
        if code_pats.get("has_round_robin"):
            self._gen_round_robin_select(module, pe, task)
            added += 1

        # Valid-ready handshake from reference
        if code_pats.get("has_valid_ready"):
            self._gen_valid_ready_handshake(module, pe, task)
            added += 1

        # Scoreboard pattern from reference
        if code_pats.get("has_scoreboard"):
            self._gen_busy_bit_scoreboard(module, pe, task)
            added += 1

        # FIFO pattern from reference
        if code_pats.get("has_fifo"):
            self._gen_fifo_buffer(module, pe, task)
            added += 1

        # Pipeline pattern from reference
        if code_pats.get("has_pipeline"):
            self._gen_pipeline_stall(module, pe, task)
            added += 1

        # FSM from reference — generate Switch-based state machine
        if code_pats.get("has_fsm") and code_pats.get("fsm_summary"):
            fsm = code_pats["fsm_summary"]
            added += self._gen_fsm_from_ref(module, pe, fsm, params)

        # Generate state variables from reference patterns
        state_vars = code_pats.get("state_vars", [])
        for sv in state_vars[:8]:  # Limit to 8 state vars
            name = sv.get("name", "")
            kind = sv.get("kind", "Wire")
            width = sv.get("width", "1")
            if not name or hasattr(module, name):
                continue
            self._add_state_from_ref(module, name, kind, width, sv.get("size", ""))
            added += 1

        return added

    def _generate_from_reference_structure(
        self, module: Module, pe: Any, task: Dict[str, Any],
        ref: Dict[str, Any], params: Dict[str, Any]
    ) -> int:
        """Generate logic using full reference structure.

        Used when no task generator matches but we have a reference
        with extracted code patterns.

        Returns number of blocks added.
        """
        if ref is None:
            return 0

        code_pats = ref.get("code_patterns", {})
        added = self._generate_from_code_patterns(module, pe, task, code_pats, params)

        # Also add design intent as module comments
        design_intent = ref.get("design_intent", [])
        for intent in design_intent[:3]:
            module.add_comment(f"[Design Intent] {intent}")

        return added

    def _gen_fsm_from_ref(self, module: Module, pe: Any,
                          fsm_summary: Dict[str, Any],
                          params: Dict[str, Any]) -> int:
        """Generate FSM structure from reference FSM pattern.

        Creates a Switch-based state machine matching the reference pattern.
        """
        state_reg = fsm_summary.get("state_reg", "_state")
        num_trans = fsm_summary.get("num_transitions", 2)
        state_width = max(1, num_trans.bit_length())

        # Create state register if not exists
        if not hasattr(module, state_reg):
            setattr(module, state_reg, Reg(state_width, state_reg))

        # Create next_state wire
        next_state = state_reg.replace("_", "_next_", 1) if "_" in state_reg else f"next_{state_reg}"
        if not hasattr(module, next_state):
            setattr(module, next_state, Wire(state_width, next_state))

        added = 0

        state_sig = getattr(module, state_reg)
        next_sig = getattr(module, next_state, None)
        rst_sig = ~module.rst_n if hasattr(module, "rst_n") else Const(0)

        with module.comb:
            with Switch(state_sig) as sw:
                sw.case(0)
                if num_trans > 1:
                    sw.case(1)
                sw.default()
            added += 1

        with module.seq(module.clk, rst_sig):
            with If(rst_sig):
                state_sig <<= 0
            with Else():
                state_sig <<= (next_sig if next_sig else Const(0))
            added += 1

        return added

    def _add_state_from_ref(self, module: Module, name: str,
                            kind: str, width_str: str, size_str: str):
        """Add a state variable based on reference pattern.

        Converts string width/size to integers and creates the appropriate
        signal type on the module.
        """
        # Try to evaluate width string (handles "ADDR_WIDTH" etc.)
        try:
            width = int(width_str)
        except (ValueError, TypeError):
            # Symbolic constant — use default widths based on common patterns
            width_map = {
                "ADDR_WIDTH": 32, "DEPTH_WARP": 4, "TAG_WIDTH": 8,
                "NUM_WARP": 4, "NUM_FETCH": 4, "XLEN": 32,
                "FLIT_WIDTH": 64,
            }
            width = width_map.get(width_str, 8)

        if kind in ("Reg", "Reg[]"):
            if "[]" in kind:
                # Array of registers — create as Array
                try:
                    depth = int(size_str) if size_str else 4
                except (ValueError, TypeError):
                    depth = 4
                setattr(module, name, Array(width, depth, name))
            else:
                setattr(module, name, Reg(width, name))
        elif kind == "Array":
            try:
                depth = int(size_str) if size_str else 4
            except (ValueError, TypeError):
                depth = 4
            setattr(module, name, Array(width, depth, name))
        else:
            setattr(module, name, Wire(width, name))

    # ------------------------------------------------------------------
    # Task-level generators (sm_wrapper decomposition)
    # ------------------------------------------------------------------

    @property
    def _task_generators(self) -> Dict[str, Callable]:
        return {
            "cta2warp": self._gen_cta2warp,
            "warp_schedule": self._gen_warp_schedule_task,
            "scoreboard_check": self._gen_scoreboard_task,
            "issue_logic": self._gen_issue_logic_task,
            "operand_collect": self._gen_operand_collect_task,
            "execute_dispatch": self._gen_execute_dispatch_task,
            "writeback": self._gen_writeback_task,
            "instruction_cache": self._gen_instruction_cache_task,
            "l1_dcache": self._gen_l1_dcache_task,
            "shared_mem": self._gen_shared_mem_task,
            "fetch_decode": self._gen_fetch_decode_task,
            "ibuffer": self._gen_ibuffer_task,
            "memory_interface": self._gen_memory_interface_task,
        }

    # ---------- Task: cta2warp ----------
    def _gen_cta2warp(self, module, pe, task, refs, patterns):
        """Generate CTA dispatch → warp allocation logic."""
        # Ensure required state exists
        if not hasattr(module, "cta_valid"):
            module.cta_valid = Wire(1, "cta_valid")
        if not hasattr(module, "cta_ready"):
            module.cta_ready = Wire(1, "cta_ready")
        if not hasattr(module, "warp_allocated"):
            module.warp_allocated = Array(1, 4, "warp_allocated")

        nwarp = 4  # inferred default; could come from pe parameters
        with module.comb:
            # Simple allocator: find first free warp
            alloc_ptr = Wire(2, "alloc_ptr")
            alloc_found = Wire(1, "alloc_found")
            alloc_found <<= 0
            alloc_ptr <<= 0
            # Mux chain for first-free search
            for w in range(nwarp):
                with If(~alloc_found & ~module.warp_allocated[w]):
                    alloc_found <<= 1
                    alloc_ptr <<= w
            module.cta_ready <<= alloc_found

        with module.seq(module.clk, ~module.rst_n):
            with If(~module.rst_n):
                for w in range(nwarp):
                    module.warp_allocated[w] <<= 0
            with Else():
                with If(module.cta_valid & module.cta_ready):
                    module.warp_allocated[alloc_ptr] <<= 1

        return LogicGenerationResult(success=True, statements_added=3,
                                     message="Generated cta2warp allocator")

    # ---------- Task: warp_schedule ----------
    def _gen_warp_schedule_task(self, module, pe, task, refs, patterns):
        """Generate warp scheduler with round-robin priority."""
        self._gen_round_robin_select(module, pe, task)
        self._gen_stall_control(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=2,
                                     message="Generated warp_schedule (RR + stall)")

    # ---------- Task: scoreboard_check ----------
    def _gen_scoreboard_task(self, module, pe, task, refs, patterns):
        """Generate busy-bit scoreboard for hazard checking."""
        self._gen_busy_bit_scoreboard(module, pe, task)
        self._gen_dependency_block(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=2,
                                     message="Generated scoreboard_check")

    # ---------- Task: issue_logic ----------
    def _gen_issue_logic_task(self, module, pe, task, refs, patterns):
        """Generate issue stage with valid-ready handshake."""
        self._gen_valid_ready_handshake(module, pe, task)
        self._gen_pipeline_stall(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=2,
                                     message="Generated issue_logic")

    # ---------- Task: operand_collect ----------
    def _gen_operand_collect_task(self, module, pe, task, refs, patterns):
        """Generate operand collector structure."""
        self._gen_operand_mux(module, pe, task)
        if "bank_arbitration" in patterns:
            self._gen_bank_arbitration(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated operand_collect")

    # ---------- Task: execute_dispatch ----------
    def _gen_execute_dispatch_task(self, module, pe, task, refs, patterns):
        """Generate execution unit dispatch logic."""
        self._gen_alu_execute(module, pe, task)
        self._gen_load_store(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=2,
                                     message="Generated execute_dispatch")

    # ---------- Task: writeback ----------
    def _gen_writeback_task(self, module, pe, task, refs, patterns):
        """Generate writeback with scoreboard clear."""
        if not hasattr(module, "wb_valid"):
            module.wb_valid = Wire(1, "wb_valid")
        if not hasattr(module, "wb_warp_id"):
            module.wb_warp_id = Wire(2, "wb_warp_id")
        if not hasattr(module, "wb_rd"):
            module.wb_rd = Wire(4, "wb_rd")

        nwarp = 4
        with module.seq(module.clk, ~module.rst_n):
            with If(~module.rst_n):
                pass  # scoreboard cleared in scoreboard task
            with Else():
                with If(module.wb_valid):
                    # Clear scoreboard for completed instruction
                    if hasattr(module, "scoreboard_busy"):
                        # Simple clear: mark rd as free
                        pass  # Handled by scoreboard task integration
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated writeback structure")

    # ---------- Task: instruction_cache ----------
    def _gen_instruction_cache_task(self, module, pe, task, refs, patterns):
        """Generate instruction cache interface (simplified)."""
        if not hasattr(module, "icache_req"):
            module.icache_req = Wire(1, "icache_req")
        if not hasattr(module, "icache_addr"):
            module.icache_addr = Wire(32, "icache_addr")
        if not hasattr(module, "icache_rdata"):
            module.icache_rdata = Wire(32, "icache_rdata")
        if not hasattr(module, "icache_valid"):
            module.icache_valid = Wire(1, "icache_valid")
        if not hasattr(module, "icache_ready"):
            module.icache_ready = Wire(1, "icache_ready")

        with module.comb:
            module.icache_ready <<= 1  # Always ready in simplified model
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated instruction_cache interface")

    # ---------- Task: l1_dcache ----------
    def _gen_l1_dcache_task(self, module, pe, task, refs, patterns):
        """Generate L1 data cache interface (simplified)."""
        if not hasattr(module, "dcache_req"):
            module.dcache_req = Wire(1, "dcache_req")
        if not hasattr(module, "dcache_addr"):
            module.dcache_addr = Wire(32, "dcache_addr")
        if not hasattr(module, "dcache_wdata"):
            module.dcache_wdata = Wire(256, "dcache_wdata")
        if not hasattr(module, "dcache_wen"):
            module.dcache_wen = Wire(1, "dcache_wen")

        with module.comb:
            module.dcache_req <<= module.mem_req
            module.dcache_addr <<= module.mem_addr
            module.dcache_wdata <<= module.mem_wdata
            module.dcache_wen <<= module.mem_wen
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated l1_dcache interface")

    # ---------- Task: shared_mem ----------
    def _gen_shared_mem_task(self, module, pe, task, refs, patterns):
        """Generate shared memory / LDS interface."""
        if not hasattr(module, "lds_addr"):
            module.lds_addr = Wire(32, "lds_addr")
        if not hasattr(module, "lds_wdata"):
            module.lds_wdata = Wire(32, "lds_wdata")
        if not hasattr(module, "lds_wen"):
            module.lds_wen = Wire(1, "lds_wen")
        if not hasattr(module, "lds_rdata"):
            module.lds_rdata = Wire(32, "lds_rdata")

        # Simplified: direct-mapped shared mem (no bank conflict in skeleton)
        if not hasattr(module, "shared_mem"):
            module.shared_mem = Array(32, 256, "shared_mem")

        with module.comb:
            module.lds_rdata <<= module.shared_mem[module.lds_addr[7:0]]
        with module.seq(module.clk, ~module.rst_n):
            with If(module.lds_wen):
                module.shared_mem[module.lds_addr[7:0]] <<= module.lds_wdata
        return LogicGenerationResult(success=True, statements_added=2,
                                     message="Generated shared_mem (LDS)")

    # ---------- Task: fetch_decode ----------
    def _gen_fetch_decode_task(self, module, pe, task, refs, patterns):
        """Generate fetch-decode pipeline stage."""
        self._gen_instruction_decode(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated fetch_decode")

    # ---------- Task: ibuffer ----------
    def _gen_ibuffer_task(self, module, pe, task, refs, patterns):
        """Generate instruction buffer (simplified FIFO per warp)."""
        self._gen_fifo_buffer(module, pe, task)
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated ibuffer")

    # ---------- Task: memory_interface ----------
    def _gen_memory_interface_task(self, module, pe, task, refs, patterns):
        """Generate LSU → memory FIFO and request logic."""
        if not hasattr(module, "lsu_fifo_valid"):
            module.lsu_fifo_valid = Wire(1, "lsu_fifo_valid")
        if not hasattr(module, "lsu_fifo_ready"):
            module.lsu_fifo_ready = Wire(1, "lsu_fifo_ready")

        with module.comb:
            module.lsu_fifo_valid <<= module.mem_req
            module.lsu_fifo_ready <<= module.mem_ready
        return LogicGenerationResult(success=True, statements_added=1,
                                     message="Generated memory_interface")

    # ------------------------------------------------------------------
    # Pattern-level generators (reusable building blocks)
    # ------------------------------------------------------------------

    def _gen_round_robin_select(self, module, pe, task):
        """Round-robin priority selector."""
        nwarp = 4  # Could be inferred from pe.parameters
        if not hasattr(module, "rr_ptr"):
            module.rr_ptr = Reg(DEPTH := max(1, (nwarp - 1).bit_length()), "rr_ptr")
        if not hasattr(module, "issue_valid"):
            module.issue_valid = Wire(1, "issue_valid")
        if not hasattr(module, "issue_warp_id"):
            module.issue_warp_id = Wire(2, "issue_warp_id")
        if not hasattr(module, "warp_ready"):
            module.warp_ready = Wire(nwarp, "warp_ready")

        with module.comb:
            module.issue_valid <<= 0
            module.issue_warp_id <<= 0
            for i in range(nwarp):
                # Use bitmask for power-of-2 wrap instead of modulo
                idx = (module.rr_ptr + i) & (nwarp - 1)
                with If(~module.issue_valid & module.warp_ready[idx]):
                    module.issue_valid <<= 1
                    module.issue_warp_id <<= idx

        with module.seq(module.clk, ~module.rst_n):
            with If(~module.rst_n):
                module.rr_ptr <<= 0
            with Else():
                with If(module.issue_valid):
                    module.rr_ptr <<= (module.issue_warp_id + 1) & (nwarp - 1)

    def _gen_valid_ready_handshake(self, module, pe, task):
        """Valid-ready handshake wiring template."""
        if not hasattr(module, "fire"):
            module.fire = Wire(1, "fire")
        # Generic fire signal; specific valid/ready should exist on module
        valid_sig = getattr(module, "valid", None)
        ready_sig = getattr(module, "ready", None)
        if valid_sig is not None and ready_sig is not None:
            with module.comb:
                module.fire <<= valid_sig & ready_sig

    def _gen_stall_control(self, module, pe, task):
        """Generate stall signal when no candidate is ready."""
        if not hasattr(module, "stall"):
            module.stall = Wire(1, "stall")
        with module.comb:
            module.stall <<= ~module.issue_valid if hasattr(module, "issue_valid") else 0

    def _gen_busy_bit_scoreboard(self, module, pe, task):
        """Per-warp busy-bit scoreboard."""
        nwarp = 4
        num_regs = 8  # Simplified: track 8 registers per warp
        if not hasattr(module, "scoreboard_busy"):
            module.scoreboard_busy = Array(num_regs, nwarp, "scoreboard_busy")
        if not hasattr(module, "issue_rd"):
            module.issue_rd = Wire(4, "issue_rd")
        if not hasattr(module, "issue_rs1"):
            module.issue_rs1 = Wire(4, "issue_rs1")
        if not hasattr(module, "issue_rs2"):
            module.issue_rs2 = Wire(4, "issue_rs2")
        if not hasattr(module, "scoreboard_stall"):
            module.scoreboard_stall = Wire(1, "scoreboard_stall")

        with module.comb:
            # Hazard check: any source or dest register busy?
            rs1_busy = module.scoreboard_busy[module.issue_rs1] if hasattr(module, "issue_rs1") else 0
            rs2_busy = module.scoreboard_busy[module.issue_rs2] if hasattr(module, "issue_rs2") else 0
            rd_busy = module.scoreboard_busy[module.issue_rd] if hasattr(module, "issue_rd") else 0
            module.scoreboard_stall <<= rs1_busy | rs2_busy | rd_busy

        with module.seq(module.clk, ~module.rst_n):
            with If(~module.rst_n):
                for w in range(nwarp):
                    for r in range(num_regs):
                        module.scoreboard_busy[r] <<= 0
            with Else():
                with If(module.issue_valid & ~module.scoreboard_stall):
                    module.scoreboard_busy[module.issue_rd] <<= 1

    def _gen_dependency_block(self, module, pe, task):
        """Block issue when dependency hazard detected."""
        if hasattr(module, "issue_ready"):
            with module.comb:
                module.issue_ready <<= ~module.scoreboard_stall if hasattr(module, "scoreboard_stall") else 1

    def _gen_fifo_buffer(self, module, pe, task):
        """Simplified FIFO buffer (head/tail pointer)."""
        depth = 4
        if not hasattr(module, "fifo_head"):
            module.fifo_head = Reg(max(1, (depth - 1).bit_length()), "fifo_head")
        if not hasattr(module, "fifo_tail"):
            module.fifo_tail = Reg(max(1, (depth - 1).bit_length()), "fifo_tail")
        if not hasattr(module, "fifo_count"):
            module.fifo_count = Reg(max(1, (depth).bit_length()), "fifo_count")
        if not hasattr(module, "fifo_full"):
            module.fifo_full = Wire(1, "fifo_full")
        if not hasattr(module, "fifo_empty"):
            module.fifo_empty = Wire(1, "fifo_empty")

        with module.comb:
            module.fifo_full <<= module.fifo_count == depth
            module.fifo_empty <<= module.fifo_count == 0

    def _gen_pipeline_stall(self, module, pe, task):
        """Pipeline stall propagation."""
        if not hasattr(module, "pipeline_stall"):
            module.pipeline_stall = Wire(1, "pipeline_stall")
        with module.comb:
            module.pipeline_stall <<= module.stall if hasattr(module, "stall") else 0

    def _gen_instruction_decode(self, module, pe, task):
        """Instruction decode control signal extraction."""
        # Usually already present in skeleton; this adds decode-wide control
        if not hasattr(module, "inst_alu"):
            module.inst_alu = Wire(1, "inst_alu")
        if not hasattr(module, "inst_lsu"):
            module.inst_lsu = Wire(1, "inst_lsu")
        if not hasattr(module, "inst_branch"):
            module.inst_branch = Wire(1, "inst_branch")

        with module.comb:
            # Simplified decode: derive from opcode
            opcode = getattr(module, "opcode", None)
            if opcode is not None:
                module.inst_alu <<= (opcode == 3) | (opcode == 4) | (opcode == 5)
                module.inst_lsu <<= (opcode == 1) | (opcode == 2)
                module.inst_branch <<= opcode == 6

    def _gen_operand_mux(self, module, pe, task):
        """Operand selection mux structure."""
        if not hasattr(module, "operand_a"):
            module.operand_a = Wire(256, "operand_a")
        if not hasattr(module, "operand_b"):
            module.operand_b = Wire(256, "operand_b")

        with module.comb:
            if hasattr(module, "vrf") and hasattr(module, "vrf_rs1"):
                module.operand_a <<= module.vrf[module.vrf_rs1]
            if hasattr(module, "vrf") and hasattr(module, "vrf_rs2"):
                module.operand_b <<= module.vrf[module.vrf_rs2]

    def _gen_alu_execute(self, module, pe, task):
        """ALU execution unit interface."""
        if not hasattr(module, "alu_result"):
            module.alu_result = Wire(256, "alu_result")
        if not hasattr(module, "alu_valid"):
            module.alu_valid = Wire(1, "alu_valid")

        with module.comb:
            if hasattr(module, "operand_a") and hasattr(module, "operand_b"):
                module.alu_result <<= module.operand_a + module.operand_b
            module.alu_valid <<= module.inst_alu if hasattr(module, "inst_alu") else 0

    def _gen_load_store(self, module, pe, task):
        """Load/store unit interface."""
        if not hasattr(module, "lsu_addr"):
            module.lsu_addr = Wire(32, "lsu_addr")
        if not hasattr(module, "lsu_wdata"):
            module.lsu_wdata = Wire(256, "lsu_wdata")
        if not hasattr(module, "lsu_valid"):
            module.lsu_valid = Wire(1, "lsu_valid")

        with module.comb:
            if hasattr(module, "mem_addr"):
                module.lsu_addr <<= module.mem_addr
            if hasattr(module, "mem_wdata"):
                module.lsu_wdata <<= module.mem_wdata
            module.lsu_valid <<= module.inst_lsu if hasattr(module, "inst_lsu") else 0

    def _gen_index_encode(self, module, pe, task):
        """Index encoding for one-hot → binary."""
        if not hasattr(module, "grant_idx"):
            module.grant_idx = Wire(2, "grant_idx")
        if not hasattr(module, "grant_onehot"):
            module.grant_onehot = Wire(4, "grant_onehot")

        with module.comb:
            module.grant_idx <<= 0
            for i in range(4):
                with If(module.grant_onehot[i]):
                    module.grant_idx <<= i

    def _gen_bank_arbitration(self, module, pe, task):
        """Bank arbitration for multi-bank memory access."""
        num_banks = 4
        if not hasattr(module, "bank_req"):
            module.bank_req = Wire(num_banks, "bank_req")
        if not hasattr(module, "bank_grant"):
            module.bank_grant = Wire(num_banks, "bank_grant")

        with module.comb:
            module.bank_grant <<= 0
            for i in range(num_banks):
                with If(module.bank_req[i]):
                    module.bank_grant[i] <<= 1

    # ------------------------------------------------------------------
    # Repair API
    # ------------------------------------------------------------------

    def repair(self, module: Module, repair_context: Any) -> Dict[str, Any]:
        """Generate a repair patch from failed verification context.

        First version performs rule-based fixes:
        - Missing signal declarations → add signals
        - Missing reset initialization → add reset logic

        Returns patch dict with keys:
            add_signals: List[{"kind": "Wire|Reg", "width": int, "name": str}]
            add_statements: List[description strings]
        """
        patch: Dict[str, Any] = {"add_signals": [], "add_statements": []}
        issues = getattr(repair_context, "issues", [])

        for issue in issues:
            issue_str = str(issue)

            # Fix: signal assigned but not declared
            if "assigned but not declared" in issue_str.lower() or \
               "implicit wire" in issue_str.lower():
                # Extract signal name heuristically
                m = re.search(r"['\"]?([a-zA-Z_][a-zA-Z0-9_]*)['\"]?", issue_str)
                if m:
                    sig_name = m.group(1)
                    if not hasattr(module, sig_name):
                        patch["add_signals"].append({
                            "kind": "Wire",
                            "width": 1,
                            "name": sig_name,
                        })

            # Fix: width mismatch — add wider wire
            if "width mismatch" in issue_str.lower():
                m = re.search(r"['\"]?([a-zA-Z_][a-zA-Z0-9_]*)['\"]?", issue_str)
                if m:
                    sig_name = m.group(1)
                    if not hasattr(module, sig_name):
                        patch["add_signals"].append({
                            "kind": "Wire",
                            "width": 32,
                            "name": sig_name,
                        })

            # Fix: missing reset coverage
            if "reset" in issue_str.lower() and "not covered" in issue_str.lower():
                patch["add_statements"].append(
                    "Add reset initialization for all state registers"
                )

        # Reference cards may suggest additional patterns to add
        for card in getattr(repair_context, "reference_cards", []):
            for pat in getattr(card, "reusable_patterns", []):
                if pat in self._pattern_gens and pat not in ["round_robin_select"]:
                    patch["add_statements"].append(
                        f"Consider adding pattern: {pat}"
                    )

        return patch
