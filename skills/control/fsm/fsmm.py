#!/usr/bin/env python3
"""
FSMM — Flexible Sparse Matrix Multiplication Accelerator.

Strict implementation according to ICCAD'24 paper:
  "FSMM: An Efficient Matrix Multiplication Accelerator Supporting Flexible Sparsity"

Parameters:
  Q  = block dimension (default 16, matching the paper)
  DW = data width (default 8)

Architecture:
  - Block outer-product: O = F x W^T
  - q = 16 matrix block size (as specified in paper Section 5.1)
  - 64 PEs, each with 4 multipliers and reconfigurable adder tree
  - 2-stage fully pipelined Computation Unit:
      Stage 1: operand fetch + 256 parallel multipliers
      Stage 2: reconfigurable adder tree + out_buf write-back
  - De-Reordering Unit: 128-adder array, 2-cycle pipeline
      Cycle 1: read out_buf columns, apply reordering MUXes to intermediate reg
      Cycle 2: add with accumulation buffer and write back
  - Sparse levels: 1:16, 2:16, 4:16, 8:16, 16:16 (dense)
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Array, LocalParam, Parameter
from rtlgen.logic import If, Else, Switch, Cat, Mux, ForGen
from rtlgen.codegen import VerilogEmitter


def mux_select(candidates, sel):
    """Return candidates[sel] using a binary tree of Mux expressions.

    candidates: list of expressions (length <= 2**sel.width)
    sel       : Signal/Wire expression used as index
    """
    if isinstance(sel, int):
        return candidates[sel]
    sel_bits = [sel[b] for b in range(sel.width)]
    cur = list(candidates)
    pad_len = 1 << len(sel_bits)
    while len(cur) < pad_len:
        cur.append(0)
    cur = cur[:pad_len]
    for sel_bit in sel_bits:
        nxt = []
        for i in range(0, len(cur), 2):
            a = cur[i]
            b = cur[i + 1] if i + 1 < len(cur) else 0
            nxt.append(Mux(sel_bit, b, a))  # sel=0 -> a, sel=1 -> b
        cur = nxt
    return cur[0]


# ---------------------------------------------------------------------------
# Fetch Unit: decode c/k and lookup w_val / w_row (shared across all rows)
# ---------------------------------------------------------------------------
class FSMMFetchUnit(Module):
    def __init__(self, Q: int = 16, DW: int = 8, name: str = "FSMMFetchUnit"):
        super().__init__(name)
        IDXW = max(2, Q.bit_length())

        self.w_reg = Input(Q * Q * DW, "w_reg")
        self.idx_reg = Input(Q * Q * IDXW, "idx_reg")
        self.p1_base_c = Input(Q.bit_length(), "p1_base_c")
        self.max_k = Input(Q.bit_length(), "max_k")

        self.w_val_vec_flat = Output(Q * DW, "w_val_vec_flat")
        self.w_row_vec_flat = Output(Q * IDXW, "w_row_vec_flat")
        self.c_vec_flat = Output(Q * Q.bit_length(), "c_vec_flat")

        # Decompose flat vectors into columns (kept as simple assigns)
        self.w_col = [Wire(Q * DW, f"w_col_{c}") for c in range(Q)]
        self.idx_col = [Wire(Q * IDXW, f"idx_col_{c}") for c in range(Q)]

        @self.comb
        def _decompose():
            for c in range(Q):
                self.w_col[c] <<= self.w_reg[c * Q * DW + (Q * DW - 1):c * Q * DW]
                self.idx_col[c] <<= self.idx_reg[c * Q * IDXW + (Q * IDXW - 1):c * Q * IDXW]

        # c/k decode arrays
        self.c_vec = Array(Q.bit_length(), Q, "c_vec", vtype=Wire)
        self.k_vec = Array(Q.bit_length(), Q, "k_vec", vtype=Wire)

        @self.comb
        def _c_k_mux():
            with ForGen("i", 0, Q) as i:
                self.c_vec[i] <<= 0
                self.k_vec[i] <<= 0
                with Switch(self.max_k) as sw:
                    with sw.case(1):
                        self.c_vec[i] <<= self.p1_base_c + i
                        self.k_vec[i] <<= 0
                    with sw.case(2):
                        self.c_vec[i] <<= self.p1_base_c + (i >> 1)
                        self.k_vec[i] <<= i & 1
                    with sw.case(4):
                        self.c_vec[i] <<= self.p1_base_c + (i >> 2)
                        self.k_vec[i] <<= i & 3
                    with sw.case(8):
                        self.c_vec[i] <<= self.p1_base_c + (i >> 3)
                        self.k_vec[i] <<= i & 7
                    with sw.default():
                        self.c_vec[i] <<= self.p1_base_c + (i >> 4)
                        self.k_vec[i] <<= i & 15

        # Lookup arrays (inside for-loop to avoid 16 copies of always blocks)
        self.w_col_sel = Array(Q * DW, Q, "w_col_sel", vtype=Wire)
        self.idx_col_sel = Array(Q * IDXW, Q, "idx_col_sel", vtype=Wire)
        self.w_val_vec_arr = Array(DW, Q, "w_val_vec_arr", vtype=Wire)
        self.w_row_vec_arr = Array(IDXW, Q, "w_row_vec_arr", vtype=Wire)

        @self.comb
        def _lookup():
            with ForGen("i", 0, Q) as i:
                self.w_col_sel[i] <<= mux_select(self.w_col, self.c_vec[i])
                self.idx_col_sel[i] <<= mux_select(self.idx_col, self.c_vec[i])
                self.w_val_vec_arr[i] <<= mux_select(
                    [self.w_col_sel[i][k * DW + (DW - 1):k * DW] for k in range(Q)],
                    self.k_vec[i])
                self.w_row_vec_arr[i] <<= mux_select(
                    [self.idx_col_sel[i][k * IDXW + (IDXW - 1):k * IDXW] for k in range(Q)],
                    self.k_vec[i])
                self.w_val_vec_flat[i * DW + (DW - 1):i * DW] <<= self.w_val_vec_arr[i]
                self.w_row_vec_flat[i * IDXW + (IDXW - 1):i * IDXW] <<= self.w_row_vec_arr[i]
                self.c_vec_flat[i * Q.bit_length() + (Q.bit_length() - 1):i * Q.bit_length()] <<= self.c_vec[i]


# ---------------------------------------------------------------------------
# Row Compute Engine: one row of multipliers + P2 accumulation + out_buf update
# ---------------------------------------------------------------------------
class FSMMRowEngine(Module):
    def __init__(self, Q: int = 16, DW: int = 8, name: str = "FSMMRowEngine"):
        super().__init__(name)
        IDXW = max(2, Q.bit_length())
        MULT_PER_ROW = 16

        self.ROW_IDX = Parameter(0, "ROW_IDX")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.f_reg = Input(Q * Q * DW, "f_reg")
        self.w_val_vec_flat = Input(Q * DW, "w_val_vec_flat")
        self.w_row_vec_flat = Input(Q * IDXW, "w_row_vec_flat")
        self.c_vec_flat = Input(Q * Q.bit_length(), "c_vec_flat")
        self.p1_valid = Input(1, "p1_valid")
        self.p2_valid = Input(1, "p2_valid")
        self.p2_base_c = Input(Q.bit_length(), "p2_base_c")
        self.batch_cols = Input(Q.bit_length(), "batch_cols")
        self.max_k = Input(Q.bit_length(), "max_k")
        self.out_buf = Input(Q * Q * DW, "out_buf")
        self.out_buf_next_row = Output(Q * DW, "out_buf_next_row")

        # Extract f_row and out_row using parameter ROW_IDX
        self.f_row = Wire(Q * DW, "f_row")
        self.out_row = Wire(Q * DW, "out_row")

        @self.comb
        def _extract_rows():
            base = self.ROW_IDX * Q * DW
            self.f_row <<= self.f_reg[base + (Q * DW - 1):base]
            self.out_row <<= self.out_buf[base + (Q * DW - 1):base]

        # Unpack flat vectors
        self.w_val_vec = Array(DW, Q, "w_val_vec", vtype=Wire)
        self.w_row_vec = Array(IDXW, Q, "w_row_vec", vtype=Wire)
        self.c_vec = Array(Q.bit_length(), Q, "c_vec", vtype=Wire)

        @self.comb
        def _unpack():
            with ForGen("i", 0, Q) as i:
                self.w_val_vec[i] <<= self.w_val_vec_flat[i * DW + (DW - 1):i * DW]
                self.w_row_vec[i] <<= self.w_row_vec_flat[i * IDXW + (IDXW - 1):i * IDXW]
                self.c_vec[i] <<= self.c_vec_flat[i * Q.bit_length() + (Q.bit_length() - 1):i * Q.bit_length()]

        # f_val lookup
        self.f_val_vec = Array(DW, Q, "f_val_vec", vtype=Wire)

        @self.comb
        def _f_lookup():
            with ForGen("i", 0, Q) as i:
                self.f_val_vec[i] <<= mux_select(
                    [self.f_row[t * DW + (DW - 1):t * DW] for t in range(Q)],
                    self.w_row_vec[i])

        # Multipliers
        self.mul_wire = Array(DW * 2, Q, "mul_wire", vtype=Wire)
        self.mul_reg = Array(DW * 2, Q, "mul_reg", vtype=Reg)

        @self.comb
        def _p1_mult():
            with ForGen("i", 0, Q) as i:
                self.mul_wire[i] <<= 0
                with If(self.p1_valid):
                    with If(self.c_vec[i] < Q):
                        self.mul_wire[i] <<= self.f_val_vec[i] * self.w_val_vec[i]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_mul():
            with If(self.rst_n == 0):
                with ForGen("i", 0, Q) as i:
                    self.mul_reg[i] <<= 0
            with Else():
                with ForGen("i", 0, Q) as i:
                    self.mul_reg[i] <<= self.mul_wire[i]

        # P2 accumulation
        self.p2_sum = Array(DW * 2, Q, "p2_sum", vtype=Wire)

        @self.comb
        def _p2_select():
            with ForGen("j", 0, Q) as j:
                self.p2_sum[j] <<= 0
            with If(self.p2_valid):
                with ForGen("j", 0, Q) as j:
                    c = self.p2_base_c + j
                    with If(c < Q):
                        s = Wire(DW * 2, "p2s")
                        s <<= 0
                        with Switch(self.max_k) as sw:
                            with sw.case(1):
                                s <<= self.mul_reg[j]
                            with sw.case(2):
                                with If(j < 8):
                                    s <<= (self.mul_reg[j * 2 + 0] +
                                           self.mul_reg[j * 2 + 1])
                            with sw.case(4):
                                with If(j < 4):
                                    s <<= (self.mul_reg[j * 4 + 0] +
                                           self.mul_reg[j * 4 + 1] +
                                           self.mul_reg[j * 4 + 2] +
                                           self.mul_reg[j * 4 + 3])
                            with sw.case(8):
                                with If(j < 2):
                                    s <<= (self.mul_reg[j * 8 + 0] +
                                           self.mul_reg[j * 8 + 1] +
                                           self.mul_reg[j * 8 + 2] +
                                           self.mul_reg[j * 8 + 3] +
                                           self.mul_reg[j * 8 + 4] +
                                           self.mul_reg[j * 8 + 5] +
                                           self.mul_reg[j * 8 + 6] +
                                           self.mul_reg[j * 8 + 7])
                            with sw.default():
                                with If(j < 1):
                                    s0 = (self.mul_reg[j * 16 + 0] +
                                          self.mul_reg[j * 16 + 1] +
                                          self.mul_reg[j * 16 + 2] +
                                          self.mul_reg[j * 16 + 3])
                                    s1 = (self.mul_reg[j * 16 + 4] +
                                          self.mul_reg[j * 16 + 5] +
                                          self.mul_reg[j * 16 + 6] +
                                          self.mul_reg[j * 16 + 7])
                                    s2 = (self.mul_reg[j * 16 + 8] +
                                          self.mul_reg[j * 16 + 9] +
                                          self.mul_reg[j * 16 + 10] +
                                          self.mul_reg[j * 16 + 11])
                                    s3 = (self.mul_reg[j * 16 + 12] +
                                          self.mul_reg[j * 16 + 13] +
                                          self.mul_reg[j * 16 + 14] +
                                          self.mul_reg[j * 16 + 15])
                                    s <<= s0 + s1 + s2 + s3
                        self.p2_sum[j] <<= s

        # out_buf_next_row
        self.obn_elem = Array(DW, Q, "obn_elem", vtype=Wire)

        @self.comb
        def _out_buf_update():
            with ForGen("c", 0, Q) as c:
                self.obn_elem[c] <<= self.out_row[c * DW + (DW - 1):c * DW]
                with If(self.p2_valid):
                    with If((c >= self.p2_base_c) & (c < self.p2_base_c + self.batch_cols)):
                        with Switch(c - self.p2_base_c) as sw2:
                            for j in range(Q):
                                with sw2.case(j):
                                    self.obn_elem[c] <<= self.p2_sum[j][DW - 1:0]
            self.out_buf_next_row <<= Cat(*[self.obn_elem[i] for i in range(Q - 1, -1, -1)])


# ---------------------------------------------------------------------------
# De-Reorder Row Engine: one row of the 128-adder de-reordering unit
# ---------------------------------------------------------------------------
class FSMMDrRowEngine(Module):
    def __init__(self, Q: int = 16, DW: int = 8, name: str = "FSMMDrRowEngine"):
        super().__init__(name)
        IDXW = max(2, Q.bit_length())

        self.ROW_IDX = Parameter(0, "ROW_IDX")
        self.out_acc_buf = Input(Q * Q * DW, "out_acc_buf")
        self.out_buf = Input(Q * Q * DW, "out_buf")
        self.reorder_reg = Input(Q * IDXW, "reorder_reg")
        self.dr_cnt = Input(1, "dr_cnt")
        self.dr_en = Input(1, "dr_en")
        self.out_acc_buf_next_row = Output(Q * DW, "out_acc_buf_next_row")

        self.out_acc_row = Wire(Q * DW, "out_acc_row")
        self.out_row = Wire(Q * DW, "out_row")

        @self.comb
        def _extract_rows():
            base = self.ROW_IDX * Q * DW
            self.out_acc_row <<= self.out_acc_buf[base + (Q * DW - 1):base]
            self.out_row <<= self.out_buf[base + (Q * DW - 1):base]

        self.dr_add_val = Array(DW, Q // 2, "dr_add_val", vtype=Wire)

        @self.comb
        def _dr_add():
            with ForGen("j", 0, Q // 2) as j:
                c0 = j
                c1 = j + Q // 2
                add0 = self.out_row[c0 * DW + (DW - 1):c0 * DW]
                add1 = self.out_row[c1 * DW + (DW - 1):c1 * DW]
                self.dr_add_val[j] <<= Mux(self.dr_cnt, add1, add0)

        self.acc_elem = Array(DW, Q, "acc_elem", vtype=Wire)

        @self.comb
        def _de_reorder():
            with ForGen("dst", 0, Q) as dst:
                self.acc_elem[dst] <<= self.out_acc_row[dst * DW + (DW - 1):dst * DW]
                with If(self.dr_en):
                    s = []
                    for j in range(Q // 2):
                        c = self.dr_cnt * (Q // 2) + j
                        match = self.reorder_reg[dst * IDXW + (IDXW - 1):dst * IDXW] == c
                        s.append(Mux(match, self.dr_add_val[j], 0))
                    sum_01 = s[0] + s[1]
                    sum_23 = s[2] + s[3]
                    sum_45 = s[4] + s[5]
                    sum_67 = s[6] + s[7]
                    sum_0123 = sum_01 + sum_23
                    sum_4567 = sum_45 + sum_67
                    total = sum_0123 + sum_4567
                    self.acc_elem[dst] <<= self.acc_elem[dst] + total
            self.out_acc_buf_next_row <<= Cat(*[self.acc_elem[i] for i in range(Q - 1, -1, -1)])


# ---------------------------------------------------------------------------
# Top FSMM
# ---------------------------------------------------------------------------
class FSMM(Module):
    def __init__(self, Q: int = 16, DW: int = 8, name: str = "FSMM"):
        super().__init__(name)
        self.Q = Q
        self.DW = DW
        IDXW = max(2, Q.bit_length())

        # ------------------------------------------------------------------
        # Ports
        # ------------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.start = Input(1, "start")
        self.mode = Input(3, "mode")  # 0=1:16, 1=2:16, 2=4:16, 3=8:16, 4=16:16

        self.f_data = Input(Q * Q * DW, "f_data")
        self.w_data = Input(Q * Q * DW, "w_data")
        self.w_idx = Input(Q * Q * IDXW, "w_idx")
        self.reorder_idx = Input(Q * IDXW, "reorder_idx")

        self.valid_out = Output(1, "valid_out")
        self.o_data = Output(Q * Q * DW, "o_data")
        self.busy = Output(1, "busy")

        # ------------------------------------------------------------------
        # State constants
        # ------------------------------------------------------------------
        self.STATE_IDLE = LocalParam(0, "STATE_IDLE")
        self.STATE_LOAD = LocalParam(1, "STATE_LOAD")
        self.STATE_COMPUTE = LocalParam(2, "STATE_COMPUTE")
        self.STATE_DEREORDER = LocalParam(3, "STATE_DEREORDER")
        self.STATE_OUTPUT = LocalParam(4, "STATE_OUTPUT")

        # ------------------------------------------------------------------
        # Buffers & Registers
        # ------------------------------------------------------------------
        self.f_reg = Reg(Q * Q * DW, "f_reg")
        self.w_reg = Reg(Q * Q * DW, "w_reg")
        self.idx_reg = Reg(Q * Q * IDXW, "idx_reg")
        self.reorder_reg = Reg(Q * IDXW, "reorder_reg")
        self.mode_reg = Reg(3, "mode_reg")

        self.state = Reg(3, "state")
        self.compute_cnt = Reg(Q.bit_length() + 1, "compute_cnt")

        self.out_buf = Reg(Q * Q * DW, "out_buf")
        self.out_acc_buf = Reg(Q * Q * DW, "out_acc_buf")
        self.out_reg = Reg(Q * Q * DW, "out_reg")
        self.valid_reg = Reg(1, "valid_reg")

        self.p1_base_c = Reg(Q.bit_length(), "p1_base_c")
        self.p1_valid = Reg(1, "p1_valid")

        self.p2_base_c = Reg(Q.bit_length(), "p2_base_c")
        self.p2_valid = Reg(1, "p2_valid")

        self.dr_cnt = Reg(1, "dr_cnt")

        # ------------------------------------------------------------------
        # Combinational Control Signals
        # ------------------------------------------------------------------
        self.max_k = Wire(Q.bit_length(), "max_k")

        @self.comb
        def _max_k():
            with Switch(self.mode_reg) as sw:
                with sw.case(0): self.max_k <<= 1
                with sw.case(1): self.max_k <<= 2
                with sw.case(2): self.max_k <<= 4
                with sw.case(3): self.max_k <<= 8
                with sw.default(): self.max_k <<= Q  # dense

        self.batch_cols = Wire(Q.bit_length(), "batch_cols")

        @self.comb
        def _batch_cols():
            with Switch(self.max_k) as sw:
                with sw.case(1): self.batch_cols <<= Q
                with sw.case(2): self.batch_cols <<= Q // 2
                with sw.case(4): self.batch_cols <<= Q // 4
                with sw.case(8): self.batch_cols <<= Q // 8
                with sw.default(): self.batch_cols <<= Q // 16

        self.dr_en = Wire(1, "dr_en")

        @self.comb
        def _dr_en():
            self.dr_en <<= (self.state == self.STATE_DEREORDER)

        # ------------------------------------------------------------------
        # Shared fetch unit
        # ------------------------------------------------------------------
        self.fetch_w_val_vec_flat = Wire(Q * DW, "fetch_w_val_vec_flat")
        self.fetch_w_row_vec_flat = Wire(Q * IDXW, "fetch_w_row_vec_flat")
        self.fetch_c_vec_flat = Wire(Q * Q.bit_length(), "fetch_c_vec_flat")

        fetch = FSMMFetchUnit(Q=Q, DW=DW)
        self.instantiate(
            fetch,
            "u_fetch",
            port_map={
                "w_reg": self.w_reg,
                "idx_reg": self.idx_reg,
                "p1_base_c": self.p1_base_c,
                "max_k": self.max_k,
                "w_val_vec_flat": self.fetch_w_val_vec_flat,
                "w_row_vec_flat": self.fetch_w_row_vec_flat,
                "c_vec_flat": self.fetch_c_vec_flat,
            },
        )

        # ------------------------------------------------------------------
        # Row-wise compute engines (generate for)
        # ------------------------------------------------------------------
        self.out_buf_next_arr = Array(Q * DW, Q, "out_buf_next_arr", vtype=Wire)
        self.out_acc_buf_next_arr = Array(Q * DW, Q, "out_acc_buf_next_arr", vtype=Wire)

        with ForGen("r", 0, Q) as r:
            row_engine = FSMMRowEngine(Q=Q, DW=DW)
            self.instantiate(
                row_engine,
                "u_row",
                params={"ROW_IDX": r},
                port_map={
                    "clk": self.clk,
                    "rst_n": self.rst_n,
                    "f_reg": self.f_reg,
                    "w_val_vec_flat": self.fetch_w_val_vec_flat,
                    "w_row_vec_flat": self.fetch_w_row_vec_flat,
                    "c_vec_flat": self.fetch_c_vec_flat,
                    "p1_valid": self.p1_valid,
                    "p2_valid": self.p2_valid,
                    "p2_base_c": self.p2_base_c,
                    "batch_cols": self.batch_cols,
                    "max_k": self.max_k,
                    "out_buf": self.out_buf,
                    "out_buf_next_row": self.out_buf_next_arr[r],
                },
            )

            dr_engine = FSMMDrRowEngine(Q=Q, DW=DW)
            self.instantiate(
                dr_engine,
                "u_dr",
                params={"ROW_IDX": r},
                port_map={
                    "out_acc_buf": self.out_acc_buf,
                    "out_buf": self.out_buf,
                    "reorder_reg": self.reorder_reg,
                    "dr_cnt": self.dr_cnt,
                    "dr_en": self.dr_en,
                    "out_acc_buf_next_row": self.out_acc_buf_next_arr[r],
                },
            )

        # ------------------------------------------------------------------
        # Output assignments
        # ------------------------------------------------------------------
        @self.comb
        def _outputs():
            self.valid_out <<= self.valid_reg
            self.o_data <<= self.out_reg
            self.busy <<= (self.state != self.STATE_IDLE) & (self.state != self.STATE_OUTPUT)

        # ------------------------------------------------------------------
        # Sequential control & pipeline
        # ------------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.state <<= self.STATE_IDLE
                self.compute_cnt <<= 0
                self.valid_reg <<= 0
                self.out_buf <<= 0
                self.out_acc_buf <<= 0
                self.out_reg <<= 0
                self.f_reg <<= 0
                self.w_reg <<= 0
                self.idx_reg <<= 0
                self.reorder_reg <<= 0
                self.mode_reg <<= 0
                self.p1_valid <<= 0
                self.p2_valid <<= 0
                self.dr_cnt <<= 0
            with Else():
                with Switch(self.state) as sw:
                    with sw.case(self.STATE_IDLE):
                        self.valid_reg <<= 0
                        self.dr_cnt <<= 0
                        with If(self.start):
                            self.f_reg <<= self.f_data
                            self.w_reg <<= self.w_data
                            self.idx_reg <<= self.w_idx
                            self.reorder_reg <<= self.reorder_idx
                            self.mode_reg <<= self.mode
                            self.state <<= self.STATE_LOAD

                    with sw.case(self.STATE_LOAD):
                        self.compute_cnt <<= 0
                        self.out_buf <<= 0
                        self.out_acc_buf <<= 0
                        self.p1_valid <<= 0
                        self.p2_valid <<= 0
                        self.state <<= self.STATE_COMPUTE

                    with sw.case(self.STATE_COMPUTE):
                        # P1 issue
                        with If(self.compute_cnt < self.max_k):
                            self.p1_valid <<= 1
                            self.p1_base_c <<= self.compute_cnt * self.batch_cols
                            self.compute_cnt <<= self.compute_cnt + 1
                        with Else():
                            self.p1_valid <<= 0

                        # Pipeline advance
                        self.p2_valid <<= self.p1_valid
                        self.p2_base_c <<= self.p1_base_c

                        # Write P2 results to out_buf
                        self.out_buf <<= Cat(*[self.out_buf_next_arr[i] for i in range(Q - 1, -1, -1)])

                        # Drain check
                        with If((self.compute_cnt >= self.max_k) & (self.p1_valid == 0) & (self.p2_valid == 0)):
                            self.state <<= self.STATE_DEREORDER

                    with sw.case(self.STATE_DEREORDER):
                        self.out_acc_buf <<= Cat(*[self.out_acc_buf_next_arr[i] for i in range(Q - 1, -1, -1)])
                        self.dr_cnt <<= self.dr_cnt + 1
                        with If(self.dr_cnt == 1):
                            self.state <<= self.STATE_OUTPUT

                    with sw.case(self.STATE_OUTPUT):
                        self.out_reg <<= self.out_acc_buf
                        self.valid_reg <<= 1
                        self.state <<= self.STATE_IDLE

                    with sw.default():
                        self.state <<= self.STATE_IDLE


if __name__ == "__main__":
    top = FSMM(Q=16, DW=8)
    emitter = VerilogEmitter()
    print(emitter.emit_design(top))
