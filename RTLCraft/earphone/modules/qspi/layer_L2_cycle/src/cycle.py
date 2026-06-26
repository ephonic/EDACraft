"""L2 CycleIR model for the EarphoneQSPI controller.

Cycle-accurate reference for the memory-mapped XIP read FSM:
cmd → addr → dummy → data, with ~15-cycle first-word latency.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from earphone.modules.qspi.layer_L1_behavior.src.behavior import QSPIFlashFunctional


def qspi_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of QSPI XIP read."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['state'] = 'idle'
            ctx.state['counter'] = 0
            ctx.state['addr'] = 0
            ctx.set_output('rdata', 0)
            ctx.set_output('ready', 0)
            return

        state = ctx.state.get('state', 'idle')
        req = ctx.get_input('req', 0)
        addr = ctx.get_input('addr', 0)
        mem = ctx.state.get('flash', QSPIFlashFunctional())

        ready = 0
        rdata = 0
        next_state = state
        counter = ctx.state.get('counter', 0)

        if state == 'idle':
            if req:
                next_state = 'cmd'
                counter = 2
                ctx.state['addr'] = addr
        elif state == 'cmd':
            if counter > 0:
                counter -= 1
            else:
                next_state = 'addr'
                counter = 2
        elif state == 'addr':
            if counter > 0:
                counter -= 1
            else:
                next_state = 'data'
                counter = 2
        elif state == 'data':
            if counter > 0:
                counter -= 1
            else:
                rdata = mem.xip_read(ctx.state.get('addr', 0))
                ready = 1
                next_state = 'idle'

        ctx.state['state'] = next_state
        ctx.state['counter'] = counter
        ctx.set_output('rdata', rdata)
        ctx.set_output('ready', ready)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneQSPI",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-accurate QSPI XIP read FSM with cmd/addr/data states.",
        "states": ["idle", "cmd", "addr", "data"],
        "first_word_latency_cycles": 9,
    }
