"""L6 Verilog emitter tests for EarphoneFFT256."""

from earphone.modules.fft256.layer_L6_verilog.src.emitter import emit_verilog


def test_emit_verilog_returns_source_and_line_count():
    source, line_count = emit_verilog()
    assert "module EarphoneFFT256" in source
    assert "di_en" in source
    assert "do_en" in source
    assert line_count == len(source.splitlines())


def test_emit_verilog_writes_output_file(tmp_path):
    source, _ = emit_verilog(str(tmp_path))
    output = tmp_path / "earphone_fft256.v"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == source
