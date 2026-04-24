#!/usr/bin/env python3
"""
8b10b Decoder Module.

Converts a 10-bit encoded word into an 8-bit symbol.
- control_in=1 : control symbol lookup
- control_in=0 : data symbol via 5b/6b + 3b/4b decoding tables

Latency: 1 clock cycle (registered output).
"""

import sys

sys.path.insert(0, "/home/yangfan/EDAClaw/rtlgen")

from rtlgen import Module, Input, Output, Wire, Reg, Switch, If, Else, Cat
from rtlgen import VerilogEmitter

# ---------------------------------------------------------------------------
# Decoding tables
# ---------------------------------------------------------------------------

CONTROL_TABLE = [
    # (10-bit pattern, 8-bit output)
    (0b001111_0100, 0b000_11100),  # K.28.0
    (0b110000_1011, 0b000_11100),  # K.28.0
    (0b001111_1001, 0b001_11100),  # K.28.1
    (0b110000_0110, 0b001_11100),  # K.28.1
    (0b001111_0101, 0b010_11100),  # K.28.2
    (0b110000_1010, 0b010_11100),  # K.28.2
    (0b001111_0011, 0b011_11100),  # K.28.3
    (0b110000_1100, 0b011_11100),  # K.28.3
    (0b001111_0010, 0b100_11100),  # K.28.4
    (0b110000_1101, 0b100_11100),  # K.28.4
    (0b001111_1010, 0b101_11100),  # K.28.5
    (0b110000_0101, 0b101_11100),  # K.28.5
    (0b001111_0110, 0b110_11100),  # K.28.6
    (0b110000_1001, 0b110_11100),  # K.28.6
    (0b001111_1000, 0b111_11100),  # K.28.7
    (0b110000_0111, 0b111_11100),  # K.28.7
    (0b111010_1000, 0b111_10111),  # K.23.7
    (0b000101_0111, 0b111_10111),  # K.23.7
    (0b110110_1000, 0b111_11011),  # K.27.7
    (0b001001_0111, 0b111_11011),  # K.27.7
    (0b101110_1000, 0b111_11101),  # K.29.7
    (0b010001_0111, 0b111_11101),  # K.29.7
    (0b011110_1000, 0b111_11110),  # K.30.7
    (0b100001_0111, 0b111_11110),  # K.30.7
]

# 5b/6b decoding: upper 6-bit -> 5-bit (EDCBA)
DATA5_TABLE = [
    (0b100111, 0b00000),
    (0b011000, 0b00000),
    (0b011101, 0b00001),
    (0b100010, 0b00001),
    (0b101101, 0b00010),
    (0b010010, 0b00010),
    (0b110001, 0b00011),
    (0b110101, 0b00100),
    (0b001010, 0b00100),
    (0b101001, 0b00101),
    (0b011001, 0b00110),
    (0b111000, 0b00111),
    (0b000111, 0b00111),
    (0b111001, 0b01000),
    (0b000110, 0b01000),
    (0b100101, 0b01001),
    (0b010101, 0b01010),
    (0b110100, 0b01011),
    (0b001101, 0b01100),
    (0b101100, 0b01101),
    (0b011100, 0b01110),
    (0b010111, 0b01111),
    (0b101000, 0b01111),
    (0b011011, 0b10000),
    (0b100100, 0b10000),
    (0b100011, 0b10001),
    (0b010011, 0b10010),
    (0b110010, 0b10011),
    (0b001011, 0b10100),
    (0b101010, 0b10101),
    (0b011010, 0b10110),
    (0b111010, 0b10111),
    (0b000101, 0b10111),
    (0b110011, 0b11000),
    (0b001100, 0b11000),
    (0b100110, 0b11001),
    (0b010110, 0b11010),
    (0b110110, 0b11011),
    (0b001001, 0b11011),
    (0b001110, 0b11100),
    (0b101110, 0b11101),
    (0b010001, 0b11101),
    (0b011110, 0b11110),
    (0b100001, 0b11110),
    (0b101011, 0b11111),
    (0b010100, 0b11111),
]

