"""
rtlgen.behavior_extract — Behavior Requirement Extraction

Extracts structured behavior requirements from ProcessingElement definitions
by analyzing ports, state, and running behavior functions with sample inputs.

Output is a dict matching plan_0525.md Section 2 format:
  {name, behavior[], interfaces[], state[], control_patterns[], datapath_patterns[]}

Reference: skills/plan_0525.md Section 2
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Set

from rtlgen.arch_def import ArchDefinition, CycleContext, ProcessingElement


def extract_behavior_requirements(
    pe: ProcessingElement,
    arch: Optional[ArchDefinition] = None,
    sample_inputs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Extract structured behavior requirements from a ProcessingElement.

    Analyzes:
    1. Interface patterns from ports (valid-ready, request-response, etc.)
    2. State patterns from state descriptors (registers, FIFOs, masks)
    3. Control patterns by running behavior with sample inputs
    4. Datapath patterns by observing input→output data flow

    Args:
        pe: ProcessingElement to analyze
        arch: Optional ArchDefinition for interconnect context
        sample_inputs: Optional custom sample inputs; auto-generated if None

    Returns:
        Dict with keys: name, behavior, interfaces, state,
                        control_patterns, datapath_patterns
    """
    # 1. Interface patterns
    interfaces = _extract_interface_patterns(pe)

    # 2. State patterns
    state_patterns = _extract_state_patterns(pe)

    # 3. Generate sample inputs if not provided
    if sample_inputs is None:
        sample_inputs = _generate_sample_inputs(pe, num_samples=10)

    # 4. Run behavior to observe control and datapath patterns
    behavior_tags = []
    control_patterns = []
    datapath_patterns = []

    if pe.behavior is not None:
        behavior_tags, control_patterns, datapath_patterns = (
            _observe_behavior(pe, sample_inputs)
        )
    else:
        # Infer from PE type and port names
        behavior_tags = _infer_behavior_tags(pe)
        control_patterns = _infer_control_patterns(pe)
        datapath_patterns = _infer_datapath_patterns(pe)

    # 5. Add interconnect-derived patterns
    if arch:
        conn_patterns = _extract_interconnect_patterns(pe, arch)
        control_patterns.extend(conn_patterns)

    # Deduplicate
    control_patterns = list(dict.fromkeys(control_patterns))
    datapath_patterns = list(dict.fromkeys(datapath_patterns))

    return {
        "name": pe.name,
        "behavior": behavior_tags,
        "interfaces": interfaces,
        "state": state_patterns,
        "control_patterns": control_patterns,
        "datapath_patterns": datapath_patterns,
    }


def _extract_interface_patterns(pe: ProcessingElement) -> List[str]:
    """Extract interface protocol patterns from port names and structure."""
    patterns = []
    input_names = {p.name.lower() for p in pe.inputs}
    output_names = {p.name.lower() for p in pe.outputs}
    all_names = input_names | output_names

    # Valid-ready handshake detection
    patterns.extend(_detect_valid_ready_patterns(pe.inputs, pe.outputs))

    # Request-response pattern
    patterns.extend(_detect_request_response_patterns(pe.inputs, pe.outputs))

    # Broadcast/fan-out pattern (single input → multiple outputs with same prefix)
    patterns.extend(_detect_broadcast_patterns(pe.inputs, pe.outputs))

    # Pipeline stage pattern (valid_in/valid_out, ready_in/ready_out)
    if any("valid" in n for n in input_names) and any("valid" in n for n in output_names):
        patterns.append("pipeline_stage")

    # Multi-port pattern
    if len(pe.inputs) > 4 or len(pe.outputs) > 4:
        patterns.append("multi_port_interface")

    return patterns


