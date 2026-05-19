# =====================================================================
# design_fft.py — Professional FFT Accelerator (Radix-2^2 SDF Pipeline)
# =====================================================================
# Based on r22sdf reference model (ref_rtl/fft/)
# Architecture: Radix-2^2 Single-Path Delay Feedback (R2^2SDF)
# Features:
#   - Parameterizable FFT size (64/128/1024/...)
#   - Parameterizable data width (default 16-bit signed Q1.15)
#   - Scaled fixed-point arithmetic (1/N scaling per butterfly stage)
#   - Bit-reversed output order
#   - Streaming input/output (1 sample/cycle)
# =====================================================================

import math
import os
from rtlgen.core import Module, Input, Output, Reg, Wire, Memory, Parameter, LocalParam, SubmoduleInst
from rtlgen.logic import If, Else, Elif, Switch, Cat, Const, Mux, SRA, comment

# -------------------------------------------------------------------------
# Helper: generate twiddle factor hex tables
# -------------------------------------------------------------------------
def generate_twiddle_hex(N, width=16, out_dir="generated/fft"):
    """Generate twiddle factor ROM hex files for W_N^k = cos(-2πk/N) + j·sin(-2πk/N).
    Returns (re_path, im_path).
    """
    os.makedirs(out_dir, exist_ok=True)
    re_path = os.path.join(out_dir, f"twiddle_{N}_re.hex")
    im_path = os.path.join(out_dir, f"twiddle_{N}_im.hex")
    max_val = (1 << (width - 1)) - 1
    min_val = -(1 << (width - 1))
    with open(re_path, "w") as fre, open(im_path, "w") as fim:
        for k in range(N):
            ang = -2.0 * math.pi * k / N
            re_f = math.cos(ang)
            im_f = math.sin(ang)
            re_q = int(round(re_f * (1 << (width - 1))))
            im_q = int(round(im_f * (1 << (width - 1))))
            re_q = max(min_val, min(max_val, re_q))
            im_q = max(min_val, min(max_val, im_q))
            fre.write(f"{re_q & ((1 << width) - 1):04x}\n")
            fim.write(f"{im_q & ((1 << width) - 1):04x}\n")
    return re_path, im_path


def log2_int(x):
    """Return ceil(log2(x)), i.e. bit width needed to represent x-1."""
    return max(x - 1, 0).bit_length()


# =====================================================================
# FFTButterfly — Complex radix-2 butterfly with scaling
# =====================================================================
class FFTButterfly(Module):
    def __init__(self, width=16, rh=0, name="FFTButterfly"):
        super().__init__(name)
        self.x0_re = Input(width, "x0_re", signed=True)
        self.x0_im = Input(width, "x0_im", signed=True)
        self.x1_re = Input(width, "x1_re", signed=True)
        self.x1_im = Input(width, "x1_im", signed=True)

        self.y0_re = Output(width, "y0_re", signed=True)
        self.y0_im = Output(width, "y0_im", signed=True)
        self.y1_re = Output(width, "y1_re", signed=True)
        self.y1_im = Output(width, "y1_im", signed=True)

        # Internal add/sub are width+1 bits to avoid overflow
        self._add_re = Wire(width + 1, "_add_re", signed=True)
        self._add_im = Wire(width + 1, "_add_im", signed=True)
        self._sub_re = Wire(width + 1, "_sub_re", signed=True)
        self._sub_im = Wire(width + 1, "_sub_im", signed=True)

        @self.comb
        def _bf():
            self._add_re <<= self.x0_re + self.x1_re
            self._add_im <<= self.x0_im + self.x1_im
            self._sub_re <<= self.x0_re - self.x1_re
            self._sub_im <<= self.x0_im - self.x1_im

            # Scaling: (sum + RH) >>> 1  —  arithmetic right shift preserves sign
            self.y0_re <<= SRA(self._add_re + rh, 1)
            self.y0_im <<= SRA(self._add_im + rh, 1)
            self.y1_re <<= SRA(self._sub_re + rh, 1)
            self.y1_im <<= SRA(self._sub_im + rh, 1)


