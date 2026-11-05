"""A rejected heat solve must not advance cross-bias transport quantum state."""
import numpy as np
import pytest
from test_native_steady_thermal import fixture


def device(axis, bias):
    sim, *_ = fixture(axis=axis, graded=False, variable=False, bias=bias)
    sim.set_quantum_enabled(True)
    sim.set_density_gradient_potential_form(True)
    sim.set_density_gradient_coefficients(1e-18, 1e-18)
    sim.set_doping(np.array([0., 1e19, 2e19, 1e19, 0.]))
    sim.set_gummel_max_iter(300)
    return sim


def same_state(actual, reference):
    for key in ('phi', 'n', 'p', 'Qn', 'Qp', 'temperature',
                'Jn_x', 'Jn_y', 'Jn_z', 'Jp_x', 'Jp_y', 'Jp_z'):
        np.testing.assert_array_equal(actual[key], reference[key], err_msg=key)
    assert actual['iterations'] == reference['iterations']


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('bias', [-.02, .02])
@pytest.mark.parametrize('warm', [False, True])
def test_rejected_thermal_step_keeps_quantum_continuation(axis, bias, warm):
    sim, reference = device(axis, bias), device(axis, bias)
    if warm:
        accepted, control = sim.solve(), reference.solve()
        assert accepted['converged'] and control['converged']
        same_state(accepted, control)
        for d in (sim, reference):
            d.set_dirichlet_potential({0: 0., 4: 2*bias})
    # Finite, positive, representable input. The electrical solve converges,
    # while its very large temperature fails the final export/ledger gate.
    sim.set_thermal_conductivity(np.full(5, 1e-308))
    failed = sim.solve()
    assert not failed['converged']
    assert failed['thermal_ledger']['linear_solve_converged']
    assert not failed['thermal_ledger']['available']
    assert max(abs(failed['Qn'])) > 1e-9
    sim.set_thermal_conductivity(np.full(5, .001))
    retry, fresh = sim.solve(), reference.solve()
    assert retry['converged'] and fresh['converged']
    same_state(retry, fresh)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('bias', [-.02, .02])
def test_accepted_quantum_steps_remain_deterministic(axis, bias):
    left, right = device(axis, bias), device(axis, bias)
    for voltage in (bias, 2*bias, -bias):
        for d in (left, right):
            d.set_dirichlet_potential({0: 0., 4: voltage})
        a, b = left.solve(), right.solve()
        assert a['converged'] and b['converged']
        same_state(a, b)
