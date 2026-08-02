import json

from gpgpu_stack import GpuSmProfileHint, run_gpu_sm_seed_flow, write_gpu_sm_seed_artifacts
from rtlgen_x.verify import foundation_contract_report_to_json


def test_gpu_sm_seed_flow_includes_foundation_contract_artifact():
    result = run_gpu_sm_seed_flow(
        launch_id="seed_foundation",
        profile=GpuSmProfileHint(memory_tokens=4, sfu_tokens=2, gemm_tokens=2),
    )

    assert result.architecture_markdown.startswith("# GPU SM Seed Architecture Report\n")
    assert result.ppa_markdown.startswith("# GPU SM Seed PPA Report\n")
    assert result.foundation_markdown.startswith("# Foundation Contract Report: gpu_sm\n")
    assert result.foundation_report.passed
    assert result.foundation_report.summary["storage"]["lowering"] == "passed"
    assert result.foundation_report.summary["storage"]["emitted_rtl"] == "passed"

    payload = json.loads(foundation_contract_report_to_json(result.foundation_report))
    assert payload["module_name"] == "gpu_sm"
    assert payload["passed"] is True
    assert "readability" in payload["summary"]
    assert "cdc" in payload["summary"]
    assert "storage" in payload["summary"]

    for finding in result.foundation_report.diagnostics.findings:
        assert finding.rule
        assert finding.category
        assert finding.severity in {"info", "warning", "error"}
        assert finding.obj is not None
        assert finding.suggested_fix is not None


def test_gpu_sm_seed_flow_artifact_writer_persists_reports(tmp_path):
    result = run_gpu_sm_seed_flow(
        launch_id="seed_artifacts",
        profile=GpuSmProfileHint(memory_tokens=4, sfu_tokens=2, gemm_tokens=2),
    )

    paths = write_gpu_sm_seed_artifacts(result, tmp_path / "seed")

    assert set(paths) == {"architecture", "ppa", "foundation", "foundation_json"}
    assert paths["architecture"].read_text(encoding="utf-8").startswith(
        "# GPU SM Seed Architecture Report\n"
    )
    assert paths["ppa"].read_text(encoding="utf-8").startswith("# GPU SM Seed PPA Report\n")
    assert paths["foundation"].read_text(encoding="utf-8").startswith(
        "# Foundation Contract Report: gpu_sm\n"
    )

    payload = json.loads(paths["foundation_json"].read_text(encoding="utf-8"))
    assert payload["module_name"] == "gpu_sm"
    assert payload["passed"] is True
    assert payload["diagnostics"]["name"] == "foundation:gpu_sm"
    assert isinstance(payload["diagnostics"]["findings"], list)
