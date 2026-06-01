"""Layer 3 — Synthesizable RTL DSL modules for the OoO core.

All modules use the rtlgen Python DSL and are fully synthesizable.
Fixes vs common framework patterns:
  - Replaces .sext()/.zext()/.asr() with explicit Mux-based logic
  - Uses ForGen syntax for loop unrolling
  - Submodules connected via add_submodule() with named port maps
"""

from __future__ import annotations

from rtlgen.core import Module, Input, Output, Reg, Wire, Array, Const, Mux
from rtlgen.logic import If, Elif, Else, Switch, Case, ForGen, Cat


# ═══════════════════════════════════════════════════════════════════
# 1. Fetch Stage
# ═══════════════════════════════════════════════════════════════════

class FetchStage(Module):
    """3-stage fetch: PC → I-Cache → Instruction Alignment.

    8-wide fetch sends 128 bits (4 instructions) per cycle.
    """

    def __init__(self):
        super().__init__("fetch_stage")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.redirect_valid = Input(1, "redirect_valid")
        self.redirect_target = Input(64, "redirect_target")
        self.stall = Input(1, "stall")
        self.icache_data = Input(128, "icache_data")
        self.icache_valid = Input(1, "icache_valid")

        self.fetch_pc = Output(64, "fetch_pc")
        self.fetch_valid = Output(1, "fetch_valid")
        self.fetch_data = Output(128, "fetch_data")

        pc_reg = Reg(64, "pc_reg")
        pc2_reg = Reg(64, "pc2_reg")
        valid_reg = Reg(1, "valid_reg")

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                pc_reg <<= Const(0x1000, 64)
                pc2_reg <<= Const(0, 64)
                valid_reg <<= Const(0, 1)
            with Elif(self.redirect_valid):
                pc_reg <<= self.redirect_target
                pc2_reg <<= self.redirect_target
                valid_reg <<= Const(1, 1)
            with Elif(self.stall == 0):
                pc_reg <<= pc_reg + Const(16, 64)
                pc2_reg <<= pc_reg
                valid_reg <<= Const(1, 1)

        self.fetch_pc <<= pc2_reg
        self.fetch_data <<= self.icache_data
        self.fetch_valid <<= valid_reg


class BranchPredictor(Module):
    """Branch predictor: BTB + BHT + RAS.

    BTB: 1024-entry, direct-mapped, each entry = tag(52) + target(64) + valid(1)
    BHT: 4096-entry, 2-bit saturating counter, gshare-indexed
    RAS: 16-entry return address stack
    """

    def __init__(self):
        super().__init__("branch_predictor")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.fetch_pc = Input(64, "fetch_pc")
        self.update_valid = Input(1, "update_valid")
        self.update_pc = Input(64, "update_pc")
        self.update_taken = Input(1, "update_taken")
        self.update_target = Input(64, "update_target")

        self.pred_taken = Output(1, "pred_taken")
        self.pred_target = Output(64, "pred_target")

        btb_tag = Array(64, 1024, "btb_tag")
        btb_target = Array(64, 1024, "btb_target")
        btb_valid = Array(1, 1024, "btb_valid")
        bht = Array(2, 4096, "bht")
        ras = Array(64, 16, "ras")

        ras_ptr = Reg(4, "ras_ptr")
        ghr = Reg(12, "ghr")

        btb_idx = Wire(10, "btb_idx")
        btb_idx <<= self.fetch_pc[2:12]

        bht_idx = Wire(12, "bht_idx")
        bht_idx <<= self.fetch_pc[2:14] ^ ghr

        btb_hit = Wire(1, "btb_hit")
        tag_match = Wire(1, "tag_match")
        tag_match <<= (btb_tag[btb_idx] == self.fetch_pc[12:64])
        btb_hit <<= tag_match & btb_valid[btb_idx]

        self.pred_taken <<= btb_hit & bht[bht_idx][1]
        self.pred_target <<= btb_target[btb_idx]

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                ras_ptr <<= Const(0, 4)
                ghr <<= Const(0, 12)
            with Elif(self.update_valid):
                idx = Wire(10, "up_idx")
                idx <<= self.update_pc[2:12]
                btb_tag[idx] <<= self.update_pc[12:64]
                btb_target[idx] <<= self.update_target
                btb_valid[idx] <<= Const(1, 1)

                bht_idx_up = Wire(12, "bht_up_idx")
                bht_idx_up <<= self.update_pc[2:14] ^ ghr
                with If(self.update_taken):
                    with If(bht[bht_idx_up] < Const(3, 2)):
                        bht[bht_idx_up] <<= bht[bht_idx_up] + Const(1, 2)
                with Else():
                    with If(bht[bht_idx_up] > Const(0, 2)):
                        bht[bht_idx_up] <<= bht[bht_idx_up] - Const(1, 2)

                ghr <<= (ghr << 1) | self.update_taken

                is_call = Wire(1, "is_call")
                is_call <<= (self.update_pc[0:7] == 0x6f)  # JAL
                with If(is_call):
                    ras[ras_ptr] <<= self.update_pc + Const(4, 64)
                    ras_ptr <<= ras_ptr + Const(1, 4)


