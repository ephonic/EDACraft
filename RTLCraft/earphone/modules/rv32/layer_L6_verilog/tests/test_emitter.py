"""L6 Verilog emitter tests for EarphoneRV32."""

from earphone.modules.rv32.layer_L6_verilog.src.emitter import emit_verilog


def test_emit_verilog_returns_source_and_line_count():
    source, line_count = emit_verilog()
    assert "module EarphoneRV32" in source
    assert "imem_addr" in source
    assert "retire_valid" in source
    assert line_count == len(source.splitlines())
    assert line_count > 100


def test_emit_verilog_writes_output_file(tmp_path):
    source, _ = emit_verilog(str(tmp_path))
    output = tmp_path / "earphone_rv32.v"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == source
