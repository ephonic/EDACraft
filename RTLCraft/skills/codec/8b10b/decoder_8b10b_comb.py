#!/usr/bin/env python3
"""
Combinational-only 8b10b Decoder (for synthesis demo).

Same decode tables as Decoder8b10b but without pipeline registers,
so the logic can be fully mapped to a standard-cell library that
has no sequential cells.

NOTE: This module manually constructs SwitchNode AST nodes to work
around a CPython 3.12 compiler bug with `with Switch(...) as sw:`
followed by `sw.default()` inside `for` loops.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Wire, Cat
from rtlgen.core import SwitchNode, Assign, Const

# Import tables from the registered decoder
from examples.decoder_8b10b import CONTROL_TABLE, DATA5_TABLE, DATA3_TABLE


class Decoder8b10bComb(Module):
    def __init__(self, name="decoder_8b10b_comb"):
        super().__init__(name)

        self.control_in = Input(1, "control_in")
        self.decoder_in = Input(10, "decoder_in")

        self.decoder_out = Output(8, "decoder_out")
        self.control_out = Output(1, "control_out")

        self.control_dec = Wire(8, "control_dec")
        self.data_dec = Wire(8, "data_dec")
        self.data5 = Wire(5, "data5")
        self.data3 = Wire(3, "data3")

        @self.comb
        def _decode_control():
            sw = SwitchNode(self.decoder_in._expr)
            for pattern, value in CONTROL_TABLE:
                sw.cases.append((
                    Const(value=pattern, width=10),
                    [Assign(self.control_dec, Const(value=value, width=8), blocking=False)],
                ))
            sw.default_body = [Assign(self.control_dec, Const(value=0, width=8), blocking=False)]
            # Manually append the SwitchNode to the comb block body
            self._comb_blocks[-1].append(sw)

        @self.comb
        def _decode_data():
            upper = self.decoder_in[9:4]
            lower = self.decoder_in[3:0]

            sw_upper = SwitchNode(upper._expr)
            for pattern, value in DATA5_TABLE:
                sw_upper.cases.append((
                    Const(value=pattern, width=6),
                    [Assign(self.data5, Const(value=value, width=5), blocking=False)],
                ))
            sw_upper.default_body = [Assign(self.data5, Const(value=0, width=5), blocking=False)]
            self._comb_blocks[-1].append(sw_upper)

            sw_lower = SwitchNode(lower._expr)
            for pattern, value in DATA3_TABLE:
                sw_lower.cases.append((
                    Const(value=pattern, width=4),
                    [Assign(self.data3, Const(value=value, width=3), blocking=False)],
                ))
            sw_lower.default_body = [Assign(self.data3, Const(value=0, width=3), blocking=False)]
            self._comb_blocks[-1].append(sw_lower)

            self.data_dec <<= Cat(self.data3, self.data5)

        @self.comb
        def _mux():
            sw = SwitchNode(self.control_in._expr)
            sw.cases.append((
                Const(value=1, width=1),
                [Assign(self.decoder_out, self.control_dec._expr, blocking=False)],
            ))
            sw.default_body = [Assign(self.decoder_out, self.data_dec._expr, blocking=False)]
            self._comb_blocks[-1].append(sw)
            self.control_out <<= self.control_in


if __name__ == "__main__":
    from rtlgen import VerilogEmitter
    print(VerilogEmitter().emit(Decoder8b10bComb()))
