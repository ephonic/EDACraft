#!/usr/bin/env python3
"""
Combinational Keccak-f[1600] single round (for synthesis demo).

Removes all registers and handshake logic from KeccakRound,
leaving only the Theta -> Rho+Pi -> Chi -> Iota combinational path.

Arrays are flattened to independent Wires for robust BLIF generation.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen.core import Module, Input, Output, Wire
from rtlgen.logic import Const, Cat, Mux

RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

ROT_OFFSETS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]


def rotl64(x, n):
    n = n % 64
    if n == 0:
        return x
    return Cat(x[63 - n : 0], x[63 : 64 - n])


class KeccakRoundComb(Module):
    def __init__(self, name="keccak_round_comb"):
        super().__init__(name)
        self.state_in = Input(1600, "state_in")
        self.round_idx = Input(5, "round_idx")
        self.state_out = Output(1600, "state_out")

        # Round constant
        self.rc = Wire(64, "rc")

        @self.comb
        def _rc_comb():
            rc_val = Const(RC[23], 64)
            for i in range(22, -1, -1):
                rc_val = Mux(self.round_idx == i, Const(RC[i], 64), rc_val)
            self.rc <<= rc_val

        # 25 lanes as independent wires
        self.a = [Wire(64, f"a_{i}") for i in range(25)]
        self.c = [Wire(64, f"c_{x}") for x in range(5)]
        self.d = [Wire(64, f"d_{x}") for x in range(5)]
        self.a_theta = [Wire(64, f"a_theta_{i}") for i in range(25)]
        self.b_rhopi = [Wire(64, f"b_rhopi_{i}") for i in range(25)]
        self.a_chi = [Wire(64, f"a_chi_{i}") for i in range(25)]

        @self.comb
        def _round_comb():
            # Decompose 1600-bit state into 25 lanes
            for idx in range(25):
                base = idx * 64
                self.a[idx] <<= self.state_in[base + 63 : base]

            # Theta
            for x in range(5):
                s = self.a[x]
                for y in range(1, 5):
                    s = s ^ self.a[x + 5 * y]
                self.c[x] <<= s
            for x in range(5):
                xm1 = (x - 1) % 5
                xp1 = (x + 1) % 5
                self.d[x] <<= self.c[xm1] ^ rotl64(self.c[xp1], 1)
            for idx in range(25):
                x = idx % 5
                self.a_theta[idx] <<= self.a[idx] ^ self.d[x]

            # Rho + Pi
            for x in range(5):
                for y in range(5):
                    idx = x + 5 * y
                    new_x = y
                    new_y = (2 * x + 3 * y) % 5
                    new_idx = new_x + 5 * new_y
                    self.b_rhopi[new_idx] <<= rotl64(self.a_theta[idx], ROT_OFFSETS[x][y])

            # Chi
            for x in range(5):
                for y in range(5):
                    idx = x + 5 * y
                    xp1 = (x + 1) % 5
                    xp2 = (x + 2) % 5
                    idx1 = xp1 + 5 * y
                    idx2 = xp2 + 5 * y
                    self.a_chi[idx] <<= self.b_rhopi[idx] ^ (
                        ~self.b_rhopi[idx1] & self.b_rhopi[idx2]
                    )

            # Iota + compose
            lanes = []
            for i in range(25):
                if i == 0:
                    lanes.append(self.a_chi[i] ^ self.rc)
                else:
                    lanes.append(self.a_chi[i])
            self.state_out <<= Cat(*reversed(lanes))


if __name__ == "__main__":
    from rtlgen import VerilogEmitter
    print(VerilogEmitter().emit(KeccakRoundComb()))
