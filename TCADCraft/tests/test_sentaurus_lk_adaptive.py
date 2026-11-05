"""Native rejection/step selection, axes and geometry vs raw commercial ports."""
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.postprocess import (audit_transient_lk_error_control,
                              audit_transient_lk_energy,
                              integrate_transient_terminal_history)


def fixture():
    return json.loads((Path(__file__).parent/'data/sentaurus_lk_adaptive.json').read_text())


NAMES = ['010nm', '020nm', '040nm', '110nm', '120nm', '140nm', 'accuracy_0.001', 'accuracy_1e-05']


def run(case, data, count):
    axis = case['axis']
    shape, spacing = [1, 1, 1], [1e-7, 1e-7, 1e-6]
    shape[axis], spacing[axis] = count, case['length_m']/(count-1)
    sim = PyDeviceSimulator(*shape, *spacing)
    sim.set_permittivity(np.full(count, data['epsilon_F_m']))
    sim.set_mobility(np.zeros(count), np.zeros(count))
    sim.set_doping(np.zeros(count))
    sim.set_effective_dos(np.full(count, 1e16), np.full(count, 1e16))
    sim.set_bandgap(np.full(count, 6.))
    sim.set_recombination(np.full(count, 1e100), np.full(count, 1e100))
    sim.set_dirichlet_potential({0: 0., count-1: 0.})
    sim.set_initial_guess(np.zeros(count), np.zeros(count), np.zeros(count))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(np.ones(count, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_gamma(.1)
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_substepping(True, .5)
    sim.set_transient_lk_error_control(True, case['rtol'], case['atol'], 1e-15, 30)
    sim.set_transient_dt(1e-7)
    sim.set_transient_t_final(data['clock_s'][-1])
    sim.set_transient_voltage_waveforms(np.array(data['clock_s']),
        {count-1: -np.array(data['field_V_m'])*case['length_m']})
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-12)
    return sim.solve_transient()


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('count', [9, 17, 33])
def test_adaptive_selection_and_all_accepted_steps_match_sentaurus(name, count):
    data = fixture()
    case = next(c for c in data['cases'] if c['name'] == name)
    history = run(case, data, count)
    assert all(s['valid'] for s in history)
    times = np.array([s['time_s'] for s in history])
    np.testing.assert_allclose(times, case['times_s'], rtol=1e-8, atol=1e-23)
    assert all(knot in times for knot in data['clock_s'])
    audit = audit_transient_lk_error_control(history)
    assert audit['valid'] and audit['rejected_attempts'] > 0
    assert audit_transient_lk_energy(history)['valid']
    polarization = np.array([s['P'].reshape(-1, 3) for s in history])
    expected = np.array(case['polarization_C_m2'])
    scale_p = max(abs(expected))
    np.testing.assert_allclose(polarization[:, :, case['axis']],
        np.broadcast_to(expected[:, None], (len(times), count)), rtol=0., atol=1e-6*scale_p)
    for inactive in set(range(3))-{case['axis']}:
        np.testing.assert_array_equal(polarization[:, :, inactive], 0.)
    q = np.array([s['electrode_charges_C'][1] for s in history])
    np.testing.assert_allclose(q, case['top_charge_C'], rtol=0., atol=1e-6*data['area_m2']*scale_p)
    current = np.r_[0., [s['electrode_total_currents_A'][1] for s in history[1:]]]
    np.testing.assert_allclose(current, case['top_current_A'], rtol=0.,
        atol=1e-6*max(abs(np.array(case['top_current_A']))))
    np.testing.assert_allclose(np.dot(np.diff(times), current[1:]),
        case['top_charge_C'][-1]-case['top_charge_C'][0], rtol=1e-6, atol=1e-25)
    integral = integrate_transient_terminal_history(history)
    assert integral['duration_s'] == data['clock_s'][-1]


def test_commercial_field_preserving_rotation_and_thickness_scaling():
    cases = fixture()['cases'][:6]
    base = cases[0]
    scale_p = max(abs(np.array(base['polarization_C_m2'])))
    scale_i = max(abs(np.array(base['top_current_A'])))
    for case in cases[1:]:
        np.testing.assert_allclose(case['times_s'], base['times_s'], rtol=1e-8, atol=1e-23)
        np.testing.assert_allclose(case['polarization_C_m2'], base['polarization_C_m2'],
            rtol=0., atol=1e-6*scale_p)
        np.testing.assert_allclose(case['top_current_A'], base['top_current_A'],
            rtol=0., atol=1e-6*scale_i)
        np.testing.assert_allclose(np.array(case['voltage_V'])/case['length_m'],
            np.array(base['voltage_V'])/base['length_m'], rtol=0., atol=1e-5)
