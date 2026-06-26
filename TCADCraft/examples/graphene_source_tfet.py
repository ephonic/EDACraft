"""Graphene-Source TFET (GS-TFET) simulation.

Novel device combining two steep-slope mechanisms:
1. BTBT tunneling — quantum tunneling from source VB to channel CB
2. Cold-source effect — graphene DOS(E)~|E-E_D| suppresses thermal tail

Compares three devices at a scale where the solver converges:
- Si-TFET: standard tunnel FET (p+ Si source)
- DSFET: Dirac-source FET (graphene cold-source, thermionic)
- GS-TFET: graphene-source TFET (cold-source + BTBT-capable structure)

All simulated with identical geometry and bias for fair comparison.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


# ---------------------------------------------------------------------------
# Configuration — 1um scale (solver convergence verified)
# ---------------------------------------------------------------------------
# Device geometry (micron-scale for solver stability)
LG = 1.0e-6
LSD = 0.5e-6
T_SHEET = 0.5e-6
W_SHEET = 0.5e-6
TOX = 1.5e-9
T_GATE = 10e-9

# Doping
SRC_DOPING = 1e19   # cm^-3
CHN_DOPING = 1e15
DRN_DOPING = 1e19

# Bias
VD = 0.1
VG_SWEEP = np.linspace(0.0, 0.8, 9)

# Solver
RESOLUTION = (100e-9, 100e-9, 100e-9)
TEMPERATURE = 300.0
MAX_ITER = 80
TOL = 1e-8


def build_simulator(device: Device, btbt: bool = False, use_nonlocal: bool = True) -> Simulator:
    mesh = structured_mesh_from_device(device, resolution=RESOLUTION)
    sim = Simulator(mesh, temperature=TEMPERATURE)
    sim.set_material_from_mesh()
    if btbt:
        sim.set_btbt(enabled=True, use_nonlocal=use_nonlocal)
    return sim


def run_sweep(sim: Simulator, device: Device, vg_values: np.ndarray,
              vd: float = VD) -> List[Dict]:
    sim.set_contact("source", 0.0)
    sim.set_contact("drain", vd)

    results = []
    for i, vg in enumerate(vg_values):
        if i == 0:
            sim.set_contact("gate", vg)
        else:
            sim.update_contact("gate", vg)
        r = sim.run(max_iter=MAX_ITER, tol=TOL)
        r["_Vg"] = vg
        results.append(r)
        status = "OK" if r["converged"] else "FAIL"
        n_max = r["n"].max() if r["converged"] else np.nan
        print(f"    Vg={vg:+.2f}V: {status}, n_max={n_max:.3e}")

    return results


def extract_metrics(results: List[Dict], name: str) -> Dict:
    vg_arr = np.array([r["_Vg"] for r in results])
    n_max_arr = np.array([r["n"].max() if r["converged"] else np.nan for r in results])

    ss_values = []
    for i in range(1, len(results)):
        n0, n1 = n_max_arr[i - 1], n_max_arr[i]
        if n0 > 0 and n1 > n0 and not np.isnan(n0) and not np.isnan(n1):
            dV = (vg_arr[i] - vg_arr[i - 1]) * 1000.0
            dlog = np.log10(n1) - np.log10(n0)
            if dlog > 0:
                ss_values.append(dV / dlog)

    min_ss = min(ss_values) if ss_values else float("inf")

    valid = ~np.isnan(n_max_arr) & (n_max_arr > 0)
    if valid.sum() >= 2:
        n_off = n_max_arr[valid][0]
        n_on = n_max_arr[valid][-1]
        i_ratio = n_on / n_off if n_off > 0 else float("inf")
    else:
        i_ratio = 1.0
        n_on = 0.0
        n_off = 0.0

    n_converged = sum(1 for r in results if r["converged"])

    return {
        "name": name,
        "min_SS_mVdec": round(min_ss, 2) if min_ss != float("inf") else "inf",
        "Ion_Ioff": round(i_ratio, 2),
        "n_on": f"{n_on:.3e}" if n_on > 0 else "N/A",
        "n_off": f"{n_off:.3e}" if n_off > 0 else "N/A",
        "converged": f"{n_converged}/{len(results)}",
    }


def main():
    print("=" * 70)
    print("Graphene-Source TFET: Three-Architecture Comparison")
    print("=" * 70)
    print(f"\nGeometry: Lg={LG*1e6:.1f}um, Lsd={LSD*1e6:.1f}um, "
          f"t_sheet={T_SHEET*1e6:.1f}um, W_sheet={W_SHEET*1e6:.1f}um")
    print(f"Bias: Vd={VD}V, Vg sweep 0-{VG_SWEEP[-1]}V")
    print(f"Resolution: {RESOLUTION[0]*1e9:.0f}nm grid")
    print()

    all_results = {}

    # ------------------------------------------------------------------
    # 1. Si-TFET
    # ------------------------------------------------------------------
    print("[1/3] Si-TFET (p+ Si source, DD)")
    print("-" * 40)
    dev = Device.tfet(
        Lg=LG, tox=TOX, t_sheet=T_SHEET, W_sheet=W_SHEET,
        Lsd=LSD, t_gate=T_GATE,
        source_doping=SRC_DOPING, channel_doping=CHN_DOPING,
        drain_doping=DRN_DOPING,
        Vg=0.0, Vd=VD, Vs=0.0,
    )
    sim = build_simulator(dev)
    t0 = time.time()
    res = run_sweep(sim, dev, VG_SWEEP, vd=VD)
    print(f"  Time: {time.time() - t0:.1f}s")
    all_results["Si-TFET"] = res

    # ------------------------------------------------------------------
    # 2. DSFET (thermionic, no BTBT)
    # ------------------------------------------------------------------
    print("\n[2/3] DSFET (graphene cold-source, thermionic)")
    print("-" * 40)
    dev = Device.dirac_source_fet(
        Lg=LG, tox=TOX, t_sheet=T_SHEET, W_sheet=W_SHEET,
        Lsd=LSD, t_gate=T_GATE,
        source_doping=SRC_DOPING, channel_doping=CHN_DOPING,
        drain_doping=DRN_DOPING,
        Vg=0.0, Vd=VD, Vs=0.0,
    )
    sim = build_simulator(dev)
    t0 = time.time()
    res = run_sweep(sim, dev, VG_SWEEP, vd=VD)
    print(f"  Time: {time.time() - t0:.1f}s")
    all_results["DSFET"] = res

    # ------------------------------------------------------------------
    # 3. GS-TFET
    # ------------------------------------------------------------------
    print("\n[3/3] GS-TFET (graphene source + p+ doping, DD)")
    print("-" * 40)
    dev = Device.graphene_source_tfet(
        Lg=LG, tox=TOX, t_sheet=T_SHEET, W_sheet=W_SHEET,
        Lsd=LSD, t_gate=T_GATE,
        source_doping=SRC_DOPING, channel_doping=CHN_DOPING,
        drain_doping=DRN_DOPING,
        Vg=0.0, Vd=VD, Vs=0.0,
    )
    sim = build_simulator(dev)
    t0 = time.time()
    res = run_sweep(sim, dev, VG_SWEEP, vd=VD)
    print(f"  Time: {time.time() - t0:.1f}s")
    all_results["GS-TFET"] = res

    # ------------------------------------------------------------------
    # PHASE 2: BTBT on TFET variants
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 2: BTBT-Enabled")
    print("=" * 70)

    # Si-TFET + BTBT
    print("\n[1/2] Si-TFET + BTBT (non-local WKB)")
    print("-" * 40)
    dev = Device.tfet(
        Lg=LG, Lsd=LSD, t_sheet=T_SHEET, W_sheet=W_SHEET,
        source_doping=SRC_DOPING, channel_doping=CHN_DOPING,
        drain_doping=DRN_DOPING,
        Vg=0.0, Vd=VD, Vs=0.0,
    )
    sim = build_simulator(dev, btbt=True, use_nonlocal=True)
    t0 = time.time()
    res = run_sweep(sim, dev, VG_SWEEP, vd=VD)
    print(f"  Time: {time.time() - t0:.1f}s")
    all_results["Si-TFET (BTBT)"] = res

    # GS-TFET + BTBT
    print("\n[2/2] GS-TFET + BTBT (non-local WKB)")
    print("-" * 40)
    dev = Device.graphene_source_tfet(
        Lg=LG, Lsd=LSD, t_sheet=T_SHEET, W_sheet=W_SHEET,
        source_doping=SRC_DOPING, channel_doping=CHN_DOPING,
        drain_doping=DRN_DOPING,
        Vg=0.0, Vd=VD, Vs=0.0,
    )
    sim = build_simulator(dev, btbt=True, use_nonlocal=True)
    t0 = time.time()
    res = run_sweep(sim, dev, VG_SWEEP, vd=VD)
    print(f"  Time: {time.time() - t0:.1f}s")
    all_results["GS-TFET (BTBT)"] = res

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Comparison Summary")
    print("=" * 70)

    all_metrics = []
    for label, results in all_results.items():
        m = extract_metrics(results, label)
        all_metrics.append(m)
        print(f"\n  {m['name']:<20}  SS={m['min_SS_mVdec']} mV/dec  "
              f"Ion/Ioff={m['Ion_Ioff']:.1e}  "
              f"n_on={m['n_on']}  n_off={m['n_off']}  "
              f"converged={m['converged']}")

    print("\n" + "-" * 70)
    print("Boltzmann limit: 60 mV/dec")
    print("-" * 70)

    output = {
        "geometry": {
            "Lg_um": LG * 1e6, "Lsd_um": LSD * 1e6,
            "t_sheet_um": T_SHEET * 1e6, "W_sheet_um": W_SHEET * 1e6,
        },
        "bias": {"Vd": VD, "Vg_range": [0.0, VG_SWEEP[-1]], "Vg_points": len(VG_SWEEP)},
        "results": {m["name"]: m for m in all_metrics},
    }
    with open("gstfet_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to gstfet_results.json")


if __name__ == "__main__":
    main()
