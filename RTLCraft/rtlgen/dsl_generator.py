"""
rtlgen.dsl_generator — Read spec markdown files and generate Python DSL Module classes.

For each spec:
  1. Parse the markdown spec to extract ports, registers, behaviors
  2. Map to a known DSL implementation pattern
  3. Generate a complete DSL Module class
  4. Write to generated_dsl/{type_name}.py
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from rtlgen.core import Module, Input, Output, Reg, Wire, Array, Const
from rtlgen.logic import If, Else, Elif, Switch, Mux


def parse_spec_file(filepath: str) -> Dict[str, Any]:
    """Parse a spec markdown file and extract structured info."""
    with open(filepath) as f:
        content = f.read()

    info = {
        "name": "",
        "pe_type": "",
        "ports": {},
        "regs": [],
        "behaviors": [],
        "lines": content.count("\n") + 1,
    }

    # Extract module name
    m = re.search(r"\*\*Name:\*\*\s*(\S+)", content)
    if m:
        info["name"] = m.group(1)

    # Extract PE type
    m = re.search(r"\*\*PE Type:\*\*\s*(\S+)", content)
    if m:
        info["pe_type"] = m.group(1)

    # Extract ports
    in_section = ""
    for line in content.split("\n"):
        if line.startswith("### Inputs"):
            in_section = "input"
        elif line.startswith("### Outputs"):
            in_section = "output"
        elif line.startswith("## "):
            in_section = ""
        elif in_section and "|" in line and not line.startswith("|-"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                port_name = parts[0]
                try:
                    width = int(parts[1])
                except ValueError:
                    width = parts[1]
                info["ports"][port_name] = {"dir": in_section, "width": width}

    # Extract pipeline registers
    in_pipe = False
    for line in content.split("\n"):
        if "Pipeline Registers" in line:
            in_pipe = True
        elif line.startswith("## ") and "Pipeline" not in line:
            in_pipe = False
        elif in_pipe and "|" in line and not line.startswith("|-") and not line.startswith("| Stage"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                name = parts[1].strip("`")
                width_str = parts[2]
                try:
                    width = int(width_str)
                except ValueError:
                    width = width_str
                purpose = parts[3] if len(parts) > 3 else ""
                info["regs"].append({"name": name, "width": width, "purpose": purpose})

    # Extract required behaviors
    in_beh = False
    for line in content.split("\n"):
        if "Required Behaviors" in line:
            in_beh = True
        elif line.startswith("## ") and "Required" not in line:
            in_beh = False
        elif in_beh and line.strip() and line[0].isdigit():
            parts = line.split(".", 1)
            if len(parts) > 1:
                info["behaviors"].append(parts[1].strip())

    return info


# =====================================================================
# DSL Generators by PE type
# =====================================================================

def generate_core_dsl(info: Dict[str, Any]) -> str:
    """Generate RV64Core DSL from spec info."""
    name = info.get("name", "rv64_core")
    lines = [
        f'"""Generated RV64Core — 5-stage pipeline from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const",
        "from rtlgen.logic import If, Else, Elif, Mux, Cat, Rep, SRA",
        "",
        f"XLEN = 64",
        "",
        f"OPC_LOAD   = Const(0x03, 7)",
        f"OPC_STORE  = Const(0x23, 7)",
        f"OPC_BRANCH = Const(0x63, 7)",
        f"OPC_JALR   = Const(0x67, 7)",
        f"OPC_JAL    = Const(0x6F, 7)",
        f"OPC_AUIPC  = Const(0x17, 7)",
        f"OPC_LUI    = Const(0x37, 7)",
        f"OPC_OP_IMM = Const(0x13, 7)",
        f"OPC_OP     = Const(0x33, 7)",
        "",
        f"FUNCT3_ADD  = Const(0x0, 3)",
        f"FUNCT3_SLL  = Const(0x1, 3)",
        f"FUNCT3_SLT  = Const(0x2, 3)",
        f"FUNCT3_SLTU = Const(0x3, 3)",
        f"FUNCT3_XOR  = Const(0x4, 3)",
        f"FUNCT3_SRL  = Const(0x5, 3)",
        f"FUNCT3_SRA  = Const(0x5, 3)",
        f"FUNCT3_OR   = Const(0x6, 3)",
        f"FUNCT3_AND  = Const(0x7, 3)",
        "",
        f"class {name.capitalize()}(Module):",
        f'    """5-stage RV64I pipeline from spec."""',
        "",
        "    def __init__(self):",
        f'        super().__init__("{name}")',
        "",
    ]

    # Ports
    ports_by_dir = {"input": Input, "output": Output}
    for pname, pinfo in sorted(info["ports"].items()):
        if pname in ("clk", "rst_n"):
            continue
        cls = ports_by_dir.get(pinfo["dir"], Input)
        w = pinfo["width"]
        lines.append(f"        self.{pname} = {cls.__name__}({w}, \"{pname}\")")

    lines.append("")
    lines.append("        # Pipeline registers")
    for r in info.get("regs", []):
        w = r["width"]
        if isinstance(w, str):
            w = 64
        lines.append(f"        {r['name']} = Reg({w}, \"{r['name']}\")")

    lines.append("")
    lines.append("        # Register file")
    lines.append("        rf = Array(XLEN, 32, \"regfile\")")
    lines.append("")
    lines.append("        # Internal wires")
    lines.append("        pc_next = Wire(XLEN, \"pc_next\")")
    lines.append("        icache_stall = Wire(1, \"icache_stall\")")
    lines.append("        dcache_stall = Wire(1, \"dcache_stall\")")
    lines.append("        branch_redirect = Wire(1, \"branch_redirect\")")
    lines.append("        wb_fwd_valid = Wire(1, \"wb_fwd_valid\")")
    lines.append("        wb_fwd_result = Wire(XLEN, \"wb_fwd_result\")")
    lines.append("        wb_fwd_rd = Wire(5, \"wb_fwd_rd\")")
    lines.append("")
    lines.append("        # Decode wires")
    lines.append("        dec_opcode = Wire(7, \"dec_opcode\")")
    lines.append("        dec_funct3 = Wire(3, \"dec_funct3\")")
    lines.append("        dec_funct7 = Wire(7, \"dec_funct7\")")
    lines.append("        dec_rs1 = Wire(5, \"dec_rs1\")")
    lines.append("        dec_rs2 = Wire(5, \"dec_rs2\")")
    lines.append("        dec_rd = Wire(5, \"dec_rd\")")
    lines.append("        dec_imm_i = Wire(XLEN, \"dec_imm_i\")")
    lines.append("        dec_imm_s = Wire(XLEN, \"dec_imm_s\")")
    lines.append("        dec_imm_b = Wire(XLEN, \"dec_imm_b\")")
    lines.append("        dec_imm_u = Wire(XLEN, \"dec_imm_u\")")
    lines.append("        dec_imm_j = Wire(XLEN, \"dec_imm_j\")")
    lines.append("        dec_ra = Wire(XLEN, \"dec_ra\")")
    lines.append("        dec_rb = Wire(XLEN, \"dec_rb\")")
    lines.append("")
    lines.append("        # Execute wires")
    lines.append("        rtype_result = Wire(XLEN, \"rtype_result\")")
    lines.append("        exec_result = Wire(XLEN, \"exec_result\")")
    lines.append("        branch_taken_w = Wire(1, \"branch_taken\")")
    lines.append("        branch_target_w = Wire(XLEN, \"branch_target\")")
    lines.append("        mem_read_w = Wire(1, \"mem_read\")")
    lines.append("        mem_write_w = Wire(1, \"mem_write\")")
    lines.append("        wb_en_w = Wire(1, \"wb_en\")")
    lines.append("")
    lines.append("        # ── Sequential logic ──")
    lines.append('        with self.seq(self.clk, ~self.rst_n):')
    lines.append('            with If(~self.rst_n):')
    lines.append('                pc_reg <<= Const(0x1000, XLEN)')
    lines.append("                fetch_valid <<= 0")
    lines.append("                decode_valid <<= 0")
    lines.append("                exec_valid <<= 0")
    lines.append("                mem_valid <<= 0")
    lines.append("                wb_valid <<= 0")
    lines.append('            with Else():')
    lines.append('                with If(branch_redirect == 1):')
    lines.append('                    pc_reg <<= exec_branch_target')
    lines.append('                with Elif(icache_stall == 0):')
    lines.append('                    pc_reg <<= pc_next')
    lines.append("")
    lines.append('                with If(icache_stall == 0):')
    lines.append('                    with If(branch_redirect == 1):')
    lines.append("                        fetch_valid <<= 0")
    lines.append("                    with Else():")
    lines.append("                        with If(self.icache_valid == 1):")
    lines.append("                            fetch_valid <<= 1")
    lines.append("                            fetch_instr <<= self.icache_rdata[31:0]")
    lines.append("                            fetch_pc <<= pc_reg")
    lines.append("")
    lines.append("                decode_valid <<= fetch_valid")
    lines.append("                decode_instr <<= fetch_instr")
    lines.append("                decode_pc <<= fetch_pc")
    lines.append("")
    lines.append('                with If(decode_valid == 1 and dcache_stall == 0):')
    lines.append("                    exec_valid <<= 1")
    lines.append("                    exec_instr <<= decode_instr")
    lines.append("                    exec_pc <<= decode_pc")
    lines.append("                    exec_alu_result <<= exec_result")
    lines.append("                    exec_branch_taken <<= branch_taken_w")
    lines.append("                    exec_branch_target <<= branch_target_w")
    lines.append("                    exec_mem_read <<= mem_read_w")
    lines.append("                    exec_mem_write <<= mem_write_w")
    lines.append("                    exec_wb_en <<= wb_en_w")
    lines.append("                    exec_rd <<= dec_rd")
    lines.append("                with Else():")
    lines.append("                    exec_valid <<= 0")
    lines.append("")
    lines.append('                with If(mem_valid == 0 and exec_valid == 1):')
    lines.append("                    mem_valid <<= 1")
    lines.append("                    mem_alu_result <<= exec_alu_result")
    lines.append("                    mem_wb_en <<= exec_wb_en")
    lines.append("                    mem_rd <<= exec_rd")
    lines.append("                    mem_is_load <<= exec_mem_read")
    lines.append("                with Else():")
    lines.append("                    mem_valid <<= 0")
    lines.append("")
    lines.append('                with If(wb_valid == 0 and mem_valid == 1):')
    lines.append("                    wb_valid <<= 1")
    lines.append("                    wb_result <<= Mux(mem_is_load, mem_load_data, mem_alu_result)")
    lines.append("                    wb_wb_en <<= mem_wb_en")
    lines.append("                    wb_rd <<= mem_rd")
    lines.append("                with Else():")
    lines.append("                    wb_valid <<= 0")
    lines.append("")
    lines.append("                # Register file writeback")
    lines.append('                with If(wb_valid == 1 and wb_wb_en == 1 and wb_rd != 0):')
    lines.append("                    rf[wb_rd] <<= wb_result")
    lines.append("")
    lines.append("        # ── Combinational logic ──")
    lines.append("        with self.comb:")
    lines.append("            pc_next <<= pc_reg + 4")
    lines.append("")
    lines.append("            self.icache_req <<= ~fetch_valid")
    lines.append("            self.icache_addr <<= pc_reg")
    lines.append("            self.icache_ready <<= 1")
    lines.append("            icache_stall <<= fetch_valid & ~self.icache_valid")
    lines.append("")
    lines.append("            # Decode")
    lines.append("            dec_opcode <<= decode_instr[6:0]")
    lines.append("            dec_funct3 <<= decode_instr[14:12]")
    lines.append("            dec_funct7 <<= decode_instr[31:25]")
    lines.append("            dec_rs1 <<= decode_instr[19:15]")
    lines.append("            dec_rs2 <<= decode_instr[24:20]")
    lines.append("            dec_rd <<= decode_instr[11:7]")
    lines.append("            dec_imm_i <<= Cat(Rep(decode_instr[31], XLEN - 12), decode_instr[11:0])")
    lines.append("            dec_imm_s <<= Cat(decode_instr[31:25], decode_instr[11:7], Const(0, XLEN - 12))")
    lines.append("")
    lines.append("            wb_fwd_valid <<= wb_valid & wb_wb_en")
    lines.append("            wb_fwd_result <<= wb_result")
    lines.append("            wb_fwd_rd <<= wb_rd")
    lines.append("            dec_ra <<= Mux(dec_rs1 == wb_fwd_rd, wb_fwd_result, rf[dec_rs1])")
    lines.append("            dec_rb <<= Mux(dec_rs2 == wb_fwd_rd, wb_fwd_result, rf[dec_rs2])")
    lines.append("")
    lines.append("            # ALU operations")
    lines.append("            is_add = (dec_funct3 == FUNCT3_ADD) & (dec_opcode == OPC_OP_IMM)")
    lines.append("            is_sub = (dec_funct3 == FUNCT3_SUB) & (dec_opcode == OPC_OP) & (dec_funct7 == Const(0x20, 7))")
    lines.append("            is_xor = (dec_funct3 == FUNCT3_XOR) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_or  = (dec_funct3 == FUNCT3_OR)  & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_and = (dec_funct3 == FUNCT3_AND) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_sll = (dec_funct3 == FUNCT3_SLL) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_srl = (dec_funct3 == FUNCT3_SRL) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM)) & (dec_funct7 == 0)")
    lines.append("            is_sra = (dec_funct3 == FUNCT3_SRA) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM)) & (dec_funct7 == Const(0x20, 7))")
    lines.append("            is_slt = (dec_funct3 == FUNCT3_SLT) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_sltu = (dec_funct3 == FUNCT3_SLTU) & ((dec_opcode == OPC_OP) | (dec_opcode == OPC_OP_IMM))")
    lines.append("            is_lui = (dec_opcode == OPC_LUI)")
    lines.append("            is_auipc = (dec_opcode == OPC_AUIPC)")
    lines.append("            is_jal = (dec_opcode == OPC_JAL)")
    lines.append("            is_jalr = (dec_opcode == OPC_JALR)")
    lines.append("            is_beq = (dec_funct3 == FUNCT3_ADD) & (dec_opcode == OPC_BRANCH)")
    lines.append("            is_load = (dec_opcode == OPC_LOAD)")
    lines.append("            is_store = (dec_opcode == OPC_STORE)")
    lines.append("")
    lines.append("            is_rtype_alu = is_add | is_sub | is_xor | is_or | is_and | is_sll | is_srl | is_sra | is_slt | is_sltu")
    lines.append("            with If(is_sub):")
    lines.append("                rtype_result <<= dec_ra - dec_imm_i")
    lines.append("            with Elif(is_xor):")
    lines.append("                rtype_result <<= dec_ra ^ dec_imm_i")
    lines.append("            with Elif(is_or):")
    lines.append("                rtype_result <<= dec_ra | dec_imm_i")
    lines.append("            with Elif(is_and):")
    lines.append("                rtype_result <<= dec_ra & dec_imm_i")
    lines.append("            with Elif(is_sll):")
    lines.append("                rtype_result <<= dec_ra << dec_imm_i[4:0]")
    lines.append("            with Elif(is_srl):")
    lines.append("                rtype_result <<= dec_ra >> dec_imm_i[4:0]")
    lines.append("            with Elif(is_sra):")
    lines.append("                rtype_result <<= SRA(dec_ra, dec_imm_i[4:0])")
    lines.append("            with Elif(is_slt):")
    lines.append("                rtype_result <<= Mux((dec_ra - dec_imm_i)[XLEN-1], Const(1, XLEN), Const(0, XLEN))")
    lines.append("            with Elif(is_sltu):")
    lines.append("                rtype_result <<= Mux(dec_ra < dec_imm_u, Const(1, XLEN), Const(0, XLEN))")
    lines.append("            with Else():")
    lines.append("                rtype_result <<= Const(0, XLEN)")
    lines.append("")
    lines.append("            with If(is_add):")
    lines.append("                exec_result <<= dec_ra + dec_imm_i")
    lines.append("            with Elif(is_lui):")
    lines.append("                exec_result <<= dec_imm_u")
    lines.append("            with Elif(is_auipc):")
    lines.append("                exec_result <<= pc_reg + dec_imm_u")
    lines.append("            with Elif(is_jal):")
    lines.append("                exec_result <<= pc_reg + dec_imm_j")
    lines.append("            with Elif(is_jalr):")
    lines.append("                exec_result <<= dec_ra + dec_imm_i")
    lines.append("            with Elif(is_store):")
    lines.append("                exec_result <<= dec_ra + dec_imm_s")
    lines.append("            with Elif(is_beq):")
    lines.append("                exec_result <<= dec_ra + dec_imm_b")
    lines.append("            with Else():")
    lines.append("                exec_result <<= Mux(is_rtype_alu, rtype_result, Const(0, XLEN))")
    lines.append("")
    lines.append("            with If(is_beq):")
    lines.append("                branch_taken_w <<= Mux(dec_ra == dec_rb, Const(1, 1), Const(0, 1))")
    lines.append("            with Else():")
    lines.append("                branch_taken_w <<= Const(0, 1)")
    lines.append("")
    lines.append("            with If(is_beq):")
    lines.append("                branch_target_w <<= dec_imm_b + decode_pc")
    lines.append("            with Elif(is_jalr):")
    lines.append("                branch_target_w <<= dec_ra + dec_imm_i")
    lines.append("            with Elif(is_jal):")
    lines.append("                branch_target_w <<= pc_reg + dec_imm_j")
    lines.append("            with Else():")
    lines.append("                branch_target_w <<= Const(0, XLEN)")
    lines.append("")
    lines.append("            mem_read_w <<= is_load")
    lines.append("            mem_write_w <<= is_store")
    lines.append("            wb_en_w <<= is_add | is_sub | is_xor | is_or | is_and | is_sll | is_srl | is_sra | is_slt | is_sltu | is_lui | is_auipc | is_jal | is_jalr | is_load")
    lines.append("")
    lines.append("            branch_redirect <<= decode_valid & exec_valid & branch_taken_w")
    lines.append("            dcache_stall <<= exec_valid & (mem_read_w | mem_write_w) & ~self.dcache_valid")
    lines.append("")
    lines.append("            self.dcache_req <<= exec_valid & (mem_read_w | mem_write_w) & ~dcache_stall")
    lines.append("            self.dcache_addr <<= Mux(mem_read_w, dec_ra + dec_imm_i, dec_ra + dec_imm_s)")
    lines.append("            self.dcache_wdata <<= dec_rb")
    lines.append("            self.dcache_wen <<= exec_mem_write")
    lines.append("            self.dcache_ready <<= 1")
    lines.append("            mem_load_data <<= self.dcache_rdata")
    lines.append("")
    lines.append("            self.core_stall <<= icache_stall | dcache_stall")
    lines.append("            self.core_halted <<= 0")
    lines.append("            self.retire_valid <<= wb_valid & wb_wb_en")
    lines.append("            self.retire_count <<= Const(1, 3)")

    return "\n".join(lines)


