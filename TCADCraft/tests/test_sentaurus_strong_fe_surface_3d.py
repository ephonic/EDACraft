"""Actual strong 3-D FE outputs must retain every unresolved acceptance gate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

from tcad.validation import audit_sentaurus_nonlinear_convergence

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'tests/data/sentaurus_strong_fe_surface_3d.json'


def data():return json.loads(DATA.read_text())


def test_strong_reference_gates_are_recomputed_without_relaxing_budgets():
    d=data();assert d['plan']['reference_relative_budget']==.02 and d['plan']['relative_budget']==.05
    assert d['plan']['commercial_cells']==[16,32]
    for key in d['reference_errors']:
        a,b=(np.asarray(c['reference'][key]) for c in d['cases'])
        error=np.max(abs(a-b))/np.max(abs(b))
        assert error==pytest.approx(d['reference_errors'][key],rel=1e-13)
    assert d['gates']['reference_mesh']==(max(d['reference_errors'].values())<=.02)
    assert d['accepted']==all(d['gates'].values())
    assert not d['complete_device_energy'] and not d['physical_validated']


@pytest.mark.parametrize('cells',[16,32])
def test_strict_nonlinear_tables_and_all_nine_raw_states(cells):
    d=data();case=next(c for c in d['cases'] if c['cells']==cells)
    directory=ROOT/case['source_directory']
    status=json.loads((directory/'status.json').read_text())
    assert status['exit_code']==0 and status['inputs_unchanged'] and len(status['snapshots'])==9
    report=audit_sentaurus_nonlinear_convergence((directory/'sdevice_run.log').read_text())
    assert report['valid'] and report['table_count']==9
    for path,digest in case['raw_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path


@pytest.mark.parametrize('cells',[16,32])
def test_independent_surface_gate_uses_absolute_charge_and_own_current_scale(cells):
    a=data()['commercial_audit'][str(cells)]
    q=np.asarray(a['surface_charge_C']);i=np.asarray(a['current_A']);t=np.asarray(a['times_s'])
    qi=np.max(abs(np.diff(q,axis=0)/np.diff(t)[:,None]-i[1:]))/np.max(abs(i))
    balance=np.max(abs(q.sum(axis=1)))/np.max(abs(q))
    assert qi==pytest.approx(a['surface_vs_current_relative'],rel=1e-13)
    assert balance==pytest.approx(a['charge_sum_relative'],rel=1e-13)
    assert a['independent_surface_accepted']==(qi<=.02 and balance<=.02)
    assert a['reconstructed_vs_exported_element_e_relative']<1e-11
    assert all(p>0 for p in a['polarization_max_C_m2'][1:])


def test_volume_energy_closure_requires_local_lk_as_well_as_small_global_residual():
    d=data()
    audits=[*d['energy_audit'].values(),d['moderate_energy_control']]
    for audit in audits:
        assert audit['inputs_unchanged']
        for records in audit['reports'].values():
            assert len(records)==8
            for r in records:
                work=np.asarray(r['source_work_J'])
                residual=work-sum(np.asarray(r[k]) for k in ['dielectric_storage_change_J',
                    'landau_storage_change_J','lk_dissipation_J','dielectric_be_correction_J','landau_be_correction_J'])
                np.testing.assert_allclose(residual,r['energy_balance_residual_J'],rtol=1e-8,atol=1e-35)
                assert r['energy_balance_compatible']==(max(abs(residual))<=r['energy_budget_J'])
                assert r['local_lk_compatible']==(max(r['lk_max_field_residual_V_m'])<=r['lk_field_budget_V_m'])
                assert r['valid']==(r['energy_balance_compatible'] and r['local_lk_compatible'] and r['charge_balance_compatible'])
                assert not r['complete_device_energy'] and not r['physical_validated']
    # Small globally integrated residuals cannot certify interpolated cell P.
    moderate=d['moderate_energy_control']['summary']['reported_charge']
    assert moderate['max_energy_relative_residual']<.02
    assert moderate['max_lk_relative_residual']>.02 and not moderate['valid']


def test_unchanged_native_replay_preserves_strong_transverse_error():
    d=data();path=ROOT/'docs/validation/nonuniform_fe_3d_20261017/compare.py'
    spec=importlib.util.spec_from_file_location('strong_surface_native_replay',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    values,record=module.native(8,d['plan']['times_s'],d['plan'])
    retained=next(r for r in d['native'] if r['cells']==8)
    for key,value in values.items():np.testing.assert_allclose(value,retained['values'][key],rtol=1e-10,atol=0)
    for r in d['native']:
        for actual,case in zip(r['errors'],d['cases']):
            expected=module.relative_errors(r['values'],case['reference'])
            assert actual==pytest.approx(expected,rel=1e-13)
        assert r['relative_errors_passed']==all(max(e.values())<=.05 for e in r['errors'])
    assert d['gates']['native_alignment']==any(r['relative_errors_passed'] for r in d['native'])


def test_previous_failed_and_accepted_controls_keep_their_original_identity():
    d=data();path=ROOT/d['parent_fixture_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==d['parent_fixture_sha256']
    assert not json.loads(path.read_text())['groups'][0]['accepted']
    moderate=json.loads((ROOT/'tests/data/sentaurus_tetrahedral_surface_3d.json').read_text())
    assert moderate['accepted'] and not moderate['strong_contrast_accepted']
