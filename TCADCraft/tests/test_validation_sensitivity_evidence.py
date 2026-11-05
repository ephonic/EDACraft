"""A sensitivity claim needs measured responses and complete controlled sweeps."""
from types import SimpleNamespace
import numpy as np
import pytest
from tcad.validation.sensitivity import SensitivityTest, ParameterImportanceTest


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('output', [{}, {'phi': [np.nan]}, {'phi': [1.], 'valid': False}])
def test_legacy_unconfigured_sweep_cannot_pass(kind, output):
    check = (SensitivityTest('x', (0., 1.)) if kind == 'sensitivity' else
             ParameterImportanceTest(['x'], {'x': (0., 1.)}))
    calls = []
    def builder(**params):
        calls.append(params)
        return SimpleNamespace(run=lambda: SimpleNamespace(**output))
    result = check.run(builder)
    assert not result.passed
    assert not calls, 'no default proxy simulations without a measurement contract'


def test_importance_cannot_swallow_all_simulation_failures():
    def builder(**params):
        raise RuntimeError('solver failed')
    assert not ParameterImportanceTest(['x'], {'x': (0., 1.)}).run(builder).passed


def sensitivity(**kwargs):
    config = dict(num_points=5, field='response', response_scale=1., protocol='fixed scalar response in SI',
                  tolerance=.6)
    config.update(kwargs)
    return SensitivityTest('x', (0., 1.), **config)


def importance(**kwargs):
    config = dict(num_samples=5, field='response', response_scale=1., baseline={'x': .5, 'y': .5},
                  protocol='fixed geometry and history, signed scalar in SI')
    config.update(kwargs)
    return ParameterImportanceTest(['x', 'y'], {'x': (0., 1.), 'y': (0., 1.)}, **config)


def builder_for(function, alter=None, calls=None):
    def builder(**params):
        if calls is not None: calls.append(dict(params))
        def run():
            result = dict(response=function(**params), parameters=dict(params), valid=True, time_s=2.)
            if alter: alter(result, params)
            return result
        return SimpleNamespace(run=run)
    return builder


@pytest.mark.parametrize('offset', [-10., 0., 10.])
@pytest.mark.parametrize('sign', [-1., 1.])
def test_signed_response_and_offsets_do_not_hide_sensitivity(offset, sign):
    report = sensitivity().run(builder_for(lambda x: offset+sign*x))
    assert report.passed, report.message
    assert report.details['normalized_first_differences'] == [sign*.25]*4
    assert not report.details['physical_validated']
    assert not report.details['parameter_application_verified']
    assert not report.details['derivative_accuracy_validated']


@pytest.mark.parametrize('offset', [-10., 0., 10.])
def test_oat_ranking_uses_fixed_baseline_not_mean_of_signed_metric(offset):
    calls = []
    report = importance().run(builder_for(lambda x, y: offset+2*x-4*y, calls=calls))
    assert report.passed, report.message
    assert report.details['sorted_params'][0][0] == 'y'
    assert report.details['sensitivities']['y'] == pytest.approx(2*report.details['sensitivities']['x'])
    assert len(calls) == 11
    assert calls[0] == {'x': .5, 'y': .5}
    assert all(p['y'] == .5 for p in calls[1:6])
    assert all(p['x'] == .5 for p in calls[6:])


@pytest.mark.parametrize('scale', [1e-300, 1e-100, 1., 1e100, 1e300])
def test_response_units_do_not_change_regularity_or_importance(scale):
    a = sensitivity(response_scale=scale).run(builder_for(lambda x: scale*x))
    b = importance(response_scale=scale).run(builder_for(lambda x, y: scale*(2*x-4*y)))
    assert a.passed and b.passed
    np.testing.assert_allclose(a.details['normalized_first_differences'], .25, rtol=1e-14)
    assert b.details['sensitivities']['y'] == pytest.approx(np.sqrt(2.))


