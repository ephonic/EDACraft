"""
skills.interfaces.btle — BTLE Controller Skill

Bluetooth Low Energy PHY transceiver using the Spec2RTL flow.
GFSK modulation/demodulation, CRC-24, data whitening,
access address detection, and TX/RX datapaths.

Reference RTL: `ref_rtl/BTLE` (open-source BLE transceiver by Xianjun Jiao).

Architecture:
  BTLE_PHY (top wrapper: TX + RX)
    ├── BTLE_TX — TX: PDU RAM → preamble+AA → CRC+scramble → GFSK
    ├── BTLE_RX_CORE — RX: GFSK demod → AA search → descramble → CRC
    ├── CRC24_CORE — CRC-24 LFSR engine (BLE spec polynomial)
    ├── SCRAMBLE_CORE — Data whitening LFSR (x^7+x^4+1)
    ├── SEARCH_AA — 32-bit access address detector
    ├── GFSK_DEMOD — Delay-multiply frequency discriminator
    ├── GAUSS_FILTER — 17-tap Gaussian FIR (BT=0.5)
    ├── BIT_REPEAT_UPSAMPLE — 1M→8M bit repeater
    ├── VCO — Phase accumulator + sin/cos ROM lookup
    └── GFSK_MODULATION — Full modulator pipeline

Modules:
  - behaviors.py: 14 behavior templates for BTLE PE types
  - models.py: CRC24_CORE_Model, SCRAMBLE_CORE_Model, GFSK_DEMOD_Model,
               BTLE_RX_Model, BTLE_TX_Model + ble_crc24/ble_whiten helpers
  - arch_templates.py: build_btle_arch(), BTLE_ControllerModel
  - skeleton_templates.py: PE type → implementation steps (14 PE types)
"""

# Register behaviors and skeleton steps at import time
import skills.interfaces.btle.behaviors  # noqa: F401
import skills.interfaces.btle.skeleton_templates  # noqa: F401

from skills.interfaces.btle.models import (
    CRC24_CORE_Model,
    SCRAMBLE_CORE_Model,
    SEARCH_AA_Model,
    GFSK_DEMOD_Model,
    BTLE_RX_Model,
    BTLE_TX_Model,
    ble_crc24,
    ble_whiten,
)
from skills.interfaces.btle.arch_templates import (
    build_btle_arch,
    BTLE_ControllerModel,
    BLE_AA_ADVERTISING,
    BLE_PREAMBLE_0,
    BLE_PREAMBLE_1,
)
from skills.interfaces.btle.behaviors import (
    crc24_core_template,
    scramble_core_template,
    access_address_detect_template,
    gfsk_demod_template,
    gauss_filter_template,
    bit_upsampler_template,
    sdpram_template,
    crc_wrapper_template,
    scramble_wrapper_template,
    vco_template,
    gfsk_mod_template,
    btle_rx_core_template,
    btle_tx_template,
    btle_phy_template,
)
from skills.interfaces.btle.skeleton_templates import (
    CRC24_CORE_STEPS,
    SCRAMBLE_CORE_STEPS,
    ACCESS_ADDRESS_DETECT_STEPS,
    GFSK_DEMOD_STEPS,
    GAUSS_FILTER_STEPS,
    BIT_UPSAMPLER_STEPS,
    SDPRAM_STEPS,
    CRC_WRAPPER_STEPS,
    SCRAMBLE_WRAPPER_STEPS,
    VCO_STEPS,
    GFSK_MOD_STEPS,
    BTLE_RX_CORE_STEPS,
    BTLE_TX_STEPS,
    BTLE_PHY_STEPS,
    register_btle_skeleton_steps,
)

from skills.interfaces.btle.dsl_modules import (
    CRC24_CORE,
    SCRAMBLE_CORE,
    SEARCH_UNIQUE_BIT_SEQ,
    GFSK_DEMODULATION,
    GAUSS_FILTER,
    BIT_REPEAT_UPSAMPLE,
    SDPRAM_ONE_CLK,
    SDPRAM_TWO_CLK,
    CRC24,
    SCRAMBLE,
    VCO,
    GFSK_MODULATION,
    BTLE_RX_CORE,
    BTLE_TX,
    BTLE_PHY,
)

__all__ = [
    "CRC24_CORE", "SCRAMBLE_CORE", "SEARCH_UNIQUE_BIT_SEQ", "GFSK_DEMODULATION", "GAUSS_FILTER", "BIT_REPEAT_UPSAMPLE", "SDPRAM_ONE_CLK", "SDPRAM_TWO_CLK", "CRC24", "SCRAMBLE", "VCO", "GFSK_MODULATION", "BTLE_RX_CORE", "BTLE_TX", "BTLE_PHY",
    "CRC24_CORE_Model",
    "SCRAMBLE_CORE_Model",
    "SEARCH_AA_Model",
    "GFSK_DEMOD_Model",
    "BTLE_RX_Model",
    "BTLE_TX_Model",
    "ble_crc24",
    "ble_whiten",
    "build_btle_arch",
    "BTLE_ControllerModel",
    "BLE_AA_ADVERTISING",
    "BLE_PREAMBLE_0",
    "BLE_PREAMBLE_1",
    "crc24_core_template",
    "scramble_core_template",
    "access_address_detect_template",
    "gfsk_demod_template",
    "gauss_filter_template",
    "bit_upsampler_template",
    "sdpram_template",
    "crc_wrapper_template",
    "scramble_wrapper_template",
    "vco_template",
    "gfsk_mod_template",
    "btle_rx_core_template",
    "btle_tx_template",
    "btle_phy_template",
    "CRC24_CORE_STEPS",
    "SCRAMBLE_CORE_STEPS",
    "ACCESS_ADDRESS_DETECT_STEPS",
    "GFSK_DEMOD_STEPS",
    "GAUSS_FILTER_STEPS",
    "BIT_UPSAMPLER_STEPS",
    "SDPRAM_STEPS",
    "CRC_WRAPPER_STEPS",
    "SCRAMBLE_WRAPPER_STEPS",
    "VCO_STEPS",
    "GFSK_MOD_STEPS",
    "BTLE_RX_CORE_STEPS",
    "BTLE_TX_STEPS",
    "BTLE_PHY_STEPS",
    "register_btle_skeleton_steps",
]
