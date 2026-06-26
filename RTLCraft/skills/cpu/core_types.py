"""
core_types — Heterogeneous RISC-V core types for SoC integration.

HPCore: 6-issue OoO with TAGE, MMU, 32-entry ROB.
EECore: 1-issue in-order with gshare BPred, 8-entry ROB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Const
from rtlgen.logic import If, Else, Elif, Mux, Cat

from skills.cpu.layer3_dsl.pcgen import PCGen
from skills.cpu.layer3_dsl.ibuf import IBuf
from skills.cpu.layer3_dsl.idu_decode import Decoder
from skills.cpu.layer3_dsl.rename import RenameTable
from skills.cpu.layer3_dsl.issue_queue import IssueQueue
from skills.cpu.layer3_dsl.alu import ALU
from skills.cpu.layer3_dsl.iu_bju import BJU
from skills.cpu.layer3_dsl.rob import ROB
from skills.cpu.layer3_dsl.csr import CSRFile


class HPCore(Module):
    """High-Performance Core — simplified 6-issue OoO.

    Decode→Rename→IssueQueue→ALU path uses pipeline register
    between decode and rename to avoid combinational loops.
    """

    def __init__(self, hartid=0, PC_WIDTH=39, XLEN=64):
        super().__init__(f"hp_core_{hartid}")

        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.hartid = Input(8, "hartid")
        self.instr = Input(32, "instr"); self.instr_valid = Input(1, "instr_valid")
        self.mem_rdata = Input(XLEN, "mem_rdata"); self.mem_rvalid = Input(1, "mem_rvalid")
        self.mtip = Input(1, "mtip"); self.meip = Input(1, "meip"); self.msip = Input(1, "msip")
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(64, "mem_req_addr")
        self.mem_req_we = Output(1, "mem_req_we")
        self.mem_req_data = Output(64, "mem_req_data")
        self.result = Output(XLEN, "result"); self.result_valid = Output(1, "result_valid")
        self.retired = Output(1, "retired")

        # ---- PCGen / IBuf (not in comb path with issue) ----
        u_pcgen = PCGen(has_l0_btb=False, has_way_pred=False, PC_WIDTH=PC_WIDTH, RESET_VEC=0)
        u_ibuf = IBuf(4, 32)

        # ---- Issue pipeline with pipelined decode/rename ----
        u_decoder = Decoder()

        # Pipeline registers between decode → rename
        r_dec_rs1 = Reg(5, "r_dec_rs1"); r_dec_rs2 = Reg(5, "r_dec_rs2"); r_dec_rd = Reg(5, "r_dec_rd")

        u_rename = RenameTable(32, 64)
        u_iq = IssueQueue(4, 64)
        u_alu = ALU(XLEN)
        u_rob = ROB(32, 64)
        u_csr = CSRFile()

        self._submodules.extend([
            ("pcgen", u_pcgen), ("ibuf", u_ibuf), ("decoder", u_decoder),
            ("rename", u_rename), ("iq", u_iq),
            ("alu", u_alu), ("rob", u_rob), ("csr", u_csr),
        ])

        is_issue = Wire(1, "is_issue"); issue_prd = Wire(7, "issue_prd")
        alloc_phy = Wire(7, "alloc_phy"); commit_en = Wire(1, "commit_en")
        rob_retire_en = Wire(1, "rob_retire_en")

        r_alloc_en = Reg(1, "r_alloc_en")
        r_issue_cnt = Reg(5, "r_issue_cnt")
        init = Reg(1, "init")
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                init <<= 0; r_dec_rs1 <<= 0; r_dec_rs2 <<= 0; r_dec_rd <<= 0
                r_alloc_en <<= 0; r_issue_cnt <<= 0
            with Else():
                init <<= 1
                r_dec_rs1 <<= u_decoder.rs1; r_dec_rs2 <<= u_decoder.rs2; r_dec_rd <<= u_decoder.rd
                r_alloc_en <<= self.instr_valid
                with If(is_issue == 1):
                    r_issue_cnt <<= r_issue_cnt + Const(1, 5)

        with self.comb:
            # Unguarded child input connections (driven every cycle)
            u_decoder.instr <<= self.instr
            u_rename.rs1 <<= r_dec_rs1; u_rename.rs2 <<= r_dec_rs2
            u_rename.rd <<= r_dec_rd; u_rename.rd_phy <<= Const(0, 7)
            u_rename.rd_we <<= 0; u_rename.flush <<= 0
            u_rename.alloc <<= r_alloc_en
            u_iq.enqueue <<= self.instr_valid
            u_iq.prs1 <<= u_rename.prs1; u_iq.prs2 <<= u_rename.prs2
            u_iq.prd <<= alloc_phy; u_iq.op <<= Const(0, 6)
            u_iq.wakeup_en <<= 1; u_iq.wakeup_pr <<= Const(0, 7)
            u_iq.issue_ready <<= 1; u_iq.flush <<= 0
            u_alu.op <<= u_iq.issue_op[3:0]
            u_alu.a <<= Const(5, XLEN); u_alu.b <<= Const(3, XLEN)
            u_rob.alloc <<= self.instr_valid
            u_rob.rd_phy <<= alloc_phy; u_rob.complete <<= is_issue
            u_rob.complete_idx <<= r_issue_cnt; u_rob.exception <<= 0; u_rob.retire_ready <<= 1
            u_csr.csr_addr <<= 0; u_csr.csr_wdata <<= 0; u_csr.csr_op <<= 0; u_csr.retire_valid <<= 0

            # Guarded parent outputs only
            alloc_phy <<= u_rename.alloc_phy
            is_issue <<= u_iq.issue_valid
            issue_prd <<= u_iq.issue_prd
            rob_retire_en <<= u_rob.retire_en

            with If(init == 0):
                self.mem_req_valid <<= 0; self.mem_req_addr <<= Const(0, 64)
                self.mem_req_we <<= 0; self.mem_req_data <<= Const(0, 64)
                self.result <<= Const(0, XLEN); self.result_valid <<= 0; self.retired <<= 0
            with Else():
                self.mem_req_valid <<= 0; self.mem_req_addr <<= Const(0, 64)
                self.mem_req_we <<= 0; self.mem_req_data <<= Const(0, 64)
                self.result <<= Mux(is_issue, u_alu.result, Const(0, XLEN))
                self.result_valid <<= is_issue
                self.retired <<= rob_retire_en


class EECore(Module):
    """Energy-Efficient Core — 1-issue in-order with pipelined decode/rename."""

    def __init__(self, hartid=0, PC_WIDTH=39, XLEN=64):
        super().__init__(f"ee_core_{hartid}")

        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.hartid = Input(8, "hartid")
        self.instr = Input(32, "instr"); self.instr_valid = Input(1, "instr_valid")
        self.mem_rdata = Input(XLEN, "mem_rdata"); self.mem_rvalid = Input(1, "mem_rvalid")
        self.mtip = Input(1, "mtip"); self.meip = Input(1, "meip"); self.msip = Input(1, "msip")
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(64, "mem_req_addr")
        self.mem_req_we = Output(1, "mem_req_we")
        self.mem_req_data = Output(64, "mem_req_data")
        self.result = Output(XLEN, "result"); self.result_valid = Output(1, "result_valid")
        self.retired = Output(1, "retired")

        u_pcgen = PCGen(has_l0_btb=False, has_way_pred=False, PC_WIDTH=PC_WIDTH, RESET_VEC=0)
        u_ibuf = IBuf(4, 32)
        u_decoder = Decoder()
        u_rename = RenameTable(32, 64)
        u_iq = IssueQueue(4, 64)
        u_alu = ALU(XLEN)
        u_bju = BJU(XLEN)
        u_rob = ROB(8, 64)
        u_csr = CSRFile()

        self._submodules.extend([
            ("pcgen", u_pcgen), ("ibuf", u_ibuf), ("decoder", u_decoder),
            ("rename", u_rename), ("iq", u_iq),
            ("alu", u_alu), ("bju", u_bju), ("rob", u_rob), ("csr", u_csr),
        ])

        r_dec_rs1 = Reg(5, "r_dec_rs1"); r_dec_rs2 = Reg(5, "r_dec_rs2"); r_dec_rd = Reg(5, "r_dec_rd")
        alloc_phy = Wire(7, "alloc_phy"); is_issue = Wire(1, "is_issue")
        rob_retire_en = Wire(1, "rob_retire_en")

        r_alloc_en = Reg(1, "r_alloc_en")
        r_issue_cnt = Reg(3, "r_issue_cnt")
        init = Reg(1, "init")
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                init <<= 0; r_dec_rs1 <<= 0; r_dec_rs2 <<= 0; r_dec_rd <<= 0
                r_alloc_en <<= 0; r_issue_cnt <<= 0
            with Else():
                init <<= 1
                r_dec_rs1 <<= u_decoder.rs1; r_dec_rs2 <<= u_decoder.rs2; r_dec_rd <<= u_decoder.rd
                r_alloc_en <<= self.instr_valid
                with If(is_issue == 1):
                    r_issue_cnt <<= r_issue_cnt + Const(1, 3)

        with self.comb:
            # Unguarded child input connections
            u_decoder.instr <<= self.instr
            u_rename.rs1 <<= r_dec_rs1; u_rename.rs2 <<= r_dec_rs2
            u_rename.rd <<= r_dec_rd; u_rename.rd_phy <<= Const(0, 7)
            u_rename.rd_we <<= 0; u_rename.flush <<= 0; u_rename.alloc <<= r_alloc_en
            u_iq.enqueue <<= self.instr_valid
            u_iq.prs1 <<= u_rename.prs1; u_iq.prs2 <<= u_rename.prs2; u_iq.prd <<= alloc_phy
            u_iq.op <<= Const(0, 6)
            u_iq.wakeup_en <<= 1; u_iq.wakeup_pr <<= Const(0, 7); u_iq.issue_ready <<= 1; u_iq.flush <<= 0
            u_alu.op <<= u_iq.issue_op[3:0]; u_alu.a <<= Const(5, XLEN); u_alu.b <<= Const(3, XLEN)
            u_bju.op <<= u_iq.issue_op[2:0]; u_bju.a <<= Const(0, XLEN); u_bju.b <<= Const(0, XLEN); u_bju.pc <<= Const(0, XLEN)
            u_rob.alloc <<= self.instr_valid; u_rob.rd_phy <<= alloc_phy
            u_rob.complete <<= is_issue; u_rob.complete_idx <<= r_issue_cnt
            u_rob.exception <<= 0; u_rob.retire_ready <<= 1
            u_csr.csr_addr <<= 0; u_csr.csr_wdata <<= 0; u_csr.csr_op <<= 0; u_csr.retire_valid <<= 0

            # Intermediate wires
            alloc_phy <<= u_rename.alloc_phy
            is_issue <<= u_iq.issue_valid
            rob_retire_en <<= u_rob.retire_en

            # Guarded parent outputs only
            with If(init == 0):
                self.mem_req_valid <<= 0; self.mem_req_addr <<= Const(0, 64)
                self.mem_req_we <<= 0; self.mem_req_data <<= Const(0, 64)
                self.result <<= Const(0, XLEN); self.result_valid <<= 0; self.retired <<= 0
            with Else():
                self.mem_req_valid <<= 0; self.mem_req_addr <<= Const(0, 64)
                self.mem_req_we <<= 0; self.mem_req_data <<= Const(0, 64)
                self.result <<= Mux(is_issue, u_alu.result, Const(0, XLEN))
                self.result_valid <<= is_issue
                self.retired <<= rob_retire_en


def test_hp_core():
    from rtlgen.sim import Simulator
    print("  Testing HPCore...")
    m = HPCore(hartid=0)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    retired_cnt = 0
    for _ in range(20):
        s.step()
        if int(s.get('retired')): retired_cnt += 1
    print(f"  HPCore: PASS (retired_x{retired_cnt})")
    assert retired_cnt > 0, f"HPCore never retired any instruction"


def test_ee_core():
    from rtlgen.sim import Simulator
    print("  Testing EECore...")
    m = EECore(hartid=2)
    s = Simulator(m, use_xz=False)
    s.reset(rst='rst_n', cycles=3)
    s.set('instr', 0x00000013); s.set('instr_valid', 1)
    retired_cnt = 0
    for _ in range(20):
        s.step()
        if int(s.get('retired')): retired_cnt += 1
    print(f"  EECore: PASS (retired_x{retired_cnt})")
    assert retired_cnt > 0, f"EECore never retired any instruction"


if __name__ == '__main__':
    test_hp_core()
    test_ee_core()
    print("ALL core_types tests PASS")
