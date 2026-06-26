"""
rtlgen.spec_markdown — Convert GenerationContext to Readable Markdown Spec

Takes a GenerationContext (ports, behaviors, references, rules, sub-modules)
and an optional Module object, and produces a structured markdown document
that serves as a specification for DSL code generation.

Enhanced with spec_enhancer to add:
  - Architecture description (B1)
  - FSM state transition table (B2)
  - Sub-module internal connections (B3)
  - Interface protocol descriptions (B4)
  - Golden test vectors (B5)
  - Behavior pseudo-code (A2)
"""
from __future__ import annotations

from typing import Any, List, Optional

from rtlgen.core import Module


def generation_context_to_markdown(
    gen_ctx: Any,
    module: Optional[Module] = None,
) -> str:
    """Convert a GenerationContext to a markdown specification document.

    Args:
        gen_ctx: GenerationContext from arch_skel._build_generation_context()
        module: Optional Module object for FSM extraction

    Returns:
        Markdown string with module spec, ports, behaviors, references, etc.
    """
    target = getattr(gen_ctx, "target", None)
    ref_summaries = getattr(gen_ctx, "reference_summaries", [])
    coding_rules = getattr(gen_ctx, "coding_rules", [])
    verification_contract = getattr(gen_ctx, "verification_contract", [])
    sub_modules = getattr(gen_ctx, "sub_modules", [])
    implementation_steps = getattr(gen_ctx, "implementation_steps", [])
    skeleton_state = getattr(gen_ctx, "skeleton_state_vars", [])
    skeleton_hints = getattr(gen_ctx, "skeleton_logic_hints", [])

    # Use spec_enhancer for additional structured info
    try:
        from rtlgen.spec_enhancer import enhance_context
        enhanced = enhance_context(gen_ctx, module)
    except ImportError:
        enhanced = {}

    pe_type = getattr(target, "pe_type", "") if target else ""

    parts: List[str] = []

    # ── Header ──
    mod_name = getattr(target, "name", "unknown") if target else "unknown"
    parts.append(f"# Module Spec: {mod_name}")
    parts.append("")

    # ── Module Info ──
    parts.append("## Module Info")
    parts.append("")
    if target:
        name = getattr(target, "name", "unknown")
        pe_type = getattr(target, "pe_type", "generic")
        role = getattr(target, "role", "")
        description = getattr(target, "description", "")
        parts.append(f"- **Name:** {name}")
        if pe_type:
            parts.append(f"- **PE Type:** {pe_type}")
        if role:
            parts.append(f"- **Role:** {role}")
        if description:
            parts.append(f"- **Description:** {description}")
    parts.append("")

    # ── Architecture Description (NEW: B1) ──
    arch_desc = enhanced.get("arch_description")
    if arch_desc:
        title = arch_desc.get("title", "Architecture")
        features = arch_desc.get("features", [])
        stages = arch_desc.get("stages", [])

        parts.append("## Architecture Description")
        parts.append("")
        parts.append(f"**{title}**")
        parts.append("")

        if stages:
            parts.append("### Pipeline Stages")
            parts.append("")
            parts.append("| Stage | Function |")
            parts.append("|-------|----------|")
            for s in stages:
                parts.append(f"| {s['name']} | {s['function']} |")
            parts.append("")

        if features:
            parts.append("### Key Features")
            parts.append("")
            for f in features:
                parts.append(f"- {f}")
            parts.append("")

    # ── Parameters ──
    params = getattr(target, "parameters", {}) if target else {}
    if params:
        parts.append(f"## Parameters")
        parts.append("")
        parts.append("| Parameter | Value |")
        parts.append("|-----------|-------|")
        for k, v in sorted(params.items()):
            parts.append(f"| {k} | {v} |")
        parts.append("")

    # ── Ports ──
    ports = getattr(target, "ports", {}) if target else {}
    if ports:
        input_ports = [(n, s) for n, s in ports.items() if s.get("dir") == "input"]
        output_ports = [(n, s) for n, s in ports.items() if s.get("dir") == "output"]

        parts.append("## Ports")
        parts.append("")

        if input_ports:
            parts.append(f"### Inputs ({len(input_ports)})")
            parts.append("")
            parts.append("| Port | Width |")
            parts.append("|------|-------|")
            for n, s in sorted(input_ports):
                parts.append(f"| {n} | {s.get('width', 1)} |")
            parts.append("")

        if output_ports:
            parts.append(f"### Outputs ({len(output_ports)})")
            parts.append("")
            parts.append("| Port | Width |")
            parts.append("|------|-------|")
            for n, s in sorted(output_ports):
                parts.append(f"| {n} | {s.get('width', 1)} |")
            parts.append("")

    # ── Port Interaction / Protocol Map (NEW: from dsl_modules.py) ──
    interactions = enhanced.get("dsl_interactions", [])
    if interactions:
        parts.append("## Port Interactions")
        parts.append("")
        parts.append("| Port | Direction | Width | Connects To | Protocol |")
        parts.append("|------|-----------|-------|-------------|----------|")
        for ix in interactions:
            parts.append(f"| {ix.get('port', '')} | {ix.get('direction', '')} | {ix.get('width', '?')} | `{ix.get('connects_to', '')}` | {ix.get('protocol', '')} |")
        parts.append("")

    # ── FSM State Transition Table (NEW: B2) ──
    fsms = enhanced.get("fsms", [])
    if fsms:
        parts.append("## FSM State Machines")
        parts.append("")

        for i, fsm in enumerate(fsms, 1):
            state_reg = fsm.get("state_reg", "?")
            width = fsm.get("width", 1)
            states = fsm.get("states", [])
            transitions = fsm.get("transitions", [])

            parts.append(f"### FSM {i}: `{state_reg}` ({2**width} states, {len(transitions)} transitions)")
            parts.append("")

            if states:
                parts.append(f"**States:** {', '.join(states)}")
                parts.append("")

            if transitions:
                parts.append("**State Transitions:**")
                parts.append("")
                parts.append("| Current State | Next State | Condition |")
                parts.append("|--------------|------------|-----------|")
                for t in transitions:
                    parts.append(f"| {t.get('from', '?')} | {t.get('to', '?')} | {t.get('condition', '')} |")
                parts.append("")

    # ── Required Behaviors ──
    behaviors = getattr(target, "required_behaviors", []) if target else []
    if behaviors:
        parts.append("## Required Behaviors")
        parts.append("")
        for i, b in enumerate(behaviors, 1):
            parts.append(f"{i}. {b}")
        parts.append("")

    # ── Behavior Pseudo-Code (NEW: A2) ──
    pseudocode = enhanced.get("behavior_pseudocode", "")
    if pseudocode:
        parts.append("## Behavior Pseudo-Code")
        parts.append("")
        parts.append("```")
        parts.append(pseudocode)
        parts.append("```")
        parts.append("")

    # ── Timing Constraints (NEW) ──
    timing_stages = enhanced.get("timing_stages", [])
    if timing_stages:
        parts.append("## Timing Constraints")
        parts.append("")
        parts.append("### Pipeline Stage Latencies")
        parts.append("")
        parts.append("| Stage | Cycles | Description |")
        parts.append("|-------|--------|-------------|")
        for s in timing_stages:
            parts.append(f"| {s.get('name', '')} | {s.get('cycles', '')} | {s.get('description', '')} |")
        parts.append("")

    timing_hazards = enhanced.get("timing_hazards", {})
    if timing_hazards:
        parts.append("### Hazard / Stall Penalties")
        parts.append("")
        for k, v in timing_hazards.items():
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    fsm_states = enhanced.get("fsm_states", [])
    if fsm_states:
        parts.append("### FSM State Timing")
        parts.append("")
        parts.append("| State | Cycles | Entry Action |")
        parts.append("|-------|--------|--------------|")
        for s in fsm_states:
            parts.append(f"| {s.get('name', '')} | {s.get('cycles', '')} | {s.get('entry_action', '')} |")
        parts.append("")

    fsm_transitions = enhanced.get("fsm_transitions", {})
    if fsm_transitions:
        parts.append("### State Transition Timing")
        parts.append("")
        for k, v in fsm_transitions.items():
            parts.append(f"- **{k}:** {v}")
        parts.append("")

    # ── Interface Protocol Timing (NEW) ──
    timing_protocols = enhanced.get("timing_protocols", {})
    if timing_protocols:
        parts.append("### Interface Protocol Timing")
        parts.append("")
        for name, proto in timing_protocols.items():
            parts.append(f"**{name}:**")
            parts.append("")
            parts.append(f"- Type: {proto.get('type', '')}")
            parts.append(f"- Request cycles: {proto.get('request_cycles', '')}")
            parts.append(f"- Response cycles: {proto.get('response_cycles', '')}")
            parts.append(f"- Backpressure: {proto.get('backpressure', '')}")
            parts.append(f"- Fire condition: {proto.get('fire_condition', '')}")
            parts.append("")

    # ── Behavioral Verification Metrics (NEW) ──
    beh_metrics = enhanced.get("behavioral_metrics", {})
    if beh_metrics:
        parts.append("## Behavioral Verification Metrics")
        parts.append("")
        for k, v in beh_metrics.items():
            parts.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        parts.append("")

    # ── Pipeline Registers ──
    uarch = enhanced.get("uarch", {})
    pipe_regs = uarch.get("pipeline_registers", [])
    if pipe_regs:
        parts.append("## Pipeline Registers")
        parts.append("")
        parts.append("| Stage | Name | Width | Purpose |")
        parts.append("|-------|------|-------|---------|")
        for r in pipe_regs:
            parts.append(f"| {r.get('stage', '')} | `{r.get('name', '')}` | {r.get('width', '')} | {r.get('purpose', '')} |")
        parts.append("")

    # ── 9. Opcode Decode Table (NEW) ──
    opcodes = uarch.get("opcode_table", [])
    if opcodes:
        parts.append("## Opcode Decode")
        parts.append("")
        parts.append("| opcode | Name | Type | Description |")
        parts.append("|--------|------|------|-------------|")
        for o in opcodes:
            parts.append(f"| `{o.get('opcode', '')}` | {o.get('name', '')} | {o.get('type', '')} | {o.get('desc', '')} |")
        parts.append("")

    # ── 10. ALU Operations (NEW) ──
    alu_ops = uarch.get("alu_operations", [])
    if alu_ops:
        parts.append("## ALU Operations")
        parts.append("")
        parts.append("| funct3 | funct7 | Name | Description |")
        parts.append("|--------|--------|------|-------------|")
        for a in alu_ops:
            parts.append(f"| {a.get('funct3', '')} | {a.get('funct7', '')} | **{a.get('name', '')}** | {a.get('desc', '')} |")
        parts.append("")

    # ── 11. Branch Conditions (NEW) ──
    branches = uarch.get("branch_conditions", [])
    if branches:
        parts.append("## Branch Conditions")
        parts.append("")
        parts.append("| funct3 | Name | Description |")
        parts.append("|--------|------|-------------|")
        for b in branches:
            parts.append(f"| {b.get('funct3', '')} | **{b.get('name', '')}** | {b.get('desc', '')} |")
        parts.append("")

    # ── 12. Immediate Formats (NEW) ──
    imms = uarch.get("immediate_formats", [])
    if imms:
        parts.append("## Immediate Formats")
        parts.append("")
        parts.append("| Type | Bit Layout | Used By |")
        parts.append("|------|------------|---------|")
        for im in imms:
            parts.append(f"| {im.get('type', '')} | `{im.get('layout', '')}` | {im.get('instructions', '')} |")
        parts.append("")

    # ── 13. Forwarding Network (NEW) ──
    fwd = uarch.get("forwarding_network")
    if fwd:
        parts.append("## Forwarding Network")
        parts.append("")
        for k, v in fwd.items():
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    # ── 14. Stall / Hazard Logic (NEW) ──
    stall = uarch.get("stall_logic")
    if stall:
        parts.append("## Stall / Hazard Logic")
        parts.append("")
        for k, v in stall.items():
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    # ── 15. Coherence Protocol (NEW, for cache) ──
    coherence = uarch.get("coherence_protocol")
    if coherence:
        parts.append("## Coherence Protocol")
        parts.append("")
        parts.append(f"**Type:** {coherence.get('type', '')}")
        parts.append("")
        for k, v in coherence.items():
            if k == "type":
                continue
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    # ── 16. Routing Algorithm (NEW, for NoC) ──
    routing = uarch.get("routing_algorithm")
    if routing:
        parts.append("## Routing Algorithm")
        parts.append("")
        parts.append(f"**Type:** {routing.get('type', '')}")
        parts.append("")
        for k, v in routing.items():
            if k == "type":
                continue
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    # ── 17. Flow Control (NEW, for NoC) ──
    flow_ctrl = uarch.get("flow_control")
    if flow_ctrl:
        parts.append("## Flow Control")
        parts.append("")
        for k, v in flow_ctrl.items():
            key_name = k.replace("_", " ").title()
            parts.append(f"- **{key_name}:** {v}")
        parts.append("")

    # ── 18. Interface Protocols (NEW: B4) ──
    protocols = enhanced.get("interface_protocols", [])
    if protocols:
        parts.append("## Interface Protocols")
        parts.append("")
        for p in protocols:
            parts.append(f"### {p.get('name', 'Interface')}")
            parts.append("")
            parts.append(f"- **Type:** {p.get('type', '')}")
            parts.append(f"- **Signals:** {p.get('signals', '')}")
            parts.append(f"- **Protocol:** {p.get('protocol', '')}")
            parts.append("")

    # ── 19. Reference Implementations ──
    ref_offset = 19 if (protocols or uarch) else 9
    if ref_summaries:
        parts.append("## Reference Implementations")
        parts.append("")

        for ref in ref_summaries:
            mod_name_ref = getattr(ref, "module_name", "unknown")
            relevance = getattr(ref, "relevance_score", 0.0)
            source_file = getattr(ref, "source_file", "")
            design_intent = getattr(ref, "design_intent", [])
            code_patterns = getattr(ref, "code_patterns", {})
            code_snippets = getattr(ref, "code_snippets", {})
            state_pattern = getattr(ref, "state_pattern", [])
            logic_pattern = getattr(ref, "logic_pattern", {})
            adaptation_notes = getattr(ref, "adaptation_notes", [])

            parts.append(f"### Reference: `{mod_name_ref}` (relevance: {relevance:.2f})")
            parts.append("")

            if source_file:
                parts.append(f"**Source:** `{source_file}`")
                parts.append("")

            if design_intent:
                parts.append("**Design Intent:**")
                for di in design_intent[:6]:
                    parts.append(f"- {di}")
                parts.append("")

            # Interface from code_patterns
            ports_info = code_patterns.get("ports", [])
            if ports_info:
                inp = [p["name"] for p in ports_info if p.get("direction") == "input"]
                out = [p["name"] for p in ports_info if p.get("direction") == "output"]
                parts.append(f"**Interface:** {len(inp)} inputs, {len(out)} outputs")
                if inp:
                    parts.append(f"- Inputs: {', '.join(f'`{n}`' for n in inp[:12])}")
                if out:
                    parts.append(f"- Outputs: {', '.join(f'`{n}`' for n in out[:12])}")
                parts.append("")

            # State variables from code_patterns
            state_vars = code_patterns.get("state_vars", [])
            if state_vars or state_pattern:
                parts.append("**State Variables:**")
                for sv in state_vars[:10]:
                    parts.append(
                        f"- {sv.get('kind', 'Reg')} `{sv.get('name', '?')}` "
                        f"(width={sv.get('width', '?')})"
                    )
                for sp in state_pattern[:6]:
                    parts.append(f"- {sp}")
                parts.append("")

            # Code patterns summary
            summary_patterns = code_patterns.get("summary_patterns", [])
            if summary_patterns:
                parts.append("**Code Patterns:**")
                for sp in summary_patterns[:6]:
                    parts.append(f"- {sp}")
                parts.append("")

            # FSM info
            fsm_summary = code_patterns.get("fsm_summary")
            if fsm_summary:
                state_reg = fsm_summary.get("state_reg", "?")
                num_trans = fsm_summary.get("num_transitions", 0)
                states = fsm_summary.get("states", [])
                parts.append(f"**FSM:** register `{state_reg}`, {num_trans} transitions")
                if states:
                    parts.append(f"- States: {', '.join(states[:10])}")
                parts.append("")

            # Handshake info
            handshakes = code_patterns.get("handshake_summary", [])
            if handshakes:
                parts.append("**Handshakes:**")
                for hs in handshakes[:4]:
                    parts.append(
                        f"- `{hs.get('valid', '?')}` / `{hs.get('ready', '?')}` "
                        f"(fire: {hs.get('fire', '?')})"
                    )
                parts.append("")

            # Derived flags
            derived = logic_pattern.get("derived_flags", [])
            if derived:
                parts.append(f"**Patterns:** {', '.join(derived)}")
                parts.append("")

            # Code snippets
            if code_snippets:
                for snippet_name, code in code_snippets.items():
                    parts.append(f"**Code Snippet ({snippet_name}):**")
                    parts.append("```python")
                    parts.append(code)
                    parts.append("```")
                    parts.append("")

            if adaptation_notes:
                parts.append("**Adaptation Notes:**")
                for note in adaptation_notes[:4]:
                    parts.append(f"- {note}")
                parts.append("")

    # ── Sub-Module Decomposition ──
    if sub_modules:
        parts.append("## Sub-Module Decomposition")
        parts.append("")
        parts.append("| Sub-Module | Type | Inputs | Outputs |")
        parts.append("|------------|------|--------|---------|")
        for sm in sub_modules:
            sm_name = getattr(sm, "name", "")
            sm_type = getattr(sm, "submod_type", "")
            sm_inputs = getattr(sm, "inputs", [])
            sm_outputs = getattr(sm, "outputs", [])
            inp_str = ", ".join(sm_inputs[:8])
            out_str = ", ".join(sm_outputs[:8])
            parts.append(f"| {sm_name} | {sm_type} | {inp_str} | {out_str} |")
        parts.append("")

    # ── Sub-Module Internal Connections (NEW: B3) ──
    submod_conns = enhanced.get("submodule_connections", [])
    if submod_conns:
        parts.append("## Sub-Module Internal Connections")
        parts.append("")
        parts.append("| From | To | Signal |")
        parts.append("|------|----|--------|")
        for c in submod_conns:
            parts.append(f"| {c.get('from', '')} | {c.get('to', '')} | {c.get('signal', '')} |")
        parts.append("")

    # ── Implementation Steps ──
    if implementation_steps:
        parts.append("## Implementation Steps")
        parts.append("")
        for i, step in enumerate(implementation_steps, 1):
            step_name = getattr(step, "name", "")
            step_goal = getattr(step, "goal", "")
            step_tags = getattr(step, "behavior_tags", [])
            line = f"{i}. **{step_name}**" if step_name else f"{i}."
            if step_goal:
                line += f" — {step_goal}"
            parts.append(line)
            if step_tags:
                parts.append(f"   Tags: {', '.join(step_tags)}")
        parts.append("")

    # ── Skeleton State (existing) ──
    if skeleton_state:
        parts.append("## Existing Skeleton State")
        parts.append("")
        for sv in skeleton_state:
            kind = sv.get("kind", "?")
            sv_name = sv.get("name", "?")
            width = sv.get("width", "")
            depth = sv.get("depth", "")
            hint = f"- {kind} `{sv_name}`"
            if width:
                hint += f" (width={width})"
            if depth:
                hint += f" (depth={depth})"
            parts.append(hint)
        parts.append("")

    if skeleton_hints:
        parts.append("### Existing Logic Hints")
        parts.append("")
        for h in skeleton_hints:
            parts.append(f"- {h}")
        parts.append("")

    # ── Golden Test Vectors (NEW: B5) ──
    golden_tests = enhanced.get("golden_tests", [])
    if golden_tests:
        parts.append("## Golden Test Vectors")
        parts.append("")
        for gt in golden_tests:
            name = gt.get("name", "Test")
            desc = gt.get("description", "")
            inputs = gt.get("inputs", {})
            expected = gt.get("expected", {})
            parts.append(f"### {name}")
            if desc:
                parts.append(f"**Description:** {desc}")
            parts.append("")
            if inputs:
                parts.append("**Inputs:**")
                for k, v in inputs.items():
                    parts.append(f"- `{k}` = {v}")
            if expected:
                parts.append("**Expected Outputs:**")
                for k, v in expected.items():
                    parts.append(f"- `{k}` = {v}")
            parts.append("")

    # ── Coding Rules ──
    if coding_rules:
        parts.append("## Coding Rules")
        parts.append("")
        for i, rule in enumerate(coding_rules, 1):
            parts.append(f"{i}. {rule}")
        parts.append("")

    # ── Verification Contract ──
    if verification_contract:
        parts.append("## Verification Contract")
        parts.append("")
        for vc in verification_contract:
            parts.append(f"- {vc}")
        parts.append("")

    return "\n".join(parts)


def generation_contexts_to_markdown(
    contexts: list,
    output_dir: str = "specs",
    modules: Optional[dict] = None,
) -> list:
    """Convert multiple GenerationContexts to markdown files.

    Args:
        contexts: List of (pe_name, GenerationContext) tuples
        output_dir: Directory to write specs into
        modules: Optional dict of {pe_name: Module} for FSM extraction

    Returns:
        List of written file paths
    """
    import os

    os.makedirs(output_dir, exist_ok=True)
    written_files = []

    for pe_name, gen_ctx in contexts:
        mod = None
        if modules and pe_name in modules:
            mod = modules[pe_name]
        md = generation_context_to_markdown(gen_ctx, module=mod)
        file_path = os.path.join(output_dir, f"{pe_name}_spec.md")
        with open(file_path, "w") as f:
            f.write(md)
        written_files.append(file_path)

    return written_files
