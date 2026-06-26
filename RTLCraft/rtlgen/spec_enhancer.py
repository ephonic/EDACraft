"""
rtlgen.spec_enhancer — Enhance GenerationContext with FSM, interconnect, and architecture details.

Extracts structured information from Module objects and ArchDefinition
that was previously lost during serialization to spec markdown.
"""
from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional, Tuple

from rtlgen.core import Module


# =====================================================================
# FSM Extraction from Module seq/comb blocks
# =====================================================================

def extract_fsms(module: Module) -> List[Dict[str, Any]]:
    """Extract FSM state machines from a Module's seq and comb blocks.

    Analyzes sequential blocks for state register patterns:
      - reg_name <<= CONSTANT_VALUE (state transitions)
      - Switch/Case patterns

    Returns a list of FSM descriptions:
      {
        "state_reg": "cache_fsm",
        "width": 2,
        "states": ["IDLE", "CHECK", "REFILL"],
        "transitions": [
            {"from": "IDLE", "to": "CHECK", "condition": "req == 1"},
            {"from": "CHECK", "to": "IDLE", "condition": "hit == 1"},
            ...
        ],
      }
    """
    fsms = []

    seq_blocks = getattr(module, "_seq_blocks", [])
    # seq_blocks entries are tuples: (clk, rst, reset_async, reset_active_low, body_list)
    for entry in seq_blocks:
        body = None
        if isinstance(entry, tuple) and len(entry) >= 5:
            body = entry[4]
        elif hasattr(entry, "_body"):
            body = entry._body
        elif hasattr(entry, "body"):
            body = entry.body
        if body is None:
            continue
        fsm = _analyze_seq_for_fsm(body)
        if fsm:
            fsms.append(fsm)

    return fsms


def _analyze_seq_for_fsm(body_list: list) -> Optional[Dict[str, Any]]:
    """Analyze a seq block body looking for FSM patterns: state regs and Switch/Case.
    
    The body_list contains AST nodes: IfNode, SwitchNode, Assign, etc.
    """
    from rtlgen.core import Assign, IfNode, SwitchNode, GenIfNode

    # Step 1: look for state registers (regs assigned to constants)
    # Collect all assignments recursively through the AST
    state_candidates = set()
    switch_exprs = {}  # switch_expr_name → list of case bodies

    _walk_ast(body_list, _build_collector(state_candidates, switch_exprs))

    if not state_candidates:
        return None

    state_reg = sorted(state_candidates, key=lambda x: -len(x))[0]
    
    if not switch_exprs:
        return None

    # Find the switch that matches our state register
    switch_expr_name = None
    for expr_name, cases in switch_exprs.items():
        if expr_name == state_reg:
            switch_expr_name = expr_name
            break

    if switch_expr_name is None:
        return None

    cases = switch_exprs[switch_expr_name]
    states = _extract_switch_states(cases)
    transitions = _extract_switch_transitions(state_reg, cases)
    width = _infer_fsm_width(states)

    return {
        "state_reg": state_reg,
        "width": width,
        "states": states,
        "transitions": transitions,
    }


def _walk_ast(nodes: list, callbacks: dict):
    """Walk AST nodes recursively, calling callbacks for each node type.
    
    callbacks: {type_name: fn(node)} or special keys like 'assign' and 'body_list'
    """
    from rtlgen.core import Assign, IfNode, SwitchNode, GenIfNode

    assign_fn = callbacks.get('assign')
    ifnode_fn = callbacks.get('ifnode')
    switchnode_fn = callbacks.get('switchnode')

    for node in list(nodes):
        if isinstance(node, Assign):
            if assign_fn:
                assign_fn(node)
        elif isinstance(node, (IfNode, GenIfNode)):
            if ifnode_fn:
                ifnode_fn(node)
            _walk_ast(node.then_body, callbacks)
            for _, elif_body in getattr(node, 'elif_bodies', []):
                _walk_ast(elif_body, callbacks)
            _walk_ast(node.else_body, callbacks)
        elif isinstance(node, SwitchNode):
            if switchnode_fn:
                switchnode_fn(node)
            for case_val, case_body in node.cases:
                _walk_ast(case_body, callbacks)
            _walk_ast(node.default_body, callbacks)
        elif isinstance(node, list):
            _walk_ast(node, callbacks)


def _signal_name(sig) -> str:
    """Extract signal name from a signal/ref object."""
    if hasattr(sig, '_name'):
        return sig._name
    if hasattr(sig, 'name'):
        return sig.name
    if hasattr(sig, '_signal') and hasattr(sig._signal, '_name'):
        return sig._signal._name
    return str(sig)


def _ref_name(expr) -> str:
    """Extract signal name from an expression (Ref or other)."""
    from rtlgen.core import Ref
    if isinstance(expr, Ref):
        return _signal_name(expr.signal)
    return _signal_name(expr)


def _build_collector(state_candidates: set, switch_exprs: dict) -> dict:
    """Build callbacks dict for FSM state reg and switch collection."""
    from rtlgen.core import SwitchNode

    def on_assign(node):
        from rtlgen.core import Const, Ref
        target = node.target
        value = node.value
        target_name = _ref_name(target) if not isinstance(target, Ref) else _signal_name(getattr(target, 'signal', target))
        if isinstance(target, Ref):
            target_name = _signal_name(target.signal)
        elif hasattr(target, '_name'):
            target_name = target._name
        if target_name and _is_const_val(value):
            state_candidates.add(target_name)

    def on_switchnode(node):
        from rtlgen.core import Ref
        expr = node.expr
        name = _ref_name(expr)
        if name:
            switch_exprs[name] = list(node.cases)

    return {'assign': on_assign, 'switchnode': on_switchnode}


def _is_const_val(value) -> bool:
    """Check if value is a constant."""
    from rtlgen.core import Const
    if isinstance(value, int):
        return True
    if isinstance(value, Const):
        return True
    return False


def _extract_switch_states(cases: list) -> list:
    """Extract state names from Switch case values."""
    from rtlgen.core import Const

    state_names = []
    for case_val, _ in cases:
        if isinstance(case_val, int):
            name = _state_int_to_name(case_val)
            if name and name not in state_names:
                state_names.append(name)
        elif isinstance(case_val, Const):
            name = _state_int_to_name(case_val.value) if hasattr(case_val, 'value') else str(case_val)
            if name and name not in state_names:
                state_names.append(name)
        else:
            name = str(case_val)
            if name not in state_names:
                state_names.append(name)
    return state_names if state_names else ["IDLE", "BUSY", "DONE"]


def _state_int_to_name(val: int) -> str:
    """Map an integer state value to a common state name."""
    COMMON_STATES = [
        "IDLE", "CHECK", "TAG_CHECK", "REFILL", "REFILL_WAIT", "REFILL_STORE",
        "DELIVER", "LOOKUP", "PROBE", "UPDATE", "WRITEBACK",
        "FETCH", "DECODE", "EXECUTE", "MEMORY", "WRITEBACK",
        "S_IDLE", "S_CHECK", "S_REFILL",
    ]
    if 0 <= val < len(COMMON_STATES):
        return COMMON_STATES[val]
    return f"STATE_{val}"


def _extract_switch_transitions(state_reg: str, cases: list) -> list:
    """Extract state transitions from Switch case bodies."""
    from rtlgen.core import Assign, Const, Ref

    transitions = []
    for case_val, case_body in cases:
        from_state = _format_val_nice(case_val)
        cond = f"{state_reg} == {from_state}"

        assigns = _collect_flat_assigns(case_body)
        for assign in assigns:
            target = assign.target
            value = assign.value
            target_name = _ref_name(target)
            
            if target_name == state_reg:
                to_val = _format_val_nice(value)
                transitions.append({
                    "from": from_state,
                    "to": to_val,
                    "condition": cond,
                })

    return transitions


def _format_val_nice(val) -> str:
    """Format a value, mapping integers to common state names."""
    from rtlgen.core import Const
    if isinstance(val, int):
        return _state_int_to_name(val)
    if isinstance(val, Const):
        v = getattr(val, 'value', None)
        if isinstance(v, int):
            return _state_int_to_name(v)
        return str(v)
    return str(val)


