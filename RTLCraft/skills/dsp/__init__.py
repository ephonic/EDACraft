"""
skills.dsp — Digital Signal Processor Skill

DSP suite using the Spec2RTL flow.
Signed multipliers, I/Q synchronizers, I2S audio interface,
DDS sine/cosine generator, and CIC sample-rate converters.

Reference RTL: `ref_rtl/dsp/rtl/` (Alex Forencich open-source DSP library)

Architecture:
  DSP_Suite
    ├── DSP_MULT — 4-stage pipelined signed scalar multiplier
    ├── IQ_JOIN — Two-channel AXI-Stream synchronizer
    ├── IQ_SPLIT — Two-channel AXI-Stream demultiplexer
    ├── I2S_CTRL — I2S bus clock generator with programmable prescaler
    ├── PHASE_ACCUMULATOR — NCO phase accumulator with programmable step
    ├── DSP_IQ_MULT — Complex IQ multiplier (I×I, Q×Q), 4-stage pipeline
    ├── I2S_RX — I2S serial receiver (edge-detects sck, MSB-first shift)
    ├── I2S_TX — I2S serial transmitter (dual-edge sck, MSB-first shift out)
    ├── SINE_DDS_LUT — 5-stage pipelined sine/cosine LUT with fine/coarse decomposition
    ├── SINE_DDS — Top-level DDS (phase_accumulator + sine_dds_lut)
    ├── CIC_DECIMATOR — N integrators → decimator → N combs
    └── CIC_INTERPOLATOR — N combs → up-converter → N integrators

Modules:
  - behaviors.py: 12 behavior templates for DSP PE types
  - models.py: Golden reference models for all 12 DSP modules
  - dsl_modules.py: 12 DSL Module class definitions (ports, seq/comb logic)
  - arch_templates.py: build_dsp_arch(), DSP_SuiteModel
  - skeleton_templates.py: PE type → implementation steps (12 PE types)
"""

# Register behaviors and skeleton steps at import time
import skills.dsp.behaviors  # noqa: F401
import skills.dsp.skeleton_templates  # noqa: F401

from skills.dsp.models import (
    DSP_MULT_Model,
    IQ_JOIN_Model,
    IQ_SPLIT_Model,
    I2S_CTRL_Model,
    PHASE_ACCUMULATOR_Model,
    DSP_IQ_MULT_Model,
    I2S_RX_Model,
    I2S_TX_Model,
    SINE_DDS_LUT_Model,
    SINE_DDS_Model,
    CIC_DECIMATOR_Model,
    CIC_INTERPOLATOR_Model,
)
from skills.dsp.arch_templates import (
    build_dsp_arch,
    DSP_SuiteModel,
)
from skills.dsp.behaviors import (
    dsp_mult_template,
    iq_join_template,
    iq_split_template,
    i2s_ctrl_template,
    phase_accumulator_template,
    dsp_iq_mult_template,
    i2s_rx_template,
    i2s_tx_template,
    sine_dds_lut_template,
    sine_dds_template,
    cic_decimator_template,
    cic_interpolator_template,
)
from skills.dsp.skeleton_templates import (
    DSP_MULT_STEPS,
    IQ_JOIN_STEPS,
    IQ_SPLIT_STEPS,
    I2S_CTRL_STEPS,
    PHASE_ACCUMULATOR_STEPS,
    DSP_IQ_MULT_STEPS,
    I2S_RX_STEPS,
    I2S_TX_STEPS,
    SINE_DDS_LUT_STEPS,
    SINE_DDS_STEPS,
    CIC_DECIMATOR_STEPS,
    CIC_INTERPOLATOR_STEPS,
    register_dsp_skeleton_steps,
)

from skills.dsp.dsl_modules import (
    DSP_MULT,
    IQ_JOIN,
    IQ_SPLIT,
    I2S_CTRL,
    PHASE_ACCUMULATOR,
    DSP_IQ_MULT,
    I2S_RX,
    I2S_TX,
    SINE_DDS_LUT,
    SINE_DDS,
    CIC_DECIMATOR,
    CIC_INTERPOLATOR,
)

__all__ = [
    "DSP_MULT", "IQ_JOIN", "IQ_SPLIT", "I2S_CTRL", "PHASE_ACCUMULATOR", "DSP_IQ_MULT", "I2S_RX", "I2S_TX", "SINE_DDS_LUT", "SINE_DDS", "CIC_DECIMATOR", "CIC_INTERPOLATOR",
    "DSP_MULT_Model",
    "IQ_JOIN_Model",
    "IQ_SPLIT_Model",
    "I2S_CTRL_Model",
    "PHASE_ACCUMULATOR_Model",
    "DSP_IQ_MULT_Model",
    "I2S_RX_Model",
    "I2S_TX_Model",
    "SINE_DDS_LUT_Model",
    "SINE_DDS_Model",
    "CIC_DECIMATOR_Model",
    "CIC_INTERPOLATOR_Model",
    "build_dsp_arch",
    "DSP_SuiteModel",
    "dsp_mult_template",
    "iq_join_template",
    "iq_split_template",
    "i2s_ctrl_template",
    "phase_accumulator_template",
    "dsp_iq_mult_template",
    "i2s_rx_template",
    "i2s_tx_template",
    "sine_dds_lut_template",
    "sine_dds_template",
    "cic_decimator_template",
    "cic_interpolator_template",
    "DSP_MULT_STEPS",
    "IQ_JOIN_STEPS",
    "IQ_SPLIT_STEPS",
    "I2S_CTRL_STEPS",
    "PHASE_ACCUMULATOR_STEPS",
    "DSP_IQ_MULT_STEPS",
    "I2S_RX_STEPS",
    "I2S_TX_STEPS",
    "SINE_DDS_LUT_STEPS",
    "SINE_DDS_STEPS",
    "CIC_DECIMATOR_STEPS",
    "CIC_INTERPOLATOR_STEPS",
    "register_dsp_skeleton_steps",
]
