"""
skills.dsp.cycle_level — Layer 2: Cycle-accurate models.

Pipeline timing and register-accurate behavior for each DSP module.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry


def dsp_mult_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate DSP_MULT: 4-stage pipelined signed multiplier."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['a_reg_0'] = 0; ctx.state['a_reg_1'] = 0
            ctx.state['b_reg_0'] = 0; ctx.state['b_reg_1'] = 0
            ctx.state['p_reg_0'] = 0; ctx.state['p_reg_1'] = 0
            ctx.state['v_reg_0'] = 0; ctx.state['v_reg_1'] = 0
            ctx.state['v_reg_2'] = 0; ctx.state['v_reg_3'] = 0
            return
        a_tv = ctx.get_input('input_a_tvalid', 0)
        b_tv = ctx.get_input('input_b_tvalid', 0)
        o_tr = ctx.get_input('output_tready', 0)
        ready = a_tv & b_tv & o_tr

        ctx.state['a_reg_1'] = ctx.state.get('a_reg_0', 0)
        ctx.state['b_reg_1'] = ctx.state.get('b_reg_0', 0)
        ctx.state['p_reg_0'] = ctx.state.get('a_reg_1', 0) * ctx.state.get('b_reg_1', 0)
        ctx.state['p_reg_1'] = ctx.state.get('p_reg_0', 0)
        ctx.state['v_reg_1'] = ctx.state.get('v_reg_0', 0)
        ctx.state['v_reg_2'] = ctx.state.get('v_reg_1', 0)
        ctx.state['v_reg_3'] = ctx.state.get('v_reg_2', 0)

        if ready:
            ctx.state['a_reg_0'] = ctx.get_input('input_a_tdata', 0)
            ctx.state['b_reg_0'] = ctx.get_input('input_b_tdata', 0)
            ctx.state['v_reg_0'] = 1
        else:
            ctx.state['v_reg_0'] = 0

        ctx.set_output('input_a_tready', int(b_tv and o_tr))
        ctx.set_output('input_b_tready', int(a_tv and o_tr))
        ctx.set_output('output_tdata', ctx.state.get('p_reg_1', 0))
        ctx.set_output('output_tvalid', ctx.state.get('v_reg_3', 0))
    return behavior


def iq_join_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IQ_JOIN: two-channel AXI-Stream synchronizer."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['i_data'] = 0; ctx.state['q_data'] = 0
            ctx.state['i_valid'] = 0; ctx.state['q_valid'] = 0
            return
        ii_tv = ctx.get_input('input_i_tvalid', 0)
        iq_tv = ctx.get_input('input_q_tvalid', 0)
        o_tr = ctx.get_input('output_tready', 0)
        o_tv = ctx.state.get('i_valid', 0) & ctx.state.get('q_valid', 0)

        ii_tr = int(not ctx.state.get('i_valid', 0) or (o_tr and o_tv))
        iq_tr = int(not ctx.state.get('q_valid', 0) or (o_tr and o_tv))

        if ii_tr and ii_tv:
            ctx.state['i_data'] = ctx.get_input('input_i_tdata', 0)
            ctx.state['i_valid'] = 1
        elif o_tr and o_tv:
            ctx.state['i_valid'] = 0

        if iq_tr and iq_tv:
            ctx.state['q_data'] = ctx.get_input('input_q_tdata', 0)
            ctx.state['q_valid'] = 1
        elif o_tr and o_tv:
            ctx.state['q_valid'] = 0

        ctx.set_output('input_i_tready', ii_tr)
        ctx.set_output('input_q_tready', iq_tr)
        ctx.set_output('output_i_tdata', ctx.state.get('i_data', 0))
        ctx.set_output('output_q_tdata', ctx.state.get('q_data', 0))
        ctx.set_output('output_tvalid', o_tv)
    return behavior


def iq_split_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IQ_SPLIT: two-channel AXI-Stream demultiplexer."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['i_data'] = 0; ctx.state['q_data'] = 0
            ctx.state['i_valid'] = 0; ctx.state['q_valid'] = 0
            return
        i_tv = ctx.get_input('input_tvalid', 0)
        oi_tr = ctx.get_input('output_i_tready', 0)
        oq_tr = ctx.get_input('output_q_tready', 0)
        i_consume = oi_tr & ctx.state.get('i_valid', 0)
        q_consume = oq_tr & ctx.state.get('q_valid', 0)
        i_tr = int((not ctx.state.get('i_valid', 0) or i_consume) and
                   (not ctx.state.get('q_valid', 0) or q_consume))

        if i_tr and i_tv:
            ctx.state['i_data'] = ctx.get_input('input_i_tdata', 0)
            ctx.state['q_data'] = ctx.get_input('input_q_tdata', 0)
            ctx.state['i_valid'] = 1
            ctx.state['q_valid'] = 1
        else:
            if i_consume: ctx.state['i_valid'] = 0
            if q_consume: ctx.state['q_valid'] = 0

        ctx.set_output('input_tready', i_tr)
        ctx.set_output('output_i_tdata', ctx.state.get('i_data', 0))
        ctx.set_output('output_i_tvalid', ctx.state.get('i_valid', 0))
        ctx.set_output('output_q_tdata', ctx.state.get('q_data', 0))
        ctx.set_output('output_q_tvalid', ctx.state.get('q_valid', 0))
    return behavior


def i2s_ctrl_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate I2S_CTRL: I2S bus clock generator."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['prescale_cnt'] = 0
            ctx.state['ws_cnt'] = 0
            ctx.state['sck'] = 0
            ctx.state['ws'] = 0
            return
        prescale = ctx.get_input('prescale', 256)
        pc = ctx.state.get('prescale_cnt', 0)
        if pc > 0:
            ctx.state['prescale_cnt'] = pc - 1
        else:
            ctx.state['prescale_cnt'] = prescale
            if ctx.state.get('sck', 0):
                ctx.state['sck'] = 0
                wc = ctx.state.get('ws_cnt', 0)
                if wc > 0:
                    ctx.state['ws_cnt'] = wc - 1
                else:
                    ctx.state['ws_cnt'] = width - 1
                    ctx.state['ws'] = 1 - ctx.state.get('ws', 0)
            else:
                ctx.state['sck'] = 1
        ctx.set_output('sck', ctx.state.get('sck', 0))
        ctx.set_output('ws', ctx.state.get('ws', 0))
    return behavior


def phase_accumulator_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate PHASE_ACCUMULATOR: NCO phase accumulator."""
    width = kwargs.get('width', 32)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['phase'] = 0
            ctx.state['step'] = 0
            return
        mask = (1 << width) - 1
        ip_tv = ctx.get_input('input_phase_tvalid', 0)
        ips_tv = ctx.get_input('input_phase_step_tvalid', 0)
        op_tr = ctx.get_input('output_phase_tready', 0)
        ip_tr = op_tr

        if ip_tr and ip_tv:
            ctx.state['phase'] = ctx.get_input('input_phase_tdata', 0) & mask
        elif op_tr:
            phase = ctx.state.get('phase', 0)
            step = ctx.state.get('step', 0)
            ctx.state['phase'] = (phase + step) & mask

        if ips_tv:
            ctx.state['step'] = ctx.get_input('input_phase_step_tdata', 0) & mask

        ctx.set_output('input_phase_tready', ip_tr)
        ctx.set_output('input_phase_step_tready', 1)
        ctx.set_output('output_phase_tdata', ctx.state.get('phase', 0))
        ctx.set_output('output_phase_tvalid', 1)
    return behavior