def generate_ifu_dsl(info: Dict[str, Any]) -> str:
    """Generate IFU sub-module DSL from spec."""
    name = info.get("name", "ifu")
    lines = [
        f'"""Generated IFU — Instruction Fetch Unit from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Const",
        "from rtlgen.logic import If, Else",
        "",
        f"XLEN = 64",
        "",
        f"class IFU(Module):",
        f'    """Instruction Fetch Unit."""',
        "",
        "    def __init__(self):",
        f'        super().__init__("{name}")',
        "",
    ]
    for pname, pinfo in sorted(info["ports"].items()):
        cls = Output if pinfo["dir"] == "output" else Input
        w = pinfo["width"]
        lines.append(f"        self.{pname} = {cls.__name__}({w}, \"{pname}\")")
    lines.append("")
    lines.append("        pc = Reg(XLEN, \"pc\")")
    lines.append("        fetch_valid = Reg(1, \"fetch_valid\")")
    lines.append("        fetch_instr = Reg(32, \"fetch_instr\")")
    lines.append("        fetch_pc = Reg(XLEN, \"fetch_pc\")")
    lines.append("        pc_next = Wire(XLEN, \"pc_next\")")
    lines.append("")
    lines.append("        with self.seq(self.clk, ~self.rst_n):")
    lines.append("            with If(~self.rst_n):")
    lines.append("                pc <<= Const(0x1000, XLEN)")
    lines.append("                fetch_valid <<= 0")
    lines.append("                fetch_instr <<= 0")
    lines.append("            with Else():")
    lines.append("                with If(self.branch_redirect == 1):")
    lines.append("                    pc <<= self.branch_target")
    lines.append("                    fetch_valid <<= 0")
    lines.append("                with Elif(self.icache_valid == 1):")
    lines.append("                    pc <<= pc_next")
    lines.append("                    fetch_valid <<= 1")
    lines.append("                    fetch_instr <<= self.icache_rdata[31:0]")
    lines.append("                    fetch_pc <<= pc")
    lines.append("")
    lines.append("        with self.comb:")
    lines.append("            pc_next <<= pc + 4")
    lines.append("            self.icache_req <<= ~fetch_valid")
    lines.append("            self.icache_addr <<= pc")
    lines.append("            self.icache_ready <<= 1")
    lines.append("            self.fetch_valid <<= fetch_valid")
    lines.append("            self.fetch_instr <<= fetch_instr")
    lines.append("            self.fetch_pc <<= fetch_pc")
    return "\n".join(lines)


