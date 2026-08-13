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
    "si_finfet8_nonplanar_v1",
    "nmos_idvg_idvd_v1",
    "gaa_idvg_idvd_v1",
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


def check_mixed_material_dashboard(dashboard_path: Path) -> list[str]:
    if not dashboard_path.is_file():
        return [f"mixed material dashboard not found: {dashboard_path}"]
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    rows = {
        (row.get("material"), row.get("layer")): row
        for row in dashboard.get("rows", [])
    }
    errors = []
    if not dashboard.get("overall_release_baseline", {}).get("passed"):
        errors.append("mixed material release baseline is not passed")

    response = rows.get(("IGZO/WSe2", "sentaurus_response_replay"))
    if not response or not response.get("passed"):
        errors.append("mixed dashboard response replay row is not passed")
    elif float(response.get("rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard response replay RMSE exceeds 0.25 decade")

    igzo = rows.get(("IGZO", "full_dd_tail_selector"))
    if not igzo or not igzo.get("passed"):
        errors.append("mixed dashboard IGZO full-DD selector row is not passed")
    elif int(igzo.get("branches") or 0) < 6:
        errors.append("mixed dashboard IGZO selector has fewer than 6 branches")
    elif float(igzo.get("worst_branch_rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard IGZO selector error exceeds 0.25 decade")

    for key in (
        ("WSe2", "compact_contact_channel_scan"),
        ("WSe2", "wf4p9_vd0p5_notch_recovery"),
    ):
        row = rows.get(key)
        if row is None:
            errors.append(f"mixed dashboard WSe2 diagnostic row missing: {key[1]}")
        elif row.get("passed"):
            errors.append(f"mixed dashboard WSe2 diagnostic unexpectedly passed: {key[1]}")
        elif row.get("status") != "diagnostic_not_full_device_pass":
            errors.append(
                f"mixed dashboard WSe2 diagnostic status changed for {key[1]}: "
                f"{row.get('status')!r}"
            )
    wse2_gap = rows.get(("WSe2", "compact_full_device_gap_audit"))
    if wse2_gap is None:
        errors.append("mixed dashboard WSe2 compact/full-device gap audit row missing")
    elif wse2_gap.get("passed"):
        errors.append("mixed dashboard WSe2 compact/full-device gap audit unexpectedly passed")
    elif wse2_gap.get("status") != "diagnostic_gap_open":
        errors.append(
            "mixed dashboard WSe2 compact/full-device gap audit status changed: "
            f"{wse2_gap.get('status')!r}"
        )
    wse2_two_window = rows.get(("WSe2", "two_window_terminal_fit"))
    if wse2_two_window is None:
        errors.append("mixed dashboard WSe2 two-window diagnostic row missing")
    elif wse2_two_window.get("passed"):
        errors.append("mixed dashboard WSe2 two-window diagnostic unexpectedly passed")
    elif wse2_two_window.get("status") != "diagnostic_not_full_device_pass":
        errors.append(
            "mixed dashboard WSe2 two-window diagnostic status changed: "
            f"{wse2_two_window.get('status')!r}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calibration-root",
        type=Path,
        help="Repository root containing bench/calibration/manifest.json",
    )
    parser.add_argument(
        "--mixed-material-dashboard",
        type=Path,
        help="Path to tcadcraft_mixed_material_calibration_dashboard.json",
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
    if args.mixed_material_dashboard:
        errors.extend(check_mixed_material_dashboard(args.mixed_material_dashboard.resolve()))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    calibration = "checked" if args.calibration_root else "not requested"
    mixed_dashboard = "checked" if args.mixed_material_dashboard else "not requested"
    print(
        f"PASS: TCADCraft {version} release metadata; "
        f"calibration={calibration}; mixed_dashboard={mixed_dashboard}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
