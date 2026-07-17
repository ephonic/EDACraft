"""Dirac-Source FET (DSFET) simulation example.

The DSFET uses a graphene source with a low effective density-of-states
(DOS) to exploit the unique DOS(E) ~ |E-E_D| profile of Dirac materials.
This suppresses the high-energy thermal tail of electron injection,
enabling steep subthreshold switching beyond the conventional 60 mV/dec
Boltzmann limit.

This example demonstrates:
  1. Building a DSFET device template
  2. Running a gate-voltage sweep
  3. Extracting transfer characteristics and subthreshold swing
"""

import numpy as np
import matplotlib.pyplot as plt

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def main():
    # Build a Dirac-Source FET
    dev = Device.dirac_source_fet(
        Lg=50e-9,
        Lsd=30e-9,
        t_sheet=10e-9,
        W_sheet=20e-9,
        tox=1.5e-9,
        Vg=0.0,
        Vd=0.1,
    )

    # Generate mesh
    mesh = structured_mesh_from_device(dev, resolution=(20e-9, 10e-9, 10e-9))

    # Gate voltage sweep
    vg_values = np.linspace(0.0, 0.8, 17)
    n_max_list = []
    p_max_list = []

    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()

    for vg in vg_values:
        # Re-apply contacts with updated gate voltage
        for name, (shape, _) in dev.contacts.items():
            voltage = vg if name == "gate" else dev.contacts[name][1]
            sim.set_contact(name, voltage)

        results = sim.run(max_iter=120, tol=1e-8)
        if results["converged"]:
            n_max_list.append(results["n"].max())
            p_max_list.append(results["p"].max())
        else:
            print(f"Warning: Vg={vg:.2f}V did not converge")
            n_max_list.append(np.nan)
            p_max_list.append(np.nan)

    # Compute subthreshold swing (SS) in mV/decade
    n_max_arr = np.array(n_max_list)
    valid = ~np.isnan(n_max_arr) & (n_max_arr > 1e10)
    ss_list = []
    for i in range(1, len(vg_values)):
        if valid[i] and valid[i - 1]:
            dV = (vg_values[i] - vg_values[i - 1]) * 1000  # mV
            dlog = np.log10(n_max_arr[i]) - np.log10(n_max_arr[i - 1])
            if dlog > 0:
                ss_list.append(dV / dlog)

    if ss_list:
        min_ss = min(ss_list)
        print(f"Minimum subthreshold swing: {min_ss:.2f} mV/decade")
    else:
        print("Could not extract subthreshold swing")

    # Plot transfer characteristics
    plt.figure(figsize=(8, 5))
    plt.semilogy(vg_values, n_max_arr, "o-", label="n_max")
    plt.xlabel("Gate Voltage Vg (V)")
    plt.ylabel("Max Electron Concentration (m$^{-3}$)")
    plt.title("Dirac-Source FET Transfer Characteristics")
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("dirac_source_fet_transfer.png", dpi=150)
    print("Saved plot: dirac_source_fet_transfer.png")


if __name__ == "__main__":
    main()
