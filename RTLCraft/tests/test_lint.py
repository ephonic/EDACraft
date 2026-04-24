"""Tests for rtlgen.lint VerilogLinter."""

import pytest
from rtlgen.lint import VerilogLinter, LintResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run(verilog: str, auto_fix: bool = False, rules=None):
    linter = VerilogLinter(rules=rules, auto_fix=auto_fix)
    return linter.lint(verilog)


# ---------------------------------------------------------------------------
# default_nettype
# ---------------------------------------------------------------------------
def test_default_nettype_missing():
    v = "module A (input x, output y);\nendmodule\n"
    r = _run(v)
    assert any(i.rule == "default_nettype" for i in r.issues)


def test_default_nettype_present():
    v = "`default_nettype none\nmodule A (input x, output y);\nendmodule\n"
    r = _run(v)
    assert not any(i.rule == "default_nettype" for i in r.issues)


def test_default_nettype_auto_fix():
    v = "module A (input x, output y);\nendmodule\n"
    r = _run(v, auto_fix=True)
    assert r.fixed_text is not None
    assert "`default_nettype none" in r.fixed_text


# ---------------------------------------------------------------------------
# implicit_wire
# ---------------------------------------------------------------------------
def test_implicit_wire_in_assign():
    v = """
module A (input x, output y);
    assign y = x;
    assign z = x;
endmodule
"""
    r = _run(v)
    imp = [i for i in r.issues if i.rule == "implicit_wire"]
    assert len(imp) == 1
    assert "z" in imp[0].message


def test_implicit_wire_in_port_conn():
    v = """
module B (input a);
endmodule
module A (input x);
    B u (.a(x));
    B v (.a(unknown_sig));
endmodule
"""
    r = _run(v)
    imp = [i for i in r.issues if i.rule == "implicit_wire"]
    assert any("unknown_sig" in i.message for i in imp)


def test_implicit_wire_auto_fix():
    v = """
module A (input x, output y);
    assign y = x;
    assign z = x;
endmodule
"""
    r = _run(v, auto_fix=True)
    assert "logic z;" in r.fixed_text


# ---------------------------------------------------------------------------
# multi_driven
# ---------------------------------------------------------------------------
def test_multi_driven_assign_and_always():
    v = """
module A (input clk, output reg y);
    assign y = 1'b0;
    always @(posedge clk) begin
        y <= 1'b1;
    end
endmodule
"""
    r = _run(v)
    md = [i for i in r.issues if i.rule == "multi_driven"]
    assert len(md) == 1
    assert "y" in md[0].message


def test_single_driven_ok():
    v = """
module A (input clk, output reg y);
    always @(posedge clk) begin
        y <= 1'b1;
    end
endmodule
"""
    r = _run(v)
    md = [i for i in r.issues if i.rule == "multi_driven"]
    assert len(md) == 0


# ---------------------------------------------------------------------------
# unused_signal
# ---------------------------------------------------------------------------
def test_unused_signal():
    v = """
module A (input x, output y);
    logic unused;
    assign y = x;
endmodule
"""
    r = _run(v)
    uu = [i for i in r.issues if i.rule == "unused_signal"]
    assert any("unused" in i.message for i in uu)


def test_used_signal_ok():
    v = """
module A (input x, output y);
    logic tmp;
    assign tmp = x;
    assign y = tmp;
endmodule
"""
    r = _run(v)
    uu = [i for i in r.issues if i.rule == "unused_signal"]
    assert not any("tmp" in i.message for i in uu)


# ---------------------------------------------------------------------------
# blocking_in_seq
# ---------------------------------------------------------------------------
def test_blocking_in_seq_detected():
    v = """
module A (input clk, output reg y);
    always @(posedge clk) begin
        y = 1'b1;
    end
endmodule
"""
    r = _run(v)
    bi = [i for i in r.issues if i.rule == "blocking_in_seq"]
    assert len(bi) == 1
    assert "y" in bi[0].message


def test_blocking_in_seq_auto_fix():
    v = """
module A (input clk, output reg y);
    always @(posedge clk) begin
        y = 1'b1;
    end
endmodule
"""
    r = _run(v, auto_fix=True)
    assert "y <= 1'b1;" in r.fixed_text


