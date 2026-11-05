"""Actual 3-D transient surface quadrature, independent of terminal Charge."""
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

from tcad.validation import audit_sentaurus_nonlinear_convergence

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/validation/tetrahedral_surface_20261017'
DATA=ROOT/'tests/data/sentaurus_tetrahedral_surface_3d.json'


def data():return json.loads(DATA.read_text())


def test_reference_mesh_keeps_the_predeclared_two_percent_component_budget():
    d=data();assert d['plan']['reference_relative_budget']==.02
    refs=[c['reference'] for c in d['cases']]
    for key in refs[0]:
        a,b=(np.asarray(r[key]) for r in refs)
        error=float(np.max(abs(a-b))/np.max(abs(b)))
        assert error==pytest.approx(d['reference_errors'][key],rel=1e-13)
        assert error<=.02,key
    assert all(d['gates'].values()) and d['accepted']


@pytest.mark.parametrize('cells',[16,32])
def test_surface_quadrature_passes_charge_and_current_audits_at_all_nine_times(cells):
    a=data()['commercial_audit'][str(cells)]
    q=np.asarray(a['surface_charge_C']);i=np.asarray(a['current_A']);t=np.asarray(a['times_s'])
    assert q.shape==i.shape==(9,2) and t.shape==(9,)
    np.testing.assert_array_equal(q[0],0.)
    np.testing.assert_allclose(a['volume_m3'],(.8e-6)**3,rtol=1e-13,atol=0)
    assert np.max(abs(q.sum(axis=1)))/np.max(abs(q))<=.02
    assert np.max(abs(np.diff(q,axis=0)/np.diff(t)[:,None]-i[1:]))/np.max(abs(i))<=.02
    assert a['surface_vs_reported_charge_relative']<=.02
    assert a['original_replay_max_relative']<1e-9
    assert a['reconstructed_vs_exported_element_e_relative']<1e-11
    assert a['polarization_max_C_m2'][0]==0
    assert all(v>0 for v in a['polarization_max_C_m2'][1:])


@pytest.mark.parametrize('cells',[16,32])
def test_actual_nonlinear_tables_and_all_exported_states_are_retained(cells):
    directory=OUT/f'transient_commercial_moderate_m{cells}'
    a=audit_sentaurus_nonlinear_convergence((directory/'sdevice_run.log').read_text())
    assert a['valid'] and a['table_count']==9
    status=json.loads((directory/'status.json').read_text())
    assert status['inputs_unchanged'] and status['exit_code']==0 and len(status['snapshots'])==9
    for name in status['snapshots']:
        assert (directory/name).stat().st_size>0
        assert (directory/Path(name).with_suffix('.dat')).stat().st_size>0


def test_new_reference_preserves_legacy_rejections_and_the_strong_case():
    d=data();p=ROOT/d['parent_fixture_path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==d['parent_fixture_sha256']
    parent=json.loads(p.read_text())
    assert not parent['groups'][0]['accepted']
    assert not parent['groups'][1]['accepted']
    assert not d['legacy_nodal_surface_audit_replaced']
    assert not d['strong_contrast_accepted']
    assert not d['complete_device_energy'] and not d['physical_validated']


def test_actual_element_exports_and_analysis_match_recorded_sha256():
    for case in data()['cases']:
        for path,digest in case['element_raw_sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
        path=ROOT/case['surface_analysis_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==case['surface_analysis_sha256']


@lru_cache(maxsize=1)
def fresh_native():
    path=ROOT/'docs/validation/nonuniform_fe_3d_20261017/compare.py'
    spec=importlib.util.spec_from_file_location('tetrahedral_surface_native_replay',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    d=data();return module.native(16,d['plan']['times_s'],d['plan'])


def test_fresh_native_16_aligns_all_nine_components_to_both_commercial_meshes():
    d=data();values,record=fresh_native()
    assert d['plan']['relative_budget']==.05
    assert record['charge_sum_relative']<1e-8 and record['current_sum_relative']<1e-8
    retained=next(r for r in d['native'] if r['cells']==16)
    for key,v in values.items():
        np.testing.assert_allclose(v,retained['values'][key],rtol=1e-10,atol=0)
        for case in d['cases']:
            reference=np.asarray(case['reference'][key])
            assert np.max(abs(v-reference))/np.max(abs(reference))<=.05,key


def test_small_transverse_components_are_checked_on_their_own_scale():
    d=data()
    for record in d['native']:
        for errors,case in zip(record['errors'],d['cases']):
            for key in ('ey','ez','py','pz'):
                r=np.asarray(case['reference'][key]);a=np.asarray(record['values'][key])
                assert np.max(abs(r))>0
                assert errors[key]==pytest.approx(np.max(abs(a-r))/np.max(abs(r)),rel=1e-13)
        assert record['relative_errors_passed']==all(max(e.values())<=.05 for e in record['errors'])
