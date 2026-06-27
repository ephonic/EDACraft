import pytest

from rtlgen.dsl import (
    Else,
    If,
    Input,
    LUT,
    Module,
    Output,
    ReadyValidFIFO,
    Reg,
    RegisterFile,
    SkidBuffer,
    assert_emitted_rtl_contract,
    assert_marker_sequence,
    analyze_marker_sequence,
    analyze_verilog_readability,
    assert_readable_verilog,
)


class ResetAccumulator(Module):
    def __init__(self):
        super().__init__("ResetAccumulator")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.din = Input(8, "din")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")

        with self.comb:
            self.out <<= self.acc

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                with If(self.en == 1):
                    self.acc <<= self.acc + self.din


def test_review_readability_contract_accepts_representative_modules():
    modules = (
        SkidBuffer(width=8),
        ReadyValidFIFO(width=8, depth=2),
        RegisterFile(width=32, depth=8),
        ResetAccumulator(),
        LUT(width=8, init_data=[1, 3, 5, 7], depth=4),
    )

    for module in modules:
        emitted = assert_emitted_rtl_contract(module)
        assert "// Module:" in emitted or "// Module       :" in emitted
        assert "// Ports:" in emitted


def test_readability_reports_long_line():
    text = (
        "// Module: Bad\n"
        "// Ports:\n"
        "module Bad (input a, output y);\n"
        "    assign y = "
        + "a ? " * 40
        + "1'b0;\n"
        "endmodule\n"
    )

    report = analyze_verilog_readability(text, max_line_length=80)

    assert any(f.kind == "long_line" for f in report.findings)


def test_readability_reports_anonymous_helper_and_unstable_name():
    text = (
        "// Module: Bad\n"
        "// Ports:\n"
        "module Bad (input a, output y);\n"
        "    wire [7:0] _tmp17;\n"
        "    assign y = _tmp17[0];\n"
        "endmodule\n"
    )

    report = analyze_verilog_readability(text)

    assert any(f.kind == "anonymous_helper" for f in report.findings)
    assert report.unstable_generated_name_count >= 1


def test_readability_reports_missing_module_header():
    text = "module Bad (input a, output y);\n    assign y = a;\nendmodule\n"

    report = analyze_verilog_readability(text)

    assert any(f.kind == "missing_module_header" for f in report.findings)
    assert any(f.kind == "missing_port_table" for f in report.findings)


def test_marker_sequence_report_points_to_missing_or_out_of_order_marker():
    text = "// Ports:\nmodule Bad;\nendmodule\n// Module: Bad\n"
    report = analyze_marker_sequence(text, ["// Module: Bad", "// Ports:"])

    assert not report.passed
    assert any(f.kind in {"missing_marker", "out_of_order_marker"} for f in report.findings)


def test_readability_assertion_raises_markdown_report():
    text = "module Bad (input a, output y);\n    wire _cse_42;\nendmodule\n"

    with pytest.raises(AssertionError) as exc_info:
        assert_readable_verilog(text)

    message = str(exc_info.value)
    assert "# RTL Readability Report" in message
    assert "anonymous_helper" in message
    assert "missing_module_header" in message


def test_marker_sequence_assertion_raises_markdown_report():
    with pytest.raises(AssertionError) as exc_info:
        assert_marker_sequence("module Bad; endmodule", ["// Module: Bad"])

    assert "# RTL Marker Contract Report" in str(exc_info.value)

