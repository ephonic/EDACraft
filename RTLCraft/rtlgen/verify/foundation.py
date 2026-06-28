"""Foundation contract preflight for DSL modules."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Optional, Sequence

from rtlgen.diagnostics import (
    DiagnosticFinding,
    DiagnosticReport,
    diagnostic_from_exception,
    diagnostic_report_to_json,
    diagnostics_from_cdc_report,
    diagnostics_from_readability_report,
)
from rtlgen.dsl.adapter import lower_dsl_module_to_sim
from rtlgen.dsl.codegen import EmitProfile, VerilogEmitter
from rtlgen.dsl.readability import ReadabilityReport, analyze_verilog_readability
from rtlgen.verify.cdc import CdcReport, analyze_cdc


@dataclass(frozen=True)
class FoundationContractReport:
    module_name: str
    passed: bool
    readability: Optional[ReadabilityReport]
    cdc: Optional[CdcReport]
    diagnostics: DiagnosticReport
    summary: Mapping[str, object]


def analyze_foundation_contract(
    module: Any,
    *,
    profile: EmitProfile | None = None,
    run_readability: bool = True,
    run_cdc: bool = True,
    run_storage: bool = True,
    strict: bool = False,
) -> FoundationContractReport:
    """Run the v1 foundation contract preflight for one DSL module."""

    resolved_profile = profile or EmitProfile.review()
    module_name = _module_name(module)
    findings: list[DiagnosticFinding] = []
    readability: Optional[ReadabilityReport] = None
    cdc: Optional[CdcReport] = None
    summary: dict[str, object] = {
        "strict": bool(strict),
        "readability": {"enabled": bool(run_readability), "status": "not_run"},
        "cdc": {"enabled": bool(run_cdc), "status": "not_run"},
        "storage": {
            "enabled": bool(run_storage),
            "lowering": "not_run",
            "emitted_rtl": "not_run",
        },
    }

    emitted_text: Optional[str] = None
    emit_exception: Optional[BaseException] = None
    if run_readability or run_storage:
        try:
            emitted_text = VerilogEmitter(profile=resolved_profile).emit(module)
        except Exception as exc:  # report-oriented preflight
            emit_exception = exc

    if run_readability:
        if emitted_text is not None:
            readability = analyze_verilog_readability(
                emitted_text,
                profile=resolved_profile.style or "review",
            )
            readability_report = diagnostics_from_readability_report(readability)
            findings.extend(readability_report.findings)
            summary["readability"] = {
                "enabled": True,
                "status": "passed" if readability.passed else "findings",
                "line_count": readability.line_count,
                "max_line_length": readability.max_line_length,
                "findings": len(readability.findings),
            }
        elif emit_exception is not None:
            findings.append(diagnostic_from_exception(emit_exception))
            summary["readability"] = {
                "enabled": True,
                "status": "emit_failed",
            }

    if run_cdc:
        try:
            cdc = analyze_cdc(module)
            cdc_report = diagnostics_from_cdc_report(cdc)
            findings.extend(cdc_report.findings)
            summary["cdc"] = {
                "enabled": True,
                "status": "passed" if not cdc.findings else "findings",
                "clock_domains": cdc.clock_domains,
                "findings": len(cdc.findings),
                "errors": cdc.error_count,
                "warnings": cdc.warning_count,
            }
        except Exception as exc:  # report-oriented preflight
            findings.append(diagnostic_from_exception(exc, category="cdc"))
            summary["cdc"] = {
                "enabled": True,
                "status": "failed",
            }

    if run_storage:
        storage_summary = {
            "enabled": True,
            "lowering": "not_run",
            "emitted_rtl": "not_run",
        }
        try:
            lower_dsl_module_to_sim(module)
            storage_summary["lowering"] = "passed"
        except Exception as exc:  # report-oriented preflight
            storage_summary["lowering"] = "failed"
            findings.append(diagnostic_from_exception(exc))

        if emitted_text is not None:
            storage_summary["emitted_rtl"] = "passed"
        elif emit_exception is not None:
            storage_summary["emitted_rtl"] = "failed"
            findings.append(diagnostic_from_exception(emit_exception))
        summary["storage"] = storage_summary

    findings = _dedupe_diagnostics(findings)
    counts = _diagnostic_counts(findings)
    summary["diagnostics"] = counts
    passed = not any(finding.severity == "error" for finding in findings)
    if strict:
        passed = passed and not findings
    diagnostic_report = DiagnosticReport(
        name=f"foundation:{module_name}",
        passed=passed,
        findings=tuple(findings),
    )
    return FoundationContractReport(
        module_name=module_name,
        passed=passed,
        readability=readability,
        cdc=cdc,
        diagnostics=diagnostic_report,
        summary=summary,
    )


def emit_foundation_contract_markdown(report: FoundationContractReport) -> str:
    """Render a foundation contract report as Markdown."""

    counts = report.summary.get("diagnostics", {})
    lines = [
        f"# Foundation Contract Report: {report.module_name}",
        "",
        f"- passed: `{str(report.passed).lower()}`",
        (
            "- diagnostics: "
            f"{counts.get('error', 0)} errors / "
            f"{counts.get('warning', 0)} warnings / "
            f"{counts.get('info', 0)} info"
        ),
        f"- readability summary: `{_summary_text(report.summary.get('readability', {}))}`",
        f"- CDC summary: `{_summary_text(report.summary.get('cdc', {}))}`",
        f"- storage summary: `{_summary_text(report.summary.get('storage', {}))}`",
        "",
        "## Findings",
        "",
    ]
    if not report.diagnostics.findings:
        lines.append("No foundation contract findings.")
        return "\n".join(lines)

    for finding in report.diagnostics.findings:
        source = _format_source(finding.source_file, finding.source_line)
        header = (
            f"- [{finding.rule}] severity={finding.severity} "
            f"category={finding.category} source={source}"
        )
        if finding.obj:
            header += f" object={finding.obj}"
        lines.append(header)
        lines.append(f"  message: {finding.message}")
        if finding.suggested_fix:
            lines.append(f"  suggested_fix: {finding.suggested_fix}")
        if finding.evidence:
            lines.append(f"  evidence: {json.dumps(_jsonable(finding.evidence), sort_keys=True)}")
    return "\n".join(lines)


def foundation_contract_report_to_json(report: FoundationContractReport) -> str:
    """Serialize a foundation contract report to stable JSON."""

    payload = {
        "module_name": report.module_name,
        "passed": report.passed,
        "summary": _jsonable(report.summary),
        "readability": _readability_payload(report.readability),
        "cdc": _cdc_payload(report.cdc),
        "diagnostics": json.loads(diagnostic_report_to_json(report.diagnostics)),
    }
    return json.dumps(payload, sort_keys=True, indent=2)


def _module_name(module: Any) -> str:
    return str(getattr(module, "name", None) or getattr(module, "_type_name", None) or module.__class__.__name__)


def _dedupe_diagnostics(findings: Sequence[DiagnosticFinding]) -> list[DiagnosticFinding]:
    deduped: list[DiagnosticFinding] = []
    seen: set[tuple[str, str, Optional[str], Optional[int], str]] = set()
    for finding in findings:
        key = (
            finding.rule,
            finding.category,
            finding.source_file,
            finding.source_line,
            finding.obj,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _diagnostic_counts(findings: Sequence[DiagnosticFinding]) -> Mapping[str, int]:
    return {
        "error": sum(1 for finding in findings if finding.severity == "error"),
        "warning": sum(1 for finding in findings if finding.severity == "warning"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }


def _summary_text(value: object) -> str:
    if not isinstance(value, Mapping):
        return str(value)
    parts = []
    for key, item in value.items():
        if key == "enabled":
            continue
        parts.append(f"{key}={item}")
    return ", ".join(parts) if parts else "not_run"


def _format_source(source_file: Optional[str], source_line: Optional[int]) -> str:
    if source_file and source_line is not None:
        return f"{source_file}:{source_line}"
    if source_file:
        return source_file
    if source_line is not None:
        return f"<unknown>:{source_line}"
    return "<unknown>"


def _readability_payload(report: Optional[ReadabilityReport]) -> Optional[Mapping[str, object]]:
    if report is None:
        return None
    return {
        "profile": report.profile,
        "passed": report.passed,
        "line_count": report.line_count,
        "max_line_length": report.max_line_length,
        "long_line_count": report.long_line_count,
        "anonymous_helper_count": report.anonymous_helper_count,
        "duplicated_block_prefix_count": report.duplicated_block_prefix_count,
        "deep_mux_assign_count": report.deep_mux_assign_count,
        "missing_header_count": report.missing_header_count,
        "missing_port_table_count": report.missing_port_table_count,
        "unlabeled_always_block_count": report.unlabeled_always_block_count,
        "unstable_generated_name_count": report.unstable_generated_name_count,
        "source_map_noise_count": report.source_map_noise_count,
        "memory_block_not_grouped_count": report.memory_block_not_grouped_count,
        "clock_reset_not_visible_count": report.clock_reset_not_visible_count,
    }


def _cdc_payload(report: Optional[CdcReport]) -> Optional[Mapping[str, object]]:
    if report is None:
        return None
    return {
        "module_name": report.module_name,
        "clock_domains": report.clock_domains,
        "findings": [
            {
                "category": finding.category,
                "severity": finding.severity,
                "message": finding.message,
            }
            for finding in report.findings
        ],
    }


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = [
    "FoundationContractReport",
    "analyze_foundation_contract",
    "emit_foundation_contract_markdown",
    "foundation_contract_report_to_json",
]

