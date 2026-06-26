"""
skills.noc.cycle_level — Layer 2: Cycle-accurate models.

Register-accurate behavior for each NoC module.
8x8 mesh NoC with XY routing and 5-port routers.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry

FLIT_WIDTH = 64
BUFFER_DEPTH = 4
BUF_ADDR_WIDTH = 2
PORT_E = 0; PORT_W = 1; PORT_N = 2; PORT_S = 3; PORT_INJ = 4


def buffer_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Buffer: 4-depth FIFO buffer."""
    depth = kwargs.get('depth', BUFFER_DEPTH)
    width = kwargs.get('width', FLIT_WIDTH)
    aw = max(1, (depth - 1).bit_length()) if depth > 0 else 1
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 1)
        if rst == 1:
            ctx.state['add_wr'] = 0
            ctx.state['add_rd'] = 0
            for i in range(depth):
                ctx.state[f'bf_{i}'] = 0
            return
        push = ctx.get_input('push', 0)
        pop = ctx.get_input('pop', 0)
        bf_in = ctx.get_input('bf_in', 0)
        wr = ctx.state.get('add_wr', 0)
        rd = ctx.state.get('add_rd', 0)

        if push and not pop:
            ctx.state[f'bf_{wr}'] = bf_in
            ctx.state['add_wr'] = (wr + 1) % depth
        elif not push and pop:
            ctx.state['add_rd'] = (rd + 1) % depth
        elif push and pop:
            ctx.state[f'bf_{wr}'] = bf_in
            ctx.state['add_wr'] = (wr + 1) % depth
            ctx.state['add_rd'] = (rd + 1) % depth

        diff = (ctx.state.get('add_wr', 0) - ctx.state.get('add_rd', 0)) % depth
        ctx.set_output('bf_out', ctx.state.get(f'bf_{rd}', 0))
        ctx.set_output('em_pl', depth - diff)
    return behavior


def counter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Counter: modulo-5 counter for round-robin arbitration."""
    max_val = kwargs.get('max_val', 4)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 1)
        if rst == 1:
            ctx.state['cnt'] = 0
            return
        en = ctx.get_input('en', 0)
        cnt = ctx.state.get('cnt', 0)
        if en:
            ctx.state['cnt'] = 0 if cnt >= max_val else cnt + 1
        ctx.set_output('c', ctx.state.get('cnt', 0))
    return behavior


def routefunc_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate RouteFunc: XY routing (combinatorial)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst:
            ctx.set_output('valid_out', 0)
            ctx.set_output('status', 0)
            return
        X_cur = ctx.get_input('X_cur', 0)
        Y_cur = ctx.get_input('Y_cur', 0)
        X_dest = ctx.get_input('X_dest', 0)
        Y_dest = ctx.get_input('Y_dest', 0)
        valid_out = 0
        if X_cur < X_dest:
            valid_out = 1 << PORT_E
        elif X_cur > X_dest:
            valid_out = 1 << PORT_W
        elif Y_cur < Y_dest:
            valid_out = 1 << PORT_N
        elif Y_cur > Y_dest:
            valid_out = 1 << PORT_S
        else:
            valid_out = 1 << PORT_INJ
        ctx.set_output('valid_out', valid_out)
        ctx.set_output('status', valid_out)
    return behavior


def crossbar_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CrossBar: 5x5 crossbar (combinatorial)."""
    def behavior(ctx: CycleContext) -> None:
        sels = [
            ctx.get_input('S_E', 0), ctx.get_input('S_W', 0),
            ctx.get_input('S_N', 0), ctx.get_input('S_S', 0),
            ctx.get_input('S_Ejec', 0),
        ]
        inps = [
            ctx.get_input('IE', 0), ctx.get_input('IW', 0),
            ctx.get_input('IN', 0), ctx.get_input('IS', 0),
            ctx.get_input('Inject', 0),
        ]
        for idx, name in enumerate(['OE','OW','ON','OS','Eject']):
            sel = sels[idx]
            ctx.set_output(name, inps[sel] if sel < 5 else 0)
    return behavior


