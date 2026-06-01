"""
skills.fundamentals.cycle_level — Layer 2: Cycle-accurate models.

Register-accurate behavior for fundamental hardware building blocks.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry


def adder_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ADDER: combinatorial a + b."""
    width = kwargs.get('width', 32)
    def behavior(ctx: CycleContext) -> None:
        a = ctx.get_input('a', 0); b = ctx.get_input('b', 0)
        cin = ctx.get_input('cin', 0)
        result = a + b + cin
        mask = (1 << width) - 1
        ctx.set_output('sum', result & mask)
        ctx.set_output('cout', (result >> width) & 1)
    return behavior


def subtractor_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SUBTRACTOR: combinatorial a - b."""
    width = kwargs.get('width', 32)
    def behavior(ctx: CycleContext) -> None:
        a = ctx.get_input('a', 0); b = ctx.get_input('b', 0)
        bin_ = ctx.get_input('bin', 0)
        result = a - b - bin_
        mask = (1 << width) - 1
        ctx.set_output('diff', result & mask)
        ctx.set_output('bout', 1 if result < 0 else 0)
    return behavior


def multiplier_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate MULTIPLIER: combinatorial a * b."""
    width = kwargs.get('width', 32)
    def behavior(ctx: CycleContext) -> None:
        a = ctx.get_input('a', 0); b = ctx.get_input('b', 0)
        ctx.set_output('product', (a * b) & ((1 << (width * 2)) - 1))
    return behavior


def counter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate COUNTER: up-counter with reset/load/enable."""
    width = kwargs.get('width', 8)
    max_val = kwargs.get('max_val', (1 << width) - 1)
    mask = (1 << width) - 1
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['count'] = 0
            ctx.set_output('count', 0)
            return
        en = ctx.get_input('en', 0)
        load = ctx.get_input('load', 0)
        load_val = ctx.get_input('load_val', 0)
        cnt = ctx.state.get('count', 0)
        if load:
            ctx.state['count'] = load_val & mask
        elif en:
            ctx.state['count'] = cnt + 1 if cnt < max_val else 0
        ctx.set_output('count', ctx.state.get('count', 0))
    return behavior


def register_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate REGISTER: D flip-flop with enable."""
    width = kwargs.get('width', 32)
    mask = (1 << width) - 1
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['q'] = 0
            ctx.set_output('q', 0)
            return
        d = ctx.get_input('d', 0)
        en = ctx.get_input('en', 1)
        if en:
            ctx.state['q'] = d & mask
        ctx.set_output('q', ctx.state.get('q', 0))
    return behavior


def mux_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate MUX: combinatorial multiplexer."""
    width = kwargs.get('width', 32)
    num_inputs = kwargs.get('num_inputs', 2)
    def behavior(ctx: CycleContext) -> None:
        sel = ctx.get_input('sel', 0)
        idx = sel if sel < num_inputs else 0
        out_val = ctx.get_input(f'in_{idx}', 0)
        ctx.set_output('out', out_val & ((1 << width) - 1))
    return behavior


def decoder_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate DECODER: combinatorial n-to-2^n."""
    in_width = kwargs.get('in_width', 3)
    out_width = 1 << in_width
    def behavior(ctx: CycleContext) -> None:
        in_val = ctx.get_input('in', 0)
        en = ctx.get_input('en', 1)
        if not en:
            ctx.set_output('out', 0)
        elif in_val < out_width:
            ctx.set_output('out', 1 << in_val)
        else:
            ctx.set_output('out', 0)
    return behavior


