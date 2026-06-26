"""
skills.fft.arch_templates — FFT Architecture Templates

Builds ArchDefinition for an FFT suite with 7 processing elements:
  FFT_BUTTERFLY, FFT_DELAY_BUFFER, FFT_MULTIPLY, FFT_TWIDDLE,
  FFT_SDF_UNIT, FFT_SDF_UNIT2, FFT_CONTROLLER

Usage:
    from skills.fft.arch_templates import build_fft_arch
    arch = build_fft_arch()
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, ArchDefinition, Algorithm_Model,
)
from rtlgen.behaviors import TemplateRegistry

# Import behaviors to register FFT templates in TemplateRegistry
import skills.fft.behaviors  # noqa: F401


def _log2_int(x: int) -> int:
    return max(x - 1, 0).bit_length()


def build_fft_arch(
    N: int = 64,
    width: int = 16,
) -> ArchDefinition:
    """Build ArchDefinition for FFT accelerator.

    Args:
        N: FFT size (default 64)
        width: Data path width in bits (default 16)
    """
    log_n = _log2_int(N)
    num_su = log_n // 2
    need_su2 = (log_n % 2) == 1

    # 1. FFT_BUTTERFLY — Complex radix-2 butterfly
    rh = 0
    butterfly_pe = ProcessingElement(
        name="FFT_BUTTERFLY", pe_type="fft_butterfly",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("x0_re", "input", width),
            PortDesc("x0_im", "input", width),
            PortDesc("x1_re", "input", width),
            PortDesc("x1_im", "input", width),
        ],
        outputs=[
            PortDesc("y0_re", "output", width),
            PortDesc("y0_im", "output", width),
            PortDesc("y1_re", "output", width),
            PortDesc("y1_im", "output", width),
        ],
        state=[],
        behavior=TemplateRegistry.get("fft_butterfly"),
        can_stall=False, latency=1,
    )

    # 2. FFT_DELAY_BUFFER — Shift-register delay line
    # Default depth for a generic stage; actual depth set per instance
    db_depth = 1 << max(1, (log_n - 1))
    delay_buf_state = []
    for i in range(db_depth):
        delay_buf_state.append(StateDesc(f"buf_re_{i}", "int", f"Delay buf re[{i}]", rtl_type="reg", rtl_width=width))
        delay_buf_state.append(StateDesc(f"buf_im_{i}", "int", f"Delay buf im[{i}]", rtl_type="reg", rtl_width=width))

    delay_buf_pe = ProcessingElement(
        name="FFT_DELAY_BUFFER", pe_type="fft_delay_buffer",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("di_re", "input", width),
            PortDesc("di_im", "input", width),
        ],
        outputs=[
            PortDesc("do_re", "output", width),
            PortDesc("do_im", "output", width),
        ],
        state=delay_buf_state,
        behavior=TemplateRegistry.get("fft_delay_buffer"),
        can_stall=False, latency=1,
    )

    # 3. FFT_MULTIPLY — Complex multiplier
    multiply_pe = ProcessingElement(
        name="FFT_MULTIPLY", pe_type="fft_multiply",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("a_re", "input", width),
            PortDesc("a_im", "input", width),
            PortDesc("b_re", "input", width),
            PortDesc("b_im", "input", width),
        ],
        outputs=[
            PortDesc("m_re", "output", width),
            PortDesc("m_im", "output", width),
        ],
        state=[],
        behavior=TemplateRegistry.get("fft_multiply"),
        can_stall=False, latency=1,
    )

    # 4. FFT_TWIDDLE — Twiddle factor ROM
    twiddle_pe = ProcessingElement(
        name="FFT_TWIDDLE", pe_type="fft_twiddle",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("addr", "input", max(1, (N - 1).bit_length())),
        ],
        outputs=[
            PortDesc("tw_re", "output", width),
            PortDesc("tw_im", "output", width),
        ],
        state=[],
        behavior=TemplateRegistry.get("fft_twiddle"),
        can_stall=False, latency=1,
    )

    # 5. FFT_SDF_UNIT — Radix-2^2 SDF Unit (full)
    log_m = max(1, log_n - 1)  # For first stage
    db1_depth = 1 << (log_m - 1) if log_m >= 1 else 1
    db2_depth = 1 << (log_m - 2) if log_m >= 2 else 1

    sdf_unit_state = [
        StateDesc("di_count", "int", "Input data counter", rtl_type="reg", rtl_width=max(1, log_n)),
        StateDesc("bf1_sp_en", "int", "BF1 single-path enable", rtl_type="reg", rtl_width=1),
        StateDesc("bf1_count", "int", "BF1 output counter", rtl_type="reg", rtl_width=max(1, log_n)),
        StateDesc("bf2_bf", "int", "BF2 butterfly flag", rtl_type="reg", rtl_width=1),
        StateDesc("bf2_sp_en", "int", "BF2 single-path enable", rtl_type="reg", rtl_width=1),
        StateDesc("bf2_count", "int", "BF2 output counter", rtl_type="reg", rtl_width=max(1, log_n)),
        StateDesc("bf2_start", "int", "BF2 start flag", rtl_type="reg", rtl_width=1),
        StateDesc("bf2_do_en", "int", "BF2 output enable", rtl_type="reg", rtl_width=1),
        StateDesc("mu_en", "int", "Multiplier enable", rtl_type="reg", rtl_width=1),
        StateDesc("mu_do_en", "int", "Multiplier output enable", rtl_type="reg", rtl_width=1),
    ]
    for i in range(db1_depth):
        sdf_unit_state.append(StateDesc(f"db1_buf_re_{i}", "int", f"DB1 buf re[{i}]", rtl_type="reg", rtl_width=width))
        sdf_unit_state.append(StateDesc(f"db1_buf_im_{i}", "int", f"DB1 buf im[{i}]", rtl_type="reg", rtl_width=width))
    for i in range(db2_depth):
        sdf_unit_state.append(StateDesc(f"db2_buf_re_{i}", "int", f"DB2 buf re[{i}]", rtl_type="reg", rtl_width=width))
        sdf_unit_state.append(StateDesc(f"db2_buf_im_{i}", "int", f"DB2 buf im[{i}]", rtl_type="reg", rtl_width=width))

    sdf_unit_pe = ProcessingElement(
        name="FFT_SDF_UNIT", pe_type="fft_sdf_unit",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("di_en", "input", 1),
            PortDesc("di_re", "input", width),
            PortDesc("di_im", "input", width),
        ],
        outputs=[
            PortDesc("do_en", "output", 1),
            PortDesc("do_re", "output", width),
            PortDesc("do_im", "output", width),
        ],
        state=sdf_unit_state,
        behavior=TemplateRegistry.get("fft_sdf_unit"),
        can_stall=False, latency=1,
    )

    # 6. FFT_SDF_UNIT2 — Radix-2 SDF (M=2, no twiddle)
    sdf_unit2_pe = ProcessingElement(
        name="FFT_SDF_UNIT2", pe_type="fft_sdf_unit2",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("di_en", "input", 1),
            PortDesc("di_re", "input", width),
            PortDesc("di_im", "input", width),
        ],
        outputs=[
            PortDesc("do_en", "output", 1),
            PortDesc("do_re", "output", width),
            PortDesc("do_im", "output", width),
        ],
        state=[
            StateDesc("bf_en", "int", "Butterfly enable", rtl_type="reg", rtl_width=1),
            StateDesc("bf_sp_en", "int", "BF single-path enable", rtl_type="reg", rtl_width=1),
            StateDesc("do_en", "int", "Output enable", rtl_type="reg", rtl_width=1),
            StateDesc("db_buf_0_re", "int", "DB buffer 0 re", rtl_type="reg", rtl_width=width),
            StateDesc("db_buf_0_im", "int", "DB buffer 0 im", rtl_type="reg", rtl_width=width),
        ],
        behavior=TemplateRegistry.get("fft_sdf_unit2"),
        can_stall=False, latency=1,
    )

    # 7. FFT_CONTROLLER — Top-level controller
    # Build stage-by-stage state for chained SDF units
    ctrl_state = []
    for i in range(num_su):
        m_val = N >> (2 * i)
        log_m_val = _log2_int(m_val)
        d1 = 1 << (log_m_val - 1) if log_m_val >= 1 else 1
        d2 = 1 << (log_m_val - 2) if log_m_val >= 2 else 1
        for j in range(d1):
            ctrl_state.append(StateDesc(f"su{i}_db1_buf_re_{j}", "int", f"SU{i} DB1 re[{j}]", rtl_type="reg", rtl_width=width))
            ctrl_state.append(StateDesc(f"su{i}_db1_buf_im_{j}", "int", f"SU{i} DB1 im[{j}]", rtl_type="reg", rtl_width=width))
        for j in range(d2):
            ctrl_state.append(StateDesc(f"su{i}_db2_buf_re_{j}", "int", f"SU{i} DB2 re[{j}]", rtl_type="reg", rtl_width=width))
            ctrl_state.append(StateDesc(f"su{i}_db2_buf_im_{j}", "int", f"SU{i} DB2 im[{j}]", rtl_type="reg", rtl_width=width))
        ctrl_state.extend([
            StateDesc(f"su{i}_di_count", "int", f"SU{i} di counter", rtl_type="reg", rtl_width=max(1, log_n)),
            StateDesc(f"su{i}_bf1_sp_en", "int", f"SU{i} bf1 sp enable", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_bf1_count", "int", f"SU{i} bf1 counter", rtl_type="reg", rtl_width=max(1, log_n)),
            StateDesc(f"su{i}_bf2_bf", "int", f"SU{i} bf2 bf flag", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_bf2_sp_en", "int", f"SU{i} bf2 sp enable", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_bf2_count", "int", f"SU{i} bf2 counter", rtl_type="reg", rtl_width=max(1, log_n)),
            StateDesc(f"su{i}_bf2_start", "int", f"SU{i} bf2 start", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_bf2_do_en", "int", f"SU{i} bf2 do enable", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_mu_en", "int", f"SU{i} mul enable", rtl_type="reg", rtl_width=1),
            StateDesc(f"su{i}_mu_do_en", "int", f"SU{i} mul do enable", rtl_type="reg", rtl_width=1),
        ])
    if need_su2:
        ctrl_state.extend([
            StateDesc("su2_bf_en", "int", "SU2 bf enable", rtl_type="reg", rtl_width=1),
            StateDesc("su2_bf_sp_en", "int", "SU2 bf sp enable", rtl_type="reg", rtl_width=1),
            StateDesc("su2_do_en", "int", "SU2 do enable", rtl_type="reg", rtl_width=1),
            StateDesc("su2_db_buf_0_re", "int", "SU2 db buf 0 re", rtl_type="reg", rtl_width=width),
            StateDesc("su2_db_buf_0_im", "int", "SU2 db buf 0 im", rtl_type="reg", rtl_width=width),
        ])

    controller_pe = ProcessingElement(
        name="FFT_CONTROLLER", pe_type="fft_controller",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("di_en", "input", 1),
            PortDesc("di_re", "input", width),
            PortDesc("di_im", "input", width),
        ],
        outputs=[
            PortDesc("do_en", "output", 1),
            PortDesc("do_re", "output", width),
            PortDesc("do_im", "output", width),
        ],
        state=ctrl_state,
        behavior=TemplateRegistry.get("fft_controller"),
        can_stall=False, latency=1,
    )

    # Interconnect: chain stages
    interconnects = []
    for i in range(num_su + (1 if need_su2 else 0) - 1):
        src = f"FFT_SDF_UNIT{'2' if i == num_su else ''}"
        dst = f"FFT_SDF_UNIT{'2' if i + 1 == num_su + (1 if need_su2 else 0) - 1 else ''}"
        interconnects.append(InterconnectSpec(
            src, dst,
            signals=[
                PortDesc("do_en", "output", 1),
                PortDesc("do_re", "output", width),
                PortDesc("do_im", "output", width),
            ],
            flow_type="stream",
        ))

    return ArchDefinition(
        name="FFT_Suite",
        description=f"Radix-2^2 Single-Path Delay Feedback FFT accelerator, "
                    f"N={N}, width={width}, {num_su} SDF units"
                    f"{' + 1 SDF2 unit' if need_su2 else ''}.",
        isa="algorithm",
        processing_elements=[
            butterfly_pe, delay_buf_pe, multiply_pe, twiddle_pe,
            sdf_unit_pe, sdf_unit2_pe, controller_pe,
        ],
        interconnects=interconnects,
        model=Algorithm_Model(),
        ppa_targets={"max_area": 100000, "target_freq": 200e6},
    )


class FFTSuiteModel:
    """FFT suite behavioral model for simulation.

    Chains the golden reference models from models.py for end-to-end simulation.
    """

    def __init__(
        self,
        N: int = 64,
        width: int = 16,
    ):
        from skills.fft.models import FFTControllerModel
        self.controller = FFTControllerModel(N=N, width=width)
        self.N = N
        self.width = width
        self.cycle_count = 0

    def step(
        self,
        di_en: int = 0,
        di_re: int = 0,
        di_im: int = 0,
    ):
        """Advance simulation by one cycle."""
        self.cycle_count += 1
        return self.controller.step(di_en, di_re, di_im)