def test_parameter_unit_conversion_keeps_oat_scores():
    one = importance().run(builder_for(lambda x, y: x+2*y))
    two = ParameterImportanceTest(['x', 'y'], {'x': (0., 1e-9), 'y': (0., 1e9)}, num_samples=5,
        field='response', response_scale=1., baseline={'x': .5e-9, 'y': .5e9}, protocol='converted units'
        ).run(builder_for(lambda x, y: x/1e-9+2*y/1e9))
    assert two.passed
    assert two.details['sensitivities'] == pytest.approx(one.details['sensitivities'])


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf, True, '1', 1+2j, [], [1.], [[1.]]])
def test_invalid_or_unreduced_metrics_fail(kind, bad):
    check = sensitivity() if kind == 'sensitivity' else importance()
    report = check.run(builder_for(lambda **p: bad))
    assert not report.passed


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('mutation', [
    lambda r, p: r.pop('response'),
    lambda r, p: r.update(valid=False),
    lambda r, p: r.update(converged=False),
    lambda r, p: r.update(valid=1),
    lambda r, p: r.pop('parameters'),
    lambda r, p: r.update(parameters={}),
    lambda r, p: r['parameters'].update(x=np.nan),
    lambda r, p: r['parameters'].update(x=True),
    lambda r, p: r['parameters'].update(x=p['x']+.01),
    lambda r, p: r.update(time_s=-1.),
    lambda r, p: r.update(time_s=[1.]),
    lambda r, p: r.update(time_s=np.nan),
    lambda r, p: r.update(times_s=[0., 1.]),
])
def test_missing_fields_failure_flags_and_incorrect_controls_never_pass(kind, mutation):
    check = sensitivity() if kind == 'sensitivity' else importance()
    report = check.run(builder_for(lambda **p: sum(p.values()), mutation))
    assert not report.passed
    assert not report.details['numerical_sweep_validated']
    if kind == 'importance':
        assert not report.details['ranking_validated']
        assert not report.details['sorted_params']


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('clock_change', ['different', 'missing'])
def test_snapshot_clocks_cannot_change_across_samples(kind, clock_change):
    def alter(result, params):
        if params['x'] == 1.:
            if clock_change == 'missing': result.pop('time_s')
            else: result['time_s'] = 3.
    check = sensitivity() if kind == 'sensitivity' else importance()
    assert not check.run(builder_for(lambda **p: sum(p.values()), alter)).passed


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
def test_middle_sample_failure_aborts_without_partial_ranking(kind):
    calls = []
    def function(**params):
        calls.append(params['x'])
        if params['x'] == .25: raise RuntimeError('genuine failed sample')
        return sum(params.values())
    check = sensitivity() if kind == 'sensitivity' else importance()
    report = check.run(builder_for(function))
    assert not report.passed and 'genuine failed sample' in report.message
    assert calls[-1] == .25
    if kind == 'importance': assert report.details['sensitivities'] == {}


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('alias', ['simulator', 'result'])
def test_reused_instances_and_results_are_rejected(kind, alias):
    shared = dict(response=1., parameters={})
    sim = SimpleNamespace()
    def builder(**params):
        def run():
            shared.update(response=sum(params.values()), parameters=params)
            return shared
        if alias == 'simulator':
            sim.run = lambda: dict(response=sum(params.values()), parameters=params)
            return sim
        return SimpleNamespace(run=run)
    check = sensitivity() if kind == 'sensitivity' else importance()
    assert not check.run(builder).passed


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
@pytest.mark.parametrize('constant', [-1., 0., 1.])
def test_constant_response_is_inconclusive(kind, constant):
    check = sensitivity() if kind == 'sensitivity' else importance()
    result = check.run(builder_for(lambda **p: constant))
    assert not result.passed and result.details['inconclusive']


def test_insensitive_parameter_scores_zero_when_other_parameters_respond():
    result = importance().run(builder_for(lambda x, y: x))
    assert result.passed and result.details['sensitivities']['y'] == 0.


@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
def test_detection_floor_cannot_be_bypassed_by_nonzero_roundoff(kind):
    check = sensitivity(min_response=.01) if kind == 'sensitivity' else importance(min_response=.01)
    assert not check.run(builder_for(lambda **p: 1e-6*sum(p.values()))).passed