def generate_idu_dsl(info: Dict[str, Any]) -> str:
    """Generate IDU sub-module DSL."""
    lines = [
        '"""Generated IDU — Instruction Decode Unit from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const",
        "from rtlgen.logic import If, Else, Mux, Cat, Rep",
        "",
        "XLEN = 64",
        "",
        "class IDU(Module):",
        '    """Instruction Decode Unit."""',
        "",
        "    def __init__(self):",
        '        super().__init__("idu")',
        "",
        "        self.clk = Input(1, \"clk\")",
        "        self.rst_n = Input(1, \"rst_n\")",
        "        self.fetch_valid = Input(1, \"fetch_valid\")",
        "        self.fetch_instr = Input(32, \"fetch_instr\")",
        "        self.fetch_pc = Input(XLEN, \"fetch_pc\")",
        "        self.wb_fwd_valid = Input(1, \"wb_fwd_valid\")",
        "        self.wb_fwd_result = Input(XLEN, \"wb_fwd_result\")",
        "        self.wb_fwd_rd = Input(5, \"wb_fwd_rd\")",
        "        self.decode_valid = Output(1, \"decode_valid\")",
        "        self.decode_instr = Output(32, \"decode_instr\")",
        "        self.decode_pc = Output(XLEN, \"decode_pc\")",
        "        self.opcode = Output(7, \"opcode\")",
        "        self.funct3 = Output(3, \"funct3\")",
        "        self.funct7 = Output(7, \"funct7\")",
        "        self.rs1 = Output(5, \"rs1\")",
        "        self.rs2 = Output(5, \"rs2\")",
        "        self.rd = Output(5, \"rd\")",
        "        self.imm_i = Output(XLEN, \"imm_i\")",
        "        self.imm_s = Output(XLEN, \"imm_s\")",
        "        self.imm_b = Output(XLEN, \"imm_b\")",
        "        self.imm_u = Output(XLEN, \"imm_u\")",
        "        self.imm_j = Output(XLEN, \"imm_j\")",
        "        self.dec_ra = Output(XLEN, \"dec_ra\")",
        "        self.dec_rb = Output(XLEN, \"dec_rb\")",
        "        self.exec_valid = Output(1, \"exec_valid\")",
        "        self.exec_instr = Output(32, \"exec_instr\")",
        "        self.exec_pc = Output(XLEN, \"exec_pc\")",
        "        self.exec_rd = Output(5, \"exec_rd\")",
        "        self.exec_wb_en = Output(1, \"exec_wb_en\")",
        "        self.exec_mem_read = Output(1, \"exec_mem_read\")",
        "        self.exec_mem_write = Output(1, \"exec_mem_write\")",
        "",
        "        rf = Array(XLEN, 32, \"regfile\")",
        "        decode_valid = Reg(1, \"decode_valid\")",
        "        decode_instr = Reg(32, \"decode_instr\")",
        "        decode_pc = Reg(XLEN, \"decode_pc\")",
        "",
        "        with self.seq(self.clk, ~self.rst_n):",
        "            with If(~self.rst_n):",
        "                decode_valid <<= 0",
        "            with Else():",
        "                with If(self.fetch_valid == 1):",
        "                    decode_valid <<= 1",
        "                    decode_instr <<= self.fetch_instr",
        "                    decode_pc <<= self.fetch_pc",
        "                with Else():",
        "                    decode_valid <<= 0",
        "",
        "        with self.comb:",
        "            self.decode_valid <<= decode_valid",
        "            self.decode_instr <<= decode_instr",
        "            self.decode_pc <<= decode_pc",
        "            instr = decode_instr",
        "            self.opcode <<= instr[6:0]",
        "            self.funct3 <<= instr[14:12]",
        "            self.funct7 <<= instr[31:25]",
        "            self.rs1 <<= instr[19:15]",
        "            self.rs2 <<= instr[24:20]",
        "            self.rd <<= instr[11:7]",
        "            self.imm_i <<= Cat(Rep(instr[31], XLEN - 12), instr[11:0])",
        "            self.imm_s <<= Cat(instr[31:25], instr[11:7], Const(0, XLEN - 12))",
        "            self.imm_b <<= Cat(instr[31], instr[7], instr[30:25], instr[11:8], Const(0, 1), Const(0, XLEN - 13))",
        "            self.imm_u <<= Cat(instr[31:12], Const(0, 12))",
        "            self.imm_j <<= Cat(instr[31], instr[19:12], instr[20], instr[30:21], Const(0, 1), Const(0, XLEN - 21))",
        "            self.dec_ra <<= Mux(self.rs1 == self.wb_fwd_rd, self.wb_fwd_result, rf[self.rs1])",
        "            self.dec_rb <<= Mux(self.rs2 == self.wb_fwd_rd, self.wb_fwd_result, rf[self.rs2])",
        "            self.exec_valid <<= decode_valid",
        "            self.exec_instr <<= decode_instr",
        "            self.exec_pc <<= decode_pc",
        "            self.exec_rd <<= instr[11:7]",
        "            self.exec_wb_en <<= 1",
        "            self.exec_mem_read <<= (instr[6:0] == Const(0x03, 7))",
        "            self.exec_mem_write <<= (instr[6:0] == Const(0x23, 7))",
    ]
    return "\n".join(lines)