# =====================================================================
# FFTDelayBuffer — Shift-register delay line (matches reference)
# =====================================================================
class FFTDelayBuffer(Module):
    def __init__(self, depth=32, width=16, name="FFTDelayBuffer"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")  # active-high async reset

        self.di_re = Input(width, "di_re", signed=True)
        self.di_im = Input(width, "di_im", signed=True)
        self.do_re = Output(width, "do_re", signed=True)
        self.do_im = Output(width, "do_im", signed=True)

        # Shift-register chain matching reference DelayBuffer.v
        self.buf_re = [Reg(width, f"buf_re_{i}", signed=True) for i in range(depth)]
        self.buf_im = [Reg(width, f"buf_im_{i}", signed=True) for i in range(depth)]

        @self.comb
        def _out():
            if depth > 0:
                self.do_re <<= self.buf_re[depth - 1]
                self.do_im <<= self.buf_im[depth - 1]
            else:
                self.do_re <<= self.di_re
                self.do_im <<= self.di_im

        @self.seq(self.clk, self.rst, reset_async=True)
        def _seq():
            with If(self.rst == 1):
                for i in range(depth):
                    self.buf_re[i] <<= 0
                    self.buf_im[i] <<= 0
            with Else():
                for i in range(depth - 1, 0, -1):
                    self.buf_re[i] <<= self.buf_re[i - 1]
                    self.buf_im[i] <<= self.buf_im[i - 1]
                if depth > 0:
                    self.buf_re[0] <<= self.di_re
                    self.buf_im[0] <<= self.di_im


# =====================================================================
# FFTMultiply — Complex multiplier (4 real multiplies)
# =====================================================================
class FFTMultiply(Module):
    def __init__(self, width=16, name="FFTMultiply"):
        super().__init__(name)
        self.a_re = Input(width, "a_re", signed=True)
        self.a_im = Input(width, "a_im", signed=True)
        self.b_re = Input(width, "b_re", signed=True)
        self.b_im = Input(width, "b_im", signed=True)

        self.m_re = Output(width, "m_re", signed=True)
        self.m_im = Output(width, "m_im", signed=True)

        # 4 real multiplications, each 2*width bits
        self._arbr = Wire(width * 2, "_arbr", signed=True)
        self._arbi = Wire(width * 2, "_arbi", signed=True)
        self._aibr = Wire(width * 2, "_aibr", signed=True)
        self._aibi = Wire(width * 2, "_aibi", signed=True)

        # Scaled back to width bits
        self._sc_arbr = Wire(width, "_sc_arbr", signed=True)
        self._sc_arbi = Wire(width, "_sc_arbi", signed=True)
        self._sc_aibr = Wire(width, "_sc_aibr", signed=True)
        self._sc_aibi = Wire(width, "_sc_aibi", signed=True)

        @self.comb
        def _mul():
            self._arbr <<= self.a_re * self.b_re
            self._arbi <<= self.a_re * self.b_im
            self._aibr <<= self.a_im * self.b_re
            self._aibi <<= self.a_im * self.b_im

            # Scale by >>> (width-1): Q1.(w-1) * Q1.(w-1) -> Q1.(w-1)
            self._sc_arbr <<= SRA(self._arbr, width - 1)
            self._sc_arbi <<= SRA(self._arbi, width - 1)
            self._sc_aibr <<= SRA(self._aibr, width - 1)
            self._sc_aibi <<= SRA(self._aibi, width - 1)

            self.m_re <<= self._sc_arbr - self._sc_aibi
            self.m_im <<= self._sc_arbi + self._sc_aibr


# =====================================================================
# FFTTwiddle — Twiddle factor ROM (complex exponential lookup)
# =====================================================================
class FFTTwiddle(Module):
    def __init__(self, N=64, width=16, name="FFTTwiddle"):
        super().__init__(name)
        log_n = log2_int(N)
        self.clk = Input(1, "clk")
        self.addr = Input(log_n, "addr")
        self.tw_re = Output(width, "tw_re", signed=True)
        self.tw_im = Output(width, "tw_im", signed=True)

        re_path, im_path = generate_twiddle_hex(N, width)
        self.tw_mem_re = Memory(width, N, "tw_mem_re", init_file=re_path)
        self.tw_mem_im = Memory(width, N, "tw_mem_im", init_file=im_path)

        self._tw_re_wire = Wire(width, "_tw_re_wire", signed=True)
        self._tw_im_wire = Wire(width, "_tw_im_wire", signed=True)

        @self.comb
        def _out():
            self._tw_re_wire <<= self.tw_mem_re[self.addr]
            self._tw_im_wire <<= self.tw_mem_im[self.addr]
            self.tw_re <<= self._tw_re_wire
            self.tw_im <<= self._tw_im_wire


# =====================================================================
# FFTSdfUnit — Radix-2^2 Single-Path Delay Feedback Unit
# =====================================================================
class FFTSdfUnit(Module):
    def __init__(self, N=64, M=64, width=16, name="FFTSdfUnit"):
        super().__init__(name)
        log_n = log2_int(N)
        log_m = log2_int(M)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")  # active-high async reset
        self.di_en = Input(1, "di_en")
        self.di_re = Input(width, "di_re", signed=True)
        self.di_im = Input(width, "di_im", signed=True)
        self.do_en = Output(1, "do_en")
        self.do_re = Output(width, "do_re", signed=True)
        self.do_im = Output(width, "do_im", signed=True)

        # -----------------------------------------------------------------
        # 1st Butterfly (BF1) + DelayBuffer1
        # -----------------------------------------------------------------
        self.di_count = Reg(log_n, "di_count")
        self.bf1_bf = Wire(1, "bf1_bf")

        # Butterfly inputs (selected by bf1_bf)
        self.bf1_x0_re = Wire(width, "bf1_x0_re", signed=True)
        self.bf1_x0_im = Wire(width, "bf1_x0_im", signed=True)
        self.bf1_x1_re = Wire(width, "bf1_x1_re", signed=True)
        self.bf1_x1_im = Wire(width, "bf1_x1_im", signed=True)

        # Butterfly outputs
        self.bf1_y0_re = Wire(width, "bf1_y0_re", signed=True)
        self.bf1_y0_im = Wire(width, "bf1_y0_im", signed=True)
        self.bf1_y1_re = Wire(width, "bf1_y1_re", signed=True)
        self.bf1_y1_im = Wire(width, "bf1_y1_im", signed=True)

        # Delay buffer signals
        self.db1_di_re = Wire(width, "db1_di_re", signed=True)
        self.db1_di_im = Wire(width, "db1_di_im", signed=True)
        self.db1_do_re = Wire(width, "db1_do_re", signed=True)
        self.db1_do_im = Wire(width, "db1_do_im", signed=True)

        # Single-path output from BF1 stage
        self.bf1_sp_re = Wire(width, "bf1_sp_re", signed=True)
        self.bf1_sp_im = Wire(width, "bf1_sp_im", signed=True)
        self.bf1_sp_en = Reg(1, "bf1_sp_en")
        self.bf1_count = Reg(log_n, "bf1_count")
        self.bf1_start = Wire(1, "bf1_start")
        self.bf1_end = Wire(1, "bf1_end")
        self.bf1_mj = Wire(1, "bf1_mj")
        self.bf1_do_re = Reg(width, "bf1_do_re", signed=True)
        self.bf1_do_im = Reg(width, "bf1_do_im", signed=True)

        # -----------------------------------------------------------------
        # 2nd Butterfly (BF2) + DelayBuffer2
        # -----------------------------------------------------------------
        self.bf2_bf = Reg(1, "bf2_bf")
        self.bf2_x0_re = Wire(width, "bf2_x0_re", signed=True)
        self.bf2_x0_im = Wire(width, "bf2_x0_im", signed=True)
        self.bf2_x1_re = Wire(width, "bf2_x1_re", signed=True)
        self.bf2_x1_im = Wire(width, "bf2_x1_im", signed=True)

        self.bf2_y0_re = Wire(width, "bf2_y0_re", signed=True)
        self.bf2_y0_im = Wire(width, "bf2_y0_im", signed=True)
        self.bf2_y1_re = Wire(width, "bf2_y1_re", signed=True)
        self.bf2_y1_im = Wire(width, "bf2_y1_im", signed=True)

        self.db2_di_re = Wire(width, "db2_di_re", signed=True)
        self.db2_di_im = Wire(width, "db2_di_im", signed=True)
        self.db2_do_re = Wire(width, "db2_do_re", signed=True)
        self.db2_do_im = Wire(width, "db2_do_im", signed=True)

        self.bf2_sp_re = Wire(width, "bf2_sp_re", signed=True)
        self.bf2_sp_im = Wire(width, "bf2_sp_im", signed=True)
        self.bf2_sp_en = Reg(1, "bf2_sp_en")
        self.bf2_count = Reg(log_n, "bf2_count")
        self.bf2_start = Reg(1, "bf2_start")
        self.bf2_end = Wire(1, "bf2_end")
        self.bf2_do_re = Reg(width, "bf2_do_re", signed=True)
        self.bf2_do_im = Reg(width, "bf2_do_im", signed=True)
        self.bf2_do_en = Reg(1, "bf2_do_en")

        # -----------------------------------------------------------------
        # Multiplication stage
        # -----------------------------------------------------------------
        self.tw_sel = Wire(2, "tw_sel")
        # Match reference SdfUnit.v: wire[LOG_N-3:0] tw_num (width = LOG_N-2)
        self.tw_num = Wire(max(1, log_n - 2), "tw_num")
        self.tw_addr = Wire(log_n, "tw_addr")
        self.tw_re = Wire(width, "tw_re", signed=True)
        self.tw_im = Wire(width, "tw_im", signed=True)

        self.mu_en = Reg(1, "mu_en")
        self.mu_a_re = Wire(width, "mu_a_re", signed=True)
        self.mu_a_im = Wire(width, "mu_a_im", signed=True)
        self.mu_m_re = Wire(width, "mu_m_re", signed=True)
        self.mu_m_im = Wire(width, "mu_m_im", signed=True)
        self.mu_do_re = Reg(width, "mu_do_re", signed=True)
        self.mu_do_im = Reg(width, "mu_do_im", signed=True)
        self.mu_do_en = Reg(1, "mu_do_en")

        # -----------------------------------------------------------------
        # Instantiate sub-modules via explicit SubmoduleInst
        # -----------------------------------------------------------------
        db1_depth = 1 << (log_m - 1) if log_m >= 1 else 1
        db2_depth = 1 << (log_m - 2) if log_m >= 2 else 1

        bf1_mod = FFTButterfly(width, rh=0, name="BF1")
        bf2_mod = FFTButterfly(width, rh=1, name="BF2")
        db1_mod = FFTDelayBuffer(db1_depth, width, name="DB1")
        db2_mod = FFTDelayBuffer(db2_depth, width, name="DB2")
        tw_mod = FFTTwiddle(N, width, name="TW")
        mu_mod = FFTMultiply(width, name="MU")

        # BF1 instance
        self._top_level.append(SubmoduleInst(
            name="BF1", module=bf1_mod, params={},
            port_map={
                "x0_re": self.bf1_x0_re, "x0_im": self.bf1_x0_im,
                "x1_re": self.bf1_x1_re, "x1_im": self.bf1_x1_im,
                "y0_re": self.bf1_y0_re, "y0_im": self.bf1_y0_im,
                "y1_re": self.bf1_y1_re, "y1_im": self.bf1_y1_im,
            }
        ))
        # DB1 instance
        self._top_level.append(SubmoduleInst(
            name="DB1", module=db1_mod, params={},
            port_map={
                "clk": self.clk, "rst": self.rst,
                "di_re": self.db1_di_re, "di_im": self.db1_di_im,
                "do_re": self.db1_do_re, "do_im": self.db1_do_im,
            }
        ))
        # BF2 instance
        self._top_level.append(SubmoduleInst(
            name="BF2", module=bf2_mod, params={},
            port_map={
                "x0_re": self.bf2_x0_re, "x0_im": self.bf2_x0_im,
                "x1_re": self.bf2_x1_re, "x1_im": self.bf2_x1_im,
                "y0_re": self.bf2_y0_re, "y0_im": self.bf2_y0_im,
                "y1_re": self.bf2_y1_re, "y1_im": self.bf2_y1_im,
            }
        ))
        # DB2 instance
        self._top_level.append(SubmoduleInst(
            name="DB2", module=db2_mod, params={},
            port_map={
                "clk": self.clk, "rst": self.rst,
                "di_re": self.db2_di_re, "di_im": self.db2_di_im,
                "do_re": self.db2_do_re, "do_im": self.db2_do_im,
            }
        ))
        # Twiddle instance
        self._top_level.append(SubmoduleInst(
            name="TW", module=tw_mod, params={},
            port_map={
                "clk": self.clk,
                "addr": self.tw_addr,
                "tw_re": self.tw_re, "tw_im": self.tw_im,
            }
        ))
        # Multiply instance
        self._top_level.append(SubmoduleInst(
            name="MU", module=mu_mod, params={},
            port_map={
                "a_re": self.mu_a_re, "a_im": self.mu_a_im,
                "b_re": self.tw_re, "b_im": self.tw_im,
                "m_re": self.mu_m_re, "m_im": self.mu_m_im,
            }
        ))

        # -----------------------------------------------------------------
        # Combinational logic
        # -----------------------------------------------------------------
        @self.comb
        def _comb():
            # BF1 control
            self.bf1_bf <<= self.di_count[log_m - 1]

            # DelayBuffer1 input mux
            self.db1_di_re <<= Mux(self.bf1_bf, self.bf1_y1_re, self.di_re)
            self.db1_di_im <<= Mux(self.bf1_bf, self.bf1_y1_im, self.di_im)

            # BF1 inputs (only valid when bf1_bf=1)
            self.bf1_x0_re <<= Mux(self.bf1_bf, self.db1_do_re, Const(0, width))
            self.bf1_x0_im <<= Mux(self.bf1_bf, self.db1_do_im, Const(0, width))
            self.bf1_x1_re <<= Mux(self.bf1_bf, self.di_re, Const(0, width))
            self.bf1_x1_im <<= Mux(self.bf1_bf, self.di_im, Const(0, width))

            # BF1 single-path output: bypass with -j rotation when bf1_mj
            self.bf1_sp_re <<= Mux(self.bf1_bf, self.bf1_y0_re,
                                   Mux(self.bf1_mj, self.db1_do_im, self.db1_do_re))
            self.bf1_sp_im <<= Mux(self.bf1_bf, self.bf1_y0_im,
                                   Mux(self.bf1_mj, Const(0, width) - self.db1_do_re, self.db1_do_im))

            # BF1 start/end triggers
            self.bf1_start <<= self.di_count == ((1 << (log_m - 1)) - 1)
            self.bf1_end <<= self.bf1_count == ((1 << log_n) - 1)
            self.bf1_mj <<= self.bf1_count[log_m - 1 : log_m - 2] == 3

            # BF2 control
            self.bf2_x0_re <<= Mux(self.bf2_bf, self.db2_do_re, Const(0, width))
            self.bf2_x0_im <<= Mux(self.bf2_bf, self.db2_do_im, Const(0, width))
            self.bf2_x1_re <<= Mux(self.bf2_bf, self.bf1_do_re, Const(0, width))
            self.bf2_x1_im <<= Mux(self.bf2_bf, self.bf1_do_im, Const(0, width))

            self.db2_di_re <<= Mux(self.bf2_bf, self.bf2_y1_re, self.bf1_do_re)
            self.db2_di_im <<= Mux(self.bf2_bf, self.bf2_y1_im, self.bf1_do_im)
            self.bf2_sp_re <<= Mux(self.bf2_bf, self.bf2_y0_re, self.db2_do_re)
            self.bf2_sp_im <<= Mux(self.bf2_bf, self.bf2_y0_im, self.db2_do_im)

            self.bf2_end <<= self.bf2_count == ((1 << log_n) - 1)

            # Twiddle address generation (matches reference SdfUnit.v)
            # tw_sel is 2 bits: {bf2_count[LOG_M-2], bf2_count[LOG_M-1]}
            if log_m >= 2:
                self.tw_sel[1] <<= self.bf2_count[log_m - 2]
                self.tw_sel[0] <<= self.bf2_count[log_m - 1]
            else:
                self.tw_sel[0] <<= Const(0, 1)
            self.tw_num <<= self.bf2_count << (log_n - log_m)
            self.tw_addr <<= self.tw_num * self.tw_sel

            # Multiply bypass
            self.mu_a_re <<= Mux(self.mu_en, self.bf2_do_re, Const(0, width))
            self.mu_a_im <<= Mux(self.mu_en, self.bf2_do_im, Const(0, width))

            # Output mux: bypass multiply when LOG_M == 2
            if log_m == 2:
                self.do_en <<= self.bf2_do_en
                self.do_re <<= self.bf2_do_re
                self.do_im <<= self.bf2_do_im
            else:
                self.do_en <<= self.mu_do_en
                self.do_re <<= self.mu_do_re
                self.do_im <<= self.mu_do_im

        # -----------------------------------------------------------------
        # Sequential logic
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst, reset_async=True)
        def _seq():
            with If(self.rst == 1):
                self.di_count <<= 0
                self.bf1_sp_en <<= 0
                self.bf1_count <<= 0
                self.bf2_sp_en <<= 0
                self.bf2_count <<= 0
                self.bf2_do_en <<= 0
                self.mu_do_en <<= 0
            with Else():
                # di_count: increments while di_en is high
                with If(self.di_en):
                    self.di_count <<= self.di_count + 1
                with Else():
                    self.di_count <<= 0

                # BF1 single-path enable
                with If(self.bf1_start):
                    self.bf1_sp_en <<= 1
                with Else():
                    with If(self.bf1_end):
                        self.bf1_sp_en <<= 0

                # BF1 count
                with If(self.bf1_sp_en):
                    self.bf1_count <<= self.bf1_count + 1
                with Else():
                    self.bf1_count <<= 0

                # BF1 output pipeline
                self.bf1_do_re <<= self.bf1_sp_re
                self.bf1_do_im <<= self.bf1_sp_im

                # BF2 butterfly enable (registered)
                self.bf2_bf <<= self.bf1_count[log_m - 2]

                # BF2 start trigger (registered)
                self.bf2_start <<= (self.bf1_count == ((1 << (log_m - 2)) - 1)) & self.bf1_sp_en

                # BF2 single-path enable
                with If(self.bf2_start):
                    self.bf2_sp_en <<= 1
                with Else():
                    with If(self.bf2_end):
                        self.bf2_sp_en <<= 0

                # BF2 count
                with If(self.bf2_sp_en):
                    self.bf2_count <<= self.bf2_count + 1
                with Else():
                    self.bf2_count <<= 0

                # BF2 output pipeline
                self.bf2_do_re <<= self.bf2_sp_re
                self.bf2_do_im <<= self.bf2_sp_im
                self.bf2_do_en <<= self.bf2_sp_en

                # Multiply enable (bypass when tw_addr == 0)
                self.mu_en <<= self.tw_addr != 0
                self.mu_do_re <<= Mux(self.mu_en, self.mu_m_re, self.bf2_do_re)
                self.mu_do_im <<= Mux(self.mu_en, self.mu_m_im, self.bf2_do_im)
                self.mu_do_en <<= self.bf2_do_en


