"""Auger rejection must reach Python and preserve the native reaction operator."""
import numpy as np
import pytest
from test_transport_parameter_guard import resistor, same_solution
from test_native_nonlinear_history import make_transport


@pytest.mark.parametrize('slot', range(2))
@pytest.mark.parametrize('bad', [-1., np.nan, np.inf, -np.inf])
def test_auger_rejects_invalid_coefficients(slot, bad):
    _, sim = resistor()
    args = [2.8e-43, 9.9e-44]
    args[slot] = bad
    with pytest.raises(ValueError, match='Auger coefficients must be finite and nonnegative'):
        sim.set_auger_params(*args)


def test_zero_auger_coefficients_are_legal_and_inactive():
    _, pristine = resistor()
    _, zero = resistor()
    zero.set_auger_enabled(True)
    zero.set_auger_params(0., 0.)
    same_solution(pristine, zero)


@pytest.mark.parametrize('enabled', [False, True])
def test_auger_rejection_preserves_reaction_audit(enabled):
    sims = [make_transport(budget=0) for _ in range(3)]
    density = 1e27
    for sim in sims:
        sim.set_initial_guess(np.zeros(3), np.array([1e19, density, 1e19]),
                              np.array([1e19, density, 1e19]))
        sim.set_doping(np.array([0., density, 0.]))
        sim.set_auger_params(2.8e-43, 9.9e-44)
        sim.set_auger_enabled(enabled)
    with pytest.raises(ValueError, match='Auger'):
        sims[1].set_auger_params(8e-43, -1.)
    sims[2].set_auger_enabled(not enabled)
    a,b,opposite = [sim.solve() for sim in sims]
    # Deliberately zero iteration budget: compare the measured returned-state
    # operator. This is not a convergence or material calibration qualification.
    assert not a['converged'] and not b['converged']
    for key in ('phi','n','p','Jn_x','Jp_x','G_ii'):
        np.testing.assert_array_equal(a[key],b[key],err_msg=key)
    assert a['steady_equation_audit'] == b['steady_equation_audit']
    assert a['steady_equation_audit']['electron_backward_error_linf'] != opposite['steady_equation_audit']['electron_backward_error_linf']