def _collect_flat_assigns(nodes: list, depth=0) -> list:
    """Flatten nested AST to collect all Assign nodes."""
    from rtlgen.core import Assign, IfNode, SwitchNode, GenIfNode

    if depth > 10:
        return []

    results = []
    for node in list(nodes):
        if isinstance(node, Assign):
            results.append(node)
        elif isinstance(node, (IfNode, GenIfNode)):
            results.extend(_collect_flat_assigns(node.then_body, depth + 1))
            for _, elif_body in getattr(node, 'elif_bodies', []):
                results.extend(_collect_flat_assigns(elif_body, depth + 1))
            results.extend(_collect_flat_assigns(node.else_body, depth + 1))
        elif isinstance(node, SwitchNode):
            for _, case_body in node.cases:
                results.extend(_collect_flat_assigns(case_body, depth + 1))
            results.extend(_collect_flat_assigns(node.default_body, depth + 1))
        elif isinstance(node, list):
            results.extend(_collect_flat_assigns(node, depth + 1))
    return results


def _format_val_simple(val) -> str:
    """Format a value for display in FSM transition table."""
    from rtlgen.core import Const
    if isinstance(val, int):
        return _state_int_to_name(val)
    if isinstance(val, Const):
        v = getattr(val, 'value', None)
        if isinstance(v, int):
            return _state_int_to_name(v)
        return str(v)
    if hasattr(val, 'name'):
        return val.name
    return str(val)


def _infer_fsm_width(states: list) -> int:
    """Infer FSM register width from number of states."""
    n = len(states)
    if n <= 2:
        return 1
    if n <= 4:
        return 2
    if n <= 8:
        return 3
    if n <= 16:
        return 4
    return 5


# =====================================================================
# Architecture description by PE type
# =====================================================================

ARCH_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    "rv64_core": {
        "title": "5-Stage RISC-V Pipeline",
        "stages": [
            {"name": "Fetch", "function": "PC generation, I-Cache request, instruction fetch"},
            {"name": "Decode", "function": "Instruction decode, register read, immediate generation, forwarding mux"},
            {"name": "Execute", "function": "ALU operations, branch comparison, address calculation"},
            {"name": "Memory", "function": "D-Cache access, load/store data path"},
            {"name": "Writeback", "function": "Result write to register file, forwarding to decode"},
        ],
        "features": [
            "3-stage forwarding (EX/MEM/WB)",
            "Load-use hazard stall",
            "All RV64I instruction types (R/I/S/B/U/J)",
            "Branch redirect with target calculation",
            "I-Cache / D-Cache interface with valid/ready handshake",
        ],
    },
    "l1_cache": {
        "title": "Direct-Mapped Cache with MSI Coherence",
        "stages": [],
        "features": [
            "Tag RAM with valid bits",
            "Data RAM with line-size storage",
            "Hit/miss detection (tag comparison)",
            "MSI coherence state (Invalid/Shared/Modified)",
            "Refill FSM: IDLE → TAG_CHECK → REFILL_WAIT → REFILL_STORE → DELIVER",
            "LRU replacement policy",
            "Snoop invalidation handling",
        ],
    },
    "noc_router": {
        "title": "5-Port NoC Router with XY Routing",
        "stages": [],
        "features": [
            "5 ports: East, West, North, South, Local (injection/ejection)",
            "Per-port input FIFO buffers (4-deep)",
            "XY deterministic routing (X-first, then Y)",
            "5×5 crossbar switch",
            "Priority arbitration: North > South > East > West > Local",
            "Valid/ready handshake flow control",
            "Wormhole switching (header flit routing, body/tail follow)",
        ],
    },
    "coherence_dir": {
        "title": "MSI Coherence Directory",
        "stages": [],
        "features": [
            "Directory entry: tag + MSI state + sharers bitmask + owner",
            "64-core sharers tracking",
            "Shared request: add sharer, M→S downgrade if needed",
            "Modified request: invalidate current owner, grant new owner",
            "Snoop invalidation generation",
            "Lookup FSM: IDLE → LOOKUP → PROBE → UPDATE → WRITEBACK",
        ],
    },
    "l2_cache": {
        "title": "L2 Cache Slice with DRAM Interface",
        "stages": [],
        "features": [
            "Tag RAM + Data RAM (larger than L1)",
            "LRU replacement",
            "Cache FSM: IDLE → LOOKUP → REFILL → WRITEBACK",
            "DRAM request/response interface",
            "Snoop invalidation from directory, writeback dirty lines",
        ],
    },
    "ooo_core": {
        "title": "2-Wide Out-of-Order RISC-V Core",
        "stages": [
            {"name": "Fetch", "function": "2-wide fetch from I-Cache, branch prediction (gshare PHT + BTB + RAS), PC generation"},
            {"name": "Decode", "function": "2-wide decode: opcode/funct3/funct7/rs1/rs2/rd/immediate extraction per instruction"},
            {"name": "Rename", "function": "Arch→Phys register map read, free list pop, map update for rd; 2-wide rename per cycle"},
            {"name": "Issue (Wakeup)", "function": "IQ wakeup logic: broadcast physical register tags to all waiting instructions"},
            {"name": "Issue (Select)", "function": "IQ select logic: pick oldest-ready instructions for dispatch to EX units"},
            {"name": "Execute", "function": "ALU(arith/logic), AGU(load/store addr), BRU(branch/resolve) — all with full bypass"},
            {"name": "Commit", "function": "ROB retire up to 2 instr/cycle, update arch regfile, free old phys regs"},
        ],
        "features": [
            "2-wide fetch/decode/rename/commit (superscalar width=2)",
            "64-entry Reorder Buffer (ROB) for out-of-order completion and precise exceptions",
            "32-entry unified Issue Queue (IQ) with wakeup-select logic",
            "128-entry Physical Register File (PRF), 6 read ports, 4 write ports",
            "Register rename with map table (32 entries × 7-bit phys reg index) + free list",
            "Gshare branch predictor: 4096-entry PHT (2-bit saturating counters), 64-entry BTB",
            "Load/Store Queue (LSQ): 16 loads + 16 stores, with memory dependency prediction",
            "Full bypass network: EX→EX (ALU), MEM→EX (load data), WB→EX (any result)",
            "MESI-coherent L1 I/D caches (separate, 32KB each, 8-way set-associative)",
            "Performance target: IPC > 1.5 for SPECint2006, 2.0 GHz on 7nm",
        ],
    },
    "pcgen": {
        "title": "PC Generation with L0 BTB",
        "stages": [],
        "features": [
            "4-entry L0 BTB (fastest, single-cycle)",
            "Next-PC calculation: PC+8 (sequential), BTB target, branch target",
            "Branch redirect flush with 1-cycle penalty",
            "RAS (Return Address Stack) for JALR predictions",
        ],
    },
    "bpred": {
        "title": "Gshare Branch Predictor with BTB",
        "stages": [],
        "features": [
            "4096-entry gshare PHT (2-bit saturating counters)",
            "64-entry BTB (4-way set-associative)",
            "8-entry RAS (Return Address Stack)",
            "Prediction update on branch execution (resolve)",
            "Speculative history for gshare XOR",
        ],
    },
    "rename": {
        "title": "Register Rename Table",
        "stages": [],
        "features": [
            "32-entry architectural→physical register mapping table",
            "Free list with 128 physical integer registers",
            "Checkpoint for precise exception recovery",
            "2-wide rename per cycle",
            "Branch checkpoint save/restore for misprediction recovery",
        ],
    },
    "coherence_bus": {
        "title": "MESI Snooping Coherence Bus",
        "stages": [],
        "features": [
            "MESI protocol (Invalid/Shared/Exclusive/Modified)",
            "3-state snoop FSM: IDLE → SNOOP_BROADCAST → SNOOP_WAIT → RESPONSE",
            "Snoop address broadcast to all cores simultaneously",
            "Snoop response collection with timeout (acks from all caches)",
            "Cache-to-cache transfer: dirty data forwarded directly between caches",
            "Writeback handling: dirty eviction data written to L2 via bus",
            "Bus arbitration: round-robin among requesting cores",
            "Transaction ordering: total store ordering (TSO) compatible",
        ],
    },
    "ifu": {
        "title": "Instruction Fetch Unit",
        "stages": [],
        "features": [
            "PC register with reset to 0x1000 (boot ROM)",
            "I-Cache request/response interface",
            "Branch redirect: flush fetch, load new PC on branch/jump",
            "Next-PC calculation: PC+4 sequential, branch target, jump target",
            "Stall on I-Cache miss",
        ],
    },
    "idu": {
        "title": "Instruction Decode Unit",
        "stages": [],
        "features": [
            "Instruction decode: opcode, funct3, funct7, rs1, rs2, rd extraction",
            "Immediate generation: I/S/B/U/J format sign-extension",
            "Register file read (32×64-bit)",
            "WB-stage forwarding: bypass writeback data to read ports",
            "Pass decoded instruction + operands to Execute stage",
        ],
    },
    "alu": {
        "title": "ALU Execution Unit",
        "stages": [],
        "features": [
            "10 RV64I ALU operations: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU",
            "Branch comparison: BEQ/BNE/BLT/BGE/BLTU/BGEU",
            "Branch target calculation",
            "Load/store address calculation",
            "Jump target calculation (JAL/JALR)",
        ],
    },
    "lsu": {
        "title": "Load/Store Unit",
        "stages": [],
        "features": [
            "D-Cache request/response interface",
            "Load data path: cache read data → writeback",
            "Store data path: register value → cache write data",
            "Stall on D-Cache miss",
            "Address calculation: base + immediate offset",
        ],
    },
    "wb": {
        "title": "Writeback Unit",
        "stages": [],
        "features": [
            "Register file writeback",
            "Forwarding result to Decode stage",
            "Retire counter increment",
            "Core stall/halt status output",
        ],
    },
}


