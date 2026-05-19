"""
skills.fft — Fast Fourier Transform Skill

Radix-2^2 Single-Path Delay Feedback (R2^2SDF) FFT accelerator suite.
Parameterizable FFT sizes (64/128/1024), 16-bit default data width.

Reference RTL: `ref_rtl/fft/verilog/`

Architecture:
  FFT_Suite
    ├── FFT_BUTTERFLY — Complex radix-2 butterfly (add/sub + scale)
    ├── FFT_DELAY_BUFFER — Shift-register delay line
    ├── FFT_MULTIPLY — Complex multiplier (4 real multiplies)
    ├── FFT_TWIDDLE — ROM-based twiddle factor lookup
    ├── FFT_SDF_UNIT — Radix-2^2 SDF unit (BF1+DB1+BF2+DB2+MULT)
    ├── FFT_SDF_UNIT2 — Radix-2 SDF unit for M=2 (no twiddle)
    └── FFT_CONTROLLER — Top-level: chains SDF stages based on N

Modules:
  - behaviors.py: 7 behavior templates for FFT PE types
  - models.py: Golden reference models for all 7 FFT modules
  - arch_templates.py: build_fft_arch(), FFTSuiteModel
  - skeleton_templates.py: PE type → implementation steps (7 PE types)
"""

# Register behaviors and skeleton steps at import time
import skills.fft.behaviors  # noqa: F401
import skills.fft.skeleton_templates  # noqa: F401

from skills.fft.models import (
    FFTButterflyModel,
    FFTDelayBufferModel,
    FFTMultiplyModel,
    FFTTwiddleModel,
    FFTSdfUnitModel,
    FFTSdfUnit2Model,
    FFTControllerModel,
)
from skills.fft.arch_templates import (
    build_fft_arch,
    FFTSuiteModel,
)
from skills.fft.behaviors import (
    fft_butterfly_template,
    fft_delay_buffer_template,
    fft_multiply_template,
    fft_twiddle_template,
    fft_sdf_unit_template,
    fft_sdf_unit2_template,
    fft_controller_template,
)
from skills.fft.skeleton_templates import (
    FFT_BUTTERFLY_STEPS,
    FFT_DELAY_BUFFER_STEPS,
    FFT_MULTIPLY_STEPS,
    FFT_TWIDDLE_STEPS,
    FFT_SDF_UNIT_STEPS,
    FFT_SDF_UNIT2_STEPS,
    FFT_CONTROLLER_STEPS,
    register_fft_skeleton_steps,
)

from skills.fft.dsl_modules import (
    FFTButterfly,
    FFTDelayBuffer,
    FFTMultiply,
    FFTTwiddle,
    FFTSdfUnit,
    FFTSdfUnit2,
    FFTController,
)

__all__ = [
    "FFTButterfly", "FFTDelayBuffer", "FFTMultiply", "FFTTwiddle", "FFTSdfUnit", "FFTSdfUnit2", "FFTController",
    "FFTButterflyModel",
    "FFTDelayBufferModel",
    "FFTMultiplyModel",
    "FFTTwiddleModel",
    "FFTSdfUnitModel",
    "FFTSdfUnit2Model",
    "FFTControllerModel",
    "build_fft_arch",
    "FFTSuiteModel",
    "fft_butterfly_template",
    "fft_delay_buffer_template",
    "fft_multiply_template",
    "fft_twiddle_template",
    "fft_sdf_unit_template",
    "fft_sdf_unit2_template",
    "fft_controller_template",
    "FFT_BUTTERFLY_STEPS",
    "FFT_DELAY_BUFFER_STEPS",
    "FFT_MULTIPLY_STEPS",
    "FFT_TWIDDLE_STEPS",
    "FFT_SDF_UNIT_STEPS",
    "FFT_SDF_UNIT2_STEPS",
    "FFT_CONTROLLER_STEPS",
    "register_fft_skeleton_steps",
]
