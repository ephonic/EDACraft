"""AlScN/MoS2 FeFET multi-level-cell program/read example.

This example exercises the robust MLC helper added for AlScN partial switching:
each reset, program, and read transition is advanced with bounded
quasistationary voltage steps, and the reported current window is a positive
state separation with an explicit polarity diagnostic.

Outputs ``alscn_mlc_programming.png``.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.postprocess.current import contact_current_1d
from tcad.postprocess.fe_loops import run_mlc_program_read_sweep
from tcad.simulator import Simulator


def build_simulator(t_fe=20e-9):
    dev = Device.alscn_mos2_fefet(
        Lg=50e-9, t_fe=t_fe, t_ox=2e-9, t_ch=5e-9,
    )
    mesh = structured_mesh_from_device(dev, resolution=(20e-9, 1e-9, 10e-9))
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.set_ferroelectric(
        enabled=True, model="nls", Ps=1.4, Ec=3.5e8,
        nls_dt=1.0e-3, polar_axis="z",
    )
    sim.set_interface_traps(E_t=0.0)
    sim.set_quantum(False)
    sim.set_use_newton(True)
    sim.set_newton_log_space(True)
    sim.set_contact("source", 0.0)
    sim.set_contact("drain", 0.05)
    sim.set_contact("gate", 0.0)
    result = sim.run(max_iter=300, tol=1e-6)
    if not result["converged"]:
        raise RuntimeError("initial equilibrium solve did not converge")
    return sim


def main():
    t_fe = 20e-9
    sim = build_simulator(t_fe=t_fe)
    vc = 3.5e8 * t_fe
    # Keep the default example as a quick smoke run.  Full MLC exploration can
    # raise this to e.g. ``np.linspace(0.0, 1.2 * vc, 9)`` and enable
    # ``reset_voltage=-0.8 * vc``; the helper will still ramp those high-field
    # transitions robustly.
    program_voltages = np.array([0.0, 1.0, 2.0])

    def read_current(simulator, result):
        return abs(contact_current_1d(simulator, result, "drain"))

    result = run_mlc_program_read_sweep(
        sim,
        "gate",
        program_voltages=program_voltages,
        read_voltage=0.0,
        reset_voltage=None,
        max_ramp_step=1.0,
        max_iter=300,
        tol=1e-6,
        current_reader=read_current,
        min_state_separation_decades=0.10,
    )

    print(f"MLC states: {result['n_states']}")
    print(f"Window: {result['memory_window_decades']:.3f} decades")
    print(f"Polarity: {result['polarity']} "
          f"(signed={result['signed_window_decades']:.3f} decades)")

    fig, ax1 = plt.subplots(figsize=(5.2, 4.0))
    ax1.semilogy(result["program_voltages"], result["read_currents"], "o-")
    ax1.set_xlabel("Program voltage [V]")
    ax1.set_ylabel(r"Read $|J_D|$ [A/m$^2$]")
    ax1.grid(True, which="both", alpha=0.3)
    ax2 = ax1.twinx()
    if result["read_polarization"].size:
        ax2.plot(result["program_voltages"], result["read_polarization"], "s--",
                 color="tab:orange")
    ax2.set_ylabel(r"Read $P_z$ [C/m$^2$]")
    fig.tight_layout()
    fig.savefig("alscn_mlc_programming.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
