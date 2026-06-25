from pathlib import Path
import json
import runpy
import sys

import pytest

from rtlgen_x.verify.remote_uvm import (
    coerce_uvm_sequence_steps,
    RemoteUvmError,
    RemoteUvmEnvironmentReport,
    RemoteUvmRegressionEntry,
    RemoteUvmRegressionReport,
    RemoteUvmTarget,
    default_remote_dir,
    load_remote_uvm_targets_json,
    load_uvm_sequence_steps_json,
    _format_remote_failure,
    _remote_failure_hint,
    probe_remote_uvm_environment,
    run_remote_uvm_regression,
    summarize_uvm_output,
    write_remote_uvm_regression_report,
)
from rtlgen_x.verify import UvmSequenceStep
from rtlgen_x.tests.test_verify_uvm import DslMultiClockMailbox


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


def test_remote_uvm_regression_report_can_be_written_as_json(tmp_path):
    target = RemoteUvmTarget(
        name="foo",
        module_file=Path("foo.py"),
        module_class="Foo",
        directed_sequence=(
            UvmSequenceStep(inputs={"wr_en": 1}, label="write0", active_domains=("wr_clk",)),
        ),
    )
    report = RemoteUvmRegressionReport(
        entries=(
            RemoteUvmRegressionEntry(target=target, status="local_error", error="boom"),
        )
    )

    out_path = write_remote_uvm_regression_report(report, tmp_path / "remote_uvm.json")
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert payload["total"] == 1
    assert payload["passed"] == 0
    assert payload["failed"] == 1
    assert payload["entries"][0]["target"]["module_class"] == "Foo"
    assert payload["entries"][0]["error"] == "boom"
    assert payload["entries"][0]["target"]["directed_sequence"][0]["active_domains"] == ["wr_clk"]


def test_remote_uvm_regression_passes_directed_sequence_to_probe(monkeypatch, tmp_path):
    captured = {}

    def fake_load_module_instance(module_file, class_name):
        return object()

    class _Summary:
        passed = True
        severity_counts = {"UVM_INFO": 1, "UVM_WARNING": 0, "UVM_ERROR": 0, "UVM_FATAL": 0}
        scoreboard_lines = ("scoreboard passed",)

    class _Result:
        host = "10.0.0.1"
        remote_dir = "$HOME/rtlgen_x/test"
        local_bundle_dir = tmp_path / "bundle"
        returncode = 0
        summary = _Summary()
        stdout = "ok"
        stderr = ""

    def fake_run_remote_uvm_probe(module, **kwargs):
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.load_module_instance", fake_load_module_instance)
    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.run_remote_uvm_probe", fake_run_remote_uvm_probe)

    target = RemoteUvmTarget(
        name="foo",
        module_file=Path("foo.py"),
        module_class="Foo",
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                label="reset",
                active_domains=("wr_clk", "rd_clk"),
            ),
        ),
    )
    report = run_remote_uvm_regression((target,), host="10.0.0.1", local_root=tmp_path / "root")

    assert len(report.entries) == 1
    assert report.entries[0].status == "passed"
    assert captured["clock_name"] == "wr_clk"
    assert captured["directed_sequence"] == target.directed_sequence


def test_run_remote_uvm_probe_canonicalizes_dsl_domain_aliases(monkeypatch, tmp_path):
    captured = {}

    class _Summary:
        passed = True
        severity_counts = {"UVM_INFO": 1, "UVM_WARNING": 0, "UVM_ERROR": 0, "UVM_FATAL": 0}
        scoreboard_lines = ("scoreboard passed",)

    class _Completed:
        returncode = 0
        stdout = "UVM_INFO :    1\nUVM_WARNING :    0\nUVM_ERROR :    0\nUVM_FATAL :    0\nscoreboard passed\n"
        stderr = ""

    def fake_write_uvm_runtime_bundle(bundle, local_dir, include_runtime_package=False):
        captured["bundle"] = bundle
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "run_vcs.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    def fake_run_remote_ssh(host, command, **kwargs):
        return _Completed()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.write_uvm_runtime_bundle", fake_write_uvm_runtime_bundle)
    monkeypatch.setattr("rtlgen_x.verify.remote_uvm._run_remote_ssh", fake_run_remote_ssh)

    from rtlgen_x.verify.remote_uvm import run_remote_uvm_probe

    run_remote_uvm_probe(
        DslMultiClockMailbox(),
        clock_name="wr_clk",
        host="10.0.0.1",
        local_bundle_dir=tmp_path / "bundle",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                label="reset",
                active_domains=("wr_clk", "rd_clk"),
            ),
        ),
    )

    bundle = captured["bundle"]
    seq_source = bundle.artifact_map()["dsl_multi_clock_mailbox_smoke_seq.sv"]
    assert "req.rtlgen_x_active_write = 1'b1;" in seq_source
    assert "req.rtlgen_x_active_read = 1'b1;" in seq_source


