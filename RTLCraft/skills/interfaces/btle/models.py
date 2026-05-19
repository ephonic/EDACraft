"""
skills.interfaces.btle.models — BTLE Controller Behavioral Models

Golden reference models for BTLE PHY verification:
  - CRC24_CORE_Model: CRC-24 LFSR (BLE spec polynomial)
  - SCRAMBLE_CORE_Model: Data whitening LFSR (x^7+x^4+1)
  - SEARCH_AA_Model: 32-bit access address detector
  - GFSK_DEMOD_Model: GFSK delay-multiply demodulator
  - BTLE_RX_Model: RX core (demod → AA → descramble → CRC)
  - BTLE_TX_Model: TX (PDU RAM → preamble+AA → CRC+scramble → GFSK)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# BLE CRC-24 Specification
# =====================================================================

def ble_crc24(data_bits: List[int], crc_init: int = 0x555555) -> int:
    """BLE CRC-24 LFSR computation (golden reference).

    Polynomial taps: 0, 1, 3, 4, 6, 9, 10
    Init value is byte-swapped: {init[7:0], init[15:8], init[23:16]}
    """
    # Byte-swap init
    lfsr = ((crc_init & 0xFF) << 16) | (crc_init & 0xFF00) | ((crc_init >> 16) & 0xFF)

    for bit in data_bits:
        new_bit = ((lfsr >> 23) & 1) ^ bit
        lfsr_new = lfsr
        # Update per BLE spec taps
        lfsr_new &= ~1
        lfsr_new |= new_bit  # bit 0
        lfsr_new &= ~(1 << 1)
        lfsr_new |= (((lfsr >> 0) & 1) ^ new_bit) << 1  # bit 1
        lfsr_new &= ~(1 << 2)
        lfsr_new |= ((lfsr >> 1) & 1) << 2  # bit 2
        lfsr_new &= ~(1 << 3)
        lfsr_new |= (((lfsr >> 2) & 1) ^ new_bit) << 3  # bit 3
        lfsr_new &= ~(1 << 4)
        lfsr_new |= (((lfsr >> 3) & 1) ^ new_bit) << 4  # bit 4
        lfsr_new &= ~(1 << 5)
        lfsr_new |= ((lfsr >> 4) & 1) << 5  # bit 5
        lfsr_new &= ~(1 << 6)
        lfsr_new |= (((lfsr >> 5) & 1) ^ new_bit) << 6  # bit 6
        lfsr_new &= ~(1 << 7)
        lfsr_new |= ((lfsr >> 6) & 1) << 7  # bit 7
        lfsr_new &= ~(1 << 8)
        lfsr_new |= ((lfsr >> 7) & 1) << 8  # bit 8
        lfsr_new &= ~(1 << 9)
        lfsr_new |= (((lfsr >> 8) & 1) ^ new_bit) << 9  # bit 9
        lfsr_new &= ~(1 << 10)
        lfsr_new |= (((lfsr >> 9) & 1) ^ new_bit) << 10  # bit 10
        lfsr_new &= ~(0xFFF << 11)
        lfsr_new |= ((lfsr >> 10) & 0xFFF) << 11  # bits 23:11

        lfsr = lfsr_new & 0xFFFFFF

    return lfsr


# =====================================================================
# BLE Data Whitening
# =====================================================================

def ble_whiten(data_bits: List[int], channel: int) -> List[int]:
    """BLE data whitening (golden reference).

    LFSR polynomial: x^7 + x^4 + 1
    Init: {1, channel_number[5:0]}
    """
    ch = channel if channel != 0 else 0x3F
    lfsr = 1 | (ch << 1)
    out = []

    for bit in data_bits:
        scram_bit = ((lfsr >> 6) & 1) ^ bit
        b0 = (lfsr >> 6) & 1
        b1 = lfsr & 1
        b2 = (lfsr >> 1) & 1
        b3 = (lfsr >> 2) & 1
        b4 = ((lfsr >> 3) & 1) ^ ((lfsr >> 6) & 1)
        b5 = (lfsr >> 4) & 1
        b6 = (lfsr >> 5) & 1
        lfsr = (b6 << 6) | (b5 << 5) | (b4 << 4) | (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
        out.append(scram_bit)

    return out


# =====================================================================
# CRC24_CORE Model
# =====================================================================

class CRC24_CORE_Model:
    """BLE CRC-24 LFSR behavioral model.

    Usage:
        crc = CRC24_CORE_Model(crc_init=0x555555)
        for bit in data_bits:
            crc.step(bit, valid=1)
        print(f"CRC: {crc.lfsr:06x}")
    """

    def __init__(self, crc_init: int = 0x555555):
        self.crc_init = crc_init
        # Byte-swap init
        self.lfsr = ((crc_init & 0xFF) << 16) | (crc_init & 0xFF00) | ((crc_init >> 16) & 0xFF)

    def step(self, data_in: int = 0, data_valid: int = 0,
             init_load: int = 0) -> int:
        """Execute one cycle. Returns current LFSR value."""
        if init_load:
            self.lfsr = ((self.crc_init & 0xFF) << 16) | \
                        (self.crc_init & 0xFF00) | ((self.crc_init >> 16) & 0xFF)
            return self.lfsr

        if data_valid:
            new_bit = ((self.lfsr >> 23) & 1) ^ data_in
            lfsr = self.lfsr
            lfsr_new = 0
            lfsr_new |= new_bit
            lfsr_new |= (((lfsr >> 0) & 1) ^ new_bit) << 1
            lfsr_new |= ((lfsr >> 1) & 1) << 2
            lfsr_new |= (((lfsr >> 2) & 1) ^ new_bit) << 3
            lfsr_new |= (((lfsr >> 3) & 1) ^ new_bit) << 4
            lfsr_new |= ((lfsr >> 4) & 1) << 5
            lfsr_new |= (((lfsr >> 5) & 1) ^ new_bit) << 6
            lfsr_new |= ((lfsr >> 6) & 1) << 7
            lfsr_new |= ((lfsr >> 7) & 1) << 8
            lfsr_new |= (((lfsr >> 8) & 1) ^ new_bit) << 9
            lfsr_new |= (((lfsr >> 9) & 1) ^ new_bit) << 10
            lfsr_new |= ((lfsr >> 10) & 0xFFF) << 11
            self.lfsr = lfsr_new & 0xFFFFFF

        return self.lfsr


# =====================================================================
# SCRAMBLE_CORE Model
# =====================================================================

class SCRAMBLE_CORE_Model:
    """BLE data whitening LFSR behavioral model.

    Polynomial: x^7 + x^4 + 1.
    Init: {1, channel_number[5:0]}
    """

    def __init__(self, channel: int = 0):
        self.channel = channel if channel != 0 else 0x3F
        self.lfsr = 1 | (self.channel << 1)

    def step(self, data_in: int = 0, data_valid: int = 0) -> Tuple[int, int]:
        """Execute one cycle. Returns (data_out, data_out_valid)."""
        if not data_valid:
            return 0, 0

        scram_bit = ((self.lfsr >> 6) & 1) ^ data_in
        b0 = (self.lfsr >> 6) & 1
        b1 = self.lfsr & 1
        b2 = (self.lfsr >> 1) & 1
        b3 = (self.lfsr >> 2) & 1
        b4 = ((self.lfsr >> 3) & 1) ^ ((self.lfsr >> 6) & 1)
        b5 = (self.lfsr >> 4) & 1
        b6 = (self.lfsr >> 5) & 1
        self.lfsr = (b6 << 6) | (b5 << 5) | (b4 << 4) | (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
        return scram_bit, 1


# =====================================================================
# SEARCH_AA Model
# =====================================================================

class SEARCH_AA_Model:
    """32-bit access address detector behavioral model."""

    def __init__(self, access_address: int = 0x123a5456):
        self.aa = access_address if access_address != 0 else 0x123a5456
        self.bit_store = 0
        self.bit_valid_d1 = 0

    def step(self, phy_bit: int = 0, bit_valid: int = 0) -> int:
        """Execute one cycle. Returns hit_flag."""
        self.bit_valid_d1 = bit_valid
        if bit_valid:
            self.bit_store = ((self.bit_store >> 1) | (phy_bit << 31)) & 0xFFFFFFFF
        return 1 if (self.bit_store == self.aa) and self.bit_valid_d1 else 0


# =====================================================================
# GFSK_DEMOD Model
# =====================================================================

class GFSK_DEMOD_Model:
    """GFSK delay-multiply demodulator behavioral model.

    Decision metric: i0*q1 - i1*q0. 3-cycle pipeline latency.
    """

    def __init__(self, bit_width: int = 16):
        self.bit_width = bit_width
        self.i0 = 0
        self.i1 = 0
        self.q0 = 0
        self.q1 = 0
        self.iq_valid_d1 = 0
        self.iq_valid_d2 = 0
        self.iq_valid_d3 = 0
        self.sig_decision = 0

    def step(self, i: int, q: int, iq_valid: int) -> Tuple[int, int, int, int]:
        """Execute one cycle. Returns (phy_bit, bit_valid, sig, sig_valid)."""
        self.iq_valid_d3 = self.iq_valid_d2
        self.iq_valid_d2 = self.iq_valid_d1
        self.iq_valid_d1 = iq_valid

        if iq_valid:
            self.i1 = i
            self.i0 = self.i1
            self.q1 = q
            self.q0 = self.q1

        self.sig_decision = self.i0 * self.q1 - self.i1 * self.q0
        phy_bit = 1 if self.sig_decision > 0 else 0
        return phy_bit, self.iq_valid_d3, self.sig_decision, self.iq_valid_d2


# =====================================================================
# BTLE_RX Model
# =====================================================================

class BTLE_RX_Model:
    """BTLE RX core behavioral model.

    Pipeline: GFSK demod → AA search → descramble → CRC check.
    3-state FSM: IDLE → EXTRACT_LENGTH → CHECK_CRC

    Usage:
        rx = BTLE_RX_Model(access_address=0x8E89BED6, channel=37)
        for i, q, valid in iq_samples:
            rx.step(i, q, valid)
            if rx.decode_end:
                print(f"CRC OK: {rx.crc_ok}, Payload length: {rx.payload_length}")
    """

    def __init__(self, access_address: int = 0x8E89BED6, channel: int = 37,
                 crc_init: int = 0x555555, payload_len_bits: int = 8):
        self.aa = access_address
        self.channel = channel if channel != 0 else 0x3F
        self.crc_init = crc_init
        self.payload_len_bits = payload_len_bits

        self.demod = GFSK_DEMOD_Model()
        self.aa_search = SEARCH_AA_Model(access_address)
        self.crc = CRC24_CORE_Model(crc_init)
        self.scramble = SCRAMBLE_CORE_Model(channel)

        self.state = 0  # 0=IDLE, 1=EXTRACT_LENGTH, 2=CHECK_CRC
        self.bit_count = 0
        self.payload_length = 0
        self.octet = 0
        self.decode_end = False
        self.crc_ok = False
        self.hit_flag = False
        self.octet_valid = False
        self.octet_out = 0

    def step(self, i: int, q: int, iq_valid: int):
        """Execute one RX cycle."""
        # Demodulate
        phy_bit, bit_valid, _, _ = self.demod.step(i, q, iq_valid)

        # AA search (on demod bits)
        hit = self.aa_search.step(phy_bit, bit_valid)
        self.hit_flag = hit

        # Descramble (always runs)
        scramble_out, scramble_valid = self.scramble.step(phy_bit, bit_valid)

        # FSM
        if self.state == 0:  # IDLE
            if hit:
                self.state = 1
                self.bit_count = 0
                self.octet = 0
                # Reset CRC and scramble
                self.crc = CRC24_CORE_Model(self.crc_init)
                self.scramble = SCRAMBLE_CORE_Model(self.channel)
                self.decode_end = False
                self.crc_ok = False

        elif self.state == 1:  # EXTRACT_LENGTH (first 2 octets = header)
            if scramble_valid:
                self.octet = (self.octet >> 1) | (scramble_out << 7)
                self.bit_count += 1
                if self.bit_count >= 16:  # 2 octets
                    self.payload_length = self.octet & 0xFF
                    self.bit_count = 0
                    self.octet = 0
                    self.state = 2

        elif self.state == 2:  # CHECK_CRC
            if scramble_valid:
                self.octet = (self.octet >> 1) | (scramble_out << 7)
                self.bit_count += 1
                # CRC over payload
                self.crc.step(scramble_out, 1)
                total_bits = (self.payload_length + 3) * 8  # header + payload + CRC
                if self.bit_count >= total_bits:
                    self.decode_end = True
                    self.crc_ok = (self.crc.lfsr == 0)
                    self.state = 0

        self.octet_valid = scramble_valid and (self.bit_count % 8 == 0) and (self.bit_count >= 8)
        if self.octet_valid:
            self.octet_out = self.octet


# =====================================================================
# BTLE_TX Model
# =====================================================================

class BTLE_TX_Model:
    """BTLE TX behavioral model.

    4-state FSM: IDLE → TX_PREAMBLE_ACCESS → TX_PDU → WAIT_LAST_SAMPLE

    Usage:
        tx = BTLE_TX_Model(access_address=0x8E89BED6, channel=37)
        tx.load_pdu(pdu_bytes)
        tx.start()
        for _ in range(1000):
            i, q, valid = tx.step()
    """

    def __init__(self, access_address: int = 0x8E89BED6, channel: int = 37,
                 crc_init: int = 0x555555, preamble: int = 0xD6):
        self.aa = access_address
        self.channel = channel
        self.crc_init = crc_init
        self.preamble = preamble
        self.pdu_bytes = bytearray()

        self.state = 0  # 0=IDLE, 1=TX_PREAMBLE_ACCESS, 2=TX_PDU, 3=WAIT
        self.bit_count = 0
        self.bit_count_pa = 0
        self.clk_count = 0
        self.pa_reg = 0
        self.info_bit = 0
        self.info_bit_valid = 0
        self.scramble = SCRAMBLE_CORE_Model(channel)
        self.crc = CRC24_CORE_Model(crc_init)

    def load_pdu(self, pdu: bytes):
        """Load PDU bytes for transmission."""
        self.pdu_bytes = bytearray(pdu)

    def start(self):
        """Start transmission."""
        self.pa_reg = ((self.aa & 0xFFFFFFFF) << 8) | (self.preamble & 0xFF)
        self.bit_count = 0
        self.bit_count_pa = 0
        self.clk_count = 0
        self.state = 1
        self.scramble = SCRAMBLE_CORE_Model(self.channel)
        self.crc = CRC24_CORE_Model(self.crc_init)

    def step(self) -> Tuple[int, int, int, int]:
        """Execute one TX cycle. Returns (i, q, iq_valid, iq_valid_last)."""
        i_out, q_out, valid, valid_last = 0, 0, 0, 0

        if self.state == 0:  # IDLE
            pass
        elif self.state == 1:  # TX_PREAMBLE_ACCESS
            self.clk_count += 1
            if (self.clk_count & 0xF) == 1:
                self.info_bit = self.pa_reg & 1
                self.info_bit_valid = 1
                self.pa_reg = (self.pa_reg >> 1) & ((1 << 40) - 1)
                self.bit_count_pa += 1
                if self.bit_count_pa == 40:
                    self.state = 2
            else:
                self.info_bit_valid = 0

            # GFSK: map bit to I/Q
            if self.info_bit_valid:
                i_out = 50 if self.info_bit else -50
                q_out = 0
                valid = 1

        elif self.state == 2:  # TX_PDU
            self.clk_count += 1
            if (self.clk_count & 0xF) == 1:
                # Serialize PDU bytes LSB first
                byte_idx = self.bit_count // 8
                bit_idx = self.bit_count % 8
                if byte_idx < len(self.pdu_bytes):
                    self.info_bit = (self.pdu_bytes[byte_idx] >> bit_idx) & 1
                else:
                    self.info_bit = 0
                self.info_bit_valid = 1
                self.bit_count += 1

                # Scramble and CRC after 40 bits
                if self.bit_count_pa >= 40:
                    self.scramble.step(self.info_bit, 1)
                    self.crc.step(self.info_bit, 1)

                total_bits = (len(self.pdu_bytes) + 2) * 8  # header + payload
                if self.bit_count >= total_bits:
                    self.info_bit_valid_last = 1
                    self.state = 3
            else:
                self.info_bit_valid = 0

            if self.info_bit_valid:
                i_out = 50 if self.info_bit else -50
                q_out = 0
                valid = 1

        elif self.state == 3:  # WAIT_LAST_SAMPLE
            valid = 0
            valid_last = 1
            self.state = 0

        return i_out, q_out, valid, valid_last
