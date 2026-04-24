"""Unit tests for BOOM submodules."""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

import pytest
from rtlgen.sim import Simulator
from rtlgen.codegen import VerilogEmitter

from skills.cpu.boom.frontend.decode_unit import DecodeUnit
from skills.cpu.boom.backend.csr_file import CSRFile
from skills.cpu.boom.backend.dcache import DCache
from skills.cpu.boom.backend.execution_units import ALU, Multiplier


# ---------------------------------------------------------------------------
# DecodeUnit tests
# ---------------------------------------------------------------------------

def test_decode_addi():
    """DecodeUnit should recognize ADDI."""
    dec = DecodeUnit(xlen=32, width=2)
    sim = Simulator(dec)
    sim.reset('rst_n')

    # ADDI x1, x0, 5 = 0x00500093
    sim.poke('fetch_valid', 0b01)
    sim.poke('fetch_instr_0', 0x00500093)
    sim.poke('fetch_pc', 0x1000)
    sim.step()

    assert sim.peek('dec_valid') & 1 == 1
    assert sim.peek('dec_rs1_0') == 0
    assert sim.peek('dec_rd_0') == 1
    assert (sim.peek('dec_is_alu') >> 0) & 1 == 1
    assert (sim.peek('dec_use_imm') >> 0) & 1 == 1
    assert (sim.peek('dec_is_csr') >> 0) & 1 == 0


def test_decode_csr():
    """DecodeUnit should recognize CSRRW."""
    dec = DecodeUnit(xlen=32, width=1)
    sim = Simulator(dec)
    sim.reset('rst_n')

    # CSRRW x1, mstatus, x2 = 0x301110F3
    # csr_addr = 0x301, rd = 1, rs1 = 2, funct3 = 001
    sim.poke('fetch_valid', 0b01)
    sim.poke('fetch_instr_0', 0x301110F3)
    sim.poke('fetch_pc', 0x1000)
    sim.step()

    assert (sim.peek('dec_is_csr') >> 0) & 1 == 1
    assert sim.peek('dec_csr_addr_0') == 0x301
    assert sim.peek('dec_rs1_0') == 2
    assert sim.peek('dec_rd_0') == 1


def test_decode_ecall():
    """DecodeUnit should recognize ECALL."""
    dec = DecodeUnit(xlen=32, width=1)
    sim = Simulator(dec)
    sim.reset('rst_n')

    # ECALL = 0x00000073
    sim.poke('fetch_valid', 0b01)
    sim.poke('fetch_instr_0', 0x00000073)
    sim.poke('fetch_pc', 0x1000)
    sim.step()

    assert (sim.peek('dec_is_ecall') >> 0) & 1 == 1
    assert (sim.peek('dec_is_csr') >> 0) & 1 == 0


def test_decode_mret():
    """DecodeUnit should recognize MRET."""
    dec = DecodeUnit(xlen=32, width=1)
    sim = Simulator(dec)
    sim.reset('rst_n')

    # MRET = 0x30200073
    sim.poke('fetch_valid', 0b01)
    sim.poke('fetch_instr_0', 0x30200073)
    sim.poke('fetch_pc', 0x1000)
    sim.step()

    assert (sim.peek('dec_is_mret') >> 0) & 1 == 1


# ---------------------------------------------------------------------------
# CSRFile tests
# ---------------------------------------------------------------------------

def test_csr_reset():
    """CSRFile should reset all CSRs to 0."""
    csr = CSRFile(xlen=32)
    sim = Simulator(csr)
    sim.reset('rst_n')
    sim.run(5)

    # mcycle increments every cycle
    assert sim.peek('mcycle') == 5


def test_csr_read_write():
    """CSRFile should support basic read/write."""
    csr = CSRFile(xlen=32)
    sim = Simulator(csr)
    sim.reset('rst_n')

    # Write mstatus = 0x8 (MIE=1)
    sim.poke('csr_addr', 0x300)
    sim.poke('csr_wdata', 0x8)
    sim.poke('csr_we', 1)
    sim.poke('csr_op', 0)  # write
    sim.step()
    sim.poke('csr_we', 0)

    # Read back
    sim.poke('csr_addr', 0x300)
    sim.poke('csr_re', 1)
    sim.step()
    assert sim.peek('csr_rdata') == 0x8


