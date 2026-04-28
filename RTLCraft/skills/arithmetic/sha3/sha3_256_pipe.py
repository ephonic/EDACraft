#!/usr/bin/env python3
"""
Fully pipelined SHA3-256 hash core (single-block messages only).

Architecture:
- KeccakRound: one combinational Keccak-f[1600] round with registered output.
- SHA3_256: 24-stage pipeline of KeccakRound via generate-for.
- Hardware padding: accepts a raw message block (up to 135 bytes) and applies
  SHA3-256 padding (0x06 || 10*1) internally.
- Latency: 24 cycles.

Ports:
  clk, rst_n        : clock and active-low async reset
  i_valid, i_ready  : input handshake
  block[1087:0]     : message bytes in little-endian order (byte0 = bits[7:0])
  block_len[7:0]    : number of valid bytes in block (0..135)
  last_block        : must be 1 (single-block only)
  o_valid, o_ready  : output handshake
  hash[255:0]       : resulting SHA3-256 digest (little-endian byte order)
"""

from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import Const, Cat, Mux, If, Else, ForGen, Switch

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


class KeccakRound(Module):
    def __init__(self, name="keccak_round"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.state_in = Input(1600, "state_in")
        self.round_idx = Input(5, "round_idx")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.state_out = Output(1600, "state_out")

        self.valid_reg = Reg(1, "valid_reg")
        self.state_reg = Reg(1600, "state_reg")

        self.ready = Wire(1, "ready")
        self.ready <<= ~self.valid_reg | self.o_ready
        self.i_ready <<= self.ready

        # Round constant
        self.rc = Wire(64, "rc")

        @self.comb
        def _rc_comb():
            with Switch(self.round_idx) as sw:
                for i, rc_val in enumerate(RC):
                    with sw.case(i):
                        self.rc <<= Const(rc_val, 64)

        # Arrays for 5x5 state (flattened index = x + 5*y)
        self.a = Array(64, 25, "a", vtype=Wire)
        self.c = Array(64, 5, "c", vtype=Wire)
        self.d = Array(64, 5, "d", vtype=Wire)
        self.a_theta = Array(64, 25, "a_theta", vtype=Wire)
        self.b_rhopi = Array(64, 25, "b_rhopi", vtype=Wire)
        self.a_chi = Array(64, 25, "a_chi", vtype=Wire)
        self.next_state = Wire(1600, "next_state")

        @self.comb
        def _round_comb():
            # Decompose 1600-bit state into 25 lanes
            with ForGen("idx", 0, 25) as idx:
                base = idx * 64
                self.a[idx] <<= self.state_in[base + 63 : base]

            # Theta (outer loop as ForGen, inner accumulation in Python)
            with ForGen("x", 0, 5) as x:
                s = self.a[x]
                for y in range(1, 5):
                    s = s ^ self.a[x + 5 * y]
                self.c[x] <<= s
            with ForGen("x", 0, 5) as x:
                xm1 = (x - 1) % 5
                xp1 = (x + 1) % 5
                self.d[x] <<= self.c[xm1] ^ rotl64(self.c[xp1], 1)
            with ForGen("idx", 0, 25) as idx:
                x = idx % 5
                self.a_theta[idx] <<= self.a[idx] ^ self.d[x]

            # Rho + Pi (keep Python for because rotl64 needs constant table lookup)
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

            # Iota + compose (lane(0,0) at LSB to match Keccak bit ordering)
            lanes = []
            for i in range(25):
                if i == 0:
                    lanes.append(self.a_chi[i] ^ self.rc)
                else:
                    lanes.append(self.a_chi[i])
            self.next_state <<= Cat(*reversed(lanes))

            self.state_out <<= self.state_reg
            self.o_valid <<= self.valid_reg

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.valid_reg <<= Const(0, 1)
                self.state_reg <<= Const(0, 1600)
            with Else():
                with If(self.ready):
                    self.valid_reg <<= self.i_valid
                    with If(self.i_valid):
                        self.state_reg <<= self.next_state


class SHA3_256(Module):
    def __init__(self, name="sha3_256"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.block = Input(1088, "block")
        self.block_len = Input(8, "block_len")
        self.last_block = Input(1, "last_block")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.hash = Output(256, "hash")

        self.padded_block = Array(8, 136, "padded_block", vtype=Wire)
        self.state_in = Wire(1600, "state_in")

        @self.comb
        def _pad_comb():
            with ForGen("i", 0, 136) as i:
                base = i * 8
                block_slice = self.block[base + 7 : base]
                with If(i == 135):
                    self.padded_block[i] <<= Mux(self.block_len == 135, Const(0x86, 8), Const(0x80, 8))
                with Else():
                    with If(self.block_len == i):
                        self.padded_block[i] <<= Const(0x06, 8)
                    with Else():
                        with If(self.block_len > i):
                            self.padded_block[i] <<= block_slice
                        with Else():
                            self.padded_block[i] <<= Const(0x00, 8)

        @self.comb
        def _state_in_comb():
            self.state_in <<= Cat(Const(0, 512), Cat(*reversed(self.padded_block)))

        NUM_ROUNDS = 24
        self.pipe_state = Array(1600, NUM_ROUNDS + 1, "pipe_state", vtype=Wire)
        self.pipe_valid = Array(1, NUM_ROUNDS + 1, "pipe_valid", vtype=Wire)
        self.pipe_ready = Array(1, NUM_ROUNDS + 1, "pipe_ready", vtype=Wire)

        @self.comb
        def _pipe_input():
            self.pipe_state[0] <<= self.state_in
            self.pipe_valid[0] <<= self.i_valid

        with ForGen("i", 0, NUM_ROUNDS) as i:
            rd = KeccakRound()
            self.instantiate(
                rd,
                "u_round",
                port_map={
                    "clk": self.clk,
                    "rst_n": self.rst_n,
                    "i_valid": self.pipe_valid[i],
                    "i_ready": self.pipe_ready[i],
                    "state_in": self.pipe_state[i],
                    "round_idx": i,
                    "o_valid": self.pipe_valid[i + 1],
                    "o_ready": self.pipe_ready[i + 1],
                    "state_out": self.pipe_state[i + 1],
                },
            )

        self.final_state = Wire(1600, "final_state")

        @self.comb
        def _output_comb():
            self.final_state <<= self.pipe_state[NUM_ROUNDS]
            self.hash <<= self.final_state[255:0]
            self.o_valid <<= self.pipe_valid[NUM_ROUNDS]
            self.pipe_ready[NUM_ROUNDS] <<= self.o_ready
            self.i_ready <<= self.pipe_ready[0]


if __name__ == "__main__":
    from rtlgen import VerilogEmitter
    top = SHA3_256()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