def _detect_valid_ready_patterns(
    inputs: list, outputs: list
) -> List[str]:
    """Detect valid-ready handshake patterns."""
    patterns = []
    input_names = {p.name.lower() for p in inputs}
    output_names = {p.name.lower() for p in outputs}

    for name in input_names:
        if "valid" in name:
            # Check for matching ready signal
            ready_name = name.replace("valid", "ready")
            if ready_name in output_names:
                patterns.append(f"valid_ready_handshake:{name}")
            elif f"{name.replace('_valid', '')}_ready" in output_names:
                base = name.replace("_valid", "")
                patterns.append(f"valid_ready_handshake:{base}")

    for name in output_names:
        if "valid" in name:
            ready_name = name.replace("valid", "ready")
            if ready_name in input_names:
                patterns.append(f"valid_ready_handshake:{name}")

    return patterns


def _detect_request_response_patterns(
    inputs: list, outputs: list
) -> List[str]:
    """Detect request-response patterns."""
    patterns = []
    input_names = {p.name.lower() for p in inputs}
    output_names = {p.name.lower() for p in outputs}

    if any("req" in n for n in input_names) and any("rsp" in n for n in output_names):
        patterns.append("request_response")
    if any("request" in n for n in input_names) and any("response" in n for n in output_names):
        patterns.append("request_response")

    return patterns


def _detect_broadcast_patterns(inputs: list, outputs: list) -> List[str]:
    """Detect broadcast/fan-out patterns."""
    patterns = []

    # Check if a single input feeds multiple outputs
    for inp in inputs:
        prefix = inp.name.lower().rstrip("0123456789_").rstrip("_")
        matching_outputs = [
            o for o in outputs
            if o.name.lower().startswith(prefix)
        ]
        if len(matching_outputs) >= 3:
            patterns.append(f"broadcast:{inp.name}")

    return patterns


def _extract_state_patterns(pe: ProcessingElement) -> List[str]:
    """Extract state variable patterns from PE state descriptors."""
    patterns = []

    for s in pe.state:
        rtl_type = s.rtl_type or ""
        type_hint = s.type_hint or ""

        if rtl_type == "reg" or type_hint in ("int", "bitmask"):
            if s.rtl_width and s.rtl_width > 1:
                patterns.append(f"reg_vector:{s.name}[{s.rtl_width - 1}:0]")
            else:
                patterns.append(f"reg_scalar:{s.name}")
        elif rtl_type == "regfile" or type_hint == "dict":
            patterns.append(f"regfile:{s.name}")
        elif rtl_type == "memory":
            patterns.append(f"memory_array:{s.name}")
        elif rtl_type in ("queue", "fifo"):
            patterns.append(f"fifo:{s.name}")
        else:
            patterns.append(f"state_var:{s.name}")

        # Detect counter patterns
        if "count" in s.name.lower() or "ptr" in s.name.lower():
            patterns.append(f"counter:{s.name}")

        # Detect mask patterns
        if "mask" in s.name.lower():
            patterns.append(f"bitmask:{s.name}")

    return patterns


def _generate_sample_inputs(
    pe: ProcessingElement, num_samples: int = 10, seed: int = 42
) -> List[Dict[str, Any]]:
    """Generate diverse sample inputs for behavior observation."""
    rng = random.Random(seed)
    samples = []

    # Always include reset case
    reset_input = {}
    for port in pe.inputs:
        if port.name.lower() in ("rst_n", "reset", "rst"):
            reset_input[port.name] = 0
        else:
            reset_input[port.name] = 0
    samples.append(reset_input)

    # Release reset case
    release_reset = {}
    for port in pe.inputs:
        if port.name.lower() in ("rst_n", "reset", "rst"):
            release_reset[port.name] = 1
        else:
            release_reset[port.name] = 0
    samples.append(release_reset)

    # Random patterns
    for _ in range(num_samples - 2):
        inp = {}
        for port in pe.inputs:
            if port.name.lower() in ("rst_n", "reset", "rst"):
                inp[port.name] = 1  # Keep reset deasserted
            elif port.width <= 1:
                inp[port.name] = rng.randint(0, 1)
            elif port.width <= 8:
                inp[port.name] = rng.randint(0, 255)
            elif port.width <= 16:
                inp[port.name] = rng.randint(0, 0xFFFF)
            else:
                inp[port.name] = rng.randint(0, 0xFFFFFFFF)
        samples.append(inp)

    return samples


