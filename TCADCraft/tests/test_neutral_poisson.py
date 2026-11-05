"""Real native equilibrium transport/heat and physical-residual diagnostics."""
import numpy as np
import pytest

from tcad.postprocess import audit_native_steady_thermal
from test_native_steady_thermal import fixture, EXTRUSION, BUDGET


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('graded', [False, True])
def test_mobile_zero_field_equilibrium_closes_two_bath_heat(axis, graded):
    sim, axes, conductivity, bath = fixture(axis=axis, graded=graded, variable=False, bias=0.)
    bath[4] = 350.
    sim.set_thermal_dirichlet(bath)
    sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    assert result['converged']
    assert result['poisson_residual_metric'] == 'physical_scaled_linf'
    assert result['poisson_residual'] < 1e-12
    np.testing.assert_allclose(result['phi'], 0., atol=1e-16)
    np.testing.assert_allclose(result['n'], 1e21, rtol=1e-13)
    np.testing.assert_allclose(result['p'], 1e21, rtol=1e-13)
    expected = 300. + 50.*axes[axis]/axes[axis][-1]
    np.testing.assert_allclose(result['temperature'], expected, atol=1e-9)
    audit = audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)
    assert audit['valid']
    stage, = result['nonlinear_history']
    assert stage['poisson_residual_metric'] == result['poisson_residual_metric']
    assert stage['poisson_scaled_linf'].shape == stage['poisson_relative_l2'].shape
    assert np.all(stage['poisson_scaled_linf'] < 1e-12)
    assert not np.shares_memory(stage['poisson_scaled_linf'], stage['poisson_relative_l2'])


def test_old_relative_residual_is_preserved_as_separate_diagnostic():
    sim, *_ = fixture(graded=False, variable=False, bias=0.)
    sim.set_nonlinear_history_enabled(True)
    result = sim.solve()
    stage, = result['nonlinear_history']
    assert result['converged']
    # History samples precede the undamped final polish; exact cancellation
    # in those samples may give raw zero even when the exit formerly gave 1.
    assert np.all(np.isfinite(stage['poisson_relative_l2']))
    assert max(stage['poisson_scaled_linf']) < 1e-12


@pytest.mark.parametrize('bias', [-.02, 0., .02])
def test_reported_physical_residual_matches_independent_uniform_row_equation(bias):
    sim, axes, *_ = fixture(graded=False, variable=False, bias=bias)
    result = sim.solve()
    assert result['converged']
    phi, n, p = (result[name] for name in ('phi', 'n', 'p'))
    c = 1e-10/np.diff(axes[0])[0]**2
    charge = -1.602176634e-19*(p[1:-1]-n[1:-1])
    residual = abs(c*(phi[:-2]-2*phi[1:-1]+phi[2:])-charge)
    scale = .02585*4*c + 1.602176634e-19*(n[1:-1]+p[1:-1]) + abs(charge)
    # Native arithmetic is quad; exported doubles lose small cancellation.
    assert result['poisson_residual'] < 1e-12
    assert max(residual/scale) < 1e-12


def test_zero_budget_wrong_field_is_still_rejected():
    sim, *_ = fixture(graded=False, variable=False, bias=0.)
    sim.set_initial_guess(np.array([0., 0., .1, 0., 0.]), np.full(5,1e21), np.full(5,1e21))
    sim.set_gummel_max_iter(0)
    result = sim.solve()
    assert not result['converged']
    assert result['poisson_residual'] > 1e-3
