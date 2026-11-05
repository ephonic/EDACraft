"""Retain the failed strong 3-D gate and replay the explicit boundary policy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'tests/data/sentaurus_natural_fe_boundary_3d.json'


def helper():
    path=ROOT/'docs/validation/nonuniform_fe_3d_20261017/compare.py'
    spec=importlib.util.spec_from_file_location('boundary_native_reference',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_recomputed_component_errors_preserve_failed_gate():
    d=json.loads(DATA.read_text());m=helper()
    assert not d['accepted'] and not d['physical_validated'] and not d['complete_device_energy']
    assert d['commercial_reference_reused'] and not d['commercial_reference_rerun']
    assert d['faces']=='yYzZ'
    assert [r['cells'] for r in d['native']]==[8,16,24,32]
    for r in d['native']:
        errors=[m.relative_errors(r['values'],case['reference']) for case in d['cases']]
        assert errors==r['reference_errors']
        assert max(e for v in errors for e in v.values())==r['worst_relative']
        assert r['charge_sum_relative']<1e-7 and r['current_sum_relative']<1e-7
    assert d['native'][-1]['worst_relative']>.05


def test_strict_commercial_reference_is_unchanged():
    d=json.loads(DATA.read_text());p=ROOT/d['parent_fixture_path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==d['parent_fixture_sha256']
    parent=json.loads(p.read_text())
    assert d['cases']==parent['cases']
    assert d['reference_errors']==parent['reference_errors']
    assert max(d['reference_errors'].values())<.02
    for case in d['cases']:
        for name,digest in case['raw_sha256'].items():
            # Names in the golden are complete repository-relative paths.
            path=ROOT/name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest


def test_fresh_native_explicit_boundary_replays_all_components():
    d=json.loads(DATA.read_text());m=helper();backend=m.PyDeviceSimulator
    def configured(*args):
        sim=backend(*args);sim.set_transient_lk_zero_d_faces(d['faces']);return sim
    m.PyDeviceSimulator=configured
    actual,record=m.native(8,d['plan']['times_s'],d['plan'])
    expected=d['native'][0]['values']
    for key in m.KEYS:np.testing.assert_allclose(actual[key],expected[key],rtol=5e-10,atol=0.)
    assert record['charge_sum_relative']<1e-7
