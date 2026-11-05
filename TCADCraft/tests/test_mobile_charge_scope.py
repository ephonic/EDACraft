"""Net pair-source charge cancellation and the actual FV geometry boundary."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.validation.conservation import TransientConservationTest
from test_lk_transport_default import make, check_blocks
from test_lk_interface_material import commercial_device, commercial_errors
from test_lk_fixed_charge import widths
from test_transient_selfconsistent import QE, VT, bernoulli
from test_transient_multidimensional_ledger import experiment


def charge_audit(states):
    return TransientConservationTest(
        integration='backward_euler', charge_atol_C=0., tolerance=1e-5
    ).run(lambda: states)


def check_ledger(states, x, area, contacts, mobile):
    """Reconstruct charge and both endpoint currents without native J arrays."""
    volume = widths(x) * area
    free = np.ones(len(x), dtype=bool)
    free[contacts] = False
    for s in states:
        assert s['valid'] and s['charge_ledger_available']
        expected_q = QE * np.dot((s['p'] - s['n'])[free], volume[free])
        assert s['stored_charge_C'] == pytest.approx(expected_q, rel=2e-12, abs=1e-40)
        u = np.diff(s['phi']) / VT
        bp = np.array([bernoulli(v) for v in u])
        bm = np.array([bernoulli(-v) for v in u])
        face = mobile[:-1] & mobile[1:]
        jn = QE * .1 * VT / np.diff(x) * (s['n'][1:] * bp - s['n'][:-1] * bm) * face
        jp = QE * .05 * VT / np.diff(x) * (s['p'][:-1] * bp - s['p'][1:] * bm) * face
        expected_i = area * np.array([jn[0] + jp[0], -jn[-1] - jp[-1]])
        np.testing.assert_allclose(s['terminal_currents_A'], expected_i, rtol=2e-9, atol=1e-28)
    verdict = charge_audit(states)
    assert verdict.passed, verdict.message
    altered = deepcopy(states)
    altered[-1]['terminal_currents_A'] *= 1.2
    assert not charge_audit(altered).passed


@pytest.mark.parametrize('kind', ['carrier', 'interface'])
@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('log_space', [False, True])
def test_active_pair_sources_keep_full_block_charge_balance(kind, axis, stretched, log_space):
    sim, spec = make(kind, axis=axis, stretched=stretched, log_space=log_space, source=True)
    states = check_blocks(sim, spec, kind)
    mobile = ~spec['blocked'] if kind == 'interface' else np.ones(9, dtype=bool)
    assert np.max(np.abs(states[-1]['n'] - states[0]['n'])) / spec['scale'] > .01
    # Both optical generation and nonlinear SRH are nonzero on mobile free nodes.
    assert np.max(np.asarray(spec['gen'])) > 0.
    initial = states[0]
    product = initial['n'][mobile] * initial['p'][mobile] / spec['scale']**2
    assert np.max(np.abs(product - 1.)) > .1
    check_ledger(states, spec['x'], 1e-14, [0, 8], mobile)


def legacy_mixed(axis, stretched=False, freeze=True):
    shape = (5, 5, 1) if axis == 1 else (5, 1, 5)
    sim, coords, axes, w, contacts, n, p = experiment(
        shape, [(0, False), (0, True)], stretched)
    blocked = coords[:, axis] < 2
    n[blocked] = 0.; p[blocked] = 0.
    sim.set_mobility((~blocked) * .1, (~blocked) * .05)
    sim.set_initial_guess(np.zeros(len(n)), n, p)
    sim.set_electron_bc({int(i): float(n[i]) for i in np.flatnonzero(contacts)})
    sim.set_hole_bc({int(i): float(p[i]) for i in np.flatnonzero(contacts)})
    sim.set_newton_freeze_phi(freeze)
    return sim


@pytest.mark.parametrize('axis', [1, 2])
@pytest.mark.parametrize('stretched', [False, True])
@pytest.mark.parametrize('freeze', [False, True])
def test_mixed_transient_volumes_have_closed_full_volume_ledger(axis, stretched, freeze):
    states = legacy_mixed(axis, stretched, freeze).solve_transient()
    assert all(s['valid'] for s in states)
    assert all(s['charge_ledger_available'] for s in states)
    assert charge_audit(states).passed


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('policy', ['split', 'centered'])
def test_lk_field_policy_does_not_change_transient_volume_ledger(axis, policy):
    sim, _ = make('interface', axis=axis)
    if policy == 'split':
        sim.set_transient_lk_coupled(False)
    else:
        sim.set_transient_lk_coupled(True)
        sim.set_transient_lk_material_field(False)
    states = sim.solve_transient()
    assert all(s['valid'] and not s['lk_material_field'] for s in states)
    assert all(s['charge_ledger_available'] for s in states)
    assert charge_audit(states).passed


@pytest.mark.parametrize('defect', [
    'generation_nan', 'generation_inf', 'generation_negative',
    'tau_n_nan', 'tau_p_inf', 'tau_n_zero', 'tau_p_negative',
])
def test_invalid_pair_source_inputs_cannot_advertise_a_ledger(defect):
    sim, *_ = experiment((5, 3, 1), [(0, False), (0, True)], final=0.)
    if defect.startswith('generation'):
        g = np.zeros(15)
        g[6] = {'generation_nan': np.nan, 'generation_inf': np.inf,
                'generation_negative': -1.}[defect]
        sim.set_optical_generation(g)
    else:
        tn = np.full(15, 1e100); tp = tn.copy()
        (tn if defect.startswith('tau_n') else tp)[6] = {
            'tau_n_nan': np.nan, 'tau_p_inf': np.inf, 'tau_n_zero': 0.,
            'tau_p_negative': -1.,
        }[defect]
        sim.set_recombination(tn, tp)
    states = sim.solve_transient()
    assert not states[0]['charge_ledger_available']


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_nonzero_net_charge_on_blocked_floor_is_not_silently_removed(axis):
    sim, spec = make('interface', axis=axis)
    n = spec['nn'] * spec['scale']; p = spec['pp'] * spec['scale']
    n[2] = 5e-21
    sim.set_initial_guess(np.zeros(9), n, p)
    sim.set_transient_t_final(0.)
    state = sim.solve_transient()[0]
    assert state['valid'] and state['lk_material_field']
    assert not state['charge_ledger_available']


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('log_space', [False, True])
def test_actual_sentaurus_replay_with_zero_density_gate_reservoir(index, log_space):
    data = json.loads((Path(__file__).parent / 'data/sentaurus_fe_si_interface.json').read_text())
    case = data['cases'][index]
    sim, x = commercial_device(case, 32, log_space)
    # Add an explicit empty carrier contact at the insulating gate. Its pinned
    # zero-density row is the same physical constraint as the blocked row.
    sim.set_electron_bc({0: 0.}); sim.set_hole_bc({0: 0.})
    states = sim.solve_transient()
    assert all(s['valid'] and s['charge_ledger_available'] for s in states)
    verdict = charge_audit(states)
    assert verdict.passed, verdict.message
    errors = commercial_errors(case, states, x)
    assert max(errors.values()) < data['predeclared_waveform_peak_normalized_budget']
    area = 1e-11
    free = slice(1, -1)
    for s in states:
        expected = QE * area * np.dot(widths(x)[free], (s['p'] - s['n'])[free])
        assert s['stored_charge_C'] == pytest.approx(expected, rel=3e-12, abs=1e-40)
    # Do not reinterpret the commercial raw Charge columns as this ledger.
    raw_sum = np.array(case['raw']['gate Charge']) + np.array(case['raw']['substrate Charge'])
    stored = np.array([s['stored_charge_C'] for s in states])
    assert np.max(np.abs(raw_sum + stored)) / np.max(np.abs(stored)) > .99
