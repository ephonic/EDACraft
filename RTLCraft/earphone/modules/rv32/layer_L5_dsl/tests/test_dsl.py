"""L5 DSL tests for EarphoneRV32."""

from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32


def test_dsl_declares_required_external_ports():
    dut = EarphoneRV32()
    required_ports = [
        "clk",
        "rst_n",
        "imem_addr",
        "imem_rdata",
        "imem_req",
        "imem_gnt",
        "dmem_addr",
        "dmem_wdata",
        "dmem_rdata",
        "dmem_we",
        "dmem_req",
        "dmem_gnt",
        "dmem_valid",
        "retire_valid",
        "retire_rd",
        "retire_result",
    ]

    for port in required_ports:
        assert hasattr(dut, port)


def test_dsl_declares_low_power_and_muldiv_state():
    dut = EarphoneRV32()
    assert dut.pc_reg.init_value == 0x1000
    assert dut.core_clk_en.width == 1
    assert dut.muldiv_busy.width == 1
    assert dut.muldiv_count.width == 6
