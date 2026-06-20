"""Helpers for running generated UVM bundles on a remote VCS host."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from typing import Any, Iterable, Mapping, Optional

from rtlgen_x.verify.uvm import generate_uvm_runtime_bundle, write_uvm_runtime_bundle


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
) -> RemoteUvmRunResult:
    """Generate, upload, and execute one UVM/VCS probe on a remote host."""

    bundle = generate_uvm_runtime_bundle(
        module,
        clock_name=clock_name,
        dut_source=dut_source,
        dut_module_name=dut_module_name,
    )
    if local_bundle_dir is None:
        local_dir = Path(tempfile.mkdtemp(prefix=f"rtlgen_x_remote_uvm_{bundle.module_name}_"))
    else:
        local_dir = Path(local_bundle_dir)
    write_uvm_runtime_bundle(bundle, local_dir, include_runtime_package=False)

    remote_dir = remote_dir or default_remote_dir(bundle.module_name)
    archive = _tar_directory(local_dir)

    subprocess.run(
        ["ssh", host, f"mkdir -p {remote_dir}"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["ssh", host, f"tar xzf - -C {remote_dir}"],
        input=archive,
        check=True,
        capture_output=True,
    )
    run_cmd = (
        f"source {source_script} && "
        f"cd {remote_dir} && "
        "chmod +x run_vcs.sh && "
        "./run_vcs.sh"
    )
    completed = subprocess.run(
        ["ssh", host, f"bash -lc '{run_cmd}'"],
        capture_output=True,
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
