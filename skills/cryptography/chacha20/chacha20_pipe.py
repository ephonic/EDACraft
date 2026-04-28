#!/usr/bin/env python3
"""
Fully pipelined ChaCha20 stream cipher core.

Architecture:
- Quarter-round is a pure combinational submodule (human-engineer style).
- Each round is a 2-stage pipeline module (column + diagonal) with handshaking.
- 20 rounds are cascaded.
- Stage 0 (init) builds the initial 512-bit matrix and drives the first round.
- Stage 21 (final) adds init_state and XORs with din.

Target: 12nm @ 1GHz.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import Const, Cat, Mux, Split, If, Else, ForGen

# ---------------------------------------------------------------------------
# Quarter-round: pure combinational block
# ---------------------------------------------------------------------------
class Chacha20QuarterRound(Module):
    """Single ChaCha quarter-round (steps 1-12), combinational."""

    def __init__(self):
        super().__init__("chacha20rng_quarterround")
        self.ai = Input(32, "ai")
        self.bi = Input(32, "bi")
        self.ci = Input(32, "ci")
        self.di = Input(32, "di")
        self.a = Output(32, "a")
        self.b = Output(32, "b")
        self.c = Output(32, "c")
        self.d = Output(32, "d")

        self.step1 = Wire(32, "step1")
        self.step2 = Wire(32, "step2")
        self.step3 = Wire(32, "step3")
        self.step4 = Wire(32, "step4")
        self.step5 = Wire(32, "step5")
        self.step6 = Wire(32, "step6")
        self.step7 = Wire(32, "step7")
        self.step8 = Wire(32, "step8")
        self.step9 = Wire(32, "step9")
        self.step10 = Wire(32, "step10")
        self.step11 = Wire(32, "step11")
        self.step12 = Wire(32, "step12")

        @self.comb
        def _qr_comb():
            s1 = self.step1
            s2 = self.step2
            s3 = self.step3
            s4 = self.step4
            s5 = self.step5
            s6 = self.step6
            s7 = self.step7
            s8 = self.step8
            s9 = self.step9
            s10 = self.step10
            s11 = self.step11
            s12 = self.step12

            s1 <<= self.ai + self.bi
            s2 <<= self.di ^ s1
            s3 <<= Cat(s2[15:0], s2[31:16])
            s4 <<= self.ci + s3
            s5 <<= self.bi ^ s4
            s6 <<= Cat(s5[19:0], s5[31:20])
            s7 <<= s1 + s6
            s8 <<= s3 ^ s7
            s9 <<= Cat(s8[23:0], s8[31:24])
            s10 <<= s9 + s4
            s11 <<= s10 ^ s6
            s12 <<= Cat(s11[24:0], s11[31:25])

            self.a <<= s7
            self.b <<= s12
            self.c <<= s10
            self.d <<= s9


# ---------------------------------------------------------------------------
# Round: 2-stage pipeline with handshaking
# ---------------------------------------------------------------------------
class Chacha20Round(Module):
    """One ChaCha round = column round + diagonal round (2 pipeline stages)."""

    def __init__(self):
        super().__init__("chacha20rng_round")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.xin = Input(512, "xin")
        self.xout = Output(512, "xout")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.init_state_in = Input(512, "init_state_in")
        self.init_state_out = Output(512, "init_state_out")

        # Decompose xin into 16 words
        self.x = Array(32, 16, "x", vtype=Wire)

        # First stage outputs
        self.t_out = Array(32, 16, "t_out", vtype=Wire)
        self.t_out_reg = Array(32, 16, "t_out_reg", vtype=Reg)
        self.stage1_valid = Reg(1, "stage1_valid")
        self.init_state_stage1 = Reg(512, "init_state_stage1")

        # Second stage outputs
        self.xd = Array(32, 16, "xd", vtype=Wire)
        self.xo = Array(32, 16, "xo", vtype=Wire)
        self.xout_t = Reg(512, "xout_t")

        # xin decomposition (unrolled to 16 simple assigns)
        @self.comb
        def _decompose_xin():
            for i in range(16):
                self.x[i] <<= self.xin[i * 32 + 31 : i * 32]

        # xd decomposition (generate for)
        with ForGen("idx", 0, 16) as idx:
            self.xd[idx] <<= self.t_out_reg[idx]

        # Quarter-round instances (stage 1: column) — generate for
        qr = Chacha20QuarterRound()
        with ForGen("idx", 0, 4) as idx:
            self.instantiate(
                qr,
                "u_qr",
                port_map={
                    "ai": self.x[idx],
                    "bi": self.x[idx + 4],
                    "ci": self.x[idx + 8],
                    "di": self.x[idx + 12],
                    "a": self.t_out[idx],
                    "b": self.t_out[idx + 4],
                    "c": self.t_out[idx + 8],
                    "d": self.t_out[idx + 12],
                },
            )

        # Quarter-round instances (stage 2: diagonal)
        for q, (a_idx, b_idx, c_idx, d_idx) in enumerate([(0, 5, 10, 15), (1, 6, 11, 12), (2, 7, 8, 13), (3, 4, 9, 14)]):
            self.instantiate(
                qr,
                f"u_qr_{q+5}",
                port_map={
                    "ai": self.xd[a_idx],
                    "bi": self.xd[b_idx],
                    "ci": self.xd[c_idx],
                    "di": self.xd[d_idx],
                    "a": self.xo[a_idx],
                    "b": self.xo[b_idx],
                    "c": self.xo[c_idx],
                    "d": self.xo[d_idx],
                },
            )

        # Handshake
        @self.comb
        def _round_comb():
            self.i_ready <<= self.o_ready
            self.xout <<= self.xout_t

        # Stage 1 sequential (column round result -> register)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _stage1_seq():
            with If(self.rst_n == 0):
                for i in range(16):
                    self.t_out_reg[i] <<= Const(0, 32)
                self.init_state_stage1 <<= Const(0, 512)
            with Else():
                with If(self.i_valid & self.i_ready):
                    for i in range(16):
                        self.t_out_reg[i] <<= self.t_out[i]
                    self.init_state_stage1 <<= self.init_state_in

        # Stage 2 sequential (diagonal round result -> register)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _stage2_seq():
            with If(self.rst_n == 0):
                self.xout_t <<= Const(0, 512)
                self.init_state_out <<= Const(0, 512)
            with Else():
                with If(self.stage1_valid & self.o_ready):
                    self.xout_t <<= Cat(*reversed([self.xo[i] for i in range(16)]))
                    self.init_state_out <<= self.init_state_stage1

        # Valid pipeline
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _valid_seq1():
            with If(self.rst_n == 0):
                self.stage1_valid <<= Const(0, 1)
            with Else():
                with If(self.o_ready):
                    self.stage1_valid <<= self.i_valid

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _valid_seq2():
            with If(self.rst_n == 0):
                self.o_valid <<= Const(0, 1)
            with Else():
                with If(self.o_ready):
                    self.o_valid <<= self.stage1_valid


# ---------------------------------------------------------------------------
# Core: cascade 20 rounds
# ---------------------------------------------------------------------------
class Chacha20CorePipe(Module):
    """Fully pipelined ChaCha20 core (20 rounds)."""

    def __init__(self, name="Chacha20CorePipe"):
        super().__init__(name)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.seed = Input(256, "seed")
        self.stream_id = Input(64, "stream_id")
        self.counter = Input(64, "counter")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.o_ready = Input(1, "o_ready")

        self.state = Output(512, "state")
        self.o_valid = Output(1, "o_valid")

        NUM_ROUNDS = 20
        CONSTANTS = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]

        # Build initial state (combinational)
        self.init_state = Wire(512, "init_state")
        self.init_valid = Wire(1, "init_valid")

        @self.comb
        def _init_comb():
            key_words = Split(self.seed, 32)
            counter_words = Split(self.counter, 32)
            nonce_words = Split(self.stream_id, 32)
            words = []
            for i in range(16):
                if i < 4:
                    val = Const(CONSTANTS[i], 32)
                elif i < 12:
                    val = key_words[i - 4]
                elif i == 12:
                    val = counter_words[0]
                elif i == 13:
                    val = counter_words[1]
                elif i == 14:
                    val = nonce_words[0]
                else:
                    val = nonce_words[1]
                words.append(val)
            self.init_state <<= Cat(*reversed(words))
            self.init_valid <<= self.i_valid

        # Pipeline signals
        self.xin = Array(512, NUM_ROUNDS + 1, "xin", vtype=Wire)
        self.xout = Array(512, NUM_ROUNDS, "xout", vtype=Wire)
        self.stage_valid = Array(1, NUM_ROUNDS + 1, "stage_valid", vtype=Wire)
        self.stage_ready = Array(1, NUM_ROUNDS + 1, "stage_ready", vtype=Wire)
        self.init_state_stage = Array(512, NUM_ROUNDS + 1, "init_state_stage", vtype=Wire)

        # Input to first stage
        @self.comb
        def _pipeline_input():
            self.xin[0] <<= self.init_state
            self.stage_valid[0] <<= self.i_valid
            self.init_state_stage[0] <<= self.init_state

        # Instantiate 20 rounds via generate-for
        with ForGen("i", 0, NUM_ROUNDS) as i:
            rd = Chacha20Round()
            self.instantiate(
                rd,
                "inst",
                port_map={
                    "clk": self.clk,
                    "rst_n": self.rst_n,
                    "i_valid": self.stage_valid[i],
                    "i_ready": self.stage_ready[i],
                    "xin": self.xin[i],
                    "xout": self.xout[i],
                    "o_valid": self.stage_valid[i + 1],
                    "o_ready": self.stage_ready[i + 1],
                    "init_state_in": self.init_state_stage[i],
                    "init_state_out": self.init_state_stage[i + 1],
                },
            )
            self.xin[i + 1] <<= self.xout[i]

        # Final stage: add init_state
        self.final_xout = Wire(512, "final_xout")
        self.final_init = Wire(512, "final_init")
        self.final_valid = Wire(1, "final_valid")

        @self.comb
        def _extract_final():
            self.final_xout <<= self.xout[NUM_ROUNDS - 1]
            self.final_init <<= self.init_state_stage[NUM_ROUNDS]
            self.final_valid <<= self.stage_valid[NUM_ROUNDS]

        self.final_state = Wire(512, "final_state")
        @self.comb
        def _final_comb():
            words = []
            for i in range(16):
                st_word = self.final_xout[i * 32 + 31 : i * 32]
                init_word = self.final_init[i * 32 + 31 : i * 32]
                words.append(st_word + init_word)
            self.final_state <<= Cat(*reversed(words))

        # Register outputs
        self.state_reg = Reg(512, "state_reg")
        self.vout_reg = Reg(1, "o_valid_reg")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _output_seq():
            with If(self.rst_n == 0):
                self.state_reg <<= Const(0, 512)
                self.vout_reg <<= Const(0, 1)
            with Else():
                self.state_reg <<= self.final_state
                self.vout_reg <<= self.final_valid

        @self.comb
        def _output_assign():
            self.state <<= self.state_reg
            self.o_valid <<= self.vout_reg
            self.i_ready <<= self.stage_ready[0]
            self.stage_ready[NUM_ROUNDS] <<= self.o_ready


# ---------------------------------------------------------------------------
# Top-level wrapper
# ---------------------------------------------------------------------------
class chacha20rng(Module):
    def __init__(self, name="chacha20rng"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.seed = Input(256, "seed")
        self.counter = Input(64, "counter")
        self.stream_id = Input(64, "stream_id")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.state = Output(512, "state")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")

        u_core = Chacha20CorePipe("u_core")
        self.instantiate(
            u_core,
            "u_core",
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "seed": self.seed,
                "stream_id": self.stream_id,
                "counter": self.counter,
                "i_valid": self.i_valid,
                "i_ready": self.i_ready,
                "o_ready": self.o_ready,
                "state": self.state,
                "o_valid": self.o_valid,
            },
        )


# ---------------------------------------------------------------------------
# Generate Verilog when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from rtlgen import VerilogEmitter

    top = chacha20rng()
    sv = VerilogEmitter().emit_design(top)
    print(sv)
