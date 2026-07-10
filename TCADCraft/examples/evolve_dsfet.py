"""
DSFET Evolution via Two-Stage Simulation-Driven Optimization.

Stage 1: Fast screening with 5nm-resolution structured mesh
Stage 2: Fine validation of top candidates with 4nm-resolution mesh

Focused parameter space (convergence-tested):
  Lg=20nm, tox={1.5,2.0}nm, Ns={1e18,1e19}, t_sheet={3,5}nm
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Tuple

import numpy as np

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


RES_COARSE = (5e-9, 5e-9, 5e-9)
RES_FINE = (4e-9, 4e-9, 4e-9)
VD = 0.1
MAX_ITER = 80
TOL = 1e-6
TEMPERATURE = 300.0

VG_EVAL = [0.0, 0.3]
VG_SWEEP = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]


def suppress_output():
    old_stdout = os.dup(1)
    old_stderr = os.dup(2)
    os.dup2(os.open('/dev/null', os.O_WRONLY), 1)
    os.dup2(os.open('/dev/null', os.O_WRONLY), 2)
    return old_stdout, old_stderr


def restore_output(old_stdout, old_stderr):
    os.dup2(old_stdout, 1)
    os.dup2(old_stderr, 2)
    os.close(old_stdout)
    os.close(old_stderr)


def evaluate(params: Dict, vg_values: List[float], resolution: Tuple[float, float, float]) -> Dict:
    t0 = time.time()
    try:
        dev = Device.dirac_source_fet(
            Lg=params["Lg"], tox=params["tox"], t_sheet=params["t_sheet"],
            W_sheet=params["W_sheet"], Lsd=params["Lsd"],
            source_doping=params["source_doping"],
            drain_doping=params["drain_doping"],
            channel_doping=params["channel_doping"],
            Vg=0.0, Vd=VD,
        )
        mesh = structured_mesh_from_device(dev, resolution=resolution)

        sim = Simulator(mesh, temperature=TEMPERATURE)
        sim.set_material_from_mesh()

        for name, (shape, voltage) in dev.contacts.items():
            if name != "gate":
                sim.set_contact(name, voltage)

        x = mesh.X.ravel()
        channel_mask = (x >= params["Lsd"]) & (x <= params["Lsd"] + params["Lg"])

        results = []
        old_out, old_err = suppress_output()
        try:
            for vg in vg_values:
                sim.set_contact("gate", vg)
                r = sim.run(max_iter=MAX_ITER, tol=TOL)
                if r["converged"]:
                    n_chan = r["n"][channel_mask]
                    n_proxy = float(n_chan.mean()) if n_chan.size > 0 else 1e-20
                else:
                    n_proxy = 1e-20
                results.append({"Vg": vg, "converged": r["converged"], "n_proxy": n_proxy})
        finally:
            restore_output(old_out, old_err)

        return {"params": params, "results": results, "time": time.time() - t0}
    except Exception as e:
        return {"params": params, "results": [], "time": time.time() - t0, "error": str(e)}


def compute_metrics(eval_data: Dict) -> Dict:
    params = eval_data["params"]
    results = eval_data["results"]

    if len(results) < 2:
        return {"fitness": 1e9, "ss_proxy": 999.0, "i_ratio": 1.0, "n_on": 1e-20}

    n_sub = results[0]["n_proxy"]
    n_on = results[-1]["n_proxy"]

    if n_sub > 0 and n_on > n_sub:
        dV = (results[-1]["Vg"] - results[0]["Vg"]) * 1000.0
        dlog = np.log10(n_on) - np.log10(n_sub)
        ss_proxy = dV / dlog if dlog > 0 else 999.0
        i_ratio = n_on / n_sub
    else:
        ss_proxy = 999.0
        i_ratio = 1.0

    fitness = ss_proxy
    if i_ratio < 10:
        fitness += 1000.0
    if ss_proxy > 300:
        fitness += 500.0
    if ss_proxy < 10:
        fitness += 1000.0

    return {"fitness": fitness, "ss_proxy": ss_proxy, "i_ratio": i_ratio, "n_on": n_on}


def main():
    print("=" * 70)
    print("DSFET Two-Stage Evolution (5nm screen -> 4nm validate)")
    print("=" * 70)

    # Stage 1: coarse screening
    print("\n[Stage 1] Coarse screening at 5nm resolution")
    configs = [
        (20e-9, 1.5e-9, 1e18, 3e-9),
        (20e-9, 1.5e-9, 1e18, 5e-9),
        (20e-9, 1.5e-9, 1e19, 3e-9),
        (20e-9, 1.5e-9, 1e19, 5e-9),
        (20e-9, 2.0e-9, 1e18, 3e-9),
        (20e-9, 2.0e-9, 1e18, 5e-9),
        (20e-9, 2.0e-9, 1e19, 3e-9),
        (20e-9, 2.0e-9, 1e19, 5e-9),
    ]

    candidates = []
    for i, (Lg, tox, Ns, t_sheet) in enumerate(configs, 1):
        params = {
            "Lg": Lg, "tox": tox, "t_sheet": t_sheet,
            "W_sheet": 20e-9, "Lsd": 20e-9,
            "source_doping": Ns, "drain_doping": 1e20,
            "channel_doping": 1e16,
        }
        print(f"  [{i}/{len(configs)}] Lg={Lg*1e9:.0f}nm tox={tox*1e9:.1f}nm "
              f"Ns={Ns:.0e} t_sheet={t_sheet*1e9:.0f}nm ...", end=" ", flush=True)
        eval_data = evaluate(params, VG_EVAL, RES_COARSE)
        metrics = compute_metrics(eval_data)
        print(f"fit={metrics['fitness']:.1f} SS={metrics['ss_proxy']:.1f} "
              f"Ion/Ioff={metrics['i_ratio']:.1f} ({eval_data['time']:.1f}s)")
        candidates.append({"params": params, "metrics": metrics})

    candidates.sort(key=lambda x: x["metrics"]["fitness"])
    coarse_best = candidates[0]

    # Stage 2: fine validation of top 3
    print("\n[Stage 2] Fine validation at 4nm resolution (top 3)")
    fine_results = []
    for rank, cand in enumerate(candidates[:3], 1):
        params = cand["params"]
        print(f"  [{rank}/3] ...", end=" ", flush=True)
        eval_data = evaluate(params, VG_EVAL, RES_FINE)
        metrics = compute_metrics(eval_data)
        print(f"fit={metrics['fitness']:.1f} SS={metrics['ss_proxy']:.1f} "
              f"Ion/Ioff={metrics['i_ratio']:.1f} ({eval_data['time']:.1f}s)")
        fine_results.append({"params": params, "metrics": metrics, "eval": eval_data})

    fine_results.sort(key=lambda x: x["metrics"]["fitness"])
    best = fine_results[0]

    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    p = coarse_best["params"]
    m = coarse_best["metrics"]
    print(f"\nCoarse best (5nm): fit={m['fitness']:.1f} SS={m['ss_proxy']:.1f} "
          f"Ion/Ioff={m['i_ratio']:.1f}")
    print(f"  Lg={p['Lg']*1e9:.0f}nm tox={p['tox']*1e9:.1f}nm Ns={p['source_doping']:.0e} "
          f"t_sheet={p['t_sheet']*1e9:.0f}nm")
    p = best["params"]
    m = best["metrics"]
    print(f"\nFine best (4nm):   fit={m['fitness']:.1f} SS={m['ss_proxy']:.1f} "
          f"Ion/Ioff={m['i_ratio']:.1f}")
    print(f"  Lg={p['Lg']*1e9:.0f}nm tox={p['tox']*1e9:.1f}nm Ns={p['source_doping']:.0e} "
          f"t_sheet={p['t_sheet']*1e9:.0f}nm")

    # Detailed sweep
    print("\n[Stage 3] Detailed Vg sweep of fine-best")
    sweep = evaluate(best["params"], VG_SWEEP, RES_FINE)
    for r in sweep["results"]:
        status = "OK" if r["converged"] else "FAIL"
        print(f"  Vg={r['Vg']:+.2f}V: {status}, n={r['n_proxy']:.3e}")

    print("\n  Point-wise SS:")
    ss_min = 999.0
    for i in range(1, len(sweep["results"])):
        r0, r1 = sweep["results"][i-1], sweep["results"][i]
        if r0["n_proxy"] > 0 and r1["n_proxy"] > r0["n_proxy"]:
            dV = (r1["Vg"] - r0["Vg"]) * 1000.0
            dlog = np.log10(r1["n_proxy"]) - np.log10(r0["n_proxy"])
            ss = dV / dlog if dlog > 0 else 999.0
            ss_min = min(ss_min, ss)
            print(f"    {r0['Vg']:+.2f}V -> {r1['Vg']:+.2f}V: SS={ss:.1f} mV/dec")
    print(f"\n  Minimum point SS = {ss_min:.1f} mV/dec")

    print("\n  CMOS Boltzmann limit: 60 mV/dec")
    print(f"  Fine-best DSFET:      {best['metrics']['ss_proxy']:.1f} mV/dec")
    print(f"  Improvement (coarse->fine): {coarse_best['metrics']['ss_proxy'] / best['metrics']['ss_proxy']:.2f}x")

    output = {
        "coarse_best": {"params": coarse_best["params"], "metrics": coarse_best["metrics"]},
        "fine_best": {"params": best["params"], "metrics": best["metrics"], "sweep": sweep["results"]},
    }
    with open("dsfet_evolution_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("\nResults saved to dsfet_evolution_results.json")


if __name__ == "__main__":
    main()