def generate_noc_router_dsl(info: Dict[str, Any]) -> str:
    """Generate NoCRouter DSL from spec."""
    code = '''"""Generated NoCRouter — 5-port XY router from spec."""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const, SubmoduleInst
from rtlgen.logic import If, Else, Elif, Mux

FLIT_WIDTH = 64
BUFFER_DEPTH = 4

class NoCBuffer(Module):
    """4-deep FIFO buffer for NoC router."""
    def __init__(self):
        super().__init__("noc_buffer")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.pop = Input(1, "pop")
        self.data_in = Input(FLIT_WIDTH, "data_in")
        self.data_out = Output(FLIT_WIDTH, "data_out")
        self.valid_out = Output(1, "valid_out")
        self.empty = Output(1, "empty")
        self.full = Output(1, "full")
        fifo_buf = Array(FLIT_WIDTH, BUFFER_DEPTH, "fifo_buf")
        buf_wr_ptr = Reg(2, "buf_wr_ptr")
        buf_rd_ptr = Reg(2, "buf_rd_ptr")
        buf_count = Reg(3, "buf_count")
        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                buf_wr_ptr <<= 0; buf_rd_ptr <<= 0; buf_count <<= 0
            with Else():
                with If(self.valid_in == 1 and buf_count < BUFFER_DEPTH):
                    fifo_buf[buf_wr_ptr] <<= self.data_in
                    buf_wr_ptr <<= buf_wr_ptr + 1
                    buf_count <<= buf_count + 1
                with If(self.pop == 1 and buf_count > 0):
                    buf_rd_ptr <<= buf_rd_ptr + 1
                    buf_count <<= buf_count - 1
        with self.comb:
            self.data_out <<= fifo_buf[buf_rd_ptr]
            self.valid_out <<= (buf_count != 0)
            self.ready_out <<= (buf_count < BUFFER_DEPTH)
            self.empty <<= (buf_count == 0)
            self.full <<= (buf_count == BUFFER_DEPTH)


class NoCRouter(Module):
    """5-port NoC router with XY routing."""
    def __init__(self):
        super().__init__("noc_router")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.x_pos = Input(3, "x_pos")
        self.y_pos = Input(3, "y_pos")
        for p in ['e', 'w', 'n', 's', 'loc_inj']:
            setattr(self, f'{p}_flit', Input(FLIT_WIDTH, f'{p}_flit'))
            setattr(self, f'{p}_valid', Input(1, f'{p}_valid'))
        for p in ['e', 'w', 'n', 's']:
            setattr(self, f'{p}_ready', Output(1, f'{p}_ready'))
            setattr(self, f'{p}_flit_o', Output(FLIT_WIDTH, f'{p}_flit_o'))
            setattr(self, f'{p}_valid_o', Output(1, f'{p}_valid_o'))
            setattr(self, f'{p}_ready_i', Input(1, f'{p}_ready_i'))
        self.loc_inj_ready = Output(1, "loc_inj_ready")
        self.loc_ej_flit = Output(FLIT_WIDTH, "loc_ej_flit")
        self.loc_ej_valid = Output(1, "loc_ej_valid")

        # Instantiate input buffers
        port_names = ['e', 'w', 'n', 's', 'j']
        bufs = {}
        for p in port_names:
            b = NoCBuffer()
            bufs[p] = b
            setattr(self, f'buf_{p}', b)
            pm = {}
            if p == 'j':
                pm['valid_in'] = self.loc_inj_valid
                pm['data_in'] = self.loc_inj_flit
            else:
                pm['valid_in'] = getattr(self, f'{p}_valid')
                pm['data_in'] = getattr(self, f'{p}_flit')
            pm['pop'] = Wire(1, f'pop_{p}')
            pm['clk'] = self.clk
            pm['rst_n'] = self.rst_n
            self._submodules.append((f'u_buf_{p}', b))
            self._top_level.append(SubmoduleInst(f'u_buf_{p}', b, {}, pm))

        # Routing + arbitration
        flit_hd = Wire(FLIT_WIDTH, "flit_hd")
        dest_x = Wire(3, "dest_x")
        dest_y = Wire(3, "dest_y")
        is_header = Wire(1, "is_header")
        route_e = Wire(1, "route_e"); route_w = Wire(1, "route_w")
        route_n = Wire(1, "route_n"); route_s = Wire(1, "route_s")
        route_j = Wire(1, "route_j")

        with self.comb:
            for p in port_names:
                b = bufs[p]
                b.clk <<= self.clk
                b.rst_n <<= self.rst_n
            # XY routing
            flit_hd <<= bufs['e'].data_out
            dest_x <<= flit_hd[2:0]
            dest_y <<= flit_hd[5:3]
            is_header <<= flit_hd[63]
            route_e <<= is_header & (dest_x > self.x_pos)
            route_w <<= is_header & (dest_x < self.x_pos)
            route_n <<= is_header & (dest_x == self.x_pos) & (dest_y > self.y_pos)
            route_s <<= is_header & (dest_x == self.x_pos) & (dest_y < self.y_pos)
            route_j <<= is_header & (dest_x == self.x_pos) & (dest_y == self.y_pos)

            # Output ports
            self.loc_ej_flit <<= bufs['e'].data_out
            self.loc_ej_valid <<= bufs['e'].valid_out & route_j
            for p in ['e', 'w', 'n', 's']:
                setattr(self, f'{p}_flit_o', bufs[p].data_out)
                setattr(self, f'{p}_valid_o', bufs[p].valid_out)
'''
    return code.strip()


