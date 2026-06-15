"""L6 Verilog emitter tests for EarphoneAPBBridge."""

from earphone.modules.apb_bridge.layer_L6_verilog.src.emitter import emit_verilog


def test_emit_verilog_returns_source_and_line_count():
    source, line_count = emit_verilog()
    assert "module EarphoneAPBBridge" in source
    assert "m_paddr" in source
    assert "m_pready" in source
    assert line_count == len(source.splitlines())


def test_emit_verilog_writes_output_file(tmp_path):
    source, _ = emit_verilog(str(tmp_path))
    output = tmp_path / "earphone_apb_bridge.v"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == source
