from pathlib import Path

from rtlgen_x.verify.remote_uvm import (
    RemoteUvmRegressionEntry,
    RemoteUvmRegressionReport,
    RemoteUvmTarget,
    default_remote_dir,
    summarize_uvm_output,
)


def test_default_remote_dir_normalizes_module_name():
    assert default_remote_dir("Earphone SRAM256K") == "$HOME/rtlgen_x/uvm_probe_earphone_sram256k"


def test_summarize_uvm_output_detects_pass():
    output = """
UVM_INFO @ 0: reporter [RNTST] Running test earphone_sram256k_test...
UVM_INFO earphone_sram256k_scoreboard.sv(49) @ 335000: uvm_test_top.env.scoreboard [EARPHONE_SRAM256K_SCOREBOARD] scoreboard passed
--- UVM Report Summary ---
UVM_INFO :    4
UVM_WARNING :    0
UVM_ERROR :    0
UVM_FATAL :    0
""".strip()
    summary = summarize_uvm_output(output)

    assert summary.passed is True
    assert summary.severity_counts["UVM_ERROR"] == 0
    assert summary.severity_counts["UVM_FATAL"] == 0
    assert summary.scoreboard_lines == (
        "UVM_INFO earphone_sram256k_scoreboard.sv(49) @ 335000: uvm_test_top.env.scoreboard [EARPHONE_SRAM256K_SCOREBOARD] scoreboard passed",
    )


def test_summarize_uvm_output_detects_failure_without_scoreboard_pass():
    output = """
UVM_ERROR :    2
UVM_FATAL :    1
""".strip()
    summary = summarize_uvm_output(output)

    assert summary.passed is False
    assert summary.severity_counts["UVM_ERROR"] == 2
    assert summary.severity_counts["UVM_FATAL"] == 1
    assert summary.scoreboard_lines == ()


def test_remote_uvm_regression_report_splits_pass_and_fail_entries():
    target_pass = RemoteUvmTarget(name="foo", module_file=Path("foo.py"), module_class="Foo")
    target_fail = RemoteUvmTarget(name="bar", module_file=Path("bar.py"), module_class="Bar")
    report = RemoteUvmRegressionReport(
        entries=(
            RemoteUvmRegressionEntry(target=target_pass, status="passed"),
            RemoteUvmRegressionEntry(target=target_fail, status="local_error", error="boom"),
        )
    )

    assert [entry.target.name for entry in report.passed] == ["foo"]
    assert [entry.target.name for entry in report.failed] == ["bar"]