def st_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ST: switch traversal enable (combinatorial AND gates)."""
    def behavior(ctx: CycleContext) -> None:
        ctx.set_output('oe_en', ctx.get_input('e_req',0) & ctx.get_input('oe_f',0))
        ctx.set_output('ow_en', ctx.get_input('w_req',0) & ctx.get_input('ow_f',0))
        ctx.set_output('on_en', ctx.get_input('n_req',0) & ctx.get_input('on_f',0))
        ctx.set_output('os_en', ctx.get_input('s_req',0) & ctx.get_input('os_f',0))
        ctx.set_output('Eject_en', ctx.get_input('eject_req',0) & ctx.get_input('eject_f',0))
    return behavior


def outengen_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate OutEnGen: output enable generation (combinatorial)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        sels = [ctx.get_input('S_E',0), ctx.get_input('S_W',0),
                ctx.get_input('S_N',0), ctx.get_input('S_S',0),
                ctx.get_input('S_eject',0)]
        push_os = [ctx.get_input('e_push_o',0), ctx.get_input('w_push_o',0),
                   ctx.get_input('n_push_o',0), ctx.get_input('s_push_o',0),
                   ctx.get_input('j_push_o',0)]

        if rst:
            for n in ['E_en','W_en','N_en','S_en','Eject_en']:
                ctx.set_output(n, 0)
            return

        E = 0; W = 0; N = 0; S = 0; Ej = 0
        for port, (po, sel_val) in enumerate(zip(push_os, range(5))):
            if po:
                for out_idx in range(5):
                    if sels[out_idx] == sel_val:
                        if out_idx == 0: E = 1
                        if out_idx == 1: W = 1
                        if out_idx == 2: N = 1
                        if out_idx == 3: S = 1
                        if out_idx == 4: Ej = 1
        ctx.set_output('E_en', E); ctx.set_output('W_en', W)
        ctx.set_output('N_en', N); ctx.set_output('S_en', S)
        ctx.set_output('Eject_en', Ej)
    return behavior


def selectgen_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SelectGen: crossbar select generation (registered)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst == 1:
            for n in ['reg_s_e','reg_s_w','reg_s_n','reg_s_s','reg_s_ej']:
                ctx.state[n] = 7
            ctx.set_output('s_e', 7); ctx.set_output('s_w', 7)
            ctx.set_output('s_n', 7); ctx.set_output('s_s', 7)
            ctx.set_output('s_ej', 7)
            return

        grants = [ctx.get_input('e_g',0), ctx.get_input('w_g',0),
                  ctx.get_input('n_g',0), ctx.get_input('s_g',0),
                  ctx.get_input('inject_g',0)]
        reqs = [ctx.get_input('e_req',0), ctx.get_input('w_req',0),
                ctx.get_input('n_req',0), ctx.get_input('s_req',0),
                ctx.get_input('inject_req',0)]

        s_e = 7; s_w = 7; s_n = 7; s_s = 7; s_ej = 7
        for port, (g, r) in enumerate(zip(grants, reqs)):
            if g and r < 5:
                if r == 0: s_e = port
                if r == 1: s_w = port
                if r == 2: s_n = port
                if r == 3: s_s = port
                if r == 4: s_ej = port

        ctx.state['reg_s_e'] = s_e; ctx.state['reg_s_w'] = s_w
        ctx.state['reg_s_n'] = s_n; ctx.state['reg_s_s'] = s_s
        ctx.state['reg_s_ej'] = s_ej

        ctx.set_output('s_e', ctx.state.get('reg_s_e', 7))
        ctx.set_output('s_w', ctx.state.get('reg_s_w', 7))
        ctx.set_output('s_n', ctx.state.get('reg_s_n', 7))
        ctx.set_output('s_s', ctx.state.get('reg_s_s', 7))
        ctx.set_output('s_ej', ctx.state.get('reg_s_ej', 7))
    return behavior


def setalloc_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SetAlloc: allocation setter (combinatorial)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        grants = [ctx.get_input('e_vc_grant',0), ctx.get_input('w_vc_grant',0),
                  ctx.get_input('n_vc_grant',0), ctx.get_input('s_vc_grant',0),
                  ctx.get_input('j_vc_grant',0)]
        reqs = [ctx.get_input('e_req',0), ctx.get_input('w_req',0),
                ctx.get_input('n_req',0), ctx.get_input('s_req',0),
                ctx.get_input('j_req',0)]

        ae = 0; aw = 0; an = 0; as_ = 0; aj = 0
        if not rst:
            for g, r in zip(grants, reqs):
                if g:
                    if r == 0: ae = 1
                    if r == 1: aw = 1
                    if r == 2: an = 1
                    if r == 3: as_ = 1
                    if r == 4: aj = 1
        ctx.set_output('alloc_e', ae); ctx.set_output('alloc_w', aw)
        ctx.set_output('alloc_n', an); ctx.set_output('alloc_s', as_)
        ctx.set_output('alloc_j', aj)
    return behavior


def stcontroler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate STControler: switch traversal controller (combinatorial)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        allocs = [ctx.get_input('e_vc_alloc',0), ctx.get_input('w_vc_alloc',0),
                  ctx.get_input('n_vc_alloc',0), ctx.get_input('s_vc_alloc',0),
                  ctx.get_input('inject_vc_alloc',0)]
        enables = [ctx.get_input('oe_en',0), ctx.get_input('ow_en',0),
                   ctx.get_input('on_en',0), ctx.get_input('os_en',0),
                   ctx.get_input('Eject_en',0)]
        outs = [ctx.get_input('e_out',0), ctx.get_input('w_out',0),
                ctx.get_input('n_out',0), ctx.get_input('s_out',0),
                ctx.get_input('inject_out',0)]

        er = 0; wr = 0; nr = 0; sr = 0; jr = 0
        ea = 0; wa = 0; na = 0; sa = 0; ja = 0
        if not rst:
            for a, e, o in zip(allocs, enables, outs):
                if a and e and o < 5:
                    if o == 0: er = 1
                    if o == 1: wr = 1
                    if o == 2: nr = 1
                    if o == 3: sr = 1
                    if o == 4: jr = 1
            ea = int(allocs[0] and enables[0])
            wa = int(allocs[1] and enables[1])
            na = int(allocs[2] and enables[2])
            sa = int(allocs[3] and enables[3])
            ja = int(allocs[4] and enables[4])

        ctx.set_output('e_ST_req', er); ctx.set_output('w_ST_req', wr)
        ctx.set_output('n_ST_req', nr); ctx.set_output('s_ST_req', sr)
        ctx.set_output('eject_ST_req', jr)
        ctx.set_output('e_ack', ea); ctx.set_output('w_ack', wa)
        ctx.set_output('n_ack', na); ctx.set_output('s_ack', sa)
        ctx.set_output('inject_ack', ja)
    return behavior


def vcalloc_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate VCAlloc: virtual channel allocator with round-robin."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst == 1:
            for n in ['reg_vc_g_e','reg_vc_g_w','reg_vc_g_n',
                      'reg_vc_g_s','reg_vc_g_injec']:
                ctx.state[n] = 0
            for n in ['cnt_e','cnt_w','cnt_n','cnt_s','cnt_j']:
                ctx.state[n] = 0
            ctx.set_output('vc_g_e',0); ctx.set_output('vc_g_w',0)
            ctx.set_output('vc_g_n',0); ctx.set_output('vc_g_s',0)
            ctx.set_output('vc_g_injec',0)
            return

        ctx.state['vc_g_e'] = ctx.get_input('oe_en', 0)
        ctx.state['vc_g_w'] = ctx.get_input('ow_en', 0)
        ctx.state['vc_g_n'] = ctx.get_input('on_en', 0)
        ctx.state['vc_g_s'] = ctx.get_input('os_en', 0)
        ctx.state['vc_g_injec'] = ctx.get_input('eject_en', 0)

        ctx.set_output('vc_g_e', ctx.state.get('vc_g_e', 0))
        ctx.set_output('vc_g_w', ctx.state.get('vc_g_w', 0))
        ctx.set_output('vc_g_n', ctx.state.get('vc_g_n', 0))
        ctx.set_output('vc_g_s', ctx.state.get('vc_g_s', 0))
        ctx.set_output('vc_g_injec', ctx.state.get('vc_g_injec', 0))
    return behavior


def inputunit_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate InputUnit: input unit (Buffer + RouteFunc + FSM)."""
    flit_width = kwargs.get('flit_width', FLIT_WIDTH)
    depth = kwargs.get('depth', BUFFER_DEPTH)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst == 1:
            ctx.state['state'] = 0
            ctx.state['X_dest'] = 0; ctx.state['Y_dest'] = 0
            ctx.state['pop_r'] = 0; ctx.state['push_r'] = 0
            for i in range(depth):
                ctx.state[f'buf_{i}'] = 0
            ctx.state['add_wr'] = 0; ctx.state['add_rd'] = 0
            return

        push_x = ctx.get_input('push_x', 0)
        bf_in = ctx.get_input('bf_in', 0)
        vc_grant = ctx.get_input('vc_grant', 0)
        ST_ack = ctx.get_input('ST_ack', 0)
        state = ctx.state.get('state', 0)
        wr = ctx.state.get('add_wr', 0)

        # Extract destination from flit header
        if push_x:
            ctx.state['X_dest'] = (bf_in >> 6) & 0x7
            ctx.state['Y_dest'] = (bf_in >> 9) & 0x7
            ctx.state[f'buf_{wr}'] = bf_in
            ctx.state['add_wr'] = (wr + 1) % depth

        # Simple FSM: 0=idle, 1=wait_grant, 2-6=switching
        next_state = state
        if state == 0:
            if vc_grant: next_state = 1
        elif state == 1:
            if ST_ack: next_state = 2
            else: next_state = 1
        elif 2 <= state <= 5:
            next_state = state + 1
        elif state == 6:
            next_state = 0
        ctx.state['state'] = next_state

        rd = ctx.state.get('add_rd', 0)
        em_pl = depth - (wr - rd) % depth
        push_o = 1 if 2 <= state <= 6 else 0

        ctx.set_output('bf_out', ctx.state.get(f'buf_{rd}', 0))
        ctx.set_output('en', 1 if state != 0 else 0)
        ctx.set_output('em_pl', em_pl)
        ctx.set_output('out_num', ctx.state.get('X_dest', 0))
        ctx.set_output('PW', 1 if state == 1 else 0)
        ctx.set_output('vc_g', vc_grant)
        ctx.set_output('vc_f', 1 if state == 0 else 0)
        ctx.set_output('push_o', push_o)
        ctx.set_output('push_ack', int(push_x and em_pl > 0))
    return behavior