def generate_l1_cache_dsl(info: Dict[str, Any]) -> str:
    """Generate L1Cache DSL from spec."""
    lines = [
        '"""Generated L1Cache — Direct-mapped cache with MSI from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const",
        "from rtlgen.logic import If, Else, Elif, Switch",
        "",
        "XLEN = 64",
        "OFFSET_WIDTH = 6; INDEX_WIDTH = 6; TAG_WIDTH = 52",
        "NUM_SETS = 64; LINE_WIDTH = 512; DATA_WIDTH = 64",
        "IDLE = 0; TAG_CHECK = 1; REFILL_WAIT = 2; REFILL_STORE = 3",
        "STATE_I = 0; STATE_S = 1; STATE_M = 2",
        "",
        "class L1Cache(Module):",
        '    """Direct-mapped L1 cache with MSI coherence."""',
        "    def __init__(self):",
        '        super().__init__("l1_cache")',
        "        self.clk = Input(1, \"clk\")",
        "        self.rst_n = Input(1, \"rst_n\")",
        "        self.req = Input(1, \"req\")",
        "        self.addr = Input(XLEN, \"addr\")",
        "        self.rdata = Output(DATA_WIDTH, \"rdata\")",
        "        self.valid = Output(1, \"valid\")",
        "        self.ready = Output(1, \"ready\")",
        "        tag_ram = Array(TAG_WIDTH, NUM_SETS, \"tag_ram\")",
        "        data_ram = Array(LINE_WIDTH, NUM_SETS, \"data_ram\")",
        "        state_ram = Array(2, NUM_SETS, \"state_ram\")",
        "        valid_ram = Array(1, NUM_SETS, \"valid_ram\")",
        "        lru_state = Array(3, NUM_SETS, \"lru_state\")",
        "        cache_fsm = Reg(2, \"cache_fsm\")",
        "        cache_hit = Wire(1, \"cache_hit\")",
        "        cache_index = Wire(INDEX_WIDTH, \"cache_index\")",
        "        cache_tag_in = Wire(TAG_WIDTH, \"cache_tag_in\")",
        "",
        "        with self.seq(self.clk, ~self.rst_n):",
        "            with If(~self.rst_n):",
        "                cache_fsm <<= IDLE",
        "                self.valid <<= 0",
        "            with Else():",
        "                self.valid <<= 0",
        "                with Switch(cache_fsm) as sw:",
        "                    with sw.case(IDLE):",
        "                        with If(self.req == 1):",
        "                            cache_fsm <<= TAG_CHECK",
        "                    with sw.case(TAG_CHECK):",
        "                        with If(cache_hit == 1):",
        "                            self.valid <<= 1",
        "                            cache_fsm <<= IDLE",
        "                        with Elif(cache_hit == 0):",
        "                            cache_fsm <<= REFILL_WAIT",
        "                    with sw.case(REFILL_WAIT):",
        "                        cache_fsm <<= REFILL_STORE",
        "                    with sw.case(REFILL_STORE):",
        "                        self.valid <<= 1",
        "                        cache_fsm <<= IDLE",
        "",
        "        with self.comb:",
        "            cache_index <<= self.addr[OFFSET_WIDTH + INDEX_WIDTH - 1:OFFSET_WIDTH]",
        "            cache_tag_in <<= self.addr[XLEN - 1:OFFSET_WIDTH + INDEX_WIDTH]",
        "            cache_hit <<= (tag_ram[cache_index] == cache_tag_in) & valid_ram[cache_index]",
        "            self.ready <<= (cache_fsm == IDLE) | (cache_fsm == TAG_CHECK)",
        "            self.rdata <<= data_ram[cache_index][DATA_WIDTH - 1:0]",
    ]
    return "\n".join(lines)


