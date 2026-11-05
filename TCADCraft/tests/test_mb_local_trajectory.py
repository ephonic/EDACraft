from copy import deepcopy
from fractions import Fraction
import json
import pytest
from tcad.postprocess.boltzmann_local_trajectory import (
    audit_mb_weak_local_trajectory as audit, _local_ledger, _sum, _prefix,
)
from tcad.postprocess.boltzmann_weak_trajectory import audit_mb_weak_trajectory, _ledger
from tcad.postprocess.boltzmann_rounded_trajectory import record_digest
from tcad.solver.boltzmann_weak_trajectory import advance_mb_weak_trajectory
from docs.validation.mb_local_graph_20261025.cases import control


@pytest.fixture(scope='module')
def cases():
    result = {}
    for mode in ('open', 'closed'):
        c, old, faces = control(mode, steps=3); lines = []
        new, report = advance_mb_weak_trajectory(c['configurations'], old, faces, c['thermal_faces'], c['dt_s'], c['steps'],
            impulses_J=c['impulses_J'], record_sink=lines.append, checkpoint_stride=1)
        header, *rows = map(json.loads, lines)
        result[mode] = (header['contract'], rows, report)
    return result


@pytest.mark.parametrize('mode', ['open', 'closed'])
def test_nonuniform_branched_graph_closes_every_cell_and_global_prefix(cases, mode):
    c, rows, report = cases[mode]; checked = audit(c, rows, checkpoint_stride=1)
    assert checked['fresh_interval_audits'] == 3 and checked['cell_intervals'] == 12
    assert checked['all_actual_cell_prefixes_closed'] and checked['all_actual_global_prefixes_closed']
    assert len(checked['checkpoints']) == 3
    assert all(len(p['cells']) == 4 for p in checked['checkpoints'])
    assert audit_mb_weak_trajectory(c, rows, checkpoint_stride=1) == report['independent_audit']
    assert not checked['complete_device_energy'] and not checked['field_work_included']


@pytest.mark.parametrize('mode', ['open', 'closed'])
def test_internal_ownership_and_sources_sum_to_separate_global_ledger(cases, mode):
    c, rows, _ = cases[mode]
    for row in rows: assert _sum(_local_ledger(c, row['report'])) == _ledger(c, row['report'])


def test_local_prefix_gate_rejects_equal_opposite_errors_hidden_by_global_sum():
    zero = [Fraction()] * 6; limits = [Fraction(1)] * 6
    plus = [Fraction(1, 4)] * 6; minus = [-x for x in plus]; budget = [Fraction(1, 8)] * 6
    assert _prefix(_sum([plus, minus]), zero, zero, _sum([budget, budget]), limits, 'global')[0] == zero
    for local in (plus, minus):
        with pytest.raises(ValueError, match='actual prefix'): _prefix(local, zero, zero, budget, limits, 'cell')


def test_local_cumulative_budget_cap_is_not_relaxed_by_cancellation():
    zero = [Fraction()] * 6
    with pytest.raises(ValueError, match='allowance exhausted'):
        _prefix(zero, zero, zero, [Fraction(2)] * 6, [Fraction(1)] * 6, 'cell')


def rechain(c, rows):
    previous = record_digest(c)
    for row in rows:
        row['previous_sha256'] = previous
        row['sha256'] = record_digest({k:v for k,v in row.items() if k != 'sha256'})
        previous = row['sha256']


@pytest.mark.parametrize('damage', ['owner', 'neighbor', 'volume', 'cv', 'law', 'source', 'bath', 'missing', 'extra', 'skip'])
def test_rehashed_graph_controls_and_coverage_forgeries_are_rejected(cases, damage):
    c, rows, _ = cases['open']; c = deepcopy(c); rows = deepcopy(rows)
    if damage == 'owner': c['faces'][0]['owner'] = 2
    elif damage == 'neighbor': c['faces'][0]['neighbor'] = 3
    elif damage == 'volume': c['configurations'][0]['parameters'][1] = '1e-25'
    elif damage == 'cv': c['configurations'][1]['parameters'][0] = '513'
    elif damage == 'law': c['configurations'][2]['parameters'][6] = '0.5'
    elif damage == 'source': c['impulses_J'][3][0] *= 2
    elif damage == 'bath': c['thermal_faces'][-1]['owner'] = 2
    elif damage == 'missing': rows.pop()
    elif damage == 'extra': rows.append(deepcopy(rows[-1]))
    else: rows[1]['index'] = 7
    rechain(c, rows)
    with pytest.raises((ValueError, ArithmeticError)): audit(c, rows)


def test_producer_audit_claims_are_ignored(cases):
    c, rows, _ = cases['open']; rows = deepcopy(rows)
    for row in rows:
        row['report']['independent_audit'] = dict(valid=True, cells='forged', global_budgets=['1e99']*6)
    rechain(c, rows)
    assert audit(c, rows)['all_actual_cell_prefixes_closed']


def test_iterator_cannot_mutate_previously_owned_controls_or_rows(cases):
    c, rows, _ = cases['closed']; c = deepcopy(c); rows = deepcopy(rows)
    def stream():
        c['steps'] = 1
        yield rows[0]
        rows[0]['new'][0]['time_s'] = 99.
        yield from rows[1:]
    assert audit(c, stream())['accepted_steps'] == 3


def test_tighter_contract_cap_is_enforced(cases):
    c, rows, _ = cases['open']; c = deepcopy(c); rows = deepcopy(rows)
    c['energy_atol_J'] = 1e-60; rechain(c, rows)
    with pytest.raises(ValueError, match='allowance exhausted'): audit(c, rows)


@pytest.mark.parametrize('stride', [0, True, 16385])
def test_invalid_checkpoint_stride_is_rejected_before_iteration(cases, stride):
    c, _, _ = cases['closed']
    def records(): raise AssertionError('iterator must not be invoked')
    with pytest.raises(ValueError, match='stride'): audit(c, records, checkpoint_stride=stride)
