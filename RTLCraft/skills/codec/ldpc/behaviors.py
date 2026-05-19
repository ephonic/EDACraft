"""
skills.codec.ldpc.behaviors — LDPC Decoder Behavior Templates

Domain-specific behavior templates for LDPC Min-Sum decoder pipeline stages.
Registered into TemplateRegistry at import time.

Pipeline stages:
  - quantized_adder:  Saturating signed adder (combinational)
  - quantized_subber: Saturating signed subtractor (combinational)
  - comparator:       Min/second-min comparator tree node (combinational)
  - check_node:       Min-Sum check node (sign XOR tree + min finder + registered R)
  - var_node:         Variable node (adder tree for sum_R, P_v = llr+sum_R, Q=P_v-R)
  - ldpc_decoder:     Top-level decoder (iteration counter + parity check + done)
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def quantized_adder_template(
    prec: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Saturating signed adder behavior.

    sum = in1 + in2, with overflow clipping to max positive / max negative.
    Combinational: 0-cycle latency.
    """
    def behavior(ctx: CycleContext):
        in1 = ctx.get_input("in1", 0)
        in2 = ctx.get_input("in2", 0)
        pmax = (1 << (prec - 1)) - 1
        pmin = -(1 << (prec - 1))
        raw_sum = in1 + in2
        # (prec+1)-bit internal: check overflow
        full = raw_sum & ((1 << (prec + 1)) - 1)
        if full >= (1 << prec):
            full -= (1 << (prec + 1))
        if full > pmax:
            full = pmax
        elif full < pmin:
            full = pmin
        # Convert to unsigned representation for output
        ctx.set_output("sum", full & ((1 << prec) - 1))

    return behavior