def priority_encoder_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate PRIORITY_ENCODER: combinatorial priority encoder."""
    in_width = kwargs.get('in_width', 8)
    def behavior(ctx: CycleContext) -> None:
        in_val = ctx.get_input('in', 0)
        if in_val == 0:
            ctx.set_output('out', 0)
            ctx.set_output('valid', 0)
            return
        for i in range(in_width):
            if in_val & (1 << i):
                ctx.set_output('out', i)
                ctx.set_output('valid', 1)
                return
    return behavior


def fifo_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FIFO: synchronous FIFO."""
    width = kwargs.get('width', 32)
    depth = kwargs.get('depth', 16)
    addr_w = max(depth.bit_length(), 1)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['wr_ptr'] = 0; ctx.state['rd_ptr'] = 0
            ctx.state['count'] = 0
            for i in range(depth):
                ctx.state[f'mem_{i}'] = 0
            ctx.set_output('dout', 0); ctx.set_output('full', 0)
            ctx.set_output('empty', 1); ctx.set_output('count', 0)
            ctx.set_output('rd_rdy', 0)
            return
        din = ctx.get_input('din', 0)
        wr_en = ctx.get_input('wr_en', 0)
        rd_en = ctx.get_input('rd_en', 0)
        cnt = ctx.state.get('count', 0)
        wr = ctx.state.get('wr_ptr', 0)
        rd = ctx.state.get('rd_ptr', 0)

        wr_ok = wr_en and (cnt < depth)
        rd_ok = rd_en and (cnt > 0)

        if wr_ok:
            ctx.state[f'mem_{wr}'] = din
            ctx.state['wr_ptr'] = (wr + 1) % depth
        if rd_ok:
            ctx.state['rd_ptr'] = (rd + 1) % depth

        if wr_ok and not rd_ok:
            ctx.state['count'] = cnt + 1
        elif rd_ok and not wr_ok:
            ctx.state['count'] = cnt - 1

        full = cnt >= depth
        empty = cnt == 0
        ctx.set_output('dout', ctx.state.get(f'mem_{rd}', 0))
        ctx.set_output('full', int(full))
        ctx.set_output('empty', int(empty))
        ctx.set_output('count', cnt)
        ctx.set_output('rd_rdy', int(not empty))
    return behavior


def arbiter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ROUND_ROBIN_ARBITER: round-robin arbiter."""
    req_count = kwargs.get('req_count', 8)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['pointer'] = 0
            ctx.set_output('grants', 0)
            return
        reqs = ctx.get_input('reqs', 0)
        ptr = ctx.state.get('pointer', 0)
        if reqs == 0:
            ctx.state['pointer'] = ptr
            ctx.set_output('grants', 0)
            return
        for i in range(req_count):
            idx = (ptr + i) % req_count
            if reqs & (1 << idx):
                ctx.state['pointer'] = (idx + 1) % req_count
                ctx.set_output('grants', 1 << idx)
                return
        ctx.set_output('grants', 0)
    return behavior


def shifter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SHIFTER: combinatorial barrel shifter."""
    width = kwargs.get('width', 32)
    direction = kwargs.get('direction', 'left')
    mask = (1 << width) - 1
    def behavior(ctx: CycleContext) -> None:
        data_in = ctx.get_input('data_in', 0)
        shift_amount = ctx.get_input('shift_amount', 0)
        amt = shift_amount % width
        if direction == 'left':
            result = (data_in << amt) & mask
        elif direction == 'right':
            result = data_in >> amt
        elif direction == 'left_rotate':
            result = ((data_in << amt) | (data_in >> (width - amt))) & mask
        elif direction == 'right_rotate':
            result = ((data_in >> amt) | (data_in << (width - amt))) & mask
        else:
            result = data_in
        ctx.set_output('data_out', result)
    return behavior


