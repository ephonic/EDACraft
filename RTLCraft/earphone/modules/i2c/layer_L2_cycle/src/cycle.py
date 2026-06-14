"""L2 CycleIR model for the EarphoneI2C controller.

Cycle-accurate reference for the APB I2C master byte controller FSM.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext


def i2c_master_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of APB I2C master byte write."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['state'] = 'idle'
            ctx.state['bit_cnt'] = 0
            ctx.set_output('scl_o', 1)
            ctx.set_output('sda_o', 1)
            ctx.set_output('busy', 0)
            ctx.set_output('done', 0)
            return

        state = ctx.state.get('state', 'idle')
        start = ctx.get_input('start', 0)
        addr = ctx.get_input('addr', 0)
        data = ctx.get_input('data', 0)
        rw = ctx.get_input('rw', 0)

        bit_cnt = ctx.state.get('bit_cnt', 0)
        shift_reg = ctx.state.get('shift_reg', 0)
        scl = 1
        sda = 1
        busy = 0
        done = 0
        next_state = state

        if state == 'idle':
            if start:
                next_state = 'start'
                ctx.state['shift_reg'] = ((addr << 1) | rw) << 1
                ctx.state['bit_cnt'] = 9
        elif state == 'start':
            sda = 0
            next_state = 'byte'
            busy = 1
        elif state == 'byte':
            busy = 1
            if bit_cnt > 0:
                sda = (shift_reg >> 8) & 1
                scl = 0
                shift_reg = (shift_reg << 1) & 0x1FF
                bit_cnt -= 1
            else:
                next_state = 'ack'
                bit_cnt = 1
        elif state == 'ack':
            busy = 1
            sda = 1
            scl = 0
            bit_cnt -= 1
            if bit_cnt <= 0:
                if rw == 0:
                    ctx.state['shift_reg'] = (data << 1) | 1
                    ctx.state['bit_cnt'] = 9
                    next_state = 'data'
                else:
                    next_state = 'stop'
        elif state == 'data':
            busy = 1
            if bit_cnt > 0:
                sda = (shift_reg >> 8) & 1
                scl = 0
                shift_reg = (shift_reg << 1) & 0x1FF
                bit_cnt -= 1
            else:
                next_state = 'stop'
        elif state == 'stop':
            busy = 1
            sda = 0
            next_state = 'finish'
        elif state == 'finish':
            done = 1
            next_state = 'idle'

        ctx.state['state'] = next_state
        ctx.state['bit_cnt'] = bit_cnt
        ctx.state['shift_reg'] = shift_reg
        ctx.set_output('scl_o', scl)
        ctx.set_output('sda_o', sda)
        ctx.set_output('busy', busy)
        ctx.set_output('done', done)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneI2C",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-accurate I2C master byte controller FSM.",
        "states": ["idle", "start", "byte", "ack", "data", "stop", "finish"],
    }