def test_jump_in_five_point_sweep_is_detected_even_with_large_offset():
    report = sensitivity(tolerance=.1).run(builder_for(lambda x: 1e6+(1. if x >= .5 else 0.)))
    assert not report.passed
    assert report.details['jump_violation'] == 1.
    assert report.details['smoothness_violation'] == 1.


def test_regularity_switches_are_executed_independently():
    builder = builder_for(lambda x: x)
    assert sensitivity(check_no_jumps=False, tolerance=1e-12).run(builder).passed
    assert not sensitivity(check_smoothness=False, tolerance=.1).run(builder).passed


@pytest.mark.parametrize('kwargs', [
    {'num_points': 0}, {'num_points': 2}, {'num_points': True}, {'num_points': 3.5},
    {'field': ''}, {'field': 'time_s'}, {'field': 1}, {'protocol': ''}, {'runner': 1},
    {'response_scale': 0.}, {'response_scale': -1.}, {'response_scale': np.nan},
    {'response_scale': True}, {'response_scale': [1.]}, {'min_response': -1.},
    {'min_response': np.inf}, {'baseline': []}, {'baseline': {'fixed': True}},
    {'tolerance': 0.}, {'tolerance': np.inf}, {'tolerance': True},
    {'check_smoothness': False, 'check_no_jumps': False}, {'check_no_jumps': 1},
])
def test_invalid_sensitivity_configuration_raises(kwargs):
    with pytest.raises(ValueError): sensitivity(**kwargs)


@pytest.mark.parametrize('bounds', [(1., 0.), (0., 0.), (0., np.nan), (True, 2.), ('0', '1'), (0.,), (0., 1., 2.)])
def test_invalid_parameter_ranges_raise(bounds):
    with pytest.raises(ValueError): SensitivityTest('x', bounds)


@pytest.mark.parametrize('names,ranges', [([], {}), (['x', 'x'], {'x': (0., 1.)}),
    (['x'], {}), (['x'], {'x': (0., 1.), 'z': (0., 1.)}), ([''], {'': (0., 1.)}),
    (['x', 1], {'x': (0., 1.), 1: (0., 1.)})])
def test_importance_names_and_ranges_must_be_complete(names, ranges):
    with pytest.raises(ValueError): ParameterImportanceTest(names, ranges)


@pytest.mark.parametrize('baseline', [{}, {'x': .5}, {'x': -1., 'y': .5}, {'x': .5, 'y': np.inf}])
def test_oat_requires_a_valid_common_baseline(baseline):
    with pytest.raises(ValueError): importance(baseline=baseline)


@pytest.mark.parametrize('key', ['field', 'response_scale', 'protocol', 'baseline'])
def test_unconfigured_importance_does_not_run_any_model(key):
    calls = []
    check = importance(**{key: None})
    assert not check.run(builder_for(lambda **p: 1., calls=calls)).passed
    assert not calls


def test_unrepresentable_or_duplicate_grid_is_rejected():
    with pytest.raises(ValueError): SensitivityTest('x', (1., np.nextafter(1., 2.)), num_points=5)


def test_opposite_huge_metrics_normalize_before_overflowing_subtraction():
    result = SensitivityTest('x', (-1., 1.), num_points=5, field='response', response_scale=1e308,
        protocol='extreme finite test', tolerance=.6).run(builder_for(lambda x: x*1e308))
    assert result.passed, result.message
    assert result.details['normalized_response_range'] == 2.


def test_large_finite_rms_does_not_overflow_before_dividing_by_sample_count():
    result = importance().run(builder_for(lambda x, y: 1e308 if x != .5 else 0.))
    assert result.passed, result.message
    assert np.isfinite(result.details['sensitivities']['x'])
    assert result.details['sensitivities']['x'] == pytest.approx(np.sqrt(.8)*1e308)


def test_native_runner_and_framework_forward_all_controls():
    from tcad.validation import ValidationFramework
    def build(**params):
        return SimpleNamespace(solve=lambda: dict(response=sum(params.values()), parameters=params))
    framework = ValidationFramework(build)
    options = dict(field='response', response_scale=1., protocol='native runner', runner=lambda sim: sim.solve())
    framework.add_sensitivity_test('x', (0., 1.), num_points=5, tolerance=.6, **options)
    framework.add_parameter_importance_test(['x'], {'x': (0., 1.)}, num_samples=5, baseline={'x': .5}, **options)
    assert all(result.passed for result in framework.run_all())