# 3b/4b decoding: lower 4-bit -> 3-bit (HGF)
DATA3_TABLE = [
    (0b0100, 0b000),
    (0b1011, 0b000),
    (0b1001, 0b001),
    (0b0101, 0b010),
    (0b0011, 0b011),
    (0b1100, 0b011),
    (0b0010, 0b100),
    (0b1101, 0b100),
    (0b1010, 0b101),
    (0b0110, 0b110),
    (0b1110, 0b111),
    (0b0001, 0b111),
]


class Decoder8b10b(Module):
    def __init__(self, name="decoder_8b10b"):
        super().__init__(name)

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk_in = Input(1, "clk_in")
        self.reset_in = Input(1, "reset_in")
        self.control_in = Input(1, "control_in")
        self.decoder_in = Input(10, "decoder_in")
        self.decoder_valid_in = Input(1, "decoder_valid_in")

        self.decoder_out = Output(8, "decoder_out")
        self.decoder_valid_out = Output(1, "decoder_valid_out")
        self.control_out = Output(1, "control_out")

        # ------------------------------------------------------------------
        # Pipeline registers (input capture + output latch)
        # ------------------------------------------------------------------
        self.r_data = Reg(10, "r_data")
        self.r_ctrl = Reg(1, "r_ctrl")
        self.r_valid = Reg(1, "r_valid")

        # Output registers (driven by sequential logic, forwarded to outputs)
        self.decoder_out_reg = Reg(8, "decoder_out_reg")
        self.decoder_valid_out_reg = Reg(1, "decoder_valid_out_reg")
        self.control_out_reg = Reg(1, "control_out_reg")

        # Combinational decode wires
        self.control_dec = Wire(8, "control_dec")
        self.data_dec = Wire(8, "data_dec")
        self.data5 = Wire(5, "data5")
        self.data3 = Wire(3, "data3")

        # ------------------------------------------------------------------
        # Sequential: 1-cycle latency pipeline
        # ------------------------------------------------------------------
        @self.seq(self.clk_in, self.reset_in, reset_async=True)
        def _pipeline():
            with If(self.reset_in == 1):
                self.r_data <<= 0
                self.r_ctrl <<= 0
                self.r_valid <<= 0
                self.decoder_out_reg <<= 0
                self.decoder_valid_out_reg <<= 0
                self.control_out_reg <<= 0
            with Else():
                self.r_data <<= self.decoder_in
                self.r_ctrl <<= self.control_in
                self.r_valid <<= self.decoder_valid_in
                self.decoder_valid_out_reg <<= self.r_valid
                self.control_out_reg <<= self.r_ctrl
                with If(self.r_ctrl == 1):
                    self.decoder_out_reg <<= self.control_dec
                with Else():
                    self.decoder_out_reg <<= self.data_dec

        # ------------------------------------------------------------------
        # Combinational: output forwarding
        # ------------------------------------------------------------------
        @self.comb
        def _output_logic():
            self.decoder_out <<= self.decoder_out_reg
            self.decoder_valid_out <<= self.decoder_valid_out_reg
            self.control_out <<= self.control_out_reg

        # ------------------------------------------------------------------
        # Combinational: control symbol lookup
        # ------------------------------------------------------------------
        @self.comb
        def _decode_control():
            with Switch(self.r_data) as sw:
                for pattern, value in CONTROL_TABLE:
                    with sw.case(pattern):
                        self.control_dec <<= value
                with sw.default():
                    self.control_dec <<= 0

        # ------------------------------------------------------------------
        # Combinational: data symbol lookup (5b/6b + 3b/4b)
        # ------------------------------------------------------------------
        @self.comb
        def _decode_data():
            upper = self.r_data[9:4]
            lower = self.r_data[3:0]

            with Switch(upper) as sw:
                for pattern, value in DATA5_TABLE:
                    with sw.case(pattern):
                        self.data5 <<= value
                with sw.default():
                    self.data5 <<= 0

            with Switch(lower) as sw2:
                for pattern, value in DATA3_TABLE:
                    with sw2.case(pattern):
                        self.data3 <<= value
                with sw2.default():
                    self.data3 <<= 0

            self.data_dec <<= Cat(self.data3, self.data5)


if __name__ == "__main__":
    dut = Decoder8b10b()
    print(VerilogEmitter().emit(dut))