def lfsr_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate LFSR: Galois LFSR."""
    width = kwargs.get('width', 16)
    taps = kwargs.get('taps', [16, 14, 13, 11])
    seed = kwargs.get('seed', 1)
    mask = (1 << width) - 1
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['state'] = seed & mask
            ctx.set_output('out', seed & mask)
            return
        enable = ctx.get_input('enable', 0)
        if not enable:
            ctx.set_output('out', ctx.state.get('state', 0))
            return
        st = ctx.state.get('state', 0)
        fb = st & 1
        next_val = 0
        for b in range(width - 1):
            if b + 1 in taps:
                next_val |= (((st >> (b + 1)) & 1) ^ fb) << b
            else:
                next_val |= ((st >> (b + 1)) & 1) << b
        next_val |= (fb << (width - 1))
        ctx.state['state'] = next_val & mask
        ctx.set_output('out', next_val & mask)
    return behavior


def crc_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CRC: combinatorial parallel CRC."""
    data_width = kwargs.get('data_width', 8)
    poly_width = kwargs.get('poly_width', 32)
    polynomial = kwargs.get('polynomial', 0x04C11DB7)
    def behavior(ctx: CycleContext) -> None:
        data = ctx.get_input('data', 0)
        crc_in = ctx.get_input('crc_in', 0)
        crc = crc_in
        for i in range(data_width):
            bit = (data >> (data_width - 1 - i)) & 1
            msb = (crc >> (poly_width - 1)) & 1
            xor = bit ^ msb
            crc = ((crc << 1) ^ (polynomial if xor else 0)) & ((1 << poly_width) - 1)
        ctx.set_output('crc_out', crc)
    return behavior


def divider_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate DIVIDER: restoring unsigned divider (multi-cycle)."""
    dividend_width = kwargs.get('dividend_width', 32)
    divisor_width = kwargs.get('divisor_width', 32)
    count_w = max(dividend_width.bit_length(), 1)
    IDLE = 0; RUN = 1; DONE = 2
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['state'] = IDLE
            ctx.state['quotient'] = 0
            ctx.state['remainder'] = 0
            ctx.state['count'] = 0
            ctx.set_output('quotient', 0); ctx.set_output('remainder', 0)
            ctx.set_output('done', 0); ctx.set_output('busy', 0)
            return
        state = ctx.state.get('state', IDLE)
        start = ctx.get_input('start', 0)
        dividend = ctx.get_input('dividend', 0)
        divisor = ctx.get_input('divisor', 0)

        if state == IDLE:
            if start:
                ctx.state['state'] = RUN
                ctx.state['quotient'] = dividend
                ctx.state['remainder'] = 0
                ctx.state['count'] = dividend_width
        elif state == RUN:
            cnt = ctx.state.get('count', 0)
            rem = ctx.state.get('remainder', 0)
            quo = ctx.state.get('quotient', 0)
            shifted = (rem << 1) | ((quo >> (dividend_width - 1)) & 1)
            quo = (quo << 1) & ((1 << dividend_width) - 1)
            if shifted >= divisor:
                rem = shifted - divisor
                quo |= 1
            else:
                rem = shifted
            ctx.state['remainder'] = rem
            ctx.state['quotient'] = quo
            ctx.state['count'] = cnt - 1
            if cnt <= 1:
                ctx.state['state'] = DONE
        elif state == DONE:
            if start:
                ctx.state['state'] = RUN
                ctx.state['quotient'] = dividend
                ctx.state['remainder'] = 0
                ctx.state['count'] = dividend_width

        ctx.set_output('quotient', ctx.state.get('quotient', 0))
        ctx.set_output('remainder', ctx.state.get('remainder', 0))
        ctx.set_output('done', 1 if state == DONE else 0)
        ctx.set_output('busy', 1 if state == RUN else 0)
    return behavior


TemplateRegistry.register('adder', adder_cycle)
TemplateRegistry.register('subtractor', subtractor_cycle)
TemplateRegistry.register('multiplier', multiplier_cycle)
TemplateRegistry.register('counter', counter_cycle)
TemplateRegistry.register('register', register_cycle)
TemplateRegistry.register('mux', mux_cycle)
TemplateRegistry.register('decoder', decoder_cycle)
TemplateRegistry.register('priority_encoder', priority_encoder_cycle)
TemplateRegistry.register('fifo', fifo_cycle)
TemplateRegistry.register('arbiter', arbiter_cycle)
TemplateRegistry.register('shifter', shifter_cycle)
TemplateRegistry.register('lfsr', lfsr_cycle)
TemplateRegistry.register('crc', crc_cycle)
TemplateRegistry.register('divider', divider_cycle)