def _observe_behavior(
    pe: ProcessingElement,
    sample_inputs: List[Dict[str, Any]],
) -> tuple:
    """Run behavior function with sample inputs and observe patterns.

    Returns:
        (behavior_tags, control_patterns, datapath_patterns)
    """
    behavior_tags: List[str] = []
    control_patterns: List[str] = []
    datapath_patterns: List[str] = []

    output_set_history: List[Set[str]] = []
    state_change_history: List[Dict[str, Any]] = []

    for inp in sample_inputs:
        ctx = CycleContext(inputs=dict(inp))

        try:
            pe.behavior(ctx)
        except Exception:
            continue

        # Track which outputs were set
        output_set_history.append(set(ctx.outputs.keys()))

        # Track state changes
        if ctx.next_state:
            state_change_history.append(dict(ctx.next_state))

    # Analyze output patterns
    if output_set_history:
        # Detect which outputs are always set together
        always_set = set.intersection(*output_set_history) if output_set_history else set()
        sometimes_set = set.union(*output_set_history) - always_set

        if always_set:
            behavior_tags.append(f"always_outputs:{','.join(sorted(always_set))}")
        if sometimes_set:
            behavior_tags.append(f"conditional_outputs:{','.join(sorted(sometimes_set))}")

    # Analyze state transitions
    if state_change_history:
        all_changed_states = set()
        for changes in state_change_history:
            all_changed_states.update(changes.keys())

        if all_changed_states:
            control_patterns.append(f"state_variables:{','.join(sorted(all_changed_states))}")

        # Detect counter-like behavior (state values change monotonically)
        for state_name in all_changed_states:
            values = []
            for changes in state_change_history:
                if state_name in changes:
                    v = changes[state_name]
                    if isinstance(v, (int, float)):
                        values.append(v)
            if len(values) >= 3:
                if all(values[i] <= values[i + 1] for i in range(len(values) - 1)):
                    control_patterns.append(f"counter_increment:{state_name}")
                elif all(values[i] >= values[i + 1] for i in range(len(values) - 1)):
                    control_patterns.append(f"counter_decrement:{state_name}")

    # Detect datapath patterns: input → output mapping
    datapath_patterns = _infer_datapath_from_observations(
        pe, sample_inputs, output_set_history
    )

    # Infer behavior tags from PE type
    behavior_tags.extend(_infer_behavior_tags(pe))

    return list(set(behavior_tags)), control_patterns, datapath_patterns


def _infer_datapath_from_observations(
    pe: ProcessingElement,
    sample_inputs: List[Dict[str, Any]],
    output_set_history: List[Set[str]],
) -> List[str]:
    """Infer datapath patterns from observed input-output relationships."""
    patterns = []

    # Check for pass-through: output == input
    for idx, inp in enumerate(sample_inputs):
        if idx >= len(output_set_history):
            break
        # We can't observe actual values from behavior functions without
        # instrumenting them, but we can note the presence of output ports
        pass

    # Infer from port naming conventions
    datapath_patterns = _infer_datapath_patterns(pe)
    return datapath_patterns