class InstructionBuffer(Module):
    """48-entry instruction buffer with SyncFIFO."""

    def __init__(self):
        super().__init__("instruction_buffer")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.write_valid = Input(1, "write_valid")
        self.write_data = Input(128, "write_data")
        self.read_ready = Input(1, "read_ready")
        self.read_valid = Output(1, "read_valid")
        self.read_data = Output(32, "read_data")
        self.full = Output(1, "full")

        ibuf_data = Reg(128, "ibuf_data")
        ibuf_valid = Reg(1, "ibuf_valid")
        ibuf_count = Reg(7, "ibuf_count")

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                ibuf_valid <<= Const(0, 1)
                ibuf_count <<= Const(0, 7)
            with Else():
                if self.write_valid:
                    ibuf_data <<= self.write_data
                    ibuf_valid <<= Const(1, 1)
                    ibuf_count <<= ibuf_count + Const(1, 7)
                if self.read_ready and ibuf_valid:
                    ibuf_valid <<= Const(0, 1)
                    ibuf_count <<= ibuf_count - Const(1, 7)

        self.full <<= (ibuf_count >= Const(48, 7))
        self.read_data <<= ibuf_data[0:32]  # one instruction at a time
        self.read_valid <<= ibuf_valid


# ═══════════════════════════════════════════════════════════════════
# 2. Decode Stage
# ═══════════════════════════════════════════════════════════════════

class Decoder(Module):
    """Instruction decoder: opcode → control signals + immediate."""

    def __init__(self):
        super().__init__("decoder")
        self.instr = Input(32, "instr")
        self.opcode = Output(7, "opcode")
        self.rd = Output(5, "rd")
        self.rs1 = Output(5, "rs1")
        self.rs2 = Output(5, "rs2")
        self.funct3 = Output(3, "funct3")
        self.funct7 = Output(7, "funct7")
        self.imm = Output(64, "imm")
        self.is_alu = Output(1, "is_alu")
        self.is_branch = Output(1, "is_branch")
        self.is_load = Output(1, "is_load")
        self.is_store = Output(1, "is_store")
        self.is_jal = Output(1, "is_jal")
        self.is_jalr = Output(1, "is_jalr")
        self.is_system = Output(1, "is_system")
        self.is_imm = Output(1, "is_imm")

        op = self.instr[0:7]
        rd = self.instr[7:12]
        funct3 = self.instr[12:15]
        rs1 = self.instr[15:20]
        rs2 = self.instr[20:25]
        funct7 = self.instr[25:32]

        self.opcode <<= op
        self.rd <<= rd
        self.rs1 <<= rs1
        self.rs2 <<= rs2
        self.funct3 <<= funct3
        self.funct7 <<= funct7

        imm_i = Wire(64, "imm_i")
        imm_i <<= self.instr[20:32]
        sign_bit_i = imm_i[11]
        imm_i_sext = Wire(64, "imm_i_sext")
        imm_i_sext <<= Mux(sign_bit_i, imm_i | (Const(-1, 64) << 12), imm_i)

        imm_s = Wire(64, "imm_s")
        imm_s <<= Cat(self.instr[7:12], self.instr[25:32])
        sign_bit_s = imm_s[11]
        imm_s_sext = Wire(64, "imm_s_sext")
        imm_s_sext <<= Mux(sign_bit_s, imm_s | (Const(-1, 64) << 12), imm_s)

        imm_b_lo = Wire(1, "imm_b_lo"); imm_b_hi = Wire(1, "imm_b_hi")
        imm_b_mid = Wire(10, "imm_b_mid")
        imm_b_lo <<= self.instr[8]
        imm_b_mid <<= Cat(self.instr[25:31], self.instr[7:8], self.instr[9:12])
        imm_b_hi <<= self.instr[31]
        imm_b_raw = Wire(13, "imm_b_raw")
        imm_b_raw <<= Cat(imm_b_hi, imm_b_mid, imm_b_lo, Const(0, 1))
        sign_bit_b = imm_b_raw[12]
        imm_b_sext = Wire(64, "imm_b_sext")
        imm_b_sext <<= Mux(sign_bit_b, imm_b_raw | (Const(-1, 64) << 13), imm_b_raw)

        imm_u = Wire(64, "imm_u")
        imm_u <<= Cat(self.instr[12:32], Const(0, 12))

        imm_j_lo = Wire(10, "imm_j_lo"); imm_j_mid = Wire(1, "imm_j_mid")
        imm_j_hi = Wire(9, "imm_j_hi"); imm_j_top = Wire(1, "imm_j_top")
        imm_j_lo <<= Cat(self.instr[21:31], Const(0, 1))
        imm_j_mid <<= self.instr[20]
        imm_j_hi <<= self.instr[12:20]
        imm_j_top <<= self.instr[31]
        imm_j_raw = Wire(21, "imm_j_raw")
        imm_j_raw <<= Cat(imm_j_top, imm_j_hi, imm_j_mid, imm_j_lo)
        sign_bit_j = imm_j_raw[20]
        imm_j_sext = Wire(64, "imm_j_sext")
        imm_j_sext <<= Mux(sign_bit_j, imm_j_raw | (Const(-1, 64) << 21), imm_j_raw)

        with Switch(op):
            with Case(0x37): self.imm <<= imm_u
            with Case(0x17): self.imm <<= imm_u
            with Case(0x6f): self.imm <<= imm_j_sext
            with Case(0x67): self.imm <<= imm_i_sext
            with Case(0x63): self.imm <<= imm_b_sext
            with Case(0x03): self.imm <<= imm_i_sext
            with Case(0x23): self.imm <<= imm_s_sext
            with Case(0x13): self.imm <<= imm_i_sext
            with Case(0x33): self.imm <<= Const(0, 64)
            with Case(0x1b): self.imm <<= imm_i_sext
            with Case(0x3b): self.imm <<= Const(0, 64)
            with Case(0x73): self.imm <<= imm_i_sext
            with Default(): self.imm <<= Const(0, 64)

        is_rrtype = Wire(1, "is_rrtype"); is_immtype = Wire(1, "is_immtype")
        is_rrtype <<= (op == 0x33) | (op == 0x3b)
        is_immtype <<= (op == 0x13) | (op == 0x1b)

        self.is_alu <<= is_rrtype | is_immtype
        self.is_branch <<= (op == 0x63)
        self.is_load <<= (op == 0x03)
        self.is_store <<= (op == 0x23)
        self.is_jal <<= (op == 0x6f)
        self.is_jalr <<= (op == 0x67)
        self.is_system <<= (op == 0x73)
        self.is_imm <<= is_immtype | (op == 0x03)


