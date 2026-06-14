"""L2 CycleIR model for the EarphoneSIMD16 accelerator.

This module provides a cycle-accurate reference model that tracks the INT16
single-cycle path and the 3-stage FP16 MAC pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from earphone.modules.common.utils import _to_u32
from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
    simd16_int16_functional,
    simd16_fp16_mac_functional,
)


def simd16_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of SIMD16: INT16 ops 1 cycle, FP16 MAC 3 cycles."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pipeline'] = []
            ctx.state['busy'] = 0
            ctx.set_output('done', 0)
            ctx.set_output('vdst', 0)
            return

        start = ctx.get_input('start', 0)
        op = ctx.get_input('op', 0)
        mode = ctx.get_input('mode', 0)
        a = ctx.get_input('vsrc0', 0)
        b = ctx.get_input('vsrc1', 0)
        c = ctx.get_input('vsrc2', 0)
        pred = ctx.get_input('pred', 0xFFFF)

        pipe = ctx.state.get('pipeline', [])
        if start:
            latency = 3 if mode == 1 else 1
            pipe.append({'op': op, 'mode': mode, 'a': a, 'b': b, 'c': c, 'pred': pred, 'count': latency})

        done = 0
        result = 0
        # Advance pipeline
        new_pipe = []
        for entry in pipe:
            entry['count'] -= 1
            if entry['count'] <= 0:
                done = 1
                if entry['mode'] == 0:
                    result = simd16_int16_functional(entry['op'], entry['a'], entry['b'], entry['pred'])
                else:
                    result = simd16_fp16_mac_functional(entry['a'], entry['b'], entry['c'], entry['pred'])
            else:
                new_pipe.append(entry)

        ctx.state['pipeline'] = new_pipe
        ctx.set_output('done', done)
        ctx.set_output('vdst', result)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneSIMD16",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-accurate SIMD16 model with 1-cycle INT16 and 3-stage FP16 MAC.",
    }
