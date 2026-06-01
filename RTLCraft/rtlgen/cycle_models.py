"""
rtlgen.cycle_models — Cycle-accurate behavioral models matching RTL timing.

Each model tracks pipeline registers and FSM states cycle-by-cycle,
producing outputs that match the hand-written DSL modules exactly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext


# =====================================================================
# Cycle-level RV64 Core (5-stage pipeline)
# =====================================================================

def cycle_rv64_core() -> dict:
    """Create a cycle-level 5-stage pipeline behavioral model.

    Returns dict with:
      'name': 'rv64_core',
      'inputs': [...], 'outputs': [...],
      'init': function(ctx),
      'cycle': function(ctx),
      'get_trace': function() -> list of dict
    """
    XLEN = 64
    NOP = 0x00000013
    RESET_PC = 0x1000

    def init(ctx: CycleContext):
        """Initialize pipeline state (reset state)."""
        ctx.state["pc"] = RESET_PC
        ctx.state["cycle_count"] = 0
        # Pipeline registers
        ctx.state["fetch_valid"] = 0
        ctx.state["fetch_instr"] = 0
        ctx.state["fetch_pc"] = 0
        ctx.state["decode_valid"] = 0
        ctx.state["decode_instr"] = 0
        ctx.state["decode_pc"] = 0
        ctx.state["exec_valid"] = 0
        ctx.state["exec_alu_result"] = 0
        ctx.state["exec_branch_taken"] = 0
        ctx.state["exec_branch_target"] = 0
        ctx.state["mem_valid"] = 0
        ctx.state["mem_alu_result"] = 0
        ctx.state["mem_wb_en"] = 0
        ctx.state["mem_rd"] = 0
        ctx.state["mem_is_load"] = 0
        ctx.state["mem_load_data"] = 0
        ctx.state["wb_valid"] = 0
        ctx.state["wb_result"] = 0
        ctx.state["wb_wb_en"] = 0
        ctx.state["wb_rd"] = 0
        ctx.state["pipeline_active"] = 0
        ctx.state["retire_count"] = 0

    def cycle(ctx: CycleContext):
        """Execute one cycle of the 5-stage pipeline."""
        rst_n = ctx.get_input("rst_n", 1)
        reset_count = ctx.state.setdefault("reset_count", 0)

        # Hold reset for first 3 cycles
        if rst_n == 0 or reset_count < 3:
            ctx.state["reset_count"] = reset_count + 1
            ctx.state["pc"] = RESET_PC
            for r in ["fetch_valid","fetch_instr","fetch_pc","decode_valid","decode_instr","decode_pc",
                       "exec_valid","exec_alu_result","exec_branch_taken","exec_branch_target",
                       "mem_valid","mem_alu_result","mem_wb_en","mem_rd","mem_is_load","mem_load_data",
                       "wb_valid","wb_result","wb_wb_en","wb_rd"]:
                ctx.state[r] = 0
            ctx.state["pipeline_active"] = 0
            ctx.state["retire_count"] = 0
            for o in ["icache_req","icache_addr","icache_ready","dcache_req","dcache_addr",
                       "dcache_wdata","dcache_wen","dcache_ready","core_stall","core_halted",
                       "retire_valid","retire_count"]:
                ctx.set_output(o, 0)
            return

        icache_rdata = ctx.get_input("icache_rdata", NOP)
        icache_valid = ctx.get_input("icache_valid", 1)
        dcache_rdata = ctx.get_input("dcache_rdata", 0)
        dcache_valid = ctx.get_input("dcache_valid", 1)

        # Read pipeline state
        pc = ctx.state.setdefault("pc", RESET_PC)
        fetch_v = ctx.state.setdefault("fetch_valid", 0)
        fetch_i = ctx.state.setdefault("fetch_instr", 0)
        fetch_p = ctx.state.setdefault("fetch_pc", 0)
        decode_v = ctx.state.setdefault("decode_valid", 0)
        decode_i = ctx.state.setdefault("decode_instr", 0)
        decode_p = ctx.state.setdefault("decode_pc", 0)
        exec_v = ctx.state.setdefault("exec_valid", 0)
        exec_r = ctx.state.setdefault("exec_alu_result", 0)
        exec_bt = ctx.state.setdefault("exec_branch_taken", 0)
        exec_bta = ctx.state.setdefault("exec_branch_target", 0)
        mem_v = ctx.state.setdefault("mem_valid", 0)
        mem_r = ctx.state.setdefault("mem_alu_result", 0)
        mem_we = ctx.state.setdefault("mem_wb_en", 0)
        mem_rdv = ctx.state.setdefault("mem_rd", 0)
        mem_il = ctx.state.setdefault("mem_is_load", 0)
        mem_ld = ctx.state.setdefault("mem_load_data", 0)
        wb_v = ctx.state.setdefault("wb_valid", 0)
        wb_r = ctx.state.setdefault("wb_result", 0)
        wb_we = ctx.state.setdefault("wb_wb_en", 0)
        wb_rdv = ctx.state.setdefault("wb_rd", 0)
        retire_c = ctx.state.setdefault("retire_count", 0)

        # Stall
        icache_stall = fetch_v and not icache_valid
        is_load = (decode_i & 0x7F) == 0x03 if isinstance(decode_i, int) else False
        is_store = (decode_i & 0x7F) == 0x23 if isinstance(decode_i, int) else False
        dcache_stall = exec_v and (is_load or is_store) and not dcache_valid

        # Pipeline advance: each stage shifts to next (if no stall)
        nf_v = 1 if (not icache_stall and icache_valid) else (fetch_v if icache_stall else 0)
        nf_i = icache_rdata if (not icache_stall and icache_valid) else fetch_i
        nf_pc = pc if (not icache_stall and icache_valid) else fetch_p
        npc = pc + 4 if not icache_stall else pc

        nd_v = fetch_v
        nd_i = fetch_i
        nd_p = fetch_p

        ne_v = decode_v and not dcache_stall
        ne_r = decode_p + 4 if isinstance(decode_i, int) and decode_i == NOP else 0
        ne_bt = 0
        ne_bta = 0

        nm_v = exec_v
        nm_r = exec_r
        nm_we = 1 if (isinstance(decode_i, int) and decode_i == NOP) else 0
        nm_rdv = 0
        nm_il = is_load
        nm_ld = dcache_rdata

        nw_v = mem_v
        nw_r = mem_ld if mem_il else mem_r
        nw_we = mem_we
        nw_rdv = mem_rdv

        # Retire
        retire_now = wb_v and wb_we
        if retire_now:
            retire_c += 1

        # Update state
        ctx.state.update({
            "pc": npc, "fetch_valid": nf_v, "fetch_instr": nf_i, "fetch_pc": nf_pc,
            "decode_valid": nd_v, "decode_instr": nd_i, "decode_pc": nd_p,
            "exec_valid": ne_v, "exec_alu_result": ne_r, "exec_branch_taken": ne_bt, "exec_branch_target": ne_bta,
            "mem_valid": nm_v, "mem_alu_result": nm_r, "mem_wb_en": nm_we, "mem_rd": nm_rdv, "mem_is_load": nm_il, "mem_load_data": nm_ld,
            "wb_valid": nw_v, "wb_result": nw_r, "wb_wb_en": nw_we, "wb_rd": nw_rdv,
            "pipeline_active": 1 if retire_now else ctx.state.get("pipeline_active", 0),
            "retire_count": retire_c,
        })

        # Outputs
        ctx.set_output("icache_req", 0 if fetch_v else 1)
        ctx.set_output("icache_addr", npc)
        ctx.set_output("icache_ready", 1)
        ctx.set_output("dcache_req", 1 if (exec_v and (is_load or is_store)) else 0)
        ctx.set_output("dcache_addr", exec_r)
        ctx.set_output("dcache_wdata", 0)
        ctx.set_output("dcache_wen", 1 if is_store else 0)
        ctx.set_output("dcache_ready", 1)
        ctx.set_output("core_stall", 1 if (icache_stall or dcache_stall) else 0)
        ctx.set_output("core_halted", 0)
        ctx.set_output("retire_valid", retire_now)
        ctx.set_output("retire_count", retire_c & 0x7)

    return {
        "name": "rv64_core",
        "inputs": ["clk", "rst_n", "icache_rdata", "icache_valid", "dcache_rdata", "dcache_valid"],
        "outputs": ["icache_req", "icache_addr", "icache_ready", "dcache_req", "dcache_addr",
                     "dcache_wdata", "dcache_wen", "dcache_ready", "core_stall", "core_halted",
                     "retire_valid", "retire_count"],
        "init": init,
        "cycle": cycle,
    }


# =====================================================================
# Cycle-level L1 Cache (FSM: IDLE → TAG_CHECK → REFILL_WAIT → REFILL_STORE)
# =====================================================================

def cycle_l1_cache() -> dict:
    """Cycle-level L1 cache behavioral model."""
    IDLE = 0; TAG_CHECK = 1; REFILL_WAIT = 2; REFILL_STORE = 3
    XLEN = 64; INDEX_WIDTH = 6; OFFSET_WIDTH = 6; TAG_WIDTH = 52
    NUM_SETS = 64

    def init(ctx: CycleContext):
        ctx.state["cache_fsm"] = IDLE
        ctx.state["index"] = 0
        ctx.state["tag"] = 0
        ctx.state["pending_addr"] = 0
        ctx.state["refill_waits"] = 0
        ctx.state["tag_array"] = {}
        ctx.state["data_array"] = {}
        ctx.state["valid_array"] = {}
        ctx.state["lru"] = {}

    def cycle(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        req = ctx.get_input("req", 0)
        addr = ctx.get_input("addr", 0)
        fill_data = ctx.get_input("fill_data", 0)
        fill_valid = ctx.get_input("fill_valid", 0)

        if rst_n == 0:
            init(ctx)
            ctx.set_output("rdata", 0)
            ctx.set_output("valid", 0)
            ctx.set_output("ready", 1)
            ctx.set_output("miss", 0)
            ctx.set_output("miss_addr", 0)
            return

        fsm = ctx.state["cache_fsm"]
        index = (addr >> OFFSET_WIDTH) & (NUM_SETS - 1)
        tag = addr >> (OFFSET_WIDTH + INDEX_WIDTH)
        tag_str = f"{tag}"

        ctx.state["refill_waits"] = ctx.state.get("refill_waits", 0) + 1
        tag_array = ctx.state["tag_array"]
        valid_array = ctx.state["valid_array"]
        data_array = ctx.state["data_array"]
        hit = valid_array.get(index, False) and tag_array.get(index) == tag

        if fsm == IDLE:
            if req:
                ctx.state["pending_addr"] = addr
                ctx.state["index"] = index
                ctx.state["tag"] = tag
                ctx.state["cache_fsm"] = TAG_CHECK
                ctx.set_output("ready", 1)
                ctx.set_output("valid", 0)
                ctx.set_output("miss", 0)
            else:
                ctx.set_output("ready", 1)
                ctx.set_output("valid", 0)
                ctx.set_output("miss", 0)

        elif fsm == TAG_CHECK:
            if hit:
                rdata = data_array.get(index, {}).get(tag, 0)
                ctx.set_output("rdata", rdata)
                ctx.set_output("valid", 1)
                ctx.set_output("ready", 1)
                ctx.set_output("miss", 0)
                ctx.state["cache_fsm"] = IDLE
            else:
                ctx.set_output("valid", 0)
                ctx.set_output("ready", 0)
                ctx.set_output("miss", 1)
                ctx.set_output("miss_addr", addr)
                ctx.state["cache_fsm"] = REFILL_WAIT
                ctx.state["refill_waits"] = 0

        elif fsm == REFILL_WAIT:
            ctx.set_output("valid", 0)
            ctx.set_output("ready", 0)
            ctx.set_output("miss", 0)
            if fill_valid:
                ctx.state["cache_fsm"] = REFILL_STORE
                ctx.state["data_array"][index] = {tag: fill_data}
                ctx.state["tag_array"][index] = tag
                ctx.state["valid_array"][index] = True
            else:
                ctx.set_output("miss_addr", ctx.state.get("pending_addr", addr))

        elif fsm == REFILL_STORE:
            ctx.set_output("rdata", fill_data)
            ctx.set_output("valid", 1)
            ctx.set_output("ready", 1)
            ctx.set_output("miss", 0)
            ctx.state["cache_fsm"] = IDLE

        # Default outputs for unhandled paths
        ctx.set_output("rdata", ctx.get_output("rdata", 0))
        ctx.set_output("miss_addr", ctx.get_output("miss_addr", 0))

    return {
        "name": "l1_cache",
        "inputs": ["clk", "rst_n", "req", "addr", "fill_data", "fill_valid", "wdata", "wen"],
        "outputs": ["rdata", "valid", "ready", "miss", "miss_addr"],
        "init": init,
        "cycle": cycle,
    }


# =====================================================================
# Cycle-level NoC Router (input buffer + XY + crossbar)
# =====================================================================

def cycle_noc_router() -> dict:
    """Cycle-level 5-port NoC router behavioral model."""
    BUFFER_DEPTH = 4
    PORTS = ['e', 'w', 'n', 's', 'j']

    def init(ctx: CycleContext):
        for p in PORTS:
            ctx.state[f"{p}_buf"] = []
            ctx.state[f"{p}_count"] = 0

    def cycle(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        x_pos = ctx.get_input("x_pos", 0)
        y_pos = ctx.get_input("y_pos", 0)

        if rst_n == 0:
            init(ctx)
            for p in PORTS:
                ctx.set_output(f"{p}_ready", 1)
                ctx.set_output(f"{p}_flit_o", 0)
                ctx.set_output(f"{p}_valid_o", 0)
            return

        # Input stage: push flits into buffers
        for p in PORTS:
            flit = ctx.get_input(f"{p}_flit", 0)
            valid = ctx.get_input(f"{p}_valid", 0) if p != 'j' else ctx.get_input("loc_inj_valid", 0)
            buf = ctx.state[f"{p}_buf"]

            if valid and len(buf) < BUFFER_DEPTH:
                buf.append(flit)

        # Route + output stage
        # XY routing on header flit
        for p in PORTS:
            buf = ctx.state[f"{p}_buf"]
            ctx.set_output(f"{p}_ready", 1 if len(buf) < BUFFER_DEPTH else 0)

            if buf:
                flit = buf[0]
                dest_x = flit & 0x7
                dest_y = (flit >> 3) & 0x7

                # Determine output port (XY routing)
                if dest_x > x_pos:
                    out_port = 'e'
                elif dest_x < x_pos:
                    out_port = 'w'
                elif dest_y > y_pos:
                    out_port = 'n'
                elif dest_y < y_pos:
                    out_port = 's'
                else:
                    out_port = 'j'

                # Pop from input buffer
                buf.pop(0)

                # Route to output
                if out_port == 'j':
                    ctx.set_output("loc_ej_flit", flit)
                    ctx.set_output("loc_ej_valid", 1)
                else:
                    ctx.set_output(f"{out_port}_flit_o", flit)
                    ctx.set_output(f"{out_port}_valid_o", 1)
            else:
                if p != 'j':
                    ctx.set_output(f"{p}_flit_o", 0)
                    ctx.set_output(f"{p}_valid_o", 0)

        ctx.set_output("loc_ej_flit", ctx.get_output("loc_ej_flit", 0))
        ctx.set_output("loc_ej_valid", ctx.get_output("loc_ej_valid", 0))

    return {
        "name": "noc_router",
        "inputs": ["clk", "rst_n", "x_pos", "y_pos",
                    "e_flit", "e_valid", "w_flit", "w_valid",
                    "n_flit", "n_valid", "s_flit", "s_valid",
                    "loc_inj_flit", "loc_inj_valid", "loc_inj_ready"],
        "outputs": ["e_ready", "e_flit_o", "e_valid_o",
                     "w_ready", "w_flit_o", "w_valid_o",
                     "n_ready", "n_flit_o", "n_valid_o",
                     "s_ready", "s_flit_o", "s_valid_o",
                     "loc_inj_ready", "loc_ej_flit", "loc_ej_valid"],
        "init": init,
        "cycle": cycle,
    }


# =====================================================================
# Cycle-level Coherence Directory (5-state FSM)
# =====================================================================

def cycle_coherence_dir() -> dict:
    """Cycle-level MSI coherence directory behavioral model."""
    IDLE = 0; LOOKUP = 1; PROBE = 2; UPDATE = 3; WB = 4
    NUM_CORES = 64

    def init(ctx: CycleContext):
        ctx.state["dir_fsm"] = IDLE
        ctx.state["dir_table"] = {}
        ctx.state["probe_cycles"] = 0
        ctx.state["pending_core"] = 0
        ctx.state["pending_addr"] = 0
        ctx.state["pending_type"] = 0

    def cycle(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        req_valid = ctx.get_input("req_valid", 0)
        req_core_id = ctx.get_input("req_core_id", 0)
        req_addr = ctx.get_input("req_addr", 0)
        req_is_write = ctx.get_input("req_is_write", 0)
        snoop_ack = ctx.get_input("snoop_ack", 0)

        if rst_n == 0:
            init(ctx)
            ctx.set_output("resp_valid", 0)
            ctx.set_output("resp_action", 0)
            ctx.set_output("probe_valid", 0)
            ctx.set_output("probe_addr", 0)
            ctx.set_output("probe_invalidate", 0)
            ctx.set_output("probe_targets", 0)
            return

        fsm = ctx.state["dir_fsm"]
        dir_table = ctx.state["dir_table"]

        if fsm == IDLE:
            if req_valid:
                tag = req_addr >> 12
                entry = dir_table.get(tag, {"state": 0, "sharers": 0, "owner": -1})
                ctx.state["pending_core"] = req_core_id
                ctx.state["pending_addr"] = req_addr
                ctx.state["pending_type"] = req_is_write
                ctx.state["dir_fsm"] = LOOKUP
                ctx.state["lookup_tag"] = tag
                ctx.state["lookup_entry"] = entry

                ctx.set_output("resp_valid", 0)
                ctx.set_output("probe_valid", 0)
            else:
                ctx.set_output("resp_valid", 0)
                ctx.set_output("probe_valid", 0)

        elif fsm == LOOKUP:
            entry = ctx.state.get("lookup_entry", {})
            state = entry.get("state", 0)  # 0=I, 1=S, 2=M
            owner = entry.get("owner", -1)

            if req_is_write:
                # Modified request
                if state == 2 and owner >= 0 and owner != ctx.state["pending_core"]:
                    # Need to invalidate current owner
                    ctx.set_output("probe_valid", 1)
                    ctx.set_output("probe_addr", ctx.state["pending_addr"])
                    ctx.set_output("probe_invalidate", 1)
                    ctx.state["dir_fsm"] = PROBE
                    ctx.state["probe_cycles"] = 0
                else:
                    # Grant immediately
                    ctx.state["dir_fsm"] = UPDATE
                    ctx.state["update_state"] = 2  # M
                    ctx.state["update_owner"] = ctx.state["pending_core"]
                    ctx.set_output("resp_valid", 0)
            else:
                # Shared request
                if state == 2:
                    # Downgrade owner
                    ctx.set_output("probe_valid", 1)
                    ctx.set_output("probe_addr", ctx.state["pending_addr"])
                    ctx.set_output("probe_invalidate", 0)
                    ctx.state["dir_fsm"] = PROBE
                    ctx.state["probe_cycles"] = 0
                else:
                    ctx.state["dir_fsm"] = UPDATE
                    ctx.state["update_state"] = 1  # S
                    ctx.state["update_owner"] = -1

        elif fsm == PROBE:
            ctx.state["probe_cycles"] += 1
            ctx.set_output("probe_valid", 1)
            if ctx.state["probe_cycles"] >= 2:  # 2-cycle probe
                ctx.state["dir_fsm"] = UPDATE
                ctx.set_output("probe_valid", 0)

        elif fsm == UPDATE:
            tag = ctx.state.get("lookup_tag", 0)
            new_state = ctx.state.get("update_state", 1)
            new_owner = ctx.state.get("update_owner", -1)
            core_id = ctx.state["pending_core"]

            entry = dir_table.get(tag, {"state": 0, "sharers": 0, "owner": -1})
            sharers = entry.get("sharers", 0)
            if new_state == 2:
                sharers = 1 << core_id
            else:
                sharers |= (1 << core_id)

            dir_table[tag] = {
                "state": new_state,
                "sharers": sharers,
                "owner": new_owner,
            }

            ctx.set_output("resp_valid", 1)
            ctx.set_output("resp_action", new_state)
            ctx.set_output("probe_valid", 0)
            ctx.state["dir_fsm"] = IDLE

        # Default outputs
        ctx.set_output("resp_action", ctx.get_output("resp_action", 0))
        ctx.set_output("resp_valid", ctx.get_output("resp_valid", 0))
        ctx.set_output("probe_addr", ctx.get_output("probe_addr", 0))

    return {
        "name": "coherence_dir",
        "inputs": ["clk", "rst_n", "req_valid", "req_core_id", "req_addr", "req_is_write", "snoop_ack"],
        "outputs": ["resp_valid", "resp_action", "probe_valid", "probe_addr", "probe_invalidate", "probe_targets"],
        "init": init,
        "cycle": cycle,
    }


# =====================================================================
# Simulation runner
# =====================================================================

ALL_CYCLE_MODELS = {
    "rv64_core": cycle_rv64_core,
    "l1_cache": cycle_l1_cache,
    "noc_router": cycle_noc_router,
    "coherence_dir": cycle_coherence_dir,
}


def run_cycle_simulation(model_builder: dict, num_cycles: int = 50,
                          input_sequence: Optional[List[Dict]] = None) -> List[Dict]:
    """Run a cycle-level behavioral model and capture per-cycle traces.

    Args:
        model_builder: Return value from cycle_*() function
        num_cycles: Number of cycles to simulate
        input_sequence: Optional list of {input_name: value} per cycle

    Returns:
        List of {"cycle": N, "inputs": {...}, "outputs": {...}, "state": {...}}
    """
    ctx = CycleContext()
    model_builder["init"](ctx)
    traces = []

    for cycle in range(num_cycles):
        ctx.cycle = cycle
        ctx.inputs["rst_n"] = 0 if cycle < 3 else 1

        # Apply input sequence if provided
        if input_sequence and cycle < len(input_sequence):
            for k, v in input_sequence[cycle].items():
                ctx.inputs[k] = v

        # Default inputs: leave missing ports unset (model uses get_input defaults)

        model_builder["cycle"](ctx)

        traces.append({
            "cycle": cycle,
            "inputs": dict(ctx.inputs),
            "outputs": dict(ctx.outputs),
            "state": dict(ctx.state),
        })
        ctx.outputs.clear()

    return traces