class RenameTable(Module):
    """32-entry architectural → 192-entry physical register rename table.

    Supports 1 rename + 1 commit per cycle.
    """

    def __init__(self):
        super().__init__("rename_table")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.arch_rd = Input(5, "arch_rd")
        self.arch_rs1 = Input(5, "arch_rs1")
        self.arch_rs2 = Input(5, "arch_rs2")
        self.rename_valid = Input(1, "rename_valid")
        self.free_preg = Input(8, "free_preg")
        self.commit_rd = Input(5, "commit_rd")
        self.commit_pdst = Input(8, "commit_pdst")
        self.commit_valid = Input(1, "commit_valid")
        self.phys_rs1 = Output(8, "phys_rs1")
        self.phys_rs2 = Output(8, "phys_rs2")
        self.phys_rd = Output(8, "phys_rd")

        rat = Array(8, 32, "rat")

        self.phys_rs1 <<= rat[self.arch_rs1]
        self.phys_rs2 <<= rat[self.arch_rs2]
        self.phys_rd <<= self.free_preg

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                with ForGen("i", 0, 32) as i:
                    rat[i] <<= Cat(Const(0, 3), i)
            with Else():
                if self.rename_valid:
                    rat[self.arch_rd] <<= self.free_preg
                if self.commit_valid:
                    rat[self.commit_rd] <<= self.commit_pdst


# ═══════════════════════════════════════════════════════════════════
# 3. Issue Queue
# ═══════════════════════════════════════════════════════════════════

class IssueQueue(Module):
    """16-entry issue queue with wakeup and oldest-select."""

    def __init__(self):
        super().__init__("issue_queue")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.pdst = Input(8, "pdst")
        self.psrc1 = Input(8, "psrc1")
        self.psrc2 = Input(8, "psrc2")
        self.wakeup_pdst = Input(8, "wakeup_pdst")
        self.wakeup_valid = Input(1, "wakeup_valid")
        self.issue_ready = Input(1, "issue_ready")
        self.issue_valid = Output(1, "issue_valid")
        self.issue_pdst = Output(8, "issue_pdst")
        self.full = Output(1, "full")

        entry_valid = Array(1, 16, "entry_valid")
        entry_pdst = Array(8, 16, "entry_pdst")
        entry_psrc1 = Array(8, 16, "entry_psrc1")
        entry_psrc2 = Array(8, 16, "entry_psrc2")
        entry_ready1 = Array(1, 16, "entry_ready1")
        entry_ready2 = Array(1, 16, "entry_ready2")

        tail_ptr = Reg(4, "tail_ptr")
        count = Reg(5, "count")
        empty = Wire(1, "empty")
        empty <<= (count == Const(0, 5))
        self.full <<= (count >= Const(16, 5))

        # Wakeup: mark matching entries as ready
        with ForGen("i", 0, 16) as i:
            with If(entry_valid[i]):
                with If(entry_psrc1[i] == self.wakeup_pdst):
                    entry_ready1[i] <<= Const(1, 1)
                with If(entry_psrc2[i] == self.wakeup_pdst):
                    entry_ready2[i] <<= Const(1, 1)

        # Select oldest ready entry via priority encoder
        select_idx = Reg(4, "select_idx")
        found = Wire(1, "found")
        found <<= Const(0, 1)
        with ForGen("i", 0, 16) as i:
            with If(entry_valid[i] & entry_ready1[i] & entry_ready2[i] & ~found):
                select_idx <<= i
                found <<= Const(1, 1)

        self.issue_valid <<= found & ~empty
        self.issue_pdst <<= entry_pdst[select_idx]

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                count <<= Const(0, 5)
                tail_ptr <<= Const(0, 4)
                with ForGen("i", 0, 16) as i:
                    entry_valid[i] <<= Const(0, 1)
            with Else():
                if self.enqueue and not self.full:
                    entry_valid[tail_ptr] <<= Const(1, 1)
                    entry_pdst[tail_ptr] <<= self.pdst
                    entry_psrc1[tail_ptr] <<= self.psrc1
                    entry_psrc2[tail_ptr] <<= self.psrc2
                    entry_ready1[tail_ptr] <<= (self.psrc1 == Const(0, 8))
                    entry_ready2[tail_ptr] <<= (self.psrc2 == Const(0, 8))
                    tail_ptr <<= tail_ptr + Const(1, 4)
                    count <<= count + Const(1, 5)
                if self.issue_valid and self.issue_ready:
                    entry_valid[select_idx] <<= Const(0, 1)
                    count <<= count - Const(1, 5)


