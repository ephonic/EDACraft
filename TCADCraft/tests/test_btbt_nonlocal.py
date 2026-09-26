"""M2 nonlocal-BTBT analytic golden suite (plan0918 verification protocol).

The C++ nonlocal kernel (``compute_nonlocal_btbt``) linearises the barrier
with the local field and integrates the WKB form over a capped path.  Since
the 2026-09-18 M2 device-level audit the generation uses the Kane-consistent
form

    G(E) = A_si * E^D * exp(-2 * Theta(E, m_t))
    Theta(E, m_t) = (2/3) * sqrt(2 * m_t * m0) * Eg^1.5 / (hbar * q * E)
    A_si = A_kane * 1e6          (cm^-3 -> m^-3, same as the local model)

with ``A_kane``/``D`` taken from ``set_btbt_params`` and the effective mass
ratio ``m_t`` from ``set_btbt_nonlocal_mass`` (default 0.25).  The kernel is
verified against four analytic layers:

1. C++ output vs an exact Python replication of the same discretized formula
   (machine-precision implementation identity),
2. the replication vs the closed form (Simpson discretization error and its
   convergence order on the sqrt-kinked integrand),
3. the local Kane degenerate limit: with ``B = B_eff(m_t) = 2*Theta(E)*E``
   the local and nonlocal models agree at uniform field for any D,
4. the parameter-transfer identity: a local calibration (A, D, B) migrates
   to the nonlocal model via ``m_t = 0.25 * (B / B_eff(0.25))^2`` and
   reproduces the same uniform-field generation.

Path truncation (``tunnel_path_fraction`` and the boundary availability cap)
must inflate the generation monotonically - the barrier is cut before it is
exhausted - and zero field must give exactly zero generation.

The toy slab decouples the kernel from the carrier loop with
``continuity_scale = 0`` and ramps the Dirichlet bias from zero, so the
solved potential is linear to machine precision and the measured field equals
V/L exactly.
"""

import math

import numpy as np
import pytest

pytest.importorskip("tcad.core")
from tcad.core import PyDeviceSimulator  # noqa: E402

EPS0 = 8.854187817e-12
HBAR = 1.054571817e-34
M0 = 9.1093837015e-31
QE = 1.602176634e-19
EG_EV = 1.12
EG_J = EG_EV * QE
#: Default Kane A in the cm^-3 s^-1 convention; A_si = A_CM * 1e6 = 1e27.
A_CM = 1.0e21
A_SI = A_CM * 1.0e6
DEFAULT_MT = 0.25


def theta_closed(field, mt_ratio=DEFAULT_MT):
    mt = mt_ratio * M0
    return (2.0 / 3.0) * math.sqrt(2.0 * mt) * EG_J ** 1.5 / (HBAR * QE * field)


def g_closed(field, mt_ratio=DEFAULT_MT, a_si=A_SI, d_exp=0.0):
    return a_si * field ** d_exp * math.exp(-2.0 * theta_closed(field, mt_ratio))


def b_eff(mt_ratio=DEFAULT_MT):
    """Kane B that makes exp(-B/E) == exp(-2*Theta(E, mt)) for all E."""
    return (4.0 / 3.0) * math.sqrt(2.0 * mt_ratio * M0) * EG_J ** 1.5 / (HBAR * QE)


def mt_from_b(b_kane, mt_ref=DEFAULT_MT):
    """Inverse of b_eff: mass ratio reproducing a local Kane B calibration."""
    return mt_ref * (b_kane / b_eff(mt_ref)) ** 2


def simpson_wkb(field, path_length, npts, mt_ratio=DEFAULT_MT):
    """Exact replication of the C++ Simpson loop for the linearised barrier."""
    mt = mt_ratio * M0
    if npts >= 4 and npts % 2:
        npts += 1
    h = path_length / npts
    total = 0.0
    for s in range(npts + 1):
        x = s * h
        barrier = max(EG_J - QE * field * x, 0.0)
        if barrier <= 0.0:
            continue
        integrand = math.sqrt(2.0 * mt * barrier) / HBAR
        weight = 1.0 if s in (0, npts) else (4.0 if s % 2 else 2.0)
        total += weight * integrand
    return total * h / 3.0