def dsp_iq_mult_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate DSP_IQ_MULT: complex IQ multiplier, 4-stage pipeline."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for r in ['ai_0','ai_1','aq_0','aq_1','bi_0','bi_1','bq_0','bq_1',
                      'oi_0','oq_0','oi_1','oq_1']:
                ctx.state[r] = 0
            return
        a_tv = ctx.get_input('input_a_tvalid', 0)
        b_tv = ctx.get_input('input_b_tvalid', 0)
        o_tr = ctx.get_input('output_tready', 0)
        ready = a_tv & b_tv & o_tr

        ctx.state['ai_1'] = ctx.state.get('ai_0', 0)
        ctx.state['aq_1'] = ctx.state.get('aq_0', 0)
        ctx.state['bi_1'] = ctx.state.get('bi_0', 0)
        ctx.state['bq_1'] = ctx.state.get('bq_0', 0)
        ctx.state['oi_0'] = ctx.state.get('ai_1', 0) * ctx.state.get('bi_1', 0)
        ctx.state['oq_0'] = ctx.state.get('aq_1', 0) * ctx.state.get('bq_1', 0)
        ctx.state['oi_1'] = ctx.state.get('oi_0', 0)
        ctx.state['oq_1'] = ctx.state.get('oq_0', 0)

        if ready:
            ctx.state['ai_0'] = ctx.get_input('input_a_i_tdata', 0)
            ctx.state['aq_0'] = ctx.get_input('input_a_q_tdata', 0)
            ctx.state['bi_0'] = ctx.get_input('input_b_i_tdata', 0)
            ctx.state['bq_0'] = ctx.get_input('input_b_q_tdata', 0)

        ctx.set_output('input_a_tready', int(b_tv and o_tr))
        ctx.set_output('input_b_tready', int(a_tv and o_tr))
        ctx.set_output('output_i_tdata', ctx.state.get('oi_1', 0))
        ctx.set_output('output_q_tdata', ctx.state.get('oq_1', 0))
        ctx.set_output('output_tvalid', int(a_tv and b_tv))
    return behavior