def native_poisson_check(axis, kind='sensitivity', corrupt=False):
    from tcad.core import PyDeviceSimulator
    shape = [3, 3, 3]; shape[axis] = 9
    count = int(np.prod(shape)); spacing = 1e-8; length = 8*spacing
    z, y, x = np.indices(tuple(shape[::-1])); coordinate = (x, y, z)[axis].reshape(-1)*spacing
    eps, charge, k = 8.854187817e-12*11.7, 1.602176634e-19, np.pi/length
    gain = (k*spacing)**2/(4*np.sin(k*spacing/2)**2)
    analytic, measured = [], []
    def builder(amplitude, offset):
        sim = PyDeviceSimulator(*shape, spacing, spacing, spacing)
        sim.set_permittivity(np.full(count, eps)); sim.set_mobility(np.zeros(count), np.zeros(count))
        sim.set_doping(eps*k*k*amplitude/charge*np.sin(k*coordinate))
        sim.set_effective_dos(np.full(count, 1e16), np.full(count, 1e16)); sim.set_bandgap(np.full(count, 6.))
        sim.set_recombination(np.full(count, 1e100), np.full(count, 1e100))
        boundary = np.flatnonzero((coordinate == 0.) | (coordinate == length))
        sim.set_dirichlet_potential({int(i): offset for i in boundary})
        sim.set_electron_bc({int(i): 0. for i in boundary}); sim.set_hole_bc({int(i): 0. for i in boundary})
        sim.set_initial_guess(np.full(count, offset), np.zeros(count), np.zeros(count))
        sim.set_gummel_max_iter(100); sim.set_tolerance(1e-12)
        def run():
            actual = sim.solve(); assert actual['converged']
            expected = offset+amplitude*np.sin(k*coordinate)*gain
            np.testing.assert_allclose(actual['phi'], expected, rtol=1e-8, atol=1e-12)
            center = int(np.argmin(abs(coordinate-length/2)))
            value = float(actual['phi'][center]); analytic.append(float(expected[center])); measured.append(value)
            if corrupt and amplitude == .002: value += .0001
            return dict(response=value, parameters=dict(amplitude=amplitude, offset=offset), valid=True)
        return SimpleNamespace(run=run, native=sim)
    options = dict(field='response', response_scale=.001, protocol='3D sine-source Poisson; midpoint phi [V], fixed geometry')
    if kind == 'sensitivity':
        check = SensitivityTest('amplitude', (.001, .003), num_points=5, baseline={'offset': 0.},
            check_no_jumps=False, tolerance=1e-7, **options)
    else:
        check = ParameterImportanceTest(['amplitude', 'offset'],
            {'amplitude': (.001, .003), 'offset': (-.001, .001)}, num_samples=5,
            baseline={'amplitude': .002, 'offset': 0.}, **options)
    report = check.run(builder)
    report.details['analytic_metric_max_error_V'] = max(abs(a-b) for a, b in zip(analytic, measured))
    if kind == 'importance' and report.passed:
        assert report.details['sensitivities']['amplitude']/report.details['sensitivities']['offset'] == pytest.approx(gain, rel=1e-8)
    return report


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
def test_actual_native_3d_sweeps_match_discrete_analytic_response(axis, kind):
    report = native_poisson_check(axis, kind)
    assert report.passed, report.message


@pytest.mark.parametrize('axis', [0, 1, 2])
def test_corrupted_native_midpoint_breaks_smoothness(axis):
    assert not native_poisson_check(axis, corrupt=True).passed


import importlib.util
import json
from pathlib import Path
from tcad.validation import ReferenceComparisonTest

COMMERCIAL = json.loads((Path(__file__).parent/'data/sentaurus_lk_sensitivity.json').read_text())
_spec = importlib.util.spec_from_file_location('lk_symmetry_helpers', Path(__file__).with_name('test_validation_symmetry_evidence.py'))
_lk = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_lk)