def _infer_behavior_tags(pe: ProcessingElement) -> List[str]:
    """Infer behavior tags from PE type, description, and children."""
    tags = []
    pe_type = pe.pe_type.lower()
    desc = pe.description.lower()

    # Type-based inference
    type_tags = {
        "scheduler": ["scheduling", "resource_allocation"],
        "warp_scheduler": ["warp_scheduling", "round_robin", "scoreboard_check"],
        "cta_scheduler": ["workgroup_dispatch", "resource_allocation"],
        "alu": ["arithmetic", "logic", "comparison"],
        "lsu": ["memory_access", "load", "store", "cache_interface"],
        "ifu": ["instruction_fetch", "pc_generation", "branch_prediction"],
        "idu": ["instruction_decode", "register_read", "forwarding"],
        "cache": ["tag_lookup", "hit_miss_fsm", "refill"],
        "router": ["routing", "arbitration", "flow_control"],
        "arbiter": ["arbitration", "round_robin", "priority"],
        "fifo": ["buffering", "valid_ready", "overflow_protection"],
        "scoreboard": ["dependency_tracking", "busy_bit", "hazard_detection"],
        "writeback": ["result_writeback", "busy_clear", "retirement"],
    }

    for keyword, kw_tags in type_tags.items():
        if keyword in pe_type or keyword in desc:
            tags.extend(kw_tags)

    # Description-based inference
    keywords_in_desc = {
        "valid": "valid_ready_protocol",
        "ready": "valid_ready_protocol",
        "handshake": "valid_ready_protocol",
        "stall": "stall_control",
        "flush": "pipeline_flush",
        "barrier": "barrier_synchronization",
        "broadcast": "broadcast",
        "reduce": "reduction",
        "pipe": "pipeline",
        "queue": "queue_management",
        "buffer": "buffering",
        "allocate": "resource_allocation",
        "free": "resource_deallocation",
    }

    for keyword, tag in keywords_in_desc.items():
        if keyword in desc:
            tags.append(tag)

    return list(set(tags))


def _infer_control_patterns(pe: ProcessingElement) -> List[str]:
    """Infer control patterns from PE structure."""
    patterns = []
    pe_type = pe.pe_type.lower()

    control_map = {
        "scheduler": ["round_robin_selection", "ready_mask_generation"],
        "warp_scheduler": ["warp_active_tracking", "issue_selection", "rr_pointer"],
        "alu": ["opcode_decode", "pipe_dispatch"],
        "cache": ["hit_miss_fsm", "refill_fsm", "lru_update"],
        "fifo": ["full_empty_detection", "head_tail_pointer"],
        "arbiter": ["priority_encoding", "grant_generation"],
        "scoreboard": ["busy_bit_set", "busy_bit_clear", "hazard_check"],
    }

    for keyword, kw_patterns in control_map.items():
        if keyword in pe_type:
            patterns.extend(kw_patterns)

    return patterns


def _infer_datapath_patterns(pe: ProcessingElement) -> List[str]:
    """Infer datapath patterns from PE structure and port names."""
    patterns = []
    pe_type = pe.pe_type.lower()
    all_port_names = {p.name.lower() for p in pe.inputs + pe.outputs}

    # Type-based inference
    datapath_map = {
        "alu": ["alu_execute", "operand_mux"],
        "lsu": ["address_calculation", "load_store_mux"],
        "cache": ["tag_compare", "data_select"],
        "fifo": ["fifo_push_pop", "data_shift"],
        "scoreboard": ["bitwise_and", "bitwise_or"],
    }

    for keyword, kw_patterns in datapath_map.items():
        if keyword in pe_type:
            patterns.extend(kw_patterns)

    # Port-based inference
    if any("addr" in n for n in all_port_names):
        patterns.append("address_calculation")
    if any("data" in n for n in all_port_names) and any("valid" in n for n in all_port_names):
        patterns.append("valid_gated_data")
    if any("result" in n or "rdata" in n for n in all_port_names):
        patterns.append("result_forwarding")

    return list(set(patterns))


def _extract_interconnect_patterns(
    pe: ProcessingElement, arch: ArchDefinition
) -> List[str]:
    """Extract patterns from PE's interconnects in the architecture."""
    patterns = []

    for conn in arch.interconnects:
        if conn.src_pe == pe.name or conn.dst_pe == pe.name:
            if conn.handshake:
                patterns.append(f"handshake:{conn.handshake.valid_signal}/{conn.handshake.ready_signal}")
            if conn.queue:
                patterns.append(f"fifo_buffer:depth={conn.queue.depth}")
            if conn.delay_cycles > 0:
                patterns.append(f"latency:{conn.delay_cycles}_cycles")

    return list(set(patterns))
