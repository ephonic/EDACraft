"""
skills.fundamentals.functional — Layer 1: Behavioral models (no timing).

Pure combinatorial models for fundamental hardware building blocks.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple


def adder_functional(**kwargs) -> Callable:
    """Functional ADDER: a + b with optional carry."""
    width = kwargs.get('width', 32)
    def func(a: int = 0, b: int = 0, cin: int = 0) -> Dict:
        result = a + b + cin
        mask = (1 << width) - 1
        return {"sum": result & mask, "cout": (result >> width) & 1}
    return func


def subtractor_functional(**kwargs) -> Callable:
    """Functional SUBTRACTOR: a - b with borrow."""
    width = kwargs.get('width', 32)
    def func(a: int = 0, b: int = 0, bin: int = 0) -> Dict:
        result = a - b - bin
        mask = (1 << width) - 1
        return {"diff": result & mask, "bout": 1 if result < 0 else 0}
    return func


def multiplier_functional(**kwargs) -> Callable:
    """Functional MULTIPLIER: a * b."""
    width = kwargs.get('width', 32)
    def func(a: int = 0, b: int = 0) -> Dict:
        return {"product": (a * b) & ((1 << (width * 2)) - 1)}
    return func


def counter_functional(**kwargs) -> Callable:
    """Functional COUNTER: combinatorial next-count value."""
    width = kwargs.get('width', 8)
    max_val = kwargs.get('max_val', (1 << width) - 1)
    def func(count: int = 0, en: int = 0, load: int = 0,
             load_val: int = 0, rst: int = 0) -> Dict:
        if rst:
            return {"next_count": 0}
        if load:
            return {"next_count": load_val & ((1 << width) - 1)}
        if en:
            next_c = count + 1 if count < max_val else 0
            return {"next_count": next_c}
        return {"next_count": count}
    return func


def register_functional(**kwargs) -> Callable:
    """Functional REGISTER: D flip-flop."""
    width = kwargs.get('width', 32)
    def func(d: int = 0, en: int = 1, rst: int = 0) -> Dict:
        if rst:
            return {"q": 0}
        if en:
            return {"q": d & ((1 << width) - 1)}
        return {"q": 0}
    return func


def mux_functional(**kwargs) -> Callable:
    """Functional MUX: 2^n-to-1 multiplexer."""
    width = kwargs.get('width', 32)
    num_inputs = kwargs.get('num_inputs', 2)
    sel_width = max((num_inputs - 1).bit_length(), 1)
    def func(sel: int = 0, **inputs) -> Dict:
        inp_list = [inputs.get(f'in_{i}', 0) for i in range(num_inputs)]
        idx = sel if sel < num_inputs else 0
        return {"out": inp_list[idx] & ((1 << width) - 1)}
    return func


def decoder_functional(**kwargs) -> Callable:
    """Functional DECODER: n-to-2^n decoder."""
    in_width = kwargs.get('in_width', 3)
    out_width = 1 << in_width
    def func(in_val: int = 0, en: int = 1) -> Dict:
        if not en:
            return {"out": 0}
        if in_val < out_width:
            return {"out": 1 << in_val}
        return {"out": 0}
    return func


def priority_encoder_functional(**kwargs) -> Callable:
    """Functional PRIORITY_ENCODER: encode lowest set bit."""
    in_width = kwargs.get('in_width', 8)
    out_width = max(in_width.bit_length(), 1)
    def func(in_val: int = 0) -> Dict:
        if in_val == 0:
            return {"out": 0, "valid": 0}
        for i in range(in_width):
            if in_val & (1 << i):
                return {"out": i, "valid": 1}
        return {"out": 0, "valid": 0}
    return func


def fifo_functional(**kwargs) -> Callable:
    """Functional FIFO: first-in-first-out queue (combinatorial state read)."""
    width = kwargs.get('width', 32)
    depth = kwargs.get('depth', 16)
    def func(din: int = 0, wr_en: int = 0, rd_en: int = 0,
             count: int = 0) -> Dict:
        full = count >= depth
        empty = count == 0
        return {
            "dout": din,
            "full": int(full),
            "empty": int(empty),
            "count": count,
            "rd_rdy": int(not empty),
        }
    return func


def arbiter_functional(**kwargs) -> Callable:
    """Functional ROUND_ROBIN_ARBITER: round-robin priority arbiter."""
    req_count = kwargs.get('req_count', 8)
    def func(reqs: int = 0, pointer: int = 0) -> Dict:
        if reqs == 0:
            return {"grants": 0, "next_pointer": pointer}
        for i in range(req_count):
            idx = (pointer + i) % req_count
            if reqs & (1 << idx):
                return {"grants": 1 << idx, "next_pointer": (idx + 1) % req_count}
        return {"grants": 0, "next_pointer": pointer}
    return func


def shifter_functional(**kwargs) -> Callable:
    """Functional SHIFTER: barrel shifter."""
    width = kwargs.get('width', 32)
    direction = kwargs.get('direction', 'left')
    def func(data_in: int = 0, shift_amount: int = 0) -> Dict:
        mask = (1 << width) - 1
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
        return {"data_out": result}
    return func


def lfsr_functional(**kwargs) -> Callable:
    """Functional LFSR: linear feedback shift register (next state)."""
    width = kwargs.get('width', 16)
    taps = kwargs.get('taps', [16, 14, 13, 11])
    seed = kwargs.get('seed', 1)
    def func(state: int = 0, enable: int = 0, rst: int = 0) -> Dict:
        if rst:
            return {"next_state": seed & ((1 << width) - 1)}
        if not enable:
            return {"next_state": state}
        fb = state & 1
        next_val = 0
        for b in range(width - 1):
            if b + 1 in taps:
                next_val |= ((state >> (b + 1)) ^ fb) << b
            else:
                next_val |= ((state >> (b + 1)) & 1) << b
        next_val |= (fb << (width - 1))
        return {"next_state": next_val}
    return func


def crc_functional(**kwargs) -> Callable:
    """Functional CRC: parallel CRC computation."""
    data_width = kwargs.get('data_width', 8)
    poly_width = kwargs.get('poly_width', 32)
    polynomial = kwargs.get('polynomial', 0x04C11DB7)
    def func(data: int = 0, crc_in: int = 0) -> Dict:
        crc = crc_in
        for i in range(data_width):
            bit = (data >> (data_width - 1 - i)) & 1
            msb = (crc >> (poly_width - 1)) & 1
            xor = bit ^ msb
            crc = ((crc << 1) ^ (polynomial if xor else 0)) & ((1 << poly_width) - 1)
        return {"crc_out": crc}
    return func


def divider_functional(**kwargs) -> Callable:
    """Functional DIVIDER: unsigned restoring division."""
    dividend_width = kwargs.get('dividend_width', 32)
    divisor_width = kwargs.get('divisor_width', 32)
    def func(dividend: int = 0, divisor: int = 0,
             start: int = 0, busy: int = 0) -> Dict:
        if start and divisor != 0:
            q = dividend // divisor
            r = dividend % divisor
        else:
            q = 0; r = 0
        return {"quotient": q, "remainder": r, "done": int(start and divisor != 0)}
    return func


FUNCTIONAL_MODELS = {
    "adder": adder_functional,
    "subtractor": subtractor_functional,
    "multiplier": multiplier_functional,
    "counter": counter_functional,
    "register": register_functional,
    "mux": mux_functional,
    "decoder": decoder_functional,
    "priority_encoder": priority_encoder_functional,
    "fifo": fifo_functional,
    "arbiter": arbiter_functional,
    "shifter": shifter_functional,
    "lfsr": lfsr_functional,
    "crc": crc_functional,
    "divider": divider_functional,
}