def test_csr_trap():
    """CSRFile should handle trap entry and mret."""
    csr = CSRFile(xlen=32)
    sim = Simulator(csr)
    sim.reset('rst_n')

    # Set mtvec = 0x8000
    sim.poke('csr_addr', 0x305)
    sim.poke('csr_wdata', 0x8000)
    sim.poke('csr_we', 1)
    sim.poke('csr_op', 0)
    sim.step()
    sim.poke('csr_we', 0)

    # Trigger trap (ecall)
    sim.poke('trap_valid', 1)
    sim.poke('trap_pc', 0x1004)
    sim.poke('trap_cause', 11)
    sim.step()
    sim.poke('trap_valid', 0)

    # mepc should be saved
    assert sim.peek('mepc_out') == 0x1004
    # mcause should be 11
    sim.poke('csr_addr', 0x342)
    sim.poke('csr_re', 1)
    sim.step()
    assert sim.peek('csr_rdata') == 11
    # mstatus.MIE should be 0
    sim.poke('csr_addr', 0x300)
    sim.step()
    assert (sim.peek('csr_rdata') >> 3) & 1 == 0

    # MRET
    sim.poke('mret_valid', 1)
    sim.step()
    sim.poke('mret_valid', 0)

    # mstatus.MIE should be restored (MPIE was 1 initially after reset? No, MPIE=0 after reset)
    # Actually after reset mstatus=0, so MPIE=0, MIE=0
    # After trap: MPIE=MIE=0, MIE=0
    # After mret: MIE=MPIE=0, MPIE=1
    sim.poke('csr_addr', 0x300)
    sim.step()
    mstatus = sim.peek('csr_rdata')
    assert (mstatus >> 3) & 1 == 0  # MIE = 0
    assert (mstatus >> 7) & 1 == 1  # MPIE = 1


def test_csr_interrupt():
    """CSRFile should assemble mip from interrupt inputs."""
    csr = CSRFile(xlen=32)
    sim = Simulator(csr)
    sim.reset('rst_n')

    # Set external interrupt
    sim.poke('irq', 1)
    sim.step()

    # Read mip
    sim.poke('csr_addr', 0x344)
    sim.poke('csr_re', 1)
    sim.step()
    mip = sim.peek('csr_rdata')
    assert (mip >> 11) & 1 == 1  # MEIP


# ---------------------------------------------------------------------------
# DCache tests
# ---------------------------------------------------------------------------

def test_dcache_miss_then_hit():
    """DCache should miss first, fill, then hit."""
    dc = DCache(xlen=32, num_sets=4)
    sim = Simulator(dc)
    sim.reset('rst_n')

    # First access: miss at addr 0x1000
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0x1000)
    sim.poke('req_we', 0)
    sim.step()

    # Should be in MISS state, mem_req_valid should be 1
    assert sim.peek('ready') == 0
    assert sim.peek('mem_req_valid') == 1
    assert sim.peek('mem_req_addr') == 0x1000

    # Memory responds
    sim.poke('req_valid', 0)
    sim.poke('mem_resp_valid', 1)
    sim.poke('mem_resp_data', 0xDEADBEEF)
    sim.step()
    sim.poke('mem_resp_valid', 0)

    # Now should be ready
    assert sim.peek('ready') == 1

    # Second access to same addr: hit
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0x1000)
    sim.step()
    assert sim.peek('resp_valid') == 1
    assert sim.peek('resp_data') == 0xDEADBEEF


