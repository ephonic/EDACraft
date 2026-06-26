"""L5 DSL module for the EarphoneFFT256 accelerator.

RTL-ready rtlgen wrapper around the reusable FFTController.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template
from design_scripts.design_fft import FFTController


class EarphoneFFT256(Module):
    """256-point streaming FFT accelerator wrapper."""

    def __init__(self):
        super().__init__("earphone_fft256")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.di_en = Input(1, "di_en")
        self.di_re = Input(16, "di_re", signed=True)
        self.di_im = Input(16, "di_im", signed=True)
        self.do_en = Output(1, "do_en")
        self.do_re = Output(16, "do_re", signed=True)
        self.do_im = Output(16, "do_im", signed=True)

        fft = FFTController(N=256, width=16, name="FFT256Core")
        self.instantiate(fft, "fft256_core", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "di_en": self.di_en,
            "di_re": self.di_re,
            "di_im": self.di_im,
            "do_en": self.do_en,
            "do_re": self.do_re,
            "do_im": self.do_im,
        })

        tpl = ModuleDocTemplate(
            source="earphone/modules/fft256/layer_L5_dsl/src/dsl.py",
            description="256-point streaming FFT wrapper (R2^2SDF, Q1.15).",
            author="RTLCraft Agent", version="0.1",
            timing="Streaming, 1 sample/cycle, bit-reversed output.",
        )
        fill_doc_template(tpl, self)


__all__ = ["EarphoneFFT256"]
