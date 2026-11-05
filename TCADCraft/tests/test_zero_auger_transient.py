"""A zero Auger operator must not narrow the existing transient API scope."""
import hashlib
import json
import os
from pathlib import Path
import struct

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from test_transient_selfconsistent import central_cell


KINDS = ['classical', 'fermi', 'split_lk', 'coupled_lk', 'nls', 'empty_blocked']


def canonical(value):
    """Preserve exported float bits, array dtype/shape and every metadata key."""
    if isinstance(value, np.ndarray):
        return dict(array_dtype=value.dtype.str, shape=value.shape, bits=value.tobytes().hex())
    if isinstance(value, float):
        return dict(float64_bits=struct.pack('>d', value).hex())
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if isinstance(value, np.generic):
        return canonical(value.item())
    return value


def digest(value):
    payload = json.dumps(canonical(value), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(payload.encode('utf8')).hexdigest()


def configured(kind, axis, log_space, budget=80):
    if kind == 'empty_blocked':
        shape = [1, 1, 1]
        shape[axis] = 3
        sim = PyDeviceSimulator(*shape, 1e-6, 1e-6, 1e-6)
        sim.set_permittivity(np.full(3, 11.7*8.854187817e-12))
        sim.set_mobility(np.zeros(3), np.zeros(3))
        sim.set_effective_dos(np.full(3, 1e16), np.full(3, 1e16))
        sim.set_bandgap(np.full(3, 6.))
        sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
        sim.set_dirichlet_potential({0: 0., 2: .01})
        sim.set_electron_bc({0: 0., 2: 0.})
        sim.set_hole_bc({0: 0., 2: 0.})
        sim.set_initial_guess(np.zeros(3), np.zeros(3), np.zeros(3))
        sim.set_transient_dt(1e-10)
        sim.set_transient_t_final(2.5e-10)
    else:
        sim = central_cell(1e16, log_space, axis, True)[0]
        if kind == 'fermi':
            sim.set_statistics_type(1)
        if kind in ['split_lk', 'coupled_lk', 'nls']:
            sim.set_dirichlet_potential({0: 0., 2: -.01})
            sim.set_ferroelectric_enabled(True)
            sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), 1e8, 1e12)
            sim.set_ferroelectric_polar_axis(axis)
            sim.set_ferroelectric_model(2 if kind == 'nls' else 0)
            sim.set_ferroelectric_gamma(0. if kind == 'nls' else .1)
            sim.set_ferroelectric_preisach(.01, 1e3, 0.)
            sim.set_ferroelectric_nls(1e-9, 0., 1e-15)
            sim.set_transient_lk_coupled(kind == 'coupled_lk')
            sim.set_transient_lk_material_field(False)
    sim.set_quantum_enabled(False)
    sim.set_newton_use_log_space(log_space)
    sim.set_gummel_max_iter(budget)
    sim.set_tolerance(1e-11)
    sim.set_nonlinear_history_enabled(True)
    return sim


def snapshot(sim):
    history = sim.solve_transient()
    return history, sim.get_transient_attempt_history()


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('log_space', [False, True])
@pytest.mark.parametrize('budget', [0, 80])
def test_zero_auger_matches_disabled_in_every_exported_bit(kind, axis, log_space, budget):
    disabled = configured(kind, axis, log_space, budget)
    disabled.set_auger_params(8e-43, 7e-44)
    disabled.set_auger_enabled(False)
    baseline = snapshot(disabled)
    baseline_hash = digest(baseline)
    key = f'{kind}/{axis}/{log_space}/{budget}'
    print(json.dumps(dict(test='zero_auger_disabled_reference', key=key, sha256=baseline_hash,
                         states=len(baseline[0]), final_valid=baseline[0][-1]['valid'])))
    oracle = os.environ.get('TCAD_ZERO_AUGER_ORACLE')
    if oracle:
        assert json.loads(Path(oracle).read_text(encoding='utf8'))[key] == baseline_hash
    assert baseline[0][0]['valid']
    if budget:
        assert len(baseline[0]) == 4 and all(s['valid'] for s in baseline[0])
    elif kind != 'empty_blocked':
        assert not baseline[0][-1]['valid'] and baseline[0][-1]['time_s'] == 0.
    zero = configured(kind, axis, log_space, budget)
    zero.set_auger_params(0., -0.)
    zero.set_auger_enabled(True)
    actual = snapshot(zero)
    assert digest(actual) == baseline_hash
    print(json.dumps(dict(test='zero_auger_equal', key=key, sha256=baseline_hash)))


@pytest.mark.parametrize('kind', KINDS[1:])
@pytest.mark.parametrize('coefficients', [(1e-300, 0.), (0., 1e-300), (2.8e-43, 9.9e-44)])
def test_any_positive_auger_coefficient_retains_the_scope_guard(kind, coefficients):
    sim = configured(kind, 0, True)
    sim.set_auger_params(*coefficients)
    sim.set_auger_enabled(True)
    with pytest.raises(ValueError, match='Auger transient requires'):
        sim.solve_transient()
    assert sim.get_transient_attempt_history() == []


@pytest.mark.parametrize('kind', KINDS[1:])
@pytest.mark.parametrize('axis', range(3))
def test_zero_coefficients_recover_after_nonzero_auger_preflight_rejection(kind, axis):
    sim = configured(kind, axis, True)
    sim.set_auger_params(2.8e-43, 9.9e-44)
    sim.set_auger_enabled(True)
    with pytest.raises(ValueError, match='Auger transient requires'):
        sim.solve_transient()
    assert sim.get_transient_attempt_history() == []
    sim.set_auger_params(-0., 0.)
    actual = snapshot(sim)
    fresh = configured(kind, axis, True)
    fresh.set_auger_enabled(False)
    expected = snapshot(fresh)
    assert all(s['valid'] for s in actual[0])
    assert digest(actual) == digest(expected)
