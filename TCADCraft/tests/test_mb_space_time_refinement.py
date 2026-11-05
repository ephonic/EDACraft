from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from tcad.postprocess.boltzmann_space_time_refinement import (
    audit_mb_uniform_space_time_refinement as audit, _comparison, _interactions,
)
from tcad.postprocess.boltzmann_rounded_trajectory import record_digest

ROOT = Path(__file__).resolve().parents[1]
LENGTH = 2. ** -24
AREA = 2. ** -60


@pytest.fixture(scope='module')
def controls():
    return json.loads((ROOT / 'docs/validation/mb_space_time_refinement_20261024/jobs_v2.json').read_bytes())['contract_grid']


@pytest.fixture(scope='module')
def levels(controls):
    from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
    from tcad.solver.boltzmann_rounded_trajectory import advance_mb_rounded_trajectory
    grid = deepcopy(controls); records = []
    for row in grid:
        streams = []
        for t, c in enumerate(row):
            c['steps'] = 1 << t; lines = []
            states = [MBScaledTransportState(**s) for s in c['initial']]
            faces = [{**f, 'reservoir': MBScaledTransportState(**f['reservoir'])} if 'reservoir' in f else f for f in c['faces']]
            advance_mb_rounded_trajectory(c['configurations'], states, faces, c['thermal_faces'], c['dt_s'], c['steps'],
                impulses_J=c['impulses_J'], record_sink=lines.append)
            assert json.loads(lines[0])['contract'] == c
            streams.append([json.loads(x) for x in lines[1:]])
        records.append(streams)
    return grid, records


def run(c, records):
    return audit(c, records, length_m=LENGTH, area_m2=AREA)


@pytest.fixture(scope='module')
def comparison(levels):
    import tcad.postprocess.boltzmann_space_time_refinement as module
    c, records = levels; calls = []; original = module.audit_mb_owned_trajectory
    class Once:
        def __init__(self, rows): self.rows = rows; self.called = False
        def __iter__(self):
            assert not self.called; self.called = True
            yield from self.rows
    def counted(*a, **kw):
        calls.append(1)
        return original(*a, **kw)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, 'audit_mb_owned_trajectory', counted)
        result = run(c, [[Once(r) for r in row] for row in records])
    return result, len(calls)


def test_nine_trajectories_audited_once_and_compared_on_common_times(comparison):
    result, calls = comparison
    assert result['valid'] and calls == result['trajectories_audited_once'] == 9
    assert result['cells'] == [2, 4, 8] and result['steps'] == [1, 2, 4]
    assert result['audited_intervals'] == 21 and result['common_time_samples'] == 1
    assert result['retained_scalar_temperature_samples'] == 180
    assert len(result['spatial_comparisons']) == len(result['temporal_comparisons']) == 3
    assert len(result['observed_interactions']) == 4
    assert all(x['triangle_inequalities_checked'] for x in result['observed_interactions'])
    assert all(a['valid'] for row in result['independent_trajectory_audits'] for a in row)
    assert not any(result[k] for k in ('spatial_convergence_qualified', 'temporal_convergence_qualified',
        'temporal_error_bound_established', 'discretization_error_bound_established', 'physical_validated', 'complete_device_energy'))


def test_native_cell_errors_are_retained_when_conservative_projection_cancels():
    zero = (Fraction(),) * 6
    def sample(value): return [(Fraction(1), (value, -value, *zero[2:]), zero)]
    levels = [sample(Fraction()), sample(Fraction(2)), sample(Fraction(3))]
    native = _comparison(levels, 1); restricted = _comparison(levels, 2)
    assert float(native['maximum_temperature_differences_K'][0]) == 2
    assert all(float(x) == 0 for x in restricted['maximum_temperature_differences_K'])
    assert restricted['equal_grid_max_norm_ratios'] == [None] and restricted['observed_orders'] == [None]


def test_spatial_norm_can_hide_large_mixed_difference_without_error_bound():
    def sample(a, b): return [(Fraction(1), (), (Fraction(a), Fraction(b)))]
    samples = [[sample(2, -2), sample(-2, 2)], [sample(0, 0), sample(0, 0)]]
    result = _interactions(samples)[0]
    assert float(result['maximum_spatial_norm_change_K']) == 0
    assert float(result['maximum_mixed_difference_K']) == float(result['maximum_observed_temporal_sum_K']) == 4
    assert result['triangle_inequalities_checked'] and not result['truncation_error_bound_established']


