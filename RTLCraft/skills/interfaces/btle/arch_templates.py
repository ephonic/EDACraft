"""
skills.interfaces.btle.arch_templates — BTLE Architecture Templates

Builds ArchDefinition for BTLE PHY controller with configurable
channel, CRC init, access address, and PDU size.

Architecture:
  BTLE_PHY (top wrapper: TX + RX)
    ├── BTLE_TX — TX: PDU RAM → preamble+AA → CRC+scramble → GFSK
    ├── BTLE_RX_CORE — RX: GFSK demod → AA search → descramble → CRC
    ├── CRC24_CORE — CRC-24 LFSR engine
    ├── SCRAMBLE_CORE — Data whitening LFSR
    ├── SEARCH_AA — Access address detector
    ├── GFSK_DEMOD — GFSK demodulator
    └── VCO — VCO with ROM lookup

Usage:
    from skills.interfaces.btle.arch_templates import build_btle_arch
    arch = build_btle_arch()
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, ArchDefinition, Protocol_Model,
)
from rtlgen.behaviors import TemplateRegistry

# Import behaviors to register BTLE templates in TemplateRegistry
import skills.interfaces.btle.behaviors  # noqa: F401

from skills.interfaces.btle.models import (
    CRC24_CORE_Model,
    SCRAMBLE_CORE_Model,
    SEARCH_AA_Model,
    GFSK_DEMOD_Model,
    BTLE_RX_Model,
    BTLE_TX_Model,
)


# =====================================================================
# BLE Default Access Addresses
# =====================================================================

# BLE advertising channels
BLE_AA_ADVERTISING = 0x8E89BED6  # Standard BLE advertising AA
BLE_PREAMBLE_0 = 0xD6  # For AA ending in 0
BLE_PREAMBLE_1 = 0x71  # For AA ending in 1


def build_btle_arch(
    access_address: int = BLE_AA_ADVERTISING,
    channel: int = 37,
    crc_init: int = 0x555555,
    payload_len_bits: int = 8,
    crc_width: int = 24,
    channel_width: int = 6,
    demod_width: int = 16,
    len_seq: int = 32,
    vco_width: int = 16,
    rom_addr_width: int = 11,
    iq_width: int = 8,
) -> ArchDefinition:
    """Build ArchDefinition for BTLE controller.

    Creates processing elements for:
    - crc24_core: CRC-24 LFSR
    - scramble_core: Data whitening LFSR
    - access_address_detect: AA detector
    - gfsk_demod: GFSK demodulator
    - btle_rx_core: RX core with FSM
    - btle_tx: TX with FSM
    - btle_phy: PHY wrapper

    Args:
        access_address: 32-bit access address (default: 0x8E89BED6)
        channel: BLE channel number (0-39)
        crc_init: CRC initialization value
        payload_len_bits: Bit width for payload length field
        crc_width: CRC state width (24 for BLE)
        channel_width: Channel number bit width (6)
        demod_width: GFSK demodulator input width
        len_seq: Access address sequence length
        vco_width: VCO integrator width
        rom_addr_width: sin/cos ROM address width
        iq_width: I/Q output width
    """
    crc_pe = ProcessingElement(
        name="CRC24", pe_type="crc24_core",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("crc_state_init_bit", "input", crc_width),
            PortDesc("crc_state_init_bit_load", "input", 1),
            PortDesc("data_in", "input", 1),
            PortDesc("data_in_valid", "input", 1),
        ],
        outputs=[PortDesc("lfsr", "output", crc_width)],
        state=[StateDesc("lfsr", "int", "CRC LFSR", rtl_type="reg",
                         rtl_width=crc_width)],
        behavior=TemplateRegistry.get("crc24_core"),
        can_stall=False, latency=1,
    )

    scramble_pe = ProcessingElement(
        name="SCRAMBLE", pe_type="scramble_core",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("channel_number", "input", channel_width),
            PortDesc("channel_number_load", "input", 1),
            PortDesc("data_in", "input", 1),
            PortDesc("data_in_valid", "input", 1),
        ],
        outputs=[
            PortDesc("data_out", "output", 1),
            PortDesc("data_out_valid", "output", 1),
        ],
        state=[StateDesc("lfsr", "int", "Whitening LFSR", rtl_type="reg",
                         rtl_width=7)],
        behavior=TemplateRegistry.get("scramble_core"),
        can_stall=False, latency=1,
    )

    aa_pe = ProcessingElement(
        name="SEARCH_AA", pe_type="access_address_detect",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("phy_bit", "input", 1),
            PortDesc("bit_valid", "input", 1),
            PortDesc("unique_bit_sequence", "input", len_seq),
        ],
        outputs=[PortDesc("hit_flag", "output", 1)],
        state=[
            StateDesc("bit_store", "int", "Shift register", rtl_type="reg",
                      rtl_width=len_seq),
            StateDesc("bit_valid_d1", "int", "Valid delay", rtl_type="reg",
                      rtl_width=1),
        ],
        behavior=TemplateRegistry.get("access_address_detect"),
        can_stall=False, latency=1,
    )

    demod_pe = ProcessingElement(
        name="GFSK_DEMOD", pe_type="gfsk_demod",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("i", "input", demod_width),
            PortDesc("q", "input", demod_width),
            PortDesc("iq_valid", "input", 1),
        ],
        outputs=[
            PortDesc("phy_bit", "output", 1),
            PortDesc("bit_valid", "output", 1),
            PortDesc("signal_for_decision", "output", 2 * demod_width),
            PortDesc("signal_for_decision_valid", "output", 1),
        ],
        state=[
            StateDesc("i0", "int", "Delayed I", rtl_type="reg",
                      rtl_width=2 * demod_width),
            StateDesc("q0", "int", "Delayed Q", rtl_type="reg",
                      rtl_width=2 * demod_width),
            StateDesc("sig_decision", "int", "Decision metric", rtl_type="reg",
                      rtl_width=2 * demod_width),
        ],
        behavior=TemplateRegistry.get("gfsk_demod"),
        can_stall=False, latency=3,
    )

    rx_pe = ProcessingElement(
        name="BTLE_RX_CORE", pe_type="btle_rx_core",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("unique_bit_sequence", "input", len_seq),
            PortDesc("channel_number", "input", channel_width),
            PortDesc("crc_state_init_bit", "input", crc_width),
            PortDesc("i", "input", demod_width),
            PortDesc("q", "input", demod_width),
            PortDesc("iq_valid", "input", 1),
        ],
        outputs=[
            PortDesc("hit_flag", "output", 1),
            PortDesc("payload_length_out", "output", payload_len_bits),
            PortDesc("payload_length_valid", "output", 1),
            PortDesc("info_bit", "output", 1),
            PortDesc("bit_valid", "output", 1),
            PortDesc("octet", "output", 8),
            PortDesc("octet_valid", "output", 1),
            PortDesc("decode_end", "output", 1),
            PortDesc("crc_ok", "output", 1),
        ],
        state=[
            StateDesc("rx_state", "int", "FSM state", rtl_type="reg", rtl_width=2),
            StateDesc("bit_count", "int", "Bit counter", rtl_type="reg",
                      rtl_width=payload_len_bits + 4),
            StateDesc("bit_store", "int", "AA search shift reg", rtl_type="reg",
                      rtl_width=len_seq),
            StateDesc("lfsr", "int", "CRC LFSR", rtl_type="reg",
                      rtl_width=crc_width),
            StateDesc("scramble_lfsr", "int", "Whitening LFSR", rtl_type="reg",
                      rtl_width=7),
        ],
        behavior=TemplateRegistry.get("btle_rx_core"),
        can_stall=False, latency=3,
    )

    tx_pe = ProcessingElement(
        name="BTLE_TX", pe_type="btle_tx",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("clkb", "input", 1),
            PortDesc("preamble", "input", 8),
            PortDesc("access_address", "input", 32),
            PortDesc("crc_state_init_bit", "input", crc_width),
            PortDesc("crc_state_init_bit_load", "input", 1),
            PortDesc("channel_number", "input", channel_width),
            PortDesc("channel_number_load", "input", 1),
            PortDesc("tx_start", "input", 1),
            PortDesc("pdu_octet_mem_data", "input", 8),
            PortDesc("pdu_octet_mem_addr", "input", payload_len_bits + 1),
        ],
        outputs=[
            PortDesc("i", "output", iq_width),
            PortDesc("q", "output", iq_width),
            PortDesc("iq_valid", "output", 1),
            PortDesc("iq_valid_last", "output", 1),
        ],
        state=[
            StateDesc("tx_state", "int", "FSM state", rtl_type="reg", rtl_width=2),
            StateDesc("tx_bit_count", "int", "Bit counter", rtl_type="reg",
                      rtl_width=8),
            StateDesc("tx_pa_reg", "int", "Preamble+AA shift reg", rtl_type="reg",
                      rtl_width=40),
        ],
        behavior=TemplateRegistry.get("btle_tx"),
        can_stall=False, latency=1,
    )

    phy_pe = ProcessingElement(
        name="BTLE_PHY", pe_type="btle_phy",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("clkb", "input", 1),
            # TX inputs
            PortDesc("tx_start", "input", 1),
            PortDesc("tx_preamble", "input", 8),
            PortDesc("tx_access_address", "input", 32),
            PortDesc("tx_crc_state_init_bit", "input", crc_width),
            PortDesc("tx_crc_state_init_bit_load", "input", 1),
            PortDesc("tx_channel_number", "input", channel_width),
            PortDesc("tx_channel_number_load", "input", 1),
            PortDesc("tx_pdu_octet_mem_data", "input", 8),
            PortDesc("tx_pdu_octet_mem_addr", "input", payload_len_bits + 1),
            # RX inputs
            PortDesc("rx_unique_bit_sequence", "input", len_seq),
            PortDesc("rx_channel_number", "input", channel_width),
            PortDesc("rx_crc_state_init_bit", "input", crc_width),
            PortDesc("rx_i_signal", "input", demod_width),
            PortDesc("rx_q_signal", "input", demod_width),
            PortDesc("rx_iq_valid", "input", 1),
        ],
        outputs=[
            PortDesc("tx_i_signal", "output", iq_width),
            PortDesc("tx_q_signal", "output", iq_width),
            PortDesc("tx_iq_valid", "output", 1),
            PortDesc("tx_iq_valid_last", "output", 1),
            PortDesc("rx_hit_flag", "output", 1),
            PortDesc("rx_decode_run", "output", 1),
            PortDesc("rx_decode_end", "output", 1),
            PortDesc("rx_crc_ok", "output", 1),
            PortDesc("rx_best_phase", "output", 3),
            PortDesc("rx_payload_length", "output", payload_len_bits),
            PortDesc("rx_pdu_octet_mem_data", "output", 8),
        ],
        state=[
            StateDesc("phy_tx_state", "int", "TX FSM", rtl_type="reg", rtl_width=2),
            StateDesc("phy_rx_state", "int", "RX FSM", rtl_type="reg", rtl_width=2),
        ],
        behavior=TemplateRegistry.get("btle_phy"),
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="BTLE_Controller",
        description="Bluetooth Low Energy transceiver: PHY datapath with GFSK "
                    "modulation/demodulation, CRC-24, data whitening, "
                    "and access address detection.",
        isa="protocol",
        processing_elements=[crc_pe, scramble_pe, aa_pe, demod_pe, rx_pe, tx_pe, phy_pe],
        interconnects=[
            InterconnectSpec("GFSK_DEMOD", "SEARCH_AA", signals=[
                PortDesc("phy_bit", "output", 1),
                PortDesc("bit_valid", "output", 1),
            ], flow_type="stream"),
            InterconnectSpec("SEARCH_AA", "SCRAMBLE", signals=[
                PortDesc("phy_bit", "output", 1),
                PortDesc("bit_valid", "output", 1),
            ], flow_type="stream"),
            InterconnectSpec("SCRAMBLE", "CRC24", signals=[
                PortDesc("data_out", "output", 1),
                PortDesc("data_out_valid", "output", 1),
            ], flow_type="stream"),
        ],
        model=Protocol_Model(),
        ppa_targets={"max_area": 50000, "target_freq": 16e6},
    )


class BTLE_ControllerModel:
    """BTLE controller behavioral model for simulation.

    Combines TX and RX models for end-to-end protocol simulation.
    """

    def __init__(
        self,
        access_address: int = BLE_AA_ADVERTISING,
        channel: int = 37,
        crc_init: int = 0x555555,
    ):
        self.tx = BTLE_TX_Model(
            access_address=access_address,
            channel=channel,
            crc_init=crc_init,
            preamble=BLE_PREAMBLE_0 if (access_address & 1) == 0 else BLE_PREAMBLE_1,
        )
        self.rx = BTLE_RX_Model(
            access_address=access_address,
            channel=channel,
            crc_init=crc_init,
        )
        self.cycle_count = 0
        self.transmitted_bits = 0
        self.received_bits = 0

    def load_pdu(self, pdu: bytes):
        """Load PDU for TX."""
        self.tx.load_pdu(pdu)

    def start_tx(self):
        """Start TX."""
        self.tx.start()

    def step(self, rx_i: int = 0, rx_q: int = 0, rx_iq_valid: int = 0):
        """Execute one cycle. Returns (tx_i, tx_q, tx_valid, rx outputs dict)."""
        tx_i, tx_q, tx_valid, tx_valid_last = self.tx.step()

        self.rx.step(rx_i, rx_q, rx_iq_valid)

        rx_outputs = {
            "hit_flag": self.rx.hit_flag,
            "decode_end": self.rx.decode_end,
            "crc_ok": self.rx.crc_ok,
            "payload_length": self.rx.payload_length,
        }

        self.cycle_count += 1
        if tx_valid:
            self.transmitted_bits += 1

        return tx_i, tx_q, tx_valid, tx_valid_last, rx_outputs