def i2s_rx_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate I2S_RX: I2S serial receiver with edge detection."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['l_data'] = 0; ctx.state['r_data'] = 0
            ctx.state['l_valid'] = 0; ctx.state['r_valid'] = 0
            ctx.state['sreg'] = 0; ctx.state['bit_cnt'] = 0
            ctx.state['last_sck'] = 0
            ctx.state['last_ws'] = 0; ctx.state['last_ws2'] = 0
            return
        o_tr = ctx.get_input('output_tready', 0)
        o_tv = ctx.state.get('l_valid', 0) & ctx.state.get('r_valid', 0)
        if o_tr and o_tv:
            ctx.state['l_valid'] = 0; ctx.state['r_valid'] = 0

        sck = ctx.get_input('sck', 0)
        ws = ctx.get_input('ws', 0)
        sd = ctx.get_input('sd', 0)
        last_sck = ctx.state.get('last_sck', 0)
        ctx.state['last_sck'] = sck

        if not last_sck and sck:
            last_ws = ctx.state.get('last_ws', 0)
            ctx.state['last_ws'] = ws
            ctx.state['last_ws2'] = last_ws

            if last_ws != ws:
                ctx.state['bit_cnt'] = width - 1
                ctx.state['sreg'] = sd
            else:
                bc = ctx.state.get('bit_cnt', 0)
                if bc > 0:
                    ctx.state['bit_cnt'] = bc - 1
                    sreg = ctx.state.get('sreg', 0)
                    if bc > 1:
                        ctx.state['sreg'] = ((sreg << 1) | sd) & ((1 << width) - 1)
                    elif last_ws:
                        ctx.state['r_data'] = ((sreg << 1) | sd) & ((1 << width) - 1)
                        ctx.state['r_valid'] = ctx.state.get('l_valid', 0)
                    else:
                        ctx.state['l_data'] = ((sreg << 1) | sd) & ((1 << width) - 1)
                        ctx.state['l_valid'] = 1

        ctx.set_output('output_l_tdata', ctx.state.get('l_data', 0))
        ctx.set_output('output_r_tdata', ctx.state.get('r_data', 0))
        ctx.set_output('output_tvalid', o_tv)
    return behavior


