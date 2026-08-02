"""Unified diagnostic report schema and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Mapping, Optional, Sequence


_SEVERITY_RANKS = {
    "info": 0,
    "warning": 1,
    "error": 2,
}


@dataclass(frozen=True)
class DiagnosticFinding:
    rule: str
    severity: str
    category: str
    message: str
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    obj: str = ""
    suggested_fix: str = ""
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in _SEVERITY_RANKS:
            raise ValueError(
                f"unknown diagnostic severity {self.severity!r}; "
                f"expected one of: {', '.join(_SEVERITY_RANKS)}"
            )


@dataclass(frozen=True)
class DiagnosticReport:
    name: str
    passed: bool
    findings: tuple[DiagnosticFinding, ...] = ()

    @property
    def error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "info")


def severity_rank(severity: str) -> int:
    """Return the ordering rank for a supported severity."""

    try:
        return _SEVERITY_RANKS[severity]
    except KeyError as exc:
        raise ValueError(
            f"unknown diagnostic severity {severity!r}; "
            f"expected one of: {', '.join(_SEVERITY_RANKS)}"
        ) from exc


def emit_diagnostic_report_markdown(report: DiagnosticReport) -> str:
    """Render a diagnostic report in a compact, stable Markdown form."""

    lines = [
        f"# Diagnostic Report: {report.name}",
        "",
        f"- passed: `{str(report.passed).lower()}`",
        f"- findings: `{len(report.findings)}`",
        f"- errors: `{report.error_count}`",
        f"- warnings: `{report.warning_count}`",
        f"- info: `{report.info_count}`",
    ]
    if not report.findings:
        lines.append("")
        lines.append("No findings.")
        return "\n".join(lines)

    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for finding in report.findings:
        source = _format_source(finding.source_file, finding.source_line)
        header = (
            f"- [{finding.rule}] severity={finding.severity} "
            f"category={finding.category} source={source}"
        )
        if finding.obj:
            header += f" object={finding.obj}"
        if finding.suggested_fix:
            header += f" suggested_fix={finding.suggested_fix}"
        lines.append(header)
        lines.append(f"  message: {finding.message}")
        if finding.evidence:
            lines.append(f"  evidence: {_stable_json(finding.evidence)}")
    return "\n".join(lines)


def diagnostic_report_to_json(report: DiagnosticReport) -> str:
    """Serialize a diagnostic report to stable JSON."""

    payload = {
        "name": report.name,
        "passed": report.passed,
        "findings": [_finding_to_payload(finding) for finding in report.findings],
    }
    return json.dumps(payload, sort_keys=True, indent=2)


def merge_diagnostic_reports(name: str, reports: Sequence[DiagnosticReport]) -> DiagnosticReport:
    """Merge several diagnostic reports while preserving finding order."""

    findings: list[DiagnosticFinding] = []
    for report in reports:
        findings.extend(report.findings)
    passed = all(report.passed for report in reports) and not any(f.severity == "error" for f in findings)
    return DiagnosticReport(name=name, passed=passed, findings=tuple(findings))


def diagnostic_from_readability_finding(finding: object, *, severity: str = "warning") -> DiagnosticFinding:
    """Adapt a readability finding into the unified diagnostic schema."""

    kind = str(getattr(finding, "kind", "readability"))
    line = getattr(finding, "line", None)
    detail = str(getattr(finding, "detail", "readability contract finding"))
    return DiagnosticFinding(
        rule=_READABILITY_RULES.get(kind, _camel_rule("ReadableRtl", kind)),
        severity=severity,
        category="readability",
        message=detail,
        source_line=line if isinstance(line, int) else None,
        obj=f"line:{line}" if isinstance(line, int) else "",
        suggested_fix=_READABILITY_FIXES.get(kind, "Inspect the emitted review RTL and adjust the DSL or emit profile."),
        evidence={"kind": kind, "line": line},
    )


def diagnostics_from_readability_report(report: object, *, severity: str = "warning") -> DiagnosticReport:
    findings = tuple(
        diagnostic_from_readability_finding(finding, severity=severity)
        for finding in getattr(report, "findings", ())
    )
    return DiagnosticReport(
        name=f"readability:{getattr(report, 'profile', 'unknown')}",
        passed=not any(finding.severity == "error" for finding in findings),
        findings=findings,
    )


def diagnostic_from_cdc_finding(finding: object) -> DiagnosticFinding:
    """Adapt a CDC finding into the unified diagnostic schema."""

    category = str(getattr(finding, "category", "cdc"))
    src = getattr(finding, "src", None)
    dst = getattr(finding, "dst", None)
    source_file = getattr(src, "source_file", None) or getattr(dst, "source_file", None)
    source_line = getattr(src, "source_line", None) or getattr(dst, "source_line", None)
    src_name = getattr(src, "signal_name", "")
    dst_name = getattr(dst, "signal_name", "")
    suggestions = tuple(str(item) for item in getattr(finding, "suggestions", ()) or ())
    evidence = dict(getattr(finding, "evidence", {}) or {})
    evidence["cdc_category"] = category
    if src is not None:
        evidence["src"] = _endpoint_payload(src)
    if dst is not None:
        evidence["dst"] = _endpoint_payload(dst)
    return DiagnosticFinding(
        rule=_CDC_RULES.get(category, "CdcUnsafeCrossing"),
        severity=str(getattr(finding, "severity", "warning")),
        category="cdc",
        message=str(getattr(finding, "message", "CDC finding")),
        source_file=str(source_file) if source_file else None,
        source_line=source_line if isinstance(source_line, int) else None,
        obj=_join_object(src_name, dst_name),
        suggested_fix="; ".join(suggestions),
        evidence=evidence,
    )


def diagnostics_from_cdc_report(report: object) -> DiagnosticReport:
    findings = tuple(diagnostic_from_cdc_finding(finding) for finding in getattr(report, "findings", ()))
    return DiagnosticReport(
        name=f"cdc:{getattr(report, 'module_name', 'unknown')}",
        passed=not any(finding.severity == "error" for finding in findings),
        findings=findings,
    )


def diagnostic_from_exception(exc: BaseException, *, rule: Optional[str] = None, category: Optional[str] = None) -> DiagnosticFinding:
    """Adapt an exception into the diagnostic schema.

    The parser recognizes the existing ``format_diagnostic(...)`` text shape,
    while still preserving the original exception text as evidence.
    """

    text = str(exc)
    parsed_rule = rule or _parse_bracketed_rule(text) or exc.__class__.__name__
    source = _parse_field(text, "source")
    obj = _parse_field(text, "object") or ""
    suggested_fix = _parse_suggested_fix(text)
    source_file, source_line = _split_source(source)
    severity = _parse_field(text, "severity") or "error"
    return DiagnosticFinding(
        rule=parsed_rule,
        severity=severity if severity in _SEVERITY_RANKS else "error",
        category=category or _category_for_exception_rule(parsed_rule),
        message=text,
        source_file=source_file,
        source_line=source_line,
        obj=obj,
        suggested_fix=suggested_fix,
        evidence={"exception_type": exc.__class__.__name__, "text": text},
    )


_READABILITY_RULES = {
    "long_line": "ReadableRtlLongLine",
    "anonymous_helper": "ReadableRtlAnonymousHelper",
    "duplicated_block_prefix": "ReadableRtlDuplicatedBlockPrefix",
    "deep_mux_assign": "ReadableRtlDeepMuxAssign",
    "missing_module_header": "ReadableRtlMissingModuleHeader",
    "missing_port_table": "ReadableRtlMissingPortTable",
    "unlabeled_always_block": "ReadableRtlUnlabeledAlwaysBlock",
    "unstable_generated_name": "ReadableRtlUnstableGeneratedName",
    "source_map_noise": "ReadableRtlSourceMapNoise",
    "memory_block_not_grouped": "ReadableRtlMemoryBlockNotGrouped",
    "clock_reset_not_visible": "ReadableRtlClockResetNotVisible",
}

_READABILITY_FIXES = {
    "long_line": "Break complex expressions into named wires or smaller statements.",
    "anonymous_helper": "Give helper logic a stable authored name or use the review profile.",
    "duplicated_block_prefix": "Remove duplicated review block labels.",
    "deep_mux_assign": "Split the mux chain into named intermediate logic or a case-style block.",
    "missing_module_header": "Emit review RTL with headers enabled.",
    "missing_port_table": "Emit review RTL with the port table enabled.",
    "unlabeled_always_block": "Add or preserve a nearby Comb/Seq block label.",
    "unstable_generated_name": "Avoid leaking generated helper names into review RTL.",
    "source_map_noise": "Move dense source mapping into a sidecar map or reduce inline comments.",
    "memory_block_not_grouped": "Group memory declarations under the storage section marker.",
    "clock_reset_not_visible": "Preserve the sequential timing comment before the always block.",
}

_CDC_RULES = {
    "reset_release_crossing": "CdcResetReleaseCrossing",
    "single_bit_crossing": "CdcUnsafeCrossing",
    "pulse_crossing": "CdcUnsafeCrossing",
    "multi_bit_crossing": "CdcUnsafeCrossing",
    "memory_crossing": "CdcUnsafeCrossing",
    "multi_writer_state": "CdcUnsafeCrossing",
    "multi_writer_memory": "CdcUnsafeCrossing",
}


def _finding_to_payload(finding: DiagnosticFinding) -> Mapping[str, Any]:
    return {
        "rule": finding.rule,
        "severity": finding.severity,
        "category": finding.category,
        "message": finding.message,
        "source_file": finding.source_file,
        "source_line": finding.source_line,
        "object": finding.obj,
        "suggested_fix": finding.suggested_fix,
        "evidence": _jsonable(finding.evidence),
    }


def _endpoint_payload(endpoint: object) -> Mapping[str, object]:
    return {
        "signal_name": getattr(endpoint, "signal_name", ""),
        "clock_domain": getattr(endpoint, "clock_domain", None),
        "width": getattr(endpoint, "width", 0),
        "kind": getattr(endpoint, "kind", ""),
        "source_file": getattr(endpoint, "source_file", None),
        "source_line": getattr(endpoint, "source_line", None),
    }


def _format_source(source_file: Optional[str], source_line: Optional[int]) -> str:
    if source_file and source_line is not None:
        return f"{source_file}:{source_line}"
    if source_file:
        return source_file
    if source_line is not None:
        return f"<unknown>:{source_line}"
    return "<unknown>"


def _stable_json(value: object) -> str:
    return json.dumps(_jsonable(value), sort_keys=True)


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _camel_rule(prefix: str, kind: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", kind) if part]
    suffix = "".join(part[:1].upper() + part[1:] for part in parts) or "Finding"
    return f"{prefix}{suffix}"


def _join_object(src_name: object, dst_name: object) -> str:
    src_text = str(src_name) if src_name else ""
    dst_text = str(dst_name) if dst_name else ""
    if src_text and dst_text:
        return f"{src_text}->{dst_text}"
    return src_text or dst_text


def _parse_bracketed_rule(text: str) -> Optional[str]:
    match = re.match(r"^\[([^\]]+)\]", text.strip())
    return match.group(1) if match else None


def _parse_field(text: str, field_name: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(field_name)}=([^\s]+)", text)
    return match.group(1) if match else None


def _parse_suggested_fix(text: str) -> str:
    marker = "suggested_fix="
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = text.find(". ", start)
    if end < 0:
        end = len(text)
    return text[start:end].strip()


def _split_source(source: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    if not source or source == "<unknown>":
        return None, None
    match = re.match(r"^(.*):(\d+)$", source)
    if match:
        return match.group(1), int(match.group(2))
    return source, None


def _category_for_exception_rule(rule: str) -> str:
    if rule == "UnsupportedStorageContract":
        return "storage"
    if rule == "UnknownSubmodulePort" or rule.startswith("Untracked"):
        return "authoring"
    return "lowering"


__all__ = [
    "DiagnosticFinding",
    "DiagnosticReport",
    "diagnostic_from_cdc_finding",
    "diagnostic_from_exception",
    "diagnostic_from_readability_finding",
    "diagnostic_report_to_json",
    "diagnostics_from_cdc_report",
    "diagnostics_from_readability_report",
    "emit_diagnostic_report_markdown",
    "merge_diagnostic_reports",
    "severity_rank",
]

