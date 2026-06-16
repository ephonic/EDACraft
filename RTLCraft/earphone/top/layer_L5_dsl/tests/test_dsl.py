"""Tests for the EarphoneTop L5 DSL implementation."""

from earphone.top.layer_L5_dsl.src.dsl import build_top, describe


def test_top_dsl_builds_earphone_top():
    top = build_top()
    assert top.name == "earphone_top"
    assert type(top).__name__ == "EarphoneTop"


def test_top_dsl_exposes_required_ports():
    top = build_top()
    required_ports = {
        "clk": 1,
        "rst_n": 1,
        "imem_addr": 32,
        "dmem_addr": 32,
        "apb_paddr": 32,
        "qspi_io_o": 4,
        "scl_o": 1,
        "sda_o": 1,
    }
    for port, width in required_ports.items():
        assert hasattr(top, port)
        assert getattr(getattr(top, port), "width") == width


def test_top_dsl_describe_records_implementation_status():
    info = describe()
    assert info["status"] == "implemented"
    assert info["dsl_object_name"] == "earphone_top"
    assert info["verilog_module_name"] == "EarphoneTop"
    assert info["source"] == "earphone.top.layer_L5_dsl.src.dsl.EarphoneTop"
    assert "apb_paddr" in info["external_ports"]