def test_run_remote_uvm_regression_canonicalizes_dsl_domain_aliases(monkeypatch, tmp_path):
    captured = {}

    def fake_load_module_instance(module_file, class_name):
        return DslMultiClockMailbox()

    class _Summary:
        passed = True
        severity_counts = {"UVM_INFO": 1, "UVM_WARNING": 0, "UVM_ERROR": 0, "UVM_FATAL": 0}
        scoreboard_lines = ("scoreboard passed",)

    class _Result:
        host = "10.0.0.1"
        remote_dir = "$HOME/rtlgen_x/test"
        local_bundle_dir = tmp_path / "bundle"
        returncode = 0
        summary = _Summary()
        stdout = "ok"
        stderr = ""

    def fake_run_remote_uvm_probe(module, **kwargs):
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.load_module_instance", fake_load_module_instance)
    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.run_remote_uvm_probe", fake_run_remote_uvm_probe)

    target = RemoteUvmTarget(
        name="mailbox",
        module_file=Path("foo.py"),
        module_class="Foo",
        clock_name="wr_clk",
        directed_sequence=(
            UvmSequenceStep(
                inputs={"wr_rst": 1, "rd_rst": 1},
                label="reset",
                active_domains=("write", "read"),
            ),
        ),
    )
    report = run_remote_uvm_regression((target,), host="10.0.0.1", local_root=tmp_path / "root")

    assert len(report.entries) == 1
    assert report.entries[0].status == "passed"
    assert captured["clock_name"] == "wr_clk"
    assert captured["directed_sequence"] == target.directed_sequence


def test_coerce_uvm_sequence_steps_accepts_structured_payload():
    steps = coerce_uvm_sequence_steps(
        (
            {
                "inputs": {"wr_rst": "0x1", "rd_rst": 1},
                "label": "reset",
                "active_domains": {"wr_clk": True, "rd_clk": True},
            },
            {
                "inputs": {"wr_en": True, "din": "17"},
                "label": "write0",
                "active_domains": ["wr_clk", "wr_clk"],
            },
        )
    )

    assert steps is not None
    assert steps[0].inputs == {"wr_rst": 1, "rd_rst": 1}
    assert steps[0].label == "reset"
    assert steps[0].active_domains == ("wr_clk", "rd_clk")
    assert steps[1].inputs == {"wr_en": 1, "din": 17}
    assert steps[1].active_domains == ("wr_clk",)


