#!/usr/bin/env python3
"""Fast, dependency-free release metadata and calibration gate checks."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_CALIBRATIONS = {
    "fe_hfo2_hysteresis_v1",
    "si_trap_occupation_v1",
    "gan_schottky_nlm_v1",
    "quantum_confinement_mos_v1",
    "electrothermal_breakdown_v1",
}


def project_version() -> str:
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = text.split("[project]", 1)[1].split("[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if not match:
        raise ValueError("[project].version is missing")
    return match.group(1)


def runtime_version() -> str:
    tree = ast.parse((PROJECT_ROOT / "tcad" / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
                return ast.literal_eval(node.value)
    raise ValueError("tcad.__version__ is missing")


def check_calibrations(calibration_root: Path) -> list[str]:
    manifest_path = calibration_root / "bench" / "calibration" / "manifest.json"
    if not manifest_path.is_file():
        return [f"calibration manifest not found: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in manifest.get("benchmarks", [])}
    errors = []
    for case_id in sorted(REQUIRED_CALIBRATIONS):
        case = cases.get(case_id)
        if case is None:
            errors.append(f"required calibration missing: {case_id}")
        elif case.get("tcadcraft_status") != "passed":
            errors.append(
                f"required calibration {case_id} is {case.get('tcadcraft_status')!r}, expected 'passed'"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calibration-root",
        type=Path,
        help="Repository root containing bench/calibration/manifest.json",
    )
    args = parser.parse_args()

    errors: list[str] = []
    version = project_version()
    runtime = runtime_version()
    if version != runtime:
        errors.append(f"version mismatch: pyproject={version}, runtime={runtime}")

    for relative in ("LICENSE", "README.md", "CHANGELOG.md", "RELEASE_NOTES.md", "MANIFEST.in"):
        if not (PROJECT_ROOT / relative).is_file():
            errors.append(f"required release file missing: {relative}")

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if "yourusername" in pyproject:
        errors.append("pyproject.toml still contains a placeholder project URL")

    headers = list((PROJECT_ROOT / "src").glob("*.h"))
    sources = list((PROJECT_ROOT / "src").glob("*.cpp"))
    if not headers or not sources:
        errors.append("C++ source/header inventory is incomplete")

    if args.calibration_root:
        errors.extend(check_calibrations(args.calibration_root.resolve()))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    calibration = "checked" if args.calibration_root else "not requested"
    print(f"PASS: TCADCraft {version} release metadata; calibration={calibration}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
