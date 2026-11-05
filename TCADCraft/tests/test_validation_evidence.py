"""Validation must compare measured fields and execute distinct requested paths."""
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.validation.base import BaseValidationTest
from tcad.validation.cross_validation import CrossValidationTest, ModelComparisonTest
from tcad.validation.limiting_cases import LimitingCaseTest


class Check(BaseValidationTest):
    def run(self, builder):
        raise NotImplementedError


class NoControls:
    def run(self):
        return dict(phi=np.ones(2), converged=True)


@pytest.mark.parametrize('kind', ['linear_solvers', 'time_integration', 'spatial_discretization'])
def test_no_algorithm_switch_cannot_pass_cross_validation(kind):
    result = CrossValidationTest(kind).run(NoControls)
    assert not result.passed


def test_no_model_switch_cannot_pass_model_comparison():
    assert not ModelComparisonTest('nls', 'landau_khalatnikov').run(NoControls).passed


@pytest.mark.parametrize('kind', ['nls_to_lk', 'preisach_to_lk'])
def test_unsupported_constitutive_equivalence_does_not_run_or_pass(kind):
    def forbidden():
        pytest.fail('an unspecified constitutive limit must fail before simulation')
    result = LimitingCaseTest(kind).run(forbidden)
    assert not result.passed
    assert result.details['unsupported'] is True
    assert result.details['physical_validated'] is False


@pytest.mark.parametrize('method', ['_compute_relative_error', '_compute_l2_error'])
@pytest.mark.parametrize('left,right', [({}, {}), ({'phi': []}, {'phi': []}),
    ({'phi': [1, 2]}, {'phi': [[1, 2]]}), ({'phi': [1, 2]}, {'phi': [1]}),
    ({'phi': [np.nan]}, {'phi': [0]}), ({'phi': [np.inf]}, {'phi': [0]}),
    ({'phi': [True]}, {'phi': [True]}), ({'phi': ['1']}, {'phi': ['1']}),
    ({'phi': [1j]}, {'phi': [1j]}),
    ({'phi': [1], 'converged': False}, {'phi': [1]}),
    ({'phi': [1]}, {'phi': [1], 'valid': False}),
    ({'phi': [1], 'converged': 1}, {'phi': [1]}),
    ([{'phi': [1]}], [{'phi': [1]}])])
def test_bad_measurement_never_becomes_zero_error(method, left, right):
    with pytest.raises(ValueError):
        getattr(Check('check'), method)(left, right)


def test_tiny_real_difference_is_not_hidden_by_a_fixed_absolute_floor():
    error = Check('check')._compute_relative_error({'P': [1e-100]}, {'P': [2e-100]}, 'P')
    assert error == pytest.approx(1.)


@pytest.mark.parametrize('method', ['_compute_relative_error', '_compute_l2_error'])
def test_opposite_extreme_values_are_compared_without_intermediate_overflow(method):
    with np.errstate(all='raise'):
        error = getattr(Check('check'), method)({'phi': [1e308]}, {'phi': [-1e308]})
    if method.endswith('relative_error'):
        assert error == 2.
    else:
        assert np.isinf(error)


def test_object_and_mapping_results_can_be_compared():
    check = Check('check')
    assert check._compute_relative_error(SimpleNamespace(phi=np.array([1., 2.])), {'phi': [1., 2.]}) == 0.
    assert check._compute_l2_error({'phi': [1., 2.]}, {'phi': [2., 4.]}) == pytest.approx(np.sqrt(2.5))


@pytest.mark.parametrize('value', [True, 0., -1., np.nan, np.inf, '0.1', np.array([.1])])
def test_invalid_tolerance_is_rejected(value):
    with pytest.raises(ValueError):
        CrossValidationTest(tolerance=value)


class Controlled:
    def __init__(self):
        self.choice = None
    def set_linear_solver(self, choice):
        self.choice = choice
    def set_discretization(self, choice):
        self.choice = choice
    def set_model(self, choice):
        self.choice = choice
    def run(self):
        return dict(phi=[1., 2.], converged=True)


@pytest.mark.parametrize('kind,choices', [('linear_solvers', ['direct', 'iterative']),
                                         ('spatial_discretization', ['FDM', 'FEM'])])
def test_requested_controls_execute_on_fresh_instances(kind, choices):
    instances = []
    def builder():
        sim = Controlled(); instances.append(sim); return sim
    result = CrossValidationTest(kind).run(builder)
    assert result.passed
    assert [s.choice for s in instances] == choices
    assert result.details['physical_validated'] is False


def test_reused_builder_instance_is_rejected():
    sim = Controlled()
    assert not CrossValidationTest().run(lambda: sim).passed


@pytest.mark.parametrize('models', [('nls', 'nls'), ('NLS', 'nls'), (' nls ', 'nls')])
def test_identical_model_names_are_rejected(models):
    with pytest.raises(ValueError):
        ModelComparisonTest(*models)


def test_explicit_runners_support_the_actual_native_transient_api():
    calls = []
    def explicit(sim):
        calls.append(('explicit', id(sim))); return {'phi': [1., 2.], 'converged': True}
    def implicit(sim):
        calls.append(('implicit', id(sim))); return {'phi': [1., 2.], 'converged': True}
    result = CrossValidationTest('time_integration', runners={'explicit': explicit, 'implicit': implicit}).run(NoControls)
    assert result.passed and calls[0][0] == 'explicit' and calls[1][0] == 'implicit'
    assert calls[0][1] != calls[1][1]


@pytest.mark.parametrize('mutation', ['missing', 'failed', 'mismatch', 'different_time'])
def test_runner_outputs_must_be_valid_comparable_evidence(mutation):
    def a(sim): return {'phi': [1., 2.], 'converged': True, 'time_s': 1.}
    def b(sim):
        if mutation == 'missing': return {}
        if mutation == 'failed': return {'phi': [1., 2.], 'valid': False}
        if mutation == 'mismatch': return {'phi': [1., 9.], 'time_s': 1.}
        return {'phi': [1., 2.], 'time_s': 2.}
    assert not CrossValidationTest(runners={'direct': a, 'iterative': b}).run(NoControls).passed


@pytest.mark.parametrize('kind', ['parameter', 'time'])
def test_convergence_reports_incomparable_data_as_failure(kind):
    from tcad.validation.convergence import TimeConvergenceTest, ParameterConvergenceTest
    class MissingFields:
        def run(self): return {}
        def run_transient(self, **kwargs): return {}
    if kind == 'time':
        check = TimeConvergenceTest(dt_values=[1e-9, 5e-10, 2.5e-10])
    else:
        check = ParameterConvergenceTest('parameter', [1, 2])
    assert not check.run(lambda **kwargs: MissingFields()).passed