def test_load_uvm_sequence_steps_json_supports_wrapped_payload(tmp_path):
    path = tmp_path / "seq.json"
    path.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "inputs": {"wr_rst": 1, "rd_rst": 1},
                        "label": "reset",
                        "active_domains": ["wr_clk", "rd_clk"],
                    },
                    {
                        "inputs": {"rd_en": 1},
                        "active_domains": "rd_clk",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    steps = load_uvm_sequence_steps_json(path)

    assert [step.label for step in steps] == ["reset", None]
    assert steps[0].active_domains == ("wr_clk", "rd_clk")
    assert steps[1].active_domains == ("rd_clk",)
    assert steps[1].inputs == {"rd_en": 1}


def test_load_remote_uvm_targets_json_supports_targets_and_report_entries(tmp_path):
    targets_path = tmp_path / "targets.json"
    targets_path.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "name": "mailbox",
                        "module_file": "foo.py",
                        "module_class": "Foo",
                        "clock_name": "wr_clk",
                        "directed_sequence": [
                            {
                                "inputs": {"wr_en": 1},
                                "active_domains": ["wr_clk"],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "target": {
                            "name": "mailbox2",
                            "module_file": "bar.py",
                            "module_class": "Bar",
                            "clock_name": "rd_clk",
                            "directed_sequence": [
                                {
                                    "inputs": {"rd_en": 1},
                                    "active_domains": ["rd_clk"],
                                }
                            ],
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    targets = load_remote_uvm_targets_json(targets_path)
    from_report = load_remote_uvm_targets_json(report_path)

    assert len(targets) == 1
    assert targets[0].clock_name == "wr_clk"
    assert targets[0].directed_sequence is not None
    assert targets[0].directed_sequence[0].active_domains == ("wr_clk",)

    assert len(from_report) == 1
    assert from_report[0].name == "mailbox2"
    assert from_report[0].directed_sequence is not None
    assert from_report[0].directed_sequence[0].inputs == {"rd_en": 1}


def test_run_remote_uvm_probe_script_loads_directed_sequence_json(monkeypatch, tmp_path, capsys):
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_remote_uvm_probe.py"
    seq_path = tmp_path / "steps.json"
    seq_path.write_text(
        json.dumps(
            [
                {
                    "inputs": {"wr_rst": 1, "rd_rst": 1},
                    "label": "reset",
                    "active_domains": ["wr_clk", "rd_clk"],
                }
            ]
        ),
        encoding="utf-8",
    )
    captured = {}

    class _Summary:
        passed = True
        severity_counts = {"UVM_INFO": 1, "UVM_WARNING": 0, "UVM_ERROR": 0, "UVM_FATAL": 0}
        scoreboard_lines = ("scoreboard passed",)

    class _Result:
        host = "10.0.0.1"
        remote_dir = "$HOME/rtlgen_x/test"
        local_bundle_dir = tmp_path / "bundle"
        returncode = 0
        summary = _Summary()

    def fake_load_module_instance(module_file, class_name):
        class _Module:
            name = "mailbox"

        return _Module()

    def fake_run_remote_uvm_probe(module, **kwargs):
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.load_module_instance", fake_load_module_instance)
    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.run_remote_uvm_probe", fake_run_remote_uvm_probe)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_remote_uvm_probe.py",
            "--module-file",
            "foo.py",
            "--module-class",
            "Foo",
            "--clock",
            "wr_clk",
            "--host",
            "10.0.0.1",
            "--directed-sequence-json",
            str(seq_path),
            "--local-bundle-dir",
            str(tmp_path / "out"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script), run_name="__main__")

    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "remote_uvm=PASS" in out
    assert captured["clock_name"] == "wr_clk"
    assert captured["directed_sequence"] is not None
    assert captured["directed_sequence"][0].active_domains == ("wr_clk", "rd_clk")


def test_run_remote_uvm_regression_script_loads_targets_json_and_overlay(monkeypatch, tmp_path, capsys):
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_remote_uvm_regression.py"
    targets_path = tmp_path / "targets.json"
    targets_path.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "name": "mailbox",
                        "module_file": "foo.py",
                        "module_class": "Foo",
                        "clock_name": "wr_clk",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    seq_path = tmp_path / "steps.json"
    seq_path.write_text(
        json.dumps(
            [
                {
                    "inputs": {"wr_en": 1},
                    "active_domains": ["wr_clk"],
                }
            ]
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_run_remote_uvm_regression(targets, **kwargs):
        captured["targets"] = tuple(targets)
        captured.update(kwargs)
        return RemoteUvmRegressionReport(
            entries=(
                RemoteUvmRegressionEntry(target=captured["targets"][0], status="passed"),
            )
        )

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.run_remote_uvm_regression", fake_run_remote_uvm_regression)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_remote_uvm_regression.py",
            "--host",
            "10.0.0.1",
            "--targets-json",
            str(targets_path),
            "--directed-sequence-json",
            str(seq_path),
            "--json-out",
            str(tmp_path / "report.json"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script), run_name="__main__")

    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "mailbox: passed" in out
    assert "passed=1 failed=0 total=1" in out
    assert captured["host"] == "10.0.0.1"
    assert captured["targets"][0].directed_sequence is not None
    assert captured["targets"][0].directed_sequence[0].active_domains == ("wr_clk",)
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["passed"] == 1


def test_remote_failure_hint_detects_ssh_auth_issue():
    hint = _remote_failure_hint(stdout="", stderr="Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password).")
    assert "SSH authentication failed" in hint


def test_remote_failure_hint_detects_missing_source_script():
    hint = _remote_failure_hint(stdout="", stderr="bash: /apps/EDAs/syn.bash: No such file or directory")
    assert "source_script path is missing" in hint


def test_format_remote_failure_includes_hint_and_context():
    completed = type(
        "_Completed",
        (),
        {
            "returncode": 255,
            "stdout": "",
            "stderr": "Permission denied (publickey).",
        },
    )()

    message = _format_remote_failure(
        "10.0.0.1",
        "prepare remote work directory",
        "mkdir -p $HOME/rtlgen_x/test",
        completed,
    )

    assert "remote UVM step failed: prepare remote work directory" in message
    assert "host: 10.0.0.1" in message
    assert "hint: SSH authentication failed" in message
    assert "stderr:" in message


def test_remote_uvm_regression_reports_remote_error_context(monkeypatch, tmp_path):
    def fake_load_module_instance(module_file, class_name):
        return object()

    def fake_run_remote_uvm_probe(module, **kwargs):
        raise RemoteUvmError("remote UVM step failed: run remote VCS/UVM probe")

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.load_module_instance", fake_load_module_instance)
    monkeypatch.setattr("rtlgen_x.verify.remote_uvm.run_remote_uvm_probe", fake_run_remote_uvm_probe)

    target = RemoteUvmTarget(name="foo", module_file=Path("foo.py"), module_class="Foo")
    report = run_remote_uvm_regression((target,), host="10.0.0.1", local_root=tmp_path / "root")

    assert len(report.entries) == 1
    assert report.entries[0].status == "local_error"
    assert report.entries[0].error == "RemoteUvmError: remote UVM step failed: run remote VCS/UVM probe"


def test_probe_remote_uvm_environment_reports_vcs_path(monkeypatch):
    class _Completed:
        returncode = 0
        stdout = "RTLGEN_X_VCS=/tools/bin/vcs\n"
        stderr = ""

    def fake_run_remote_ssh(host, command, **kwargs):
        assert host == "10.0.0.1"
        assert "source /apps/EDAs/syn.bash" in command
        return _Completed()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm._run_remote_ssh", fake_run_remote_ssh)

    report = probe_remote_uvm_environment(host="10.0.0.1")

    assert isinstance(report, RemoteUvmEnvironmentReport)
    assert report.environment_ok is True
    assert report.vcs_path == "/tools/bin/vcs"
    assert report.returncode == 0


def test_probe_remote_uvm_environment_reports_missing_vcs(monkeypatch):
    class _Completed:
        returncode = 2
        stdout = "RTLGEN_X_VCS=\n"
        stderr = ""

    def fake_run_remote_ssh(host, command, **kwargs):
        return _Completed()

    monkeypatch.setattr("rtlgen_x.verify.remote_uvm._run_remote_ssh", fake_run_remote_ssh)

    report = probe_remote_uvm_environment(host="10.0.0.1")

    assert report.environment_ok is False
    assert report.vcs_path is None
    assert report.returncode == 2


def test_probe_remote_uvm_environment_script_reports_status(monkeypatch, capsys):
    script = Path(__file__).resolve().parents[2] / "scripts" / "probe_remote_uvm_environment.py"

    def fake_probe_remote_uvm_environment(*, host, source_script):
        return RemoteUvmEnvironmentReport(
            host=host,
            source_script=source_script,
            returncode=0,
            stdout="RTLGEN_X_VCS=/tools/bin/vcs",
            stderr="",
            vcs_path="/tools/bin/vcs",
            environment_ok=True,
        )

    monkeypatch.setattr(
        "rtlgen_x.verify.remote_uvm.probe_remote_uvm_environment",
        fake_probe_remote_uvm_environment,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe_remote_uvm_environment.py",
            "--host",
            "10.0.0.1",
            "--source-script",
            "/apps/EDAs/syn.bash",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(script), run_name="__main__")

    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "host=10.0.0.1" in out
    assert "environment_ok=1" in out
    assert "vcs_path=/tools/bin/vcs" in out