def lk_measurement(case, engine):
    if engine == 'native':
        values = _lk.run_native_lk(_lk.build_native_lk(case), dict(case, positive=case), 'positive')
        return values
    return dict(P=np.array(case['sentaurus_P_C_m2']), Q=np.array(case['sentaurus_top_Q_C']),
        I=np.array(case['sentaurus_interval_I_A']), times_s=np.array(case['times_s']),
        interval_times_s=np.array(case['times_s'][1:]), valid=True)


def commercial_sweep(engine, field='P', kind='sensitivity', damage=None):
    def builder(rho, alpha, beta):
        case = next(c for c in COMMERCIAL['cases'] if c['rho'] == rho)
        assert case['alpha'] == alpha and case['beta'] == beta
        def run():
            measurement = lk_measurement(case, engine)
            value = float(measurement[field][-1])
            if damage and rho == .2: value += damage
            return dict(response=value, parameters=dict(rho=rho, alpha=alpha, beta=beta),
                        time_s=float(measurement['times_s'][-1]), valid=True)
        return SimpleNamespace(run=run)
    scale = {'P': .01, 'Q': 1e-15, 'I': 1e-6}[field]
    options = dict(field='response', response_scale=scale, baseline={'rho': .2, 'alpha': 2e8, 'beta': 3e12},
                   protocol='fixed 40 nm LK pulse, zero initial P; measured endpoint at 4 ns; vary damping only')
    if kind == 'sensitivity':
        check = SensitivityTest('rho', (.1, .3), num_points=5, tolerance=.2, **options)
    else:
        check = ParameterImportanceTest(['rho'], {'rho': (.1, .3)}, num_samples=5, **options)
    return check.run(builder)


@pytest.mark.parametrize('case', COMMERCIAL['cases'], ids=lambda c: c['name'])
def test_fresh_native_lk_matches_all_new_commercial_trajectories(case):
    native, commercial = lk_measurement(case, 'native'), lk_measurement(case, 'sentaurus')
    report = ReferenceComparisonTest(lambda: native, lambda: commercial, fields=('P', 'Q'), rtol=1e-7,
        reference_source='five new raw Sentaurus W-2024.09 damping runs').run()
    assert report.passed, report.message
    report = ReferenceComparisonTest(lambda: dict(I=native['I'], times_s=native['interval_times_s']),
        lambda: dict(I=commercial['I'], times_s=commercial['interval_times_s']), fields=('I',), rtol=1e-7,
        reference_source='new noninitial BE interval currents').run()
    assert report.passed, report.message


@pytest.mark.parametrize('field', ['P', 'Q', 'I'])
@pytest.mark.parametrize('kind', ['sensitivity', 'importance'])
def test_new_commercial_and_fresh_native_parameter_responses_agree(field, kind):
    actual = commercial_sweep('native', field, kind)
    reference = commercial_sweep('sentaurus', field, kind)
    assert actual.passed and reference.passed, actual.message+'; '+reference.message
    if kind == 'sensitivity':
        np.testing.assert_allclose(actual.details['normalized_first_differences'],
            reference.details['normalized_first_differences'], rtol=1e-7, atol=1e-8)
    else:
        assert actual.details['sensitivities']['rho'] == pytest.approx(reference.details['sensitivities']['rho'], rel=1e-7)


@pytest.mark.parametrize('engine', ['sentaurus', 'native'])
def test_corrupted_commercial_or_native_parameter_sample_breaks_regularity(engine):
    assert not commercial_sweep(engine, damage=.01).passed


def test_damping_endpoint_is_nonmonotonic_in_both_engines():
    # A pulse-history response cannot be replaced by an assumed monotonic trend.
    for engine in ('sentaurus', 'native'):
        report = commercial_sweep(engine)
        assert report.passed
        shifts = report.details['normalized_first_differences']
        assert any(v > 0 for v in shifts) and any(v < 0 for v in shifts)


def test_grid_preserves_correctly_rounded_controls_for_decimal_endpoints():
    assert SensitivityTest('rho', (.1, .3), num_points=5).values == [.1, .15, .2, .25, .3]
