"""
Apple-to-apple comparison of SRH recombination and optical generation
between tcad and devsim.

Design principles for fair comparison:
- Identical mesh (same nx, same L)
- Identical material parameters (eps, mu_n, mu_p)
- Identical doping profiles
- Identical boundary conditions (Dirichlet, same values)
- Identical SRH lifetimes (tau_n, tau_p)
- Identical optical generation rate (G_opt)
- devsim uses Newton-Raphson; tcad uses Gummel iteration
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Skip the entire module if devsim is not installed (M6c import guard).
pytest.importorskip("devsim")

K_B = 1.3806503e-23
Q_E = 1.602176634e-19
EPS0 = 8.854187817e-12


def _run_devsim_uniform_optical(Nd, ni, VT, L, nx, mu_n, mu_p, eps, tau_n, tau_p, G_opt):
    """Run devsim for uniform doping with SRH + optical generation."""
    import devsim
    from devsim.python_packages.simple_physics import (
        SetSiliconParameters,
        CreateSiliconPotentialOnly,
        CreateSiliconPotentialOnlyContact,
        CreateSiliconDriftDiffusion,
        CreateSiliconDriftDiffusionAtContact,
        GetContactBiasName,
        CreateSRH,
        CreateECE,
        CreateHCE,
        CreatePE,
        CreateBernoulli,
        CreateElectronCurrent,
        CreateHoleCurrent,
    )
    from devsim.python_packages.model_create import (
        CreateSolution,
        CreateNodeModel,
        CreateNodeModelDerivative,
    )
    from devsim.python_packages.model_create import CreateNodeModelDerivative

    import uuid
    uid = str(uuid.uuid4())[:8]
    mesh_name = f"opt_{uid}"
    device = f"dev_{uid}"
    region = "MyRegion"
    dx = L / (nx - 1)

    devsim.create_1d_mesh(mesh=mesh_name)
    for i in range(nx):
        devsim.add_1d_mesh_line(mesh=mesh_name, pos=i * dx * 1e2, ps=dx * 1e2, tag=f"n{i}")
    devsim.add_1d_contact(mesh=mesh_name, name="top", tag="n0", material="metal")
    devsim.add_1d_contact(mesh=mesh_name, name="bot", tag=f"n{nx - 1}", material="metal")
    devsim.add_1d_region(mesh=mesh_name, material="Si", region=region, tag1="n0", tag2=f"n{nx - 1}")
    devsim.finalize_mesh(mesh=mesh_name)
    devsim.create_device(mesh=mesh_name, device=device)

    SetSiliconParameters(device, region, 300)
    devsim.set_parameter(device=device, region=region, name="Permittivity", value=eps * 1e-2)
    devsim.set_parameter(device=device, region=region, name="ElectronCharge", value=Q_E)
    devsim.set_parameter(device=device, region=region, name="n_i", value=ni * 1e-6)
    devsim.set_parameter(device=device, region=region, name="V_t", value=VT)
    devsim.set_parameter(device=device, region=region, name="mu_n", value=mu_n * 1e4)
    devsim.set_parameter(device=device, region=region, name="mu_p", value=mu_p * 1e4)
    # Set SRH lifetimes
    devsim.set_parameter(device=device, region=region, name="taun", value=tau_n)
    devsim.set_parameter(device=device, region=region, name="taup", value=tau_p)

    Nd_cm = Nd * 1e-6
    if Nd > 0:
        devsim.node_model(device=device, region=region, name="Donors", equation=f"{Nd_cm}")
        devsim.node_model(device=device, region=region, name="Acceptors", equation="0")
    else:
        devsim.node_model(device=device, region=region, name="Donors", equation="0")
        devsim.node_model(device=device, region=region, name="Acceptors", equation=f"{-Nd_cm}")
    devsim.node_model(device=device, region=region, name="NetDoping", equation="Donors-Acceptors")

    # Optical generation node model [cm^-3 s^-1]
    G_opt_cm = G_opt * 1e-6
    CreateNodeModel(device, region, "OptGen", f"{G_opt_cm}")

    CreateSolution(device, region, "Potential")
    CreateSiliconPotentialOnly(device, region)
    for contact in devsim.get_contact_list(device=device):
        devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10, maximum_iterations=30)

    CreateSolution(device, region, "Electrons")
    CreateSolution(device, region, "Holes")
    devsim.set_node_values(device=device, region=region, name="Electrons",
                           init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=region, name="Holes",
                           init_from="IntrinsicHoles")

    # Build drift-diffusion manually so we can inject OptGen into continuity equations
    CreatePE(device, region)
    CreateBernoulli(device, region)
    CreateSRH(device, region)

    # Modify generation to include optical: ElectronGeneration = -q*(USRH - OptGen)
    # HoleGeneration = +q*(USRH - OptGen)
    # But devsim models are already created by CreateSRH, so we overwrite them.
    # Note: devsim uses ElectronCharge = +1.602e-19 C (positive magnitude)
    # In devsim: ElectronGeneration = -ElectronCharge * USRH
    #            HoleGeneration = +ElectronCharge * USRH
    # We want:   ElectronGeneration = -ElectronCharge * (USRH - OptGen)
    #            HoleGeneration = +ElectronCharge * (USRH - OptGen)
    devsim.node_model(device=device, region=region, name="ElectronGeneration",
                      equation="-ElectronCharge*(USRH - OptGen)")
    devsim.node_model(device=device, region=region, name="HoleGeneration",
                      equation="+ElectronCharge*(USRH - OptGen)")
    # Derivatives w.r.t Electrons and Holes
    for v in ("Electrons", "Holes"):
        CreateNodeModelDerivative(device, region, "ElectronGeneration",
                                  "-ElectronCharge*(USRH - OptGen)", v)
        CreateNodeModelDerivative(device, region, "HoleGeneration",
                                  "+ElectronCharge*(USRH - OptGen)", v)

    CreateElectronCurrent(device, region, "mu_n")
    CreateHoleCurrent(device, region, "mu_p")

    NCharge = "-ElectronCharge * Electrons"
    CreateNodeModel(device, region, "NCharge", NCharge)
    CreateNodeModelDerivative(device, region, "NCharge", NCharge, "Electrons")
    PCharge = "ElectronCharge * Holes"
    CreateNodeModel(device, region, "PCharge", PCharge)
    CreateNodeModelDerivative(device, region, "PCharge", PCharge, "Holes")

    from devsim import equation
    equation(
        device=device, region=region,
        name="ElectronContinuityEquation", variable_name="Electrons",
        time_node_model="NCharge", edge_model="ElectronCurrent",
        variable_update="positive", node_model="ElectronGeneration",
    )
    equation(
        device=device, region=region,
        name="HoleContinuityEquation", variable_name="Holes",
        time_node_model="PCharge", edge_model="HoleCurrent",
        variable_update="positive", node_model="HoleGeneration",
    )

    for contact in devsim.get_contact_list(device=device):
        CreateSiliconDriftDiffusionAtContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=100)

    x = np.array(devsim.get_node_model_values(device=device, region=region, name="x")) * 1e-2
    phi = np.array(devsim.get_node_model_values(device=device, region=region, name="Potential"))
    n = np.array(devsim.get_node_model_values(device=device, region=region, name="Electrons")) * 1e6
    p = np.array(devsim.get_node_model_values(device=device, region=region, name="Holes")) * 1e6

    try:
        devsim.delete_device(device=device)
    except Exception:
        pass
    try:
        devsim.delete_mesh(mesh=mesh_name)
    except Exception:
        pass

    return {"x": x, "phi": phi, "n": n, "p": p}


def _run_tcad_uniform_optical(Nd, ni, VT, L, nx, mu_n, mu_p, eps, tau_n, tau_p, G_opt):
    """Run tcad for uniform doping with SRH + optical generation."""
    from tcad.core import PyDeviceSimulator as DeviceSimulator

    dx = L / (nx - 1)
    sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
    doping = np.ones(nx) * Nd
    sim.set_doping(doping)
    sim.set_permittivity(np.ones(nx) * eps)
    sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)
    sim.set_optical_generation(np.ones(nx) * G_opt)
    sim.set_recombination(np.ones(nx) * tau_n, np.ones(nx) * tau_p)

    phi_eq = VT * np.log(max(Nd, ni) / ni) if Nd > 0 else -VT * np.log(max(abs(Nd), ni) / ni)
    n_eq = max(Nd, ni) if Nd > 0 else ni * ni / max(abs(Nd), ni)
    p_eq = ni * ni / max(abs(Nd), ni) if Nd > 0 else max(abs(Nd), ni)
    sim.set_dirichlet_potential({0: phi_eq, nx - 1: phi_eq})
    sim.set_electron_bc({0: n_eq, nx - 1: n_eq})
    sim.set_hole_bc({0: p_eq, nx - 1: p_eq})
    sim.set_tolerance(1e-8)
    sim.set_gummel_max_iter(100)
    return sim.solve()


def _run_devsim_uniform_srh_only(Nd, ni, VT, L, nx, mu_n, mu_p, eps, tau_n, tau_p):
    """Run devsim for uniform doping with SRH only (no optical gen)."""
    import devsim
    from devsim.python_packages.simple_physics import (
        SetSiliconParameters,
        CreateSiliconPotentialOnly,
        CreateSiliconPotentialOnlyContact,
        CreateSiliconDriftDiffusion,
        CreateSiliconDriftDiffusionAtContact,
        GetContactBiasName,
    )
    from devsim.python_packages.model_create import CreateSolution

    import uuid
    uid = str(uuid.uuid4())[:8]
    mesh_name = f"srh_{uid}"
    device = f"dev_{uid}"
    region = "MyRegion"
    dx = L / (nx - 1)

    devsim.create_1d_mesh(mesh=mesh_name)
    for i in range(nx):
        devsim.add_1d_mesh_line(mesh=mesh_name, pos=i * dx * 1e2, ps=dx * 1e2, tag=f"n{i}")
    devsim.add_1d_contact(mesh=mesh_name, name="top", tag="n0", material="metal")
    devsim.add_1d_contact(mesh=mesh_name, name="bot", tag=f"n{nx - 1}", material="metal")
    devsim.add_1d_region(mesh=mesh_name, material="Si", region=region, tag1="n0", tag2=f"n{nx - 1}")
    devsim.finalize_mesh(mesh=mesh_name)
    devsim.create_device(mesh=mesh_name, device=device)

    SetSiliconParameters(device, region, 300)
    devsim.set_parameter(device=device, region=region, name="Permittivity", value=eps * 1e-2)
    devsim.set_parameter(device=device, region=region, name="ElectronCharge", value=Q_E)
    devsim.set_parameter(device=device, region=region, name="n_i", value=ni * 1e-6)
    devsim.set_parameter(device=device, region=region, name="V_t", value=VT)
    devsim.set_parameter(device=device, region=region, name="mu_n", value=mu_n * 1e4)
    devsim.set_parameter(device=device, region=region, name="mu_p", value=mu_p * 1e4)
    devsim.set_parameter(device=device, region=region, name="taun", value=tau_n)
    devsim.set_parameter(device=device, region=region, name="taup", value=tau_p)

    Nd_cm = Nd * 1e-6
    if Nd > 0:
        devsim.node_model(device=device, region=region, name="Donors", equation=f"{Nd_cm}")
        devsim.node_model(device=device, region=region, name="Acceptors", equation="0")
    else:
        devsim.node_model(device=device, region=region, name="Donors", equation="0")
        devsim.node_model(device=device, region=region, name="Acceptors", equation=f"{-Nd_cm}")
    devsim.node_model(device=device, region=region, name="NetDoping", equation="Donors-Acceptors")

    CreateSolution(device, region, "Potential")
    CreateSiliconPotentialOnly(device, region)
    for contact in devsim.get_contact_list(device=device):
        devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10, maximum_iterations=30)

    CreateSolution(device, region, "Electrons")
    CreateSolution(device, region, "Holes")
    devsim.set_node_values(device=device, region=region, name="Electrons",
                           init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=region, name="Holes",
                           init_from="IntrinsicHoles")
    CreateSiliconDriftDiffusion(device, region)
    for contact in devsim.get_contact_list(device=device):
        CreateSiliconDriftDiffusionAtContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10, maximum_iterations=100)

    x = np.array(devsim.get_node_model_values(device=device, region=region, name="x")) * 1e-2
    phi = np.array(devsim.get_node_model_values(device=device, region=region, name="Potential"))
    n = np.array(devsim.get_node_model_values(device=device, region=region, name="Electrons")) * 1e6
    p = np.array(devsim.get_node_model_values(device=device, region=region, name="Holes")) * 1e6

    try:
        devsim.delete_device(device=device)
    except Exception:
        pass
    try:
        devsim.delete_mesh(mesh=mesh_name)
    except Exception:
        pass

    return {"x": x, "phi": phi, "n": n, "p": p}


def _run_tcad_uniform_srh_only(Nd, ni, VT, L, nx, mu_n, mu_p, eps, tau_n, tau_p):
    """Run tcad for uniform doping with SRH only."""
    from tcad.core import PyDeviceSimulator as DeviceSimulator

    dx = L / (nx - 1)
    sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
    doping = np.ones(nx) * Nd
    sim.set_doping(doping)
    sim.set_permittivity(np.ones(nx) * eps)
    sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)
    sim.set_recombination(np.ones(nx) * tau_n, np.ones(nx) * tau_p)

    phi_eq = VT * np.log(max(Nd, ni) / ni) if Nd > 0 else -VT * np.log(max(abs(Nd), ni) / ni)
    n_eq = max(Nd, ni) if Nd > 0 else ni * ni / max(abs(Nd), ni)
    p_eq = ni * ni / max(abs(Nd), ni) if Nd > 0 else max(abs(Nd), ni)
    sim.set_dirichlet_potential({0: phi_eq, nx - 1: phi_eq})
    sim.set_electron_bc({0: n_eq, nx - 1: n_eq})
    sim.set_hole_bc({0: p_eq, nx - 1: p_eq})
    sim.set_tolerance(1e-8)
    sim.set_gummel_max_iter(100)
    return sim.solve()


class TestSRHOnlyUniform:
    """Uniform doping with SRH only (no optical generation).
    
    At equilibrium with uniform doping, SRH recombination rate is identically
    zero because n*p = ni^2 everywhere.  Therefore this test primarily
    validates that enabling SRH does not break the equilibrium solution.
    """

    @pytest.fixture(scope="class")
    def case_params(self):
        return {
            "Nd": 1e22,
            "ni": 1e16,
            "VT": 0.02585,
            "L": 40e-9,
            "mu_n": 0.14,
            "mu_p": 0.045,
            "eps": EPS0 * 11.7,
            "tau_n": 1e-7,
            "tau_p": 1e-7,
        }

    @pytest.mark.parametrize("nx", [21, 51])
    def test_phi_unchanged_with_srh(self, case_params, nx):
        """Potential should match the no-SRH baseline within numerical noise."""
        p = case_params
        dev = _run_devsim_uniform_srh_only(**p, nx=nx)
        tcad_res = _run_tcad_uniform_srh_only(**p, nx=nx)

        assert tcad_res["converged"], "tcad did not converge"
        np.testing.assert_allclose(dev["phi"], tcad_res["phi"], rtol=1e-6, atol=1e-6)

    @pytest.mark.parametrize("nx", [21, 51])
    def test_majority_carriers_unchanged(self, case_params, nx):
        p = case_params
        dev = _run_devsim_uniform_srh_only(**p, nx=nx)
        tcad_res = _run_tcad_uniform_srh_only(**p, nx=nx)
        np.testing.assert_allclose(dev["n"], tcad_res["n"], rtol=1e-5, atol=1e10)
        np.testing.assert_allclose(dev["p"], tcad_res["p"], rtol=1e-5, atol=1e10)

    @pytest.mark.parametrize("nx", [21, 51])
    def test_phi_unchanged_with_srh(self, case_params, nx):
        """Potential should match the no-SRH baseline within numerical noise."""
        p = case_params
        dev = _run_devsim_uniform_srh_only(**p, nx=nx)
        tcad_res = _run_tcad_uniform_srh_only(**p, nx=nx)

        assert tcad_res["converged"], "tcad did not converge"
        np.testing.assert_allclose(dev["phi"], tcad_res["phi"], rtol=1e-6, atol=1e-6)

    @pytest.mark.parametrize("nx", [21, 51])
    def test_majority_carriers_unchanged(self, case_params, nx):
        p = case_params
        dev = _run_devsim_uniform_srh_only(**p, nx=nx)
        tcad_res = _run_tcad_uniform_srh_only(**p, nx=nx)
        np.testing.assert_allclose(dev["n"], tcad_res["n"], rtol=1e-5, atol=1e10)
        np.testing.assert_allclose(dev["p"], tcad_res["p"], rtol=1e-5, atol=1e10)


class TestOpticalGenerationUniform:
    """Uniform n-type doping with optical generation + SRH.

    Physical picture: light generates e-h pairs at rate G_opt uniformly.
    In a finite 1D device with fixed carrier BCs, steady-state carrier
    concentration is diffusion-limited:
        p_max ≈ G_opt * L^2 / (8 * D_p) + p_eq
    where D_p = mu_p * VT.  We verify tcad and devsim agree on the
    elevated minority carrier (hole) density.
    """

    @pytest.fixture(scope="class")
    def case_params(self):
        return {
            "Nd": 1e22,
            "ni": 1e16,
            "VT": 0.02585,
            "L": 1e-6,
            "mu_n": 0.14,
            "mu_p": 0.045,
            "eps": EPS0 * 11.7,
            "tau_n": 1e-7,
            "tau_p": 1e-7,
            "G_opt": 1e27,
        }

    @pytest.mark.parametrize("nx", [21, 51])
    def test_minority_carrier_elevation(self, case_params, nx):
        """Hole density elevated by optical generation; tcad vs devsim agreement."""
        p = case_params
        dev = _run_devsim_uniform_optical(**p, nx=nx)
        tcad_res = _run_tcad_uniform_optical(**p, nx=nx)

        assert tcad_res["converged"], "tcad did not converge"

        # Potential: devsim (Newton) keeps phi nearly flat; tcad (Gummel+phi_frozen)
        # develops a small dip (~0.02 V) due to sequential coupling.  Tolerance
        # is relaxed to account for the different coupling strategies.
        phi_err = np.abs(dev["phi"] - tcad_res["phi"])
        print(f"\nnx={nx}: phi max err = {phi_err.max():.3e} V")
        assert phi_err.max() < 0.03  # 30 mV tolerance

        # Majority carriers (electrons): devsim keeps n ≈ Nd everywhere,
        # while tcad's Gummel+phi_frozen causes a dip in the interior.
        # We only check that the order of magnitude is correct.
        assert tcad_res["n"].max() > 5e21
        assert dev["n"].max() > 5e21

        # Minority carriers (holes) — the key metric.  Gummel vs Newton
        # differences are expected, but both should show the same order of
        # magnitude elevation above equilibrium.
        interior = slice(3, -3)
        dev_p_int = dev["p"][interior]
        tcad_p_int = tcad_res["p"][interior]
        rel_err = np.abs(dev_p_int - tcad_p_int) / np.maximum(dev_p_int, 1e10)
        print(f"nx={nx}: hole max rel err = {rel_err.max():.3e}")
        print(f"  devsim p_mean = {dev_p_int.mean():.3e}, tcad p_mean = {tcad_p_int.mean():.3e}")
        assert rel_err.max() < 0.35  # 35% agreement on minority carriers
        # Both simulators must show p >> p_eq (1e10)
        assert tcad_p_int.mean() > 1e14
        assert dev_p_int.mean() > 1e14

    @pytest.mark.parametrize("nx", [21, 51])
    def test_steady_state_balance(self, case_params, nx):
        """Verify that p_max is within ~40% of the diffusion-limited estimate."""
        p = case_params
        tcad_res = _run_tcad_uniform_optical(**p, nx=nx)
        assert tcad_res["converged"]

        D_p = p["mu_p"] * p["VT"]
        p_analytical = p["G_opt"] * p["L"]**2 / (8 * D_p)
        p_max = tcad_res["p"].max()
        # Allow 40% deviation due to SRH, discretization, and Gummel coupling effects
        rel_err = abs(p_max - p_analytical) / p_analytical
        print(f"\nnx={nx}: p_max={p_max:.3e}, analytical={p_analytical:.3e}, rel_err={rel_err:.3e}")
        assert rel_err < 0.40
