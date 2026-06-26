import cocotb
from cocotb.triggers import ClockCycles
from cocotb.clock import Clock


@cocotb.test()
async def test_simd16_vadd_overflow(dut):
    """Intent-driven cocotb test for SIMD16 vadd 16-bit wrap."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    a = sum(((i + 1) & 0xFFFF) << (i * 16) for i in range(16))
    b = sum(((i + 2) & 0xFFFF) << (i * 16) for i in range(16))

    dut.vsrc0.value = a
    dut.vsrc1.value = b
    dut.op.value = 0       # vadd
    dut.mode.value = 0     # INT16
    dut.pred.value = 0xFFFF
    dut.start.value = 1
    await ClockCycles(dut.clk, 1)
    dut.start.value = 0
    await ClockCycles(dut.clk, 2)

    assert dut.done.value == 1
    for i in range(16):
        lane = (int(dut.vdst.value) >> (i * 16)) & 0xFFFF
        expected = ((i + 1) + (i + 2)) & 0xFFFF
        assert lane == expected, f"lane {i}: {lane} != {expected}"
