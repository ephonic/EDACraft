"""Tests for the EarphoneTop L6 Verilog emitter."""

from earphone.top.layer_L6_verilog.src.emitter import emit_verilog


def test_emit_top_verilog_returns_source_and_line_count():
    source, line_count = emit_verilog()
    assert "module EarphoneTop" in source
    assert "apb_paddr" in source
    assert "qspi_cs_n" in source
    assert "scl_o" in source
    assert line_count == len(source.splitlines())


def test_emit_top_verilog_writes_output_file(tmp_path):
    source, _ = emit_verilog(str(tmp_path))
    output = tmp_path / "earphone_top.v"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == source