def test_dcache_write_through():
    """DCache should update cache on write hit and pass through to memory."""
    dc = DCache(xlen=32, num_sets=4)
    sim = Simulator(dc)
    sim.reset('rst_n')

    # Fill cache first (read at 0x1000)
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0x1000)
    sim.poke('req_we', 0)
    sim.step()
    sim.poke('mem_resp_valid', 1)
    sim.poke('mem_resp_data', 0x11111111)
    sim.step()
    sim.poke('mem_resp_valid', 0)
    sim.poke('req_valid', 0)
    sim.step()

    # Write hit
    sim.poke('req_valid', 1)
    sim.poke('req_addr', 0x1000)
    sim.poke('req_we', 1)
    sim.poke('req_wdata', 0x22222222)
    sim.step()

    # Memory should see the write
    assert sim.peek('mem_req_valid') == 1
    assert sim.peek('mem_req_we') == 1
    assert sim.peek('mem_req_wdata') == 0x22222222

    # Read back should see new value (hit)
    sim.poke('req_we', 0)
    sim.step()
    assert sim.peek('resp_valid') == 1
    assert sim.peek('resp_data') == 0x22222222


# ---------------------------------------------------------------------------
# ALU tests
# ---------------------------------------------------------------------------

def test_alu_add():
    """ALU should compute ADD with 1-cycle latency."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b0000)  # ADD
    sim.poke('rs1', 10)
    sim.poke('rs2', 20)
    sim.poke('use_imm', 0)
    sim.step()

    # After 1 cycle pipeline delay
    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 30


def test_alu_add_imm():
    """ALU should compute ADDI with immediate."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b0000)  # ADD
    sim.poke('rs1', 7)
    sim.poke('imm', 5)
    sim.poke('use_imm', 1)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 12


def test_alu_sub():
    """ALU should compute SUB."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b0001)  # SUB
    sim.poke('rs1', 30)
    sim.poke('rs2', 12)
    sim.poke('use_imm', 0)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 18


def test_alu_and():
    """ALU should compute AND."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b1001)  # AND
    sim.poke('rs1', 0xFF00)
    sim.poke('rs2', 0x0F0F)
    sim.poke('use_imm', 0)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 0x0F00


def test_alu_beq_taken():
    """ALU should detect BEQ taken."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b1010)  # BEQ
    sim.poke('rs1', 42)
    sim.poke('rs2', 42)
    sim.poke('pc', 0x1000)
    sim.poke('imm', 0x20)
    sim.poke('is_branch', 1)
    sim.poke('use_imm', 0)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('br_taken') == 1
    assert sim.peek('br_target') == 0x1020


def test_alu_beq_not_taken():
    """ALU should detect BEQ not taken."""
    alu = ALU(xlen=32)
    sim = Simulator(alu)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('op', 0b1010)  # BEQ
    sim.poke('rs1', 10)
    sim.poke('rs2', 20)
    sim.poke('pc', 0x1000)
    sim.poke('imm', 0x20)
    sim.poke('is_branch', 1)
    sim.poke('use_imm', 0)
    sim.step()

    assert sim.peek('out_valid') == 1
    assert sim.peek('br_taken') == 0
    assert sim.peek('br_target') == 0x1004


# ---------------------------------------------------------------------------
# Multiplier tests
# ---------------------------------------------------------------------------

def test_mul_unsigned():
    """Multiplier should compute unsigned product."""
    mul = Multiplier(xlen=32)
    sim = Simulator(mul)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('rs1', 6)
    sim.poke('rs2', 7)
    sim.poke('is_signed', 0)
    sim.poke('high', 0)

    # 3-cycle pipeline
    sim.step()
    assert sim.peek('out_valid') == 0
    sim.step()
    assert sim.peek('out_valid') == 0
    sim.step()
    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 42


def test_mul_high():
    """Multiplier should return upper 32 bits."""
    mul = Multiplier(xlen=32)
    sim = Simulator(mul)
    sim.reset('rst_n')

    sim.poke('valid', 1)
    sim.poke('rs1', 0x10000)
    sim.poke('rs2', 0x10000)
    sim.poke('is_signed', 0)
    sim.poke('high', 1)

    sim.run(3)
    assert sim.peek('out_valid') == 1
    assert sim.peek('result') == 1  # (0x10000 * 0x10000) >> 32 = 1