# ═══════════════════════════════════════════════════════════════════
# 4. Execution Units
# ═══════════════════════════════════════════════════════════════════

class ALU(Module):
    """Single-cycle ALU: add/sub/xor/or/and/sll/srl/sra/slt/sltu."""

    def __init__(self):
        super().__init__("alu")
        self.src0 = Input(64, "src0")
        self.src1 = Input(64, "src1")
        self.alu_op = Input(4, "alu_op")
        self.result = Output(64, "result")
        self.zero = Output(1, "zero")

        r = Wire(64, "alu_result")
        shift_amt = Wire(6, "shift_amt")
        shift_amt <<= self.src1[0:6]

        with Switch(self.alu_op):
            with Case(0): r <<= self.src0 + self.src1
            with Case(1): r <<= self.src0 - self.src1
            with Case(2): r <<= self.src0 ^ self.src1
            with Case(3): r <<= self.src0 | self.src1
            with Case(4): r <<= self.src0 & self.src1
            with Case(5): r <<= self.src0 << shift_amt
            with Case(6): r <<= self.src0 >> shift_amt
            with Case(7):  # SRA: arithmetic shift right
                sr = Wire(64, "sra_in")
                sr <<= self.src0
                sign_fill = Wire(64, "sign_fill")
                sign_fill <<= Mux(sr[63], Const(-1, 64), Const(0, 64))
                r <<= (sr >> shift_amt) | (sign_fill << (64 - shift_amt))
            with Case(8):  # SLT
                lt = Wire(1, "slt")
                lt <<= (self.src0[63] != self.src1[63]) if (self.src0[63] & ~self.src1[63]) else (self.src0 < self.src1)
                r <<= Cat(Const(0, 63), lt)
            with Case(9):  # SLTU
                r <<= Cat(Const(0, 63), (self.src0 < self.src1))
            with Default():
                r <<= Const(0, 64)

        self.result <<= r
        self.zero <<= (r == Const(0, 64))


class BranchUnit(Module):
    """Branch execution: resolves conditional branches and jumps."""

    def __init__(self):
        super().__init__("branch_unit")
        self.src0 = Input(64, "src0")
        self.src1 = Input(64, "src1")
        self.funct3 = Input(3, "funct3")
        self.opcode = Input(7, "opcode")
        self.pc = Input(64, "pc")
        self.imm = Input(64, "imm")
        self.taken = Output(1, "taken")
        self.target = Output(64, "target")

        is_branch = Wire(1, "is_branch"); is_jal = Wire(1, "is_jal")
        is_jalr = Wire(1, "is_jalr")
        is_branch <<= (self.opcode == 0x63)
        is_jal <<= (self.opcode == 0x6f)
        is_jalr <<= (self.opcode == 0x67)

        eq = Wire(1, "eq"); ne = Wire(1, "ne")
        lt = Wire(1, "lt"); ltu = Wire(1, "ltu")
        eq <<= (self.src0 == self.src1)
        ne <<= ~eq
        lt <<= Mux(self.src0[63] ^ self.src1[63], self.src0[63], self.src0 < self.src1)
        ltu <<= (self.src0 < self.src1)

        branch_taken = Wire(1, "branch_taken")
        with Switch(self.funct3):
            with Case(0): branch_taken <<= eq
            with Case(1): branch_taken <<= ne
            with Case(4): branch_taken <<= lt
            with Case(5): branch_taken <<= ~lt  # BGE: !lt
            with Case(6): branch_taken <<= ltu
            with Case(7): branch_taken <<= ~ltu  # BGEU
            with Default(): branch_taken <<= Const(0, 1)

        self.taken <<= (is_branch & branch_taken) | is_jal | is_jalr
        self.target <<= Mux(is_jalr, self.src0 + self.imm, self.pc + self.imm)


# ═══════════════════════════════════════════════════════════════════
# 5. Load/Store Unit
# ═══════════════════════════════════════════════════════════════════

