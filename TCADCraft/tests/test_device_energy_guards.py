"""Energy gates must resolve nanoscale errors without hiding them in baselines."""
from copy import deepcopy
import sys

import numpy as np
import pytest

from tcad.postprocess import audit_complete_device_energy, solver_energy_history
from tcad.postprocess.device_energy import DEFAULT_COMPONENTS


def ledger(scale=1e-20):
    before = {name: scale for name in DEFAULT_COMPONENTS}
    after = {name: 2 * scale for name in DEFAULT_COMPONENTS}
    net = {name: scale for name in DEFAULT_COMPONENTS}
    return [{'energy_storage_J': before},
            {'energy_storage_J': after, 'interval_net_energy_J': net}]


@pytest.mark.parametrize('scale', [1e-30, 1e-20, 1., 1e20])
def test_same_relative_error_is_rejected_at_every_energy_scale(scale):
    history = ledger(scale)
    assert audit_complete_device_energy(history)['valid']
    history[1]['interval_net_energy_J']['carrier'] *= 1.01
    assert not audit_complete_device_energy(history)['valid']


def test_large_thermal_baseline_cannot_hide_quantum_error():
    history = ledger()
    for snapshot in history:
        snapshot['energy_storage_J']['thermal'] = 1e10
    history[1]['interval_net_energy_J']['thermal'] = 0.
    history[1]['interval_net_energy_J']['quantum'] *= 1.01
    result = audit_complete_device_energy(history)
    assert not result['valid']
    assert result['interval_tolerances_J'][0]['quantum'] < 1e-27


def test_later_large_interval_cannot_hide_earlier_error():
    history = ledger()
    history[1]['interval_net_energy_J']['trap'] *= 1.01
    history.append({'energy_storage_J': {n: 1. for n in DEFAULT_COMPONENTS},
                    'interval_net_energy_J': {n: 1. for n in DEFAULT_COMPONENTS}})
    assert not audit_complete_device_energy(history)['valid']


def test_cancelling_component_errors_are_rejected():
    history = ledger()
    history[1]['interval_net_energy_J']['carrier'] = 0.
    history[1]['interval_net_energy_J']['trap'] *= 2
    result = audit_complete_device_energy(history)
    assert abs(result['interval_residuals_J'][0]['total']) < 1e-35
    assert not result['valid']


def test_zero_energy_passes_only_storage_consistency():
    result = audit_complete_device_energy(ledger(0.))
    assert result['valid'] and result['storage_consistency_validated']
    assert not result['energy_balance_validated']
    assert not result['complete_device_energy'] and not result['physical_validated']


@pytest.mark.parametrize('bad', [True, '1e-20', 1e-20+0j, None, [1e-20], np.nan, np.inf])
def test_nonreal_or_nonfinite_storage_is_rejected(bad):
    history = ledger()
    history[1]['energy_storage_J']['carrier'] = bad
    with pytest.raises(ValueError):
        audit_complete_device_energy(history)


@pytest.mark.parametrize('bad', [True, '1e-8', np.inf, -1., 1.])
def test_invalid_relative_budget_is_rejected(bad):
    with pytest.raises(ValueError):
        audit_complete_device_energy(ledger(), rtol=bad)


@pytest.mark.parametrize('bad', [True, '0', -1., np.nan])
def test_invalid_absolute_budget_is_rejected(bad):
    with pytest.raises(ValueError):
        audit_complete_device_energy(ledger(), atol_J=bad)


@pytest.mark.parametrize('names', [(['carrier'],), ('carrier', 'carrier'), ('carrier', '')])
def test_invalid_components_raise_value_error(names):
    with pytest.raises(ValueError):
        audit_complete_device_energy(ledger(), components=names)


def test_aggregate_overflow_is_rejected():
    history = ledger(sys.float_info.max / 4)
    history[1]['energy_storage_J'] = {n: sys.float_info.max for n in DEFAULT_COMPONENTS}
    history[1]['interval_net_energy_J'] = {n: 0. for n in DEFAULT_COMPONENTS}
    with pytest.raises(ValueError):
        audit_complete_device_energy(history)


def test_storage_subtraction_roundoff_is_explicit_and_small():
    history = ledger()
    history[0]['energy_storage_J']['thermal'] = 1.
    history[1]['energy_storage_J']['thermal'] = 1. + 1e-12
    history[1]['interval_net_energy_J']['thermal'] = 1e-12
    result = audit_complete_device_energy(history)
    assert result['valid']
    assert result['interval_roundoff_allowance_J'][0]['thermal'] < 1e-15


def test_adapter_requires_boolean_option_and_real_fields():
    from test_native_energy_adapter import report
    with pytest.raises(ValueError):
        solver_energy_history(report(), include_electrostatic='false')
    bad = deepcopy(report())
    bad['energy_before_J']['quantum_J'] = True
    with pytest.raises(ValueError):
        solver_energy_history(bad)
