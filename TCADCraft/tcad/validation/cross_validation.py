"""Compare explicitly executed numerical paths; absent controls never pass."""
from collections.abc import Mapping
import numpy as np
from .base import BaseValidationTest, ValidationResult


def _tolerance(value):
    array = np.asarray(value)
    if (array.shape != () or array.dtype.kind not in 'iuf' or
            not np.isfinite(array) or not np.isfinite(float(value)) or float(value) <= 0.):
        raise ValueError('tolerance must be a finite positive real scalar')
    return float(value)


def _runners(runners, choices):
    if runners is None:
        return None
    if (not isinstance(runners, Mapping) or set(runners) != set(choices) or
            any(not callable(r) for r in runners.values())):
        raise ValueError(f'runners must provide exactly {choices}, each callable')
    if runners[choices[0]] is runners[choices[1]]:
        raise ValueError('comparison requires distinct runners')
    return dict(runners)


class CrossValidationTest(BaseValidationTest):
    """Compare measured phi from two algorithms on fresh instances.

    Optional runners map algorithm names to runner(simulator) -> result.
    Use them for APIs without legacy setters or to explicitly extract/align
    transient data. Agreement cannot establish independent implementations
    or physical validity. Missing controls fail instead of rerunning defaults.
    """
    _choices = {'linear_solvers': ('direct', 'iterative'),
                'time_integration': ('explicit', 'implicit'),
                'spatial_discretization': ('FDM', 'FEM')}

    def __init__(self, validation_type='linear_solvers', tolerance=.01, *, runners=None):
        super().__init__(f'Cross Validation ({validation_type})')
        if validation_type not in self._choices:
            raise ValueError(f'unknown validation_type: {validation_type}')
        self.validation_type = validation_type
        self.tolerance = _tolerance(tolerance)
        self.runners = _runners(runners, self._choices[validation_type])

    def run(self, device_builder):
        choices = self._choices[self.validation_type]
        details = dict(algorithms=list(choices), physical_validated=False,
                       independent_implementation_validated=False)
        try:
            first, second = device_builder(), device_builder()
            if first is second:
                raise ValueError('builder must return fresh simulator instances')
            if self.runners is not None:
                results = [self.runners[name](sim) for name, sim in zip(choices, (first, second))]
                details['execution'] = 'explicit_runners'
            else:
                results = self._execute(first, second, choices)
                details['execution'] = 'required_simulator_controls'
            error = self._compute_relative_error(*results, 'phi')
            details['error'] = error
            return ValidationResult(self.name, error < self.tolerance,
                f'measured phi relative error: {error:.2e} (tolerance {self.tolerance:.2e})', details)
        except Exception as error:
            return ValidationResult(self.name, False, f'comparison unavailable/failed: {error}', details)

    def _execute(self, first, second, choices):
        method = {'linear_solvers': 'set_linear_solver',
                  'spatial_discretization': 'set_discretization',
                  'time_integration': 'run_transient'}[self.validation_type]
        for sim in (first, second):
            if not callable(getattr(sim, method, None)):
                raise ValueError(f'{method} is unavailable; provide explicit runners')
            if self.validation_type != 'time_integration' and not callable(getattr(sim, 'run', None)):
                raise ValueError('run is unavailable')
        results = []
        for name, sim in zip(choices, (first, second)):
            if self.validation_type == 'time_integration':
                results.append(sim.run_transient(method=name, dt=1e-9, t_final=1e-7))
            else:
                getattr(sim, method)(name)
                results.append(sim.run())
        return results


class ModelComparisonTest(BaseValidationTest):
    """Measured phi comparison with explicit selection, not model equivalence."""
    def __init__(self, model1, model2, tolerance=.05, *, runners=None):
        super().__init__(f'Model Comparison ({model1} vs {model2})')
        if (not isinstance(model1, str) or not isinstance(model2, str) or
                not model1.strip() or not model2.strip() or
                model1.strip().lower() == model2.strip().lower()):
            raise ValueError('provide two distinct nonempty model names')
        self.model1, self.model2 = model1, model2
        self.tolerance = _tolerance(tolerance)
        self.runners = _runners(runners, (model1, model2))

    def run(self, device_builder):
        details = dict(models=[self.model1, self.model2], physical_validated=False,
                       constitutive_equivalence_validated=False)
        try:
            first, second = device_builder(), device_builder()
            if first is second:
                raise ValueError('builder must return fresh simulator instances')
            if self.runners is None:
                for sim in (first, second):
                    if not callable(getattr(sim, 'set_model', None)):
                        raise ValueError('set_model is unavailable; provide explicit runners')
                first.set_model(self.model1)
                second.set_model(self.model2)
                results = first.run(), second.run()
            else:
                results = self.runners[self.model1](first), self.runners[self.model2](second)
            error = self._compute_relative_error(*results, 'phi')
            details['error'] = error
            return ValidationResult(self.name, error < self.tolerance,
                f'measured phi relative error: {error:.2e} (tolerance {self.tolerance:.2e})', details)
        except Exception as error:
            return ValidationResult(self.name, False, f'comparison unavailable/failed: {error}', details)