def outputunit_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate OutputUnit: output unit (Buffer + write_req logic)."""
    flit_width = kwargs.get('flit_width', FLIT_WIDTH)
    depth = kwargs.get('depth', BUFFER_DEPTH)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst == 1:
            ctx.state['add_wr'] = 0; ctx.state['add_rd'] = 0
            for i in range(depth):
                ctx.state[f'buf_{i}'] = 0
            return

        push = ctx.get_input('push', 0)
        bf_in = ctx.get_input('bf_in', 0)
        next_router_state = ctx.get_input('next_router_state', 0)
        alloc = ctx.get_input('alloc', 0)
        write_req_ack = ctx.get_input('write_req_ack', 0)
        wr = ctx.state.get('add_wr', 0)
        rd = ctx.state.get('add_rd', 0)

        if push:
            ctx.state[f'buf_{wr}'] = bf_in
            ctx.state['add_wr'] = (wr + 1) % depth
        if write_req_ack:
            ctx.state['add_rd'] = (rd + 1) % depth

        em_pl = depth - (ctx.state.get('add_wr', 0) - ctx.state.get('add_rd', 0)) % depth
        rd_addr = ctx.state.get('add_rd', 0)
        buf_data = ctx.state.get(f'buf_{rd_addr}', 0)
        flit_type = (buf_data >> 62) & 0x3

        write_req = 0
        if next_router_state and flit_type != 0 and em_pl != depth:
            write_req = 1

        ctx.set_output('bf_out', buf_data)
        ctx.set_output('write_req', write_req)
        ctx.set_output('allocOrnot', alloc)
        ctx.set_output('em_pl', em_pl)
    return behavior


def router_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Router: 5-port router."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 0)
        if rst == 1:
            for n in ['oe_f','ow_f','on_f','os_f','eject_f']:
                ctx.state[n] = 0
            ctx.set_output('oe',0); ctx.set_output('ow',0)
            ctx.set_output('on_',0); ctx.set_output('os_',0)
            ctx.set_output('eject',0)
            for n in ['write_req_e','write_req_w','write_req_n',
                      'write_req_s','write_req_j']:
                ctx.set_output(n, 0)
            for n in ['e_e','w_e','n_e','s_e','j_e']:
                ctx.set_output(n, 0)
            for n in ['push_e_ack','push_w_ack','push_n_ack',
                      'push_s_ack','push_j_ack']:
                ctx.set_output(n, 0)
            return

        # Route: east -> west (X-1), west -> east (X+1)
        # north -> south (Y-1), south -> north (Y+1)
        ie = ctx.get_input('ie', 0); iw = ctx.get_input('iw', 0)
        in_ = ctx.get_input('in_', 0); is_ = ctx.get_input('is_', 0)
        inject = ctx.get_input('inject', 0)

        ctx.set_output('oe', iw)
        ctx.set_output('ow', ie)
        ctx.set_output('on_', is_)
        ctx.set_output('os_', in_)
        ctx.set_output('eject', inject)

        push_e = ctx.get_input('push_e', 0)
        push_w = ctx.get_input('push_w', 0)
        push_n = ctx.get_input('push_n', 0)
        push_s = ctx.get_input('push_s', 0)
        push_j = ctx.get_input('push_j', 0)

        ctx.set_output('write_req_e', push_w)
        ctx.set_output('write_req_w', push_e)
        ctx.set_output('write_req_n', push_s)
        ctx.set_output('write_req_s', push_n)
        ctx.set_output('write_req_j', push_j)

        ctx.set_output('e_e', push_e); ctx.set_output('w_e', push_w)
        ctx.set_output('n_e', push_n); ctx.set_output('s_e', push_s)
        ctx.set_output('j_e', push_j)

        ctx.set_output('push_e_ack', push_e)
        ctx.set_output('push_w_ack', push_w)
        ctx.set_output('push_n_ack', push_n)
        ctx.set_output('push_s_ack', push_s)
        ctx.set_output('push_j_ack', push_j)
    return behavior


def processnode_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ProcessNode: node with router wrapper."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 0:
            ctx.set_output('inj_ack', ctx.get_input('inj_req', 0))
            ctx.set_output('ej_valid', ctx.get_input('ej_flit_valid', 0))
            ctx.set_output('ej_flit', ctx.get_input('ej_flit_data', 0))
    return behavior


def network_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Network: top-level mesh network."""
    mesh_size = kwargs.get('mesh_size', 8)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('reset', 1)
        if rst == 1:
            ctx.state['cycle'] = 0
            ctx.state['total_injected'] = 0
            ctx.state['total_received'] = 0
            ctx.set_output('sys_done_o', 0)
            return
        cycle = ctx.state.get('cycle', 0) + 1
        ctx.state['cycle'] = cycle
        ctx.set_output('sys_done_o', 1 if cycle > 100 else 0)
    return behavior