def quantized_subber_template(
    prec: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Saturating signed subtractor behavior.

    sum = in1 - in2, with overflow clipping.
    Combinational: 0-cycle latency.
    """
    def behavior(ctx: CycleContext):
        in1 = ctx.get_input("in1", 0)
        in2 = ctx.get_input("in2", 0)
        pmax = (1 << (prec - 1)) - 1
        pmin = -(1 << (prec - 1))
        raw_diff = in1 - in2
        full = raw_diff & ((1 << (prec + 1)) - 1)
        if full >= (1 << prec):
            full -= (1 << (prec + 1))
        if full > pmax:
            full = pmax
        elif full < pmin:
            full = pmin
        ctx.set_output("sum", full & ((1 << prec) - 1))

    return behavior


def comparator_template(
    prec: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Min/second-min comparator tree node behavior.

    Given two (min, sec_min) pairs, output overall minimum and second-minimum.
    Combinational: 0-cycle latency.
    """
    def behavior(ctx: CycleContext):
        min1 = ctx.get_input("min1", 0)
        min2 = ctx.get_input("min2", 0)
        sec_min1 = ctx.get_input("sec_min1", 0)
        sec_min2 = ctx.get_input("sec_min2", 0)

        if min2 > min1:
            out_min = min1
            not_min = min2
        else:
            out_min = min2
            not_min = min1

        if sec_min1 <= sec_min2:
            not_max = sec_min1
        else:
            not_max = sec_min2

        if not_min <= not_max:
            out_sec_min = not_min
        else:
            out_sec_min = not_max

        ctx.set_output("min", out_min)
        ctx.set_output("sec_min", out_sec_min)

    return behavior


def check_node_template(
    num_connections: int = 6,
    prec: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Min-Sum check node behavior.

    For each connected variable node i:
      R_i = (sign_product XOR Q_sign_i) ? -min : min
      (if |Q_i| == min, use second_min instead)

    Registered outputs (1-cycle latency).
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        if rst:
            for i in range(num_connections):
                ctx.set_state(f"Rreg_{i}", 0)
            for i in range(num_connections):
                ctx.set_output(f"Rwires_{i}", 0)
            return

        # Read Rreg from state (registered outputs)
        for i in range(num_connections):
            ctx.set_output(f"Rwires_{i}", ctx.get_state(f"Rreg_{i}", 0))

        # Extract Q values from packed input
        qwires = ctx.get_input("Qwires", 0)
        q_vals = []
        for i in range(num_connections):
            raw = (qwires >> (i * prec)) & ((1 << prec) - 1)
            # Sign-extend
            if raw >= (1 << (prec - 1)):
                raw -= (1 << prec)
            q_vals.append(raw)

        # Compute signs and absolute values
        signs = [1 if q < 0 else 0 for q in q_vals]
        abs_q = [abs(q) for q in q_vals]

        # XOR tree for sign_product
        sign_product = sum(signs) & 1

        # Find min and second min
        sorted_abs = sorted((abs_q[i], i) for i in range(num_connections))
        min1 = sorted_abs[0][0]
        min2 = sorted_abs[1][0] if num_connections > 1 else min1

        # Compute new R values
        max_val = (1 << prec) - 1
        new_r = []
        for i in range(num_connections):
            s = sign_product ^ signs[i]
            use_min = min2 if abs_q[i] == min1 else min1
            r_val = -use_min if s else use_min
            # Saturate
            pmax = (1 << (prec - 1)) - 1
            pmin = -(1 << (prec - 1))
            if r_val > pmax:
                r_val = pmax
            elif r_val < pmin:
                r_val = pmin
            new_r.append(r_val & ((1 << prec) - 1))

        # Register update
        for i in range(num_connections):
            ctx.set_state(f"Rreg_{i}", new_r[i])

    return behavior


def var_node_template(
    num_connections: int = 3,
    prec: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Variable node behavior.

    sum_R = saturating sum of all R messages
    P_v   = saturate(sum_R + llr)
    Q_i   = saturate(P_v - R_i)
    x     = sign bit of P_v

    Registered Qwires output (1-cycle latency).
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        if rst:
            ctx.set_state("Qreg", 0)
            return

        # Read Qreg (registered output)
        qreg = ctx.get_state("Qreg", 0)
        for i in range(num_connections):
            val = (qreg >> (i * prec)) & ((1 << prec) - 1)
            ctx.set_output(f"Qwires_{i}", val)

        # Extract R values from packed input
        rwires = ctx.get_input("Rwires", 0)
        r_vals = []
        for i in range(num_connections):
            raw = (rwires >> (i * prec)) & ((1 << prec) - 1)
            if raw >= (1 << (prec - 1)):
                raw -= (1 << prec)
            r_vals.append(raw)

        # Saturating adder tree for sum_R
        pmax = (1 << (prec - 1)) - 1
        pmin = -(1 << (prec - 1))

        def sat(val):
            if val > pmax:
                return pmax
            if val < pmin:
                return pmin
            return val

        # Tree add: pairwise saturating add
        tree = list(r_vals)
        while len(tree) > 1:
            next_tree = []
            for j in range(0, len(tree) - 1, 2):
                next_tree.append(sat(tree[j] + tree[j + 1]))
            if len(tree) % 2 == 1:
                next_tree.append(tree[-1])
            tree = next_tree
        sum_r = tree[0] if tree else 0

        # P_v = sat(sum_R + llr)
        llr = ctx.get_input("llr", 0)
        p_v = sat(sum_r + llr)
        ctx.set_output("P_v", p_v & ((1 << prec) - 1))
        ctx.set_output("x", 1 if p_v < 0 else 0)

        # Q_i = sat(P_v - R_i)
        q_vals = []
        for i in range(num_connections):
            q_i = sat(p_v - r_vals[i])
            q_vals.append(q_i & ((1 << prec) - 1))

        # Pack Q into Qreg
        packed = 0
        for i in range(num_connections - 1, -1, -1):
            packed = (packed << prec) | q_vals[i]
        ctx.set_state("Qreg", packed)

    return behavior


def ldpc_decoder_template(
    n: int = 24,
    m: int = 12,
    prec: int = 4,
    iter_max: int = 25,
    cn_edges: list | None = None,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Top-level LDPC decoder behavior.

    One Min-Sum iteration per clock cycle.
    Terminates when iter_max reached or all parity checks pass.
    """
    if cn_edges is None:
        # Default: dummy edges for z=1 demo
        cn_edges = {c: [c, c + n // m] for c in range(m)}

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 0)
        if rst:
            ctx.set_state("count", 0)
            ctx.set_state("done", 0)
            for v in range(n):
                ctx.set_state(f"P_v_{v}", 0)
                ctx.set_state(f"x_{v}", 0)
            return

        done = ctx.get_state("done", 0)
        count = ctx.get_state("count", 0)

        if done:
            ctx.set_output("done", 1)
            for v in range(n):
                ctx.set_output(f"out_{v}", ctx.get_state(f"P_v_{v}", 0))
                ctx.set_output(f"x_{v}", ctx.get_state(f"x_{v}", 0))
            return

        # Read LLR inputs
        llr = [ctx.get_input(f"llr_{v}", 0) for v in range(n)]

        # Simplified: one iteration of Min-Sum using llr
        # Full behavior would track edge Q/R state
        pmax = (1 << (prec - 1)) - 1
        pmin = -(1 << (prec - 1))

        def sat(val):
            if val > pmax:
                return pmax
            if val < pmin:
                return pmin
            return val

        # Update P_v and x from LLR (simplified — full flow tracks Q/R edges)
        x_vals = []
        for v in range(n):
            pv = sat(llr[v])
            ctx.set_state(f"P_v_{v}", pv)
            xv = 1 if pv < 0 else 0
            ctx.set_state(f"x_{v}", xv)
            x_vals.append(xv)

        # Parity check
        all_zero = True
        for c in range(m):
            parity = 0
            for v in cn_edges.get(c, []):
                parity ^= x_vals[v]
            if parity != 0:
                all_zero = False

        count += 1
        if all_zero or count >= iter_max:
            ctx.set_state("done", 1)
            ctx.set_output("done", 1)
        else:
            ctx.set_state("count", count)

        for v in range(n):
            ctx.set_output(f"out_{v}", ctx.get_state(f"P_v_{v}", 0))
            ctx.set_output(f"x_{v}", ctx.get_state(f"x_{v}", 0))

    return behavior


# Register all templates at import time
TemplateRegistry.register("quantized_adder", quantized_adder_template)
TemplateRegistry.register("quantized_subber", quantized_subber_template)
TemplateRegistry.register("comparator", comparator_template)
TemplateRegistry.register("check_node", check_node_template)
TemplateRegistry.register("var_node", var_node_template)
TemplateRegistry.register("ldpc_decoder", ldpc_decoder_template)
