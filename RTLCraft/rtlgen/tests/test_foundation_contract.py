import json

from rtlgen.diagnostics import (
    DiagnosticFinding,
    DiagnosticReport,
    diagnostic_from_cdc_finding,
    diagnostic_from_exception,
    diagnostic_from_readability_finding,
    diagnostic_report_to_json,
    emit_diagnostic_report_markdown,
)
from rtlgen.dsl import (
    APBRegisterBank,
    AXI4LiteRegisterBank,
    AsyncFIFO,
    DslLoweringError,
    Input,
    Memory,
    Module,
    Output,
    ReadyValidFIFO,
    ReadabilityFinding,
    RegisterFile,
    SkidBuffer,
    WishboneRegisterBank,
)
from rtlgen.verify import (
    analyze_foundation_contract,
    emit_foundation_contract_markdown,
    foundation_contract_report_to_json,
)
from rtlgen.verify.cdc import CdcEndpoint, CdcFinding


def test_diagnostics_from_readability_finding():
    finding = ReadabilityFinding(
        kind="long_line",
        line=7,
        detail="line length 140 exceeds review budget 120",
    )

    diagnostic = diagnostic_from_readability_finding(finding)

    assert diagnostic.rule == "ReadableRtlLongLine"
    assert diagnostic.category == "readability"
    assert diagnostic.severity == "warning"
    assert diagnostic.source_line == 7
    assert diagnostic.obj == "line:7"


def test_diagnostics_from_cdc_finding_preserves_source_locations():
    finding = CdcFinding(
        category="reset_release_crossing",
        severity="warning",
        message="raw reset crosses into core_clk",
        src=CdcEndpoint(
            signal_name="rst_async",
            clock_domain=None,
            width=1,
            kind="reset",
            source_file="design.py",
            source_line=42,
        ),
        dst=CdcEndpoint(
            signal_name="core_clk",
            clock_domain="core_clk",
            width=1,
            kind="clock_domain",
            source_file="design.py",
            source_line=77,
        ),
        suggestions=("Instantiate AsyncResetRel.",),
        evidence={"destination_domain": "core_clk"},
    )

    diagnostic = diagnostic_from_cdc_finding(finding)

    assert diagnostic.rule == "CdcResetReleaseCrossing"
    assert diagnostic.category == "cdc"
    assert diagnostic.source_file == "design.py"
    assert diagnostic.source_line == 42
    assert diagnostic.obj == "rst_async->core_clk"
    assert diagnostic.evidence["src"]["source_line"] == 42
    assert diagnostic.evidence["dst"]["source_line"] == 77


def test_diagnostics_from_storage_exception():
    exc = DslLoweringError(
        "[UnsupportedStorageContract] severity=error source=storage_case.py:12 "
        "object=memory.mem suggested_fix=Use supported storage. memory uses read_ports=2"
    )

    diagnostic = diagnostic_from_exception(exc)

    assert diagnostic.rule == "UnsupportedStorageContract"
    assert diagnostic.category == "storage"
    assert diagnostic.severity == "error"
    assert diagnostic.source_file == "storage_case.py"
    assert diagnostic.source_line == 12
    assert diagnostic.obj == "memory.mem"
    assert diagnostic.suggested_fix == "Use supported storage"


def test_diagnostics_markdown_contains_actionable_fields():
    report = DiagnosticReport(
        name="example",
        passed=False,
        findings=(
            DiagnosticFinding(
                rule="UnsupportedStorageContract",
                severity="error",
                category="storage",
                message="memory uses read_ports=2",
                source_file="storage_case.py",
                source_line=12,
                obj="memory.mem",
                suggested_fix="Use supported storage",
                evidence={"read_ports": 2},
            ),
        ),
    )

    markdown = emit_diagnostic_report_markdown(report)

    assert "[UnsupportedStorageContract]" in markdown
    assert "source=storage_case.py:12" in markdown
    assert "object=memory.mem" in markdown
    assert "suggested_fix=Use supported storage" in markdown


def test_diagnostics_json_round_trip_is_stable():
    report = DiagnosticReport(
        name="json-example",
        passed=True,
        findings=(
            DiagnosticFinding(
                rule="ReadableRtlLongLine",
                severity="warning",
                category="readability",
                message="long line",
                source_line=3,
                obj="line:3",
                suggested_fix="Break the expression",
                evidence={"length": 140},
            ),
        ),
    )

    payload = json.loads(diagnostic_report_to_json(report))

    assert payload["name"] == "json-example"
    assert payload["passed"] is True
    assert payload["findings"][0]["rule"] == "ReadableRtlLongLine"
    assert payload["findings"][0]["evidence"]["length"] == 140


class MultiPortStorageContract(Module):
    def __init__(self):
        super().__init__("MultiPortStorageContract")
        self.addr = Input(2, "addr")
        self.dout = Output(8, "dout")
        self.mem = self.add_memory(Memory(8, 4, "mem", read_ports=2))

        @self.comb
        def _comb():
            self.dout <<= self.mem[self.addr]


def test_foundation_contract_reports_apb_reset_release_warning_without_failing():
    report = analyze_foundation_contract(APBRegisterBank(depth=8))

    assert report.readability is not None
    assert report.readability.passed
    assert report.cdc is not None
    assert report.passed
    assert any(f.rule == "CdcResetReleaseCrossing" for f in report.diagnostics.findings)
    assert report.summary["storage"]["lowering"] == "passed"
    assert report.summary["storage"]["emitted_rtl"] == "passed"


def test_foundation_contract_accepts_clean_register_banks_and_fifo():
    modules = (
        SkidBuffer(width=8),
        AXI4LiteRegisterBank(depth=8),
        WishboneRegisterBank(depth=8),
        ReadyValidFIFO(width=8, depth=2),
        RegisterFile(width=32, depth=8),
    )

    for module in modules:
        report = analyze_foundation_contract(module)
        assert report.passed
        assert report.summary["storage"]["lowering"] == "passed"
        assert report.summary["storage"]["emitted_rtl"] == "passed"


def test_foundation_contract_accepts_async_fifo_cdc_primitive():
    report = analyze_foundation_contract(AsyncFIFO(width=8, depth=4))

    assert report.passed
    assert report.cdc is not None
    assert report.cdc.findings == ()


def test_foundation_contract_reports_storage_fail_fast_as_diagnostic():
    report = analyze_foundation_contract(MultiPortStorageContract())

    assert not report.passed
    assert report.summary["storage"]["lowering"] == "failed"
    assert report.summary["storage"]["emitted_rtl"] == "failed"
    assert any(f.rule == "UnsupportedStorageContract" for f in report.diagnostics.findings)
    assert all(f.category != "unknown" for f in report.diagnostics.findings)


def test_foundation_contract_markdown_and_json_include_findings():
    report = analyze_foundation_contract(MultiPortStorageContract())
    markdown = emit_foundation_contract_markdown(report)
    payload = json.loads(foundation_contract_report_to_json(report))

    assert "# Foundation Contract Report: MultiPortStorageContract" in markdown
    assert "[UnsupportedStorageContract]" in markdown
    assert "suggested_fix" in markdown
    assert payload["module_name"] == "MultiPortStorageContract"
    assert payload["passed"] is False
    assert payload["diagnostics"]["findings"][0]["rule"] == "UnsupportedStorageContract"