# =====================================================================
# FFTSdfUnit2 — Radix-2 SDF unit for M=2 (no twiddle multiply)
# =====================================================================
class FFTSdfUnit2(Module):
    def __init__(self, N=64, width=16, name="FFTSdfUnit2"):
        super().__init__(name)
        log_n = log2_int(N)
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.di_en = Input(1, "di_en")
        self.di_re = Input(width, "di_re", signed=True)
        self.di_im = Input(width, "di_im", signed=True)
        self.do_en = Output(1, "do_en")
        self.do_re = Output(width, "do_re", signed=True)
        self.do_im = Output(width, "do_im", signed=True)

        self.bf_en = Reg(1, "bf_en")
        self.x0_re = Wire(width, "x0_re", signed=True)
        self.x0_im = Wire(width, "x0_im", signed=True)
        self.x1_re = Wire(width, "x1_re", signed=True)
        self.x1_im = Wire(width, "x1_im", signed=True)

        self.y0_re = Wire(width, "y0_re", signed=True)
        self.y0_im = Wire(width, "y0_im", signed=True)
        self.y1_re = Wire(width, "y1_re", signed=True)
        self.y1_im = Wire(width, "y1_im", signed=True)

        self.db_di_re = Wire(width, "db_di_re", signed=True)
        self.db_di_im = Wire(width, "db_di_im", signed=True)
        self.db_do_re = Wire(width, "db_do_re", signed=True)
        self.db_do_im = Wire(width, "db_do_im", signed=True)

        self.bf_sp_re = Wire(width, "bf_sp_re", signed=True)
        self.bf_sp_im = Wire(width, "bf_sp_im", signed=True)
        self.bf_sp_en = Reg(1, "bf_sp_en")

        bf_mod = FFTButterfly(width, rh=0, name="BF")
        db_mod = FFTDelayBuffer(1, width, name="DB")

        self._top_level.append(SubmoduleInst(
            name="BF", module=bf_mod, params={},
            port_map={
                "x0_re": self.x0_re, "x0_im": self.x0_im,
                "x1_re": self.x1_re, "x1_im": self.x1_im,
                "y0_re": self.y0_re, "y0_im": self.y0_im,
                "y1_re": self.y1_re, "y1_im": self.y1_im,
            }
        ))
        self._top_level.append(SubmoduleInst(
            name="DB", module=db_mod, params={},
            port_map={
                "clk": self.clk, "rst": self.rst,
                "di_re": self.db_di_re, "di_im": self.db_di_im,
                "do_re": self.db_do_re, "do_im": self.db_do_im,
            }
        ))

        @self.comb
        def _comb():
            self.x0_re <<= Mux(self.bf_en, self.db_do_re, Const(0, width))
            self.x0_im <<= Mux(self.bf_en, self.db_do_im, Const(0, width))
            self.x1_re <<= Mux(self.bf_en, self.di_re, Const(0, width))
            self.x1_im <<= Mux(self.bf_en, self.di_im, Const(0, width))

            self.db_di_re <<= Mux(self.bf_en, self.y1_re, self.di_re)
            self.db_di_im <<= Mux(self.bf_en, self.y1_im, self.di_im)
            self.bf_sp_re <<= Mux(self.bf_en, self.y0_re, self.db_do_re)
            self.bf_sp_im <<= Mux(self.bf_en, self.y0_im, self.db_do_im)

        @self.seq(self.clk, self.rst, reset_async=True)
        def _seq():
            with If(self.rst == 1):
                self.bf_en <<= 0
                self.bf_sp_en <<= 0
                self.do_en <<= 0
            with Else():
                with If(self.di_en):
                    self.bf_en <<= ~self.bf_en
                with Else():
                    self.bf_en <<= 0
                self.bf_sp_en <<= self.di_en
                self.do_en <<= self.bf_sp_en
                self.do_re <<= self.bf_sp_re
                self.do_im <<= self.bf_sp_im


