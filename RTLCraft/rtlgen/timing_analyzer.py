"""
rtlgen.timing_analyzer — Extract timing constraints from behavioral models and hand-written DSL.

For each PE type:
  - Pipeline depth and stage latencies
  - Interface handshake timing (valid/ready fire conditions)
  - FSM state transition timing (cycles per state)
  - Memory/NoC access latencies
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from rtlgen.core import Module, Reg, Wire, Array
from rtlgen.arch_def import CycleContext


# =====================================================================
# Timing data extracted from behavioral models / hand-written DSL
# =====================================================================

# Core pipeline timing — from rv64_core_template and RV64Core DSL
CORE_PIPELINE_TIMING = {
    "pipeline_depth": 5,
    "stages": [
        {"name": "Fetch", "cycles": 1, "description": "PC → I-Cache → instruction ready (1 cycle if cache hit)"},
        {"name": "Decode", "cycles": 1, "description": "Instruction decode, register read, forwarding mux"},
        {"name": "Execute", "cycles": 1, "description": "ALU operation, branch comparison, address calculation"},
        {"name": "Memory", "cycles": 1, "description": "D-Cache access (1 cycle if cache hit), load/store"},
        {"name": "Writeback", "cycles": 1, "description": "Register file write, forwarding to decode"},
    ],
    "hazard_penalties": {
        "load_use_hazard": 1,
        "branch_mispredict": 2,
        "icache_miss": "≥ 10 (depends on refill latency)",
        "dcache_miss": "≥ 10 (depends on coherence/DRAM latency)",
    },
    "forwarding": {
        "ex_to_ex": 0,
        "mem_to_ex": 0,
        "wb_to_ex": 0,
        "load_use_stall": 1,
    },
    "reset_latency": 1,
    "interface_protocols": {
        "icache": {
            "type": "valid/ready handshake",
            "request_cycles": 1,
            "response_cycles": 1,
            "backpressure": "icache_ready deasserted when cache miss",
            "fire_condition": "icache_valid && icache_ready",
        },
        "dcache": {
            "type": "valid/ready handshake with RW control",
            "request_cycles": 1,
            "response_cycles": 1,
            "backpressure": "dcache_ready deasserted when cache miss or busy",
            "fire_condition": "dcache_valid && dcache_ready",
        },
    },
}

# Cache timing — from l1_cache_template and L1Cache DSL
CACHE_TIMING = {
    "stages": [
        {"name": "Tag Check", "cycles": 1, "description": "index → tag_ram → compare (hit/miss decision)"},
        {"name": "Data Read", "cycles": 1, "description": "data_ram[index] → rdata output (on hit)"},
        {"name": "Refill Wait", "cycles": "N (10+ cycles to L2/DRAM)", "description": "Coherence request → fill_valid (miss path)"},
        {"name": "Refill Store", "cycles": 1, "description": "fill_data → data_ram[index], tag update, LRU update"},
    ],
    "hit_latency": 1,
    "miss_refill_cycles": 10,
    "tag_check_cycles": 1,
    "data_access_cycles": 1,
    "coherence_probe_cycles": 2,
    "writeback_cycles": 2,
    "reset_latency": 1,
    "states": [
        {"name": "IDLE", "cycles": "∞ (wait for request)", "entry_action": "Wait for req=1"},
        {"name": "TAG_CHECK", "cycles": 1, "entry_action": "Compare tag RAM, check valid bit"},
        {"name": "REFILL_WAIT", "cycles": "N (refill from L2/DRAM)", "entry_action": "Send coherence/DRAM request"},
        {"name": "REFILL_STORE", "cycles": 1, "entry_action": "Store fill data into cache line"},
    ],
    "transitions": {
        "IDLE→TAG_CHECK": "req=1 (1 cycle)",
        "TAG_CHECK→IDLE": "hit=1 (1 cycle, data ready next cycle)",
        "TAG_CHECK→REFILL_WAIT": "miss=1 (start refill)",
        "REFILL_WAIT→REFILL_STORE": "fill_valid=1 (data returned)",
        "REFILL_STORE→IDLE": "data stored, valid=1 for 1 cycle",
    },
}

# NoC Router timing — from noc_router_template and NoCRouter DSL
NOC_TIMING = {
    "stages": [
        {"name": "Input Buffer Write", "cycles": 1, "description": "Flit written to input FIFO on valid & ready"},
        {"name": "Route Decision", "cycles": 1, "description": "XY routing: compare dest vs current coordinates"},
        {"name": "Crossbar Traversal", "cycles": 1, "description": "Flit passes through 5×5 crossbar to output port"},
        {"name": "Output Buffer", "cycles": 1, "description": "Flit staged in output buffer for downstream handshake"},
    ],
    "input_buffer_cycles": 1,
    "route_decision_cycles": 1,
    "crossbar_traversal_cycles": 1,
    "output_buffer_cycles": 1,
    "total_pipeline_cycles": 4,
    "flow_control": {
        "type": "valid/ready with credit-based backpressure",
        "credit_init": 4,
        "credit_update": "pop signal from downstream router",
        "stall_condition": "buf_count >= BUFFER_DEPTH (4)",
    },
    "xy_routing_cycles": 1,
    "arbitration_priority": "N > S > E > W > J",
}

# Coherence directory timing
COHERENCE_TIMING = {
    "stages": [
        {"name": "Lookup", "cycles": 1, "description": "Tag match, read directory entry (state, sharers, owner)"},
        {"name": "Probe", "cycles": 2, "description": "Send snoop to current sharers/owner, wait for ack"},
        {"name": "Update", "cycles": 1, "description": "Update sharers bitmask, state, owner"},
        {"name": "Writeback Wait", "cycles": 2, "description": "Wait for dirty data writeback from evicted owner"},
    ],
    "lookup_cycles": 1,
    "probe_generation_cycles": 1,
    "snoop_wait_cycles": 2,
    "state_update_cycles": 1,
    "total_directory_cycles": 5,
    "states": [
        {"name": "IDLE", "cycles": "∞", "entry_action": "Wait for req_valid"},
        {"name": "LOOKUP", "cycles": 1, "entry_action": "Tag match, read directory entry"},
        {"name": "PROBE", "cycles": "2 (wait for snoop ack)", "entry_action": "Send snoop to sharers/owner"},
        {"name": "UPDATE", "cycles": 1, "entry_action": "Update sharers/owner/state"},
        {"name": "WB", "cycles": 2, "entry_action": "Wait for writeback data"},
    ],
}

# L2 cache timing
L2_TIMING = {
    "stages": [
        {"name": "Lookup", "cycles": 1, "description": "Tag compare on L2 tag_ram"},
        {"name": "DRAM Read", "cycles": "20", "description": "DRAM burst read on miss"},
        {"name": "Refill", "cycles": 1, "description": "DRAM data → data_ram, update tag/LRU"},
        {"name": "Writeback", "cycles": "20", "description": "Dirty victim → DRAM write burst"},
    ],
    "hit_latency": 1,
    "dram_read_latency": 20,
    "dram_write_latency": 20,
    "refill_from_dram": 20,
    "writeback_to_dram": 20,
    "states": [
        {"name": "IDLE", "cycles": "∞", "entry_action": "Wait for request"},
        {"name": "LOOKUP", "cycles": 1, "entry_action": "Tag compare"},
        {"name": "REFILL", "cycles": "N (DRAM latency)", "entry_action": "DRAM read request"},
        {"name": "WRITEBACK", "cycles": "N (DRAM latency)", "entry_action": "DRAM write request"},
    ],
}


# OoO core timing
OFO_TIMING = {
    "pipeline_depth": 6,
    "stages": [
        {"name": "Fetch", "cycles": 1, "description": "2-wide fetch from I-Cache with branch prediction"},
        {"name": "Decode", "cycles": 1, "description": "2-wide decode, immediate extraction"},
        {"name": "Rename", "cycles": 1, "description": "Arch→Phys register rename, free list pop"},
        {"name": "Issue", "cycles": "1 (wakeup) + 1 (select)", "description": "Wakeup-select from IQ, dispatch to EX"},
        {"name": "Execute", "cycles": "1 (ALU/AGU), 1-3 (BRU)", "description": "ALU/AGU/BRU with full bypass"},
        {"name": "Commit", "cycles": 1, "description": "ROB retire, arch reg update, free list push"},
    ],
    "hazard_penalties": {
        "branch_mispredict": "min 3 (pipeline flush + redirect)",
        "cache_miss": "≥ 10 (refill from L2/DRAM)",
        "load_to_use": "1 (if not bypassed via LSQ forwarding)",
    },
    "forwarding": {
        "ex_to_ex": 0,
        "mem_to_ex": 0,
        "wb_to_ex": 0,
        "lsq_forwarding": 1,
    },
    "reset_latency": 1,
    "interface_protocols": {
        "icache": {
            "type": "valid/ready handshake",
            "request_cycles": 1,
            "response_cycles": 1,
            "backpressure": "fetch_stall when I-cache miss or ROB full",
            "fire_condition": "icache_valid && icache_ready && !rob_full",
        },
    },
}

# Coherence bus timing
COHERENCE_BUS_TIMING = {
    "pipeline_depth": 3,
    "stages": [
        {"name": "Snoop Broadcast", "cycles": 1, "description": "Broadcast address to all cores"},
        {"name": "Snoop Wait", "cycles": "1-2", "description": "Wait for snoop responses (acks/data)"},
        {"name": "Response", "cycles": 1, "description": "Arbitrate and send response to requestor"},
    ],
    "states": [
        {"name": "IDLE", "cycles": "∞", "entry_action": "Wait for req_valid"},
        {"name": "SNOOP", "cycles": 1, "entry_action": "Broadcast snoop, wait for acks"},
        {"name": "RESP", "cycles": 1, "entry_action": "Send combined response"},
    ],
}

PE_TIMING = {
    "rv64_core": CORE_PIPELINE_TIMING,
    "ooo_core": OFO_TIMING,
    "coherence_bus": COHERENCE_BUS_TIMING,
    "ifu": {
        "pipeline_depth": 1,
        "stages": [{"name": "Fetch", "cycles": 1, "description": "PC → I-Cache request → response"}],
        "interface_protocols": CORE_PIPELINE_TIMING["interface_protocols"],
        "hazard_penalties": {"branch_flush": 2, "icache_miss": "≥ 10"},
    },
    "idu": {
        "pipeline_depth": 1,
        "stages": [{"name": "Decode", "cycles": 1, "description": "Decode + regfile read + forwarding"}],
        "forwarding": CORE_PIPELINE_TIMING["forwarding"],
        "hazard_penalties": {"load_use_hazard": 1, "forward_resolution": 0},
    },
    "alu": {
        "pipeline_depth": 1,
        "stages": [{"name": "Execute", "cycles": 1, "description": "ALU computation + branch comparison + address calculation"}],
        "latency": 1,
        "hazard_penalties": {"branch_mispredict": 2},
        "interface_protocols": {
            "idu_to_alu": {
                "type": "combinational forward",
                "request_cycles": 0,
                "response_cycles": 1,
                "backpressure": "exec_valid from IDU, dcache_stall from LSU",
                "fire_condition": "exec_valid && !dcache_stall",
            },
            "alu_to_lsu": {
                "type": "pipeline register",
                "request_cycles": 1,
                "response_cycles": 0,
                "backpressure": "mem_valid handshake",
                "fire_condition": "mem_valid == 0 && exec_valid == 1",
            },
        },
    },
    "lsu": {
        "pipeline_depth": 1,
        "stages": [{"name": "Memory", "cycles": 1, "description": "D-Cache access for load/store"}],
        "interface_protocols": CORE_PIPELINE_TIMING["interface_protocols"],
        "hazard_penalties": {"dcache_miss": "≥ 10"},
    },
    "wb": {
        "pipeline_depth": 1,
        "stages": [{"name": "Writeback", "cycles": 1, "description": "Register file write + forwarding to decode"}],
        "hazard_penalties": {},
        "interface_protocols": {
            "lsu_to_wb": {
                "type": "pipeline register",
                "request_cycles": 1,
                "response_cycles": 0,
                "backpressure": "wb_valid handshake",
                "fire_condition": "wb_valid == 0 && mem_valid == 1",
            },
            "wb_to_idu": {
                "type": "combinational forwarding",
                "request_cycles": 0,
                "response_cycles": 0,
                "backpressure": "none (combinational)",
                "fire_condition": "wb_valid && wb_wb_en",
            },
        },
    },
    "l1_cache": CACHE_TIMING,
    "l2_cache": L2_TIMING,
    "noc_router": NOC_TIMING,
    "coherence_dir": COHERENCE_TIMING,
    "noc_buffer": {
        "input_cycles": 1,
        "output_cycles": 1,
        "flow_control": { "type": "valid/ready", "depth": 4 },
    },
}


def get_timing(pe_type: str) -> Dict[str, Any]:
    """Get timing constraints for a PE type."""
    return PE_TIMING.get(pe_type, {})


# =====================================================================
# Behavioral simulation results
# =====================================================================

def run_behavioral_analysis(skill_name: str = "riscv64_soc") -> Dict[str, Any]:
    """Run behavioral models and extract metrics."""
    results = {}

    # Import and run the SoC model
    try:
        from skills.riscv64_soc.models import SoCModel
        soc = SoCModel(mesh_x=2, mesh_y=2)
        status = soc.run(num_cycles=100)
        results["soc_sim"] = {
            "total_cycles": 100,
            "retired": status.get("total_retired", 0),
            "ipc": status.get("total_retired", 0) / 100,
        }
    except Exception as e:
        results["soc_sim"] = {"error": str(e)}

    # Run individual behavioral templates
    from skills.riscv64_soc.behaviors import (
        rv64_core_template, l1_cache_template, noc_router_template,
        coherence_dir_template, l2_cache_template,
    )
    from rtlgen.arch_def import CycleContext

    # RV64 Core behavior analysis
    core_beh = rv64_core_template()
    ctx = CycleContext()
    ctx.inputs["stall"] = 0
    core_beh(ctx)
    results["rv64_core"] = {
        "retire_per_cycle": ctx.outputs.get("retire_count", 0),
        "pc_increment": ctx.outputs.get("pc_out", 0) - 0x1000,
        "stall_handling": "retire_valid=0 when stall=1",
    }

    # L1 Cache behavior analysis
    cache_beh = l1_cache_template()
    ctx = CycleContext()
    ctx.inputs["req_valid"] = 1
    ctx.inputs["addr"] = 0x1000
    cache_beh(ctx)
    results["l1_cache"] = {
        "hit_behavior": f"valid={ctx.outputs.get('valid', 0)}, miss={ctx.outputs.get('miss', 0)}",
    }

    ctx.inputs["addr"] = 0x2000
    cache_beh(ctx)
    results["l1_cache"]["miss_behavior"] = f"miss={ctx.outputs.get('miss', 1)}, stall={ctx.outputs.get('stall', 0)}"

    # NoC Router behavior analysis
    noc_beh = noc_router_template()
    ctx = CycleContext()
    ctx.inputs["x"] = 1; ctx.inputs["y"] = 1
    ctx.inputs["dest_x"] = 3; ctx.inputs["dest_y"] = 1
    ctx.inputs["flit_valid"] = 1
    noc_beh(ctx)
    results["noc_router"] = {
        "xy_routing": f"route_east={ctx.outputs.get('route_east', 0)} (x:1→3)",
    }

    # Coherence Dir behavior analysis
    dir_beh = coherence_dir_template()
    ctx = CycleContext()
    ctx.inputs["req_valid"] = 1
    ctx.inputs["req_type"] = 1  # Modified
    ctx.inputs["core_id"] = 0
    ctx.inputs["addr"] = 0x1000
    dir_beh(ctx)
    results["coherence_dir"] = {
        "modified_grant": ctx.outputs.get("grant", 0),
        "grant_state": ctx.outputs.get("grant_state", 0),
    }

    return results


def run_behavioral_pipeline(skill_name: str = "riscv64_soc") -> Dict[str, Any]:
    """Run the full behavioral pipeline and return per-stage metrics."""
    results = run_behavioral_analysis(skill_name)

    # Use skill_ppa runner for full results
    try:
        from rtlgen.skill_ppa import SkillPPARunner
        runner = SkillPPARunner(skill_name)
        beh_result = runner._run_behaviors()
        results["stage_result"] = {
            "passed": beh_result.passed,
            "metrics": beh_result.metrics,
        }
    except Exception as e:
        results["stage_result"] = {"error": str(e)}

    return results