@pytest.mark.parametrize('axis,number', [('space', 0), ('space', 2), ('space', 6), ('time', 0), ('time', 2), ('time', 6)])
def test_grid_level_bounds_are_checked_before_streams(controls, axis, number):
    c = deepcopy(controls)
    c = [c[0]] * number if axis == 'space' else [[row[0]] * number for row in c]
    with pytest.raises(ValueError): run(c, [])


def test_ragged_contract_grid_rejected(controls):
    c = deepcopy(controls); c[1].append(deepcopy(c[1][-1]))
    with pytest.raises(ValueError, match='rectangular'): run(c, [])


@pytest.mark.parametrize('damage', ['row', 'column'])
def test_record_grid_shape_must_match(controls, damage):
    records = [[iter(()) for _ in row] for row in controls]
    if damage == 'row': records.pop()
    else: records[1].pop()
    with pytest.raises(ValueError, match='rectangular record'): run(controls, records)


@pytest.mark.parametrize('damage', ['dt', 'steps', 'source_power', 'material', 'initial', 'boundary',
    'budget', 'geometry', 'volume', 'metadata'])
def test_mismatched_axes_fail_before_any_records_run(controls, damage):
    c = deepcopy(controls)
    for row in c:
        x = row[1]
        if damage == 'dt': x['dt_s'] *= 1.01
        elif damage == 'steps': x['steps'] += 1
        elif damage == 'source_power':
            for q in x['impulses_J']: q[0] *= 2
        elif damage == 'material':
            for cfg in x['configurations']: cfg['parameters'][6] = '0.5'
        elif damage == 'initial': x['initial'][0]['endpoint'] = deepcopy(x['initial'][1]['endpoint'])
        elif damage == 'boundary': x['faces'][-1]['reservoir']['endpoint'][5] = '301'
        elif damage == 'budget': x['energy_atol_J'] /= 2
        elif damage == 'geometry': x['thermal_faces'][0]['geometry'][0] *= 2
        elif damage == 'volume': x['configurations'][0]['parameters'][1] = '1e-20'
        else: x['physical_validated'] = True
    class Forbidden:
        def __iter__(self): raise AssertionError('records consumed')
    with pytest.raises(ValueError): run(c, [[Forbidden() for _ in row] for row in c])


@pytest.mark.parametrize('damage', ['missing', 'extra', 'endpoint', 'source_proof'])
def test_rehashed_forged_records_rejected(levels, damage):
    c, records = deepcopy(levels); rows = records[0][1]
    if damage == 'missing': rows.pop()
    elif damage == 'extra': rows.append(deepcopy(rows[-1]))
    elif damage == 'endpoint': rows[0]['new'][0]['endpoint'] = c[0][1]['initial'][0]['endpoint']
    else: rows[0]['report']['conducting']['carrier_split']['collisions'][0]['command'][15] = '0'
    previous = record_digest(c[0][1])
    for row in rows:
        row['previous_sha256'] = previous
        row['sha256'] = record_digest({k: v for k, v in row.items() if k != 'sha256'})
        previous = row['sha256']
    with pytest.raises(ValueError): run(c, records)


def test_callback_cannot_change_later_contracts_or_previous_rows(levels, comparison):
    c, records = deepcopy(levels); original = records[0][0]
    def mutate():
        c[2][2]['steps'] = 1
        c[1][1]['impulses_J'][0][0] *= 2
        for row in original:
            yield row
            row['new'][0]['time_s'] = 1.
            row['new'][0]['endpoint'] = c[0][0]['initial'][0]['endpoint']
    records[0][0] = mutate()
    assert run(c, records) == comparison[0]


def test_joint_native_and_restricted_sample_budget_checked_before_reading(controls):
    c = deepcopy(controls)
    for row in c:
        for t, x in enumerate(row): x['steps'] = 512 * (1 << t)
    with pytest.raises(ValueError, match='joint.*sample budget'): run(c, [[iter(()) for _ in row] for row in c])


def test_shared_time_comparison_rejects_different_exact_clocks():
    sample = [(Fraction(1), (Fraction(2),), (Fraction(2),))]
    other = [(Fraction(2), (Fraction(2),), (Fraction(2),))]
    with pytest.raises(ValueError, match='clock mismatch'): _comparison([sample, other], 1)
