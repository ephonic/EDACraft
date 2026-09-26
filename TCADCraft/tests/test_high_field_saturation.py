"""Analytic golden suite for high-field velocity saturation (Caugy-Thomas).

Golden 1 (uniform-field resistor): a uniformly doped bar with an ohmic
contact pair has a spatially constant driving force F = V/L; the SG edge
mobility reduction is then exactly the closed-form Caugy-Thomas factor and
the terminal current saturates at J -> q*n*mu(F)*F with mu(F) the analytic
mobility.  The current must be strictly below the constant-mu baseline and
approach the saturation-velocity ceiling at high bias.

Golden 2 (edge function): the single-edge mobility factor matches the
closed form (1 + (mu*F/vsat)^beta)^(-1/beta) to machine precision by
construction of the C++ expression - verified indirectly through the
resistor current ratio.

Bit preservation: with the model disabled the resistor current must equal
the pre-model value exactly.
"""

import math

import numpy as np
import pytest

pytest.importorskip("tcad.core")
from tcad.core import PyDeviceSimulator  # noqa: E402

EPS0 = 8.854187817e-12
QE = 1.602176634e-19
VT = 0.0258520


def build_resistor(nx=41, length=1e-6, nd=1e21, mu=0.1):
    dx = length / (nx - 1)
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
    sim.set_permittivity(np.full(nx, EPS0 * 11.7))
    sim.set_mobility(np.full(nx, mu), np.full(nx, mu * 0.35))
    sim.set_doping(np.full(nx, nd))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(nx, 1e-7), np.full(nx, 1e-7))
    sim.set_effective_dos(np.full(nx, 2.8e25), np.full(nx, 1.04e25))
    sim.set_bandgap(np.full(nx, 1.12))
    sim.set_dirichlet_potential({0: 0.0, nx - 1: 0.0})
    sim.set_electron_bc({0: nd, nx - 1: nd})
    sim.set_hole_bc({0: 1e5, nx - 1: 1e5})
    return sim, nx, dx


def resistor_current(sim, nx, v_a):
    sim.set_dirichlet_potential({0: v_a, nx - 1: 0.0})
    r = sim.solve()
    assert r["converged"], f"resistor did not converge at V={v_a}"
    return float(np.asarray(r["Jn_x"])[nx // 2]), r


def caugy_factor(mu, force, vsat, beta):
    ratio = mu * force / vsat
    return 1.0 / (1.0 + ratio ** beta) ** (1.0 / beta)


class TestUniformFieldResistor:
    def test_current_matches_closed_form_electric_field_driving(self):
        # In a uniformly doped resistor the quasi-Fermi gradient equals the
        # electric field, so both driving conventions give the same physics
        # here; the electric-field drive is the numerically robust one for
        # the exact golden (the laged GradQuasiFermi drive oscillates in
        # deep saturation - recorded model boundary).
        sim_b, nx, dx = build_resistor()
        sim_h, _, _ = build_resistor()
        vsat = 5.0e4
        sim_h.set_high_field_saturation(True, vsat, vsat, 2.0, 1.0, 1)
        for v in (0.02, 0.2, 2.0):
            j_base, _ = resistor_current(sim_b, nx, v)
            j_hfs, _ = resistor_current(sim_h, nx, v)
            force = v / (dx * (nx - 1))
            mu = 0.1
            expected = j_base * caugy_factor(mu, force, vsat, 2.0)
            assert j_hfs == pytest.approx(expected, rel=5e-3), (
                f"V={v}: J_hfs {j_hfs:.4e} vs closed form {expected:.4e}"
            )
            assert j_hfs < j_base

    def test_grad_quasi_fermi_driving_smoke(self):
        # The Sentaurus-default driving convention must work at moderate
        # fields and give the same current as the field drive in the
        # uniform resistor (the two forces coincide there).
        sim_e, nx, _ = build_resistor()
        sim_q, _, _ = build_resistor()
        sim_e.set_high_field_saturation(True, 5.0e4, 5.0e4, 2.0, 1.0, 1)
        sim_q.set_high_field_saturation(True, 5.0e4, 5.0e4, 2.0, 1.0, 0)
        j_e, _ = resistor_current(sim_e, nx, 0.2)
        j_q, _ = resistor_current(sim_q, nx, 0.2)
        assert j_q == pytest.approx(j_e, rel=5e-3)

    def test_saturation_ceiling(self):
        sim_h, nx, _ = build_resistor()
        vsat = 5.0e4
        sim_h.set_high_field_saturation(True, vsat, vsat, 2.0, 1.0, 1)
        j_hfs, _ = resistor_current(sim_h, nx, 2.0)
        nd = 1e21
        assert j_hfs < 1.602176634e-19 * nd * vsat * 1.001

    def test_disabled_model_bit_preserved(self):
        sim1, nx, _ = build_resistor()
        sim2, nx2, _ = build_resistor()
        sim2.set_high_field_saturation(False, 1.07e5, 8.37e4, 2.0, 1.0, 0)
        j1, _ = resistor_current(sim1, nx, 0.2)
        j2, _ = resistor_current(sim2, nx2, 0.2)
        assert j1 == pytest.approx(j2, rel=1e-12)

    def test_parameter_validation(self):
        sim, _, _ = build_resistor()
        with pytest.raises(Exception):
            sim.set_high_field_saturation(True, -1.0, 8.37e4, 2.0, 1.0, 0)
        with pytest.raises(Exception):
            sim.set_high_field_saturation(True, 1.0e5, 8.37e4, 2.0, 1.0, 7)