def get_arch_description(pe_type: str) -> Optional[Dict[str, Any]]:
    """Get structured architecture description for a PE type."""
    return ARCH_DESCRIPTIONS.get(pe_type)


# =====================================================================
# Sub-module internal connection extraction
# =====================================================================

SUBMODULE_CONNECTIONS: Dict[str, List[Dict[str, str]]] = {
    "rv64_core": [
        {"from": "ifu.fetch_valid", "to": "idu.fetch_valid", "signal": "fetch_valid"},
        {"from": "ifu.fetch_instr", "to": "idu.fetch_instr", "signal": "fetch_instr[31:0]"},
        {"from": "ifu.fetch_pc", "to": "idu.fetch_pc", "signal": "fetch_pc[63:0]"},
        {"from": "idu.exec_valid", "to": "alu.exec_valid", "signal": "exec_valid"},
        {"from": "idu.dec_ra", "to": "alu.dec_ra", "signal": "dec_ra[63:0]"},
        {"from": "idu.dec_rb", "to": "alu.dec_rb", "signal": "dec_rb[63:0]"},
        {"from": "idu.opcode", "to": "alu.opcode", "signal": "opcode[6:0]"},
        {"from": "idu.funct3", "to": "alu.funct3", "signal": "funct3[2:0]"},
        {"from": "idu.funct7", "to": "alu.funct7", "signal": "funct7[6:0]"},
        {"from": "idu.rd", "to": "alu.rd", "signal": "rd[4:0]"},
        {"from": "idu.wb_en", "to": "alu.wb_en", "signal": "wb_en"},
        {"from": "alu.mem_valid", "to": "lsu.mem_valid", "signal": "mem_valid"},
        {"from": "alu.exec_alu_result", "to": "lsu.mem_addr", "signal": "mem_addr[63:0]"},
        {"from": "alu.mem_wb_en", "to": "lsu.mem_wb_en", "signal": "mem_wb_en"},
        {"from": "alu.mem_rd", "to": "lsu.mem_rd", "signal": "mem_rd[4:0]"},
        {"from": "alu.branch_taken", "to": "ifu.branch_taken", "signal": "branch_taken"},
        {"from": "alu.branch_target", "to": "ifu.branch_target", "signal": "branch_target[63:0]"},
        {"from": "lsu.wb_valid", "to": "wb.wb_valid", "signal": "wb_valid"},
        {"from": "lsu.wb_result", "to": "wb.wb_result", "signal": "wb_result[63:0]"},
        {"from": "lsu.wb_rd", "to": "wb.wb_rd", "signal": "wb_rd[4:0]"},
        {"from": "lsu.wb_wb_en", "to": "wb.wb_wb_en", "signal": "wb_wb_en"},
        {"from": "wb.wb_fwd_valid", "to": "idu.wb_fwd_valid", "signal": "wb_fwd_valid"},
        {"from": "wb.wb_fwd_result", "to": "idu.wb_fwd_result", "signal": "wb_fwd_result[63:0]"},
        {"from": "wb.wb_fwd_rd", "to": "idu.wb_fwd_rd", "signal": "wb_fwd_rd[4:0]"},
    ],
    "l1_cache": [
        {"from": "tag_ram.hit", "to": "cache_fsm.hit", "signal": "hit"},
        {"from": "data_ram.rdata", "to": "cache_fsm.data_rdata", "signal": "data_rdata[63:0]"},
        {"from": "cache_fsm.index", "to": "tag_ram.index", "signal": "index"},
        {"from": "cache_fsm.index", "to": "data_ram.index", "signal": "index"},
        {"from": "cache_fsm.tag_in", "to": "tag_ram.tag_in", "signal": "tag_in"},
    ],
    "noc_router": [
        {"from": "input_buf_e.e_flit_out", "to": "route_logic.e_flit", "signal": "e_flit[63:0]"},
        {"from": "input_buf_w.w_flit_out", "to": "route_logic.w_flit", "signal": "w_flit[63:0]"},
        {"from": "input_buf_n.n_flit_out", "to": "route_logic.n_flit", "signal": "n_flit[63:0]"},
        {"from": "input_buf_s.s_flit_out", "to": "route_logic.s_flit", "signal": "s_flit[63:0]"},
        {"from": "input_buf_j.j_flit_out", "to": "route_logic.j_flit", "signal": "j_flit[63:0]"},
        {"from": "route_logic.grant_e", "to": "crossbar.grant_e", "signal": "grant_e"},
        {"from": "route_logic.grant_w", "to": "crossbar.grant_w", "signal": "grant_w"},
        {"from": "route_logic.grant_n", "to": "crossbar.grant_n", "signal": "grant_n"},
        {"from": "route_logic.grant_s", "to": "crossbar.grant_s", "signal": "grant_s"},
        {"from": "route_logic.grant_j", "to": "crossbar.grant_j", "signal": "grant_j"},
        {"from": "input_buf_e.e_flit_out", "to": "crossbar.e_flit", "signal": "e_flit[63:0]"},
        {"from": "input_buf_w.w_flit_out", "to": "crossbar.w_flit", "signal": "w_flit[63:0]"},
        {"from": "input_buf_n.n_flit_out", "to": "crossbar.n_flit", "signal": "n_flit[63:0]"},
        {"from": "input_buf_s.s_flit_out", "to": "crossbar.s_flit", "signal": "s_flit[63:0]"},
        {"from": "input_buf_j.j_flit_out", "to": "crossbar.j_flit", "signal": "j_flit[63:0]"},
    ],
    "coherence_dir": [
        {"from": "snoop_gen.snoop_req", "to": "resp_arb.snoop_req", "signal": "snoop_req"},
        {"from": "dir_ram.dir_state", "to": "snoop_gen.dir_state", "signal": "dir_state[2:0]"},
        {"from": "dir_ram.dir_state", "to": "resp_arb.dir_state", "signal": "dir_state[2:0]"},
    ],
}


def get_submodule_connections(pe_type: str) -> List[Dict[str, str]]:
    """Get sub-module internal connections for a PE type."""
    return SUBMODULE_CONNECTIONS.get(pe_type, [])


# =====================================================================
# Behavior pseudo-code extraction
# =====================================================================

BEHAVIOR_PSEUDOCODE: Dict[str, str] = {
    "rv64_core": """每个周期:
  stall = input.stall
  if stall: output.retire_valid = 0; return
  pc = state.pc (default 0x1000)
  iss_result = model.isa_step()
  if iss_result.done:
    pc = model.get_pc()
    output.retire_valid = 1
  else:
    pc = pc + 4
    output.retire_valid = 1
  state.pc = pc
  output.pc_out = pc""",

    "l1_cache": """每个周期:
  addr = input.addr
  if not input.req_valid:
    output.valid = 0; output.ready = 0; return
  hit = cache_hit("l1", addr)
  if hit:
    output.valid = 1; output.ready = 1
    output.miss = 0; output.stall = 0
  else:
    output.valid = 0; output.ready = 0
    output.miss = 1; output.stall = 1
    coherence_request("read_shared", addr)""",

    "noc_router": """每个周期:
  x = input.x; y = input.y
  dest_x = input.dest_x; dest_y = input.dest_y
  if input.flit_valid:
    if dest_x > x: route_east = 1
    elif dest_x < x: route_west = 1
    elif dest_y > y: route_north = 1
    elif dest_y < y: route_south = 1
    else: route_local = 1
  output.route_* = route_*""",

    "coherence_dir": """每个周期:
  if not input.req_valid: output.grant = 0; return
  tag = input.addr >> 12
  dir_state = state.dir_state[tag]
  if req_type == 1 (Modified):
    invalidate current owner if different
    set new owner
  else (Shared):
    add sharer, downgrade M→S if needed
  state.dir_state[tag] = updated entry
  output.grant = 1
  output.grant_state = state""",
}


