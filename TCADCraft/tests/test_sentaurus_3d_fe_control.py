"""Actual 3-D tetrahedral commercial FE control; homogeneous artificial law."""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

OUT=Path(__file__).resolve().parents[1]/'docs/validation/configuration_inheritance_20261017'
spec=importlib.util.spec_from_file_location('fe_3d_comparison',OUT/'compare_3d.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)


@lru_cache(maxsize=2)
def actual(cells):
    raw=json.loads((OUT/'commercial_3d_ep128_m8/raw.json').read_text())
    return comparison.native(cells,raw['time'])[0]


@pytest.mark.parametrize('native_cells',[4,8])
@pytest.mark.parametrize('commercial_cells',[4,8])
def test_actual_3d_fe_fields_polarization_and_ports(native_cells,commercial_cells):
    plan=json.loads((OUT/'commercial_3d_plan.json').read_text())
    raw=json.loads((OUT/f'commercial_3d_ep128_m{commercial_cells}/raw.json').read_text())
    reference=comparison.reference(raw);found=actual(native_cells)
    for key in ['phi','ex','px','charge','current']:
        error=np.max(abs(found[key]-reference[key]))/np.max(abs(reference[key]))
        assert error<=plan['relative_budget'],(key,error)
    for data in [reference,found]:
        assert max(np.max(abs(data[k])) for k in ['ey','ez'])<=plan['zero_field_absolute_budget_V_m']
        assert max(np.max(abs(data[k])) for k in ['py','pz'])<=plan['zero_polarization_absolute_budget_C_m2']
        for key in ['charge','current']:
            assert np.max(abs(data[key].sum(axis=1)))<np.max(abs(data[key]))*1e-8


def test_3d_commercial_reference_refines_within_fixed_budget():
    plan=json.loads((OUT/'commercial_3d_plan.json').read_text())
    refs=[comparison.reference(json.loads((OUT/f'commercial_3d_ep128_m{n}/raw.json').read_text())) for n in [4,8]]
    for key in ['phi','ex','px','charge','current']:
        assert np.max(abs(refs[0][key]-refs[1][key]))/np.max(abs(refs[1][key]))<=plan['reference_relative_budget']
    assert not plan['physical_validated']