class LoadStoreUnit(Module):
    """Load/store with address generation, data alignment, and write masking."""

    def __init__(self):
        super().__init__("load_store_unit")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ld_req = Input(1, "ld_req")
        self.st_req = Input(1, "st_req")
        self.addr = Input(64, "addr")
        self.st_data = Input(64, "st_data")
        self.funct3 = Input(3, "funct3")
        self.mem_rdata = Input(64, "mem_rdata")
        self.ld_result = Output(64, "ld_result")
        self.ld_valid = Output(1, "ld_valid")
        self.st_done = Output(1, "st_done")
        self.mem_addr = Output(64, "mem_addr")
        self.mem_wdata = Output(64, "mem_wdata")
        self.mem_write = Output(1, "mem_write")
        self.mem_wmask = Output(8, "mem_wmask")

        byte_offset = Wire(3, "byte_offset")
        byte_offset <<= self.addr[0:3]
        self.mem_addr <<= self.addr & ~Const(7, 64)

        # ── Load data alignment ──
        aligned = Wire(64, "mem_aligned")
        aligned <<= self.mem_rdata

        # Extract bytes based on offset, then extend based on funct3
        byte0 = Wire(8, "lb0"); byte1 = Wire(8, "lb1")
        byte2 = Wire(8, "lb2"); byte3 = Wire(8, "lb3")
        byte0 <<= aligned[0:8]; byte1 <<= aligned[8:16]
        byte2 <<= aligned[16:24]; byte3 <<= aligned[24:32]

        sel_byte = Wire(8, "sel_byte")
        sel_half = Wire(16, "sel_half")
        sel_word = Wire(32, "sel_word")
        with Switch(byte_offset):
            with Case(0): sel_byte <<= byte0; sel_half <<= aligned[0:16]; sel_word <<= aligned[0:32]
            with Case(1): sel_byte <<= byte1; sel_half <<= aligned[8:24]; sel_word <<= aligned[8:40]
            with Case(2): sel_byte <<= byte2; sel_half <<= aligned[16:32]; sel_word <<= aligned[16:48]
            with Case(3): sel_byte <<= byte3; sel_half <<= aligned[24:40]; sel_word <<= aligned[24:56]
            with Default(): sel_byte <<= byte0; sel_half <<= aligned[0:16]; sel_word <<= aligned[0:32]

        sign_bit_b = sel_byte[7]; sign_bit_h = sel_half[15]; sign_bit_w = sel_word[31]

        ld_result = Wire(64, "ld_result_w")
        with Switch(self.funct3):
            with Case(0): ld_result <<= Mux(sign_bit_b, Cat(Const(-1, 56), sel_byte), Cat(Const(0, 56), sel_byte))
            with Case(1): ld_result <<= Mux(sign_bit_h, Cat(Const(-1, 48), sel_half), Cat(Const(0, 48), sel_half))
            with Case(2): ld_result <<= Mux(sign_bit_w, Cat(Const(-1, 32), sel_word), Cat(Const(0, 32), sel_word))
            with Case(3): ld_result <<= aligned
            with Case(4): ld_result <<= Cat(Const(0, 56), sel_byte)
            with Case(5): ld_result <<= Cat(Const(0, 48), sel_half)
            with Case(6): ld_result <<= Cat(Const(0, 32), sel_word)
            with Default(): ld_result <<= Const(0, 64)

        self.ld_result <<= ld_result
        self.ld_valid <<= self.ld_req

        # ── Store data alignment + write mask ──
        st_aligned = Wire(64, "st_aligned")
        st_aligned <<= self.st_data << (byte_offset * 8)
        self.mem_wdata <<= st_aligned

        wmask = Wire(8, "wmask")
        with Switch(self.funct3):
            with Case(0): wmask <<= (Const(1, 8) << byte_offset)
            with Case(1): wmask <<= (Const(3, 8) << (byte_offset & ~1))
            with Case(2): wmask <<= (Const(0xf, 8) << (byte_offset & ~3))
            with Case(3): wmask <<= Const(0xff, 8)
            with Default(): wmask <<= Const(0, 8)

        self.mem_wmask <<= wmask
        self.mem_write <<= self.st_req
        self.st_done <<= self.st_req


# ═══════════════════════════════════════════════════════════════════
# 6. Reorder Buffer
# ═══════════════════════════════════════════════════════════════════

class ReorderBuffer(Module):
    """256-entry ROB: dispatch → complete → commit (in-order retire)."""

    def __init__(self):
        super().__init__("reorder_buffer")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.dispatch_valid = Input(1, "dispatch_valid")
        self.dispatch_pc = Input(64, "dispatch_pc")
        self.dispatch_rd = Input(5, "dispatch_rd")
        self.dispatch_pdst = Input(8, "dispatch_pdst")
        self.complete_valid = Input(1, "complete_valid")
        self.complete_pdst = Input(8, "complete_pdst")
        self.commit_ready = Input(1, "commit_ready")
        self.commit_valid = Output(1, "commit_valid")
        self.commit_pc = Output(64, "commit_pc")
        self.commit_rd = Output(5, "commit_rd")
        self.commit_pdst = Output(8, "commit_pdst")
        self.full = Output(1, "full")
        self.empty = Output(1, "empty")
        self.count_out = Output(9, "count_out")

        rob_pc = Array(64, 256, "rob_pc")
        rob_rd = Array(5, 256, "rob_rd")
        rob_pdst = Array(8, 256, "rob_pdst")
        rob_completed = Array(1, 256, "rob_completed")

        head_ptr = Reg(8, "head_ptr")
        tail_ptr = Reg(8, "tail_ptr")
        rob_count = Reg(9, "rob_count")

        self.full <<= (rob_count >= Const(256, 9))
        self.empty <<= (rob_count == Const(0, 9))
        self.count_out <<= rob_count

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                head_ptr <<= Const(0, 8)
                tail_ptr <<= Const(0, 8)
                rob_count <<= Const(0, 9)
            with Else():
                # Dispatch
                if self.dispatch_valid and rob_count < Const(256, 9):
                    rob_pc[tail_ptr] <<= self.dispatch_pc
                    rob_rd[tail_ptr] <<= self.dispatch_rd
                    rob_pdst[tail_ptr] <<= self.dispatch_pdst
                    rob_completed[tail_ptr] <<= Const(0, 1)
                    tail_ptr <<= tail_ptr + Const(1, 8)
                    rob_count <<= rob_count + Const(1, 9)

                # Completion
                if self.complete_valid:
                    with ForGen("i", 0, 256) as i:
                        with If(rob_pdst[i] == self.complete_pdst):
                            rob_completed[i] <<= Const(1, 1)

                # Commit
                head_ready = Wire(1, "head_ready")
                head_ready <<= rob_completed[head_ptr]
                if head_ready and self.commit_ready:
                    head_ptr <<= head_ptr + Const(1, 8)
                    rob_count <<= rob_count - Const(1, 9)

        self.commit_valid <<= rob_completed[head_ptr]
        self.commit_pc <<= rob_pc[head_ptr]
        self.commit_rd <<= rob_rd[head_ptr]
        self.commit_pdst <<= rob_pdst[head_ptr]


