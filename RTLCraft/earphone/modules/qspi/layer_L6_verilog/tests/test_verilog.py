"""L6 Verilog emitter tests for EarphoneQSPI."""

from earphone.modules.qspi.layer_L6_verilog.src.emitter import emit_verilog


def test_emit_verilog_returns_source_and_line_count():
    source, line_count = emit_verilog()
    assert "module EarphoneQSPI" in source
    assert "qspi_cs_n" in source
    assert "qspi_io_i" in source
    assert line_count == len(source.splitlines())


def test_emit_verilog_writes_output_file(tmp_path):
    source, _ = emit_verilog(str(tmp_path))
    output = tmp_path / "earphone_qspi.v"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == source
