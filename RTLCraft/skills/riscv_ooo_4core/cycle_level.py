"""
skills.riscv_ooo_4core.cycle_level — Layer 2: Cycle-Level Models + Template Registry
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry

def ooo_core_cycle(**kwargs) -> Callable[[CycleContext], None]:
    NOP = 0x00000013; RESET_PC = 0x1000
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        instr = ctx.get_input("icache_rdata", NOP)
        icache_valid = ctx.get_input("icache_valid", 1)
        if rst_n == 0:
            ctx.state["pc"] = RESET_PC
            ctx.state["fetch_valid"] = 0
            ctx.state["rob_head"] = 0
            ctx.state["rob_tail"] = 0
            ctx.state["retire_count"] = 0
            ctx.state["cycle"] = 0
            ctx.state["pht"] = {}
            for o in ["icache_req", "icache_addr", "retire_valid", "retire_count",
                       "core_stall", "dcache_req", "dcache_addr"]:
                ctx.set_output(o, 0)
            return
        ctx.state["cycle"] += 1
        fetch_valid = ctx.state.setdefault("fetch_valid", 0)
        pc = ctx.state.setdefault("pc", RESET_PC)
        rob_tail = ctx.state.setdefault("rob_tail", 0)
        retire_c = ctx.state.setdefault("retire_count", 0)
        if not fetch_valid and icache_valid:
            fetch_valid = 1
            ctx.state["fetch_valid"] = 1
        if fetch_valid:
            rob_tail = (rob_tail + 2) % ROB_DEPTH
            ctx.state["rob_tail"] = rob_tail
            pc += 8
            ctx.state["pc"] = pc
        if rob_tail != ctx.state.setdefault("rob_head", 0):
            head = ctx.state["rob_head"]
            ctx.state["rob_head"] = (head + 1) % ROB_DEPTH
            retire_c += 1
            ctx.state["retire_count"] = retire_c
        ctx.set_output("icache_req", 1)
        ctx.set_output("icache_addr", pc)
        ctx.set_output("retire_valid", 1)
        ctx.set_output("retire_count", retire_c & 0x7)
        ctx.set_output("core_stall", 0)
    return behavior

def l1_cache_cycle(**kwargs) -> Callable[[CycleContext], None]:
    IDLE, TAG_CHECK, REFILL, SNOOP = 0, 1, 2, 3
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["fsm"] = IDLE
            ctx.state["tag_arr"] = {}
            ctx.state["data_arr"] = {}
            ctx.state["valid_arr"] = {}
            ctx.state["mesi_arr"] = {}
            for o in ["rdata", "valid", "ready", "miss"]:
                ctx.set_output(o, 0)
            return
        fsm = ctx.state.setdefault("fsm", IDLE)
        req = ctx.get_input("req", 0)
        addr = ctx.get_input("addr", 0)
        snoop_inv = ctx.get_input("snoop_invalidate", 0)
        snoop_addr = ctx.get_input("snoop_addr", 0)
        idx = (addr >> 6) & 0x3F
        tag = addr >> 12
        if fsm == IDLE and req:
            ctx.state["fsm"] = TAG_CHECK
        elif fsm == TAG_CHECK:
            hit = ctx.state["valid_arr"].get(idx, False) and ctx.state["tag_arr"].get(idx) == tag
            if hit:
                ctx.set_output("rdata", ctx.state["data_arr"].get(idx, {}).get(tag, 0))
                ctx.set_output("valid", 1); ctx.state["fsm"] = IDLE
            else:
                ctx.set_output("miss", 1); ctx.set_output("ready", 0)
                ctx.state["fsm"] = REFILL
        elif fsm == REFILL:
            ctx.set_output("valid", 1)
            ctx.state["tag_arr"][idx] = tag
            ctx.state["valid_arr"][idx] = True
            ctx.state["data_arr"][idx] = {tag: ctx.get_input("fill_data", 0)}
            ctx.state["mesi_arr"][idx] = "E"
            ctx.state["fsm"] = IDLE
        elif snoop_inv:
            sidx = (snoop_addr >> 6) & 0x3F
            if ctx.state.get("mesi_arr", {}).get(sidx) == "M":
                ctx.set_output("snoop_ack", 1)
            ctx.state["mesi_arr"][sidx] = "I"
            ctx.state["fsm"] = IDLE
        ctx.set_output("ready", 1 if fsm == IDLE else 0)
    return behavior

def coherence_bus_cycle(**kwargs) -> Callable[[CycleContext], None]:
    IDLE, SNOOP, RESP = 0, 1, 2
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["fsm"] = IDLE; ctx.state["pending_addr"] = 0
            ctx.state["pending_core"] = 0
            for o in ["snoop_valid", "snoop_addr", "snoop_invalidate",
                       "shared_resp", "data_resp"]:
                ctx.set_output(o, 0)
            return
        fsm = ctx.state.setdefault("fsm", IDLE)
        req_valid = ctx.get_input("req_valid", 0)
        req_core = ctx.get_input("req_core", 0)
        req_addr = ctx.get_input("req_addr", 0)
        req_type = ctx.get_input("req_type", 0)
        if fsm == IDLE and req_valid:
            ctx.state["pending_addr"] = req_addr
            ctx.state["pending_core"] = req_core
            ctx.state["fsm"] = SNOOP
            ctx.set_output("snoop_valid", 1)
            ctx.set_output("snoop_addr", req_addr)
            ctx.set_output("snoop_invalidate", 1 if req_type == "read_exclusive" else 0)
        elif fsm == SNOOP:
            ctx.state["fsm"] = RESP
            ctx.set_output("snoop_valid", 0)
        elif fsm == RESP:
            ctx.set_output("shared_resp", 0)
            ctx.set_output("data_resp", 0)
            ctx.state["fsm"] = IDLE
    return behavior

def noc_router_cycle(**kwargs) -> Callable[[CycleContext], None]:
    PORTS = ['e', 'w', 'n', 's', 'j']; BDEPTH = 4
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        x_pos = ctx.get_input("x_pos", 0); y_pos = ctx.get_input("y_pos", 0)
        if rst_n == 0:
            for p in PORTS: ctx.state[f"buf_{p}"] = []
            for o in ["e_ready","w_ready","n_ready","s_ready","loc_inj_ready"]:
                ctx.set_output(o, 1)
            for o in ["e_flit_o","e_valid_o","w_flit_o","w_valid_o",
                       "n_flit_o","n_valid_o","s_flit_o","s_valid_o",
                       "loc_ej_flit","loc_ej_valid"]:
                ctx.set_output(o, 0)
            return
        for p in ['e','w','n','s']:
            flit = ctx.get_input(f"{p}_flit", 0)
            valid = ctx.get_input(f"{p}_valid", 0)
            buf = ctx.state.setdefault(f"buf_{p}", [])
            if valid and len(buf) < BDEPTH:
                buf.append(flit)
        lj_flit = ctx.get_input("loc_inj_flit", 0)
        if ctx.get_input("loc_inj_valid", 0):
            buf_j = ctx.state.setdefault("buf_j", [])
            if len(buf_j) < BDEPTH:
                buf_j.append(lj_flit)
        for p in PORTS:
            buf = ctx.state.setdefault(f"buf_{p}", [])
            if buf:
                flit = buf.pop(0)
                dx = flit & 0x7; dy = (flit >> 3) & 0x7
                if dx > x_pos: out = 'e'
                elif dx < x_pos: out = 'w'
                elif dy > y_pos: out = 'n'
                elif dy < y_pos: out = 's'
                else: out = 'j'
                if out == 'j':
                    ctx.set_output("loc_ej_flit", flit)
                    ctx.set_output("loc_ej_valid", 1)
                else:
                    ctx.set_output(f"{out}_flit_o", flit)
                    ctx.set_output(f"{out}_valid_o", 1)
            if p != 'j':
                ctx.set_output(f"{p}_ready", 1 if len(buf) < BDEPTH else 0)
        ctx.set_output("loc_inj_ready", 1 if len(ctx.state.get("buf_j", [])) < BDEPTH else 0)
    return behavior

# =====================================================================

# Template Registry
# =====================================================================

_template_map = {
    "ooo_core": ooo_core_cycle,
    "l1_cache": l1_cache_cycle,
    "coherence_bus": coherence_bus_cycle,
    "noc_router": noc_router_cycle,
}
for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

ooo_core_template = ooo_core_cycle
l1_cache_template = l1_cache_cycle
coherence_bus_template = coherence_bus_cycle
noc_router_template = noc_router_cycle
