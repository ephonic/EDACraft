"""Trace-oriented protocol rule checkers for Python-side verification flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from rtlgen.verify.directed import TraceSample


@dataclass(frozen=True)
class ProtocolViolation:
    protocol: str
    cycle: int
    rule: str
    severity: str
    message: str
    signal_values: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtocolCheckReport:
    protocol: str
    violations: Tuple[ProtocolViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def error_count(self) -> int:
        return sum(1 for violation in self.violations if violation.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for violation in self.violations if violation.severity == "warning")


def check_ready_valid_trace(
    source: Any,
    *,
    protocol_name: str = "ReadyValid",
    data_name: str = "data",
    valid_name: str = "valid",
    ready_name: str = "ready",
    last_name: Optional[str] = None,
    keep_name: Optional[str] = None,
    user_name: Optional[str] = None,
    extra_payload_names: Sequence[str] = (),
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    payload_fields = [data_name]
    if last_name is not None:
        payload_fields.append(last_name)
    if keep_name is not None:
        payload_fields.append(keep_name)
    if user_name is not None:
        payload_fields.append(user_name)
    payload_fields.extend(extra_payload_names)
    violations = _check_stall_stability(
        traces,
        protocol=protocol_name,
        channel="ready_valid",
        valid_name=valid_name,
        ready_name=ready_name,
        payload_fields=tuple(payload_fields),
    )
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def check_axistream_trace(
    source: Any,
    *,
    protocol_name: str = "AXI4Stream",
    data_name: str = "tdata",
    valid_name: str = "tvalid",
    ready_name: str = "tready",
    last_name: str = "tlast",
    keep_name: str = "tkeep",
    user_name: str = "tuser",
    strb_name: str = "tstrb",
) -> ProtocolCheckReport:
    return check_ready_valid_trace(
        source,
        protocol_name=protocol_name,
        data_name=data_name,
        valid_name=valid_name,
        ready_name=ready_name,
        last_name=last_name,
        keep_name=keep_name,
        user_name=user_name,
        extra_payload_names=(strb_name,),
    )


def check_reqrsp_trace(
    source: Any,
    *,
    protocol_name: str = "ReqRsp",
    req_name: str = "req",
    req_valid_name: str = "req_valid",
    req_ready_name: str = "req_ready",
    rsp_name: str = "rsp",
    rsp_valid_name: str = "rsp_valid",
    rsp_ready_name: str = "rsp_ready",
    addr_name: Optional[str] = "addr",
    write_name: Optional[str] = "write",
    strb_name: Optional[str] = "strb",
    extra_req_payload_names: Sequence[str] = (),
    extra_rsp_payload_names: Sequence[str] = (),
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    violations = []

    req_payload_fields = [req_name]
    if addr_name is not None:
        req_payload_fields.append(addr_name)
    if write_name is not None:
        req_payload_fields.append(write_name)
    if strb_name is not None:
        req_payload_fields.append(strb_name)
    req_payload_fields.extend(extra_req_payload_names)

    rsp_payload_fields = [rsp_name]
    rsp_payload_fields.extend(extra_rsp_payload_names)

    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="req",
            valid_name=req_valid_name,
            ready_name=req_ready_name,
            payload_fields=tuple(req_payload_fields),
        )
    )
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="rsp",
            valid_name=rsp_valid_name,
            ready_name=rsp_ready_name,
            payload_fields=tuple(rsp_payload_fields),
        )
    )
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def check_apb_trace(
    source: Any,
    *,
    protocol_name: str = "APB",
    select_name: str = "psel",
    enable_name: str = "penable",
    write_name: str = "pwrite",
    addr_name: str = "paddr",
    wdata_name: str = "pwdata",
    strb_name: str = "pstrb",
    prot_name: str = "pprot",
    ready_name: str = "pready",
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    violations = []
    previous: Optional[Dict[str, int]] = None
    previous_cycle: Optional[int] = None
    for trace in traces:
        sample = _merged_sample(trace)
        cycle = trace.cycle
        psel = _sig(sample, select_name)
        penable = _sig(sample, enable_name)
        pready = _sig(sample, ready_name, default=1)
        if penable and not psel:
            violations.append(
                _violation(
                    protocol_name,
                    cycle,
                    "access_requires_select",
                    f"`{enable_name}` asserted without `{select_name}`.",
                    sample,
                    (select_name, enable_name, addr_name, write_name),
                )
            )

        if previous is not None and previous_cycle is not None:
            prev_psel = _sig(previous, select_name)
            prev_penable = _sig(previous, enable_name)
            prev_pready = _sig(previous, ready_name, default=1)
            prev_setup = prev_psel and not prev_penable
            prev_wait = prev_psel and prev_penable and not prev_pready
            current_access = psel and penable

            if prev_setup and not current_access:
                violations.append(
                    _violation(
                        protocol_name,
                        cycle,
                        "setup_followed_by_access",
                        f"APB setup phase from cycle {previous_cycle} was not followed by an access phase.",
                        sample,
                        (select_name, enable_name, addr_name, write_name),
                    )
                )

            if current_access and not prev_setup and not prev_wait:
                violations.append(
                    _violation(
                        protocol_name,
                        cycle,
                        "access_requires_prior_setup",
                        "APB access phase must be preceded by setup or an existing wait-state access.",
                        sample,
                        (select_name, enable_name, addr_name, write_name, ready_name),
                    )
                )

            if (prev_setup or prev_wait) and current_access:
                for field_name in _apb_control_fields(
                    previous,
                    current=sample,
                    addr_name=addr_name,
                    write_name=write_name,
                    wdata_name=wdata_name,
                    strb_name=strb_name,
                    prot_name=prot_name,
                ):
                    if _sig(previous, field_name) != _sig(sample, field_name):
                        violations.append(
                            _violation(
                                protocol_name,
                                cycle,
                                "control_stable_during_access",
                                f"APB control field `{field_name}` changed during setup/access at cycle {cycle}.",
                                sample,
                                (field_name, select_name, enable_name, ready_name),
                            )
                        )
        previous = sample
        previous_cycle = cycle
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def check_wishbone_trace(
    source: Any,
    *,
    protocol_name: str = "Wishbone",
    addr_name: str = "adr_i",
    wdata_name: str = "dat_i",
    rdata_name: str = "dat_o",
    write_name: str = "we_i",
    sel_name: str = "sel_i",
    stb_name: str = "stb_i",
    cyc_name: str = "cyc_i",
    ack_name: str = "ack_o",
    err_name: str = "err_o",
    retry_name: str = "rty_o",
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    violations = []
    previous: Optional[Dict[str, int]] = None
    previous_cycle: Optional[int] = None
    for trace in traces:
        sample = _merged_sample(trace)
        cycle = trace.cycle
        stb = _sig(sample, stb_name)
        cyc = _sig(sample, cyc_name)
        terminated = _sig(sample, ack_name) or _sig(sample, err_name) or _sig(sample, retry_name)
        request = stb and cyc

        if stb and not cyc:
            violations.append(
                _violation(
                    protocol_name,
                    cycle,
                    "strobe_requires_cycle",
                    f"`{stb_name}` asserted without `{cyc_name}`.",
                    sample,
                    (stb_name, cyc_name, addr_name, write_name),
                )
            )
        if terminated and not request:
            violations.append(
                _violation(
                    protocol_name,
                    cycle,
                    "response_requires_request",
                    "Wishbone response asserted without an active request.",
                    sample,
                    (ack_name, err_name, retry_name, stb_name, cyc_name, rdata_name),
                )
            )

        if previous is not None and previous_cycle is not None:
            prev_request = _sig(previous, stb_name) and _sig(previous, cyc_name)
            prev_terminated = _sig(previous, ack_name) or _sig(previous, err_name) or _sig(previous, retry_name)
            if prev_request and not prev_terminated:
                if not request:
                    violations.append(
                        _violation(
                            protocol_name,
                            cycle,
                            "request_hold_until_termination",
                            f"Wishbone request from cycle {previous_cycle} was dropped before termination.",
                            sample,
                            (stb_name, cyc_name, ack_name, err_name, retry_name),
                        )
                    )
                else:
                    for field_name in _wishbone_control_fields(
                        previous,
                        current=sample,
                        addr_name=addr_name,
                        write_name=write_name,
                        wdata_name=wdata_name,
                        sel_name=sel_name,
                    ):
                        if _sig(previous, field_name) != _sig(sample, field_name):
                            violations.append(
                                _violation(
                                    protocol_name,
                                    cycle,
                                    "request_stable_while_waiting",
                                    f"Wishbone control field `{field_name}` changed before request termination.",
                                    sample,
                                    (field_name, stb_name, cyc_name, ack_name),
                                )
                            )
        previous = sample
        previous_cycle = cycle
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def check_axilite_trace(
    source: Any,
    *,
    protocol_name: str = "AXI4Lite",
    awaddr_name: str = "awaddr",
    awvalid_name: str = "awvalid",
    awready_name: str = "awready",
    awprot_name: str = "awprot",
    wdata_name: str = "wdata",
    wstrb_name: str = "wstrb",
    wvalid_name: str = "wvalid",
    wready_name: str = "wready",
    bresp_name: str = "bresp",
    bvalid_name: str = "bvalid",
    bready_name: str = "bready",
    araddr_name: str = "araddr",
    arvalid_name: str = "arvalid",
    arready_name: str = "arready",
    arprot_name: str = "arprot",
    rdata_name: str = "rdata",
    rresp_name: str = "rresp",
    rvalid_name: str = "rvalid",
    rready_name: str = "rready",
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    violations = []
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="aw",
            valid_name=awvalid_name,
            ready_name=awready_name,
            payload_fields=(awaddr_name, awprot_name),
        )
    )
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="w",
            valid_name=wvalid_name,
            ready_name=wready_name,
            payload_fields=(wdata_name, wstrb_name),
        )
    )
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="b",
            valid_name=bvalid_name,
            ready_name=bready_name,
            payload_fields=(bresp_name,),
        )
    )
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="ar",
            valid_name=arvalid_name,
            ready_name=arready_name,
            payload_fields=(araddr_name, arprot_name),
        )
    )
    violations.extend(
        _check_stall_stability_if_present(
            traces,
            protocol=protocol_name,
            channel="r",
            valid_name=rvalid_name,
            ready_name=rready_name,
            payload_fields=(rdata_name, rresp_name),
        )
    )
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def check_ahblite_trace(
    source: Any,
    *,
    protocol_name: str = "AHBLite",
    haddr_name: str = "haddr",
    htrans_name: str = "htrans",
    hwrite_name: str = "hwrite",
    hsize_name: str = "hsize",
    hburst_name: str = "hburst",
    hprot_name: str = "hprot",
    hwdata_name: str = "hwdata",
    hsel_name: str = "hsel",
    hready_name: str = "hready",
) -> ProtocolCheckReport:
    traces = _coerce_traces(source)
    violations = []
    pending_sample: Optional[Dict[str, int]] = None
    pending_cycle: Optional[int] = None
    for trace in traces:
        sample = _merged_sample(trace)
        cycle = trace.cycle
        hready = _sig(sample, hready_name, default=1)
        active = _ahb_is_active(sample, hsel_name=hsel_name, htrans_name=htrans_name)

        if pending_sample is not None and pending_cycle is not None:
            if not active:
                violations.append(
                    _violation(
                        protocol_name,
                        cycle,
                        "transfer_held_until_ready",
                        f"AHB-Lite transfer from cycle {pending_cycle} was dropped before `{hready_name}` returned high.",
                        sample,
                        (haddr_name, htrans_name, hwrite_name, hsize_name, hburst_name, hprot_name, hwdata_name, hsel_name, hready_name),
                    )
                )
            else:
                for field_name in (haddr_name, htrans_name, hwrite_name, hsize_name, hburst_name, hprot_name, hwdata_name, hsel_name):
                    if _sig(previous := pending_sample, field_name) != _sig(sample, field_name):
                        violations.append(
                            _violation(
                                protocol_name,
                                cycle,
                                "transfer_control_stable",
                                f"AHB-Lite control field `{field_name}` changed while waiting for `{hready_name}`.",
                                sample,
                                (field_name, hready_name, hsel_name),
                            )
                        )
        if active and not hready:
            pending_sample = sample
            pending_cycle = cycle
        else:
            pending_sample = None
            pending_cycle = None
    return ProtocolCheckReport(protocol=protocol_name, violations=tuple(violations))


def emit_protocol_check_report_markdown(
    report: ProtocolCheckReport,
    *,
    title: Optional[str] = None,
) -> str:
    heading = title or f"{report.protocol} Protocol Check"
    lines = [f"# {heading}", ""]
    lines.append(f"- protocol: `{report.protocol}`")
    lines.append(
        f"- violations: {len(report.violations)} "
        f"({report.error_count} errors, {report.warning_count} warnings)"
    )
    lines.append("")
    if not report.violations:
        lines.append("No protocol-rule violations detected in the provided trace.")
        return "\n".join(lines) + "\n"

    for index, violation in enumerate(report.violations, start=1):
        lines.append(f"## {index}. [{violation.severity}] {violation.rule}")
        lines.append("")
        lines.append(violation.message)
        lines.append("")
        lines.append(f"- cycle: {violation.cycle}")
        if violation.signal_values:
            lines.append("- signals:")
            for signal_name, value in sorted(violation.signal_values.items()):
                lines.append(f"  - `{signal_name}` = `{value}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def _coerce_traces(source: Any) -> Tuple[TraceSample, ...]:
    traces = getattr(source, "traces", source)
    if not isinstance(traces, Iterable):
        raise TypeError("protocol checker source must be a PythonUvmReport or iterable of TraceSample")
    normalized = []
    for trace in traces:
        if not isinstance(trace, TraceSample):
            raise TypeError("protocol checker source must contain TraceSample objects")
        normalized.append(trace)
    return tuple(normalized)


def _check_stall_stability_if_present(
    traces: Sequence[TraceSample],
    *,
    protocol: str,
    channel: str,
    valid_name: str,
    ready_name: str,
    payload_fields: Sequence[str],
) -> Tuple[ProtocolViolation, ...]:
    if not _signal_seen(traces, valid_name) or not _signal_seen(traces, ready_name):
        return ()
    return tuple(
        _check_stall_stability(
            traces,
            protocol=protocol,
            channel=channel,
            valid_name=valid_name,
            ready_name=ready_name,
            payload_fields=tuple(payload_fields),
        )
    )


def _check_stall_stability(
    traces: Sequence[TraceSample],
    *,
    protocol: str,
    channel: str,
    valid_name: str,
    ready_name: str,
    payload_fields: Sequence[str],
) -> Tuple[ProtocolViolation, ...]:
    violations = []
    pending_sample: Optional[Dict[str, int]] = None
    pending_cycle: Optional[int] = None
    for trace in traces:
        sample = _merged_sample(trace)
        cycle = trace.cycle
        valid = _sig(sample, valid_name)
        ready = _sig(sample, ready_name)
        if pending_sample is not None and pending_cycle is not None:
            if ready == 0 and valid == 0:
                violations.append(
                    _violation(
                        protocol,
                        cycle,
                        f"{channel}_valid_hold",
                        f"{protocol} channel `{channel}` deasserted `{valid_name}` before handshake after stall at cycle {pending_cycle}.",
                        sample,
                        (valid_name, ready_name),
                    )
                )
            if ready == 0:
                for field_name in payload_fields:
                    if _sig(sample, field_name) != _sig(pending_sample, field_name):
                        violations.append(
                            _violation(
                                protocol,
                                cycle,
                                f"{channel}_payload_stable",
                                f"{protocol} channel `{channel}` changed `{field_name}` while `{valid_name}` was stalled low on `{ready_name}`.",
                                sample,
                                (field_name, valid_name, ready_name),
                            )
                        )
        if valid and not ready:
            pending_sample = sample
            pending_cycle = cycle
        else:
            pending_sample = None
            pending_cycle = None
    return tuple(violations)


def _merged_sample(trace: TraceSample) -> Dict[str, int]:
    sample = dict(trace.inputs)
    sample.update(trace.outputs)
    return sample


def _signal_seen(traces: Sequence[TraceSample], name: str) -> bool:
    return any(name in trace.inputs or name in trace.outputs for trace in traces)


def _sig(sample: Mapping[str, int], name: str, *, default: int = 0) -> int:
    return int(sample.get(name, default))


def _apb_control_fields(
    previous: Mapping[str, int],
    *,
    current: Mapping[str, int],
    addr_name: str,
    write_name: str,
    wdata_name: str,
    strb_name: str,
    prot_name: str,
) -> Tuple[str, ...]:
    fields = [addr_name, write_name, strb_name, prot_name]
    if _sig(previous, write_name) or _sig(current, write_name):
        fields.append(wdata_name)
    return tuple(fields)


def _wishbone_control_fields(
    previous: Mapping[str, int],
    *,
    current: Mapping[str, int],
    addr_name: str,
    write_name: str,
    wdata_name: str,
    sel_name: str,
) -> Tuple[str, ...]:
    fields = [addr_name, write_name, sel_name]
    if _sig(previous, write_name) or _sig(current, write_name):
        fields.append(wdata_name)
    return tuple(fields)


def _ahb_is_active(
    sample: Mapping[str, int],
    *,
    hsel_name: str,
    htrans_name: str,
) -> bool:
    return bool(_sig(sample, hsel_name) and _sig(sample, htrans_name) in (2, 3))


def _violation(
    protocol: str,
    cycle: int,
    rule: str,
    message: str,
    sample: Mapping[str, int],
    signal_names: Sequence[str],
    *,
    severity: str = "error",
) -> ProtocolViolation:
    return ProtocolViolation(
        protocol=protocol,
        cycle=cycle,
        rule=rule,
        severity=severity,
        message=message,
        signal_values={name: _sig(sample, name) for name in signal_names if name in sample},
    )