def build_slab(
    v_a=20.0,
    nx=101,
    dx=1.0e-9,
    use_nonlocal=True,
    path_fraction=0.5,
    wkb_npts=64,
    ramp_steps=81,
    a_kane=A_CM,
    d_kane=0.0,
    mt_ratio=DEFAULT_MT,
    b_kane=None,
):
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
    sim.set_permittivity(np.full(nx, EPS0 * 11.7))
    sim.set_mobility(np.full(nx, 1.0e-9), np.full(nx, 1.0e-9))
    sim.set_doping(np.zeros(nx))
    sim.set_thermal_voltage(0.025852)
    sim.set_recombination(np.full(nx, 1.0e-7), np.full(nx, 1.0e-7))
    sim.set_effective_dos(np.full(nx, 1.0e3), np.full(nx, 1.0e3))
    sim.set_bandgap(np.full(nx, EG_EV))
    sim.set_btbt_enabled(True)
    if use_nonlocal:
        sim.set_btbt_params(a_kane, 2.0e9, d_kane)
        sim.set_btbt_use_nonlocal(True)
        sim.set_btbt_nonlocal_params(path_fraction, wkb_npts)
        if hasattr(sim, "set_btbt_nonlocal_mass"):
            sim.set_btbt_nonlocal_mass(mt_ratio)
    else:
        if b_kane is None:
            b_kane = b_eff(mt_ratio)
        sim.set_btbt_params(a_kane, b_kane, d_kane)
        sim.set_btbt_use_nonlocal(False)
    sim.set_btbt_continuity_scale(0.0)
    sim.set_electron_bc({0: 0.0, nx - 1: 0.0})
    sim.set_hole_bc({0: 0.0, nx - 1: 0.0})
    result = None
    for v in np.linspace(0.0, v_a, ramp_steps):
        sim.set_dirichlet_potential({0: float(v), nx - 1: 0.0})
        result = sim.solve()
    return result


class TestUniformFieldSlab:
    def test_solution_is_linear_and_kernel_runs(self):
        nx = 101
        result = build_slab(v_a=20.0, nx=nx)
        assert result["converged"]
        phi = np.asarray(result["phi"])[:nx]
        linear = np.linspace(20.0, 0.0, nx)
        assert np.max(np.abs(phi - linear)) < 1.0e-9
        field = 20.0 / (100.0e-9)
        assert -(phi[51] - phi[49]) / (2.0e-9) == pytest.approx(field, rel=1e-9)
        assert np.all(np.isfinite(np.asarray(result["G_btbt"])[:nx]))


class TestImplementationIdentity:
    def test_cpp_matches_replicated_simpson_machine_precision(self):
        nx, dx = 101, 1.0e-9
        field = 20.0 / (100.0e-9)
        d_min = EG_J / (QE * field)
        path_full = 2.0 * d_min
        for mt in (0.25, 0.15, 0.08):
            result = build_slab(v_a=20.0, nx=nx, dx=dx, wkb_npts=64, mt_ratio=mt)
            G = np.asarray(result["G_btbt"])[:nx]
            domain = (nx - 1) * dx
            for i in (12, 25, 50, 75, 88):
                avail = min(i, nx - 1 - i) * dx
                path = min(path_full, avail, 0.5 * domain)
                expected = (
                    A_SI
                    * field ** 0.0
                    * math.exp(-2.0 * simpson_wkb(field, path, 64, mt))
                )
                assert G[i] == pytest.approx(expected, rel=1e-10)

    def test_cpp_generation_matches_closed_form_at_high_resolution(self):
        field = 20.0 / (100.0e-9)
        result = build_slab(v_a=20.0, wkb_npts=512)
        G = np.asarray(result["G_btbt"])
        closed = g_closed(field)
        for i in (25, 50, 75):
            assert G[i] == pytest.approx(closed, rel=5.0e-3)

    def test_kane_prefactor_and_exponent_enter_the_generation(self):
        field = 20.0 / (100.0e-9)
        result = build_slab(v_a=20.0, a_kane=1.0e20, d_kane=2.0, wkb_npts=256)
        G = np.asarray(result["G_btbt"])
        closed = g_closed(field, a_si=1.0e20 * 1e6, d_exp=2.0)
        assert G[50] == pytest.approx(closed, rel=5.0e-3)


class TestSimpsonConvergence:
    def test_replication_converges_to_closed_form(self):
        field = 20.0 / (100.0e-9)
        d_min = EG_J / (QE * field)
        path = 2.0 * d_min
        errors = []
        for npts in (16, 32, 64, 128):
            theta_num = simpson_wkb(field, path, npts)
            errors.append(abs(theta_num - theta_closed(field)) / theta_closed(field))
        for k in range(len(errors) - 1):
            assert errors[k + 1] < errors[k]
        assert errors[2] / errors[3] >= 1.5
        assert errors[3] < 2.0e-2