def i2s_tx_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate I2S_TX: I2S serial transmitter with dual-edge."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['l_data'] = 0; ctx.state['r_data'] = 0
            ctx.state['l_valid'] = 0; ctx.state['r_valid'] = 0
            ctx.state['sreg'] = 0; ctx.state['bit_cnt'] = 0
            ctx.state['last_sck'] = 0; ctx.state['last_ws'] = 0
            ctx.state['sd'] = 0
            return
        i_tv = ctx.get_input('input_tvalid', 0)
        i_tr = int(not ctx.state.get('l_valid', 0) and not ctx.state.get('r_valid', 0))
        if i_tr and i_tv:
            ctx.state['l_data'] = ctx.get_input('input_l_tdata', 0)
            ctx.state['r_data'] = ctx.get_input('input_r_tdata', 0)
            ctx.state['l_valid'] = 1
            ctx.state['r_valid'] = 1

        sck = ctx.get_input('sck', 0)
        ws = ctx.get_input('ws', 0)
        last_sck = ctx.state.get('last_sck', 0)
        ctx.state['last_sck'] = sck

        if not last_sck and sck:
            last_ws = ctx.state.get('last_ws', 0)
            ctx.state['last_ws'] = ws
            if last_ws != ws:
                ctx.state['bit_cnt'] = width
                if ws:
                    ctx.state['sreg'] = ctx.state.get('r_data', 0)
                    ctx.state['r_valid'] = 0
                else:
                    ctx.state['sreg'] = ctx.state.get('l_data', 0)
                    ctx.state['l_valid'] = 0

        sck_falling = last_sck and not sck
        if sck_falling:
            bc = ctx.state.get('bit_cnt', 0)
            if bc > 0:
                ctx.state['bit_cnt'] = bc - 1
                sreg = ctx.state.get('sreg', 0)
                msb = (sreg >> (width - 1)) & 1
                ctx.state['sd'] = msb
                ctx.state['sreg'] = (sreg << 1) & ((1 << width) - 1)

        ctx.set_output('input_tready', i_tr)
        ctx.set_output('sd', ctx.state.get('sd', 0))
    return behavior


