"""
rtlgen.prompt_builder — Serialize GenerationContext into Claude agent prompt.

Generates a structured prompt that Claude (as the DSL generation agent)
can read and use to produce RTLCraft DSL code.

The prompt includes:
  1. Module specification (ports, parameters, behaviors)
  2. Reference implementations with code patterns (abstraction only, no verbatim code)
  3. Coding rules
  4. Verification contract

Reference: skills/plan_0525.md Section 5
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_generation_prompt(gen_ctx: Any, task: Optional[Dict] = None) -> str:
    """Build a Claude agent prompt from GenerationContext.

    Args:
        gen_ctx: GenerationContext from arch_skel._build_generation_context()
        task: Optional task dict for context

    Returns:
        Prompt text for Claude to generate DSL code
    """
    target = getattr(gen_ctx, "target", None)
    ref_summaries = getattr(gen_ctx, "reference_summaries", [])
    coding_rules = getattr(gen_ctx, "coding_rules", [])
    verification_contract = getattr(gen_ctx, "verification_contract", [])

    parts: List[str] = []

    # ── Header ──
    parts.append("=" * 70)
    parts.append("RTLCraft DSL Code Generation Request")
    parts.append("=" * 70)
    parts.append("")

    # ── Section 1: Module Specification ──
    parts.append("## 1. Target Module Specification")
    parts.append("")
    if target:
        name = getattr(target, "name", "unknown")
        pe_type = getattr(target, "pe_type", "generic")
        role = getattr(target, "role", "")
        description = getattr(target, "description", "")
        parts.append(f"**Module Name:** `{name}`")
        if role:
            parts.append(f"**Role:** {role}")
        if description:
            parts.append(f"**Description:** {description}")
        parts.append(f"**PE Type:** {pe_type}")
        parts.append("")

        # Parameters
        params = getattr(target, "parameters", {})
        if params:
            parts.append("### Parameters")
            for k, v in params.items():
                parts.append(f"- `{k}` = {v}")
            parts.append("")

        # Ports
        ports = getattr(target, "ports", {})
        if ports:
            input_ports = [n for n, s in ports.items() if s.get("dir") == "input"]
            output_ports = [n for n, s in ports.items() if s.get("dir") == "output"]
            parts.append(f"### Ports ({len(input_ports)} inputs, {len(output_ports)} outputs)")
            parts.append("")
            parts.append("**Inputs:**")
            for n in sorted(input_ports):
                spec = ports[n]
                parts.append(f"- `{n}` [{spec.get('width', 1)} bits]")
            parts.append("")
            parts.append("**Outputs:**")
            for n in sorted(output_ports):
                spec = ports[n]
                parts.append(f"- `{n}` [{spec.get('width', 1)} bits]")
            parts.append("")

        # Required behaviors
        behaviors = getattr(target, "required_behaviors", [])
        if behaviors:
            parts.append("### Required Behaviors")
            for b in behaviors:
                parts.append(f"- {b}")
            parts.append("")

        # State suggestions
        state_hints = getattr(target, "internal_state_suggestions", [])
        if state_hints:
            parts.append("### Internal State Suggestions")
            for s in state_hints:
                parts.append(f"- {s}")
            parts.append("")

    # ── Section 2: Reference Implementations ──
    if ref_summaries:
        parts.append("## 2. Reference Implementation Patterns")
        parts.append("")
        parts.append("The following reference modules show HOW similar designs")
        parts.append("were implemented. DO NOT copy code verbatim — use these")
        parts.append("patterns as GUIDANCE for your implementation.")
        parts.append("")

        for i, ref in enumerate(ref_summaries, 1):
            mod_name = getattr(ref, "module_name", "unknown")
            relevance = getattr(ref, "relevance_score", 0.0)
            design_intent = getattr(ref, "design_intent", [])
            logic_pattern = getattr(ref, "logic_pattern", {})
            state_pattern = getattr(ref, "state_pattern", [])
            code_patterns = getattr(ref, "code_patterns", {})
            pseudo_dsl = getattr(ref, "pseudo_dsl", [])
            adaptation_notes = getattr(ref, "adaptation_notes", [])
            caution = getattr(ref, "caution", [])

            parts.append(f"### Reference {i}: `{mod_name}` (relevance: {relevance:.2f})")
            parts.append("")

            # Design intent
            if design_intent:
                parts.append("**Design Intent:**")
                for intent in design_intent[:4]:
                    parts.append(f"- {intent}")
                parts.append("")

            # Architecture patterns
            derived_flags = logic_pattern.get("derived_flags", [])
            if derived_flags:
                parts.append(f"**Architecture Patterns:** {', '.join(derived_flags)}")
                parts.append("")

            # State patterns
            if state_pattern:
                parts.append("**State Patterns:**")
                for s in state_pattern[:5]:
                    parts.append(f"- {s}")
                parts.append("")

            # Code-level patterns (from actual DSL source)
            if code_patterns:
                parts.append("**Code-Level Patterns (extracted from reference source):**")

                ports_info = code_patterns.get("ports", [])
                if ports_info:
                    inp = [p["name"] for p in ports_info if p.get("direction") == "input"]
                    out = [p["name"] for p in ports_info if p.get("direction") == "output"]
                    parts.append(f"- Interface: {len(inp)} inputs, {len(out)} outputs")
                    parts.append(f"  Input examples: {inp[:5]}")
                    parts.append(f"  Output examples: {out[:5]}")

                state_vars = code_patterns.get("state_vars", [])
                if state_vars:
                    parts.append(f"- State variables: {len(state_vars)} registers/wires")
                    for sv in state_vars[:5]:
                        parts.append(f"  - {sv['kind']} `{sv['name']}` (width={sv['width']})")

                summary_patterns = code_patterns.get("summary_patterns", [])
                if summary_patterns:
                    parts.append(f"- Summary: {'; '.join(summary_patterns[:3])}")

                fsm_summary = code_patterns.get("fsm_summary")
                if fsm_summary:
                    parts.append(
                        f"- FSM: state register `{fsm_summary.get('state_reg')}` "
                        f"with {fsm_summary.get('num_transitions', 0)} transitions"
                    )

                handshake_summary = code_patterns.get("handshake_summary", [])
                if handshake_summary:
                    for hs in handshake_summary[:2]:
                        parts.append(
                            f"- Handshake: `{hs['valid']}`/`{hs['ready']}` "
                            f"(fire: {hs['fire']})"
                        )

                parts.append("")

            # Pseudo-DSL hints
            if pseudo_dsl:
                parts.append("**Structural Hints:**")
                for hint in pseudo_dsl[:4]:
                    parts.append(f"- {hint}")
                parts.append("")

            # Adaptation notes
            if adaptation_notes:
                parts.append("**Adaptation Notes:**")
                for note in adaptation_notes[:3]:
                    parts.append(f"- {note}")
                parts.append("")

            # Caution
            if caution:
                parts.append("**Caution:**")
                for c in caution[:2]:
                    parts.append(f"- {c}")
                parts.append("")

            # Actual code snippets from reference DSL source
            code_snippets = getattr(ref, "code_snippets", {})
            if code_snippets:
                parts.append("**Reference Code Snippets (for structural guidance only):**")
                parts.append("These show HOW the reference module is structured.")
                parts.append("Do NOT copy verbatim — adapt to current port names and logic.")
                parts.append("")

                if "state_decl" in code_snippets:
                    parts.append("State declarations:")
                    parts.append("```python")
                    parts.append(code_snippets["state_decl"])
                    parts.append("```")
                    parts.append("")

                if "comb_logic" in code_snippets:
                    parts.append("Combinational logic:")
                    parts.append("```python")
                    parts.append(code_snippets["comb_logic"])
                    parts.append("```")
                    parts.append("")

                if "seq_logic" in code_snippets:
                    parts.append("Sequential logic:")
                    parts.append("```python")
                    parts.append(code_snippets["seq_logic"])
                    parts.append("```")
                    parts.append("")

    # ── Section 3: Coding Rules ──
    if coding_rules:
        parts.append("## 3. Coding Rules")
        parts.append("")
        for rule in coding_rules:
            parts.append(f"- {rule}")
        parts.append("")

    # ── Section 4: Verification Contract ──
    if verification_contract:
        parts.append("## 4. Verification Contract")
        parts.append("")
        for item in verification_contract:
            parts.append(f"- {item}")
        parts.append("")

    # ── Section 5: Sub-Module Decomposition ──
    sub_modules = getattr(gen_ctx, "sub_modules", [])
    if sub_modules:
        parts.append("## 5. Module Architecture: Sub-Module Decomposition")
        parts.append("")
        parts.append("This module is decomposed into the following sub-modules.")
        parts.append("You MUST implement this module as a monolithic module")
        parts.append("that incorporates the functionality of ALL sub-modules.")
        parts.append("Do NOT instantiate sub-modules as separate classes.")
        parts.append("")

        for i, sm in enumerate(sub_modules, 1):
            sm_name = getattr(sm, "name", "")
            sm_type = getattr(sm, "submod_type", "")
            sm_desc = getattr(sm, "description", "")
            sm_inputs = getattr(sm, "inputs", [])
            sm_outputs = getattr(sm, "outputs", [])
            parts.append(f"### Sub-Module {i}: `{sm_name}` (type: {sm_type})")
            if sm_desc:
                parts.append(f"**Description:** {sm_desc}")
            if sm_inputs:
                parts.append(f"**Inputs:** {', '.join(sm_inputs)}")
            if sm_outputs:
                parts.append(f"**Outputs:** {', '.join(sm_outputs)}")
            parts.append("")

    # ── Section 6: Implementation Steps ──
    impl_steps = getattr(gen_ctx, "implementation_steps", [])
    if impl_steps:
        parts.append("## 6. Implementation Steps (Full Task List)")
        parts.append("")
        parts.append("The following are ALL sub-tasks for this PE type.")
        parts.append("Each step defines a sub-module or functional block.")
        parts.append("Implement ALL steps as a SINGLE monolithic module.")
        parts.append("")

        for step in impl_steps:
            step_name = getattr(step, "name", "")
            step_goal = getattr(step, "goal", "")
            step_keywords = getattr(step, "keywords", [])
            parts.append(f"### Step: `{step_name}`")
            parts.append(f"**Goal:** {step_goal}")
            if step_keywords:
                # Separate short keywords from long descriptions
                short_kw = [k for k in step_keywords if len(k.split()) <= 5]
                long_desc = [k for k in step_keywords if len(k.split()) > 5]
                if short_kw:
                    parts.append(f"**Keywords:** {', '.join(short_kw)}")
                if long_desc:
                    parts.append(f"**Functional description:** {' '.join(long_desc)}")
            parts.append("")

    # ── Section 7: Skeleton State and Logic ──
    skeleton_state = getattr(gen_ctx, "skeleton_state_vars", [])
    skeleton_hints = getattr(gen_ctx, "skeleton_logic_hints", [])
    if skeleton_state or skeleton_hints:
        parts.append("## 7. Existing Skeleton Framework")
        parts.append("")
        if skeleton_state:
            parts.append("### Declared State Variables")
            parts.append("The following state variables are already declared on the module.")
            parts.append("You MUST use these variable names in your implementation.")
            parts.append("")
            for sv in skeleton_state:
                name = sv.get("name", "?")
                kind = sv.get("kind", "?")
                width = sv.get("width", "")
                depth = sv.get("depth", "")
                if kind == "Array" and depth:
                    parts.append(f"- `{name}`: {kind}({width}, {depth})")
                elif kind == "Array":
                    parts.append(f"- `{name}`: {kind}({width})")
                else:
                    parts.append(f"- `{name}`: {kind}({width})")
            parts.append("")
        if skeleton_hints:
            parts.append("### Skeleton Logic Status")
            for hint in skeleton_hints:
                parts.append(f"- {hint}")
            parts.append("")

    # ── Section 8: DSL Syntax Reference ──
    section_num = 8 if (sub_modules or impl_steps or skeleton_state or skeleton_hints) else 5
    parts.append(f"## {section_num}. RTLCraft DSL Syntax Reference")
    parts.append("")
    parts.append("Use the following DSL syntax to generate the module:")
    parts.append("")
    parts.append("```python")
    parts.append("from rtlgen.core import Module, Input, Output, Wire, Reg, Array")
    parts.append("from rtlgen.logic import If, Else, Elif, Switch, Mux")
    parts.append("")
    parts.append("class MyModule(Module):")
    parts.append("    def __init__(self, name=\"MyModule\"):")
    parts.append("        super().__init__(name)")
    parts.append("        # Ports")
    parts.append('        self.clk = Input(1, "clk")')
    parts.append('        self.rst_n = Input(1, "rst_n")')
    parts.append('        self.data_in = Input(8, "data_in")')
    parts.append('        self.data_out = Output(8, "data_out")')
    parts.append("        # Internal signals")
    parts.append('        self.state_reg = Reg(4, "state_reg")')
    parts.append("        # Combinational logic")
    parts.append("        with self.comb:")
    parts.append("            self.data_out <<= self.data_in & 0xFF")
    parts.append("            with If(self.state_reg == 3):")
    parts.append("                self.data_out <<= 0")
    parts.append("        # Sequential logic")
    parts.append("        with self.seq(self.clk, ~self.rst_n):")
    parts.append("            with If(~self.rst_n):")
    parts.append("                self.state_reg <<= 0")
    parts.append("            with Else():")
    parts.append("                self.state_reg <<= self.state_reg + 1")
    parts.append("```")
    parts.append("")
    parts.append("Key DSL elements:")
    parts.append("- `Input(width, name)` / `Output(width, name)` — ports")
    parts.append("- `Wire(width, name)` / `Reg(width, name)` — internal signals")
    parts.append('- `Array(width, depth, name)` — register/memory arrays')
    parts.append("- `with self.comb:` — combinational logic block")
    parts.append("- `with self.seq(clk, rst):` — sequential logic block")
    parts.append("- `target <<= expr` — signal assignment")
    parts.append("- `with If(cond):` / `with Else():` — conditional logic")
    parts.append("- `with Switch(expr) as sw:` / `sw.case(N):` — multi-way branch")
    parts.append("- `Mux(sel, a, b)` — 2-to-1 multiplexer")
    parts.append("- `Cat(a, b, c)` — concatenation (a is MSB)")
    parts.append("- `Rep(bit, N)` — replicate a bit N times (sign extension)")
    parts.append("- `Const(value, width)` — constant with explicit width")
    parts.append("")
    parts.append("**Sign Extension Example:**")
    parts.append("```python")
    parts.append("# Sign-extend 12-bit value to 64-bit:")
    parts.append("wire_64 <<= Cat(Rep(wire_12[11], 52), wire_12)")
    parts.append("# Zero-extend 12-bit value to 64-bit:")
    parts.append("wire_64 <<= Cat(Const(0, 52), wire_12)")
    parts.append("# Sign-extend 8-bit load to 64-bit:")
    parts.append("lb_ext <<= Cat(Rep(dcache_rdata[7], 56), dcache_rdata[7:0])")
    parts.append("# Zero-extend 8-bit load to 64-bit:")
    parts.append("lbu_ext <<= Cat(Const(0, 56), dcache_rdata[7:0])")
    parts.append("```")
    parts.append("")
    parts.append("**FSM/Switch Example:**")
    parts.append("```python")
    parts.append("with Switch(fsm_state_reg) as sw:")
    parts.append("    with sw.case(IDLE):")
    parts.append("        fsm_state_reg <<= ACTIVE")
    parts.append("    with sw.case(ACTIVE):")
    parts.append("        fsm_state_reg <<= DONE")
    parts.append("```")
    parts.append("")
    parts.append("**CRITICAL — Common Errors to Avoid:**")
    parts.append("1. NEVER use `.sign_extend()`, `.zero_extend()`, `.concat()` on signals")
    parts.append("2. ALWAYS use `with Switch(x) as sw:` then `with sw.case(N):` (NOT `signal.case()`)")
    parts.append("3. NEVER declare local computation variables as `Const()` — use `Wire()` instead")
    parts.append("4. ALWAYS use `Cat(Rep(sign_bit, N), low_bits)` for sign extension")
    parts.append("5. `~Const(value, width)` IS supported for bitwise NOT of constants")
    parts.append("6. NEVER invent methods like `.case()`, `.concat()` on signals")
    parts.append("7. ONLY use: `Cat()`, `Rep()`, `Const()`, `Mux()`, `If/Else/Elif`, `Switch/case`")
    parts.append("")

    # ── Section 9: Generation Task ──
    parts.append(f"## {section_num + 1}. Generation Task")
    parts.append("")
    parts.append("Generate a complete RTLCraft DSL module that:")
    parts.append("1. Declares ALL input and output ports as specified above")
    parts.append("2. Implements ALL sub-modules as a SINGLE monolithic module")
    parts.append("3. Follows the implementation steps in order")
    parts.append("4. Uses the skeleton state variables (do NOT rename them)")
    parts.append("5. Uses reference patterns as GUIDANCE (not verbatim code)")
    parts.append("6. Follows all coding rules")
    parts.append("7. Is complete and synthesizable")
    parts.append("")
    parts.append("IMPORTANT: The generated module must implement COMPLETE")
    parts.append("functionality — not just the current sub-task. Include ALL")
    parts.append("pipeline stages, ALL forwarding paths, ALL hazard detection,")
    parts.append("and ALL control logic as described in the Implementation Steps.")
    parts.append("")
    parts.append("Output the DSL code as a Python class inheriting from `Module`.")
    parts.append("Include ONLY the class definition — no imports, no test code.")
    parts.append("")
    parts.append("```python")
    parts.append("# Your generated DSL code here")
    parts.append("```")
    parts.append("")

    return "\n".join(parts)


def build_batch_prompt(gen_ctx_list: List[Any],
                       task_map: Optional[Dict[str, Dict]] = None) -> str:
    """Build a batch prompt for generating multiple modules.

    Args:
        gen_ctx_list: List of GenerationContext objects
        task_map: Optional mapping from module name to task dict

    Returns:
        Batch prompt text
    """
    parts: List[str] = []
    parts.append("=" * 70)
    parts.append("RTLCraft Batch DSL Code Generation")
    parts.append("=" * 70)
    parts.append("")
    parts.append(f"Generate {len(gen_ctx_list)} RTL modules using the RTLCraft DSL.")
    parts.append("Each module specification follows below.")
    parts.append("")
    parts.append("---")
    parts.append("")

    for i, ctx in enumerate(gen_ctx_list, 1):
        target = getattr(ctx, "target", None)
        task_name = ""
        if task_map and target:
            task_name = task_map.get(getattr(target, "name", ""), "")

        parts.append(f"## Module {i}" + (f" ({task_name})" if task_name else ""))
        parts.append("")
        parts.append(build_generation_prompt(ctx))
        parts.append("")
        parts.append("---")
        parts.append("")

    return "\n".join(parts)
