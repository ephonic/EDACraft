# btle — Bluetooth Low Energy Controller Skill

## Overview

BTLE PHY transceiver using the Spec2RTL flow.
GFSK modulation/demodulation, CRC-24, data whitening, access address detection,
and TX/RX datapaths at 1Mbps (BLE 1M PHY).

Reference RTL: `ref_rtl/BTLE` (open-source BLE transceiver by Xianjun Jiao).

## Modules

| File | Description |
|------|-------------|
| `behaviors.py` | 14 behavior templates (crc24_core, scramble_core, access_address_detect, gfsk_demod, gauss_filter, bit_upsampler, sdpram, crc_wrapper, scramble_wrapper, vco, gfsk_mod, btle_rx_core, btle_tx, btle_phy) |
| `models.py` | CRC24_CORE_Model, SCRAMBLE_CORE_Model, GFSK_DEMOD_Model, BTLE_RX_Model, BTLE_TX_Model + ble_crc24/ble_whiten helpers |
| `arch_templates.py` | build_btle_arch(), BTLE_ControllerModel |
| `skeleton_templates.py` | PE type → implementation steps (14 PE types) |

## Quick Start

### Build Architecture

```python
from skills.interfaces.btle.arch_templates import build_btle_arch
from skills.interfaces.btle import BLE_AA_ADVERTISING

arch = build_btle_arch(
    access_address=BLE_AA_ADVERTISING,
    channel=37,
    crc_init=0x555555,
)
```

### Golden Reference Verification

```python
from skills.interfaces.btle.models import (
    BTLE_RX_Model, BTLE_TX_Model, ble_crc24, ble_whiten
)

# CRC-24 computation
data_bits = [0, 1, 0, 1, ...]
crc = ble_crc24(data_bits, crc_init=0x555555)

# Data whitening
scrambled = ble_whiten(data_bits, channel=37)

# RX core simulation
rx = BTLE_RX_Model(access_address=0x8E89BED6, channel=37)
for i, q, valid in iq_samples:
    rx.step(i, q, valid)
    if rx.decode_end:
        print(f"CRC OK: {rx.crc_ok}")

# TX simulation
tx = BTLE_TX_Model(access_address=0x8E89BED6, channel=37)
tx.load_pdu(pdu_bytes)
tx.start()
for _ in range(1000):
    i, q, valid, last = tx.step()
```

## BTLE Pipeline Stages

| Stage | pe_type | Description | Latency |
|-------|---------|-------------|---------|
| CRC24_CORE | crc24_core | BLE CRC-24 LFSR (taps 0,1,3,4,6,9,10) | 1 cycle/bit |
| SCRAMBLE_CORE | scramble_core | Data whitening LFSR (x^7+x^4+1) | 1 cycle/bit |
| SEARCH_AA | access_address_detect | 32-bit access address detector | 1 cycle |
| GFSK_DEMOD | gfsk_demod | Delay-multiply frequency discriminator | 3 cycles |
| GAUSS_FILTER | gauss_filter | 17-tap Gaussian FIR (BT=0.5) | 1 cycle |
| BIT_REPEAT | bit_upsampler | 1M→8M bit upsampler (16MHz clk) | Variable |
| SDPRAM | sdpram | Simple dual-port RAM (single/dual clock) | 1 cycle read |
| CRC_WRAPPER | crc_wrapper | CRC wrapper (skip 40-bit preamble+AA) | Variable |
| SCRAMBLE_WRAPPER | scramble_wrapper | Whitening wrapper (skip 40-bit preamble+AA) | Variable |
| VCO | vco | Phase accumulator + sin/cos ROM lookup | 1 cycle |
| GFSK_MOD | gfsk_mod | Full modulator: upsample→FIR→VCO | Multi-cycle |
| BTLE_RX_CORE | btle_rx_core | RX FSM: IDLE→EXTRACT_LENGTH→CHECK_CRC | Variable |
| BTLE_TX | btle_tx | TX FSM: IDLE→TX_PREAMBLE_ACCESS→TX_PDU→WAIT | Variable |
| BTLE_PHY | btle_phy | PHY wrapper combining TX + RX | Variable |

## BLE Frame Format

```
| Preamble (8b) | Access Address (32b) | PDU Header (16b) | Payload (0-251B) | CRC (24b) |
```

- **Preamble**: 0xD6 (if AA ends in 0) or 0x71 (if AA ends in 1)
- **Access Address**: 32-bit, standard advertising = 0x8E89BED6
- **PDU Header**: 8-bit header + 8-bit length
- **CRC**: CRC-24/BLUETOOTH, init = 0x555555
- **Data Whitening**: LFSR seeded with {1, channel_number[5:0]}

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| ACCESS_ADDRESS | 0x8E89BED6 | Standard BLE advertising AA |
| PREAMBLE | 0xD6 | 8-bit preamble pattern |
| CRC_INIT | 0x555555 | CRC-24 initialization value |
| CRC_WIDTH | 24 | CRC state bit width |
| CHANNEL | 37 | BLE channel number (0-39) |
| DEMOD_WIDTH | 16 | GFSK demodulator I/Q width |
| VCO_WIDTH | 16 | VCO phase accumulator width |
| ROM_ADDR_WIDTH | 11 | sin/cos ROM address width (2048 entries) |
| IQ_WIDTH | 8 | I/Q output width |

## BLE CRC-24 Polynomial

Polynomial taps at bit positions: 0, 1, 3, 4, 6, 9, 10

```
LFSR update per bit:
  new_bit = lfsr[23] ^ data_in
  lfsr[0]  = new_bit
  lfsr[1]  = lfsr[0] ^ new_bit
  lfsr[2]  = lfsr[1]
  lfsr[3]  = lfsr[2] ^ new_bit
  lfsr[4]  = lfsr[3] ^ new_bit
  lfsr[5]  = lfsr[4]
  lfsr[6]  = lfsr[5] ^ new_bit
  lfsr[7]  = lfsr[6]
  lfsr[8]  = lfsr[7]
  lfsr[9]  = lfsr[8] ^ new_bit
  lfsr[10] = lfsr[9] ^ new_bit
  lfsr[23:11] = lfsr[22:10]
```

## Data Whitening LFSR

Polynomial: x^7 + x^4 + 1

```
LFSR update per bit:
  bit[0] = lfsr[6]
  bit[1] = lfsr[0]
  bit[2] = lfsr[1]
  bit[3] = lfsr[2]
  bit[4] = lfsr[3] ^ lfsr[6]
  bit[5] = lfsr[4]
  bit[6] = lfsr[5]

  data_out = lfsr[6] ^ data_in
```

Init value: {MSB=1, channel_number[5:0]}

## GFSK Modulation

- **Frequency deviation**: ±250 kHz for BLE 1M PHY
- **BT product**: 0.5 (Gaussian filter bandwidth-time product)
- **Modulation index**: 0.5
- **Sampling rate**: 16 MHz (8 samples per symbol at 1Msps)

TX Pipeline:
1. `bit_repeat_upsample`: 1M → 8M (8 samples/bit)
2. `gauss_filter`: 17-tap Gaussian FIR pulse shaping
3. `vco`: Phase accumulator + sin/cos ROM lookup → I/Q output

RX Pipeline:
1. `gfsk_demodulation`: Delay-multiply discriminator → phy_bit
2. `search_unique_bit_seq`: 32-bit AA detection
3. `scramble_core`: Descrambling
4. `crc24_core`: CRC verification
