"""
skills.noc.behaviors — NoC Behavior Templates

Domain-specific behavior templates for mesh-based Network-on-Chip:
  - router_template:        5-port router top-level behavior
  - input_unit_template:    Input processing unit (buffer + route + FSM)
  - output_unit_template:   Output buffer unit
  - vc_alloc_template:      Virtual channel allocator (round-robin)
  - crossbar_template:      5x5 crossbar switch fabric
  - route_func_template:    XY routing function
  - buffer_template:        Input buffer (FIFO)
  - packet_gen_template:    Traffic generator
  - packet_rec_template:    Packet receiver
  - st_controler_template:  Switch traversal control
  - select_gen_template:    Crossbar select decoder
  - set_alloc_template:     Output port allocator
  - out_en_gen_template:    Output enable generation
  - network_template:       Full mesh network behavior

Registered into TemplateRegistry at import time.
"""
from __future__ import annotations

from typing import Any, Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry

# Flit type encoding
FLIT_HEAD = 0b00
FLIT_BODY = 0b01
FLIT_TAIL = 0b10
FLIT_SINGLE = 0b11

# Port mapping
PORT_E = 0
PORT_W = 1
PORT_N = 2
PORT_S = 3
PORT_INJ = 4


# =====================================================================
# Route Function (XY Routing)
# =====================================================================

def route_func_template(**kwargs) -> Callable[[CycleContext], None]:
    """XY routing function behavior.

    Determines valid output port(s) based on current vs destination coordinates.
    If X_cur < X_dest → East (port 0)
    If X_cur > X_dest → West (port 1)
    If X_cur == X_dest:
        If Y_cur < Y_dest → North (port 2)
        If Y_cur > Y_dest → South (port 3)
        If Y_cur == Y_dest → Eject (port 4)
    """
    def behavior(ctx: CycleContext):
        x_cur = ctx.get_input("x_cur", 0)
        y_cur = ctx.get_input("y_cur", 0)
        x_dest = ctx.get_input("x_dest", 0)
        y_dest = ctx.get_input("y_dest", 0)

        valid_out = 0
        if x_cur < x_dest:
            valid_out = 1 << PORT_E
        elif x_cur > x_dest:
            valid_out = 1 << PORT_W
        else:
            if y_cur < y_dest:
                valid_out = 1 << PORT_N
            elif y_cur > y_dest:
                valid_out = 1 << PORT_S
            else:
                valid_out = 1 << PORT_INJ  # Eject (arrived)

        ctx.set_output("valid_out", valid_out)

    return behavior


# =====================================================================
# Buffer (FIFO)
# =====================================================================

def buffer_template(depth: int = 4, flit_width: int = 64) -> Callable[[CycleContext], None]:
    """Input buffer behavior (4-depth FIFO with empty_slots tracking).

    Push: when push_x and buffer not full
    Pop: when state requests pop during switch traversal
    """
    def behavior(ctx: CycleContext):
        push = ctx.get_input("push", 0)
        pop = ctx.get_input("pop", 0)
        push_x = ctx.get_input("push_x", 0)
        wr_data = ctx.get_input("bf_in", 0)

        head = ctx.get_state("head", 0)
        tail = ctx.get_state("tail", 0)
        count = ctx.get_state("count", 0)

        if push_x and count < depth:
            ctx.set_state(f"mem_{tail}", wr_data)
            tail = (tail + 1) % depth
            count = count + 1

        rd_data = 0
        if pop and count > 0:
            rd_data = ctx.get_state(f"mem_{head}", 0)
            head = (head + 1) % depth
            count = count - 1

        empty_slots = depth - count

        ctx.set_output("bf_out", rd_data if pop else ctx.get_state(f"mem_{head}", 0))
        ctx.set_output("em_pl", empty_slots)
        ctx.set_state("head", head)
        ctx.set_state("tail", tail)
        ctx.set_state("count", count)

    return behavior


# =====================================================================
# Input Unit
# =====================================================================