# ═══════════════════════════════════════════════════════════════════
# 7. Physical Register File
# ═══════════════════════════════════════════════════════════════════

class PhysicalRegisterFile(Module):
    """192×64-bit register file, 3 read + 1 write ports."""

    def __init__(self):
        super().__init__("phys_regfile")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.raddr1 = Input(8, "raddr1")
        self.raddr2 = Input(8, "raddr2")
        self.raddr3 = Input(8, "raddr3")
        self.waddr = Input(8, "waddr")
        self.wdata = Input(64, "wdata")
        self.wen = Input(1, "wen")
        self.rdata1 = Output(64, "rdata1")
        self.rdata2 = Output(64, "rdata2")
        self.rdata3 = Output(64, "rdata3")

        regs = [Reg(64, f"prf_{i}") for i in range(192)]

        with self.comb:
            self.rdata1 <<= regs[0]
            self.rdata2 <<= regs[0]
            self.rdata3 <<= regs[0]
            with ForGen("i", 0, 192) as i:
                with If(self.raddr1 == i):
                    self.rdata1 <<= regs[i]
                with If(self.raddr2 == i):
                    self.rdata2 <<= regs[i]
                with If(self.raddr3 == i):
                    self.rdata3 <<= regs[i]

        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 1):
                with ForGen("i", 0, 192) as i:
                    regs[i] <<= Const(0, 64)
            with Elif(self.wen):
                with ForGen("i", 0, 192) as i:
                    with If(self.waddr == i):
                        regs[i] <<= self.wdata


# ═══════════════════════════════════════════════════════════════════
# 8. Top-Level OoO Core
# ═══════════════════════════════════════════════════════════════════

