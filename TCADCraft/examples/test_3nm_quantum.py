"""
Test best DSFET design at 3nm resolution with and without
Density Gradient quantum correction.

Design: Lg=20nm, tox=1.5nm, Ns=1e19, t_sheet=5nm (best from 4nm evolution)
"""

import os
import time
import numpy as np
from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


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


def run_sweep(params, resolution, quantum, label):
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    
    dev = Device.dirac_source_fet(
        Lg=params["Lg"], tox=params["tox"], t_sheet=params["t_sheet"],
        W_sheet=params["W_sheet"], Lsd=params["Lsd"],
        source_doping=params["source_doping"],
        drain_doping=params["drain_doping"],
        channel_doping=params["channel_doping"],
        Vg=0.0, Vd=0.1,
    )
    mesh = structured_mesh_from_device(dev, resolution=resolution)
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_quantum(quantum)
    
    for name, (shape, voltage) in dev.contacts.items():
        if name != "gate":
            sim.set_contact(name, voltage)
    
    x = mesh.X.ravel()
    channel_mask = (x >= params["Lsd"]) & (x <= params["Lsd"] + params["Lg"])
    
    vg_points = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
    results = []
    total_time = 0.0
    
    old_out, old_err = suppress_output()
    try:
        for vg in vg_points:
            t0 = time.time()
            sim.set_contact("gate", vg)
            r = sim.run(max_iter=80, tol=1e-6)
            elapsed = time.time() - t0
            total_time += elapsed
            
            if r["converged"]:
                n_chan = r["n"][channel_mask]
                n_proxy = float(n_chan.mean()) if n_chan.size > 0 else 1e-20
            else:
                n_proxy = 1e-20
            
            status = "OK" if r["converged"] else "FAIL"
            print(f"  Vg={vg:+.2f}V: {status}, n={n_proxy:.3e}, iter={r.get('iterations', 0)}, time={elapsed:.1f}s")
            results.append({"Vg": vg, "n": n_proxy, "converged": r["converged"]})
    finally:
        restore_output(old_out, old_err)
    
    # Compute metrics
    if len(results) >= 2 and results[0]["converged"] and results[-1]["converged"]:
        n0, n1 = results[0]["n"], results[-1]["n"]
        dV = (vg_points[-1] - vg_points[0]) * 1000.0
        dlog = np.log10(n1) - np.log10(n0)
        ss = dV / dlog if dlog > 0 else 999.0
        ratio = n1 / n0
    else:
        ss = 999.0
        ratio = 1.0
    
    # Point-wise SS
    ss_min = 999.0
    print(f"\n  Point-wise SS:")
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["n"] > 0 and r1["n"] > r0["n"]:
            dV = (r1["Vg"] - r0["Vg"]) * 1000.0
            dlog = np.log10(r1["n"]) - np.log10(r0["n"])
            point_ss = dV / dlog if dlog > 0 else 999.0
            ss_min = min(ss_min, point_ss)
            print(f"    {r0['Vg']:+.2f}V -> {r1['Vg']:+.2f}V: SS={point_ss:.1f} mV/dec")
    
    print(f"\n  Summary: SS={ss:.1f} mV/dec, min_point_SS={ss_min:.1f}, Ion/Ioff={ratio:.1f}, total_time={total_time:.1f}s")
    return {"ss": ss, "ss_min": ss_min, "ratio": ratio, "results": results, "time": total_time}


def main():
    params = {
        "Lg": 20e-9, "tox": 1.5e-9, "t_sheet": 5e-9,
        "W_sheet": 20e-9, "Lsd": 20e-9,
        "source_doping": 1e19, "drain_doping": 1e20,
        "channel_doping": 1e16,
    }
    
    print("=" * 60)
    print("DSFET 3nm Resolution + Quantum Correction Test")
    print("=" * 60)
    print(f"Design: Lg={params['Lg']*1e9:.0f}nm, tox={params['tox']*1e9:.1f}nm, "
          f"t_sheet={params['t_sheet']*1e9:.0f}nm, Ns={params['source_doping']:.0e}")
    
    res_3nm = (3e-9, 3e-9, 3e-9)
    
    # Run without quantum
    noq = run_sweep(params, res_3nm, False, "3nm WITHOUT quantum correction")
    
    # Run with quantum
    q = run_sweep(params, res_3nm, True, "3nm WITH quantum correction (Density Gradient)")
    
    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"  Without quantum: SS={noq['ss']:.1f}, min_SS={noq['ss_min']:.1f}, ratio={noq['ratio']:.1f}")
    print(f"  With quantum:    SS={q['ss']:.1f}, min_SS={q['ss_min']:.1f}, ratio={q['ratio']:.1f}")
    if noq['ss'] > 0 and q['ss'] > 0:
        print(f"  SS improvement:  {noq['ss'] / q['ss']:.2f}x")
    
    print("\n  CMOS Boltzmann limit: 60 mV/dec")
    print(f"  3nm without quantum:  {noq['ss']:.1f} mV/dec")
    print(f"  3nm with quantum:     {q['ss']:.1f} mV/dec")


if __name__ == "__main__":
    main()
