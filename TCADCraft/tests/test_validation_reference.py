"""Explicit numerical evidence, including independently generated Sentaurus PLTs."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.validation import ReferenceComparisonTest, ValidationFramework
from tcad.validation.cross_validation import CrossValidationTest, ModelComparisonTest


def compare(actual, reference, **kwargs):
    return ReferenceComparisonTest(lambda: actual, lambda: reference,
        reference_source='independent prescribed measurements', **kwargs).run()


@pytest.mark.parametrize('field', ['P', 'top_Q_C', 'top_I_A'])
def test_all_declared_fields_participate_in_acceptance(field):
    reference = dict(P=[0., 1., 0.], top_Q_C=[0., 1e-15, 0.], top_I_A=[0., 1e-6, 0.],
                     times_s=[0., 1e-9, 2e-9], converged=True)
    actual = deepcopy(reference)
    assert compare(actual, reference, fields=('P', 'top_Q_C', 'top_I_A')).passed
    actual[field][0] = max(reference[field])*.1
    report = compare(actual, reference, fields=('P', 'top_Q_C', 'top_I_A'))
    assert not report.passed and report.details['field_error_ratios'][field] > 1.


@pytest.mark.parametrize('mutation', ['missing', 'empty', 'nan', 'failed', 'invalid_flag',
    'shape', 'clock_missing', 'clock_different', 'clock_negative', 'clock_repeated',
    'clock_decreasing', 'clock_length', 'clock_matrix', 'snapshot_clock_vector'])
def test_bad_reference_evidence_cannot_pass(mutation):
    actual = dict(phi=[1., 2.], times_s=[0., 1.], converged=True)
    reference = deepcopy(actual)
    if mutation == 'missing': del reference['phi']
    if mutation == 'empty': reference['phi'] = []
    if mutation == 'nan': reference['phi'][0] = np.nan
    if mutation == 'failed': reference['converged'] = False
    if mutation == 'invalid_flag': reference['converged'] = 'true'
    if mutation == 'shape': reference['phi'] = [[1., 2.]]
    if mutation == 'clock_missing': del reference['times_s']
    if mutation == 'clock_different': reference['times_s'] = [0., 2.]
    if mutation == 'clock_negative': actual['times_s'] = reference['times_s'] = [-1., 0.]
    if mutation == 'clock_repeated': actual['times_s'] = reference['times_s'] = [0., 0.]
    if mutation == 'clock_decreasing': actual['times_s'] = reference['times_s'] = [1., 0.]
    if mutation == 'clock_length': actual['times_s'] = reference['times_s'] = [0., 1., 2.]
    if mutation == 'clock_matrix': actual['times_s'] = reference['times_s'] = [[0., 1.]]
    if mutation == 'snapshot_clock_vector': actual['time_s'] = reference['time_s'] = [0., 1.]
    assert not compare(actual, reference).passed


@pytest.mark.parametrize('kwargs', [dict(fields=[]), dict(fields='phi'), dict(fields=('phi','phi')),
    dict(fields=('',)), dict(atol={'wrong': 1}), dict(atol={'phi': True}),
    dict(atol={'phi': -1}), dict(atol={'phi': np.inf}), dict(atol={'phi': '1'}),
    dict(rtol=0), dict(rtol=np.nan), dict(rtol=True), dict(reference_source='')])
def test_invalid_configuration_is_rejected(kwargs):
    params = dict(reference_source='test'); params.update(kwargs)
    with pytest.raises(ValueError):
        ReferenceComparisonTest(lambda: {'phi':[1]}, lambda: {'phi':[1]}, **params)


def test_same_runner_or_same_result_cannot_be_its_own_reference():
    result = {'phi':[1]}
    runner = lambda: result
    with pytest.raises(ValueError):
        ReferenceComparisonTest(runner, runner, reference_source='self')
    assert not ReferenceComparisonTest(lambda: result, lambda: result, reference_source='self').run().passed


@pytest.mark.parametrize('text', ['1e400', '1e-400'])
def test_extended_precision_budget_cannot_silently_overflow_or_underflow(text):
    value = np.longdouble(text)
    assert np.isfinite(value) and value != 0.
    with pytest.raises(ValueError):
        ReferenceComparisonTest(lambda: {'phi':[1]}, lambda: {'phi':[2]},
            atol={'phi':value}, reference_source='test')


def test_absolute_budget_is_explicit_and_in_the_fields_units():
    assert compare({'phi':[1e-13]}, {'phi':[0.]}, atol={'phi':1e-12}).passed
    assert not compare({'phi':[1e-13]}, {'phi':[0.]}).passed


@pytest.mark.parametrize('magnitude', [1e-300, 1., 1e308])
def test_scaling_cannot_hide_a_large_error_or_overflow(magnitude):
    with np.errstate(all='raise'):
        result = compare({'phi':[magnitude]}, {'phi':[-magnitude]}, rtol=.5)
    assert not result.passed and result.details['field_error_ratios']['phi'] == 4.


def test_runner_failure_reports_failed_evidence():
    def broken(): raise RuntimeError('solver failed')
    result = ReferenceComparisonTest(broken, lambda: {'phi':[1]}, reference_source='test').run()
    assert not result.passed and not result.details['numerical_agreement_validated']


def test_framework_exposes_reference_and_explicit_runner_configuration():
    framework = ValidationFramework(lambda: object())
    framework.add_cross_validation_test(runners={'direct':lambda s: {'phi':[1]}, 'iterative':lambda s: {'phi':[1]}})
    framework.add_model_comparison_test('A', 'B', runners={'A':lambda s: {'phi':[1]}, 'B':lambda s: {'phi':[1]}})
    framework.add_reference_comparison_test(lambda: {'phi':[1]}, lambda: {'phi':[1]}, reference_source='specified')
    assert all(r.passed for r in framework.run_all())


@pytest.mark.parametrize('runners', [{}, {'direct':None, 'iterative':None}, {'wrong':lambda s: {}},
                                    {'direct':lambda s: {}, 'iterative':lambda s: {}, 'extra':lambda s: {}}])
def test_incomplete_or_noncallable_algorithm_runners_are_rejected(runners):
    with pytest.raises(ValueError): CrossValidationTest(runners=runners)


@pytest.fixture(scope='module', params=['double_well', 'convex_holdout'])
def commercial_pair(request):
    data = json.loads((Path(__file__).parent/'data/sentaurus_lk_dynamic.json').read_text())
    case = next(c for c in data['cases'] if c['name']==request.param and c['max_step_normalized']==.05)
    times, voltage = np.array(case['times_s']), np.array(case['voltage_V'])
    sim = PyDeviceSimulator(9, 1, 1, data['length_m']/8, 1e-7, 1e-6)
    sim.set_permittivity(np.full(9, data['epsilon_F_m']))
    sim.set_mobility(np.zeros(9), np.zeros(9)); sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9,1e16), np.full(9,1e16))
    sim.set_bandgap(np.full(9,6.)); sim.set_recombination(np.full(9,1e100),np.full(9,1e100))
    sim.set_dirichlet_potential({0:0.,8:0.})
    sim.set_initial_guess(np.zeros(9),np.zeros(9),np.zeros(9))
    sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_params(np.ones(9,dtype=np.int8), case['alpha'],case['beta'])
    sim.set_ferroelectric_gamma(case['rho']); sim.set_ferroelectric_polar_axis(0)
    sim.set_transient_lk_coupled(True); sim.set_gummel_max_iter(80); sim.set_tolerance(1e-12)
    sim.set_transient_dt(float(times[-1])); sim.set_transient_t_final(float(times[-1]))
    sim.set_transient_voltage_waveforms(times,{8:voltage})
    history = sim.solve_transient()
    assert all(s['valid'] for s in history)
    actual = dict(times_s=np.array([s['time_s'] for s in history]), converged=True,
        P=np.array([s['P'].reshape(-1,3)[0,0] for s in history]),
        top_Q_C=np.array([s['electrode_charges_C'][1] for s in history]),
        top_I_A=np.r_[0.,[s['electrode_total_currents_A'][1] for s in history[1:]]])
    reference = dict(times_s=times, P=np.array(case['polarization_C_m2']),
        top_Q_C=np.array(case['top_charge_C']), top_I_A=np.array(case['top_current_A']))
    return actual, reference


def test_new_reference_gate_accepts_real_sentaurus_trajectories(commercial_pair):
    actual, reference = commercial_pair
    result = compare(actual,reference,fields=('P','top_Q_C','top_I_A'),rtol=1e-7)
    assert result.passed and result.details['numerical_agreement_validated']
    assert not result.details['physical_validated']
    assert not result.details['constitutive_equivalence_validated']


@pytest.mark.parametrize('field', ['P','top_Q_C','top_I_A'])
def test_real_commercial_gate_rejects_independent_corruption_of_each_output(commercial_pair,field):
    actual, reference = commercial_pair
    damaged = deepcopy(actual)
    damaged[field][len(damaged[field])//2] += .01*max(abs(reference[field]))
    assert not compare(damaged,reference,fields=('P','top_Q_C','top_I_A'),rtol=1e-7).passed
