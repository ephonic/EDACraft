"""
rtlgen.dpi_runtime — Python reference models exposed to SV/UVM via DPI.

Any function decorated with @sv_dpi from rtlgen.pyuvm is automatically
registered here so that the C DPI bridge can find it at runtime.
"""

import hashlib
from rtlgen.pyuvm import sv_dpi

_REGISTRY: dict = {}


def register(name: str, func):
    """Register a Python function as a DPI-callable reference model."""
    _REGISTRY[name] = func


def call(name: str, *args, **kwargs):
    """Dispatch a DPI call to the registered Python function."""
    func = _REGISTRY.get(name)
    if func is None:
        raise RuntimeError(f"DPI function '{name}' not found in rtlgen.dpi_runtime registry")
    return func(*args, **kwargs)


def is_registered(name: str) -> bool:
    return name in _REGISTRY


@sv_dpi(c_decl='import "DPI-C" function void dpi_sha3_256(input longint block[17], input int len, output longint hash[4]);')
def dpi_sha3_256(block_arr=None, msg_len=None, hash_arr=None):
    """Python reference model for SHA3-256 (single-block messages).

    Dual-interface:
      - C DPI bridge calls with a single bytes object (block_arr is bytes).
      - Python scoreboard calls with (block_arr, msg_len, hash_arr).
    """
    if isinstance(block_arr, bytes):
        return hashlib.sha3_256(block_arr).digest()

    msg = 0
    for i in range(17):
        msg |= block_arr[i] << (i * 64)
    msg_bytes = msg.to_bytes(17 * 8, 'little')[:msg_len]
    digest = hashlib.sha3_256(msg_bytes).digest()
    for i in range(4):
        hash_arr[i] = int.from_bytes(digest[i * 8:(i + 1) * 8], 'little')


# ---------------------------------------------------------------------------
# 8b10b Decoder reference model
# ---------------------------------------------------------------------------

def _build_decoder_luts():
    """Build 8b10b lookup tables."""
    control_lut = {
        0b001111_0100: 0b000_11100, 0b110000_1011: 0b000_11100,
        0b001111_1001: 0b001_11100, 0b110000_0110: 0b001_11100,
        0b001111_0101: 0b010_11100, 0b110000_1010: 0b010_11100,
        0b001111_0011: 0b011_11100, 0b110000_1100: 0b011_11100,
        0b001111_0010: 0b100_11100, 0b110000_1101: 0b100_11100,
        0b001111_1010: 0b101_11100, 0b110000_0101: 0b101_11100,
        0b001111_0110: 0b110_11100, 0b110000_1001: 0b110_11100,
        0b001111_1000: 0b111_11100, 0b110000_0111: 0b111_11100,
        0b111010_1000: 0b111_10111, 0b000101_0111: 0b111_10111,
        0b110110_1000: 0b111_11011, 0b001001_0111: 0b111_11011,
        0b101110_1000: 0b111_11101, 0b010001_0111: 0b111_11101,
        0b011110_1000: 0b111_11110, 0b100001_0111: 0b111_11110,
    }
    data5_lut = {
        0b100111: 0b00000, 0b011000: 0b00000,
        0b011101: 0b00001, 0b100010: 0b00001,
        0b101101: 0b00010, 0b010010: 0b00010,
        0b110001: 0b00011,
        0b110101: 0b00100, 0b001010: 0b00100,
        0b101001: 0b00101,
        0b011001: 0b00110,
        0b111000: 0b00111, 0b000111: 0b00111,
        0b111001: 0b01000, 0b000110: 0b01000,
        0b100101: 0b01001,
        0b010101: 0b01010,
        0b110100: 0b01011,
        0b001101: 0b01100,
        0b101100: 0b01101,
        0b011100: 0b01110,
        0b010111: 0b01111, 0b101000: 0b01111,
        0b011011: 0b10000, 0b100100: 0b10000,
        0b100011: 0b10001,
        0b010011: 0b10010,
        0b110010: 0b10011,
        0b001011: 0b10100,
        0b101010: 0b10101,
        0b011010: 0b10110,
        0b111010: 0b10111, 0b000101: 0b10111,
        0b110011: 0b11000, 0b001100: 0b11000,
        0b100110: 0b11001,
        0b010110: 0b11010,
        0b110110: 0b11011, 0b001001: 0b11011,
        0b001110: 0b11100,
        0b101110: 0b11101, 0b010001: 0b11101,
        0b011110: 0b11110, 0b100001: 0b11110,
        0b101011: 0b11111, 0b010100: 0b11111,
    }
    data3_lut = {
        0b0100: 0b000, 0b1011: 0b000,
        0b1001: 0b001,
        0b0101: 0b010,
        0b0011: 0b011, 0b1100: 0b011,
        0b0010: 0b100, 0b1101: 0b100,
        0b1010: 0b101,
        0b0110: 0b110,
        0b1110: 0b111, 0b0001: 0b111,
    }
    d5 = {}
    for pat, val in data5_lut.items():
        d5[pat] = val
    d3 = {}
    for pat, val in data3_lut.items():
        d3[pat] = val
    data_lut = {}
    for upper in range(1 << 6):
        for lower in range(1 << 4):
            ten = (upper << 4) | lower
            if upper in d5 and lower in d3:
                data_lut[ten] = (d3[lower] << 5) | d5[upper]
    return control_lut, data_lut


_CONTROL_LUT_8B10B, _DATA_LUT_8B10B = _build_decoder_luts()

# Rebuild sub-table lookups for exact DUT matching
_D5_LUT_8B10B = {}
_D3_LUT_8B10B = {}
for _upper in range(1 << 6):
    for _lower in range(1 << 4):
        _ten = (_upper << 4) | _lower
        if _ten in _DATA_LUT_8B10B:
            _D5_LUT_8B10B[_upper] = _DATA_LUT_8B10B[_ten] & 0x1F
            _D3_LUT_8B10B[_lower] = (_DATA_LUT_8B10B[_ten] >> 5) & 0x7


@sv_dpi(c_decl='import "DPI-C" function void dpi_decoder_8b10b_ref(input int decoder_in, input int control_in, output int decoder_out, output int control_out);')
def dpi_decoder_8b10b_ref(decoder_in=None, control_in=None, decoder_out_arr=None, control_out_arr=None):
    """Python reference model for 8b10b decoder.

    Python scoreboard calls with (decoder_in, control_in, [0], [0]).
    C DPI bridge calls with primitive values and writes back through pointers.
    """
    if control_in:
        out = _CONTROL_LUT_8B10B.get(decoder_in, 0)
        ctrl = 1
    else:
        upper = (decoder_in >> 4) & 0x3F
        lower = decoder_in & 0xF
        d5 = _D5_LUT_8B10B.get(upper, 0)
        d3 = _D3_LUT_8B10B.get(lower, 0)
        out = (d3 << 5) | d5
        ctrl = 0
    if decoder_out_arr is not None:
        decoder_out_arr[0] = out
    if control_out_arr is not None:
        control_out_arr[0] = ctrl