def test_nonblocking_ok():
    v = """
module A (input clk, output reg y);
    always @(posedge clk) begin
        y <= 1'b1;
    end
endmodule
"""
    r = _run(v)
    bi = [i for i in r.issues if i.rule == "blocking_in_seq"]
    assert len(bi) == 0


# ---------------------------------------------------------------------------
# latch_risk
# ---------------------------------------------------------------------------
def test_latch_risk_if_without_else():
    v = """
module A (input a, output reg y);
    always @(*) begin
        if (a)
            y = 1'b1;
    end
endmodule
"""
    r = _run(v)
    lr = [i for i in r.issues if i.rule == "latch_risk"]
    assert len(lr) >= 1


def test_latch_risk_case_without_default():
    v = """
module A (input [1:0] a, output reg y);
    always @(*) begin
        case (a)
            2'b00: y = 1'b0;
            2'b01: y = 1'b1;
        endcase
    end
endmodule
"""
    r = _run(v)
    lr = [i for i in r.issues if i.rule == "latch_risk"]
    assert any("case" in i.message for i in lr)


def test_no_latch_when_complete():
    v = """
module A (input a, output reg y);
    always @(*) begin
        if (a)
            y = 1'b1;
        else
            y = 1'b0;
    end
endmodule
"""
    r = _run(v)
    lr = [i for i in r.issues if i.rule == "latch_risk"]
    assert len(lr) == 0


def test_latch_risk_if_without_else_auto_fix():
    v = """
module A (input a, output reg y);
    always @(*) begin
        if (a)
            y = 1'b1;
    end
endmodule
"""
    r = _run(v, auto_fix=True)
    assert r.fixed_text is not None
    assert "y = 1'b0;" in r.fixed_text


def test_latch_risk_if_without_else_auto_fix_width():
    v = """
module A (input a, output reg [3:0] y);
    always @(*) begin
        if (a)
            y = 4'b1111;
    end
endmodule
"""
    r = _run(v, auto_fix=True)
    assert r.fixed_text is not None
    assert "y = {4{1'b0}};" in r.fixed_text


def test_latch_risk_if_else_mismatch_auto_fix():
    v = """
module A (input a, output reg y, output reg z);
    always @(*) begin
        if (a) begin
            y = 1'b1;
        end else begin
            z = 1'b0;
        end
    end
endmodule
"""
    r = _run(v, auto_fix=True)
    assert r.fixed_text is not None
    assert "y = 1'b0;" in r.fixed_text
    assert "z = 1'b0;" in r.fixed_text


def test_latch_risk_case_without_default_auto_fix():
    v = """
module A (input [1:0] a, output reg y);
    always @(*) begin
        case (a)
            2'b00: y = 1'b0;
            2'b01: y = 1'b1;
        endcase
    end
endmodule
"""
    r = _run(v, auto_fix=True)
    assert r.fixed_text is not None
    assert "y = 1'b0;" in r.fixed_text


# ---------------------------------------------------------------------------
# width_mismatch
# ---------------------------------------------------------------------------
def test_width_mismatch_assign():
    v = """
module A (input [7:0] x, output y);
    logic [3:0] tmp;
    assign tmp = x;
endmodule
"""
    r = _run(v)
    wm = [i for i in r.issues if i.rule == "width_mismatch"]
    assert len(wm) == 1
    assert "left=4" in wm[0].message and "right=8" in wm[0].message


def test_width_match_ok():
    v = """
module A (input [7:0] x, output y);
    logic [7:0] tmp;
    assign tmp = x;
endmodule
"""
    r = _run(v)
    wm = [i for i in r.issues if i.rule == "width_mismatch"]
    assert len(wm) == 0


# ---------------------------------------------------------------------------
# Integration / edge cases
# ---------------------------------------------------------------------------
def test_empty_verilog_no_crash():
    r = _run("")
    # empty file only triggers default_nettype warning
    assert r.fixed_text is None
    assert isinstance(r, LintResult)


def test_multiple_modules():
    v = """
module B (input a, output b);
    assign b = a;
endmodule
module A (input x, output y);
    assign y = x;
    B u (.a(x), .b(z));
endmodule
"""
    r = _run(v)
    imp = [i for i in r.issues if i.rule == "implicit_wire"]
    # z 在 A 中隐式
    assert any("z" in i.message for i in imp)