def get_behavior_pseudocode(pe_type: str) -> str:
    """Get behavior pseudo-code for a PE type."""
    return BEHAVIOR_PSEUDOCODE.get(pe_type, "")


# =====================================================================
# Golden test vectors
# =====================================================================

GOLDEN_TESTS: Dict[str, List[Dict[str, Any]]] = {
    "rv64_core": [
        {
            "name": "NOP Execution",
            "inputs": {"icache_valid": 1, "icache_rdata": 0x00000013, "rst_n": 1},
            "expected": {"icache_req": 0, "fetch_valid": 1, "retire_valid": 1},
            "description": "NOP (0x00000013) should flow through pipeline and retire",
        },
        {
            "name": "I-Cache Stall",
            "inputs": {"icache_valid": 0, "rst_n": 1},
            "expected": {"icache_req": 1, "fetch_valid": 0},
            "description": "When I-Cache is not valid, pipeline stalls and requests cache",
        },
        {
            "name": "Reset State",
            "inputs": {"rst_n": 0},
            "expected": {"core_stall": 0, "retire_valid": 0},
            "description": "After reset, all outputs should be zero",
        },
    ],
    "l1_cache": [
        {
            "name": "Cache Hit",
            "inputs": {"req": 1, "addr": 0x1000},
            "expected": {"valid": 1, "ready": 1, "miss": 0},
            "description": "After initial fill, same address should hit",
        },
    ],
    "noc_router": [
        {
            "name": "XY Routing East",
            "inputs": {"x_pos": 1, "y_pos": 1, "dest_x": 3, "dest_y": 1, "flit_valid": 1},
            "expected": {"route_east": 1},
            "description": "Destination X > current X → route East",
        },
        {
            "name": "XY Routing North",
            "inputs": {"x_pos": 3, "y_pos": 1, "dest_x": 3, "dest_y": 4, "flit_valid": 1},
            "expected": {"route_north": 1},
            "description": "Same X, Destination Y > current Y → route North",
        },
    ],
}


def get_golden_tests(pe_type: str) -> List[Dict[str, Any]]:
    """Get golden test vectors for a PE type."""
    return GOLDEN_TESTS.get(pe_type, [])


# =====================================================================
# Interface protocol descriptions
# =====================================================================

INTERFACE_PROTOCOLS: Dict[str, List[Dict[str, str]]] = {
    "rv64_core": [
        {
            "name": "I-Cache Interface",
            "type": "valid/ready handshake",
            "signals": "icache_req (output), icache_addr (output), icache_rdata (input), icache_valid (input), icache_ready (output)",
            "protocol": "Core asserts icache_req when it needs an instruction. Cache responds with icache_valid when data is ready. Core absorbs data when both valid & ready are high.",
        },
        {
            "name": "D-Cache Interface",
            "type": "valid/ready handshake with write enable",
            "signals": "dcache_req (output), dcache_addr (output), dcache_wdata (output), dcache_wen (output), dcache_rdata (input), dcache_valid (input), dcache_ready (output)",
            "protocol": "Core asserts dcache_req + dcache_wen for stores, dcache_req alone for loads. Cache returns dcache_valid + dcache_rdata for loads.",
        },
    ],
    "ifu": [
        {
            "name": "I-Cache Interface",
            "type": "valid/ready handshake",
            "signals": "icache_req, icache_addr[63:0], icache_rdata[63:0], icache_valid, icache_ready",
            "protocol": "IFU asserts icache_req + icache_addr when fetch_valid=0. Cache returns icache_valid + icache_rdata on hit. On branch redirect, IFU flushes fetch and loads new PC target.",
        },
        {
            "name": "Branch Redirect",
            "type": "combinational flush + redirect",
            "signals": "branch_redirect, branch_target[63:0]",
            "protocol": "When branch_redirect=1: IFU flushes current fetch (fetch_valid=0), loads branch_target as new PC next cycle. Redirect takes 1 cycle penalty.",
        },
    ],
    "idu": [
        {
            "name": "Decode → Execute Pipeline",
            "type": "pipeline register with stall",
            "signals": "exec_valid, exec_instr[31:0], decode_pc[63:0], dec_ra[63:0], dec_rb[63:0], opcode[6:0], funct3[2:0], rd[4:0], imm_*",
            "protocol": "IDU asserts exec_valid when decode is done. Execute stage samples on rising edge when dcache_stall=0. Backpressure via exec_valid handshake: if EX stage is stalled, IDU holds decode_valid.",
        },
        {
            "name": "WB Forwarding",
            "type": "combinational bypass",
            "signals": "wb_fwd_valid, wb_fwd_result[63:0], wb_fwd_rd[4:0]",
            "protocol": "When wb_fwd_valid && (rs1 == wb_fwd_rd): dec_ra = wb_fwd_result (bypass register file). Same for rs2. Zero-cycle forward from WB to D stage.",
        },
    ],
    "alu": [
        {
            "name": "IDU → ALU Interface",
            "type": "pipeline register with stall",
            "signals": "exec_valid, dec_ra[63:0], dec_rb[63:0], opcode[6:0], funct3[2:0], funct7[6:0], imm_*",
            "protocol": "ALU receives decoded operands from IDU via pipeline registers. When exec_valid=1 and dcache_stall=0, ALU computes result in 1 cycle. exec_valid held low when stall is active.",
        },
        {
            "name": "ALU → LSU Interface",
            "type": "pipeline register",
            "signals": "mem_valid, mem_alu_result[63:0], mem_rd[4:0], mem_is_load, mem_wb_en",
            "protocol": "ALU passes computed address (mem_alu_result) and control signals to LSU via pipeline register. mem_valid=1 indicates valid memory operation. LSU samples on next cycle.",
        },
        {
            "name": "ALU → IFU (Branch Redirect)",
            "type": "combinational redirect",
            "signals": "branch_taken, branch_target[63:0]",
            "protocol": "When branch_taken=1: IFU flushes fetch pipeline and jumps to branch_target. Combinational path: ALU computes comparison and target in execute stage, result available same cycle for flush.",
        },
    ],
    "lsu": [
        {
            "name": "ALU → LSU Interface",
            "type": "pipeline register",
            "signals": "mem_valid, mem_alu_result[63:0], mem_rd[4:0], mem_is_load, mem_wb_en",
            "protocol": "LSU receives memory address and control from ALU. When mem_valid=1 and dcache_stall=0: for load, send dcache_req; for store, send dcache_req + dcache_wdata.",
        },
        {
            "name": "D-Cache Interface",
            "type": "valid/ready with RW control",
            "signals": "dcache_req, dcache_addr[63:0], dcache_wdata[63:0], dcache_wen, dcache_rdata[63:0], dcache_valid",
            "protocol": "Load: dcache_req=1, dcache_wen=0, addr=mem_alu_result. Store: dcache_req=1, dcache_wen=1, addr=mem_alu_result, wdata=rb. Cache returns dcache_valid + dcache_rdata for loads. LSU stalls when dcache_valid=0.",
        },
    ],
    "wb": [
        {
            "name": "LSU → WB Interface",
            "type": "pipeline register",
            "signals": "wb_valid, wb_result[63:0], wb_rd[4:0], wb_wb_en",
            "protocol": "WB receives final result from LSU (Mux(mem_is_load, mem_load_data, mem_alu_result)). When wb_valid=1: write wb_result to regfile[wb_rd] if wb_wb_en=1.",
        },
        {
            "name": "WB → IDU Forwarding",
            "type": "combinational bypass",
            "signals": "wb_fwd_valid, wb_fwd_result[63:0], wb_fwd_rd[4:0]",
            "protocol": "Zero-cycle forward: wb_fwd_valid indicates WB has valid result. IDU uses this to bypass regfile read when rs1/rs2 match wb_fwd_rd.",
        },
    ],
    "noc_router": [
        {
            "name": "Port Valid/Ready Handshake",
            "type": "valid/ready flow control",
            "signals": "{port}_flit[63:0], {port}_valid, {port}_ready",
            "protocol": "Input: upstream asserts {port}_valid + flit data. Router asserts {port}_ready when buffer not full. Output: router asserts {port}_valid_o when flit ready for downstream.",
        },
    ],
}


