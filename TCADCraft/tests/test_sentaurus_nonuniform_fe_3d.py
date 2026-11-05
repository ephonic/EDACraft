"""Nonuniform real 3-D controls, including explicitly rejected refinements."""
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.validation import ReferenceComparisonTest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/validation/nonuniform_fe_3d_20261017'
DATA=ROOT/'tests/data/sentaurus_nonuniform_fe_3d.json'
spec=importlib.util.spec_from_file_location('nonuniform_3d_comparison',OUT/'compare.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)


def groups():return json.loads(DATA.read_text())['groups']


@lru_cache(maxsize=2)
def actual(index):
    group=groups()[index]
    return comparison.native(8,group['cases'][-1]['times_s'],group['plan'])


@pytest.mark.parametrize('index',[0,1])
def test_native_3d_has_three_nonzero_components_and_conserves_terminal_charge(index):
    values,record=actual(index)
    assert record['shape']==(10,8,8)
    for key in ['ex','ey','ez','px','py','pz']:
        assert np.max(abs(values[key]))>0.
    assert record['charge_sum_relative']<1e-7
    assert record['current_sum_relative']<1e-7
    assert record['yz_symmetry_field_relative']<1e-10
    assert record['yz_symmetry_p_relative']<1e-10


@pytest.mark.parametrize('index',[0,1])
def test_fresh_coarse_native_reproduces_frozen_refinement(index):
    values,_=actual(index)
    saved=next(r for r in groups()[index]['native'] if r['cells']==8)['values']
    for key in comparison.KEYS:
        np.testing.assert_allclose(values[key],saved[key],rtol=1e-10,atol=0.)


@pytest.mark.parametrize('axis',['py','pz'])
def test_small_transverse_polarization_has_its_own_error_scale(axis):
    group=groups()[0];ref=group['cases'][-1]['reference']
    changed={k:np.asarray(v).copy() for k,v in ref.items()}
    changed[axis]*=1.2
    errors=comparison.relative_errors(changed,ref)
    assert errors[axis]>.19
    fields=('px','py','pz')
    result=ReferenceComparisonTest(lambda:changed,lambda:ref,fields=fields,
        rtol=group['plan']['relative_budget'],reference_source='Actual 3-D tetrahedral GLK octant').run()
    assert not result.passed and result.details['field_error_ratios'][axis]>1.


@pytest.mark.parametrize('index',[0,1])
def test_independent_alignment_gates_are_required(index):
    group=groups()[index];plan=group['plan']
    ref_pass=(group['reference_errors'] is not None and
              max(group['reference_errors'].values())<=plan['reference_relative_budget'])
    assert group['gates']['reference_mesh']==ref_pass
    for record in group['native']:
        assert record['relative_errors_passed']==all(max(e.values())<=plan['relative_budget'] for e in record['errors'])
    assert group['gates']['native_alignment']==any(r['relative_errors_passed'] for r in group['native'])
    assert group['accepted']==all(group['gates'].values())
    assert not group['physical_validated'] and not group['complete_device_energy']


def test_strong_contrast_is_still_an_open_case():
    group=groups()[0]
    assert group['plan']['alpha']==1e8
    assert not group['accepted']
    # This is a recorded unresolved benchmark, never an expected-success test.
    assert not group['gates']['reference_mesh']


@pytest.mark.parametrize('index',[0,1])
def test_actual_commercial_charge_and_current_are_independently_consistent(index):
    for audit in groups()[index]['commercial_audit'].values():
        assert audit['nonlinear']['valid']
        assert audit['exported_charge_vs_current_relative']<1e-9
        assert audit['exported_charge_sum_relative']<1e-9
        assert audit['current_sum_relative']<1e-9


def test_reference_raw_files_are_byte_identical_to_their_receipts():
    for group in groups():
        for case in group['cases']:
            assert hashlib.sha256((ROOT/case['raw_path']).read_bytes()).hexdigest()==case['raw_sha256']
            assert case['times_s']==group['plan']['times_s']
            for key in ['ey','ez','py','pz']:
                assert np.max(abs(np.asarray(case['reference'][key])))>0.