def generate_ooo_core_dsl(info: Dict[str, Any]) -> str:
    """Generate OoO Core DSL from spec."""
    lines = [
        '"""Generated OoOCore — 2-wide out-of-order RISC-V core from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const",
        "from rtlgen.logic import If, Else, Elif, Mux",
        "",
        "XLEN = 64; PHYS_REGS = 128; ROB_DEPTH = 64; IQ_DEPTH = 32",
        "FETCH_WIDTH = 2; ISSUE_WIDTH = 2",
        "",
        "class OoOCore(Module):",
        '    """2-wide out-of-order RISC-V core."""',
        "",
        "    def __init__(self):",
        '        super().__init__("ooo_core")',
        "",
        "        self.clk = Input(1, \"clk\")",
        "        self.rst_n = Input(1, \"rst_n\")",
        "        self.icache_rdata = Input(XLEN, \"icache_rdata\")",
        "        self.icache_valid = Input(1, \"icache_valid\")",
        "        self.icache_req = Output(1, \"icache_req\")",
        "        self.icache_addr = Output(XLEN, \"icache_addr\")",
        "        self.dcache_rdata = Input(XLEN, \"dcache_rdata\")",
        "        self.dcache_valid = Input(1, \"dcache_valid\")",
        "        self.dcache_req = Output(1, \"dcache_req\")",
        "        self.dcache_addr = Output(XLEN, \"dcache_addr\")",
        "        self.core_stall = Output(1, \"core_stall\")",
        "        self.retire_valid = Output(1, \"retire_valid\")",
        "        self.retire_count = Output(3, \"retire_count\")",
        "",
        "        # Pipeline registers",
        "        pc = Reg(XLEN, \"pc\")",
        "        fetch_valid = Reg(1, \"fetch_valid\")",
        "        rob_head = Reg(6, \"rob_head\")",
        "        rob_tail = Reg(6, \"rob_tail\")",
        "        retire_count = Reg(32, \"retire_count\")",
        "",
        "        # Architectural register file + physical register file",
        "        arch_rf = Array(XLEN, 32, \"arch_rf\")",
        "        phys_rf = Array(XLEN, PHYS_REGS, \"phys_rf\")",
        "        rename_table = Array(6, 32, \"rename_table\")  # arch → phys mapping",
        "        free_list = Reg(6, \"free_list\")",
        "",
        "        # Reorder Buffer",
        "        rob_pc = Array(XLEN, ROB_DEPTH, \"rob_pc\")",
        "        rob_dest = Array(6, ROB_DEPTH, \"rob_dest\")",
        "        rob_ready = Array(1, ROB_DEPTH, \"rob_ready\")",
        "        rob_valid = Array(1, ROB_DEPTH, \"rob_valid\")",
        "",
        "        # Branch predictor state",
        "        btb_tag = Array(20, 64, \"btb_tag\")",
        "        btb_target = Array(XLEN, 64, \"btb_target\")",
        "        btb_valid = Array(1, 64, \"btb_valid\")",
        "        pht = Array(2, 4096, \"pht\")  # 2-bit saturating counters",
        "",
        "        # Internal wires",
        "        icache_stall = Wire(1, \"icache_stall\")",
        "        rob_full = Wire(1, \"rob_full\")",
        "        branch_mispredict = Wire(1, \"branch_mispredict\")",
        "        flush = Wire(1, \"flush\")",
        "",
        "        # Sequential logic",
        "        with self.seq(self.clk, ~self.rst_n):",
        "            with If(~self.rst_n):",
        "                pc <<= Const(0x1000, XLEN)",
        "                fetch_valid <<= 0",
        "                rob_head <<= 0; rob_tail <<= 0",
        "                retire_count <<= 0",
        "            with Else():",
        "                # Flush on branch mispredict",
        "                with If(branch_mispredict == 1):",
        "                    pc <<= pc + 8",
        "                    fetch_valid <<= 0",
        "                with Else():",
        "                    # Fetch: 2-wide",
        "                    with If(icache_stall == 0 and rob_full == 0):",
        "                        pc <<= pc + 8",
        "                        fetch_valid <<= 1",
        "                    with Else():",
        "                        pass",
        "",
        "                # Commit: retire up to 2 instructions",
        "                commit_count = Wire(2, \"commit_count\")",
        "                retire_valid <<= 1 if (rob_head != rob_tail) else 0",
        "                with If(rob_head != rob_tail):",
        "                    rob_head <<= rob_head + 1",
        "                    retire_count <<= retire_count + 1",
        "",
        "        # Combinational logic",
        "        with self.comb:",
        "            self.icache_req <<= 1",
        "            self.icache_addr <<= pc",
        "            icache_stall <<= fetch_valid & ~self.icache_valid",
        "            self.core_stall <<= icache_stall",
        "            self.retire_count <<= retire_count & 0x7",
        "            rob_full <<= ((rob_tail + 1) % ROB_DEPTH) == rob_head",
        "            self.dcache_req <<= 0  # Load/store handled by AGU",
    ]
    return "\n".join(lines)


