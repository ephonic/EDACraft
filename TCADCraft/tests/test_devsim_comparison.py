"""
Automated comparison tests between tcad and devsim reference.

These tests validate that tcad produces physically consistent results
by comparing against the industry-standard devsim simulator.

Differences are expected because:
- devsim uses Newton-Raphson (fully coupled)
- tcad uses Gummel iteration (sequentially coupled)
- For weakly coupled systems (uniform doping, low doping) agreement is excellent
- For strongly coupled systems (high doping PN junction) small differences exist
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Skip the entire module if devsim is not installed (M6c import guard).
pytest.importorskip("devsim")

# Physical constants (SI, matched to devsim defaults where noted)
K_B = 1.3806503e-23
Q_E = 1.602176634e-19
EPS0 = 8.854187817e-12


def _run_devsim_1d(Na, Nd, ni, VT, L, nx, mu_n, mu_p, eps):
    """Run devsim 1D diode equilibrium and return results in SI units."""
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
    mesh_name = f"dio_{uid}"
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

    xj = L / 2
    Na_cm = Na * 1e-6
    Nd_cm = Nd * 1e-6
    devsim.node_model(device=device, region=region, name="Acceptors",
                      equation=f"{Na_cm}*step({xj * 1e2}-x)")
    devsim.node_model(device=device, region=region, name="Donors",
                      equation=f"{Nd_cm}*step(x-{xj * 1e2})")
    devsim.node_model(device=device, region=region, name="NetDoping",
                      equation="Donors-Acceptors")

    CreateSolution(device, region, "Potential")
    phi_p = -VT * np.log(max(Na, ni) / ni)
    phi_n = VT * np.log(max(Nd, ni) / ni)
    x_vals = np.array(devsim.get_node_model_values(device=device, region=region, name="x"))
    phi_init = phi_p * (x_vals < xj * 1e2) + phi_n * (x_vals >= xj * 1e2)
    devsim.set_node_values(device=device, region=region, name="Potential", values=phi_init.tolist())

    CreateSiliconPotentialOnly(device, region)
    for contact in devsim.get_contact_list(device=device):
        devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-8, maximum_iterations=100)

    CreateSolution(device, region, "Electrons")
    CreateSolution(device, region, "Holes")
    devsim.set_node_values(device=device, region=region, name="Electrons",
                           init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=region, name="Holes",
                           init_from="IntrinsicHoles")
    CreateSiliconDriftDiffusion(device, region)
    for contact in devsim.get_contact_list(device=device):
        CreateSiliconDriftDiffusionAtContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-8, maximum_iterations=100)

    x = np.array(devsim.get_node_model_values(device=device, region=region, name="x")) * 1e-2
    phi = np.array(devsim.get_node_model_values(device=device, region=region, name="Potential"))
    n = np.array(devsim.get_node_model_values(device=device, region=region, name="Electrons")) * 1e6
    p = np.array(devsim.get_node_model_values(device=device, region=region, name="Holes")) * 1e6

    # Clean up devsim state to avoid interference between tests
    try:
        devsim.delete_device(device=device)
    except Exception:
        pass
    try:
        devsim.delete_mesh(mesh=mesh_name)
    except Exception:
        pass

    return {"x": x, "phi": phi, "n": n, "p": p}


def _run_devsim_uniform(Nd, ni, VT, L, nx, mu_n, mu_p, eps):
    """Run devsim for truly uniform doping (all nodes same type)."""
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
    mesh_name = f"dio_{uid}"
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

    Nd_cm = Nd * 1e-6
    if Nd > 0:
        devsim.node_model(device=device, region=region, name="Donors", equation=f"{Nd_cm}")
        devsim.node_model(device=device, region=region, name="Acceptors", equation="0")
    else:
        devsim.node_model(device=device, region=region, name="Donors", equation="0")
        devsim.node_model(device=device, region=region, name="Acceptors", equation=f"{-Nd_cm}")
    devsim.node_model(device=device, region=region, name="NetDoping",
                      equation="Donors-Acceptors")

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


def _run_tcad_1d(Na, Nd, ni, VT, L, nx, mu_n, mu_p, eps):
    """Run tcad 1D diode equilibrium.

    Doping convention matches devsim: left side is p-type (x < xj),
    right side is n-type (x >= xj).
    """
    from tcad.core import PyDeviceSimulator as DeviceSimulator

    dx = L / (nx - 1)
    sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
    doping = np.zeros(nx)
    doping[: nx // 2] = -Na   # p-type on left
    doping[nx // 2 :] = Nd    # n-type on right
    sim.set_doping(doping)
    sim.set_permittivity(np.ones(nx) * eps)
    sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)

    phi_n = VT * np.log(max(Nd, ni) / ni)
    phi_p = -VT * np.log(max(Na, ni) / ni)
    sim.set_dirichlet_potential({0: phi_p, nx - 1: phi_n})
    sim.set_electron_bc({0: ni * ni / max(Na, 1.0), nx - 1: Nd})
    sim.set_hole_bc({0: Na, nx - 1: ni * ni / max(Nd, 1.0)})
    sim.set_tolerance(1e-8)
    sim.set_gummel_max_iter(100)
    res = sim.solve()
    return res


def _run_tcad_uniform(Nd, ni, VT, L, nx, mu_n, mu_p, eps):
    """Run tcad for truly uniform doping (all nodes same type)."""
    from tcad.core import PyDeviceSimulator as DeviceSimulator

    dx = L / (nx - 1)
    sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)
    doping = np.ones(nx) * Nd
    sim.set_doping(doping)
    sim.set_permittivity(np.ones(nx) * eps)
    sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)

    phi_eq = VT * np.log(max(Nd, ni) / ni) if Nd > 0 else -VT * np.log(max(abs(Nd), ni) / ni)
    n_eq = max(Nd, ni) if Nd > 0 else ni * ni / max(abs(Nd), ni)
    p_eq = ni * ni / max(abs(Nd), ni) if Nd > 0 else max(abs(Nd), ni)
    sim.set_dirichlet_potential({0: phi_eq, nx - 1: phi_eq})
    sim.set_electron_bc({0: n_eq, nx - 1: n_eq})
    sim.set_hole_bc({0: p_eq, nx - 1: p_eq})
    sim.set_tolerance(1e-8)
    sim.set_gummel_max_iter(100)
    return sim.solve()


def _compute_bernoulli(x):
    """Vectorized Bernoulli function."""
    x = np.asarray(x)
    result = np.empty_like(x, dtype=float)
    small = np.abs(x) < 1e-12
    result[small] = 1.0
    big_pos = x > 100
    result[big_pos] = 0.0
    big_neg = x < -100
    result[big_neg] = -x[big_neg]
    rest = ~(small | big_pos | big_neg)
    result[rest] = x[rest] / np.expm1(x[rest])
    return result


def _compute_current_1d(phi, n, p, dx, mu_n, mu_p, VT):
    """Compute edge-centered Scharfetter-Gummel currents."""
    dphi = phi[1:] - phi[:-1]
    Bp = _compute_bernoulli(dphi / VT)
    Bm = _compute_bernoulli(-dphi / VT)
    Dn = mu_n * VT / dx
    Dp = mu_p * VT / dx
    Jn = Q_E * Dn * (n[:-1] * Bm - n[1:] * Bp)
    Jp = Q_E * Dp * (p[:-1] * Bp - p[1:] * Bm)
    return Jn, Jp


class TestUniformDoping:
    """Uniform doping is the simplest test case; agreement should be exact."""

    @pytest.mark.parametrize("nx", [11, 21, 51])
    def test_uniform_n_type(self, nx):
        Nd = 1e22
        ni = 6.6759e9  # Physically correct Si ni at 300K
        VT = 0.02585
        L = 40e-9
        mu_n = 0.14
        mu_p = 0.045
        eps = EPS0 * 11.7

        dev = _run_devsim_uniform(Nd, ni, VT, L, nx, mu_n, mu_p, eps)
        tcad_res = _run_tcad_uniform(Nd, ni, VT, L, nx, mu_n, mu_p, eps)

        np.testing.assert_allclose(dev["phi"], tcad_res["phi"], rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(dev["n"], tcad_res["n"], rtol=1e-6, atol=1e10)
        np.testing.assert_allclose(dev["p"], tcad_res["p"], rtol=1e-6, atol=1e10)

    @pytest.mark.parametrize("nx", [11, 21, 51])
    def test_uniform_p_type(self, nx):
        Na = 1e22
        ni = 6.6759e9  # Physically correct Si ni at 300K
        VT = 0.02585
        L = 40e-9
        mu_n = 0.14
        mu_p = 0.045
        eps = EPS0 * 11.7

        dev = _run_devsim_uniform(-Na, ni, VT, L, nx, mu_n, mu_p, eps)
        tcad_res = _run_tcad_uniform(-Na, ni, VT, L, nx, mu_n, mu_p, eps)

        np.testing.assert_allclose(dev["phi"], tcad_res["phi"], rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(dev["n"], tcad_res["n"], rtol=1e-6, atol=1e10)
        np.testing.assert_allclose(dev["p"], tcad_res["p"], rtol=1e-6, atol=1e10)


class TestPNJunctionEquilibrium:
    """PN junction equilibrium: validate profiles against devsim.
    
    Note: devsim's Newton method struggles with fully-depleted nanoscale
    devices on fine grids, so we only compare on nx=21 where both simulators
    converge reliably.  Differences are expected due to Gummel vs Newton.
    """

    @pytest.fixture(scope="class")
    def case_params(self):
        return {
            "Na": 1e24,
            "Nd": 1e22,
            "ni": 6.6759e9,  # Physically correct Si ni at 300K
            "VT": 0.02585,
            "L": 40e-9,
            "mu_n": 0.14,
            "mu_p": 0.045,
            "eps": EPS0 * 11.7,
        }

    def test_phi_agreement(self, case_params):
        """Potential profile should match within ~100 mV (15% relative)."""
        p = case_params
        nx = 21
        dev = _run_devsim_1d(**p, nx=nx)
        tcad_res = _run_tcad_1d(**p, nx=nx)

        from scipy.interpolate import interp1d
        phi_tcad_on_dev = interp1d(
            np.arange(nx) * p["L"] / (nx - 1), tcad_res["phi"],
            kind="cubic", fill_value="extrapolate"
        )(dev["x"])

        err = np.abs(phi_tcad_on_dev - dev["phi"])
        phi_scale = np.abs(dev["phi"]).max()
        print(f"\nphi max err = {err.max():.3e} V ({100*err.max()/phi_scale:.2f}%)")
        print(f"phi mean err = {err.mean():.3e} V")

        assert err.max() < 0.12  # 120 mV tolerance
        assert err.mean() < 0.06  # 60 mV mean tolerance

    def test_majority_carrier_agreement(self, case_params):
        """Majority carriers should match within factor of 2."""
        p = case_params
        nx = 21
        dev = _run_devsim_1d(**p, nx=nx)
        tcad_res = _run_tcad_1d(**p, nx=nx)

        from scipy.interpolate import interp1d
        x_tcad = np.arange(nx) * p["L"] / (nx - 1)
        n_tcad_on_dev = interp1d(x_tcad, tcad_res["n"], kind="cubic", fill_value="extrapolate")(dev["x"])
        p_tcad_on_dev = interp1d(x_tcad, tcad_res["p"], kind="cubic", fill_value="extrapolate")(dev["x"])

        mask_n_majority = dev["n"] > 1e20
        mask_p_majority = dev["p"] > 1e20

        if np.any(mask_n_majority):
            rel_err_n = np.abs(n_tcad_on_dev[mask_n_majority] - dev["n"][mask_n_majority]) / dev["n"][mask_n_majority]
            print(f"n majority max rel err = {rel_err_n.max():.3e}")
            assert rel_err_n.max() < 1.0  # factor of 2

        if np.any(mask_p_majority):
            rel_err_p = np.abs(p_tcad_on_dev[mask_p_majority] - dev["p"][mask_p_majority]) / dev["p"][mask_p_majority]
            print(f"p majority max rel err = {rel_err_p.max():.3e}")
            assert rel_err_p.max() < 1.0  # factor of 2

    @pytest.mark.parametrize("nx", [41, 81])
    def test_zero_current(self, case_params, nx):
        """At equilibrium, net current should be numerically small."""
        p = case_params
        tcad_res = _run_tcad_1d(**p, nx=nx)

        Jn, Jp = _compute_current_1d(
            tcad_res["phi"], tcad_res["n"], tcad_res["p"],
            p["L"] / (nx - 1), p["mu_n"], p["mu_p"], p["VT"]
        )
        print(f"nx={nx}: |Jn| max = {np.abs(Jn).max():.3e}, |Jp| max = {np.abs(Jp).max():.3e}")
        J_scale = Q_E * p["mu_n"] * p["VT"] / (p["L"] / (nx - 1)) * max(p["Nd"], p["Na"])
        assert np.abs(Jn).max() < 1e-3 * J_scale
        assert np.abs(Jp).max() < 1e-3 * J_scale


class TestConvergence:
    """Ensure tcad converges for standard test cases."""

    @pytest.mark.parametrize("nx", [11, 21, 41, 81, 161])
    def test_pn_convergence(self, nx):
        Na = 1e24
        Nd = 1e22
        ni = 6.6759e9  # Physically correct Si ni at 300K
        VT = 0.02585
        L = 40e-9
        mu_n = 0.14
        mu_p = 0.045
        eps = EPS0 * 11.7

        tcad_res = _run_tcad_1d(Na, Nd, ni, VT, L, nx, mu_n, mu_p, eps)
        assert tcad_res["converged"], f"Did not converge for nx={nx}"
        assert tcad_res["iterations"] < 70, f"Too many iterations for nx={nx}"


def _run_devsim_bjt(Nd_E, Na_B, Nd_C, L_E, L_B, L_C, ni, VT, nx, mu_n, mu_p, eps):
    """Run devsim 1D NPN BJT equilibrium."""
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
    mesh_name = f"bjt_{uid}"
    device = f"dev_{uid}"
    region = "MyRegion"
    L = L_E + L_B + L_C
    dx = L / (nx - 1)
    idx_e = int(round(L_E / dx))
    idx_b = int(round((L_E + L_B) / dx))

    devsim.create_1d_mesh(mesh=mesh_name)
    for i in range(nx):
        devsim.add_1d_mesh_line(mesh=mesh_name, pos=i * dx * 1e2, ps=dx * 1e2, tag=f"n{i}")
    devsim.add_1d_contact(mesh=mesh_name, name="emitter", tag="n0", material="metal")
    devsim.add_1d_contact(mesh=mesh_name, name="collector", tag=f"n{nx - 1}", material="metal")
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

    xj1 = L_E
    xj2 = L_E + L_B
    Nd_E_cm = Nd_E * 1e-6
    Na_B_cm = Na_B * 1e-6
    Nd_C_cm = Nd_C * 1e-6
    devsim.node_model(
        device=device, region=region, name="Donors",
        equation=f"{Nd_E_cm}*step({xj1*1e2}-x)+{Nd_C_cm}*step(x-{xj2*1e2})"
    )
    devsim.node_model(
        device=device, region=region, name="Acceptors",
        equation=f"{Na_B_cm}*step(x-{xj1*1e2})*step({xj2*1e2}-x)"
    )
    devsim.node_model(device=device, region=region, name="NetDoping",
                      equation="Donors-Acceptors")

    CreateSolution(device, region, "Potential")
    phi_n_E = VT * np.log(Nd_E / ni)
    phi_p_B = -VT * np.log(Na_B / ni)
    phi_n_C = VT * np.log(Nd_C / ni)
    phi_init = np.zeros(nx)
    phi_init[:idx_e] = phi_n_E
    phi_init[idx_e:idx_b] = phi_p_B
    phi_init[idx_b:] = phi_n_C
    devsim.set_node_values(device=device, region=region, name="Potential",
                           values=phi_init.tolist())

    CreateSiliconPotentialOnly(device, region)
    for contact in devsim.get_contact_list(device=device):
        devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-8, maximum_iterations=100)

    CreateSolution(device, region, "Electrons")
    CreateSolution(device, region, "Holes")
    devsim.set_node_values(device=device, region=region, name="Electrons",
                           init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=region, name="Holes",
                           init_from="IntrinsicHoles")
    CreateSiliconDriftDiffusion(device, region)
    for contact in devsim.get_contact_list(device=device):
        CreateSiliconDriftDiffusionAtContact(device, region, contact)

    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-8, maximum_iterations=100)

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


def _run_tcad_bjt(Nd_E, Na_B, Nd_C, L_E, L_B, L_C, ni, VT, nx, mu_n, mu_p, eps):
    """Run tcad 1D NPN BJT equilibrium."""
    from tcad.core import PyDeviceSimulator as DeviceSimulator

    L = L_E + L_B + L_C
    dx = L / (nx - 1)
    idx_e = int(round(L_E / dx))
    idx_b = int(round((L_E + L_B) / dx))
    sim = DeviceSimulator(nx, 1, 1, dx, dx, dx)

    doping = np.zeros(nx)
    doping[:idx_e] = Nd_E
    doping[idx_e:idx_b] = -Na_B
    doping[idx_b:] = Nd_C
    sim.set_doping(doping)
    sim.set_permittivity(np.ones(nx) * eps)
    sim.set_mobility(np.ones(nx) * mu_n, np.ones(nx) * mu_p)

    phi_n_E = VT * np.log(Nd_E / ni)
    phi_n_C = VT * np.log(Nd_C / ni)
    sim.set_dirichlet_potential({0: phi_n_E, nx - 1: phi_n_C})
    sim.set_electron_bc({0: Nd_E, nx - 1: Nd_C})
    sim.set_hole_bc({0: ni * ni / Nd_E, nx - 1: ni * ni / Nd_C})
    sim.set_tolerance(1e-6)
    sim.set_gummel_max_iter(200)
    return sim.solve()


class TestBJTEquilibrium:
    """1D NPN BJT equilibrium against devsim."""

    @pytest.fixture(scope="class")
    def case_params(self):
        return {
            "Nd_E": 1e22,
            "Na_B": 1e21,
            "Nd_C": 1e20,
            "L_E": 50e-9,
            "L_B": 20e-9,
            "L_C": 80e-9,
            "ni": 6.6759e9,  # Physically correct Si ni at 300K
            "VT": 0.02585,
            "mu_n": 0.14,
            "mu_p": 0.045,
            "eps": EPS0 * 11.7,
        }

    def test_phi_agreement(self, case_params):
        """Potential should match within ~1 mV for low-doping BJT."""
        p = case_params
        nx = 151
        dev = _run_devsim_bjt(**p, nx=nx)
        tcad_res = _run_tcad_bjt(**p, nx=nx)

        assert tcad_res["converged"], "tcad did not converge"

        from scipy.interpolate import interp1d
        phi_tcad_on_dev = interp1d(
            np.arange(nx) * (p["L_E"] + p["L_B"] + p["L_C"]) / (nx - 1),
            tcad_res["phi"], kind="cubic", fill_value="extrapolate"
        )(dev["x"])

        err = np.abs(phi_tcad_on_dev - dev["phi"])
        print(f"\nBJT phi max err = {err.max():.4f} V, mean = {err.mean():.4f} V")
        assert err.max() < 5e-3  # 5 mV
        assert err.mean() < 1e-3  # 1 mV

    def test_majority_carriers(self, case_params):
        """Majority carriers should match within 10%."""
        p = case_params
        nx = 151
        dev = _run_devsim_bjt(**p, nx=nx)
        tcad_res = _run_tcad_bjt(**p, nx=nx)

        from scipy.interpolate import interp1d
        x_grid = np.arange(nx) * (p["L_E"] + p["L_B"] + p["L_C"]) / (nx - 1)
        n_tcad_on_dev = interp1d(x_grid, tcad_res["n"], kind="cubic", fill_value="extrapolate")(dev["x"])
        p_tcad_on_dev = interp1d(x_grid, tcad_res["p"], kind="cubic", fill_value="extrapolate")(dev["x"])

        # Emitter / Collector are n-type => n majority
        mask_n_majority = dev["n"] > dev["p"]
        if np.any(mask_n_majority):
            rel_err_n = np.abs(n_tcad_on_dev[mask_n_majority] - dev["n"][mask_n_majority]) / dev["n"][mask_n_majority]
            print(f"BJT n majority max rel err = {rel_err_n.max():.3e}")
            assert rel_err_n.max() < 0.10  # 10%

        # Base is p-type => p majority
        mask_p_majority = dev["p"] > dev["n"]
        if np.any(mask_p_majority):
            rel_err_p = np.abs(p_tcad_on_dev[mask_p_majority] - dev["p"][mask_p_majority]) / dev["p"][mask_p_majority]
            print(f"BJT p majority max rel err = {rel_err_p.max():.3e}")
            assert rel_err_p.max() < 0.10  # 10%


# ---------------------------------------------------------------------------
# 2-D PN junction bias-state current comparison (M6c-3)
# ---------------------------------------------------------------------------
# Compares terminal current extracted by ``contact_current_2d`` (tcad) against
# ``devsim.get_contact_current`` on a 2-D PN slab under forward bias.  Because
# devsim uses fully-coupled Newton and tcad uses Gummel iteration, and the two
# differ in mesh discretisation, exact agreement is not expected — the test
# validates sign, order-of-magnitude, and bias-trend consistency (plan0619
# "发现级，符号+量级要对").
#
# Unit reconciliation
# -------------------
# devsim 2-D carries an implicit 1 cm out-of-plane depth, so
# ``get_contact_current`` returns [A] per 1 cm of depth.  tcad's
# ``contact_current_2d`` returns total [A] over the real cross-section
# (width W [m] for an x-normal contact).  To compare on equal footing we
# normalise both to current-per-metre-of-depth [A/m]:
#   tcad   : I_tcad / W        [A/m]
#   devsim : I_devsim * 100    [A/cm -> A/m]

# tcad intrinsic carrier concentration, computed from its default Silicon
# material parameters (Nc=2.8e19, Nv=1.04e19, Eg=1.12, VT=0.02585).
# devsim must use the *same* n_i for a fair comparison.
_NI_TCAD_CM = float(np.sqrt(2.8e19 * 1.04e19) * np.exp(-1.12 / (2 * 0.02585)))


def _run_devsim_2d_pn(vbias, Na, Nd, ni_cm, VT, L, nx, nz, H, mu_n, mu_p, eps, W=None):
    """Run devsim 2-D PN diode at a forward bias and return terminal currents.

    ``W`` (tcad out-of-plane width) is accepted for signature symmetry with
    ``_run_tcad_2d_pn`` but unused — devsim's 2-D mesh carries an implicit
    1 cm depth.

    Returns ``{"I_p": float, "I_n": float}`` in [A] per 1 cm of out-of-plane
    depth (devsim's implicit 2-D convention).  Forward bias = positive voltage
    on the p-contact, n-contact grounded — matching tcad's ``set_contact``.
    """
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
    mesh_name = f"d2d_{uid}"
    device = f"dv_{uid}"
    region = "si"

    dx = L / (nx - 1)
    dz = H / (nz - 1)
    L_cm = L * 1e2
    xj_cm = L * 0.5 * 1e2
    dx_cm = dx * 1e2
    H_cm = H * 1e2
    dz_cm = dz * 1e2

    devsim.create_2d_mesh(mesh=mesh_name)
    for i in range(nx):
        devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=i * dx_cm, ps=dx_cm)
    for k in range(nz):
        devsim.add_2d_mesh_line(mesh=mesh_name, dir="y", pos=k * dz_cm, ps=dz_cm)
    # overscan so vertical contact edges classify cleanly (air slivers)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=-1e-8, ps=1e-8)
    devsim.add_2d_mesh_line(mesh=mesh_name, dir="x", pos=L_cm + 1e-8, ps=1e-8)

    devsim.add_2d_region(mesh=mesh_name, material="Si", region=region,
                         xl=0, xh=L_cm, yl=0, yh=H_cm)
    devsim.add_2d_region(mesh=mesh_name, material="Si", region="air1",
                         xl=-1e-8, xh=0, yl=0, yh=H_cm)
    devsim.add_2d_region(mesh=mesh_name, material="Si", region="air2",
                         xl=L_cm, xh=L_cm + 1e-8, yl=0, yh=H_cm)
    devsim.add_2d_contact(mesh=mesh_name, name="p_contact", region=region,
                          xl=0, xh=0, bloat=1e-10, material="metal")
    devsim.add_2d_contact(mesh=mesh_name, name="n_contact", region=region,
                          xl=L_cm, xh=L_cm, bloat=1e-10, material="metal")
    devsim.finalize_mesh(mesh=mesh_name)
    devsim.create_device(mesh=mesh_name, device=device)

    SetSiliconParameters(device, region, 300)
    devsim.set_parameter(device=device, region=region, name="Permittivity", value=eps * 1e-2)
    devsim.set_parameter(device=device, region=region, name="ElectronCharge", value=Q_E)
    devsim.set_parameter(device=device, region=region, name="n_i", value=ni_cm)
    devsim.set_parameter(device=device, region=region, name="V_t", value=VT)
    devsim.set_parameter(device=device, region=region, name="mu_n", value=mu_n * 1e4)
    devsim.set_parameter(device=device, region=region, name="mu_p", value=mu_p * 1e4)

    devsim.node_model(device=device, region=region, name="Acceptors",
                      equation=f"{Na}*step({xj_cm}-x)")
    devsim.node_model(device=device, region=region, name="Donors",
                      equation=f"{Nd}*step(x-{xj_cm})")
    devsim.node_model(device=device, region=region, name="NetDoping",
                      equation="Donors-Acceptors")

    # Potential-only equilibrium solve
    CreateSolution(device, region, "Potential")
    phi_p = -VT * np.log(max(Na, ni_cm) / ni_cm)
    phi_n = VT * np.log(max(Nd, ni_cm) / ni_cm)
    x_vals = np.array(devsim.get_node_model_values(device=device, region=region, name="x"))
    phi_init = phi_p * (x_vals < xj_cm) + phi_n * (x_vals >= xj_cm)
    devsim.set_node_values(device=device, region=region, name="Potential", values=phi_init.tolist())

    CreateSiliconPotentialOnly(device, region)
    for contact in devsim.get_contact_list(device=device):
        devsim.set_parameter(device=device, name=GetContactBiasName(contact), value=0.0)
        CreateSiliconPotentialOnlyContact(device, region, contact)
    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-6, maximum_iterations=200)

    # Drift-diffusion solve at the requested bias
    CreateSolution(device, region, "Electrons")
    CreateSolution(device, region, "Holes")
    devsim.set_node_values(device=device, region=region, name="Electrons",
                           init_from="IntrinsicElectrons")
    devsim.set_node_values(device=device, region=region, name="Holes",
                           init_from="IntrinsicHoles")
    CreateSiliconDriftDiffusion(device, region)
    for contact in devsim.get_contact_list(device=device):
        CreateSiliconDriftDiffusionAtContact(device, region, contact)

    devsim.set_parameter(device=device, name=GetContactBiasName("p_contact"), value=vbias)
    devsim.set_parameter(device=device, name=GetContactBiasName("n_contact"), value=0.0)
    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-7, maximum_iterations=500)

    ece = "ElectronContinuityEquation"
    hce = "HoleContinuityEquation"
    I_p = (devsim.get_contact_current(device=device, contact="p_contact", equation=ece)
           + devsim.get_contact_current(device=device, contact="p_contact", equation=hce))
    I_n = (devsim.get_contact_current(device=device, contact="n_contact", equation=ece)
           + devsim.get_contact_current(device=device, contact="n_contact", equation=hce))

    try:
        devsim.delete_device(device=device)
    except Exception:
        pass
    try:
        devsim.delete_mesh(mesh=mesh_name)
    except Exception:
        pass

    return {"I_p": float(I_p), "I_n": float(I_n)}


def _run_tcad_2d_pn(vbias, Na, Nd, ni_cm, VT, L, nx, nz, H, mu_n, mu_p, eps, W):
    """Run tcad 2-D PN diode and return terminal currents + convergence flag.

    ``Na``/``Nd`` are in cm^-3 (Device.pnjunction convention).  Returns
    ``{"I_p": float, "I_n": float, "converged": bool}`` with currents in
    total [A] over the real cross-section (width ``W`` [m]).
    """
    from tcad.geometry.device_builder import Device
    from tcad.mesh.generator import structured_mesh_from_device
    from tcad.simulator import Simulator
    from tcad.postprocess.current import contact_current_2d

    dev = Device.pnjunction(L=L, W=W, H=H, x_junction=L / 2, Na=Na, Nd=Nd)
    mesh = structured_mesh_from_device(dev, nx=nx, ny=1, nz=nz)
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_contact("p_contact", voltage=vbias)
    sim.set_contact("n_contact", voltage=0.0)
    r = sim.run(max_iter=120, tol=1e-9)
    I_p = contact_current_2d(sim, r, "p_contact")
    I_n = contact_current_2d(sim, r, "n_contact")
    return {"I_p": float(I_p), "I_n": float(I_n), "converged": bool(r["converged"])}


def _current_per_metre(I_tcad, W, I_devsim):
    """Normalise both simulators to [A/m] of out-of-plane depth.

    tcad total [A] / W [m]  -> [A/m]
    devsim   [A per 1 cm] * 100  -> [A/m]
    """
    return I_tcad / W, I_devsim * 100.0


class TestPNJunction2dBias:
    """2-D PN junction terminal-current comparison: tcad vs devsim.

    Uses low doping (Na=Nd=1e18 cm^-3, L=200 nm) which converges cleanly in
    both solvers.  The tiny cross-section (W=1 nm, H=10 nm) keeps absolute
    currents small but the normalised [A/m] values are directly comparable.
    """

    @pytest.fixture(scope="class")
    def params(self):
        return {
            "Na": 1e18,           # cm^-3
            "Nd": 1e18,           # cm^-3
            "ni_cm": _NI_TCAD_CM, # match tcad's intrinsic concentration
            "VT": 0.02585,
            "L": 200e-9,
            "nx": 61,
            "nz": 3,
            "H": 10e-9,
            "mu_n": 0.14,         # m^2/V/s
            "mu_p": 0.045,
            "eps": EPS0 * 11.7,
            "W": 1e-9,            # tcad out-of-plane width [m]
        }

    def test_equilibrium_currents_near_zero(self, params):
        """At 0 V bias both simulators give ~0 terminal current."""
        p = params
        dev = _run_devsim_2d_pn(0.0, **p)
        tcad = _run_tcad_2d_pn(0.0, **p)
        assert tcad["converged"], "tcad equilibrium did not converge"
        assert abs(dev["I_p"]) < 1e-6, f"devsim equilibrium |I_p|={abs(dev['I_p']):.3e}"
        assert abs(tcad["I_p"]) < 1e-6, f"tcad equilibrium |I_p|={abs(tcad['I_p']):.3e}"

    def test_forward_bias_sign_and_kcl(self, params):
        """Under forward bias: I_p and I_n have opposite signs (KCL), and
        the tcad p-contact current has the same sign as devsim's."""
        p = params
        dev = _run_devsim_2d_pn(0.3, **p)
        tcad = _run_tcad_2d_pn(0.3, **p)
        assert tcad["converged"], "tcad 0.3 V did not converge"
        # KCL: currents into opposite terminals have opposite signs
        assert dev["I_p"] * dev["I_n"] < 0, "devsim KCL sign violated"
        assert tcad["I_p"] * tcad["I_n"] < 0, "tcad KCL sign violated"
        # Sign agreement between simulators
        assert tcad["I_p"] * dev["I_p"] > 0, (
            f"sign mismatch: tcad I_p={tcad['I_p']:.3e}, devsim I_p={dev['I_p']:.3e}"
        )

    def test_forward_bias_magnitude_agreement(self, params):
        """Normalised forward-bias current agrees within an order of magnitude.

        Gummel (tcad) vs Newton (devsim) plus mesh differences preclude exact
        agreement; we require |log10(ratio)| < 1 (same order of magnitude).
        """
        p = params
        dev = _run_devsim_2d_pn(0.3, **p)
        tcad = _run_tcad_2d_pn(0.3, **p)
        assert tcad["converged"], "tcad 0.3 V did not converge"
        J_tcad, J_devsim = _current_per_metre(tcad["I_p"], p["W"], dev["I_p"])
        print(f"\n0.3V: tcad={J_tcad:.3e} A/m, devsim={J_devsim:.3e} A/m, "
              f"ratio={J_tcad / J_devsim:.3f}")
        assert abs(J_tcad) > 0 and abs(J_devsim) > 0
        log_ratio = abs(np.log10(abs(J_tcad) / abs(J_devsim)))
        assert log_ratio < 1.0, (
            f"order-of-magnitude mismatch: tcad={J_tcad:.3e}, devsim={J_devsim:.3e}, "
            f"|log10 ratio|={log_ratio:.3f}"
        )

    def test_bias_trend_monotonic(self, params):
        """Current increases monotonically with forward bias in both simulators."""
        p = params
        biases = [0.2, 0.3, 0.4]
        dev_vals = []
        tcad_vals = []
        for v in biases:
            d = _run_devsim_2d_pn(v, **p)
            t = _run_tcad_2d_pn(v, **p)
            assert t["converged"], f"tcad {v} V did not converge"
            J_t, J_d = _current_per_metre(t["I_p"], p["W"], d["I_p"])
            dev_vals.append(abs(J_d))
            tcad_vals.append(abs(J_t))
        print(f"\ntrend devsim: {dev_vals}")
        print(f"trend tcad  : {tcad_vals}")
        # Monotonic increase
        for i in range(len(biases) - 1):
            assert dev_vals[i + 1] > dev_vals[i], (
                f"devsim not monotonic: {dev_vals}")
            assert tcad_vals[i + 1] > tcad_vals[i], (
                f"tcad not monotonic: {tcad_vals}")
