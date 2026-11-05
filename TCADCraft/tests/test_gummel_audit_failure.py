"""Optional returned-state telemetry must preserve an honest FE failure."""
import numpy as np
import pytest
from test_native_nonlinear_history import make_device


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_failed_fe_hidden_state_marks_diagnostics_unavailable_without_raising(axis):
    sim = make_device(axis)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), 2e8, 3e12)
    sim.set_ferroelectric_polar_axis(axis)
    result = sim.solve()
    assert not result['converged']
    assert all(np.all(np.isfinite(result[k])) for k in ('phi', 'n', 'p'))
    audit = result['steady_equation_audit']
    assert not audit['available']
    assert audit['unavailable_reason'].startswith('reassembly_failed: ')
    assert audit['equations_pass'] is None
    assert audit['poisson_scaled_linf'] is None
    assert audit['electron_backward_error_linf'] is None
    assert audit['hole_backward_error_linf'] is None