def get_interface_protocols(pe_type: str) -> List[Dict[str, str]]:
    """Get interface protocol descriptions for a PE type."""
    return INTERFACE_PROTOCOLS.get(pe_type, [])


# =====================================================================
# Micro-architecture details — per PE type
# =====================================================================
# These tables contain the detailed register-level design information
# that an LLM needs to generate correct RTL code.

UARCH_TABLES: Dict[str, Dict[str, Any]] = {
    "rv64_core": {
        "pipeline_registers": [
            {"stage": "F", "name": "pc", "width": 64, "purpose": "Program counter, reset to 0x1000 (boot ROM)"},
            {"stage": "F", "name": "fetch_valid", "width": 1, "purpose": "Fetch stage has valid instruction"},
            {"stage": "F", "name": "fetch_instr", "width": 32, "purpose": "Fetched instruction word"},
            {"stage": "F", "name": "fetch_pc", "width": 64, "purpose": "PC of fetched instruction"},
            {"stage": "D", "name": "decode_valid", "width": 1, "purpose": "Decode stage has valid instruction"},
            {"stage": "D", "name": "decode_instr", "width": 32, "purpose": "Instruction being decoded"},
            {"stage": "D", "name": "decode_pc", "width": 64, "purpose": "PC of instruction being decoded"},
            {"stage": "E", "name": "exec_valid", "width": 1, "purpose": "Execute stage has valid instruction"},
            {"stage": "E", "name": "exec_instr", "width": 32, "purpose": "Instruction in execute"},
            {"stage": "E", "name": "exec_pc", "width": 64, "purpose": "PC of instruction in execute"},
            {"stage": "E", "name": "exec_alu_result", "width": 64, "purpose": "ALU result (before memory)"},
            {"stage": "E", "name": "exec_branch_taken", "width": 1, "purpose": "Branch was taken in execute"},
            {"stage": "E", "name": "exec_branch_target", "width": 64, "purpose": "Branch target address"},
            {"stage": "E", "name": "exec_mem_read", "width": 1, "purpose": "Instruction is a load"},
            {"stage": "E", "name": "exec_mem_write", "width": 1, "purpose": "Instruction is a store"},
            {"stage": "E", "name": "exec_wb_en", "width": 1, "purpose": "Instruction writes register file"},
            {"stage": "E", "name": "exec_rd", "width": 5, "purpose": "Destination register index"},
            {"stage": "M", "name": "mem_valid", "width": 1, "purpose": "Memory stage has valid instruction"},
            {"stage": "M", "name": "mem_alu_result", "width": 64, "purpose": "ALU result in memory stage"},
            {"stage": "M", "name": "mem_wb_en", "width": 1, "purpose": "Writeback enable in memory stage"},
            {"stage": "M", "name": "mem_rd", "width": 5, "purpose": "Destination register in memory stage"},
            {"stage": "M", "name": "mem_load_data", "width": 64, "purpose": "Load data from D-Cache"},
            {"stage": "M", "name": "mem_is_load", "width": 1, "purpose": "Instruction in memory stage is a load"},
            {"stage": "W", "name": "wb_valid", "width": 1, "purpose": "Writeback stage has valid instruction"},
            {"stage": "W", "name": "wb_result", "width": 64, "purpose": "Final writeback result"},
            {"stage": "W", "name": "wb_wb_en", "width": 1, "purpose": "Writeback enable"},
            {"stage": "W", "name": "wb_rd", "width": 5, "purpose": "Destination register for writeback"},
        ],
        "opcode_table": [
            {"opcode": "0b0110011 (0x33)", "name": "OP", "type": "R-type", "desc": "Register-register ALU operations"},
            {"opcode": "0b0010011 (0x13)", "name": "OP-IMM", "type": "I-type", "desc": "Register-immediate ALU operations"},
            {"opcode": "0b0000011 (0x03)", "name": "LOAD", "type": "I-type", "desc": "Load from memory"},
            {"opcode": "0b0100011 (0x23)", "name": "STORE", "type": "S-type", "desc": "Store to memory"},
            {"opcode": "0b1100011 (0x63)", "name": "BRANCH", "type": "B-type", "desc": "Conditional branch"},
            {"opcode": "0b1101111 (0x6F)", "name": "JAL", "type": "J-type", "desc": "Jump and link"},
            {"opcode": "0b1100111 (0x67)", "name": "JALR", "type": "I-type", "desc": "Jump and link register"},
            {"opcode": "0b0110111 (0x37)", "name": "LUI", "type": "U-type", "desc": "Load upper immediate"},
            {"opcode": "0b0010111 (0x17)", "name": "AUIPC", "type": "U-type", "desc": "Add upper immediate to PC"},
        ],
        "alu_operations": [
            {"funct3": "000", "funct7": "0000000", "name": "ADD", "desc": "ra + rb (R-type) or ra + imm (I-type)"},
            {"funct3": "000", "funct7": "0100000", "name": "SUB", "desc": "ra - rb (R-type only)"},
            {"funct3": "001", "funct7": "0000000", "name": "SLL", "desc": "ra << rb[4:0] (logical left shift)"},
            {"funct3": "010", "funct7": "0000000", "name": "SLT", "desc": "ra < rb (signed compare)"},
            {"funct3": "011", "funct7": "0000000", "name": "SLTU", "desc": "ra < rb (unsigned compare)"},
            {"funct3": "100", "funct7": "0000000", "name": "XOR", "desc": "ra ^ rb (bitwise XOR)"},
            {"funct3": "101", "funct7": "0000000", "name": "SRL", "desc": "ra >> rb[4:0] (logical right shift)"},
            {"funct3": "101", "funct7": "0100000", "name": "SRA", "desc": "ra >>> rb[4:0] (arithmetic right shift)"},
            {"funct3": "110", "funct7": "0000000", "name": "OR", "desc": "ra | rb (bitwise OR)"},
            {"funct3": "111", "funct7": "0000000", "name": "AND", "desc": "ra & rb (bitwise AND)"},
        ],
        "branch_conditions": [
            {"funct3": "000", "name": "BEQ", "desc": "Branch if Equal (ra == rb)"},
            {"funct3": "001", "name": "BNE", "desc": "Branch if Not Equal (ra != rb)"},
            {"funct3": "100", "name": "BLT", "desc": "Branch if Less Than (ra < rb, signed)"},
            {"funct3": "101", "name": "BGE", "desc": "Branch if Greater or Equal (ra >= rb, signed)"},
            {"funct3": "110", "name": "BLTU", "desc": "Branch if Less Than (ra < rb, unsigned)"},
            {"funct3": "111", "name": "BGEU", "desc": "Branch if Greater or Equal (ra >= rb, unsigned)"},
        ],
        "immediate_formats": [
            {"type": "I-type", "layout": "[31:20] = imm[11:0]", "instructions": "OP-IMM, LOAD, JALR"},
            {"type": "S-type", "layout": "[31:25]=imm[11:5], [11:7]=imm[4:0]", "instructions": "STORE"},
            {"type": "B-type", "layout": "[31]=imm[12], [7]=imm[11], [30:25]=imm[10:5], [11:8]=imm[4:1], LSB=0", "instructions": "BRANCH"},
            {"type": "U-type", "layout": "[31:12] = imm[31:12], lower 12 bits = 0", "instructions": "LUI, AUIPC"},
            {"type": "J-type", "layout": "[31]=imm[20], [19:12]=imm[19:12], [20]=imm[11], [30:21]=imm[10:1], LSB=0", "instructions": "JAL"},
        ],
        "forwarding_network": {
            "stages": "3-stage forwarding from EX/MEM/WB",
            "wb_only": "WB → D (register read bypass): wb_fwd_valid, wb_fwd_result, wb_fwd_rd",
            "ex_forward": "EX → EX (for back-to-back ALU ops): forward ALU result to next instruction's ALU",
            "mem_forward": "MEM → EX (for load-use): forward D-Cache read data to next instruction's ALU",
            "load_use_hazard": "If instruction in EX is a load and next instruction in D reads same register: stall 1 cycle + forward from MEM",
            "forward_condition": "Compare rs1/rs2 against exec_rd/mem_rd/wb_rd; if match and wb_en=1, use forwarded value",
        },
        "stall_logic": {
            "icache_stall": "fetch_valid && !icache_valid → pipeline freezes at fetch",
            "dcache_stall": "exec_valid && (is_load || is_store) && !dcache_valid → pipeline freezes at execute",
            "load_use_stall": "exec_is_load && (exec_rd == decode_rs1 || exec_rd == decode_rs2) → stall decode for 1 cycle",
            "branch_flush": "branch_redirect → flush fetch (fetch_valid=0), redirect PC to branch_target",
        },
    },
    "ooo_core": {
        "pipeline_registers": [
            {"stage": "F", "name": "pc", "width": 64, "purpose": "Program counter (2-wide fetch, increments by 8)"},
            {"stage": "F", "name": "fetch_valid", "width": 1, "purpose": "Fetch stage has valid instruction bundle"},
            {"stage": "F", "name": "fetch_pc_0", "width": 64, "purpose": "PC of first fetched instruction"},
            {"stage": "F", "name": "fetch_pc_1", "width": 64, "purpose": "PC of second fetched instruction"},
            {"stage": "F", "name": "fetch_instr_0", "width": 32, "purpose": "First fetched instruction"},
            {"stage": "F", "name": "fetch_instr_1", "width": 32, "purpose": "Second fetched instruction"},
            {"stage": "D", "name": "decoded_uop_0", "width": "128", "purpose": "Decoded micro-op 0 (opcode + operands + imm)"},
            {"stage": "D", "name": "decoded_uop_1", "width": "128", "purpose": "Decoded micro-op 1"},
            {"stage": "RN", "name": "rename_map", "width": "7*32", "purpose": "Arch→Phys register mapping table (32 entries × 7-bit)"},
            {"stage": "RN", "name": "free_list_ptr", "width": 7, "purpose": "Free list head pointer"},
            {"stage": "RN", "name": "rename_preg_0", "width": 7, "purpose": "Allocated physical register for uop 0 destination"},
            {"stage": "RN", "name": "rename_preg_1", "width": 7, "purpose": "Allocated physical register for uop 1 destination"},
            {"stage": "IQ", "name": "iq_entry", "width": "160", "purpose": "Issue queue entry: opcode + phys_regs + ready_bits + payload"},
            {"stage": "IQ", "name": "iq_ready", "width": 32, "purpose": "Ready bit vector for all IQ entries"},
            {"stage": "IQ", "name": "iq_issued", "width": 32, "purpose": "Issued bit vector (cleared on wakeup)"},
            {"stage": "EX", "name": "alu_result", "width": 64, "purpose": "ALU execution result"},
            {"stage": "EX", "name": "agu_result", "width": 64, "purpose": "Address generation result (load/store)"},
            {"stage": "EX", "name": "bru_result", "width": 64, "purpose": "Branch resolution result (target PC + taken)"},
            {"stage": "EX", "name": "ex_phys_rd", "width": 7, "purpose": "Physical destination register from execution"},
            {"stage": "ROB", "name": "rob_entry", "width": "192", "purpose": "ROB entry: pc + phys_rd + old_phys_rd + ready + exception"},
            {"stage": "ROB", "name": "rob_head", "width": 6, "purpose": "ROB head pointer (oldest not-yet-retired)"},
            {"stage": "ROB", "name": "rob_tail", "width": 6, "purpose": "ROB tail pointer (next allocation slot)"},
            {"stage": "CMT", "name": "arch_pc", "width": 64, "purpose": "Architectural PC (committed state)"},
        ],
        "performance_targets": {
            "ipc": "1.5+ on SPECint2006",
            "frequency": "2.0 GHz (7nm)",
            "branch_mispredict_rate": "< 5%",
            "l1_hit_rate": "> 95%",
            "load_use_latency": "2 cycles (AGU → bypass → dependent ALU)",
        },
        "stall_logic": {
            "rob_full": "ROB has 64 entries; fetch stalls when (tail+1)%64 == head",
            "iq_full": "IQ has 32 entries; rename stalls when no free IQ slot",
            "icache_miss": "Fetch stalls until fill data returns from L2/memory",
            "dcache_miss": "Load queue head stalls until fill returns; younger loads may proceed",
            "branch_mispredict": "Pipeline flush: fetch redirect to correct PC, rename checkpoint restore",
            "store_buffer_full": "16-entry store buffer full → AGU stalls",
        },
        "rename_details": {
            "map_table": "32 entries × 7-bit (128 physical registers). Reset: map[i] = i.",
            "free_list": "Stack-based: pop during rename, push during commit. 128 entries.",
            "checkpoint": "On branch predict: save rename state. On mispredict: restore.",
            "width": "2 instructions per cycle rename",
        },
        "rob_entry_format": [
            {"field": "pc", "width": 64, "purpose": "Instruction PC for precise exception"},
            {"field": "instr", "width": 32, "purpose": "Raw instruction encoding"},
            {"field": "phys_rd", "width": 7, "purpose": "Physical destination register"},
            {"field": "old_phys_rd", "width": 7, "purpose": "Previous physical register for same arch reg (free on commit)"},
            {"field": "ready", "width": 1, "purpose": "Execution result is ready"},
            {"field": "exception", "width": 1, "purpose": "Instruction caused an exception"},
            {"field": "load", "width": 1, "purpose": "Instruction is a load (needs LSQ)"},
            {"field": "store", "width": 1, "purpose": "Instruction is a store (needs LSQ)"},
            {"field": "branch", "width": 1, "purpose": "Instruction is a branch"},
        ],
    },
    "coherence_bus": {
        "pipeline_registers": [
            {"stage": "BUS", "name": "bus_fsm", "width": 2, "purpose": "Bus FSM: IDLE=0, SNOOP=1, RESP=2"},
            {"stage": "BUS", "name": "pending_addr", "width": 64, "purpose": "Address being snooped"},
            {"stage": "BUS", "name": "pending_core", "width": 2, "purpose": "Requesting core ID"},
            {"stage": "BUS", "name": "snoop_acks", "width": 4, "purpose": "Snoop ack bitmask (one bit per core)"},
            {"stage": "BUS", "name": "shared_detected", "width": 1, "purpose": "Any cache has line in S state"},
        ],
        "mesi_transitions": [
            {"from": "I", "event": "Read miss (bus: shared resp)", "to": "S"},
            {"from": "I", "event": "Write miss (bus: exclusive resp)", "to": "E"},
            {"from": "S", "event": "Write hit (bus: upgrade)", "to": "E"},
            {"from": "S", "event": "Snoop invalidate", "to": "I"},
            {"from": "E", "event": "Read hit", "to": "E"},
            {"from": "E", "event": "Write hit", "to": "M"},
            {"from": "E", "event": "Snoop read", "to": "S"},
            {"from": "E", "event": "Snoop invalidate", "to": "I"},
            {"from": "M", "event": "Read/write hit", "to": "M"},
            {"from": "M", "event": "Snoop read (writeback)", "to": "S"},
            {"from": "M", "event": "Snoop invalidate (writeback)", "to": "I"},
        ],
    },
    "l1_cache": {
        "pipeline_registers": [
            {"stage": "FSM", "name": "cache_fsm", "width": 2, "purpose": "Cache FSM state: IDLE=0, CHECK=1, REFILL=2"},
            {"stage": "FSM", "name": "msi_state", "width": 2, "purpose": "MSI coherence state per line: I=0, S=1, M=2"},
            {"stage": "RAM", "name": "tag_ram", "width": "tag_bits", "purpose": "Tag storage array (SETS entries × tag_width)"},
            {"stage": "RAM", "name": "data_ram", "width": "line_size*8", "purpose": "Data storage array (SETS entries × line_size bytes)"},
            {"stage": "CTRL", "name": "valid_ram", "width": 1, "purpose": "Valid bit per line"},
            {"stage": "CTRL", "name": "lru_state", "width": "log2(WAYS)", "purpose": "LRU replacement tracking per set"},
        ],
        "coherence_protocol": {
            "type": "MSI (Modified/Shared/Invalid)",
            "I_to_S": "Read miss → send coherence request to directory, wait for fill data, transition to S",
            "I_to_M": "Write miss → send exclusive coherence request, wait for fill, transition to M",
            "S_to_M": "Write hit → send upgrade request to directory, invalidate other sharers, transition to M",
            "M_to_S": "Snoop invalidation received → writeback dirty data to L2, transition to S",
            "M_to_I": "Snoop invalidation for exclusive request → writeback dirty data, transition to I",
            "eviction": "LRU victim with M state → writeback to L2 before replacing",
        },
    },
    "coherence_dir": {
        "pipeline_registers": [
            {"stage": "RAM", "name": "dir_tag", "width": "tag_width", "purpose": "Directory tag storage"},
            {"stage": "RAM", "name": "dir_state", "width": 2, "purpose": "MSI state per line: I=0, S=1, M=2"},
            {"stage": "RAM", "name": "dir_sharers", "width": 64, "purpose": "Per-core sharers bitmask"},
            {"stage": "RAM", "name": "dir_owner", "width": 6, "purpose": "Current owner core ID"},
            {"stage": "FSM", "name": "dir_fsm", "width": 3, "purpose": "Directory FSM: IDLE→LOOKUP→PROBE→UPDATE→WB"},
            {"stage": "CTRL", "name": "snoop_pending", "width": 1, "purpose": "Snoop transaction in flight"},
        ],
        "coherence_protocol": {
            "type": "MSI Directory (64-core, bitmask-based sharers)",
            "read_shared": "Core requests read: if M, downgrade owner to S; add requester to sharers; respond with data",
            "read_exclusive": "Core requests write: invalidate current owner; grant exclusive ownership; respond with data",
            "writeback": "Victim eviction: directory clears sharers/owner bit for evicting core",
            "snoop_invalidate": "Directory sends invalidation to all sharers except requestor; wait for acknowledgements",
            "state_transition": "Track per-line: I(no sharers)→S(one+ sharers)→M(exclusive owner)",
        },
    },
    "l2_cache": {
        "pipeline_registers": [
            {"stage": "RAM", "name": "tag_ram", "width": "tag_width", "purpose": "L2 tag storage"},
            {"stage": "RAM", "name": "data_ram", "width": "line_size*8", "purpose": "L2 data storage"},
            {"stage": "RAM", "name": "lru_state", "width": "log2(WAYS)", "purpose": "LRU tracking per set"},
            {"stage": "FSM", "name": "l2_fsm", "width": 2, "purpose": "L2 FSM: IDLE→LOOKUP→REFILL→WRITEBACK"},
            {"stage": "CTRL", "name": "valid_bits", "width": "WAYS", "purpose": "Valid bit per way"},
        ],
        "coherence_protocol": {
            "type": "L2 victim writeback + snoop response",
            "lookup": "On request: tag compare, if hit → respond data, if miss → issue DRAM read",
            "refill": "DRAM data returned → fill data RAM, update tag, clear LRU",
            "writeback": "LRU victim is dirty → write data back to DRAM before refill",
            "snoop_response": "On directory invalidation: if hit and M → writeback dirty data, invalidate line",
        },
    },
    "noc_router": {
        "pipeline_registers": [
            {"stage": "IBUF", "name": "e_buf_count", "width": 3, "purpose": "East input buffer fill count (0-4)"},
            {"stage": "IBUF", "name": "w_buf_count", "width": 3, "purpose": "West input buffer fill count (0-4)"},
            {"stage": "IBUF", "name": "n_buf_count", "width": 3, "purpose": "North input buffer fill count (0-4)"},
            {"stage": "IBUF", "name": "s_buf_count", "width": 3, "purpose": "South input buffer fill count (0-4)"},
            {"stage": "IBUF", "name": "j_buf_count", "width": 3, "purpose": "Local injection buffer fill count (0-4)"},
            {"stage": "CBUF", "name": "fifo_buf", "width": "flit_width", "purpose": "Per-port FIFO storage (4-deep)"},
        ],
        "routing_algorithm": {
            "type": "XY deterministic routing",
            "x_compare": "if dest_x > current_x → route East; if dest_x < current_x → route West",
            "y_compare": "if dest_y > current_y → route North; if dest_y < current_y → route South",
            "local": "if dest_x == current_x && dest_y == current_y → route to local port",
            "priority": "Arbiter priority: North > South > East > West > Local",
        },
        "flow_control": {
            "type": "valid/ready handshake with credit-based backpressure",
            "buffer_full": "buf_count >= 4 → deassert ready (backpressure)",
            "buffer_empty": "buf_count == 0 → no valid output",
            "push_condition": "valid_in && ready_out && !full",
            "pop_condition": "pop signal from arbiter && !empty",
        },
    },
    "ifu": {
        "pipeline_registers": [
            {"stage": "F", "name": "pc", "width": 64, "purpose": "Program counter, reset to 0x1000"},
            {"stage": "F", "name": "fetch_valid", "width": 1, "purpose": "Fetch valid"},
            {"stage": "F", "name": "fetch_instr", "width": 32, "purpose": "Fetched instruction"},
            {"stage": "F", "name": "fetch_pc", "width": 64, "purpose": "Fetch PC"},
        ],
        "stall_logic": {
            "icache_stall": "fetch_valid && !icache_valid → freeze fetch, hold PC",
            "branch_flush": "branch_redirect → flush fetch, redirect PC to branch_target",
        },
    },
    "idu": {
        "pipeline_registers": [
            {"stage": "D", "name": "decode_valid", "width": 1, "purpose": "Decode valid"},
            {"stage": "D", "name": "decode_instr", "width": 32, "purpose": "Decoded instruction"},
            {"stage": "D", "name": "decode_pc", "width": 64, "purpose": "Decode PC"},
        ],
        "opcode_table": [
            {"opcode": "0x33", "name": "OP", "type": "R-type", "desc": "Register-register ALU"},
            {"opcode": "0x13", "name": "OP-IMM", "type": "I-type", "desc": "Register-immediate ALU"},
            {"opcode": "0x03", "name": "LOAD", "type": "I-type", "desc": "Load"},
            {"opcode": "0x23", "name": "STORE", "type": "S-type", "desc": "Store"},
            {"opcode": "0x63", "name": "BRANCH", "type": "B-type", "desc": "Branch"},
            {"opcode": "0x6F", "name": "JAL", "type": "J-type", "desc": "Jump and link"},
            {"opcode": "0x37", "name": "LUI", "type": "U-type", "desc": "Load upper imm"},
            {"opcode": "0x17", "name": "AUIPC", "type": "U-type", "desc": "Add upper imm to PC"},
        ],
        "immediate_formats": [
            {"type": "I-type", "layout": "[31:20]", "instructions": "OP-IMM, LOAD, JALR"},
            {"type": "S-type", "layout": "[31:25]+[11:7]", "instructions": "STORE"},
            {"type": "B-type", "layout": "[31]+[7]+[30:25]+[11:8]", "instructions": "BRANCH"},
            {"type": "U-type", "layout": "[31:12]", "instructions": "LUI, AUIPC"},
            {"type": "J-type", "layout": "[31]+[19:12]+[20]+[30:21]", "instructions": "JAL"},
        ],
    },
    "alu": {
        "pipeline_registers": [
            {"stage": "E", "name": "exec_valid", "width": 1, "purpose": "Execute valid"},
            {"stage": "E", "name": "exec_instr", "width": 32, "purpose": "Executing instruction"},
            {"stage": "E", "name": "exec_pc", "width": 64, "purpose": "Execute PC"},
            {"stage": "E", "name": "exec_alu_result", "width": 64, "purpose": "ALU result"},
            {"stage": "E", "name": "exec_branch_taken", "width": 1, "purpose": "Branch taken"},
            {"stage": "E", "name": "exec_branch_target", "width": 64, "purpose": "Branch target"},
            {"stage": "E", "name": "exec_mem_read", "width": 1, "purpose": "Is load"},
            {"stage": "E", "name": "exec_mem_write", "width": 1, "purpose": "Is store"},
            {"stage": "E", "name": "exec_wb_en", "width": 1, "purpose": "Write regfile"},
            {"stage": "E", "name": "exec_rd", "width": 5, "purpose": "Dest register"},
        ],
        "alu_operations": [
            {"funct3": "000", "funct7": "0000000", "name": "ADD", "desc": "ra + rb/imm"},
            {"funct3": "000", "funct7": "0100000", "name": "SUB", "desc": "ra - rb"},
            {"funct3": "001", "funct7": "0000000", "name": "SLL", "desc": "ra << rb[4:0]"},
            {"funct3": "010", "funct7": "0000000", "name": "SLT", "desc": "ra < rb (signed)"},
            {"funct3": "011", "funct7": "0000000", "name": "SLTU", "desc": "ra < rb (unsigned)"},
            {"funct3": "100", "funct7": "0000000", "name": "XOR", "desc": "ra ^ rb/imm"},
            {"funct3": "101", "funct7": "0000000", "name": "SRL", "desc": "ra >> rb[4:0]"},
            {"funct3": "101", "funct7": "0100000", "name": "SRA", "desc": "ra >>> rb[4:0]"},
            {"funct3": "110", "funct7": "0000000", "name": "OR", "desc": "ra | rb/imm"},
            {"funct3": "111", "funct7": "0000000", "name": "AND", "desc": "ra & rb/imm"},
        ],
        "branch_conditions": [
            {"funct3": "000", "name": "BEQ", "desc": "ra == rb"},
            {"funct3": "001", "name": "BNE", "desc": "ra != rb"},
            {"funct3": "100", "name": "BLT", "desc": "ra < rb (signed)"},
            {"funct3": "101", "name": "BGE", "desc": "ra >= rb (signed)"},
            {"funct3": "110", "name": "BLTU", "desc": "ra < rb (unsigned)"},
            {"funct3": "111", "name": "BGEU", "desc": "ra >= rb (unsigned)"},
        ],
    },
    "lsu": {
        "pipeline_registers": [
            {"stage": "M", "name": "mem_valid", "width": 1, "purpose": "Memory stage valid"},
            {"stage": "M", "name": "mem_alu_result", "width": 64, "purpose": "Address from ALU"},
            {"stage": "M", "name": "mem_wb_en", "width": 1, "purpose": "Writeback enable"},
            {"stage": "M", "name": "mem_rd", "width": 5, "purpose": "Dest register"},
            {"stage": "M", "name": "mem_load_data", "width": 64, "purpose": "Load data from D$"},
            {"stage": "M", "name": "mem_is_load", "width": 1, "purpose": "Is load instruction"},
        ],
        "stall_logic": {
            "dcache_stall": "exec_valid && (is_load || is_store) && !dcache_valid → freeze at execute",
        },
    },
    "wb": {
        "pipeline_registers": [
            {"stage": "W", "name": "wb_valid", "width": 1, "purpose": "Writeback valid"},
            {"stage": "W", "name": "wb_result", "width": 64, "purpose": "Writeback data"},
            {"stage": "W", "name": "wb_wb_en", "width": 1, "purpose": "Register write enable"},
            {"stage": "W", "name": "wb_rd", "width": 5, "purpose": "Destination register"},
        ],
    },
    "noc_buffer": {
        "pipeline_registers": [
            {"stage": "BUF", "name": "fifo_buf", "width": "flit_width", "purpose": "FIFO storage (4-deep)"},
            {"stage": "BUF", "name": "buf_count", "width": 3, "purpose": "Fill count (0-4)"},
            {"stage": "BUF", "name": "buf_rd_ptr", "width": 2, "purpose": "FIFO read pointer"},
            {"stage": "BUF", "name": "buf_wr_ptr", "width": 2, "purpose": "FIFO write pointer"},
        ],
    },
    "route_logic": {
        "pipeline_registers": [
            {"stage": "RT", "name": "grant_*", "width": 1, "purpose": "Grant signals per output port"},
            {"stage": "RT", "name": "route_*", "width": 1, "purpose": "Route decision per port"},
        ],
    },
    "crossbar": {},
    "tag_ram": {
        "pipeline_registers": [
            {"stage": "TAG", "name": "tag_rdata", "width": "tag_width", "purpose": "Tag read data"},
            {"stage": "TAG", "name": "hit", "width": 1, "purpose": "Tag match result"},
        ],
    },
    "data_ram": {},
    "cache_fsm": {
        "pipeline_registers": [
            {"stage": "FSM", "name": "cache_state", "width": 2, "purpose": "FSM state: IDLE/CHECK/REFILL"},
        ],
    },
    "snoop_gen": {},
    "resp_arb": {},
    "dir_ram": {},
}