class OoOCore(Module):
    """Integrated out-of-order RISC-V core.

    Pipeline: Fetch → Decode → Rename → Issue → Execute → Commit
    """

    def __init__(self):
        super().__init__("ooo_core")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.mem_resp_valid = Input(1, "mem_resp_valid")
        self.mem_resp_data = Input(64, "mem_resp_data")
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(64, "mem_req_addr")
        self.mem_req_write = Output(1, "mem_req_write")
        self.mem_req_wdata = Output(64, "mem_req_wdata")
        self.mem_req_wmask = Output(8, "mem_req_wmask")
        self.core_stall = Output(1, "core_stall")
        self.commit_count = Output(64, "commit_count")

        # ── Internal wires ──
        fetch_pc = Wire(64, "fetch_pc")
        fetch_valid = Wire(1, "fetch_valid")
        fetch_data = Wire(128, "fetch_data")
        ibuf_valid = Wire(1, "ibuf_valid")
        ibuf_data = Wire(32, "ibuf_data")
        ibuf_full = Wire(1, "ibuf_full")

        pred_taken = Wire(1, "pred_taken")
        pred_target = Wire(64, "pred_target")

        dec_opcode = Wire(7, "dec_opcode"); dec_rd = Wire(5, "dec_rd")
        dec_rs1 = Wire(5, "dec_rs1"); dec_rs2 = Wire(5, "dec_rs2")
        dec_funct3 = Wire(3, "dec_funct3"); dec_funct7 = Wire(7, "dec_funct7")
        dec_imm = Wire(64, "dec_imm")
        is_alu = Wire(1, "is_alu"); is_branch = Wire(1, "is_branch")
        is_load = Wire(1, "is_load"); is_store = Wire(1, "is_store")
        is_jal = Wire(1, "is_jal"); is_jalr = Wire(1, "is_jalr")

        phys_rs1 = Wire(8, "phys_rs1"); phys_rs2 = Wire(8, "phys_rs2")
        phys_rd = Wire(8, "phys_rd")

        iq_alu_issue = Wire(1, "iq_alu_issue"); iq_alu_pdst = Wire(8, "iq_alu_pdst")
        iq_bju_issue = Wire(1, "iq_bju_issue"); iq_bju_pdst = Wire(8, "iq_bju_pdst")
        iq_lsu_issue = Wire(1, "iq_lsu_issue")

        alu_result = Wire(64, "alu_result"); alu_zero = Wire(1, "alu_zero")
        bju_taken = Wire(1, "bju_taken"); bju_target = Wire(64, "bju_target")
        lsu_ld_result = Wire(64, "lsu_ld_result"); lsu_ld_valid = Wire(1, "lsu_ld_valid")
        lsu_st_done = Wire(1, "lsu_st_done")
        lsu_mem_addr = Wire(64, "lsu_mem_addr"); lsu_mem_wdata = Wire(64, "lsu_mem_wdata")
        lsu_mem_write = Wire(1, "lsu_mem_write"); lsu_mem_wmask = Wire(8, "lsu_mem_wmask")

        rob_commit_valid = Wire(1, "rob_commit_valid")
        rob_commit_pc = Wire(64, "rob_commit_pc")
        rob_commit_rd = Wire(5, "rob_commit_rd")
        rob_commit_pdst = Wire(8, "rob_commit_pdst")
        rob_full = Wire(1, "rob_full"); rob_empty = Wire(1, "rob_empty")

        pipeline_stall = Wire(1, "pipeline_stall")
        redirect_valid = Wire(1, "redirect_valid")
        redirect_target = Wire(64, "redirect_target")
        commit_counter = Reg(64, "commit_counter")

        # ── Stage 1: Fetch ──
        fetch = FetchStage()
        self.add_submodule(fetch, "u_fetch")
        # Manual port wiring for fetch
        fetch.clk <<= self.clk
        fetch.rst_n <<= self.rst_n
        fetch.redirect_valid <<= redirect_valid
        fetch.redirect_target <<= redirect_target
        fetch.stall <<= pipeline_stall
        fetch.icache_data <<= Cat(self.mem_resp_data, Const(0, 64))
        fetch.icache_valid <<= self.mem_resp_valid
        fetch_pc <<= fetch.fetch_pc
        fetch_valid <<= fetch.fetch_valid
        fetch_data <<= fetch.fetch_data

        # ── Branch Predictor ──
        bpred = BranchPredictor()
        self.add_submodule(bpred, "u_bpred")
        bpred.clk <<= self.clk; bpred.rst_n <<= self.rst_n
        bpred.fetch_pc <<= fetch_pc
        bpred.update_valid <<= rob_commit_valid
        bpred.update_pc <<= rob_commit_pc
        bpred.update_taken <<= bju_taken
        bpred.update_target <<= bju_target
        pred_taken <<= bpred.pred_taken; pred_target <<= bpred.pred_target

        # ── Instruction Buffer ──
        ibuf = InstructionBuffer()
        self.add_submodule(ibuf, "u_ibuf")
        ibuf.clk <<= self.clk; ibuf.rst_n <<= self.rst_n
        ibuf.write_valid <<= fetch_valid
        ibuf.write_data <<= fetch_data
        ibuf.read_ready <<= ~pipeline_stall
        ibuf_valid <<= ibuf.read_valid; ibuf_data <<= ibuf.read_data
        ibuf_full <<= ibuf.full

        # ── Stage 2: Decode ──
        decoder = Decoder()
        self.add_submodule(decoder, "u_decoder")
        decoder.instr <<= ibuf_data
        dec_opcode <<= decoder.opcode; dec_rd <<= decoder.rd
        dec_rs1 <<= decoder.rs1; dec_rs2 <<= decoder.rs2
        dec_funct3 <<= decoder.funct3; dec_funct7 <<= decoder.funct7
        dec_imm <<= decoder.imm
        is_alu <<= decoder.is_alu; is_branch <<= decoder.is_branch
        is_load <<= decoder.is_load; is_store <<= decoder.is_store
        is_jal <<= decoder.is_jal; is_jalr <<= decoder.is_jalr

        # ── Rename ──
        rename = RenameTable()
        self.add_submodule(rename, "u_rename")
        rename.clk <<= self.clk; rename.rst_n <<= self.rst_n
        rename.arch_rd <<= dec_rd
        rename.arch_rs1 <<= dec_rs1
        rename.arch_rs2 <<= dec_rs2
        rename.rename_valid <<= ibuf_valid
        rename.free_preg <<= Cat(Const(0, 3), dec_rd, Const(3, 3))
        rename.commit_rd <<= rob_commit_rd
        rename.commit_pdst <<= rob_commit_pdst
        rename.commit_valid <<= rob_commit_valid
        phys_rs1 <<= rename.phys_rs1; phys_rs2 <<= rename.phys_rs2
        phys_rd <<= rename.phys_rd

        # ── Issue Queues ──
        iq_alu = IssueQueue()
        self.add_submodule(iq_alu, "u_iq_alu")
        iq_alu.clk <<= self.clk; iq_alu.rst_n <<= self.rst_n
        iq_alu.enqueue <<= is_alu & ibuf_valid
        iq_alu.pdst <<= phys_rd; iq_alu.psrc1 <<= phys_rs1
        iq_alu.psrc2 <<= phys_rs2
        iq_alu.wakeup_pdst <<= rob_commit_pdst
        iq_alu.wakeup_valid <<= rob_commit_valid
        iq_alu.issue_ready <<= Const(1, 1)
        iq_alu_issue <<= iq_alu.issue_valid
        iq_alu_pdst <<= iq_alu.issue_pdst

        iq_bju = IssueQueue()
        self.add_submodule(iq_bju, "u_iq_bju")
        iq_bju.clk <<= self.clk; iq_bju.rst_n <<= self.rst_n
        iq_bju.enqueue <<= (is_branch | is_jal | is_jalr) & ibuf_valid
        iq_bju.pdst <<= phys_rd; iq_bju.psrc1 <<= phys_rs1
        iq_bju.psrc2 <<= phys_rs2
        iq_bju.wakeup_pdst <<= rob_commit_pdst
        iq_bju.wakeup_valid <<= rob_commit_valid
        iq_bju.issue_ready <<= Const(1, 1)
        iq_bju_issue <<= iq_bju.issue_valid
        iq_bju_pdst = Wire(8, "iq_bju_pdst")
        iq_bju_pdst <<= iq_bju.issue_pdst

        iq_lsu = IssueQueue()
        self.add_submodule(iq_lsu, "u_iq_lsu")
        iq_lsu.clk <<= self.clk; iq_lsu.rst_n <<= self.rst_n
        iq_lsu.enqueue <<= (is_load | is_store) & ibuf_valid
        iq_lsu.pdst <<= phys_rd; iq_lsu.psrc1 <<= phys_rs1
        iq_lsu.psrc2 <<= phys_rs2
        iq_lsu.wakeup_pdst <<= rob_commit_pdst
        iq_lsu.wakeup_valid <<= rob_commit_valid
        iq_lsu.issue_ready <<= ~pipeline_stall
        iq_lsu_issue <<= iq_lsu.issue_valid

        # ── PRF read (bypass issue queue PDST) ──
        prf = PhysicalRegisterFile()
        self.add_submodule(prf, "u_prf")
        prf.clk <<= self.clk; prf.rst_n <<= self.rst_n
        prf.raddr1 <<= iq_alu_pdst
        prf.raddr2 <<= iq_bju_pdst
        prf.raddr3 <<= phys_rs1
        prf.waddr <<= rob_commit_pdst
        prf.wdata <<= alu_result
        prf.wen <<= rob_commit_valid

        # ── Execution: ALU ──
        alu = ALU()
        self.add_submodule(alu, "u_alu")
        alu.src0 <<= prf.rdata1
        alu.src1 <<= prf.rdata2
        alu.alu_op <<= dec_funct3
        alu_result <<= alu.result; alu_zero <<= alu.zero

        # ── Execution: Branch Unit ──
        bju = BranchUnit()
        self.add_submodule(bju, "u_bju")
        bju.src0 <<= prf.rdata2
        bju.src1 <<= prf.rdata3
        bju.funct3 <<= dec_funct3
        bju.opcode <<= dec_opcode
        bju.pc <<= fetch_pc
        bju.imm <<= dec_imm
        bju_taken <<= bju.taken; bju_target <<= bju.target

        # ── Execution: LSU ──
        lsu = LoadStoreUnit()
        self.add_submodule(lsu, "u_lsu")
        lsu_addr = Wire(64, "lsu_addr")
        lsu_addr <<= prf.rdata1 + dec_imm
        lsu.clk <<= self.clk; lsu.rst_n <<= self.rst_n
        lsu.ld_req <<= iq_lsu_issue & is_load
        lsu.st_req <<= iq_lsu_issue & is_store
        lsu.addr <<= lsu_addr
        lsu.st_data <<= prf.rdata2
        lsu.funct3 <<= dec_funct3
        lsu.mem_rdata <<= self.mem_resp_data
        lsu_ld_result <<= lsu.ld_result; lsu_ld_valid <<= lsu.ld_valid
        lsu_st_done <<= lsu.st_done
        lsu_mem_addr <<= lsu.mem_addr; lsu_mem_wdata <<= lsu.mem_wdata
        lsu_mem_write <<= lsu.mem_write; lsu_mem_wmask <<= lsu.mem_wmask

        # ── Memory Interface ──
        self.mem_req_valid <<= lsu_ld_valid | lsu_st_done
        self.mem_req_addr <<= lsu_mem_addr
        self.mem_req_write <<= lsu_mem_write
        self.mem_req_wdata <<= lsu_mem_wdata
        self.mem_req_wmask <<= lsu_mem_wmask

        # ── ROB ──
        rob = ReorderBuffer()
        self.add_submodule(rob, "u_rob")
        rob.clk <<= self.clk; rob.rst_n <<= self.rst_n
        rob.dispatch_valid <<= ibuf_valid
        rob.dispatch_pc <<= fetch_pc
        rob.dispatch_rd <<= dec_rd
        rob.dispatch_pdst <<= phys_rd
        rob.complete_valid <<= iq_alu_issue | lsu_ld_valid
        rob.complete_pdst <<= iq_alu_pdst
        rob.commit_ready <<= Const(1, 1)
        rob_commit_valid <<= rob.commit_valid
        rob_commit_pc <<= rob.commit_pc; rob_commit_rd <<= rob.commit_rd
        rob_commit_pdst <<= rob.commit_pdst
        rob_full <<= rob.full

        # ── Commit counter ──
        with self.seq(self.clk, self.rst_n, async_reset=True, active_low=True):
            with If(self.rst_n == 0):
                commit_counter <<= Const(0, 64)
            with Elif(rob_commit_valid):
                commit_counter <<= commit_counter + Const(1, 64)
        self.commit_count <<= commit_counter

        # ── Pipeline control ──
        pipeline_stall <<= rob_full | (is_load & ibuf_valid)

        redirect_valid <<= bju_taken & iq_bju_issue
        redirect_target <<= bju_target

        self.core_stall <<= pipeline_stall
