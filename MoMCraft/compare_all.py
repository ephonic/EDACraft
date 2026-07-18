"""Dataset-wide routed-line S21 comparison against ADS.

This script follows the routed-net validation path that actually aligned with
ADS:

1. reconstruct each net from DEF centerlines + testcase metadata
2. solve each routed line as a local 2-port stripline problem
3. compare per-line thru S21 against the ADS touchstone
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, "py")

import numpy as np

from routed_case_solver import solve_case_s21


def _env_fixed_step_um():
    raw = os.environ.get("MOM_FIXED_STEP_UM")
    if raw is None:
        return 16.0
    if raw.strip().lower() == "auto":
        return None
    return float(raw)


def _env_use_mag_model():
    return os.environ.get("MOM_MAG_MODEL", "1") != "0"


def _default_cases():
    ads_dir = Path("mom_testcases/ads_touchstone")
    return sorted(path.stem for path in ads_dir.glob("*.s*p"))


def main():
    cases = sys.argv[1:] or _default_cases()
    max_traces = os.environ.get("MOM_MAX_TRACES")
    if max_traces is not None:
        max_traces = int(max_traces)
    use_phase_model = os.environ.get("MOM_PHASE_MODEL", "1") != "0"
    use_mag_model = _env_use_mag_model()

    all_dmag = []
    all_raw_dph = []
    all_dph = []
    solved_cases = 0

    for case_name in cases:
        print(f'\n{"#" * 72}')
        print(f"Case: {case_name}")
        try:
            result = solve_case_s21(
                case_name,
                use_full_route=os.environ.get("MOM_USE_DEF_ROUTE", "0") == "1",
                use_phase_model=use_phase_model,
                use_mag_model=use_mag_model,
                fixed_step_um=_env_fixed_step_um(),
                max_traces=max_traces,
            )
        except FileNotFoundError as exc:
            print(f"Skip {case_name}: {exc}")
            continue

        print(
            f'Freq: {result["freq_hz"] / 1e9:.6f} GHz, '
            f'traces solved {result["solved_count"]}/{result["total_count"]}'
        )
        if result["solved_count"] == 0:
            print("No valid routed traces were solved.")
            continue

        dmag = result["mag_errs"]
        raw_dph = result["raw_phase_errs"]
        dph = result["phase_errs"]
        print(
            f'  |S21| error: mean={dmag.mean():.1f}%  '
            f'median={np.median(dmag):.1f}%  max={dmag.max():.1f}%'
        )
        if result["phase_refs"]:
            print(
                f'  raw phase error: mean={raw_dph.mean():+.1f} deg  '
                f'median={np.median(raw_dph):+.1f} deg  maxabs={np.max(np.abs(raw_dph)):.1f} deg'
            )
            phase_refs = result["phase_refs"]
            if len(phase_refs) == 1:
                ref = next(iter(phase_refs.values()))
                if ref.get("mode") == "fixed":
                    print(
                        "  phase model: "
                        f'fixed port phase {result["port_phase_deg"]:+.2f} deg'
                    )
                else:
                    print(
                        "  phase model: "
                        f'port phase {result["port_phase_deg"]:+.2f} deg from trace {ref["line_index"]}'
                    )
            else:
                fixed_refs = all(ref.get("mode") == "fixed" for ref in phase_refs.values())
                print(
                    "  phase model: "
                    + ("per-layer fixed port phase" if fixed_refs else "per-layer shortest-trace calibration")
                )
                for label, ref in sorted(phase_refs.items()):
                    if ref.get("mode") == "fixed":
                        print(
                            f'    {label}: fixed port phase '
                            f'{result["port_phase_deg_by_group"][label]:+.2f} deg'
                        )
                    else:
                        print(
                            f'    {label}: port phase {result["port_phase_deg_by_group"][label]:+.2f} deg '
                            f'from trace {ref["line_index"]}'
                        )
        phase_label = "corrected phase error" if result["use_phase_model"] else "phase error"
        print(
            f"  {phase_label}: mean={dph.mean():+.1f} deg  "
            f"median={np.median(dph):+.1f} deg  maxabs={np.max(np.abs(dph)):.1f} deg"
        )
        good = int(np.sum(dmag < 15.0))
        print(f"  traces within 15% magnitude error: {good}/{result['solved_count']}")

        all_dmag.append(dmag)
        all_raw_dph.append(raw_dph)
        all_dph.append(dph)
        solved_cases += 1

    if not solved_cases:
        print("\nNo cases were solved.")
        return

    all_dmag = np.concatenate(all_dmag)
    all_raw_dph = np.concatenate(all_raw_dph)
    all_dph = np.concatenate(all_dph)
    print(f'\n{"=" * 72}')
    print(f"OVERALL ({solved_cases} cases, {len(all_dmag)} traces):")
    print(
        f'  |S21| error: mean={all_dmag.mean():.1f}%  '
        f'median={np.median(all_dmag):.1f}%  max={all_dmag.max():.1f}%'
    )
    print(
        f'  raw phase error: mean={all_raw_dph.mean():+.1f} deg  '
        f'median={np.median(all_raw_dph):+.1f} deg  maxabs={np.max(np.abs(all_raw_dph)):.1f} deg'
    )
    overall_phase_label = "corrected phase error" if use_phase_model else "phase error"
    print(
        f"  {overall_phase_label}: mean={all_dph.mean():+.1f} deg  "
        f"median={np.median(all_dph):+.1f} deg  maxabs={np.max(np.abs(all_dph)):.1f} deg"
    )


if __name__ == "__main__":
    main()
