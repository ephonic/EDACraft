from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from tcad.postprocess.boltzmann_spatial_refinement import (
    audit_mb_uniform_spatial_refinement as audit, _restricted_temperatures,
)
from tcad.postprocess.boltzmann_rounded_trajectory import record_digest
from tcad.postprocess.boltzmann_recomputed_transport import point
from tcad.postprocess.boltzmann_scaled_split import ALPHA

ROOT = Path(__file__).resolve().parents[1]
LENGTH = 2. ** -24
AREA = 2. ** -60


@pytest.fixture(scope='module')
def controls():
    return [j['contract'] for j in json.loads((ROOT / 'docs/validation/mb_spatial_refinement_20261024/jobs.json').read_bytes())['jobs']]


@pytest.fixture(scope='module')
def levels(controls):
    from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
    from tcad.solver.boltzmann_rounded_trajectory import advance_mb_rounded_trajectory
    contracts = []; streams = []
    for source in controls:
        c = deepcopy(source); c['steps'] = 2; lines = []
        states = [MBScaledTransportState(**s) for s in c['initial']]
        faces = [{**f, 'reservoir': MBScaledTransportState(**f['reservoir'])} if 'reservoir' in f else f for f in c['faces']]
        advance_mb_rounded_trajectory(c['configurations'], states, faces, c['thermal_faces'], c['dt_s'], 2,
            impulses_J=c['impulses_J'], record_sink=lines.append)
        assert json.loads(lines[0])['contract'] == c
        contracts.append(c); streams.append([json.loads(x) for x in lines[1:]])
    return contracts, streams


def run(contracts, streams):
    return audit(contracts, streams, length_m=LENGTH, area_m2=AREA)


def test_three_spatial_levels_recompute_all_intervals_and_prefixes(levels):
    c, rows = levels; result = run(c, rows)
    assert result['valid'] and result['cells'] == [2, 4, 8]
    assert result['common_time_samples'] == 2 and result['retained_scalar_temperature_samples'] == 36
    assert result['common_carrier_and_lattice_section_matched'] and result['initial_extensive_restriction_matched']
    assert all(a['valid'] and a['accepted_steps'] == 2 for a in result['independent_trajectory_audits'])
    assert not any(result[k] for k in ('spatial_convergence_qualified', 'temporal_convergence_qualified',
        'discretization_error_bound_established', 'physical_validated', 'complete_device_energy'))


def test_conservative_restriction_uses_particle_weighted_carrier_temperatures(controls):
    from tcad.postprocess.boltzmann_recomputed_transport import endpoint_wire
    from tcad.postprocess.boltzmann_product_range import _binary113
    states = deepcopy(controls[1]['initial'][:2])
    for i, s in enumerate(states):
        p = point(s['endpoint']); f = list(s['endpoint'][3:12]); values = p['values'].copy()
        density = p['frame'][0] * (1 if i == 0 else 2)
        values[3] = density - p['frame'][0]
        # Select exact dyadic kinetic energies with unequal carrier density.
        kinetic = _binary113(ALPHA) * density * (320 if i == 0 else 440)
        values[1] = kinetic - _binary113(ALPHA) * p['frame'][0] * 300
        # The ALPHA reference is not dyadic; its fixed discrepancy is preserved.
        s['endpoint'] = endpoint_wire(f, values)
    projected = _restricted_temperatures(states, 1)
    points = list(map(lambda s: point(s['endpoint']), states))
    expected = sum(p['K'][0] for p in points) / (ALPHA * sum(p['n'][0] for p in points))
    arithmetic = sum(p['temperatures'][1] for p in points) / 2
    assert projected[1] == expected and projected[1] != arithmetic


@pytest.mark.parametrize('damage', ['volume', 'configuration_volume', 'material', 'carrier_area', 'thermal_area',
    'distance', 'mobility', 'conductivity', 'contact', 'bath', 'source', 'initial', 'steps', 'dt', 'budget',
    'chain', 'missing_boundary', 'metadata'])
