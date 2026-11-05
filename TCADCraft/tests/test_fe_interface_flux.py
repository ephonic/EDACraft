"""Gauss-law limits for FE/linear-dielectric stacks on stretched meshes."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator

EPS0 = 8.854187817e-12


@pytest.mark.parametrize("charge", [-1e3, 1e3])
@pytest.mark.parametrize("newton", [False, True])
def test_signed_bulk_trap_charge_matches_parabolic_poisson_limit(charge, newton):
    size, dx, eps = 9, 1e-8, EPS0*20
    sim = PyDeviceSimulator(size, 1, 1, dx, 1., 1.)
    sim.set_permittivity(np.full(size, eps))
    sim.set_mobility(np.zeros(size), np.zeros(size))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.full(size, 6.))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_dirichlet_potential({0: 0., size-1: 0.})
    sim.set_electron_bc({0: 0., size-1: 0.})
    sim.set_hole_bc({0: 0., size-1: 0.})
    sim.set_initial_guess(np.zeros(size), np.zeros(size), np.zeros(size))
    sim.set_oxide_traps(np.full(size, charge))
    sim.set_use_newton(newton)
    sim.set_newton_primary(newton)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    state = sim.solve()
    assert state["converged"]
    x = np.arange(size)*dx
    expected = charge*x*(x[-1]-x)/(2*eps)
    np.testing.assert_allclose(state["phi"], expected, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("positions", [[0., 1., np.inf], [np.nan, 1., 2.],
                                      [0., 1., 1.], [0., 1.]])
def test_nonuniform_coordinates_reject_nonfinite_unordered_and_wrong_size(axis, positions):
    dimensions = [1, 1, 1]
    dimensions[axis] = 3
    sim = PyDeviceSimulator(*dimensions, 1e-8, 1e-8, 1e-8)
    with pytest.raises(ValueError, match="position"):
        getattr(sim, f"set_{'xyz'[axis]}_positions")(np.asarray(positions, dtype=float))


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("single_node", [False, True])
@pytest.mark.parametrize("log_space", [False, True])
def test_layered_transient_has_constant_displacement_and_correct_potential(axis, stretched, single_node, log_space):
    size = 9
    dimensions = [1, 1, 1]
    dimensions[axis] = size
    sim = PyDeviceSimulator(*dimensions, 1e-8, 1e-8, 1e-8)
    x = np.arange(size) * 1e-8
    if stretched:
        x = np.array([0., .3, .9, 1.8, 3., 4.7, 5.6, 7.2, 8.]) * 1e-8
        getattr(sim, f"set_{'xyz'[axis]}_positions")(x)
    mask = np.zeros(size, dtype=np.int8)
    mask[4:5] = 1 if single_node else 0
    if not single_node:
        mask[2:7] = 1
    eps = EPS0 * np.where(mask, 25., 4.)
    sim.set_permittivity(eps)
    sim.set_mobility(np.zeros(size), np.zeros(size))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.full(size, 6.))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_dirichlet_potential({0: 0., size-1: -.1})
    sim.set_electron_bc({0: 0., size-1: 0.})
    sim.set_hole_bc({0: 0., size-1: 0.})
    sim.set_initial_guess(-.1 * x/x[-1], np.zeros(size), np.zeros(size))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(mask, -1e8, 1e12)
    sim.set_ferroelectric_model(2)
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_preisach(.002, 1e5, 0.)
    sim.set_ferroelectric_nls(1e-9, 0., 1e-15)
    sim.set_ferroelectric_gamma(0.)
    sim.set_transient_dt(1e-10)
    sim.set_transient_t_final(1e-10)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-10)
    sim.set_newton_use_log_space(log_space)
    state = sim.solve_transient()[-1]
    assert state["valid"]
    np.testing.assert_array_equal(state["n"][[0, -1]], 0.)
    np.testing.assert_array_equal(state["p"][[0, -1]], 0.)
    polarization = state["P"].reshape(size, 3)[:, axis]
    assert polarization[4] > 0.
    h = np.diff(x)
    # Independent continuum integration: each edge consists of two half
    # layers with its endpoint material and polarization. With no free charge,
    # D is constant and dphi/dx=(P-D)/eps in each half layer.
    compliance = h/2 * (1/eps[:-1] + 1/eps[1:])
    source_voltage = h/2 * (polarization[:-1]/eps[:-1] + polarization[1:]/eps[1:])
    displacement = (.1 + source_voltage.sum()) / compliance.sum()
    expected = np.r_[0., np.cumsum(source_voltage - displacement*compliance)]
    np.testing.assert_allclose(state["phi"], expected, rtol=1e-10, atol=1e-12)
    measured_d = (source_voltage - np.diff(state["phi"])) / compliance
    np.testing.assert_allclose(measured_d, displacement, rtol=1e-10, atol=1e-15)
    # A single-node FE film still has two bound-charge sheets: its field must
    # differ from the field obtained by omitting polarization altogether.
    linear_phi = -.1 * np.r_[0., np.cumsum(compliance)] / compliance.sum()
    assert max(abs(state["phi"] - linear_phi)) > 1e-4
