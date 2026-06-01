"""
L3 DSL — CSRFile.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class CSRFile(Module):
    def __init__(self):
        super().__init__("csrfile")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.csr_addr = Input(12, "csr_addr")
        self.csr_wdata = Input(64, "csr_wdata")
        self.csr_op = Input(3, "csr_op")
        self.retire_valid = Input(1, "retire_valid")
        self.csr_rdata = Output(64, "csr_rdata")
        self.illegal = Output(1, "illegal")

        self.init = Reg(1, "init")
        self.mvendorid = Reg(64, "mvendorid")
        self.marchid = Reg(64, "marchid")
        self.mimpid = Reg(64, "mimpid")
        self.mhartid = Reg(64, "mhartid")
        self.mstatus = Reg(64, "mstatus")
        self.mie = Reg(64, "mie")
        self.mtvec = Reg(64, "mtvec")
        self.mscratch = Reg(64, "mscratch")
        self.mepc = Reg(64, "mepc")
        self.mcause = Reg(64, "mcause")
        self.mtval = Reg(64, "mtval")
        self.mip = Reg(64, "mip")
        self.mcycle = Reg(64, "mcycle")
        self.minstret = Reg(64, "minstret")
        self.stvec = Reg(64, "stvec")
        self.sscratch = Reg(64, "sscratch")
        self.sepc = Reg(64, "sepc")
        self.scause = Reg(64, "scause")
        self.stval = Reg(64, "stval")
        self.satp = Reg(64, "satp")
        self.misa = Reg(64, "misa")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.csr_rdata <<= 0
                self.illegal <<= 0
            with Else():
                with If(self.csr_addr == 0xF11):
                    self.csr_rdata <<= self.mvendorid
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0xF12):
                    self.csr_rdata <<= self.marchid
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0xF13):
                    self.csr_rdata <<= self.mimpid
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0xF14):
                    self.csr_rdata <<= self.mhartid
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x300):
                    self.csr_rdata <<= self.mstatus
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x304):
                    self.csr_rdata <<= self.mie
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x305):
                    self.csr_rdata <<= self.mtvec
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x340):
                    self.csr_rdata <<= self.mscratch
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x341):
                    self.csr_rdata <<= self.mepc
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x342):
                    self.csr_rdata <<= self.mcause
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x343):
                    self.csr_rdata <<= self.mtval
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x344):
                    self.csr_rdata <<= self.mip
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0xB00):
                    self.csr_rdata <<= self.mcycle
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0xB02):
                    self.csr_rdata <<= self.minstret
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x105):
                    self.csr_rdata <<= self.stvec
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x140):
                    self.csr_rdata <<= self.sscratch
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x141):
                    self.csr_rdata <<= self.sepc
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x142):
                    self.csr_rdata <<= self.scause
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x143):
                    self.csr_rdata <<= self.stval
                    self.illegal <<= 0
                with Elif(self.csr_addr == 0x180):
                    self.csr_rdata <<= self.satp
                    self.illegal <<= 0
                with Else():
                    self.illegal <<= 1

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                self.mvendorid <<= 0x9E4
                self.marchid <<= 0x04
                self.mimpid <<= 0x01
                self.mhartid <<= 0x00
            with Else():
                self.init <<= 1
                self.mcycle <<= self.mcycle + 1
                with If(self.retire_valid == 1):
                    self.minstret <<= self.minstret + 1
                with If(self.csr_op != 0):
                    with If(self.csr_addr == 0x300):
                        self.mstatus <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x304):
                        self.mie <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x305):
                        self.mtvec <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x340):
                        self.mscratch <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x341):
                        self.mepc <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x342):
                        self.mcause <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x343):
                        self.mtval <<= self.csr_wdata
                    with Elif(self.csr_addr == 0xB00):
                        self.mcycle <<= self.csr_wdata
                    with Elif(self.csr_addr == 0xB02):
                        self.minstret <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x105):
                        self.stvec <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x140):
                        self.sscratch <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x141):
                        self.sepc <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x142):
                        self.scause <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x143):
                        self.stval <<= self.csr_wdata
                    with Elif(self.csr_addr == 0x180):
                        self.satp <<= self.csr_wdata
