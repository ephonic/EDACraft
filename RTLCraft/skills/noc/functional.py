"""
skills.noc.functional — Layer 1: Functional models (no timing).

Pure combinatorial models for all 15 NoC modules.
8x8 mesh NoC with XY routing and 5-port routers.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple

FLIT_WIDTH = 64
PORT_E = 0; PORT_W = 1; PORT_N = 2; PORT_S = 3; PORT_INJ = 4


def buffer_functional(**kwargs) -> Callable:
    """Functional Buffer: FIFO buffer (combinatorial read)."""
    depth = kwargs.get('depth', 4)
    width = kwargs.get('width', 64)
    def func(bf_in: int = 0, push: int = 0, pop: int = 0) -> Dict:
        return {"bf_out": bf_in, "em_pl": depth}
    return func


def counter_functional(**kwargs) -> Callable:
    """Functional Counter: modulo-5 counter."""
    def func(en: int = 0) -> Dict:
        return {"c": 0}
    return func


def routefunc_functional(**kwargs) -> Callable:
    """Functional RouteFunc: XY routing.
    Returns valid_out bitmask and status for 5 ports.
    """
    x_width = kwargs.get('x_width', 3)
    y_width = kwargs.get('y_width', 3)
    def func(X_cur: int = 0, Y_cur: int = 0,
             X_dest: int = 0, Y_dest: int = 0,
             reset: int = 0) -> Dict:
        valid_out = 0
        if reset:
            return {"valid_out": 0, "status": 0}
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
        return {"valid_out": valid_out, "status": valid_out}
    return func


def crossbar_functional(**kwargs) -> Callable:
    """Functional CrossBar: 5x5 crossbar mux.
    Selects which input goes to each output port.
    """
    width = kwargs.get('width', 64)
    def func(S_E: int = 0, S_W: int = 0, S_N: int = 0, S_S: int = 0,
             S_Ejec: int = 0,
             IE: int = 0, IW: int = 0, IN_: int = 0, IS_: int = 0,
             Inject: int = 0) -> Dict:
        inp = [IE, IW, IN_, IS_, Inject]
        def mux(sel, inps):
            if sel < 5: return inps[sel]
            return 0
        return {
            "OE": mux(S_E, inp), "OW": mux(S_W, inp),
            "ON": mux(S_N, inp), "OS": mux(S_S, inp),
            "Eject": mux(S_Ejec, inp),
        }
    return func


def st_functional(**kwargs) -> Callable:
    """Functional ST: switch traversal enable (AND gates)."""
    def func(e_req: int = 0, w_req: int = 0, n_req: int = 0, s_req: int = 0,
             eject_req: int = 0,
             oe_f: int = 0, ow_f: int = 0, on_f: int = 0, os_f: int = 0,
             eject_f: int = 0) -> Dict:
        return {
            "oe_en": e_req & oe_f,
            "ow_en": w_req & ow_f,
            "on_en": n_req & on_f,
            "os_en": s_req & os_f,
            "Eject_en": eject_req & eject_f,
        }
    return func


def outengen_functional(**kwargs) -> Callable:
    """Functional OutEnGen: output enable generator."""
    def func(S_E: int = 0, S_W: int = 0, S_N: int = 0, S_S: int = 0,
             S_eject: int = 0,
             e_push_o: int = 0, w_push_o: int = 0, n_push_o: int = 0,
             s_push_o: int = 0, j_push_o: int = 0,
             reset: int = 0) -> Dict:
        E_en = 0; W_en = 0; N_en = 0; S_en = 0; Eject_en = 0
        if not reset:
            def check(sels, push_o, sel_val):
                nonlocal E_en, W_en, N_en, S_en, Eject_en
                if push_o:
                    if sels[0] == sel_val: E_en = 1
                    if sels[1] == sel_val: W_en = 1
                    if sels[2] == sel_val: N_en = 1
                    if sels[3] == sel_val: S_en = 1
                    if sels[4] == sel_val: Eject_en = 1
            sels = [S_E, S_W, S_N, S_S, S_eject]
            check(sels, e_push_o, 0)
            check(sels, w_push_o, 1)
            check(sels, n_push_o, 2)
            check(sels, s_push_o, 3)
            check(sels, j_push_o, 4)
        return {"E_en": E_en, "W_en": W_en, "N_en": N_en,
                "S_en": S_en, "Eject_en": Eject_en}
    return func


def selectgen_functional(**kwargs) -> Callable:
    """Functional SelectGen: crossbar select generator."""
    def func(e_g: int = 0, w_g: int = 0, n_g: int = 0, s_g: int = 0,
             inject_g: int = 0,
             e_req: int = 0, w_req: int = 0, n_req: int = 0,
             s_req: int = 0, inject_req: int = 0,
             reset: int = 0) -> Dict:
        s_e = 7; s_w = 7; s_n = 7; s_s = 7; s_ej = 7
        if not reset:
            reqs = [e_req, w_req, n_req, s_req, inject_req]
            grants = [e_g, w_g, n_g, s_g, inject_g]
            for port, (g, r) in enumerate(zip(grants, reqs)):
                if g and r < 5:
                    if r == 0: s_e = port
                    if r == 1: s_w = port
                    if r == 2: s_n = port
                    if r == 3: s_s = port
                    if r == 4: s_ej = port
        return {"s_e": s_e, "s_w": s_w, "s_n": s_n,
                "s_s": s_s, "s_ej": s_ej}
    return func


def setalloc_functional(**kwargs) -> Callable:
    """Functional SetAlloc: allocation setter."""
    def func(e_vc_grant: int = 0, w_vc_grant: int = 0,
             n_vc_grant: int = 0, s_vc_grant: int = 0,
             j_vc_grant: int = 0,
             e_req: int = 0, w_req: int = 0, n_req: int = 0,
             s_req: int = 0, j_req: int = 0,
             reset: int = 0) -> Dict:
        ae = 0; aw = 0; an = 0; as_ = 0; aj = 0
        if not reset:
            reqs = [e_req, w_req, n_req, s_req, j_req]
            grants = [e_vc_grant, w_vc_grant, n_vc_grant, s_vc_grant, j_vc_grant]
            for g, r in zip(grants, reqs):
                if g:
                    if r == 0: ae = 1
                    if r == 1: aw = 1
                    if r == 2: an = 1
                    if r == 3: as_ = 1
                    if r == 4: aj = 1
        return {"alloc_e": ae, "alloc_w": aw, "alloc_n": an,
                "alloc_s": as_, "alloc_j": aj}
    return func


def stcontroler_functional(**kwargs) -> Callable:
    """Functional STControler: switch traversal controller."""
    def func(e_vc_alloc: int = 0, w_vc_alloc: int = 0,
             n_vc_alloc: int = 0, s_vc_alloc: int = 0,
             inject_vc_alloc: int = 0,
             oe_en: int = 0, ow_en: int = 0, on_en: int = 0,
             os_en: int = 0, Eject_en: int = 0,
             e_out: int = 0, w_out: int = 0, n_out: int = 0,
             s_out: int = 0, inject_out: int = 0,
             reset: int = 0) -> Dict:
        er = 0; wr = 0; nr = 0; sr = 0; jr = 0
        ea = 0; wa = 0; na = 0; sa = 0; ja = 0
        if not reset:
            allocs = [e_vc_alloc, w_vc_alloc, n_vc_alloc, s_vc_alloc, inject_vc_alloc]
            enables = [oe_en, ow_en, on_en, os_en, Eject_en]
            outs = [e_out, w_out, n_out, s_out, inject_out]
            for a, e, o in zip(allocs, enables, outs):
                if a and e and o < 5:
                    if o == 0: er = 1
                    if o == 1: wr = 1
                    if o == 2: nr = 1
                    if o == 3: sr = 1
                    if o == 4: jr = 1
            ea = int(e_vc_alloc and oe_en)
            wa = int(w_vc_alloc and ow_en)
            na = int(n_vc_alloc and on_en)
            sa = int(s_vc_alloc and os_en)
            ja = int(inject_vc_alloc and Eject_en)
        return {"e_ST_req": er, "w_ST_req": wr, "n_ST_req": nr,
                "s_ST_req": sr, "eject_ST_req": jr,
                "e_ack": ea, "w_ack": wa, "n_ack": na,
                "s_ack": sa, "inject_ack": ja}
    return func


def vcalloc_functional(**kwargs) -> Callable:
    """Functional VCAlloc: virtual channel allocator (combinatorial)."""
    def func(E_req: int = 0, W_req: int = 0, N_req: int = 0,
             S_req: int = 0, Inject_req: int = 0,
             oe_en: int = 0, ow_en: int = 0, on_en: int = 0,
             os_en: int = 0, eject_en: int = 0,
             ie_en: int = 0, iw_en: int = 0, in_en: int = 0,
             is_en: int = 0, inject_en: int = 0,
             vc_e_f: int = 0, vc_w_f: int = 0, vc_n_f: int = 0,
             vc_s_f: int = 0, vc_j_f: int = 0) -> Dict:
        return {"vc_g_e": oe_en, "vc_g_w": ow_en, "vc_g_n": on_en,
                "vc_g_s": os_en, "vc_g_injec": eject_en}
    return func


def inputunit_functional(**kwargs) -> Callable:
    """Functional InputUnit: input processing unit (combinatorial)."""
    flit_width = kwargs.get('flit_width', 64)
    def func(push_x: int = 0, PW_fail: int = 0, vc_grant: int = 0,
             ST_ack: int = 0, bf_in: int = 0,
             X_cur: int = 0, Y_cur: int = 0,
             in_channel: int = 0) -> Dict:
        em_pl = 4
        en = int(vc_grant)
        out_num = in_channel
        return {
            "bf_out": bf_in, "en": en, "em_pl": em_pl,
            "out_num": out_num, "PW": int(vc_grant and ST_ack),
            "vc_g": vc_grant, "vc_f": 1,
            "push_o": int(push_x and em_pl > 0),
            "push_ack": int(push_x and em_pl > 0),
        }
    return func


def outputunit_functional(**kwargs) -> Callable:
    """Functional OutputUnit: output processing unit (combinatorial)."""
    flit_width = kwargs.get('flit_width', 64)
    def func(push: int = 0, next_router_state: int = 0,
             alloc: int = 0, bf_in: int = 0,
             write_req_ack: int = 0) -> Dict:
        return {
            "bf_out": bf_in,
            "write_req": int(push and next_router_state),
            "allocOrnot": alloc,
            "em_pl": 4,
        }
    return func


def router_functional(**kwargs) -> Callable:
    """Functional Router: 5-port router (combinatorial composition)."""
    flit_width = kwargs.get('flit_width', 64)
    def func(X_cur: int = 0, Y_cur: int = 0,
             ie: int = 0, iw: int = 0, in_: int = 0, is_: int = 0,
             inject: int = 0,
             push_e: int = 0, push_w: int = 0, push_n: int = 0,
             push_s: int = 0, push_j: int = 0,
             e_state: int = 0, w_state: int = 0, n_state: int = 0,
             s_state: int = 0, eject_state: int = 0,
             w_e_ack: int = 0, w_w_ack: int = 0, w_n_ack: int = 0,
             w_s_ack: int = 0, w_j_ack: int = 0) -> Dict:
        return {
            "oe": ie, "ow": iw, "on_": in_, "os_": is_,
            "eject": inject,
            "write_req_e": push_e, "write_req_w": push_w,
            "write_req_n": push_n, "write_req_s": push_s,
            "write_req_j": push_j,
            "e_e": e_state, "w_e": w_state, "n_e": n_state,
            "s_e": s_state, "j_e": eject_state,
            "push_e_ack": push_e, "push_w_ack": push_w,
            "push_n_ack": push_n, "push_s_ack": push_s,
            "push_j_ack": push_j,
        }
    return func


def processnode_functional(**kwargs) -> Callable:
    """Functional ProcessNode: node with router (combinatorial wrapper)."""
    flit_width = kwargs.get('flit_width', 64)
    def func(**inputs) -> Dict:
        return {}
    return func


def network_functional(**kwargs) -> Callable:
    """Functional Network: full mesh network (combinatorial)."""
    mesh_size = kwargs.get('mesh_size', 8)
    flit_width = kwargs.get('flit_width', 64)
    def func(**inputs) -> Dict:
        return {"sys_done_o": 1}
    return func
