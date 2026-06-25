"""Helpers for running generated UVM bundles on a remote VCS host."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from typing import Any, Iterable, Mapping, Optional, Sequence

from rtlgen_x.verify.uvm import (
    UvmSequenceStep,
    describe_verification_interface,
    generate_uvm_runtime_bundle,
    write_uvm_runtime_bundle,
)


class RemoteUvmError(RuntimeError):
    """One actionable remote-UVM execution failure."""


@dataclass(frozen=True)
class RemoteUvmEnvironmentReport:
    host: str
    source_script: str
    returncode: int
    stdout: str
    stderr: str
    vcs_path: Optional[str]
    environment_ok: bool


@dataclass(frozen=True)
class RemoteUvmSummary:
    passed: bool
    severity_counts: Mapping[str, int]
    scoreboard_lines: tuple[str, ...]


@dataclass(frozen=True)
class RemoteUvmRunResult:
    host: str
    remote_dir: str
    local_bundle_dir: Path
    stdout: str
    stderr: str
    returncode: int
    summary: RemoteUvmSummary


@dataclass(frozen=True)
class RemoteUvmTarget:
    """One remote-regression target description."""

    name: str
    module_file: Path
    module_class: str
    clock_name: str = "clk"
    directed_sequence: Optional[tuple[UvmSequenceStep, ...]] = None


@dataclass(frozen=True)
class RemoteUvmRegressionEntry:
    """One regression target outcome."""

    target: RemoteUvmTarget
    status: str
    result: Optional[RemoteUvmRunResult] = None
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == "passed"


@dataclass(frozen=True)
class RemoteUvmRegressionReport:
    """Summary of a multi-target remote UVM regression."""

    entries: tuple[RemoteUvmRegressionEntry, ...]

    @property
    def passed(self) -> tuple[RemoteUvmRegressionEntry, ...]:
        return tuple(entry for entry in self.entries if entry.passed)

    @property
    def failed(self) -> tuple[RemoteUvmRegressionEntry, ...]:
        return tuple(entry for entry in self.entries if not entry.passed)

    def to_dict(self) -> dict[str, object]:
        return {
            "total": len(self.entries),
            "passed": len(self.passed),
            "failed": len(self.failed),
            "entries": [_entry_to_dict(entry) for entry in self.entries],
        }


def write_remote_uvm_regression_report(
    report: RemoteUvmRegressionReport,
    path: Path | str,
) -> Path:
    """Persist a remote UVM regression report as JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def load_module_instance(module_file: Path | str, class_name: str) -> Any:
    """Load and instantiate one module class from a Python file."""

    path = Path(module_file).resolve()
    spec = importlib.util.spec_from_file_location(f"rtlgen_x_remote_uvm_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load module file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name)
    return cls()


def coerce_uvm_sequence_steps(
    payload: Optional[Sequence[UvmSequenceStep | Mapping[str, object]]],
) -> Optional[tuple[UvmSequenceStep, ...]]:
    """Normalize JSON- or API-supplied directed steps into UvmSequenceStep objects."""

    if payload is None:
        return None
    steps = []
    for index, step in enumerate(payload):
        if isinstance(step, UvmSequenceStep):
            steps.append(
                UvmSequenceStep(
                    inputs=dict(step.inputs),
                    label=step.label,
                    active_domains=tuple(dict.fromkeys(step.active_domains)),
                )
            )
            continue
        if not isinstance(step, Mapping):
            raise TypeError(f"directed sequence step {index} must be a mapping or UvmSequenceStep")
        if any(key in step for key in ("inputs", "label", "active_domains")):
            inputs_payload = step.get("inputs")
            if not isinstance(inputs_payload, Mapping):
                raise TypeError(
                    f"directed sequence step {index} must provide an 'inputs' mapping when using "
                    "structured step payloads"
                )
            label_payload = step.get("label")
            active_domains = _coerce_active_domains_payload(step.get("active_domains", ()), index=index)
            steps.append(
                UvmSequenceStep(
                    inputs=_coerce_input_mapping(inputs_payload, index=index),
                    label=None if label_payload is None else str(label_payload),
                    active_domains=active_domains,
                )
            )
            continue
        steps.append(
            UvmSequenceStep(
                inputs=_coerce_input_mapping(step, index=index),
            )
        )
    return tuple(steps)


def _canonicalize_sequence_active_domains_for_module(
    module: Any,
    directed_sequence: Optional[tuple[UvmSequenceStep, ...]],
) -> Optional[tuple[UvmSequenceStep, ...]]:
    """Prefer declared semantic clock-domain names when the module exposes them.

    JSON/script payloads may still name physical clock ports such as `wr_clk`.
    For DSL-authored multi-clock modules that declared semantic domain names
    like `write` / `read`, normalize those aliases before bundle generation so
    remote UVM follows the same conventions as local Python-UVM and generated
    collateral tests.
    """

    if not directed_sequence:
        return directed_sequence
    try:
        interface = describe_verification_interface(module)
    except Exception:
        return directed_sequence
    if len(interface.clock_names) <= 1:
        return directed_sequence
    alias_to_domain = {canonical: canonical for canonical in interface.clock_names}
    for canonical, signal_name in zip(interface.clock_names, interface.clock_signals):
        alias_to_domain.setdefault(signal_name, canonical)
    normalized_steps = []
    for step in directed_sequence:
        if not step.active_domains:
            normalized_steps.append(step)
            continue
        normalized_steps.append(
            UvmSequenceStep(
                inputs=dict(step.inputs),
                label=step.label,
                active_domains=tuple(
                    dict.fromkeys(alias_to_domain.get(name, name) for name in step.active_domains)
                ),
            )
        )
    return tuple(normalized_steps)


def load_uvm_sequence_steps_json(path: Path | str) -> tuple[UvmSequenceStep, ...]:
    """Load one directed-sequence JSON file for remote UVM helpers/scripts."""

    json_path = Path(path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        if "directed_sequence" in payload:
            payload = payload["directed_sequence"]
        elif "steps" in payload:
            payload = payload["steps"]
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        raise TypeError(
            f"directed sequence JSON must be a list of steps or an object containing "
            f"'directed_sequence'/'steps': {json_path}"
        )
    normalized = coerce_uvm_sequence_steps(payload)
    return normalized or ()


def load_remote_uvm_targets_json(path: Path | str) -> tuple[RemoteUvmTarget, ...]:
    """Load regression targets from JSON target specs or prior regression reports."""

    json_path = Path(path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    raw_targets: object = payload
    if isinstance(payload, Mapping):
        if "targets" in payload:
            raw_targets = payload["targets"]
        elif "entries" in payload:
            raw_targets = [entry["target"] for entry in payload["entries"]]
        elif {"name", "module_file", "module_class"} <= set(payload):
            raw_targets = [payload]
    if not isinstance(raw_targets, Sequence) or isinstance(raw_targets, (str, bytes, bytearray)):
        raise TypeError(
            f"remote UVM targets JSON must be a list, a 'targets' object, or a regression "
            f"report 'entries' object: {json_path}"
        )
    targets = []
    for index, entry in enumerate(raw_targets):
        if not isinstance(entry, Mapping):
            raise TypeError(f"remote UVM target {index} must be a mapping")
        missing = [field for field in ("name", "module_file", "module_class") if field not in entry]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"remote UVM target {index} is missing required fields: {joined}")
        sequence_payload = entry.get("directed_sequence")
        targets.append(
            RemoteUvmTarget(
                name=str(entry["name"]),
                module_file=Path(str(entry["module_file"])),
                module_class=str(entry["module_class"]),
                clock_name=str(entry.get("clock_name", entry.get("clock", "clk"))),
                directed_sequence=coerce_uvm_sequence_steps(sequence_payload)
                if sequence_payload is not None
                else None,
            )
        )
    return tuple(targets)


def summarize_uvm_output(output: str) -> RemoteUvmSummary:
    """Extract a compact pass/fail summary from VCS/UVM stdout."""

    severity_counts = {}
    for severity in ("UVM_INFO", "UVM_WARNING", "UVM_ERROR", "UVM_FATAL"):
        match = re.search(rf"^{severity}\s*:\s*(\d+)\s*$", output, flags=re.MULTILINE)
        severity_counts[severity] = int(match.group(1)) if match else 0
    scoreboard_lines = tuple(
        line.strip()
        for line in output.splitlines()
        if "scoreboard passed" in line.lower() or "scoreboard" in line.lower() and "UVM_" in line
    )
    passed = (
        severity_counts.get("UVM_ERROR", 0) == 0
        and severity_counts.get("UVM_FATAL", 0) == 0
        and any("scoreboard passed" in line.lower() for line in scoreboard_lines)
    )
    return RemoteUvmSummary(
        passed=passed,
        severity_counts=severity_counts,
        scoreboard_lines=scoreboard_lines,
    )


def default_remote_dir(module_name: str) -> str:
    """Return a stable default remote work directory shell path."""

    stem = re.sub(r"[^0-9a-zA-Z_]+", "_", module_name).strip("_").lower() or "module"
    return f"$HOME/rtlgen_x/uvm_probe_{stem}"


def probe_remote_uvm_environment(
    *,
    host: str,
    source_script: str = "/apps/EDAs/syn.bash",
) -> RemoteUvmEnvironmentReport:
    """Check SSH reachability plus remote simulator environment readiness."""

    command = (
        f"bash -lc 'source {source_script} >/dev/null 2>&1 && "
        "if command -v vcs >/dev/null 2>&1; then "
        "printf \"RTLGEN_X_VCS=%s\\n\" \"$(command -v vcs)\"; "
        "else "
        "echo RTLGEN_X_VCS=; "
        "exit 2; "
        "fi'"
    )
    completed = _run_remote_ssh(
        host,
        command,
        step="probe remote UVM environment",
        check=False,
        text=True,
    )
    stdout = _decode_remote_stream(completed.stdout)
    stderr = _decode_remote_stream(completed.stderr)
    vcs_path = None
    for line in stdout.splitlines():
        if line.startswith("RTLGEN_X_VCS="):
            candidate = line.split("=", 1)[1].strip()
            vcs_path = candidate or None
            break
    return RemoteUvmEnvironmentReport(
        host=host,
        source_script=source_script,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        vcs_path=vcs_path,
        environment_ok=completed.returncode == 0 and bool(vcs_path),
    )


def run_remote_uvm_probe(
    module: Any,
    *,
    clock_name: str,
    host: str,
    remote_dir: Optional[str] = None,
    source_script: str = "/apps/EDAs/syn.bash",
    local_bundle_dir: Optional[Path | str] = None,
    dut_source: Optional[str] = None,
    dut_module_name: Optional[str] = None,
    directed_sequence: Optional[Sequence[UvmSequenceStep | Mapping[str, int]]] = None,
) -> RemoteUvmRunResult:
    """Generate, upload, and execute one UVM/VCS probe on a remote host."""

    normalized_directed_sequence = coerce_uvm_sequence_steps(directed_sequence)
    normalized_directed_sequence = _canonicalize_sequence_active_domains_for_module(
        module,
        normalized_directed_sequence,
    )
    bundle = generate_uvm_runtime_bundle(
        module,
        clock_name=clock_name,
        dut_source=dut_source,
        dut_module_name=dut_module_name,
        directed_sequence=normalized_directed_sequence,
    )
    if local_bundle_dir is None:
        local_dir = Path(tempfile.mkdtemp(prefix=f"rtlgen_x_remote_uvm_{bundle.module_name}_"))
    else:
        local_dir = Path(local_bundle_dir)
    write_uvm_runtime_bundle(bundle, local_dir, include_runtime_package=False)

    remote_dir = remote_dir or default_remote_dir(bundle.module_name)
    archive = _tar_directory(local_dir)

    _run_remote_ssh(
        host,
        f"mkdir -p {remote_dir}",
        step="prepare remote work directory",
    )
    _run_remote_ssh(
        host,
        f"tar xzf - -C {remote_dir}",
        step="upload UVM runtime bundle",
        input_data=archive,
        text=False,
    )
    run_cmd = (
        f"source {source_script} && "
        f"cd {remote_dir} && "
        "chmod +x run_vcs.sh && "
        "./run_vcs.sh"
    )
    completed = _run_remote_ssh(
        host,
        f"bash -lc '{run_cmd}'",
        step="run remote VCS/UVM probe",
        check=False,
        text=True,
    )
    summary = summarize_uvm_output(completed.stdout)
    return RemoteUvmRunResult(
        host=host,
        remote_dir=remote_dir,
        local_bundle_dir=local_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
        summary=summary,
    )


def run_remote_uvm_regression(
    targets: Iterable[RemoteUvmTarget],
    *,
    host: str,
    source_script: str = "/apps/EDAs/syn.bash",
    local_root: Optional[Path | str] = None,
) -> RemoteUvmRegressionReport:
    """Run a batch of remote UVM probes and capture per-target status."""

    entries = []
    root = Path(local_root) if local_root is not None else None
    for target in targets:
        local_bundle_dir = None if root is None else root / target.name
        try:
            module = load_module_instance(target.module_file, target.module_class)
            result = run_remote_uvm_probe(
                module,
                clock_name=target.clock_name,
                host=host,
                remote_dir=default_remote_dir(getattr(module, "name", target.name)),
                source_script=source_script,
                local_bundle_dir=local_bundle_dir,
                directed_sequence=target.directed_sequence,
            )
        except Exception as exc:
            entries.append(
                RemoteUvmRegressionEntry(
                    target=target,
                    status="local_error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        status = "passed" if result.returncode == 0 and result.summary.passed else "remote_fail"
        entries.append(
            RemoteUvmRegressionEntry(
                target=target,
                status=status,
                result=result,
            )
        )
    return RemoteUvmRegressionReport(entries=tuple(entries))


def _tar_directory(path: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for child in sorted(path.iterdir()):
            archive.add(child, arcname=child.name)
    return buffer.getvalue()


def _entry_to_dict(entry: RemoteUvmRegressionEntry) -> dict[str, object]:
    payload: dict[str, object] = {
        "target": {
            "name": entry.target.name,
            "module_file": str(entry.target.module_file),
            "module_class": entry.target.module_class,
            "clock_name": entry.target.clock_name,
            "directed_sequence": (
                [
                    {
                        "inputs": dict(step.inputs),
                        "label": step.label,
                        "active_domains": list(step.active_domains),
                    }
                    for step in entry.target.directed_sequence
                ]
                if entry.target.directed_sequence is not None
                else None
            ),
        },
        "status": entry.status,
        "passed": entry.passed,
        "error": entry.error,
    }
    if entry.result is not None:
        payload["result"] = {
            "host": entry.result.host,
            "remote_dir": entry.result.remote_dir,
            "local_bundle_dir": str(entry.result.local_bundle_dir),
            "returncode": entry.result.returncode,
            "summary": asdict(entry.result.summary),
            "stdout": entry.result.stdout,
            "stderr": entry.result.stderr,
        }
    return payload


def _run_remote_ssh(
    host: str,
    command: str,
    *,
    step: str,
    input_data: bytes | None = None,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["ssh", host, command],
        input=input_data,
        capture_output=True,
        text=text,
    )
    if check and completed.returncode != 0:
        raise RemoteUvmError(_format_remote_failure(host, step, command, completed))
    return completed


def _format_remote_failure(
    host: str,
    step: str,
    command: str,
    completed: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes],
) -> str:
    stdout = _decode_remote_stream(completed.stdout)
    stderr = _decode_remote_stream(completed.stderr)
    details = []
    if stdout:
        details.append(f"stdout:\n{stdout}")
    if stderr:
        details.append(f"stderr:\n{stderr}")
    hint = _remote_failure_hint(stdout=stdout, stderr=stderr)
    parts = [
        f"remote UVM step failed: {step}",
        f"host: {host}",
        f"command: {command}",
        f"returncode: {completed.returncode}",
    ]
    if hint:
        parts.append(f"hint: {hint}")
    if details:
        parts.extend(details)
    return "\n".join(parts)


def _decode_remote_stream(stream: object) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace").strip()
    return str(stream).strip()


def _remote_failure_hint(*, stdout: str, stderr: str) -> str:
    haystack = f"{stdout}\n{stderr}".lower()
    if "permission denied" in haystack or "publickey" in haystack:
        return "SSH authentication failed; confirm this environment can access your ssh-agent/key for the target host."
    if "could not resolve hostname" in haystack or "name or service not known" in haystack:
        return "SSH hostname resolution failed; check network reachability and host spelling."
    if "no such file or directory" in haystack and "syn.bash" in haystack:
        return "The remote source_script path is missing; verify /apps/EDAs/syn.bash or pass the correct setup script."
    if "vcs not found" in haystack:
        return "VCS was not found after sourcing the remote environment; verify the setup script and license/tool installation."
    if "license" in haystack and "vcs" in haystack:
        return "VCS appears to have a licensing/setup problem on the remote host."
    return ""


def _coerce_input_mapping(payload: Mapping[str, object], *, index: int) -> dict[str, int]:
    normalized = {}
    for name, value in payload.items():
        signal_name = str(name)
        if isinstance(value, bool):
            normalized[signal_name] = int(value)
            continue
        if isinstance(value, int):
            normalized[signal_name] = int(value)
            continue
        if isinstance(value, str):
            try:
                normalized[signal_name] = int(value, 0)
            except ValueError as exc:
                raise TypeError(
                    f"directed sequence step {index} input '{signal_name}' must be an int/bool or "
                    "a base-10/base-16 integer string"
                ) from exc
            continue
        raise TypeError(
            f"directed sequence step {index} input '{signal_name}' must be an int/bool or integer string"
        )
    return normalized


def _coerce_active_domains_payload(payload: object, index: int) -> tuple[str, ...]:
    if payload is None:
        return ()
    if isinstance(payload, Mapping):
        selected = [str(name) for name, enabled in payload.items() if enabled]
        return tuple(dict.fromkeys(selected))
    if isinstance(payload, str):
        return (payload,)
    if isinstance(payload, Sequence) and not isinstance(payload, (bytes, bytearray)):
        return tuple(dict.fromkeys(str(name) for name in payload))
    raise TypeError(
        f"directed sequence step {index} active_domains must be a sequence of names or a name->bool mapping"
    )