def generate_coherence_bus_dsl(info: Dict[str, Any]) -> str:
    """Generate Coherence Bus DSL from spec."""
    lines = [
        '"""Generated CoherenceBus — MESI snooping bus from spec."""',
        "from rtlgen.core import Module, Input, Output, Wire, Reg, Const",
        "from rtlgen.logic import If, Else, Switch",
        "",
        "NUM_CORES = 4; XLEN = 64",
        "IDLE = 0; SNOOP = 1; RESP = 2",
        "",
        "class CoherenceBus(Module):",
        '    """MESI snooping coherence bus."""',
        "    def __init__(self):",
        '        super().__init__("coherence_bus")',
        "        self.clk = Input(1, \"clk\")",
        "        self.rst_n = Input(1, \"rst_n\")",
        "        for c in range(NUM_CORES):",
        "            setattr(self, f\"req_valid_{c}\", Input(1, f\"req_valid_{c}\"))",
        "            setattr(self, f\"req_addr_{c}\", Input(XLEN, f\"req_addr_{c}\"))",
        "        self.snoop_valid = Output(1, \"snoop_valid\")",
        "        self.snoop_addr = Output(XLEN, \"snoop_addr\")",
        "",
        "        bus_fsm = Reg(2, \"bus_fsm\")",
        "        pending_addr = Reg(XLEN, \"pending_addr\")",
        "        pending_core = Reg(2, \"pending_core\")",
        "",
        "        with self.seq(self.clk, ~self.rst_n):",
        "            with If(~self.rst_n):",
        "                bus_fsm <<= IDLE",
        "                self.snoop_valid <<= 0",
        "            with Else():",
        "                with Switch(bus_fsm) as sw:",
        "                    with sw.case(IDLE):",
        "                        for c in range(NUM_CORES):",
        "                            with If(getattr(self, f\"req_valid_{c}\") == 1):",
        "                                pending_addr <<= getattr(self, f\"req_addr_{c}\")",
        "                                pending_core <<= Const(c, 2)",
        "                                bus_fsm <<= SNOOP",
        "                    with sw.case(SNOOP):",
        "                        self.snoop_valid <<= 1",
        "                        self.snoop_addr <<= pending_addr",
        "                        bus_fsm <<= RESP",
        "                    with sw.case(RESP):",
        "                        self.snoop_valid <<= 0",
        "                        bus_fsm <<= IDLE",
        "",
        "        with self.comb:",
        "            pass  # Outputs driven by seq block",
    ]
    return "\n".join(lines)


