"""A rejected invocation owns no trace, including the first scope guards."""
from copy import deepcopy

import numpy as np
import pytest

from test_transient_displacement import film
from test_transient_selfconsistent import central_cell


def assert_exact(actual, expected):
    if isinstance(expected, np.ndarray):
        np.testing.assert_array_equal(actual, expected)
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_exact(actual[key], expected[key])
    elif isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected):
            assert_exact(left, right)
    else:
        assert actual == expected


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('recording', [False, True])
@pytest.mark.parametrize('model', [None, 0, 1, 2, 3])
@pytest.mark.parametrize('scope', ['ii', 'hfs', 'quantum'])
def test_scope_rejection_clears_previous_trace_without_changing_material_or_retry(
        axis, recording, model, scope):
    def device():
        sim = (central_cell(1e19, False, axis, True)[0] if model is None
               else film(axis, model, True)[0])
        sim.set_nonlinear_history_enabled(True)
        states = sim.solve_transient()
        assert all(s['valid'] for s in states)
        assert sim.get_transient_attempt_history()
        return sim

    sim, reference = device(), device()
    owned = sim.get_transient_attempt_history()
    owned_before = deepcopy(owned)
    memory = sim.get_ferroelectric_ensemble_history()
    sim.set_nonlinear_history_enabled(recording)
    reference.set_nonlinear_history_enabled(recording)
    # FE itself rejects these scopes. The classical case uses DG to exercise
    # the same early geometry guard with positive mobile carrier densities.
    quantum = scope == 'quantum' or model is None
    if quantum:
        sim.set_quantum_enabled(True)
    if scope == 'ii':
        sim.set_ii_driving(1)
        sim.set_ii_enabled(True)
        message = 'II GradQuasiFermi requires'
    elif scope == 'hfs':
        sim.set_high_field_saturation(True, 5e4, 4e4, 2., 1., 0)
        sim.set_high_field_reference_density(1e18, 2e18)
        message = 'nonzero HFS RefDens requires'
    else:
        message = 'transient currently supports'
    with pytest.raises(ValueError, match=message):
        sim.solve_transient()
    cleared = sim.get_transient_attempt_history() == []
    assert_exact(sim.get_ferroelectric_ensemble_history(), memory)
    assert_exact(owned, owned_before)
    if scope == 'ii':
        sim.set_ii_enabled(False)
        sim.set_ii_driving(0)
    if scope == 'hfs':
        sim.set_high_field_saturation(False, 5e4, 4e4, 2., 1., 0)
        sim.set_high_field_reference_density(0., 0.)
    if quantum:
        sim.set_quantum_enabled(False)
    # Compare every returned field and diagnostic, then reverse the drive to
    # expose any persistent FE/play-history change hidden by the first retry.
    assert_exact(sim.solve_transient(), reference.solve_transient())
    assert_exact(sim.get_transient_attempt_history(), reference.get_transient_attempt_history())
    for backend in (sim, reference):
        last = 2 if model is None else 8
        backend.set_dirichlet_potential({0: 0., last: .015})
    assert_exact(sim.solve_transient(), reference.solve_transient())
    assert_exact(sim.get_transient_attempt_history(), reference.get_transient_attempt_history())
    assert cleared, 'preflight rejection retained diagnostics from the previous invocation'


def configure_explicit(sim, mode):
    if mode == 'three_temperature':
        from test_three_temperature import case
        from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
        model, old = case(count=3)
        sim.configure_three_temperature(*pack_three_temperature_inputs(
            model, old, 1., 2e-28, 1e-9, 1e-27), old.time_s)
        return (sim.three_temperature_state,
                lambda: sim.prepare_three_temperature(2e-14, 2e-28, 1e-9, 1e-27),
                sim.discard_three_temperature)
    if mode == 'energy_coordinate':
        from test_energy_coordinate_transport import transport_case
        from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates, _pack
        model, old = transport_case(count=3, a=0, c=0)
        state = initialize_energy_coordinates(model, old)
        packed, _ = _pack(model, state.thermal, 1., 2e-28, 1e-9, 1e-27)
        sim.configure_energy_coordinate(*packed, state.excess_J_m3, 0.)
        return (sim.energy_coordinate_state,
                lambda: sim.prepare_energy_coordinate(2e-14, 2e-28, 1e-9, 1e-27),
                sim.discard_energy_coordinate)
    from test_lattice_excess import lattice_case
    from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
    model, old = lattice_case(a=0, c=0, count=3)
    device = LatticeCoupledExcessRelaxation(model, old)
    config = device.configuration
    initial = [v for cell in config.cells for v in (
        *cell.initial_densities_m3, cell.initial_temperatures_K[2],
        *cell.initial_temperatures_K[:2])]
    sim.configure_lattice_excess(initial, config.packed_parameters(), config.packed_faces(),
        *config.cells[0].packed_valleys(), 0.)
    return (sim.isolated_relaxation_state,
            lambda: sim.prepare_isolated_relaxation(2e-14, 2e-28, 1e-9, 1e-27),
            sim.discard_isolated_relaxation)


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('recording', [False, True])
@pytest.mark.parametrize('mode', ['three_temperature', 'energy_coordinate', 'isolated_lattice'])
def test_explicit_mode_rejection_clears_trace_and_keeps_accepted_state_and_pending_token(
        axis, recording, mode):
    sim = central_cell(1e19, False, axis, True)[0]
    sim.set_nonlinear_history_enabled(True)
    assert all(s['valid'] for s in sim.solve_transient())
    owned = sim.get_transient_attempt_history()
    assert owned
    saved = deepcopy(owned)
    sim.set_nonlinear_history_enabled(recording)
    snapshot, prepare, discard = configure_explicit(sim, mode)
    before = snapshot()
    candidate, token = prepare()
    # The mode rejection must neither discard nor commit a pending candidate.
    with pytest.raises(RuntimeError, match='legacy solve/transaction unavailable'):
        sim.solve_transient()
    cleared = sim.get_transient_attempt_history() == []
    assert_exact(snapshot(), before)
    assert_exact(owned, saved)
    discard(token)
    again, next_token = prepare()
    assert next_token > token
    assert_exact(again, candidate)
    assert_exact(snapshot(), before)
    discard(next_token)
    assert cleared, 'explicit-mode rejection retained diagnostics from the previous invocation'
