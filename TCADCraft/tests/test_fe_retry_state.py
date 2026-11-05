"""Failed electrical attempts must not consume a ferroelectric dwell."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.material.library import alscn


def _slab(model, use_newton):
    count = 9
    material = alscn()
    sim = PyDeviceSimulator(count, 1, 1, 40e-9 / (count - 1), 1.0, 1.0)
    sim.set_permittivity(np.full(count, 8.854187817e-12 * material.epsilon_r))
    sim.set_mobility(np.zeros(count), np.zeros(count))
    sim.set_doping(np.zeros(count))
    sim.set_effective_dos(np.full(count, 2.8e25), np.full(count, 1.04e25))
    sim.set_bandgap(np.full(count, material.Eg))
    sim.set_thermal_voltage(0.02585)
    sim.set_electron_bc({0: 0.0, count - 1: 0.0})
    sim.set_hole_bc({0: 0.0, count - 1: 0.0})
    sim.set_dirichlet_potential({0: 0.0, count - 1: 0.0})
    sim.set_ferroelectric_enabled(True)
    # Interior FE/linear-dielectric interfaces create bound charge after the
    # first predictor, requiring another electrical iteration to settle it.
    mask = np.ones(count, dtype=np.int8)
    mask[[0, count - 1]] = 0
    sim.set_ferroelectric_params(mask, material.fe_alpha, material.fe_beta)
    sim.set_ferroelectric_model(model)
    sim.set_ferroelectric_preisach(material.fe_ps, material.fe_ec, 0.0)
    sim.set_ferroelectric_nls(1e-6, 2e9, 1e-2)
    sim.set_use_newton(use_newton)
    sim.set_tolerance(1e-8)
    sim.set_gummel_max_iter(300)
    assert sim.solve()["converged"]
    return sim, count


@pytest.mark.parametrize("model,use_newton,start_voltage", [
    (model, newton, 0.0) for model in (1, 2, 3) for newton in (False, True)
] + [
    # A homogeneous reversal can be solved by Newton in one iteration;
    # use the block path to force failure from a nonzero memory state.
    (model, False, 20.0) for model in (1, 2, 3)
])
def test_failed_attempt_does_not_advance_fe_memory(model, use_newton, start_voltage):
    retried, count = _slab(model, use_newton)
    reference, _ = _slab(model, use_newton)
    for sim in (retried, reference):
        sim.set_dirichlet_potential({0: 0.0, count - 1: start_voltage})
        initial = sim.solve()
        assert initial["converged"]
        if sim is retried:
            before = initial["P"].copy()
        # A large reversal overcomes the previous state's depolarizing field.
        target = 20.0 if start_voltage == 0.0 else -80.0
        sim.set_dirichlet_potential({0: 0.0, count - 1: target})

    retried.set_gummel_max_iter(1)
    for _ in range(3):
        failed = retried.solve()
        assert not failed["converged"]
        np.testing.assert_array_equal(failed["P"], before)

    retried.set_gummel_max_iter(300)
    recovered = retried.solve()
    direct = reference.solve()
    assert recovered["converged"] and direct["converged"]
    assert np.max(np.abs(direct["P"])) > 1e-3
    np.testing.assert_allclose(recovered["P"], direct["P"], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(recovered["phi"], direct["phi"], rtol=1e-8, atol=1e-8)