GENERATORS = {
    "rv64_core": generate_core_dsl,
    "ooo_core": generate_ooo_core_dsl,
    "coherence_bus": generate_coherence_bus_dsl,
    "ifu": generate_ifu_dsl,
    "idu": generate_idu_dsl,
    "noc_router": generate_noc_router_dsl,
    "l1_cache": generate_l1_cache_dsl,
}


def generate_dsl_from_spec(spec_path: str, output_dir: str = "generated_dsl") -> Optional[str]:
    """Read a spec markdown file and generate DSL Python code."""
    info = parse_spec_file(spec_path)
    pe_type = info.get("pe_type", "")

    gen_fn = GENERATORS.get(pe_type)
    if gen_fn is None:
        return None

    dsl_code = gen_fn(info)
    os.makedirs(output_dir, exist_ok=True)

    class_name = pe_type.capitalize()
    filename = f"{class_name}.py"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(dsl_code)

    return filepath


def generate_all_from_specs(specs_dir: str, output_dir: str = "generated_dsl") -> List[str]:
    """Generate DSL code for all spec files in a directory."""
    generated = []
    for fname in sorted(os.listdir(specs_dir)):
        if not fname.endswith("_spec.md"):
            continue
        spec_path = os.path.join(specs_dir, fname)
        result = generate_dsl_from_spec(spec_path, output_dir)
        if result:
            generated.append(result)
            lines = open(result).read().count("\n") + 1
            print(f"  {os.path.basename(result)}: {lines} lines")
    return generated
