#!/usr/bin/env python3
"""Fast, dependency-free release metadata and calibration gate checks."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(str(__file__).replace("\\", "/")).resolve().parent.parent
REQUIRED_CALIBRATIONS = {
    "fe_hfo2_hysteresis_v1",
    "si_trap_occupation_v1",
    "gan_schottky_nlm_v1",
    "quantum_confinement_mos_v1",
    "quantum_confinement_mos_thickness_v1",
    "si_finfet8_nonplanar_v1",
    "nmos_idvg_idvd_v1",
    "gaa_idvg_idvd_v1",
    "electrothermal_breakdown_v1",
    "dielectric_leakage_pf_fn_v1",
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
    manifest_gate = calibration_root / "bench" / "tools" / "check_calibration_manifest.py"
    if not manifest_gate.is_file():
        errors.append(f"calibration manifest gate not found: {manifest_gate}")
    else:
        completed = subprocess.run(
            [sys.executable, str(manifest_gate), "--root", str(calibration_root)],
            cwd=calibration_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            output = "\n".join(
                line
                for line in (completed.stdout + completed.stderr).splitlines()
                if line.strip()
            )
            errors.append(f"calibration manifest gate failed:\n{output}")
    device_family_gate = calibration_root / "bench" / "tools" / "check_device_family_support.py"
    if not device_family_gate.is_file():
        errors.append(f"device-family calibration gate not found: {device_family_gate}")
    else:
        completed = subprocess.run(
            [
                sys.executable,
                str(device_family_gate),
                "--run-replays",
                "--require-replay-metrics",
            ],
            cwd=calibration_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            output = "\n".join(
                line
                for line in (completed.stdout + completed.stderr).splitlines()
                if line.strip()
            )
            errors.append(f"device-family calibration gate failed:\n{output}")
    device_family_compare_gate = (
        calibration_root / "bench" / "tools" / "verify_device_family_compare_gates.py"
    )
    if not device_family_compare_gate.is_file():
        errors.append(
            f"device-family comparison verifier not found: {device_family_compare_gate}"
        )
    else:
        completed = subprocess.run(
            [sys.executable, str(device_family_compare_gate)],
            cwd=calibration_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            output = "\n".join(
                line
                for line in (completed.stdout + completed.stderr).splitlines()
                if line.strip()
            )
            errors.append(f"device-family comparison verifier failed:\n{output}")
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

    wse2_compact = rows.get(("WSe2", "compact_contact_channel_scan"))
    wse2_branch_selector = rows.get(("WSe2", "compact_branch_selector"))
    if wse2_branch_selector is None:
        errors.append("mixed dashboard WSe2 compact branch-selector row missing")
    elif wse2_branch_selector.get("passed"):
        errors.append("mixed dashboard WSe2 compact branch-selector unexpectedly passed")
    elif wse2_branch_selector.get("status") != "compact_branch_selector_gap_open":
        errors.append(
            "mixed dashboard WSe2 compact branch-selector status changed: "
            f"{wse2_branch_selector.get('status')!r}"
        )
    elif wse2_compact is not None and (
        float(wse2_branch_selector.get("rmse_log_current_decades", 99.0))
        >= float(wse2_compact.get("rmse_log_current_decades", -1.0))
    ):
        errors.append("mixed dashboard WSe2 compact branch-selector does not improve global RMSE")
    elif wse2_compact is not None and (
        float(wse2_branch_selector.get("worst_branch_rmse_log_current_decades", 99.0))
        >= float(wse2_compact.get("worst_branch_rmse_log_current_decades", -1.0))
    ):
        errors.append("mixed dashboard WSe2 compact branch-selector does not improve worst-branch RMSE")

    wse2_compact_surrogate = rows.get(("WSe2", "compact_profile_surrogate"))
    if wse2_compact_surrogate is None:
        errors.append("mixed dashboard WSe2 compact/profile surrogate row missing")
    elif not wse2_compact_surrogate.get("passed"):
        errors.append("mixed dashboard WSe2 compact/profile surrogate is not passed")
    elif wse2_compact_surrogate.get("status") != "deck_local_surrogate_pass":
        errors.append(
            "mixed dashboard WSe2 compact/profile surrogate status changed: "
            f"{wse2_compact_surrogate.get('status')!r}"
        )
    elif float(wse2_compact_surrogate.get("rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 compact/profile surrogate exceeds global RMSE gate")
    elif float(wse2_compact_surrogate.get("worst_branch_rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 compact/profile surrogate exceeds worst-branch RMSE gate")

    wse2_profile_decomposition = rows.get(("WSe2", "contact_profile_decomposition"))
    if wse2_profile_decomposition is None:
        errors.append("mixed dashboard WSe2 contact/profile decomposition row missing")
    elif wse2_profile_decomposition.get("passed"):
        errors.append("mixed dashboard WSe2 contact/profile decomposition unexpectedly passed")
    elif wse2_profile_decomposition.get("status") != "profile_transport_decomposition_gap_open":
        errors.append(
            "mixed dashboard WSe2 contact/profile decomposition status changed: "
            f"{wse2_profile_decomposition.get('status')!r}"
        )
    elif int(wse2_profile_decomposition.get("branches") or 0) < 18:
        errors.append("mixed dashboard WSe2 contact/profile decomposition has incomplete branch coverage")
    elif float(wse2_profile_decomposition.get("rmse_log_current_decades", 0.0)) <= 0.25:
        errors.append("mixed dashboard WSe2 contact/profile decomposition no longer reports selector gap")
    elif float(wse2_profile_decomposition.get("worst_branch_rmse_log_current_decades", 0.0)) <= 2.0:
        errors.append("mixed dashboard WSe2 contact/profile decomposition no longer reports severe LUT correction")

    for key in (("WSe2", "wf4p9_vd0p5_notch_recovery"),):
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
    if wse2_compact is None:
        errors.append("mixed dashboard WSe2 diagnostic row missing: compact_contact_channel_scan")
    elif wse2_compact.get("passed"):
        errors.append("mixed dashboard WSe2 diagnostic unexpectedly passed: compact_contact_channel_scan")
    elif wse2_compact.get("status") != "diagnostic_not_full_device_pass":
        errors.append(
            "mixed dashboard WSe2 diagnostic status changed for compact_contact_channel_scan: "
            f"{wse2_compact.get('status')!r}"
        )
    wse2_gap = rows.get(("WSe2", "compact_full_device_gap_audit"))
    if wse2_gap is None:
        errors.append("mixed dashboard WSe2 compact/full-device gap audit row missing")
    elif wse2_gap.get("passed"):
        errors.append("mixed dashboard WSe2 legacy compact/full-device gap audit unexpectedly passed")
    elif wse2_gap.get("status") != "diagnostic_not_full_device_pass":
        errors.append(
            "mixed dashboard WSe2 legacy compact/full-device gap audit status changed: "
            f"{wse2_gap.get('status')!r}"
        )
    wse2_profile_gap = rows.get(("WSe2", "profile_constrained_gap_audit"))
    if wse2_profile_gap is None:
        errors.append("mixed dashboard WSe2 profile-constrained gap audit row missing")
    elif not wse2_profile_gap.get("passed"):
        errors.append("mixed dashboard WSe2 profile-constrained gap audit is not passed")
    elif wse2_profile_gap.get("status") != "closed":
        errors.append(
            "mixed dashboard WSe2 profile-constrained gap audit status is not closed: "
            f"{wse2_profile_gap.get('status')!r}"
        )
    elif float(wse2_profile_gap.get("rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 profile-constrained gap audit exceeds global RMSE gate")
    elif float(wse2_profile_gap.get("worst_branch_rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 profile-constrained gap audit exceeds worst-branch RMSE gate")
    wse2_two_window = rows.get(("WSe2", "two_window_terminal_fit"))
    if wse2_two_window is None:
        errors.append("mixed dashboard WSe2 two-window row missing")
    elif not wse2_two_window.get("passed"):
        errors.append("mixed dashboard WSe2 two-window row is not passed")
    elif wse2_two_window.get("status") != "passed":
        errors.append(
            "mixed dashboard WSe2 two-window passed row has non-passed status: "
            f"{wse2_two_window.get('status')!r}"
        )
    elif float(wse2_two_window.get("rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 two-window row exceeds global RMSE gate")
    elif float(wse2_two_window.get("worst_branch_rmse_log_current_decades", 99.0)) > 0.25:
        errors.append("mixed dashboard WSe2 two-window row exceeds worst-branch RMSE gate")
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