# =====================================================================
# FFTController — Top-level parameterized FFT accelerator
# =====================================================================
class FFTController(Module):
    def __init__(self, N=64, width=16, name="FFTController"):
        super().__init__(name)
        log_n = log2_int(N)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.di_en = Input(1, "di_en")
        self.di_re = Input(width, "di_re", signed=True)
        self.di_im = Input(width, "di_im", signed=True)
        self.do_en = Output(1, "do_en")
        self.do_re = Output(width, "do_re", signed=True)
        self.do_im = Output(width, "do_im", signed=True)

        # Determine number of SdfUnit stages
        num_su = log_n // 2
        need_su2 = (log_n % 2) == 1

        stages = []
        for i in range(num_su):
            m = N >> (2 * i)
            stages.append(("su", m))
        if need_su2:
            stages.append(("su2", 2))

        # Chain stages via explicit intermediate wires
        prev_en = self.di_en
        prev_re = self.di_re
        prev_im = self.di_im

        for idx, (stype, m) in enumerate(stages):
            inst_name = f"SU{idx + 1}"
            out_en_w = Wire(1, f"{inst_name.lower()}_out_en")
            out_re_w = Wire(width, f"{inst_name.lower()}_out_re", signed=True)
            out_im_w = Wire(width, f"{inst_name.lower()}_out_im", signed=True)

            if stype == "su":
                su_mod = FFTSdfUnit(N=N, M=m, width=width, name=inst_name)
            else:
                su_mod = FFTSdfUnit2(N=N, width=width, name=inst_name)

            self._top_level.append(SubmoduleInst(
                name=inst_name, module=su_mod, params={},
                port_map={
                    "clk": self.clk, "rst": self.rst,
                    "di_en": prev_en, "di_re": prev_re, "di_im": prev_im,
                    "do_en": out_en_w, "do_re": out_re_w, "do_im": out_im_w,
                }
            ))

            prev_en = out_en_w
            prev_re = out_re_w
            prev_im = out_im_w

        @self.comb
        def _out():
            self.do_en <<= prev_en
            self.do_re <<= prev_re
            self.do_im <<= prev_im
