"""High-field AlScN-parameter film protocol; commercial agreement is numerical."""
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.validation import ferroelectric_program_read_protocol


def protocol(**kwargs):
    values = dict(reset_voltage_V=-8., ramp_s=.2e-9, reset_hold_s=1e-9,
                  program_hold_s=1e-9, read_hold_s=1e-9)
    values.update(kwargs)
    return ferroelectric_program_read_protocol(np.linspace(0., 8., 15), **values)


def test_target_metadata_does_not_call_zero_bias_an_erase():
    value = Device.alscn_mos2_fefet().metadata['sentaurus_calibration']['protocol']
    assert value['erase_voltage_V'] is None
    assert value['erase_status'] == 'requires_calibration'
    assert value['program_levels_kind'] == 'requested_candidates'
    assert value['validated_levels'] is None and not value['physical_validated']


def test_protocol_measures_reset_and_program_at_the_same_read_voltage():
    value = protocol()
    assert value['candidate_count'] == 15
    assert value['measured_state_count'] is None
    assert not value['physical_validated'] and not value['reset_effect_validated']
    times, voltage = np.array(value['times_s']), np.array(value['drive_voltage_V'])
    assert times[0] == 0. and np.all(np.diff(times) > 0.)
    assert times[-1] == pytest.approx(15*(4*.2+4)*1e-9)
    for event in value['read_events']:
        a = np.flatnonzero(times == event['baseline_read_time_s']).item()
        b = np.flatnonzero(times == event['program_read_time_s']).item()
        assert voltage[a] == voltage[b] == 0.
        assert voltage[a-2] == -8.
        assert voltage[b-2] == event['program_voltage_V']


@pytest.mark.parametrize('change', [dict(reset_voltage_V=None), dict(reset_voltage_V=True),
    dict(ramp_s=0.), dict(ramp_s=-1.), dict(reset_hold_s=np.nan),
    dict(program_hold_s=np.inf), dict(read_hold_s='1'), dict(read_voltage_V=False),
    dict(reset_hold_s=1e308), dict(read_hold_s=1e-300)])
def test_protocol_rejects_invalid_or_unresolvable_clock(change):
    with pytest.raises(ValueError):
        protocol(**change)


@pytest.mark.parametrize('candidates', [[], [[1., 2.]], [np.nan], [True], ['1']])
def test_protocol_rejects_invalid_candidates(candidates):
    with pytest.raises(ValueError):
        ferroelectric_program_read_protocol(candidates, reset_voltage_V=-8.,
            ramp_s=1., reset_hold_s=1., program_hold_s=1., read_hold_s=1.)


def fixture():
    return json.loads((Path(__file__).parent/'data/sentaurus_alscn_protocol.json').read_text())


def tiny_increment_history():
    return json.loads((Path(__file__).parent/'data/sentaurus_alscn_energy_increment.json').read_text())['history']


def test_actual_quad_increment_does_not_fail_only_at_aggregate_export_audit():
    from tcad.postprocess import audit_transient_lk_energy
    report = audit_transient_lk_energy(tiny_increment_history())
    assert report['valid']
    assert report['max_interval_raw_relative_residual'] > .4
    allowance = report['interval_export_rounding_allowances_J'][0]
    assert abs(report['interval_kinetic_residuals_J'][0]) < allowance < 1e-50
    assert not report['energy_balance_validated'] and not report['physical_validated']


@pytest.mark.parametrize('key',['lk_free_energy_increment_J','lk_dissipation_J',
                                'lk_field_work_J','lk_be_correction_J'])
def test_increment_export_allowance_still_rejects_resolvable_energy_corruption(key):
    from tcad.postprocess import audit_transient_lk_energy
    history = tiny_increment_history()
    history[-1][key] += 1e-50
    assert not audit_transient_lk_energy(history)['valid']


@pytest.mark.parametrize('case_index', range(4))
@pytest.mark.parametrize('nodes', [9, 17, 33])
def test_high_field_native_ports_match_raw_commercial_trajectory(case_index, nodes):
    from tcad.validation.ferroelectric_benchmark import run_uniform_film
    data = fixture(); case = data['cases'][case_index]
    history, actual = run_uniform_film(case, data, nodes=nodes)
    for key in ['polarization_C_m2', 'top_charge_C', 'top_current_A']:
        reference = np.array(case[key]); scale = max(abs(reference))
        np.testing.assert_allclose(actual[key], reference, rtol=0., atol=1e-6*scale)
    times = np.array(case['times_s']); current = actual['top_current_A']
    np.testing.assert_allclose(np.dot(np.diff(times), current[1:]),
        case['top_charge_C'][-1]-case['top_charge_C'][0], rtol=1e-6, atol=1e-25)
    for event in data['protocol']['read_events']:
        baseline = np.argmin(abs(times-event['baseline_read_time_s']))
        assert actual['polarization_C_m2'][baseline] < -.99*data['material']['Ps_C_m2']
    # A positive programmed branch remains positive at zero bias: zero is read, not erase.
    assert actual['polarization_C_m2'][-1] > .99*data['material']['Ps_C_m2']


def test_adaptive_high_field_ports_match_raw_commercial_accepted_grid():
    test_high_field_native_ports_match_raw_commercial_trajectory(4, 9)