def test_incompatible_meshes_rejected_before_stream_consumption(controls, damage):
    c = deepcopy(controls)
    if damage == 'volume': c[1]['initial'][0]['endpoint'][7] = '1e-20'
    elif damage == 'configuration_volume': c[1]['configurations'][0]['parameters'][1] = '1e-20'
    elif damage == 'material': c[1]['configurations'][0]['parameters'][6] = '0.5'
    elif damage == 'carrier_area': c[1]['faces'][0]['geometry'][0] *= 2
    elif damage == 'thermal_area': c[1]['thermal_faces'][0]['geometry'][0] *= 2
    elif damage == 'distance': c[1]['faces'][0]['geometry'][1] *= 2
    elif damage == 'mobility': c[1]['faces'][0]['geometry'][3] *= 2
    elif damage == 'conductivity': c[1]['thermal_faces'][0]['geometry'][3] *= 2
    elif damage == 'contact': c[1]['faces'][-1]['reservoir']['endpoint'][5] = '301'
    elif damage == 'bath': c[1]['thermal_faces'][-1]['bath_temperature_K'] += 1
    elif damage == 'source': c[1]['impulses_J'][0][0] *= 2
    elif damage == 'initial': c[1]['initial'][0]['endpoint'] = c[1]['initial'][1]['endpoint']
    elif damage == 'steps': c[1]['steps'] += 1
    elif damage == 'dt': c[1]['dt_s'] *= 2
    elif damage == 'budget': c[1]['energy_atol_J'] /= 2
    elif damage == 'chain': c[1]['faces'][0]['neighbor'] = 2
    elif damage == 'missing_boundary': c[1]['thermal_faces'].pop()
    else: c[1]['complete_device_energy'] = True
    class Forbidden:
        def __iter__(self): raise AssertionError('stream consumed')
    with pytest.raises(ValueError): run(c, [Forbidden() for _ in c])


@pytest.mark.parametrize('damage', ['missing', 'extra', 'endpoint', 'source_proof'])
def test_rehashed_bad_physical_records_rejected(levels, damage):
    c, rows = deepcopy(levels)
    if damage == 'missing': rows[1].pop()
    elif damage == 'extra': rows[1].append(deepcopy(rows[1][-1]))
    elif damage == 'endpoint': rows[1][0]['new'][0]['endpoint'] = c[1]['initial'][0]['endpoint']
    else: rows[1][0]['report']['conducting']['carrier_split']['collisions'][0]['command'][15] = '0'
    previous = record_digest(c[1])
    for row in rows[1]:
        row['previous_sha256'] = previous
        row['sha256'] = record_digest({k: v for k, v in row.items() if k != 'sha256'})
        previous = row['sha256']
    with pytest.raises(ValueError): run(c, rows)


def test_controls_and_previous_rows_are_detached_from_iterator_callbacks(levels):
    c, rows = deepcopy(levels); expected = run(c, rows)
    def mutate():
        c[1]['impulses_J'][0][0] *= 2
        for row in rows[0]:
            yield row
            row['new'][0]['time_s'] = 1.
            row['new'][0]['endpoint'] = c[0]['initial'][0]['endpoint']
    assert run(c, [mutate(), rows[1], rows[2]]) == expected


def test_each_level_is_single_pass(levels):
    c, rows = levels
    class Once:
        def __init__(self, rows): self.rows = rows; self.called = False
        def __iter__(self):
            assert not self.called; self.called = True
            yield from self.rows
    assert run(c, [Once(r) for r in rows])['valid']


def test_sample_budget_is_checked_before_reading(controls):
    c = deepcopy(controls)
    for x in c: x['steps'] = 4000
    with pytest.raises(ValueError, match='sample budget'): run(c, [iter(()) for _ in c])


@pytest.mark.parametrize('length,area', [(0, AREA), (LENGTH, -AREA), (LENGTH * 2, AREA), (LENGTH, AREA * 2)])
def test_invalid_or_mismatched_domain_rejected(controls, length, area):
    with pytest.raises(ValueError): audit(controls, [iter(()) for _ in controls], length_m=length, area_m2=area)


def test_level_count_and_stream_count_rejected():
    with pytest.raises(ValueError): run([], [])
    with pytest.raises(ValueError): run([{}] * 3, [])