def input_unit_template(
    buffer_depth: int = 4,
    flit_width: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Input unit behavior.

    7-state FSM:
      0: Idle — wait for vc_grant
      1: Wait for ST_ack (handshake)
      2-5: Switch traversal (pop + push flit to crossbar)
      6: Cleanup — release VC (vc_f = 1)

    Flit header parsing:
      [63:62] = flit_type, [11:0] = {dest_Y, dest_X, src_Y, src_X}
    """
    def behavior(ctx: CycleContext):
        vc_grant = ctx.get_input("vc_grant", 0)
        st_ack = ctx.get_input("st_ack", 0)
        pw_fail = ctx.get_input("pw_fail", 0)
        push_x = ctx.get_input("push_x", 0)

        state = ctx.get_state("state", 0)
        pri = ctx.get_state("pri", 0)
        valid_out = ctx.get_state("valid_out", 0)
        status = ctx.get_state("status", 0)
        x_cur = ctx.get_input("x_cur", 0)
        y_cur = ctx.get_input("y_cur", 0)

        # Buffer control
        em_pl = ctx.get_state("em_pl", buffer_depth)
        bf_in = ctx.get_input("bf_in", 0)
        bf_out = ctx.get_state("bf_out", 0)

        # Push logic (from reference RTL)
        push = 0
        push_ack = 0
        if bf_in[63:62] == FLIT_SINGLE and em_pl == buffer_depth:
            push = push_x
            push_ack = push_x
        elif bf_in[63:62] in (FLIT_BODY, FLIT_TAIL):
            push = push_x
            push_ack = push_x

        # Parse flit header for enable logic
        if bf_out[63:62] == FLIT_SINGLE and em_pl < buffer_depth:
            dest_x = (bf_out >> 6) & 0x7
            dest_y = (bf_out >> 9) & 0x7
            ctx.set_output("en", 1)
            pri = pri + 1
        else:
            ctx.set_output("en", 0)

        # FSM
        vc_f = 1  # Default: request VC
        push_o = 0
        pop = 0

        if state == 0:
            if vc_grant:
                state = 1
                vc_f = 0  # Got grant, release request
        elif state == 1:
            if st_ack:
                state = 2
        elif state == 2:
            push_o = 1
            pop = 1
            state = 3
        elif state == 3:
            push_o = 1
            pop = 1
            state = 4
        elif state == 4:
            push_o = 1
            pop = 1
            state = 5
        elif state == 5:
            push_o = 1
            pop = 1
            state = 6
        elif state == 6:
            vc_f = 1  # Release VC
            pop = 0
            push_o = 0
            state = 0

        # Output port selection (simplified from valid_out + PW logic)
        out_num = 5  # Default: no valid output
        pw = 0
        if valid_out == (1 << PORT_E):
            out_num = PORT_E
        elif valid_out == (1 << PORT_W):
            out_num = PORT_W
        elif valid_out == (1 << PORT_N):
            out_num = PORT_N
        elif valid_out == (1 << PORT_S):
            out_num = PORT_S
        elif valid_out == (1 << PORT_INJ):
            out_num = PORT_INJ
        elif valid_out & 0x15:  # Multi-port: E+N or E+S
            pw = 1
            if status & (1 << PORT_E):
                out_num = PORT_E
            elif status & (1 << PORT_N):
                out_num = PORT_N
            elif status & (1 << PORT_S):
                out_num = PORT_S
            else:
                out_num = PORT_E if pri == 0 else PORT_N

        ctx.set_state("state", state)
        ctx.set_state("pri", pri)
        ctx.set_state("valid_out", valid_out)
        ctx.set_state("status", status)
        ctx.set_state("em_pl", em_pl)
        ctx.set_state("bf_out", bf_out)

        ctx.set_output("vc_f", vc_f)
        ctx.set_output("push_o", push_o)
        ctx.set_output("pop", pop)
        ctx.set_output("out_num", out_num)
        ctx.set_output("pw", pw)
        ctx.set_output("push", push)
        ctx.set_output("push_ack", push_ack)
        ctx.set_output("bf_out", bf_out)
        ctx.set_output("em_pl", em_pl)

    return behavior


# =====================================================================
# Output Unit
# =====================================================================

def output_unit_template(
    flit_width: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Output unit behavior.

    Generates write_req based on next router's state and buffer occupancy.
    """
    def behavior(ctx: CycleContext):
        in_flit = ctx.get_input("in_flit", 0)
        next_buf_full = ctx.get_input("next_buf_full", 0)

        write_req = 0
        if in_flit != 0 and not next_buf_full:
            write_req = 1

        ctx.set_output("write_req", write_req)

    return behavior


# =====================================================================
# VC Allocator
# =====================================================================

def vc_alloc_template(
    num_ports: int = 5,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Virtual channel allocator behavior.

    Uses 5 round-robin counters (c_e, c_w, c_n, c_s, c_j),
    cycling through input ports to grant VC access per output port.

    Each output port independently arbitrates among requesting inputs.
    """
    def behavior(ctx: CycleContext):
        # Request signals from each input port
        req_e = ctx.get_input("req_e", 0)
        req_w = ctx.get_input("req_w", 0)
        req_n = ctx.get_input("req_n", 0)
        req_s = ctx.get_input("req_s", 0)
        req_j = ctx.get_input("req_j", 0)

        c_e = ctx.get_state("c_e", 0)
        c_w = ctx.get_state("c_w", 0)
        c_n = ctx.get_state("c_n", 0)
        c_s = ctx.get_state("c_s", 0)
        c_j = ctx.get_state("c_j", 0)

        grant_e = 0
        grant_w = 0
        grant_n = 0
        grant_s = 0
        grant_j = 0

        # Round-robin for East output port
        for ptr, req in [(c_e, req_e), (c_w, req_w), (c_n, req_n), (c_s, req_s), (c_j, req_j)]:
            pass  # Logic below

        # Simplified: each output port grants to the next requesting input
        reqs = [req_e, req_w, req_n, req_s, req_j]
        grants = [0, 0, 0, 0, 0]
        counters = [c_e, c_w, c_n, c_s, c_j]

        active = sum(1 for r in reqs if r)
        if active > 0:
            for out_port in range(num_ports):
                for offset in range(num_ports):
                    inp = (counters[out_port] + offset) % num_ports
                    if reqs[inp]:
                        grants[out_port] = inp
                        counters[out_port] = (inp + 1) % num_ports
                        break

        ctx.set_output("grant_e", 1 if grants[0] else 0)
        ctx.set_output("grant_w", 1 if grants[1] else 0)
        ctx.set_output("grant_n", 1 if grants[2] else 0)
        ctx.set_output("grant_s", 1 if grants[3] else 0)
        ctx.set_output("grant_j", 1 if grants[4] else 0)

        ctx.set_state("c_e", counters[0])
        ctx.set_state("c_w", counters[1])
        ctx.set_state("c_n", counters[2])
        ctx.set_state("c_s", counters[3])
        ctx.set_state("c_j", counters[4])

    return behavior


# =====================================================================
# Crossbar
# =====================================================================

def crossbar_template(
    num_ports: int = 5,
    flit_width: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """5x5 crossbar switch fabric behavior.

    Each output port selects one of 5 inputs based on select signal.
    Select encoding: 0=IE, 1=IW, 2=IN, 3=IS, 4=Inject
    """
    def behavior(ctx: CycleContext):
        ie = ctx.get_input("ie", 0)
        iw = ctx.get_input("iw", 0)
        i_n = ctx.get_input("in", 0)
        i_s = ctx.get_input("is", 0)
        inject = ctx.get_input("inject", 0)

        inputs = [ie, iw, i_n, i_s, inject]

        s_e = ctx.get_input("s_e", 7)
        s_w = ctx.get_input("s_w", 7)
        s_n = ctx.get_input("s_n", 7)
        s_s = ctx.get_input("s_s", 7)
        s_eject = ctx.get_input("s_eject", 7)

        sel_map = {"s_e": s_e, "s_w": s_w, "s_n": s_n, "s_s": s_s, "s_eject": s_eject}

        for name, sel in sel_map.items():
            if sel < num_ports:
                ctx.set_output(name.replace("s_", "o_", 1), inputs[sel])
            else:
                ctx.set_output(name.replace("s_", "o_", 1), 0)

    return behavior


# =====================================================================
# ST Controler
# =====================================================================

def st_controler_template(
    num_ports: int = 5,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Switch traversal controller behavior.

    Generates ST requests based on VC allocation grants and output port selections.
    Generates ack signals based on output enables and select matches.
    """
    def behavior(ctx: CycleContext):
        e_vc_alloc = ctx.get_input("e_vc_alloc", 0)
        w_vc_alloc = ctx.get_input("w_vc_alloc", 0)
        n_vc_alloc = ctx.get_input("n_vc_alloc", 0)
        s_vc_alloc = ctx.get_input("s_vc_alloc", 0)
        inject_vc_alloc = ctx.get_input("inject_vc_alloc", 0)

        e_out = ctx.get_input("e_out", 0)
        w_out = ctx.get_input("w_out", 0)
        n_out = ctx.get_input("n_out", 0)
        s_out = ctx.get_input("s_out", 0)
        inject_out = ctx.get_input("inject_out", 0)

        st_reqs = [0, 0, 0, 0, 0]  # e, w, n, s, eject

        vc_allocs = [e_vc_alloc, w_vc_alloc, n_vc_alloc, s_vc_alloc, inject_vc_alloc]
        outs = [e_out, w_out, n_out, s_out, inject_out]

        for vc_grant, out_port in zip(vc_allocs, outs):
            if vc_grant:
                st_reqs[out_port] = 1

        ctx.set_output("e_st_req", st_reqs[0])
        ctx.set_output("w_st_req", st_reqs[1])
        ctx.set_output("n_st_req", st_reqs[2])
        ctx.set_output("s_st_req", st_reqs[3])
        ctx.set_output("eject_st_req", st_reqs[4])

        # Ack generation
        oe_en = ctx.get_input("oe_en", 0)
        ow_en = ctx.get_input("ow_en", 0)
        on_en = ctx.get_input("on_en", 0)
        os_en = ctx.get_input("os_en", 0)
        eject_en = ctx.get_input("eject_en", 0)

        enables = [(oe_en, 0), (ow_en, 1), (on_en, 2), (os_en, 3), (eject_en, 4)]
        ack_e = 0
        ack_w = 0
        ack_n = 0
        ack_s = 0
        ack_j = 0

        for en, target_out in enables:
            if en:
                if e_out == target_out and e_vc_alloc:
                    ack_e = 1
                elif w_out == target_out and w_vc_alloc:
                    ack_w = 1
                elif n_out == target_out and n_vc_alloc:
                    ack_n = 1
                elif s_out == target_out and s_vc_alloc:
                    ack_s = 1
                elif inject_out == target_out and inject_vc_alloc:
                    ack_j = 1

        ctx.set_output("e_ack", ack_e)
        ctx.set_output("w_ack", ack_w)
        ctx.set_output("n_ack", ack_n)
        ctx.set_output("s_ack", ack_s)
        ctx.set_output("inject_ack", ack_j)

    return behavior


# =====================================================================
# Select Generator
# =====================================================================

def select_gen_template(**kwargs) -> Callable[[CycleContext], None]:
    """Crossbar select signal decoder.

    Decodes VC grant + request into crossbar select signals.
    """
    def behavior(ctx: CycleContext):
        e_g = ctx.get_input("e_g", 0)
        w_g = ctx.get_input("w_g", 0)
        n_g = ctx.get_input("n_g", 0)
        s_g = ctx.get_input("s_g", 0)
        inject_g = ctx.get_input("inject_g", 0)

        e_req = ctx.get_input("e_req", 0)
        w_req = ctx.get_input("w_req", 0)
        n_req = ctx.get_input("n_req", 0)
        s_req = ctx.get_input("s_req", 0)
        inject_req = ctx.get_input("inject_req", 0)

        s_e = 7
        s_w = 7
        s_n = 7
        s_s = 7
        s_eject = 7

        grants = [(e_g, e_req), (w_g, w_req), (n_g, n_req), (s_g, s_req), (inject_g, inject_req)]
        for idx, (grant, req) in enumerate(grants):
            if grant:
                if req == 0: s_e = idx
                elif req == 1: s_w = idx
                elif req == 2: s_n = idx
                elif req == 3: s_s = idx
                elif req == 4: s_eject = idx

        ctx.set_output("s_e", s_e)
        ctx.set_output("s_w", s_w)
        ctx.set_output("s_n", s_n)
        ctx.set_output("s_s", s_s)
        ctx.set_output("s_eject", s_eject)

    return behavior


# =====================================================================
# Set Allocator
# =====================================================================

def set_alloc_template(**kwargs) -> Callable[[CycleContext], None]:
    """Output port allocator.

    Maps VC grants to output port allocation signals.
    """
    def behavior(ctx: CycleContext):
        e_vc_grant = ctx.get_input("e_vc_grant", 0)
        w_vc_grant = ctx.get_input("w_vc_grant", 0)
        n_vc_grant = ctx.get_input("n_vc_grant", 0)
        s_vc_grant = ctx.get_input("s_vc_grant", 0)
        j_vc_grant = ctx.get_input("j_vc_grant", 0)

        e_req = ctx.get_input("e_req", 0)
        w_req = ctx.get_input("w_req", 0)
        n_req = ctx.get_input("n_req", 0)
        s_req = ctx.get_input("s_req", 0)
        j_req = ctx.get_input("j_req", 0)

        alloc_e = 0
        alloc_w = 0
        alloc_n = 0
        alloc_s = 0
        alloc_j = 0

        grants_reqs = [
            (e_vc_grant, e_req),
            (w_vc_grant, w_req),
            (n_vc_grant, n_req),
            (s_vc_grant, s_req),
            (j_vc_grant, j_req),
        ]

        for grant, req in grants_reqs:
            if grant:
                if req == 0: alloc_e = 1
                elif req == 1: alloc_w = 1
                elif req == 2: alloc_n = 1
                elif req == 3: alloc_s = 1
                elif req == 4: alloc_j = 1

        ctx.set_output("alloc_e", alloc_e)
        ctx.set_output("alloc_w", alloc_w)
        ctx.set_output("alloc_n", alloc_n)
        ctx.set_output("alloc_s", alloc_s)
        ctx.set_output("alloc_j", alloc_j)

    return behavior


# =====================================================================
# Output Enable Generator
# =====================================================================

def out_en_gen_template(**kwargs) -> Callable[[CycleContext], None]:
    """Output enable signal generator.

    Maps push_o signals from each input port to output enable flags
    based on crossbar select configuration.
    """
    def behavior(ctx: CycleContext):
        s_e = ctx.get_input("s_e", 7)
        s_w = ctx.get_input("s_w", 7)
        s_n = ctx.get_input("s_n", 7)
        s_s = ctx.get_input("s_s", 7)
        s_eject = ctx.get_input("s_eject", 7)

        e_push = ctx.get_input("e_push_o", 0)
        w_push = ctx.get_input("w_push_o", 0)
        n_push = ctx.get_input("n_push_o", 0)
        s_push = ctx.get_input("s_push_o", 0)
        j_push = ctx.get_input("j_push_o", 0)

        en_e = 0
        en_w = 0
        en_n = 0
        en_s = 0
        en_eject = 0

        pushes = [
            (e_push, 0), (w_push, 1), (n_push, 2), (s_push, 3), (j_push, 4)
        ]

        for push, src_idx in pushes:
            if push:
                if s_e == src_idx: en_e = 1
                if s_w == src_idx: en_w = 1
                if s_n == src_idx: en_n = 1
                if s_s == src_idx: en_s = 1
                if s_eject == src_idx: en_eject = 1

        ctx.set_output("e_en", en_e)
        ctx.set_output("w_en", en_w)
        ctx.set_output("n_en", en_n)
        ctx.set_output("s_en", en_s)
        ctx.set_output("eject_en", en_eject)

    return behavior


# =====================================================================
# Packet Generator
# =====================================================================

def packet_gen_template(
    mesh_size: int = 8,
    payload_len: int = 3,  # HEAD + 2 BODY + TAIL = 4 flits, payload = 2
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Traffic generator behavior.

    FSM:
      0: Init (reset counters)
      1: Inter-packet gap (count to 9 cycles)
      2: Wait for buffer space (j_e == 1)
      3: Send HEAD flit (with random dest != src)
      4: Send BODY flit(s)
      5: Send TAIL flit
      6: Cleanup
      7: Done, back to state 1
    """
    def behavior(ctx: CycleContext):
        j_e = ctx.get_input("j_e", 0)  # Buffer empty space available
        src_x = ctx.get_input("src_x", 0)
        src_y = ctx.get_input("src_y", 0)

        state = ctx.get_state("state", 0)
        count = ctx.get_state("count", 0)
        cnt = ctx.get_state("pkt_cnt", 0)
        flit_idx = ctx.get_state("flit_idx", 0)

        state_transitions = {
            0: 1,
            1: 2 if count >= 9 else 1,
            2: 3 if j_e else 2,
            3: 4,
            4: 5,
            5: 6,
            6: 7,
            7: 1,
        }

        if state == 0:
            count = 0
            cnt = 0
            flit_idx = 0

        write_req = 0
        flit_out = 0

        if state == 1:
            count = count + 1
        elif state == 2:
            pass  # Wait
        elif state == 3:
            # HEAD flit
            write_req = 1
            dest_x = (src_x + 1 + cnt) % mesh_size
            dest_y = (src_y + 1 + cnt // mesh_size) % mesh_size
            if dest_x == src_x and dest_y == src_y:
                dest_x = (dest_x + 1) % mesh_size
            node_id = src_y * mesh_size + src_x
            header = ((dest_y & 0x7) << 9) | ((dest_x & 0x7) << 6) | \
                     ((src_y & 0x7) << 3) | (src_x & 0x7)
            flit_id = ((cnt & 0x3FFFF) << 6) | (node_id & 0x3F)
            flit_out = (FLIT_SINGLE << 62) | flit_id << 12 | header
            flit_idx = 1
        elif state == 4:
            # BODY flit
            write_req = 1
            flit_out = (FLIT_BODY << 62) | (cnt & 0x3FFFF) << 12
            flit_idx = 2
        elif state == 5:
            # TAIL flit
            write_req = 1
            flit_out = (FLIT_TAIL << 62) | (cnt & 0x3FFFF) << 12
            flit_idx = 3
        elif state == 6:
            count = 0
            cnt = cnt + 1
            flit_idx = 0
        elif state == 7:
            count = 0
            flit_idx = 0

        ctx.set_state("state", state_transitions.get(state, 0))
        ctx.set_state("count", count)
        ctx.set_state("pkt_cnt", cnt)
        ctx.set_state("flit_idx", flit_idx)

        ctx.set_output("write_req", write_req)
        ctx.set_output("flit", flit_out)

    return behavior


# =====================================================================
# Packet Receiver
# =====================================================================

def packet_rec_template(**kwargs) -> Callable[[CycleContext], None]:
    """Packet receiver behavior.

    Collects flits from the eject port, reassembles packets.
    """
    def behavior(ctx: CycleContext):
        eject_flit = ctx.get_input("eject_flit", 0)
        eject_valid = ctx.get_input("eject_valid", 0)

        pkt_cnt = ctx.get_state("pkt_cnt", 0)
        flit_cnt = ctx.get_state("flit_cnt", 0)
        received = ctx.get_state("received", 0)

        if eject_valid:
            flit_type = (eject_flit >> 62) & 0x3
            flit_cnt = flit_cnt + 1

            if flit_type == FLIT_SINGLE:
                # Single-flit packet
                pkt_cnt = pkt_cnt + 1
                received = received + 1
                flit_cnt = 0
            elif flit_type == FLIT_TAIL:
                pkt_cnt = pkt_cnt + 1
                received = received + 1
                flit_cnt = 0
            else:
                received = received + 1

        ctx.set_state("pkt_cnt", pkt_cnt)
        ctx.set_state("flit_cnt", flit_cnt)
        ctx.set_state("received", received)

        ctx.set_output("pkt_cnt", pkt_cnt)
        ctx.set_output("received", received)

    return behavior


# =====================================================================
# Router Top-Level
# =====================================================================

def router_template(
    num_ports: int = 5,
    buffer_depth: int = 4,
    flit_width: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """5-port router top-level behavior.

    Orchestrates: InputUnit × 5, OutputUnit × 5, VC_Alloc,
    Select_gen, set_Alloc, ST_Controler, ST, CrossBar, out_en_gen.
    """
    def behavior(ctx: CycleContext):
        # Simplified router behavior: each input port processes flits
        # through the pipeline stages

        for port_idx in range(num_ports):
            port_name = ["e", "w", "n", "s", "j"][port_idx]

            # Input side
            push_x = ctx.get_input(f"{port_name}_push_x", 0)
            bf_in = ctx.get_input(f"{port_name}_bf_in", 0)

            # Track buffer occupancy
            buf_count = ctx.get_state(f"{port_name}_buf_count", 0)
            if push_x and buf_count < buffer_depth:
                buf_count = buf_count + 1
            ctx.set_state(f"{port_name}_buf_count", buf_count)

            em_pl = buffer_depth - buf_count
            ctx.set_output(f"{port_name}_em_pl", em_pl)

            # Output side (simplified)
            if buf_count > 0:
                ctx.set_output(f"{port_name}_push_o", 1)
            else:
                ctx.set_output(f"{port_name}_push_o", 0)

        # Crossbar forwarding (simplified)
        for out_idx in range(num_ports):
            out_name = ["e", "w", "n", "s", "j"][out_idx]
            s_sel = ctx.get_input(f"s_{out_name}", 7)
            if s_sel < num_ports:
                in_name = ["ie", "iw", "in", "is", "inject"][s_sel]
                in_data = ctx.get_input(in_name, 0)
                ctx.set_output(f"o_{out_name}", in_data)

    return behavior


# =====================================================================
# Network (Full Mesh)
# =====================================================================

def network_template(
    mesh_size: int = 8,
    num_ports: int = 5,
    buffer_depth: int = 4,
    flit_width: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Full mesh network behavior.

    Models 8x8 grid of routers with east/west/north/south links.
    Each node has a packet generator and receiver.
    """
    def behavior(ctx: CycleContext):
        cycle = ctx.get_state("cycle", 0)

        # Track network-wide statistics
        total_injected = ctx.get_state("total_injected", 0)
        total_received = ctx.get_state("total_received", 0)

        for y in range(mesh_size):
            for x in range(mesh_size):
                node_id = y * mesh_size + x
                # Per-node injection
                inj_req = ctx.get_input(f"node_{node_id}_inj_req", 0)
                if inj_req:
                    total_injected = total_injected + 1

                # Per-node reception
                ej_valid = ctx.get_input(f"node_{node_id}_ej_valid", 0)
                if ej_valid:
                    total_received = total_received + 1

        ctx.set_state("cycle", cycle + 1)
        ctx.set_state("total_injected", total_injected)
        ctx.set_state("total_received", total_received)

        ctx.set_output("total_injected", total_injected)
        ctx.set_output("total_received", total_received)
        ctx.set_output("avg_latency", total_received > 0 and cycle // max(1, total_received) or 0)

    return behavior


# =====================================================================
# Register NoC Templates
# =====================================================================

TemplateRegistry.register("route_func", route_func_template)
TemplateRegistry.register("buffer", buffer_template)
TemplateRegistry.register("input_unit", input_unit_template)
TemplateRegistry.register("output_unit", output_unit_template)
TemplateRegistry.register("vc_alloc", vc_alloc_template)
TemplateRegistry.register("crossbar", crossbar_template)
TemplateRegistry.register("st_controler", st_controler_template)
TemplateRegistry.register("select_gen", select_gen_template)
TemplateRegistry.register("set_alloc", set_alloc_template)
TemplateRegistry.register("out_en_gen", out_en_gen_template)
TemplateRegistry.register("packet_gen", packet_gen_template)
TemplateRegistry.register("packet_rec", packet_rec_template)
TemplateRegistry.register("router", router_template)
TemplateRegistry.register("network", network_template)

__all__ = [
    "route_func_template",
    "buffer_template",
    "input_unit_template",
    "output_unit_template",
    "vc_alloc_template",
    "crossbar_template",
    "st_controler_template",
    "select_gen_template",
    "set_alloc_template",
    "out_en_gen_template",
    "packet_gen_template",
    "packet_rec_template",
    "router_template",
    "network_template",
]
