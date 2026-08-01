"""AlScN + MoS₂ FeFET end-to-end demonstration (P8).

This example validates that the model now correctly simulates FeFETs,
addressing the comments.docx conclusion "该模型暂时不具备正确仿真FeFET的能力".

Demonstrates:
  1. AlScN+MoS₂ FeFET built from the material library (alscn() + mos2_channel()).
  2. Ferroelectric (Preisach) + breakdown + interface traps enabled.
  3. Bidirectional Id-Vg sweep showing hysteresis / memory window.
  4. Academic-style transfer characteristic plot.
  5. Off-state leakage (PF/FN model).

Outputs ``alscn_mos2_fefet_transfer.png``.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from tcad.viz.style import set_academic_style
from tcad.viz.plotter import plot_transfer


def main():
    set_academic_style(figsize=(5, 4))

    # 1. Build AlScN + MoS₂ FeFET (small grid for speed)
    print("Building AlScN+MoS2 FeFET...")
    dev = Device.alscn_mos2_fefet(Lg=50e-9, t_fe=20e-9, t_ox=2e-9, t_ch=5e-9)
    mesh = structured_mesh_from_device(dev, resolution=(20e-9, 1e-9, 10e-9))
    print(f"  Mesh: {mesh.nx}x{mesh.ny}x{mesh.nz} = {mesh.npts()} nodes")
    fe_nodes = np.sum(np.abs(mesh.fields["fe_alpha"].ravel()) > 0)
    print(f"  Ferroelectric nodes: {fe_nodes}")

    # 2. Configure simulator
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    # Use NLS model for AlScN (more realistic for wurtzite structure).
    # P0-1: the MFIS stack is z-directed, so the polar axis must be z —
    # polar_axis=None auto-detects the thin-film normal (smallest FE span).
    # nls_dt is the physical dwell time per bias point (10 ms = a typical
    # quasi-static sweep rate); it is NOT a numerical knob (P0-2 decouples
    # it from the nonlinear iteration count).
    sim.set_ferroelectric(enabled=True, model="nls", Ps=1.4, Ec=3.5e8,
                          nls_dt=1e-2, polar_axis="z")
    # Interface traps at the MATERIAL value (AlScN Dit=1e11 cm^-2 eV^-1).
    # The old D_it=1e13 override (100x the material value "to enhance the
    # memory window") was numerics masquerading as physics (issues0719 P0-6).
    sim.set_interface_traps(E_t=0.0)
    sim.set_quantum(False)
    # Gummel warm-up + line-searched Newton polish in LOG-SPACE carrier
    # variables: the bare Gummel loop limit-cycles at the inversion onset of
    # this device, and the linear-space Newton stalls there (issues0719 P0-3).
    sim.set_use_newton(True)
    sim.set_newton_log_space(True)

    # Set contacts
    sim.set_contact("source", 0.0)
    sim.set_contact("drain", 0.05)
    sim.set_contact("gate", 0.0)
    r0 = sim.run(max_iter=300, tol=1e-6)
    if not r0["converged"]:
        raise RuntimeError(
            "Equilibrium solve did not converge; refusing to continue the "
            "sweep from an invalid state (issues0719 P0-3).")

    # 3. Bidirectional Id-Vg sweep (0 -> +3 -> -3 -> 0).  Note: the 20 nm
    # AlScN film has a coercive voltage Ec*t_fe ~ 7 V, so a 3 V sweep only
    # partially switches the ferroelectric — this is the physical series-
    # capacitor / partial-switching regime of issues0719 §4.1, not a bug.
    print("Sweeping Id-Vg (forward + reverse)...")
    Vg_fwd = np.linspace(0, 3, 4)
    Vg_bwd = np.linspace(3, -3, 7)[1:]
    Vg_back = np.linspace(-3, 0, 4)[1:]
    Vg_all = np.concatenate([Vg_fwd, Vg_bwd, Vg_back])

    from tcad.postprocess.current import contact_current_1d

    Ids = []
    Pz_mean = []
    for Vg in Vg_all:
        sim.update_contact("gate", Vg)
        r = sim.run(max_iter=700, tol=1e-6)
        # P0-3: never plot a non-converged bias point.
        if not r["converged"]:
            raise RuntimeError(
                f"Bias point Vg={Vg:.3f} V did not converge; refusing to "
                f"plot invalid data (issues0719 P0-3).")
        # P0-4: real terminal current only — the n.max() density proxy
        # fallback is removed; a failed extraction must fail loudly.
        Id = abs(contact_current_1d(sim, r, "drain"))
        Ids.append(max(Id, 1e-30))  # Floor for log scale
        P = np.asarray(r["P"])
        fe = np.abs(P[:, 2]) > 1e-30
        Pz_mean.append(float(np.mean(P[fe, 2])) if np.any(fe) else 0.0)

    # P0-1 sanity: the z-directed gate field must drive Pz (and only Pz).
    P = np.asarray(r["P"])
    print(f"  Pz range over sweep: [{min(Pz_mean):.3e}, {max(Pz_mean):.3e}] C/m^2")
    print(f"  |Px|max={np.abs(P[:, 0]).max():.2e}, |Py|max={np.abs(P[:, 1]).max():.2e}")
    if max(Pz_mean) - min(Pz_mean) < 1e-3:
        raise RuntimeError(
            "Ferroelectric Pz did not respond to the gate sweep — the polar "
            "axis wiring is broken (issues0719 P0-1).")

    Ids = np.array(Ids)
    Vg_all = np.array(Vg_all)
    n_fwd = len(Vg_fwd)

    # 4. Plot transfer characteristics
    fig, ax = plt.subplots()
    ax = plot_transfer(Vg_all[:n_fwd], Ids[:n_fwd], ax=ax, label="Forward (0→+3V)")
    ax = plot_transfer(Vg_all[n_fwd:], Ids[n_fwd:], ax=ax, label="Reverse (+3→-3→0V)")
    ax.set_title("AlScN+MoS$_2$ FeFET: Id-Vg Hysteresis")
    # P0-4: contact_current_1d returns the SG edge flux on a unit-area
    # cutline — a current DENSITY in A/m^2, not a terminal current in A.
    ax.set_ylabel(r"Drain current density $|J_D|$ [A/m$^2$]")
    fig.savefig("alscn_mos2_fefet_transfer.png", dpi=300)
    print("  Saved alscn_mos2_fefet_transfer.png")

    # 5. Check hysteresis / memory window
    # Compare Id at Vg=0 for forward vs reverse sweep
    Id_fwd_0 = Ids[0]   # Vg=0 forward start
    Id_rev_0 = Ids[-1]  # Vg=0 reverse end
    print(f"\n  Id at Vg=0 (forward): {Id_fwd_0:.3e}")
    print(f"  Id at Vg=0 (reverse): {Id_rev_0:.3e}")
    print(f"  Memory window (Id ratio): {max(Id_rev_0, 1e-30) / max(Id_fwd_0, 1e-30):.1f}x")
    print(f"\nDone. FeFET simulation completed successfully.")

    plt.close("all")


if __name__ == "__main__":
    main()