class TestPathTruncation:
    def test_path_fraction_cap_truncation_inflates_generation(self):
        field = 20.0 / (100.0e-9)
        closed = g_closed(field)
        full = build_slab(v_a=20.0, wkb_npts=64, path_fraction=0.2)
        truncated = build_slab(v_a=20.0, wkb_npts=64, path_fraction=0.04)
        g_full = np.asarray(full["G_btbt"])[50]
        g_trunc = np.asarray(truncated["G_btbt"])[50]
        assert g_full == pytest.approx(closed, rel=2.0e-2)
        assert g_trunc > 1.5 * closed

    def test_boundary_availability_cap_inflates_generation(self):
        result = build_slab(v_a=20.0, wkb_npts=64)
        G = np.asarray(result["G_btbt"])
        assert G[1] > 100.0 * G[50]

    def test_zero_field_gives_zero_generation(self):
        result = build_slab(v_a=0.0, ramp_steps=3)
        G = np.asarray(result["G_btbt"])
        assert np.all(G == 0.0)


class TestLocalKaneDegenerateLimit:
    def test_local_kane_with_mapped_B_equals_nonlocal_closed_form(self):
        field = 20.0 / (100.0e-9)
        local = build_slab(v_a=20.0, use_nonlocal=False)
        g_local = float(np.asarray(local["G_btbt"])[50])
        assert g_local == pytest.approx(g_closed(field), rel=1.0e-6)
        assert b_eff() == pytest.approx(4.046e9, rel=2.0e-3)

    def test_identity_holds_with_kane_exponent(self):
        field = 20.0 / (100.0e-9)
        local = build_slab(
            v_a=20.0, use_nonlocal=False, a_kane=1.0e20, d_kane=2.0,
        )
        nonlocal_run = build_slab(v_a=20.0, a_kane=1.0e20, d_kane=2.0, wkb_npts=256)
        g_local = float(np.asarray(local["G_btbt"])[50])
        g_nonlocal = float(np.asarray(nonlocal_run["G_btbt"])[50])
        closed = g_closed(field, a_si=1.0e20 * 1e6, d_exp=2.0)
        assert g_local == pytest.approx(closed, rel=1.0e-6)
        assert g_nonlocal == pytest.approx(closed, rel=5.0e-3)


class TestMassTransferIdentity:
    def test_local_calibration_migrates_to_nonlocal_via_mass_mapping(self):
        # The TFET deck's calibrated local Kane B (plan0918 M2) and the mass
        # ratio that must reproduce it in the nonlocal kernel.
        b_calibrated = 2.35e9
        mt_transfer = mt_from_b(b_calibrated)
        assert mt_transfer == pytest.approx(0.0843, rel=2.0e-2)
        field = 20.0 / (100.0e-9)
        local = build_slab(
            v_a=20.0, use_nonlocal=False, a_kane=3.5e21, d_kane=2.0,
            b_kane=b_calibrated,
        )
        nonlocal_run = build_slab(
            v_a=20.0, a_kane=3.5e21, d_kane=2.0, mt_ratio=mt_transfer,
            wkb_npts=256,
        )
        g_local = float(np.asarray(local["G_btbt"])[50])
        g_nonlocal = float(np.asarray(nonlocal_run["G_btbt"])[50])
        expected = 3.5e21 * 1e6 * field ** 2.0 * math.exp(-b_calibrated / field)
        assert g_local == pytest.approx(expected, rel=1.0e-6)
        # The transfer identity: B_eff(mt_transfer) == B_calibrated makes the
        # nonlocal WKB exponent equal the local Kane exponent; only the
        # residual Simpson discretization error remains.
        assert g_nonlocal == pytest.approx(expected, rel=5.0e-3)
        assert b_eff(mt_transfer) == pytest.approx(b_calibrated, rel=1.0e-12)

    def test_mass_ratio_changes_generation_monotonically(self):
        field = 20.0 / (100.0e-9)
        light = build_slab(v_a=20.0, mt_ratio=0.10, wkb_npts=128)
        heavy = build_slab(v_a=20.0, mt_ratio=0.40, wkb_npts=128)
        g_light = float(np.asarray(light["G_btbt"])[50])
        g_heavy = float(np.asarray(heavy["G_btbt"])[50])
        assert g_light > 100.0 * g_heavy
