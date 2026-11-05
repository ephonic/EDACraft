"""Recompute mesh-study gates and check the uniform-limit native solution."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / 'docs/validation/graded_fe_mesh_20261017'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_components_and_physical_supports_recompute():
    d = json.loads((PHASE / 'final_result.json').read_text())
    reference = ROOT / d['reference_fixture_path']
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == d['reference_fixture_sha256']
    parent = json.loads(reference.read_text())
    helper = load_module(PHASE / 'compare.py', 'graded_mesh_comparison')
    assert [(r['fine'], r['coarse']) for r in d['native']] == [(12, 8), (16, 8), (24, 8)]
    for r in d['native']:
        errors = [helper.helper.relative_errors(r['values'], case['reference'])
                  for case in parent['cases']]
        assert errors == r['reference_errors']
        assert r['worst_relative'] == max(v for error in errors for v in error.values())
        x, y, z = map(np.asarray, r['axes_m'])
        assert x[0] == 0 and x[-1] == .8e-6
        np.testing.assert_array_equal(y, z)
        for a in (x[1:-1], y, z):
            np.testing.assert_allclose([a[0] - np.diff(a)[0] / 2,
                                       a[-1] + np.diff(a)[-1] / 2],
                                      [0, .8e-6], rtol=0, atol=1e-21)
            assert abs((a[r['fine'] - 1] + a[r['fine']]) / 2 - .4e-6) < 1e-21
        assert r['charge_sum_relative'] < 1e-7
        assert r['current_sum_relative'] < 1e-7
        assert r['yz_symmetry_field_relative'] < 1e-12
        assert r['yz_symmetry_p_relative'] < 1e-12
    fine = list(parent['commercial_audit'].values())[-1]
    accepted = (d['native'][-1]['worst_relative'] <= .05
                and max(parent['reference_errors'].values()) <= .02
                and fine['surface_vs_current_relative'] <= .02
                and fine['charge_sum_relative'] <= .02
                and fine['nonlinear']['valid'])
    assert d['accepted'] == accepted
    assert not d['physical_validated'] and not d['complete_device_energy']


def test_actual_native_uniform_limit_matches_frozen_boundary_control():
    d = json.loads((ROOT / 'tests/data/sentaurus_natural_fe_boundary_3d.json').read_text())
    helper = load_module(PHASE / 'compare.py', 'graded_native_uniform_control')
    actual, record = helper.native(4, 4, d['plan']['times_s'], d['plan'])
    expected = d['native'][0]['values']
    for key in helper.KEYS:
        scale = np.max(np.abs(expected[key]))
        assert np.max(np.abs(actual[key] - expected[key])) / scale < 5e-10
    assert record['charge_sum_relative'] < 1e-7
    assert record['current_sum_relative'] < 1e-7
