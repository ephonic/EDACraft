"""CMOS Evolution: Device comparison for future node exploration.

Compares four device architectures using the TCAD simulator:
1. Baseline GAA nanosheet (SiO2 gate oxide)
2. GAA with high-k (HfO2) gate dielectric
3. Junctionless Nanowire FET
4. FeFET (Ferroelectric GAA with HfZrO gate stack)

Each device is simulated with a gate voltage sweep to extract:
- Subthreshold swing (SS)
- On/off current ratio
- Threshold voltage (Vth)
- Estimated energy-delay product
"""

from __future__ import annotations
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from tcad import Device, Simulator
from tcad.solver import SolverType
from tcad.geometry.device_builder import Material
from tcad.postprocess.metrics import (
    extract_transfer_characteristics,
    compute_energy_delay,
    compare_devices,
)


def simulate_single_device(
    device: Device,
    resolution,
    gate_voltages: np.ndarray,
    drain_voltage: float = 0.5,
    btbt: bool = False,
    ferroelectric: bool = False,
    max_iter: int = 50,
    tol: float = 1e-8,
) -> dict:
    """Run a gate voltage sweep on a single device.

    Returns sweep_results list and the Simulator object.
    """
    from tcad.solver.unstructured_simulator import UnstructuredSimulator
    from tcad.mesh.generator import structured_mesh_from_device

    mesh = structured_mesh_from_device(device, resolution=resolution)

    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_quantum(True)
    sim.set_solver_type(SolverType.PETSC, SolverType.PETSC)

    if btbt:
        sim.set_btbt(enabled=True, A_kane=3.1e21, B_kane=2.0e7, D=2)
    if ferroelectric:
        sim.set_ferroelectric(enabled=True, alpha=-1.0e8, beta=1.0e18)

    # Set drain contact
    if "drain" in device.contacts:
        sim.set_contact("drain", drain_voltage)
    if "source" in device.contacts:
        sim.set_contact("source", 0.0)

    # Gate sweep
    sweep_results = []
    prev_solved = False

    for Vg in gate_voltages:
        print(f"  Vg = {Vg:.3f} V", end=" ... ")

        if prev_solved:
            sim.update_contact("gate", Vg)
        else:
            if "gate" in device.contacts:
                sim.set_contact("gate", Vg)

        results = sim.run(max_iter=max_iter, tol=tol)
        prev_solved = True

        if results["converged"]:
            n_max = float(results["n"].max())
            print(f"converged, n_max={n_max:.3e}")
        else:
            print(f"NOT converged")

        sweep_results.append(results)

    return sim, sweep_results


