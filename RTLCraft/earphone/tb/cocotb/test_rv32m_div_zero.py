import cocotb
from cocotb.triggers import ClockCycles
from cocotb.clock import Clock


@cocotb.test()
async def test_rv32m_div_zero(dut):
    """Intent-driven cocotb test for RV32M DIV by zero."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Drive instruction memory: DIV x3, x1, x2 where x2 = 0
    # This is a simplified stimulus; real test would use memory BFM.
    for _ in range(50):
        await ClockCycles(dut.clk, 1)

    # Check retire
    assert dut.retire_valid.value == 1
    assert dut.retire_rd.value == 3
    # DIV by zero result = -1 (0xFFFFFFFF)
    assert dut.retire_result.value == 0xFFFFFFFF
