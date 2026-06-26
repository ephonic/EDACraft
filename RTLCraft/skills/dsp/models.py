"""
skills.dsp.models — DSP Golden Reference Models

Cycle-accurate Python simulators for all 12 DSP modules.
Used as golden reference for RTL verification.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


# =====================================================================
# DSP_MULT Model
# =====================================================================

class DSP_MULT_Model:
    """4-stage pipelined signed scalar multiplier."""

    def __init__(self, width: int = 16):
        self.width = width
        self.input_a_reg_0 = 0
        self.input_a_reg_1 = 0
        self.input_b_reg_0 = 0
        self.input_b_reg_1 = 0
        self.output_reg_0 = 0
        self.output_reg_1 = 0

    def step(
        self,
        input_a_tdata: int = 0,
        input_b_tdata: int = 0,
        input_a_tvalid: int = 0,
        input_b_tvalid: int = 0,
        output_tready: int = 0,
    ) -> Tuple[int, int, int, int]:
        input_a_tready = int(input_b_tvalid and output_tready)
        input_b_tready = int(input_a_tvalid and output_tready)
        output_tdata = self._to_signed(self.output_reg_1, self.width * 2)
        output_tvalid = int(input_a_tvalid and input_b_tvalid)

        transfer = int(input_a_tvalid and input_b_tvalid and output_tready)
        if transfer:
            self.input_a_reg_0 = input_a_tdata
            self.input_b_reg_0 = input_b_tdata
            self.input_a_reg_1 = self.input_a_reg_0
            self.input_b_reg_1 = self.input_b_reg_0
            self.output_reg_0 = self._signed_mul(self.input_a_reg_1, self.input_b_reg_1)
            self.output_reg_1 = self.output_reg_0

        return input_a_tready, input_b_tready, output_tdata, output_tvalid

    def _to_signed(self, val: int, width: int) -> int:
        if val & (1 << (width - 1)):
            return val - (1 << width)
        return val

    def _signed_mul(self, a: int, b: int) -> int:
        return self._to_signed(a, self.width) * self._to_signed(b, self.width)


# =====================================================================
# IQ_JOIN Model
# =====================================================================

class IQ_JOIN_Model:
    """Two-channel AXI-Stream synchronizer."""

    def __init__(self, width: int = 16):
        self.width = width
        self.i_data_reg = 0
        self.q_data_reg = 0
        self.i_valid_reg = 0
        self.q_valid_reg = 0

    def step(
        self,
        input_i_tdata: int = 0,
        input_q_tdata: int = 0,
        input_i_tvalid: int = 0,
        input_q_tvalid: int = 0,
        output_tready: int = 0,
    ) -> Tuple[int, int, int, int, int, int]:
        output_tvalid = int(self.i_valid_reg and self.q_valid_reg)
        input_i_tready = int(not self.i_valid_reg or (output_tready and output_tvalid))
        input_q_tready = int(not self.q_valid_reg or (output_tready and output_tvalid))

        if input_i_tready and input_i_tvalid:
            self.i_data_reg = input_i_tdata
            self.i_valid_reg = 1
        elif output_tready and output_tvalid:
            self.i_valid_reg = 0

        if input_q_tready and input_q_tvalid:
            self.q_data_reg = input_q_tdata
            self.q_valid_reg = 1
        elif output_tready and output_tvalid:
            self.q_valid_reg = 0

        return (
            input_i_tready, input_q_tready,
            self.i_data_reg, self.q_data_reg,
            output_tvalid,
        )


# =====================================================================
# IQ_SPLIT Model
# =====================================================================

class IQ_SPLIT_Model:
    """Two-channel AXI-Stream demultiplexer."""

    def __init__(self, width: int = 16):
        self.width = width
        self.i_data_reg = 0
        self.q_data_reg = 0
        self.i_valid_reg = 0
        self.q_valid_reg = 0

    def step(
        self,
        input_i_tdata: int = 0,
        input_q_tdata: int = 0,
        input_tvalid: int = 0,
        output_i_tready: int = 0,
        output_q_tready: int = 0,
    ) -> Tuple[int, int, int, int]:
        i_consume = int(output_i_tready and self.i_valid_reg)
        q_consume = int(output_q_tready and self.q_valid_reg)
        input_tready = int((not self.i_valid_reg or i_consume) and (not self.q_valid_reg or q_consume))

        if input_tready and input_tvalid:
            self.i_data_reg = input_i_tdata
            self.q_data_reg = input_q_tdata
            self.i_valid_reg = 1
            self.q_valid_reg = 1
        else:
            if i_consume:
                self.i_valid_reg = 0
            if q_consume:
                self.q_valid_reg = 0

        return input_tready, self.i_valid_reg, self.q_valid_reg


# =====================================================================
# I2S_CTRL Model
# =====================================================================

class I2S_CTRL_Model:
    """I2S bus clock generator with programmable prescaler."""

    def __init__(self, width: int = 16):
        self.width = width
        self.prescale_cnt = 0
        self.ws_cnt = 0
        self.sck_reg = 0
        self.ws_reg = 0

    def step(self, prescale: int = 0) -> Tuple[int, int]:
        if self.prescale_cnt > 0:
            self.prescale_cnt -= 1
        else:
            self.prescale_cnt = prescale
            if self.sck_reg:
                self.sck_reg = 0
                if self.ws_cnt > 0:
                    self.ws_cnt -= 1
                else:
                    self.ws_cnt = self.width - 1
                    self.ws_reg = 1 - self.ws_reg
            else:
                self.sck_reg = 1

        return self.sck_reg, self.ws_reg


# =====================================================================
# PHASE_ACCUMULATOR Model
# =====================================================================

class PHASE_ACCUMULATOR_Model:
    """NCO phase accumulator with programmable step."""

    def __init__(self, width: int = 32, initial_phase: int = 0, initial_phase_step: int = 0):
        self.width = width
        self.mask = (1 << width) - 1
        self.phase_reg = initial_phase & self.mask
        self.phase_step_reg = initial_phase_step & self.mask

    def step(
        self,
        input_phase_tdata: int = 0,
        input_phase_tvalid: int = 0,
        input_phase_step_tdata: int = 0,
        input_phase_step_tvalid: int = 0,
        output_phase_tready: int = 0,
    ) -> Tuple[int, int, int, int]:
        input_phase_tready = output_phase_tready
        input_phase_step_tready = 1

        if input_phase_tready and input_phase_tvalid:
            self.phase_reg = input_phase_tdata & self.mask
        elif output_phase_tready:
            self.phase_reg = (self.phase_reg + self.phase_step_reg) & self.mask

        if input_phase_step_tvalid:
            self.phase_step_reg = input_phase_step_tdata & self.mask

        return input_phase_tready, input_phase_step_tready, self.phase_reg, 1


# =====================================================================
# DSP_IQ_MULT Model
# =====================================================================

class DSP_IQ_MULT_Model:
    """Complex IQ multiplier, 4-stage pipeline."""

    def __init__(self, width: int = 16):
        self.width = width
        self.a_i_0 = 0
        self.a_q_0 = 0
        self.a_i_1 = 0
        self.a_q_1 = 0
        self.b_i_0 = 0
        self.b_q_0 = 0
        self.b_i_1 = 0
        self.b_q_1 = 0
        self.out_i_0 = 0
        self.out_q_0 = 0
        self.out_i_1 = 0
        self.out_q_1 = 0

    def step(
        self,
        input_a_i: int = 0,
        input_a_q: int = 0,
        input_b_i: int = 0,
        input_b_q: int = 0,
        input_a_tvalid: int = 0,
        input_b_tvalid: int = 0,
        output_tready: int = 0,
    ) -> Tuple[int, int, int, int, int, int]:
        input_a_tready = int(input_b_tvalid and output_tready)
        input_b_tready = int(input_a_tvalid and output_tready)
        output_tvalid = int(input_a_tvalid and input_b_tvalid)

        transfer = int(input_a_tvalid and input_b_tvalid and output_tready)
        if transfer:
            self.a_i_0 = input_a_i
            self.a_q_0 = input_a_q
            self.b_i_0 = input_b_i
            self.b_q_0 = input_b_q
            self.a_i_1 = self.a_i_0
            self.a_q_1 = self.a_q_0
            self.b_i_1 = self.b_i_0
            self.b_q_1 = self.b_q_0
            self.out_i_0 = self._signed_mul(self.a_i_1, self.b_i_1)
            self.out_q_0 = self._signed_mul(self.a_q_1, self.b_q_1)
            self.out_i_1 = self.out_i_0
            self.out_q_1 = self.out_q_0

        out_i = self._to_signed(self.out_i_1, self.width * 2)
        out_q = self._to_signed(self.out_q_1, self.width * 2)

        return input_a_tready, input_b_tready, out_i, out_q, output_tvalid

    def _to_signed(self, val: int, width: int) -> int:
        if val & (1 << (width - 1)):
            return val - (1 << width)
        return val

    def _signed_mul(self, a: int, b: int) -> int:
        return self._to_signed(a, self.width) * self._to_signed(b, self.width)


# =====================================================================
# I2S_RX Model
# =====================================================================

class I2S_RX_Model:
    """I2S serial receiver: edge-detects sck rising edges, shifts in MSB-first."""

    def __init__(self, width: int = 16):
        self.width = width
        self.l_data_reg = 0
        self.r_data_reg = 0
        self.l_data_valid_reg = 0
        self.r_data_valid_reg = 0
        self.sreg = 0
        self.bit_cnt = 0
        self.last_sck = 0
        self.last_ws = 0
        self.last_ws2 = 0

    def step(
        self,
        sck: int = 0,
        ws: int = 0,
        sd: int = 0,
        output_tready: int = 0,
    ) -> Tuple[int, int, int]:
        output_tvalid = int(self.l_data_valid_reg and self.r_data_valid_reg)

        if output_tready and output_tvalid:
            self.l_data_valid_reg = 0
            self.r_data_valid_reg = 0

        sck_rising = (not self.last_sck) and sck
        self.last_sck = sck

        if sck_rising:
            self.last_ws = ws
            self.last_ws2 = self.last_ws

            if self.last_ws2 != ws:
                self.bit_cnt = self.width - 1
                self.sreg = sd
            elif self.bit_cnt > 0:
                self.bit_cnt -= 1
                if self.bit_cnt > 1:
                    self.sreg = ((self.sreg << 1) | sd) & ((1 << self.width) - 1)
                elif self.last_ws2:
                    self.r_data_reg = ((self.sreg << 1) | sd) & ((1 << self.width) - 1)
                    self.r_data_valid_reg = self.l_data_valid_reg
                else:
                    self.l_data_reg = ((self.sreg << 1) | sd) & ((1 << self.width) - 1)
                    self.l_data_valid_reg = 1

        return self.l_data_reg, self.r_data_reg, output_tvalid


# =====================================================================
# I2S_TX Model
# =====================================================================

class I2S_TX_Model:
    """I2S serial transmitter: dual-edge sck, MSB-first shift out."""

    def __init__(self, width: int = 16):
        self.width = width
        self.l_data_reg = 0
        self.r_data_reg = 0
        self.l_data_valid_reg = 0
        self.r_data_valid_reg = 0
        self.sreg = 0
        self.bit_cnt = 0
        self.last_sck = 0
        self.last_ws = 0
        self.sd_reg = 0

    def step(
        self,
        input_l_tdata: int = 0,
        input_r_tdata: int = 0,
        input_tvalid: int = 0,
        sck: int = 0,
        ws: int = 0,
    ) -> Tuple[int, int]:
        input_tready = int(not self.l_data_valid_reg and not self.r_data_valid_reg)

        if input_tready and input_tvalid:
            self.l_data_reg = input_l_tdata
            self.r_data_reg = input_r_tdata
            self.l_data_valid_reg = 1
            self.r_data_valid_reg = 1

        sck_rising = (not self.last_sck) and sck
        self.last_sck = sck

        if sck_rising:
            self.last_ws = ws
            if self.last_ws != ws:
                self.bit_cnt = self.width
                if ws:
                    self.sreg = self.r_data_reg
                    self.r_data_valid_reg = 0
                else:
                    self.sreg = self.l_data_reg
                    self.l_data_valid_reg = 0

        sck_falling = self.last_sck and (not sck)
        if sck_falling and self.bit_cnt > 0:
            self.bit_cnt -= 1
            msb = (self.sreg >> (self.width - 1)) & 1
            self.sd_reg = msb
            self.sreg = (self.sreg << 1) & ((1 << self.width) - 1)

        return input_tready, self.sd_reg


# =====================================================================
# SINE_DDS_LUT Model
# =====================================================================

class SINE_DDS_LUT_Model:
    """Pipelined sine/cosine LUT with fine/coarse angle decomposition."""

    def __init__(self, output_width: int = 16, input_width: Optional[int] = None):
        self.output_width = output_width
        if input_width is None:
            input_width = output_width + 2
        self.input_width = input_width

        W = (input_width - 2) // 2
        coarse_size = 2 ** (W + 1)
        fine_size = 2 ** W
        scale = (2 ** (output_width - 1)) - 1
        pi = 3.1415926535

        self.coarse_c_lut: List[int] = []
        self.coarse_s_lut: List[int] = []
        for i in range(coarse_size):
            cval = int(round(math.cos(2 * pi * i / (2 ** (W + 2))) * scale))
            sval = int(round(math.sin(2 * pi * i / (2 ** (W + 2))) * scale))
            cval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, cval))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            self.coarse_c_lut.append(cval)
            self.coarse_s_lut.append(sval)

        self.fine_s_lut: List[int] = []
        half_fine = 2 ** (W - 1)
        for i in range(fine_size):
            sval = int(round(math.sin(2 * pi * (i - half_fine) / (2 ** input_width)) * scale))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            self.fine_s_lut.append(sval)

        self.W = W
        self.phase_reg = 0
        self.pipeline: List[dict] = [{} for _ in range(5)]

    def step(
        self,
        input_phase_tdata: int = 0,
        input_phase_tvalid: int = 0,
        output_sample_tready: int = 0,
    ) -> Tuple[int, int, int]:
        input_phase_tready = output_sample_tready
        if input_phase_tready and input_phase_tvalid:
            self.phase_reg = input_phase_tdata & ((1 << self.input_width) - 1)

        sign = (self.phase_reg >> (self.input_width - 1)) & 1
        a = (self.phase_reg >> self.W) & ((1 << (self.W + 1)) - 1)
        b = self.phase_reg & ((1 << self.W) - 1) if self.W > 0 else 0

        scale = (2 ** (self.output_width - 1)) - 1

        # Stage 1: LUT read
        cc = self.coarse_c_lut[a]
        cs = self.coarse_s_lut[a]
        fs = self.fine_s_lut[b]

        # Stage 2: pipeline
        cc2 = cc
        cs2 = cs
        fs2 = fs

        # Stage 3: multiply
        cp = cs2 * fs2
        sp = cc2 * fs2

        # Stage 4: add/sub with shift
        shift_amt = self.output_width - 1
        cs_val = cc2 - (cp >> shift_amt)
        ss_val = cs2 + (sp >> shift_amt)

        # Stage 5: sign correction
        if sign:
            sample_i = -cs_val
            sample_q = -ss_val
        else:
            sample_i = cs_val
            sample_q = ss_val

        # Saturate
        sample_i = max(-(2 ** (self.output_width - 1)), min(2 ** (self.output_width - 1) - 1, sample_i))
        sample_q = max(-(2 ** (self.output_width - 1)), min(2 ** (self.output_width - 1) - 1, sample_q))

        return sample_i, sample_q, input_phase_tvalid


# =====================================================================
# SINE_DDS Model
# =====================================================================

class SINE_DDS_Model:
    """Top-level DDS: phase accumulator + sine/cosine LUT."""

    def __init__(
        self,
        phase_width: int = 32,
        output_width: int = 16,
        initial_phase: int = 0,
        initial_phase_step: int = 0,
    ):
        self.phase_accumulator = PHASE_ACCUMULATOR_Model(
            width=phase_width,
            initial_phase=initial_phase,
            initial_phase_step=initial_phase_step,
        )
        lut_input_width = output_width + 2
        self.lut = SINE_DDS_LUT_Model(
            output_width=output_width,
            input_width=lut_input_width,
        )
        self.phase_width = phase_width
        self.lut_input_width = lut_input_width

    def step(
        self,
        input_phase_tdata: int = 0,
        input_phase_tvalid: int = 0,
        input_phase_step_tdata: int = 0,
        input_phase_step_tvalid: int = 0,
        output_sample_tready: int = 0,
    ) -> Tuple[int, int, int, int, int]:
        input_phase_tready, input_phase_step_tready, phase_out, _ = self.phase_accumulator.step(
            input_phase_tdata=input_phase_tdata,
            input_phase_tvalid=input_phase_tvalid,
            input_phase_step_tdata=input_phase_step_tdata,
            input_phase_step_tvalid=input_phase_step_tvalid,
            output_phase_tready=output_sample_tready,
        )

        # Extract top bits for LUT
        lut_phase = (phase_out >> (self.phase_width - self.lut_input_width)) & ((1 << self.lut_input_width) - 1)

        sample_i, sample_q, sample_valid = self.lut.step(
            input_phase_tdata=lut_phase,
            input_phase_tvalid=1,
            output_sample_tready=output_sample_tready,
        )

        return input_phase_tready, input_phase_step_tready, sample_i, sample_q, sample_valid


# =====================================================================
# CIC_DECIMATOR Model
# =====================================================================

class CIC_DECIMATOR_Model:
    """CIC decimator: N integrators → decimator → N combs."""

    def __init__(self, width: int = 16, rmax: int = 2, m: int = 1, n: int = 2):
        self.width = width
        self.rmax = rmax
        self.m = m
        self.n = n
        reg_width = width + ((rmax * m) ** n - 1).bit_length()
        self.reg_width = reg_width
        self.mask = (1 << reg_width) - 1

        self.int_regs = [0] * n
        self.comb_regs = [0] * n
        self.delay_regs = [[0] * m for _ in range(n)]
        self.cycle_reg = 0

    def _to_signed(self, val: int, w: int) -> int:
        if val & (1 << (w - 1)):
            return val - (1 << w)
        return val

    def step(
        self,
        input_tdata: int = 0,
        input_tvalid: int = 0,
        output_tready: int = 0,
        rate: int = 1,
    ) -> Tuple[int, int, int]:
        output_tvalid = int(input_tvalid and self.cycle_reg == 0)
        input_tready = int(output_tready or self.cycle_reg != 0)

        if input_tready and input_tvalid:
            for k in range(self.n):
                if k == 0:
                    new_val = self._to_signed(self.int_regs[k], self.reg_width) + self._to_signed(input_tdata, self.width)
                else:
                    new_val = self._to_signed(self.int_regs[k], self.reg_width) + self._to_signed(self.int_regs[k - 1], self.reg_width)
                self.int_regs[k] = new_val & self.mask

        if output_tready and output_tvalid:
            for k in range(self.n):
                if k == 0:
                    src = self.int_regs[self.n - 1]
                else:
                    src = self.comb_regs[k - 1]
                self.delay_regs[k][0] = src & self.mask
                diff = self._to_signed(src, self.reg_width) - self._to_signed(self.delay_regs[k][self.m - 1], self.reg_width)
                self.comb_regs[k] = diff & self.mask
                for i in range(self.m - 1):
                    self.delay_regs[k][i + 1] = self.delay_regs[k][i] & self.mask

        if input_tready and input_tvalid:
            if self.cycle_reg < (self.rmax - 1) and self.cycle_reg < (rate - 1):
                self.cycle_reg += 1
            else:
                self.cycle_reg = 0

        return input_tready, self.comb_regs[self.n - 1] & self.mask, output_tvalid


# =====================================================================
# CIC_INTERPOLATOR Model
# =====================================================================

class CIC_INTERPOLATOR_Model:
    """CIC interpolator: N combs → up-converter → N integrators."""

    def __init__(self, width: int = 16, rmax: int = 2, m: int = 1, n: int = 2):
        self.width = width
        self.rmax = rmax
        self.m = m
        self.n = n
        gain_bits = ((rmax * m) ** n // rmax - 1).bit_length() if rmax > 0 else 0
        reg_width = width + max(n, gain_bits)
        self.reg_width = reg_width
        self.mask = (1 << reg_width) - 1

        self.comb_regs = [0] * n
        self.int_regs = [0] * n
        self.delay_regs = [[0] * m for _ in range(n)]
        self.cycle_reg = 0

    def _to_signed(self, val: int, w: int) -> int:
        if val & (1 << (w - 1)):
            return val - (1 << w)
        return val

    def step(
        self,
        input_tdata: int = 0,
        input_tvalid: int = 0,
        output_tready: int = 0,
        rate: int = 1,
    ) -> Tuple[int, int, int]:
        input_tready = int(output_tready and self.cycle_reg == 0)
        output_tvalid = int(input_tvalid or self.cycle_reg != 0)

        if input_tready and input_tvalid:
            for k in range(self.n):
                if k == 0:
                    src = input_tdata
                else:
                    src = self.comb_regs[k - 1]
                self.delay_regs[k][0] = src & self.mask
                diff = self._to_signed(src, self.reg_width) - self._to_signed(self.delay_regs[k][self.m - 1], self.reg_width)
                self.comb_regs[k] = diff & self.mask
                for i in range(self.m - 1):
                    self.delay_regs[k][i + 1] = self.delay_regs[k][i] & self.mask

        if output_tready and output_tvalid:
            for k in range(self.n):
                if k == 0:
                    if self.cycle_reg == 0:
                        new_val = self._to_signed(self.int_regs[k], self.reg_width) + self._to_signed(self.comb_regs[self.n - 1], self.reg_width)
                        self.int_regs[k] = new_val & self.mask
                else:
                    new_val = self._to_signed(self.int_regs[k], self.reg_width) + self._to_signed(self.int_regs[k - 1], self.reg_width)
                    self.int_regs[k] = new_val & self.mask

        if output_tready and output_tvalid:
            if self.cycle_reg < (self.rmax - 1) and self.cycle_reg < (rate - 1):
                self.cycle_reg += 1
            else:
                self.cycle_reg = 0

        return input_tready, self.int_regs[self.n - 1] & self.mask, output_tvalid
