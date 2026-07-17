"""Artifact path resolution helpers.

These functions know the conventional ImplCraft work-root layout and provide
fallback searches for predecessor-stage outputs.  They depend only on the
state dataclass / artifact dict, not on any adapter internals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


WorkRoot = str | Path | None


def resolve_artifact_path(path: str, work_root: WorkRoot = None) -> Path:
    """Resolve an artifact path, interpreting relative paths against work_root."""
    p = Path(path)
    if p.is_absolute():
        return p
    root = Path(work_root) if work_root else Path.cwd()
    candidate = root / p
    if candidate.exists():
        return candidate
    return p.resolve() if p.exists() else candidate


def resolve_routed_gds(
    design_name: str,
    work_root: WorkRoot = None,
    artifacts: dict[str, str] | None = None,
) -> Path:
    """Return the routed GDS file, preferring uncompressed but accepting .gz."""
    artifacts = artifacts or {}
    for key in ("routed_gds", "routed_gds_gz"):
        if key in artifacts:
            p = resolve_artifact_path(artifacts[key], work_root)
            if p.exists():
                return p.resolve()
    root = Path(work_root) if work_root else Path.cwd()
    candidates = [
        root / "finish" / "out" / f"{design_name}.gds",
        root / "finish" / "out" / f"{design_name}.gds.gz",
        root / "out" / f"{design_name}.gds",
        root / "out" / f"{design_name}.gds.gz",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def resolve_routed_netlist(
    design_name: str,
    work_root: WorkRoot = None,
    artifacts: dict[str, str] | None = None,
) -> Path:
    """Return the routed Verilog netlist for LVS."""
    artifacts = artifacts or {}
    if "routed_v" in artifacts:
        p = resolve_artifact_path(artifacts["routed_v"], work_root)
        if p.exists():
            return p.resolve()
    root = Path(work_root) if work_root else Path.cwd()
    candidates = [
        root / "finish" / "out" / f"{design_name}.v",
        root / "route_opt" / "out" / f"{design_name}_routed.v",
        root / "out" / f"{design_name}_routed.v",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def resolve_routed_def(
    design_name: str,
    work_root: WorkRoot = None,
    artifacts: dict[str, str] | None = None,
) -> Path | None:
    """Return the routed DEF file path, if available."""
    artifacts = artifacts or {}
    if "routed_def" in artifacts:
        p = resolve_artifact_path(artifacts["routed_def"], work_root)
        if p.exists():
            return p
    root = Path(work_root) if work_root else Path.cwd()
    candidates = [
        root / "finish" / "out" / f"{design_name}.def",
        root / "out" / f"{design_name}.def",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_syn_verilog(
    design_name: str,
    work_root: WorkRoot = None,
    artifacts: dict[str, str] | None = None,
) -> Path | None:
    """Return the synthesized Verilog netlist, if available."""
    artifacts = artifacts or {}
    for key in ("syn_v", "verilog"):
        if key in artifacts:
            p = resolve_artifact_path(artifacts[key], work_root)
            if p.exists():
                return p.resolve()
    root = Path(work_root) if work_root else Path.cwd()
    candidates = [
        root / "synthesis" / "DC" / "out" / f"{design_name}.v",
        root / "synthesis" / "out" / f"{design_name}.v",
        root / "out" / f"{design_name}.v",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def resolve_sdc_file(
    explicit_sdc: str | None,
    design_name: str,
    work_root: WorkRoot = None,
    artifacts: dict[str, str] | None = None,
) -> Path | None:
    """Return the SDC constraint file to use."""
    if explicit_sdc:
        p = resolve_artifact_path(explicit_sdc, work_root)
        if p.exists():
            return p.resolve()
    artifacts = artifacts or {}
    if "syn_sdc" in artifacts:
        p = resolve_artifact_path(artifacts["syn_sdc"], work_root)
        if p.exists():
            return p.resolve()
    root = Path(work_root) if work_root else Path.cwd()
    candidates = [
        root / "synthesis" / "DC" / "out" / f"{design_name}.sdc",
        root / "synthesis" / "out" / f"{design_name}.sdc",
        root / "out" / f"{design_name}.sdc",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None