def get_uarch_tables(pe_type: str) -> Dict[str, Any]:
    return UARCH_TABLES.get(pe_type, {})


# =====================================================================
# Convenience: enhance a GenerationContext with all extracted info
# =====================================================================

def enhance_context(gen_ctx: Any, module: Optional[Module] = None,
                    skill_name: str = "riscv64_soc") -> Dict[str, Any]:
    """Enhance a GenerationContext by extracting additional structured info.

    Returns a dict of extra information that spec_markdown can use:
      - fsms: extracted FSM state machines
      - arch_description: structured architecture description
      - submodule_connections: sub-module internal wiring
      - behavior_pseudocode: pseudo-code of behavioral model
      - golden_tests: test vectors
      - interface_protocols: interface protocol descriptions
      - uarch: micro-architecture details
      - dsl_ports: exact port widths from hand-written DSL code
      - dsl_interactions: port-level interaction tables from ClusterTop wiring
      - dsl_state: state registers/arrays from hand-written DSL code
    """
    pe_type = ""
    target = getattr(gen_ctx, "target", None)
    if target:
        pe_type = getattr(target, "pe_type", "")

    result = {}

    # Extract FSMs from module
    if module is not None:
        result["fsms"] = extract_fsms(module)
    else:
        result["fsms"] = []

    # Architecture description
    arch_desc = get_arch_description(pe_type)
    result["arch_description"] = arch_desc

    # Sub-module connections
    result["submodule_connections"] = get_submodule_connections(pe_type)

    # Behavior pseudo-code
    result["behavior_pseudocode"] = get_behavior_pseudocode(pe_type)

    # Golden tests
    result["golden_tests"] = get_golden_tests(pe_type)

    # Interface protocols
    result["interface_protocols"] = get_interface_protocols(pe_type)

    # Micro-architecture tables
    result["uarch"] = get_uarch_tables(pe_type)

    # ── Timing constraints from behavioral analysis ──
    try:
        from rtlgen.timing_analyzer import get_timing, run_behavioral_analysis
        timing = get_timing(pe_type)
        result["timing"] = timing
        if timing:
            result["timing_stages"] = timing.get("stages", [])
            result["timing_hazards"] = timing.get("hazard_penalties", timing.get("hazard_penalties", {}))
            result["timing_protocols"] = timing.get("interface_protocols", {})
            result["fsm_states"] = timing.get("states", [])
            result["fsm_transitions"] = timing.get("transitions", {})
    except ImportError:
        pass

    # ── Behavioral verification metrics ──
    try:
        from rtlgen.timing_analyzer import run_behavioral_analysis
        metrics = run_behavioral_analysis()
        if pe_type in metrics:
            result["behavioral_metrics"] = metrics[pe_type]
    except ImportError:
        pass

    # ── DSL-level extracted data from hand-written code ──
    try:
        from rtlgen.dsl_analyzer import (
            build_port_database,
            get_port_widths_by_type,
            get_submodule_interactions,
        )
        db = build_port_database(skill_name)

        # Exact port widths from DSL classes
        dsl_ports = get_port_widths_by_type(pe_type, db)
        result["dsl_ports"] = dsl_ports

        # Port-level interaction mapping
        interactions = get_submodule_interactions(pe_type, db)
        result["dsl_interactions"] = interactions

        # State from hand-written code
        type_to_class = {
            "rv64_core": "RV64Core", "l1_cache": "L1Cache",
            "coherence_dir": "CoherenceDir", "l2_cache": "L2CacheSlice",
            "noc_router": "NoCRouter", "noc_buffer": "NoCBuffer",
            "cluster": "ClusterTop",
        }
        cls_name = type_to_class.get(pe_type, "")
        state_data = db.get("state", {}).get(cls_name, {})
        if state_data:
            result["dsl_regs"] = state_data.get("regs", [])
            result["dsl_arrays"] = state_data.get("arrays", [])
    except ImportError:
        pass
    except Exception:
        pass

    return result
