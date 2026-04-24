"""
BOOM Decode Unit

Decodes raw RV32I instructions into control signals for the rename/issue stages.
Handles all major RV32I instruction formats:
  - R-type: register-register ALU ops
  - I-type: immediate ALU, loads, JALR
  - S-type: stores
  - B-type: branches
  - U-type: LUI, AUIPC
  - J-type: JAL
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


# RISC-V RV32I opcodes
OPCODE_LOAD = 0b0000011
OPCODE_STORE = 0b0100011
OPCODE_BRANCH = 0b1100011
OPCODE_JALR = 0b1100111
OPCODE_JAL = 0b1101111
OPCODE_OP_IMM = 0b0010011
OPCODE_OP = 0b0110011
OPCODE_LUI = 0b0110111
OPCODE_AUIPC = 0b0010111
OPCODE_SYSTEM = 0b1110011

# ALU op encoding
ALU_ADD = 0b0000
ALU_SUB = 0b0001
ALU_SLL = 0b0010
ALU_SLT = 0b0011
ALU_SLTU = 0b0100
ALU_XOR = 0b0101
ALU_SRL = 0b0110
ALU_SRA = 0b0111
ALU_OR = 0b1000
ALU_AND = 0b1001
ALU_BEQ = 0b1010
ALU_BNE = 0b1011
ALU_BLT = 0b1100
ALU_BGE = 0b1101
ALU_BLTU = 0b1110
ALU_BGEU = 0b1111


class DecodeUnit(Module):
    """RISC-V RV32I instruction decoder."""

    def __init__(self, xlen: int = 32, width: int = 2, name: str = "DecodeUnit"):
        super().__init__(name)
        self.xlen = xlen
        self.width = width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Input from fetch
        self.fetch_valid = Input(width, "fetch_valid")
        self.fetch_instr = Vector(32, width, "fetch_instr", vtype=Input)
        self.fetch_pc = Input(xlen, "fetch_pc")

        # Decoded output
        self.dec_valid = Output(width, "dec_valid")
        self.dec_rs1 = Vector(5, width, "dec_rs1", vtype=Output)
        self.dec_rs2 = Vector(5, width, "dec_rs2", vtype=Output)
        self.dec_rd = Vector(5, width, "dec_rd", vtype=Output)
        self.dec_need_rs1 = Output(width, "dec_need_rs1")
        self.dec_need_rs2 = Output(width, "dec_need_rs2")
        self.dec_need_rd = Output(width, "dec_need_rd")
        self.dec_imm = Vector(xlen, width, "dec_imm", vtype=Output)
        self.dec_use_imm = Output(width, "dec_use_imm")
        self.dec_is_load = Output(width, "dec_is_load")
        self.dec_is_store = Output(width, "dec_is_store")
        self.dec_is_branch = Output(width, "dec_is_branch")
        self.dec_is_jump = Output(width, "dec_is_jump")
        self.dec_is_alu = Output(width, "dec_is_alu")
        self.dec_is_mul = Output(width, "dec_is_mul")
        self.dec_alu_op = Vector(4, width, "dec_alu_op", vtype=Output)
        self.dec_mem_size = Vector(2, width, "dec_mem_size", vtype=Output)
        self.dec_mem_signed = Output(width, "dec_mem_signed")
        self.dec_pc = Vector(xlen, width, "dec_pc", vtype=Output)
        # CSR / Exception signals
        self.dec_is_csr = Output(width, "dec_is_csr")
        self.dec_is_ecall = Output(width, "dec_is_ecall")
        self.dec_is_ebreak = Output(width, "dec_is_ebreak")
        self.dec_is_mret = Output(width, "dec_is_mret")
        self.dec_csr_addr = Vector(12, width, "dec_csr_addr", vtype=Output)

        # Create per-instruction wires as self attributes
        for w in range(width):
            setattr(self, f"opcode_{w}", Wire(7, f"opcode_{w}"))
            setattr(self, f"rd_{w}", Wire(5, f"rd_{w}"))
            setattr(self, f"rs1_{w}", Wire(5, f"rs1_{w}"))
            setattr(self, f"rs2_{w}", Wire(5, f"rs2_{w}"))
            setattr(self, f"funct3_{w}", Wire(3, f"funct3_{w}"))
            setattr(self, f"funct7_{w}", Wire(7, f"funct7_{w}"))
            setattr(self, f"imm_i_{w}", Wire(xlen, f"imm_i_{w}"))
            setattr(self, f"imm_s_{w}", Wire(xlen, f"imm_s_{w}"))
            setattr(self, f"imm_b_{w}", Wire(xlen, f"imm_b_{w}"))
            setattr(self, f"imm_u_{w}", Wire(xlen, f"imm_u_{w}"))
            setattr(self, f"imm_j_{w}", Wire(xlen, f"imm_j_{w}"))
            setattr(self, f"is_r_{w}", Wire(1, f"is_r_{w}"))
            setattr(self, f"is_i_{w}", Wire(1, f"is_i_{w}"))
            setattr(self, f"is_s_{w}", Wire(1, f"is_s_{w}"))
            setattr(self, f"is_b_{w}", Wire(1, f"is_b_{w}"))
            setattr(self, f"is_u_{w}", Wire(1, f"is_u_{w}"))
            setattr(self, f"is_j_{w}", Wire(1, f"is_j_{w}"))
            setattr(self, f"alu_op_{w}", Wire(4, f"alu_op_{w}"))
            setattr(self, f"imm_sel_{w}", Wire(xlen, f"imm_sel_{w}"))
            setattr(self, f"use_imm_w_{w}", Wire(1, f"use_imm_w_{w}"))
            setattr(self, f"need_rs1_w_{w}", Wire(1, f"need_rs1_w_{w}"))
            setattr(self, f"need_rs2_w_{w}", Wire(1, f"need_rs2_w_{w}"))
            setattr(self, f"need_rd_w_{w}", Wire(1, f"need_rd_w_{w}"))
            setattr(self, f"is_load_w_{w}", Wire(1, f"is_load_w_{w}"))
            setattr(self, f"is_store_w_{w}", Wire(1, f"is_store_w_{w}"))
            setattr(self, f"is_br_w_{w}", Wire(1, f"is_br_w_{w}"))
            setattr(self, f"is_jump_w_{w}", Wire(1, f"is_jump_w_{w}"))
            setattr(self, f"is_alu_w_{w}", Wire(1, f"is_alu_w_{w}"))
            setattr(self, f"is_mul_w_{w}", Wire(1, f"is_mul_w_{w}"))
            setattr(self, f"mem_sz_{w}", Wire(2, f"mem_sz_{w}"))
            setattr(self, f"mem_sg_{w}", Wire(1, f"mem_sg_{w}"))
            setattr(self, f"is_csr_{w}", Wire(1, f"is_csr_{w}"))
            setattr(self, f"is_ecall_{w}", Wire(1, f"is_ecall_{w}"))
            setattr(self, f"is_ebreak_{w}", Wire(1, f"is_ebreak_{w}"))
            setattr(self, f"is_mret_{w}", Wire(1, f"is_mret_{w}"))
            setattr(self, f"csr_addr_{w}", Wire(12, f"csr_addr_{w}"))

        @self.comb
        def _extract():
            for w in range(width):
                instr = self.fetch_instr[w]
                opcode = getattr(self, f"opcode_{w}")
                rd = getattr(self, f"rd_{w}")
                rs1 = getattr(self, f"rs1_{w}")
                rs2 = getattr(self, f"rs2_{w}")
                funct3 = getattr(self, f"funct3_{w}")
                funct7 = getattr(self, f"funct7_{w}")
                imm_i = getattr(self, f"imm_i_{w}")
                imm_s = getattr(self, f"imm_s_{w}")
                imm_b = getattr(self, f"imm_b_{w}")
                imm_u = getattr(self, f"imm_u_{w}")
                imm_j = getattr(self, f"imm_j_{w}")

                opcode <<= instr[6:0]
                rd <<= instr[11:7]
                rs1 <<= instr[19:15]
                rs2 <<= instr[24:20]
                funct3 <<= instr[14:12]
                funct7 <<= instr[31:25]

                # I-type immediate (sign-extended)
                imm_i <<= instr[31:20]
                with If(instr[31] == 1):
                    imm_i <<= instr[31:20] | (((1 << (xlen - 12)) - 1) << 12)

                # S-type immediate
                imm_s <<= (instr[31:25] << 5) | instr[11:7]
                with If(instr[31] == 1):
                    imm_s <<= ((instr[31:25] << 5) | instr[11:7]) | (((1 << (xlen - 12)) - 1) << 12)

                # B-type immediate
                imm_b <<= ((instr[31] << 12) | (instr[7] << 11) | (instr[30:25] << 5) | (instr[11:8] << 1))
                with If(instr[31] == 1):
                    imm_b <<= ((instr[31] << 12) | (instr[7] << 11) | (instr[30:25] << 5) | (instr[11:8] << 1)) | (((1 << (xlen - 13)) - 1) << 13)

                # U-type immediate
                imm_u <<= instr[31:12] << 12

                # J-type immediate
                imm_j <<= ((instr[31] << 20) | (instr[19:12] << 12) | (instr[20] << 11) | (instr[30:21] << 1))
                with If(instr[31] == 1):
                    imm_j <<= ((instr[31] << 20) | (instr[19:12] << 12) | (instr[20] << 11) | (instr[30:21] << 1)) | (((1 << (xlen - 21)) - 1) << 21)

        @self.comb
        def _decode_ctrl():
            for w in range(width):
                instr = self.fetch_instr[w]
                opcode = getattr(self, f"opcode_{w}")
                funct3 = getattr(self, f"funct3_{w}")
                funct7 = getattr(self, f"funct7_{w}")
                imm_i = getattr(self, f"imm_i_{w}")
                imm_s = getattr(self, f"imm_s_{w}")
                imm_b = getattr(self, f"imm_b_{w}")
                imm_u = getattr(self, f"imm_u_{w}")
                imm_j = getattr(self, f"imm_j_{w}")
                is_r = getattr(self, f"is_r_{w}")
                is_i = getattr(self, f"is_i_{w}")
                is_s = getattr(self, f"is_s_{w}")
                is_b = getattr(self, f"is_b_{w}")
                is_u = getattr(self, f"is_u_{w}")
                is_j = getattr(self, f"is_j_{w}")
                alu_op = getattr(self, f"alu_op_{w}")
                imm_sel = getattr(self, f"imm_sel_{w}")
                use_imm = getattr(self, f"use_imm_w_{w}")
                need_rs1 = getattr(self, f"need_rs1_w_{w}")
                need_rs2 = getattr(self, f"need_rs2_w_{w}")
                need_rd = getattr(self, f"need_rd_w_{w}")
                is_load = getattr(self, f"is_load_w_{w}")
                is_store = getattr(self, f"is_store_w_{w}")
                is_branch = getattr(self, f"is_br_w_{w}")
                is_jump = getattr(self, f"is_jump_w_{w}")
                is_alu = getattr(self, f"is_alu_w_{w}")
                is_mul = getattr(self, f"is_mul_w_{w}")
                mem_size = getattr(self, f"mem_sz_{w}")
                mem_signed = getattr(self, f"mem_sg_{w}")
                is_csr = getattr(self, f"is_csr_{w}")
                is_ecall = getattr(self, f"is_ecall_{w}")
                is_ebreak = getattr(self, f"is_ebreak_{w}")
                is_mret = getattr(self, f"is_mret_{w}")
                csr_addr = getattr(self, f"csr_addr_{w}")

                is_r <<= (opcode == OPCODE_OP)
                is_i <<= (opcode == OPCODE_OP_IMM) | (opcode == OPCODE_LOAD) | (opcode == OPCODE_JALR)
                is_s <<= (opcode == OPCODE_STORE)
                is_b <<= (opcode == OPCODE_BRANCH)
                is_u <<= (opcode == OPCODE_LUI) | (opcode == OPCODE_AUIPC)
                is_j <<= (opcode == OPCODE_JAL)

                # Default control signals
                alu_op <<= ALU_ADD
                imm_sel <<= 0
                use_imm <<= 0
                need_rs1 <<= 0
                need_rs2 <<= 0
                need_rd <<= 0
                is_load <<= 0
                is_store <<= 0
                is_branch <<= 0
                is_jump <<= 0
                is_alu <<= 0
                is_mul <<= 0
                mem_size <<= 0
                mem_signed <<= 0
                is_csr <<= 0
                is_ecall <<= 0
                is_ebreak <<= 0
                is_mret <<= 0
                csr_addr <<= 0

                # OP / R-type
                with If(opcode == OPCODE_OP):
                    need_rs1 <<= 1
                    need_rs2 <<= 1
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_alu <<= 1
                    use_imm <<= 0

                    with If(funct3 == 0b000):
                        with If(funct7 == 0b0000000):
                            alu_op <<= ALU_ADD
                        with Else():
                            with If(funct7 == 0b0100000):
                                alu_op <<= ALU_SUB
                            with Else():
                                with If(funct7 == 0b0000001):
                                    is_mul <<= 1
                    with Else():
                        with If(funct3 == 0b001):
                            alu_op <<= ALU_SLL
                        with Else():
                            with If(funct3 == 0b010):
                                alu_op <<= ALU_SLT
                            with Else():
                                with If(funct3 == 0b011):
                                    alu_op <<= ALU_SLTU
                                with Else():
                                    with If(funct3 == 0b100):
                                        alu_op <<= ALU_XOR
                                    with Else():
                                        with If(funct3 == 0b101):
                                            with If(funct7 == 0b0000000):
                                                alu_op <<= ALU_SRL
                                            with Else():
                                                alu_op <<= ALU_SRA
                                        with Else():
                                            with If(funct3 == 0b110):
                                                alu_op <<= ALU_OR
                                            with Else():
                                                with If(funct3 == 0b111):
                                                    alu_op <<= ALU_AND

                # OP-IMM / I-type ALU
                with If(opcode == OPCODE_OP_IMM):
                    need_rs1 <<= 1
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_i

                    with If(funct3 == 0b000):
                        alu_op <<= ALU_ADD
                    with Else():
                        with If(funct3 == 0b001):
                            alu_op <<= ALU_SLL
                        with Else():
                            with If(funct3 == 0b010):
                                alu_op <<= ALU_SLT
                            with Else():
                                with If(funct3 == 0b011):
                                    alu_op <<= ALU_SLTU
                                with Else():
                                    with If(funct3 == 0b100):
                                        alu_op <<= ALU_XOR
                                    with Else():
                                        with If(funct3 == 0b101):
                                            with If(instr[30] == 0):
                                                alu_op <<= ALU_SRL
                                            with Else():
                                                alu_op <<= ALU_SRA
                                        with Else():
                                            with If(funct3 == 0b110):
                                                alu_op <<= ALU_OR
                                            with Else():
                                                with If(funct3 == 0b111):
                                                    alu_op <<= ALU_AND

                # Load
                with If(opcode == OPCODE_LOAD):
                    need_rs1 <<= 1
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_load <<= 1
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_i
                    alu_op <<= ALU_ADD
                    mem_size <<= funct3[1:0]
                    mem_signed <<= ~funct3[2]

                # Store
                with If(opcode == OPCODE_STORE):
                    need_rs1 <<= 1
                    need_rs2 <<= 1
                    is_store <<= 1
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_s
                    alu_op <<= ALU_ADD
                    mem_size <<= funct3[1:0]

                # Branch
                with If(opcode == OPCODE_BRANCH):
                    need_rs1 <<= 1
                    need_rs2 <<= 1
                    is_branch <<= 1
                    use_imm <<= 0

                    with If(funct3 == 0b000):
                        alu_op <<= ALU_BEQ
                    with Else():
                        with If(funct3 == 0b001):
                            alu_op <<= ALU_BNE
                        with Else():
                            with If(funct3 == 0b100):
                                alu_op <<= ALU_BLT
                            with Else():
                                with If(funct3 == 0b101):
                                    alu_op <<= ALU_BGE
                                with Else():
                                    with If(funct3 == 0b110):
                                        alu_op <<= ALU_BLTU
                                    with Else():
                                        with If(funct3 == 0b111):
                                            alu_op <<= ALU_BGEU

                # LUI
                with If(opcode == OPCODE_LUI):
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_u
                    alu_op <<= ALU_ADD

                # AUIPC
                with If(opcode == OPCODE_AUIPC):
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_u
                    alu_op <<= ALU_ADD

                # JAL
                with If(opcode == OPCODE_JAL):
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_jump <<= 1
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_j
                    alu_op <<= ALU_ADD

                # JALR
                with If(opcode == OPCODE_JALR):
                    need_rs1 <<= 1
                    need_rd <<= (getattr(self, f"rd_{w}") != 0)
                    is_jump <<= 1
                    is_alu <<= 1
                    use_imm <<= 1
                    imm_sel <<= imm_i
                    alu_op <<= ALU_ADD

                # SYSTEM (CSR / ECALL / EBREAK / MRET)
                with If(opcode == OPCODE_SYSTEM):
                    with If(funct3 == 0b000):
                        # ECALL, EBREAK, MRET (and other privileged instructions)
                        need_rs1 <<= 0
                        need_rs2 <<= 0
                        need_rd <<= 0
                        with If(instr[31:20] == 0):
                            is_ecall <<= 1
                        with Else():
                            with If(instr[31:20] == 1):
                                is_ebreak <<= 1
                            with Else():
                                with If(instr[31:20] == 0x302):
                                    is_mret <<= 1
                    with Else():
                        # CSR instructions: CSRRW, CSRRS, CSRRC, CSRRWI, CSRRSI, CSRRCI
                        is_csr <<= 1
                        is_alu <<= 1  # goes through ALU for result writeback
                        csr_addr <<= instr[31:20]
                        use_imm <<= (funct3[2] == 1)  # CSRRxI use zimm in rs1 field
                        imm_sel <<= instr[19:15]  # zimm for CSRRxI
                        with If(funct3[2] == 0):
                            # CSRRW / CSRRS / CSRRC: need rs1
                            need_rs1 <<= 1
                        need_rd <<= (getattr(self, f"rd_{w}") != 0)
                        alu_op <<= ALU_ADD  # CSR result passes through ALU

        @self.comb
        def _outputs():
            for w in range(width):
                self.dec_valid[w] <<= self.fetch_valid[w]
                self.dec_rs1[w] <<= getattr(self, f"rs1_{w}")
                self.dec_rs2[w] <<= getattr(self, f"rs2_{w}")
                self.dec_rd[w] <<= getattr(self, f"rd_{w}")
                self.dec_need_rs1[w] <<= getattr(self, f"need_rs1_w_{w}")
                self.dec_need_rs2[w] <<= getattr(self, f"need_rs2_w_{w}")
                self.dec_need_rd[w] <<= getattr(self, f"need_rd_w_{w}")
                self.dec_imm[w] <<= getattr(self, f"imm_sel_{w}")
                self.dec_use_imm[w] <<= getattr(self, f"use_imm_w_{w}")
                self.dec_is_load[w] <<= getattr(self, f"is_load_w_{w}")
                self.dec_is_store[w] <<= getattr(self, f"is_store_w_{w}")
                self.dec_is_branch[w] <<= getattr(self, f"is_br_w_{w}")
                self.dec_is_jump[w] <<= getattr(self, f"is_jump_w_{w}")
                self.dec_is_alu[w] <<= getattr(self, f"is_alu_w_{w}")
                self.dec_is_mul[w] <<= getattr(self, f"is_mul_w_{w}")
                self.dec_alu_op[w] <<= getattr(self, f"alu_op_{w}")
                self.dec_mem_size[w] <<= getattr(self, f"mem_sz_{w}")
                self.dec_mem_signed[w] <<= getattr(self, f"mem_sg_{w}")
                self.dec_pc[w] <<= self.fetch_pc + (w * 4)
                self.dec_is_csr[w] <<= getattr(self, f"is_csr_{w}")
                self.dec_is_ecall[w] <<= getattr(self, f"is_ecall_{w}")
                self.dec_is_ebreak[w] <<= getattr(self, f"is_ebreak_{w}")
                self.dec_is_mret[w] <<= getattr(self, f"is_mret_{w}")
                self.dec_csr_addr[w] <<= getattr(self, f"csr_addr_{w}")
