"""Replay a fixed concave polygon helper against actual independent SDevice references."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.parametrize('cells', [16, 128])
def test_prism_dielectric_contrast_keeps_coarse_rejection_and_fine_acceptance(cells):
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / 'tests/data/sentaurus_prism_cut.json').read_text())
    helper = root / fixture['reference_helper']
    # The deliberately fixed replay helper is part of this reference's scope.
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == fixture['reference_helper_sha256']
    spec = importlib.util.spec_from_file_location('fixed_prism_dielectric', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = module.native(cells)
    baseline = .2 * np.array(fixture['points_um'])[:, 0]
    induced = np.array(native['sampled_phi_V']) - baseline
    gain = native['capacitance_F'] / (8.854187817e-12 * 3.9 * 1e-6) - 1
    errors = []
    for ref in fixture['commercial']:
        signal = np.array(ref['induced_phi_V'])
        errors += [float(max(abs(induced - signal)) / max(abs(signal))),
                   abs(gain / ref['capacitance_gain'] - 1)]
    accepted = max(errors) <= fixture['relative_contrast_budget']
    assert bool(accepted) == fixture['expected_native_acceptance'][str(cells)]
    assert bool(accepted) == (cells == 128)
    assert native['independent_gauss_relative_error'] < 1e-8
    assert native['independent_equation_relative_error'] < 1e-8
    assert native['independent_graph_energy_relative_error'] < 1e-8