def sine_dds_lut_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SINE_DDS_LUT: 5-stage pipelined sine/cosine LUT."""
    output_width = kwargs.get('output_width', 16)
    input_width = kwargs.get('input_width', output_width + 2)
    W = (input_width - 2) // 2
    coarse_size = 1 << (W + 1)
    fine_size = 1 << W
    scale = (1 << (output_width - 1)) - 1
    pi = 3.1415926535

    coarse_c = []
    coarse_s = []
    for i in range(coarse_size):
        a = 2 * pi * i / (1 << (W + 2))
        coarse_c.append(int(round(math.cos(a) * scale)))
        coarse_s.append(int(round(math.sin(a) * scale)))
    fine_s = []
    half_fine = 1 << (W - 1)
    for i in range(fine_size):
        a = 2 * pi * (i - half_fine) / (1 << input_width)
        fine_s.append(int(round(math.sin(a) * scale)))

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for r in ['phase','sign_1','sign_2','sign_3','sign_4',
                      'ccs_1','ccs_2','ccs_3','css_1','css_2','css_3',
                      'fss_1','fss_2','cp_1','sp_1','cs_1','ss_1',
                      'si','sq']:
                ctx.state[r] = 0
            return
        ip_tv = ctx.get_input('input_phase_tvalid', 0)
        os_tr = ctx.get_input('output_sample_tready', 0)
        ip_tr = os_tr

        if ip_tr and ip_tv:
            ctx.state['phase'] = ctx.get_input('input_phase_tdata', 0)

        phase = ctx.state.get('phase', 0)
        sign = (phase >> (input_width - 1)) & 1
        a_idx = (phase >> W) & ((1 << (W + 1)) - 1) if W >= 0 else 0
        b_idx = phase & ((1 << W) - 1) if W > 0 else 0

        if ip_tr and ip_tv:
            ctx.state['sign_1'] = sign
            ctx.state['ccs_1'] = coarse_c[a_idx] if a_idx < coarse_size else 0
            ctx.state['css_1'] = coarse_s[a_idx] if a_idx < coarse_size else 0
            ctx.state['fss_1'] = fine_s[b_idx] if b_idx < fine_size else 0

        ctx.state['sign_2'] = ctx.state.get('sign_1', 0)
        ctx.state['ccs_2'] = ctx.state.get('ccs_1', 0)
        ctx.state['css_2'] = ctx.state.get('css_1', 0)
        ctx.state['fss_2'] = ctx.state.get('fss_1', 0)

        ctx.state['sign_3'] = ctx.state.get('sign_2', 0)
        ctx.state['ccs_3'] = ctx.state.get('ccs_2', 0)
        ctx.state['css_3'] = ctx.state.get('css_2', 0)
        ctx.state['cp_1'] = ctx.state.get('css_2', 0) * ctx.state.get('fss_2', 0)
        ctx.state['sp_1'] = ctx.state.get('ccs_2', 0) * ctx.state.get('fss_2', 0)

        ctx.state['sign_4'] = ctx.state.get('sign_3', 0)
        shift = output_width - 1
        ctx.state['cs_1'] = ctx.state.get('ccs_3', 0) - (ctx.state.get('cp_1', 0) >> shift)
        ctx.state['ss_1'] = ctx.state.get('css_3', 0) + (ctx.state.get('sp_1', 0) >> shift)

        if ctx.state.get('sign_4', 0):
            ctx.state['si'] = -ctx.state.get('cs_1', 0)
            ctx.state['sq'] = -ctx.state.get('ss_1', 0)
        else:
            ctx.state['si'] = ctx.state.get('cs_1', 0)
            ctx.state['sq'] = ctx.state.get('ss_1', 0)

        ctx.set_output('input_phase_tready', ip_tr)
        ctx.set_output('output_sample_i_tdata', ctx.state.get('si', 0))
        ctx.set_output('output_sample_q_tdata', ctx.state.get('sq', 0))
        ctx.set_output('output_sample_tvalid', ip_tv)
    return behavior


def sine_dds_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SINE_DDS: top-level DDS (phase accumulator + LUT pipeline)."""
    phase_width = kwargs.get('phase_width', 32)
    output_width = kwargs.get('output_width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['phase'] = 0; ctx.state['step'] = 0
            for r in ['sign_1','sign_2','sign_3','sign_4',
                      'ccs_1','ccs_2','ccs_3','css_1','css_2','css_3',
                      'fss_1','fss_2','cp_1','sp_1','cs_1','ss_1','si','sq']:
                ctx.state[r] = 0
            return
        mask = (1 << phase_width) - 1
        ip_tv = ctx.get_input('input_phase_tvalid', 0)
        ips_tv = ctx.get_input('input_phase_step_tvalid', 0)
        os_tr = ctx.get_input('output_sample_tready', 0)
        ip_tr = os_tr

        if ip_tr and ip_tv:
            ctx.state['phase'] = ctx.get_input('input_phase_tdata', 0) & mask
        elif os_tr:
            p = ctx.state.get('phase', 0); s = ctx.state.get('step', 0)
            ctx.state['phase'] = (p + s) & mask
        if ips_tv:
            ctx.state['step'] = ctx.get_input('input_phase_step_tdata', 0) & mask

        phase = ctx.state.get('phase', 0)
        lut_input_width = output_width + 2
        lut_phase = (phase >> (phase_width - lut_input_width)) & ((1 << lut_input_width) - 1)

        W = (lut_input_width - 2) // 2
        scale = (1 << (output_width - 1)) - 1
        pi = 3.1415926535
        coarse_size = 1 << (W + 1)
        fine_size = 1 << W
        a_idx = (lut_phase >> W) & ((1 << (W + 1)) - 1) if W >= 0 else 0
        b_idx = lut_phase & ((1 << W) - 1) if W > 0 else 0

        if ip_tr and ip_tv:
            sign = (lut_phase >> (lut_input_width - 1)) & 1
            ctx.state['sign_1'] = sign
            ctx.state['ccs_1'] = int(round(math.cos(2 * pi * a_idx / (1 << (W + 2))) * scale))
            ctx.state['css_1'] = int(round(math.sin(2 * pi * a_idx / (1 << (W + 2))) * scale))
            ctx.state['fss_1'] = int(round(math.sin(2 * pi * (b_idx - (1 << (W - 1))) / (1 << lut_input_width)) * scale))

        ctx.state['sign_2'] = ctx.state.get('sign_1', 0)
        ctx.state['ccs_2'] = ctx.state.get('ccs_1', 0)
        ctx.state['css_2'] = ctx.state.get('css_1', 0)
        ctx.state['fss_2'] = ctx.state.get('fss_1', 0)

        ctx.state['sign_3'] = ctx.state.get('sign_2', 0)
        ctx.state['ccs_3'] = ctx.state.get('ccs_2', 0)
        ctx.state['css_3'] = ctx.state.get('css_2', 0)
        ctx.state['cp_1'] = ctx.state.get('css_2', 0) * ctx.state.get('fss_2', 0)
        ctx.state['sp_1'] = ctx.state.get('ccs_2', 0) * ctx.state.get('fss_2', 0)

        ctx.state['sign_4'] = ctx.state.get('sign_3', 0)
        shift = output_width - 1
        ctx.state['cs_1'] = ctx.state.get('ccs_3', 0) - (ctx.state.get('cp_1', 0) >> shift)
        ctx.state['ss_1'] = ctx.state.get('css_3', 0) + (ctx.state.get('sp_1', 0) >> shift)

        if ctx.state.get('sign_4', 0):
            ctx.state['si'] = -ctx.state.get('cs_1', 0)
            ctx.state['sq'] = -ctx.state.get('ss_1', 0)
        else:
            ctx.state['si'] = ctx.state.get('cs_1', 0)
            ctx.state['sq'] = ctx.state.get('ss_1', 0)

        ctx.set_output('input_phase_tready', ip_tr)
        ctx.set_output('input_phase_step_tready', 1)
        ctx.set_output('output_sample_i_tdata', ctx.state.get('si', 0))
        ctx.set_output('output_sample_q_tdata', ctx.state.get('sq', 0))
        ctx.set_output('output_sample_tvalid', ip_tv)
    return behavior


def cic_decimator_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CIC_DECIMATOR: N integrator + decimate + N comb."""
    width = kwargs.get('width', 16)
    rmax = kwargs.get('rmax', 2)
    m = kwargs.get('m', 1)
    n = kwargs.get('n', 2)
    reg_width = width + ((rmax * m) ** n - 1).bit_length()
    mask = (1 << reg_width) - 1

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for k in range(n):
                ctx.state[f'int_{k}'] = 0
                ctx.state[f'comb_{k}'] = 0
                for i in range(m):
                    ctx.state[f'delay_{k}_{i}'] = 0
            ctx.state['cycle'] = 0
            return
        i_tv = ctx.get_input('input_tvalid', 0)
        o_tr = ctx.get_input('output_tready', 0)
        rate = ctx.get_input('rate', 1)
        cycle = ctx.state.get('cycle', 0)
        o_tv = i_tv & (cycle == 0)
        i_tr = o_tr | (cycle != 0)

        def to_s(v): return v if v < (1 << (reg_width - 1)) else v - (1 << reg_width)
        if i_tr and i_tv:
            inp = ctx.get_input('input_tdata', 0)
            for k in range(n):
                if k == 0:
                    nv = to_s(ctx.state.get(f'int_{k}', 0)) + to_s(inp)
                else:
                    nv = to_s(ctx.state.get(f'int_{k}', 0)) + to_s(ctx.state.get(f'int_{k-1}', 0))
                ctx.state[f'int_{k}'] = nv & mask

        if o_tr and o_tv:
            for k in range(n):
                src = ctx.state.get(f'int_{n-1}', 0) if k == 0 else ctx.state.get(f'comb_{k-1}', 0)
                ctx.state[f'delay_{k}_0'] = src & mask
                diff = to_s(src) - to_s(ctx.state.get(f'delay_{k}_{m-1}', 0))
                ctx.state[f'comb_{k}'] = diff & mask
                for i in range(m - 1):
                    ctx.state[f'delay_{k}_{i+1}'] = ctx.state.get(f'delay_{k}_{i}', 0)

        if i_tr and i_tv:
            if cycle < (rmax - 1) and cycle < (rate - 1):
                ctx.state['cycle'] = cycle + 1
            else:
                ctx.state['cycle'] = 0

        ctx.set_output('input_tready', i_tr)
        ctx.set_output('output_tdata', ctx.state.get(f'comb_{n-1}', 0))
        ctx.set_output('output_tvalid', o_tv)
    return behavior


def cic_interpolator_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CIC_INTERPOLATOR: N comb + up-convert + N integrator."""
    width = kwargs.get('width', 16)
    rmax = kwargs.get('rmax', 2)
    m = kwargs.get('m', 1)
    n = kwargs.get('n', 2)
    gain_bits = ((rmax * m) ** n // rmax - 1).bit_length() if rmax > 0 else 0
    reg_width = width + max(n, gain_bits)
    mask = (1 << reg_width) - 1

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for k in range(n):
                ctx.state[f'comb_{k}'] = 0
                ctx.state[f'int_{k}'] = 0
                for i in range(m):
                    ctx.state[f'delay_{k}_{i}'] = 0
            ctx.state['cycle'] = 0
            return
        i_tv = ctx.get_input('input_tvalid', 0)
        o_tr = ctx.get_input('output_tready', 0)
        rate = ctx.get_input('rate', 1)
        cycle = ctx.state.get('cycle', 0)
        i_tr = o_tr & (cycle == 0)
        o_tv = i_tv | (cycle != 0)

        def to_s(v): return v if v < (1 << (reg_width - 1)) else v - (1 << reg_width)
        if i_tr and i_tv:
            inp = ctx.get_input('input_tdata', 0)
            for k in range(n):
                src = inp if k == 0 else ctx.state.get(f'comb_{k-1}', 0)
                ctx.state[f'delay_{k}_0'] = src & mask
                diff = to_s(src) - to_s(ctx.state.get(f'delay_{k}_{m-1}', 0))
                ctx.state[f'comb_{k}'] = diff & mask
                for i in range(m - 1):
                    ctx.state[f'delay_{k}_{i+1}'] = ctx.state.get(f'delay_{k}_{i}', 0)

        if o_tr and o_tv:
            for k in range(n):
                if k == 0 and cycle == 0:
                    nv = to_s(ctx.state.get(f'int_{k}', 0)) + to_s(ctx.state.get(f'comb_{n-1}', 0))
                else:
                    nv = to_s(ctx.state.get(f'int_{k}', 0)) + to_s(ctx.state.get(f'int_{k-1}', 0))
                ctx.state[f'int_{k}'] = nv & mask

        if o_tr and o_tv:
            if cycle < (rmax - 1) and cycle < (rate - 1):
                ctx.state['cycle'] = cycle + 1
            else:
                ctx.state['cycle'] = 0

        ctx.set_output('input_tready', i_tr)
        ctx.set_output('output_tdata', ctx.state.get(f'int_{n-1}', 0))
        ctx.set_output('output_tvalid', o_tv)
    return behavior


TemplateRegistry.register('dsp_mult', dsp_mult_cycle)
TemplateRegistry.register('iq_join', iq_join_cycle)
TemplateRegistry.register('iq_split', iq_split_cycle)
TemplateRegistry.register('i2s_ctrl', i2s_ctrl_cycle)
TemplateRegistry.register('phase_accumulator', phase_accumulator_cycle)
TemplateRegistry.register('dsp_iq_mult', dsp_iq_mult_cycle)
TemplateRegistry.register('i2s_rx', i2s_rx_cycle)
TemplateRegistry.register('i2s_tx', i2s_tx_cycle)
TemplateRegistry.register('sine_dds_lut', sine_dds_lut_cycle)
TemplateRegistry.register('sine_dds', sine_dds_cycle)
TemplateRegistry.register('cic_decimator', cic_decimator_cycle)
TemplateRegistry.register('cic_interpolator', cic_interpolator_cycle)

dsp_mult_template = dsp_mult_cycle
iq_join_template = iq_join_cycle
iq_split_template = iq_split_cycle
i2s_ctrl_template = i2s_ctrl_cycle
phase_accumulator_template = phase_accumulator_cycle
dsp_iq_mult_template = dsp_iq_mult_cycle
i2s_rx_template = i2s_rx_cycle
i2s_tx_template = i2s_tx_cycle
sine_dds_lut_template = sine_dds_lut_cycle
sine_dds_template = sine_dds_cycle
cic_decimator_template = cic_decimator_cycle
cic_interpolator_template = cic_interpolator_cycle

import math