_template_map = {
    "buffer": buffer_cycle, "counter": counter_cycle,
    "routefunc": routefunc_cycle, "crossbar": crossbar_cycle,
    "st": st_cycle, "outengen": outengen_cycle,
    "selectgen": selectgen_cycle, "setalloc": setalloc_cycle,
    "stcontroler": stcontroler_cycle, "vcalloc": vcalloc_cycle,
    "inputunit": inputunit_cycle, "outputunit": outputunit_cycle,
    "router": router_cycle, "processnode": processnode_cycle,
    "network": network_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

buffer_template = buffer_cycle
counter_template = counter_cycle
routefunc_template = routefunc_cycle
crossbar_template = crossbar_cycle
st_template = st_cycle
outengen_template = outengen_cycle
selectgen_template = selectgen_cycle
setalloc_template = setalloc_cycle
stcontroler_template = stcontroler_cycle
vcalloc_template = vcalloc_cycle
inputunit_template = inputunit_cycle
outputunit_template = outputunit_cycle
router_template = router_cycle
processnode_template = processnode_cycle
network_template = network_cycle
input_unit_template = inputunit_cycle
output_unit_template = outputunit_cycle
vc_alloc_template = vcalloc_cycle
route_func_template = routefunc_cycle
st_controler_template = stcontroler_cycle
select_gen_template = selectgen_cycle
set_alloc_template = setalloc_cycle
out_en_gen_template = outengen_cycle

def packetgen_cycle(**kw):
    def behavior(ctx):
        pass
    return behavior
packet_gen_template = packetgen_cycle

def packetrec_cycle(**kw):
    def behavior(ctx):
        pass
    return behavior
packet_rec_template = packetrec_cycle

def skeleton_gen(**kwargs):
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
skeleton_template = skeleton_gen
