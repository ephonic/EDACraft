"""
BOOM CSR (Control and Status Register) File

Implements the M-mode CSR subset required for basic exception/interrupt handling:
  - mstatus  (0x300): global interrupt enable, privilege mode
  - mie      (0x304): interrupt enable bits
  - mtvec    (0x305): trap vector base address
  - mscratch (0x340): scratch register
  - mepc     (0x341): exception program counter
  - mcause   (0x342): trap cause
  - mip      (0x344): interrupt pending bits
  - mcycle   (0xB00): cycle counter
  - minstret (0xB02): instruction retire counter

Trap handling (hardware):
  1. Save PC to mepc
  2. Write cause to mcause
  3. mstatus.MIE -> mstatus.MPIE, mstatus.MIE = 0
  4. Next PC = mtvec

MRET (software):
  1. mstatus.MPIE -> mstatus.MIE, mstatus.MPIE = 1
  2. Next PC = mepc

Simplifications:
  - Only M-mode (no S/U mode)
  - No misa, mvendorid, etc. (read-only CSRs return 0)
  - No counter-inhibit (mcycle always increments)
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else, Mux


class CSRFile(Module):
    """M-mode CSR register file with trap handling."""

    def __init__(self, xlen: int = 32, name: str = "CSRFile"):
        super().__init__(name)
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # CSR read/write port
        self.csr_addr = Input(12, "csr_addr")
        self.csr_wdata = Input(xlen, "csr_wdata")
        self.csr_we = Input(1, "csr_we")
        self.csr_re = Input(1, "csr_re")
        self.csr_op = Input(2, "csr_op")   # 0=write, 1=set, 2=clear
        self.csr_rdata = Output(xlen, "csr_rdata")

        # Trap interface
        self.trap_valid = Input(1, "trap_valid")
        self.trap_pc = Input(xlen, "trap_pc")
        self.trap_cause = Input(xlen, "trap_cause")
        self.mret_valid = Input(1, "mret_valid")

        # Interrupt inputs
        self.irq = Input(1, "irq")
        self.timer_irq = Input(1, "timer_irq")
        self.sw_irq = Input(1, "sw_irq")

        # Outputs
        self.trap_vector = Output(xlen, "trap_vector")
        self.mepc_out = Output(xlen, "mepc_out")
        self.mstatus_mie = Output(1, "mstatus_mie")

        # CSR registers
        self.mstatus = Reg(xlen, "mstatus")
        self.mie = Reg(xlen, "mie")
        self.mtvec = Reg(xlen, "mtvec")
        self.mscratch = Reg(xlen, "mscratch")
        self.mepc = Reg(xlen, "mepc")
        self.mcause = Reg(xlen, "mcause")
        self.mip = Reg(xlen, "mip")
        self.mcycle = Reg(xlen, "mcycle")
        self.minstret = Reg(xlen, "minstret")

        # --- CSR read decode ---
        self.csr_rdata_comb = Wire(xlen, "csr_rdata_comb")

        @self.comb
        def _csr_read():
            self.csr_rdata_comb <<= 0
            # Use multiple independent If blocks (Python loop unrolls)
            # mstatus = 0x300
            with If(self.csr_addr == 0x300):
                self.csr_rdata_comb <<= self.mstatus
            with If(self.csr_addr == 0x304):
                self.csr_rdata_comb <<= self.mie
            with If(self.csr_addr == 0x305):
                self.csr_rdata_comb <<= self.mtvec
            with If(self.csr_addr == 0x340):
                self.csr_rdata_comb <<= self.mscratch
            with If(self.csr_addr == 0x341):
                self.csr_rdata_comb <<= self.mepc
            with If(self.csr_addr == 0x342):
                self.csr_rdata_comb <<= self.mcause
            with If(self.csr_addr == 0x344):
                self.csr_rdata_comb <<= self.mip
            with If(self.csr_addr == 0xB00):
                self.csr_rdata_comb <<= self.mcycle
            with If(self.csr_addr == 0xB02):
                self.csr_rdata_comb <<= self.minstret

        self.csr_rdata <<= self.csr_rdata_comb

        # --- Sequential: writes, traps, counters ---
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _csr_seq():
            with If(self.rst_n == 0):
                self.mstatus <<= 0
                self.mie <<= 0
                self.mtvec <<= 0
                self.mscratch <<= 0
                self.mepc <<= 0
                self.mcause <<= 0
                self.mip <<= 0
                self.mcycle <<= 0
                self.minstret <<= 0
            with Else():
                # Cycle counter always increments
                self.mcycle <<= self.mcycle + 1

                # Assemble mip from interrupt inputs
                self.mip <<= ((self.irq & 1) << 11) | ((self.timer_irq & 1) << 7) | ((self.sw_irq & 1) << 3)

                # Trap entry: save state
                with If(self.trap_valid):
                    self.mepc <<= self.trap_pc
                    self.mcause <<= self.trap_cause
                    # mstatus.MIE (bit 3) -> mstatus.MPIE (bit 7)
                    # mstatus.MIE = 0
                    self.mstatus <<= (self.mstatus & ~((1 << 3) | (1 << 7))) | (((self.mstatus >> 3) & 1) << 7)

                # MRET: restore state
                with If(self.mret_valid):
                    # mstatus.MPIE (bit 7) -> mstatus.MIE (bit 3)
                    # mstatus.MPIE = 1
                    self.mstatus <<= (self.mstatus & ~((1 << 3) | (1 << 7))) | ((((self.mstatus >> 7) & 1) << 3) | (1 << 7))

                # CSR write
                with If(self.csr_we):
                    self._write_csr(0x300, self.mstatus)
                    self._write_csr(0x304, self.mie)
                    self._write_csr(0x305, self.mtvec)
                    self._write_csr(0x340, self.mscratch)
                    self._write_csr(0x341, self.mepc)
                    self._write_csr(0x342, self.mcause)

        self.trap_vector <<= self.mtvec
        self.mepc_out <<= self.mepc
        self.mstatus_mie <<= (self.mstatus >> 3) & 1

    def _write_csr(self, addr: int, reg):
        """Helper to emit CSR write/update/clear logic for a given register."""
        with If(self.csr_addr == addr):
            with If(self.csr_op == 0):
                reg <<= self.csr_wdata
            with Else():
                with If(self.csr_op == 1):
                    reg <<= reg | self.csr_wdata
                with Else():
                    with If(self.csr_op == 2):
                        reg <<= reg & ~self.csr_wdata