def main():
    print("=" * 70)
    print("CMOS Evolution: Device Architecture Comparison")
    print("=" * 70)

    # Gate sweep parameters
    gate_voltages = np.linspace(0.0, 0.7, 8)
    resolution = (5e-9, 5e-9, 5e-9)  # coarse for quick exploration

    all_metrics = {}

    # ----------------------------------------------------------------
    # 1. Baseline GAA (SiO2)
    # ----------------------------------------------------------------
    print("\n[1/4] Baseline GAA (SiO2 gate oxide)")
    print("-" * 40)
    device_gaa = Device.gaa(
        Lg=15e-9, tox=1.5e-9, t_sheet=5e-9, W_sheet=20e-9,
        Lsd=15e-9, t_gate=10e-9,
        Vg=0.0, Vd=0.5, Vs=0.0,
    )
    sim_gaa, results_gaa = simulate_single_device(
        device_gaa, resolution, gate_voltages,
    )
    metrics_gaa = extract_transfer_characteristics(results_gaa)
    all_metrics["GAA (SiO2)"] = metrics_gaa
    print(f"  SS={metrics_gaa['SS']:.1f} mV/dec, "
          f"Ion/Ioff={metrics_gaa['Ion_Ioff']:.2e}, "
          f"Vth={metrics_gaa['Vth']:.3f} V")

    # ----------------------------------------------------------------
    # 2. GAA with high-k (HfO2)
    # ----------------------------------------------------------------
    print("\n[2/4] GAA with high-k (HfO2, kappa=25)")
    print("-" * 40)
    device_highk = Device.gaa_highk(
        Lg=12e-9, t_ox=1.0e-9, t_sheet=5e-9, W_sheet=20e-9,
        Lsd=15e-9, t_gate=10e-9, kappa=25.0,
        Vg=0.0, Vd=0.5, Vs=0.0,
    )
    sim_highk, results_highk = simulate_single_device(
        device_highk, resolution, gate_voltages,
    )
    metrics_highk = extract_transfer_characteristics(results_highk)
    all_metrics["GAA (HfO2)"] = metrics_highk
    print(f"  SS={metrics_highk['SS']:.1f} mV/dec, "
          f"Ion/Ioff={metrics_highk['Ion_Ioff']:.2e}, "
          f"Vth={metrics_highk['Vth']:.3f} V")

    # ----------------------------------------------------------------
    # 3. Junctionless Nanowire FET
    # ----------------------------------------------------------------
    print("\n[3/4] Junctionless Nanowire FET")
    print("-" * 40)
    device_jl = Device.junctionless_fet(
        Lg=12e-9, tox=1.5e-9, t_wire=5e-9, W_wire=5e-9,
        Lsd=12e-9, t_gate=10e-9,
        doping=1e19,
        Vg=0.0, Vd=0.5, Vs=0.0,
    )
    sim_jl, results_jl = simulate_single_device(
        device_jl, resolution, gate_voltages,
        btbt=True,  # Enable BTBT for junctionless
    )
    metrics_jl = extract_transfer_characteristics(results_jl)
    all_metrics["Junctionless FET"] = metrics_jl
    print(f"  SS={metrics_jl['SS']:.1f} mV/dec, "
          f"Ion/Ioff={metrics_jl['Ion_Ioff']:.2e}, "
          f"Vth={metrics_jl['Vth']:.3f} V")

    # ----------------------------------------------------------------
    # 4. FeFET (Ferroelectric GAA)
    # ----------------------------------------------------------------
    print("\n[4/4] FeFET (HfZrO ferroelectric gate stack)")
    print("-" * 40)
    device_fefet = Device.gaa_fefet(
        Lg=12e-9, t_fe=5e-9, t_ox=1.0e-9, t_sheet=5e-9,
        W_sheet=20e-9, Lsd=15e-9, t_gate=10e-9,
        Vg=0.0, Vd=0.5, Vs=0.0,
    )
    sim_fefet, results_fefet = simulate_single_device(
        device_fefet, resolution, gate_voltages,
        ferroelectric=True,
    )
    metrics_fefet = extract_transfer_characteristics(results_fefet)
    all_metrics["FeFET (HfZrO)"] = metrics_fefet
    print(f"  SS={metrics_fefet['SS']:.1f} mV/dec, "
          f"Ion/Ioff={metrics_fefet['Ion_Ioff']:.2e}, "
          f"Vth={metrics_fefet['Vth']:.3f} V")

    # ----------------------------------------------------------------
    # Comparison table
    # ----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Device Comparison Summary")
    print("=" * 70)
    print(compare_devices(all_metrics))

    # Energy-delay estimates
    print("\nEnergy-Delay Estimates (Vdd=0.7V)")
    print("-" * 50)
    for name, m in all_metrics.items():
        Cox_baseline = 8.854e-12 * 3.9 / 1.5e-9  # SiO2, 1.5nm
        if "HfO2" in name:
            Cox_baseline = 8.854e-12 * 25.0 / 1.0e-9
        elif "FeFET" in name:
            Cox_baseline = 8.854e-12 * 35.0 / 6.0e-9  # series FE + SiO2
        elif "Junctionless" in name:
            Cox_baseline = 8.854e-12 * 3.9 / 1.5e-9

        ed = compute_energy_delay(
            Vdd=0.7, Cox=Cox_baseline,
            W=20e-9, L=12e-9,
            Ion=m["Ion"], Ioff=m["Ioff"],
        )
        print(f"  {name:<20} E={ed['E_switch']:.3e} J  "
              f"tau={ed['tau_delay']:.3e} s  "
              f"EDP={ed['EDP']:.3e} J*s")

    print("\nDone. CMOS evolution exploration complete.")


if __name__ == "__main__":
    main()
