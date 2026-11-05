"""Controlled scalar-response sweeps; no implicit electrical proxy or physics claim."""
import inspect
import math
from collections.abc import Mapping
from fractions import Fraction

import numpy as np

from .base import BaseValidationTest, ValidationResult, measured_field, _get, _MISSING
from .convergence import _callable, _fresh, _record
from .cross_validation import _tolerance


_RESERVED = {'time_s', 'times_s', 'valid', 'converged', 'parameters'}


def _name(value):
    if not isinstance(value, str) or not value.strip() or value in _RESERVED:
        raise ValueError('provide a nonempty measurement/parameter name, not a control field')
    return value


def _scalar(value):
    array = measured_field({'value': value}, 'value')
    if array.shape != ():
        raise ValueError('require a finite real scalar; extract a measurement explicitly')
    return float(array)


def _range(values):
    array = np.asarray(values)
    if array.shape != (2,) or array.dtype.kind not in 'iuf':
        raise ValueError('parameter range must contain two finite real bounds')
    low, high = (_scalar(value) for value in values)
    if not low < high:
        raise ValueError('parameter range must be strictly increasing')
    return low, high


def _count(value):
    if (not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_))
            or value < 3):
        raise ValueError('at least three integer sample points are required')
    return int(value)


def _parameters(values):
    if not isinstance(values, Mapping):
        raise ValueError('baseline/parameters must be an explicit scalar mapping')
    return {_name(key): _scalar(value) for key, value in values.items()}


def _grid(bounds, count):
    # Exact interpolation avoids overflow and intermediate rounding of controls.
    low, high = bounds
    values = [float((Fraction(low)*(count-1-i)+Fraction(high)*i)/(count-1)) for i in range(count)]
    values[0], values[-1] = low, high
    if not all(math.isfinite(v) for v in values) or not all(a < b for a, b in zip(values, values[1:])):
        raise ValueError('sampling grid must have distinct representable parameter values')
    return values


def _difference(a, b, scale):
    # Exact float ratios avoid overflow before normalization and a unit floor.
    exact = (Fraction(a)-Fraction(b))/Fraction(scale)
    value = float(exact)
    if not math.isfinite(value) or (exact and value == 0.):
        raise ValueError('response difference is not representable in the declared units')
    return value


class _MeasuredSweep(BaseValidationTest):
    def _configure(self, field, response_scale, baseline, protocol, runner, min_response):
        self.field = None if field is None else _name(field)
        self.response_scale = None if response_scale is None else _scalar(response_scale)
        if self.response_scale is not None and self.response_scale <= 0.:
            raise ValueError('response_scale must be finite and positive in metric units')
        if protocol is not None and (not isinstance(protocol, str) or not protocol.strip()):
            raise ValueError('protocol must describe fixed conditions and measurement units')
        self.protocol = protocol
        self.baseline = None if baseline is None else _parameters(baseline)
        self.runner = _callable(runner, 'runner')
        self.min_response = _scalar(min_response)
        if self.min_response < 0.:
            raise ValueError('min_response must be a nonnegative fraction of response_scale')

    def _details(self):
        return dict(field=self.field, response_scale=self.response_scale, protocol=self.protocol,
                    baseline=None if self.baseline is None else dict(self.baseline),
                    min_response=self.min_response, numerical_sweep_validated=False,
                    parameter_application_verified=False, physical_validated=False,
                    global_sensitivity_validated=False, derivative_accuracy_validated=False,
                    reference_authenticity_validated=False)

    def _supported(self, details, *, baseline_required=False):
        missing = self.field is None or self.response_scale is None or self.protocol is None
        missing |= baseline_required and self.baseline is None
        if missing:
            details['unsupported'] = True
            raise ValueError('declare field, response_scale, protocol and required baseline explicitly')

    def _measure(self, builder, params, instances, records, clock):
        inspect.signature(builder).bind(**params)
        sim = _fresh(builder, instances, **dict(params))
        result = self.runner(sim) if self.runner else sim.run()
        _record(result, records)
        value = _scalar(measured_field(result, self.field))
        applied = _get(result, 'parameters')
        if applied is _MISSING:
            raise ValueError('result must record actual parameters explicitly')
        applied = _parameters(applied)
        if any(key not in applied or applied[key] != val for key, val in params.items()):
            raise ValueError('measured parameters must match all requested varied and fixed controls')
        if _get(result, 'times_s') is not _MISSING:
            raise ValueError('extract one scalar metric; do not pass an unreduced trajectory')
        time = _get(result, 'time_s')
        time = None if time is _MISSING else _scalar(time)
        if time is not None and time < 0.:
            raise ValueError('snapshot time_s must be nonnegative')
        if clock and clock[0] != time:
            raise ValueError('all sweep metrics require identical snapshot clocks when supplied')
        if not clock:
            clock.append(time)
        return value

    def _failure(self, error, details):
        return ValidationResult(self.name, False, f'unavailable/failed sweep evidence: {error}', details)


class SensitivityTest(_MeasuredSweep):
    """Audit measured scalar regularity on a uniform one-parameter grid.

    field is an actual scalar (e.g. measured terminal charge or extracted Vth),
    never max(phi). runner(sim) adapts solve APIs and measurement extraction.
    Each result records parameters, optional time_s and true success flags.
    baseline supplies fixed controls; protocol owns geometry, history and units.
    response_scale is an explicit positive scale in metric units, independent
    of output offset. Adjacent and second differences divided by that scale
    must each be <= tolerance when enabled. These finite-grid checks cannot
    prove continuity, distinguish phase transitions, or validate derivatives.
    A constant response is inconclusive; min_response adds a detection floor.
    """
    def __init__(self, param_name, param_range, num_points=10,
                 check_smoothness=True, check_no_jumps=True, tolerance=.1, *,
                 field=None, response_scale=None, baseline=None, protocol=None,
                 runner=None, min_response=0.):
        super().__init__(f'Sensitivity Test ({param_name})')
        self.param_name = _name(param_name)
        self.param_range = _range(param_range)
        self.num_points = _count(num_points)
        self.values = _grid(self.param_range, self.num_points)
        if (not isinstance(check_smoothness, (bool, np.bool_)) or
                not isinstance(check_no_jumps, (bool, np.bool_)) or
                not (check_smoothness or check_no_jumps)):
            raise ValueError('enable at least one explicit boolean regularity check')
        self.check_smoothness, self.check_no_jumps = bool(check_smoothness), bool(check_no_jumps)
        self.tolerance = _tolerance(tolerance)
        self._configure(field, response_scale, baseline, protocol, runner, min_response)

    def run(self, device_builder):
        details = self._details()
        details.update(param_name=self.param_name, param_values=list(self.values), metrics=[],
                       tolerance=self.tolerance, response_detected=False)
        try:
            self._supported(details)
            instances, records, clock = [], [], []
            for value in self.values:
                params = dict(self.baseline or {}, **{self.param_name: value})
                details['metrics'].append(self._measure(device_builder, params, instances, records, clock))
            metrics = details['metrics']
            spread = _difference(max(metrics), min(metrics), self.response_scale)
            details['response_detected'] = spread > self.min_response
            details['normalized_response_range'] = spread
            first = [_difference(b, a, self.response_scale) for a, b in zip(metrics, metrics[1:])]
            second = [_difference(b, a, 1.) for a, b in zip(first, first[1:])]
            details.update(normalized_first_differences=first, normalized_second_differences=second,
                           jump_violation=max(map(abs, first)), smoothness_violation=max(map(abs, second)))
            passed = (details['response_detected'] and
                      (not self.check_no_jumps or details['jump_violation'] <= self.tolerance) and
                      (not self.check_smoothness or details['smoothness_violation'] <= self.tolerance))
            details['numerical_sweep_validated'] = bool(passed)
            details['inconclusive'] = not details['response_detected']
            return ValidationResult(self.name, bool(passed),
                                    'measured finite-grid regularity only' if passed else
                                    'response below detection floor or regularity budget exceeded', details)
        except Exception as error:
            return self._failure(error, details)


class ParameterImportanceTest(_MeasuredSweep):
    """Rank complete one-at-a-time sweeps around an explicit common baseline.

    Score = RMS((metric(parameter_i)-metric(baseline))/response_scale).
    Signs and zero/negative baseline metrics are meaningful. Parameter units
    do not change scores if ranges/baseline are converted consistently. This
    is range-dependent OAT screening, not a Sobol index or an interaction test.
    Any failed sample aborts; no partial ranking is marked valid. All-flat
    sweeps are inconclusive, while insensitive individual parameters score 0.
    """
    def __init__(self, param_names, param_ranges, num_samples=20, *, field=None,
                 response_scale=None, baseline=None, protocol=None, runner=None,
                 min_response=0.):
        super().__init__('Parameter Importance Test')
        if (not isinstance(param_names, (list, tuple)) or not param_names or
                any(not isinstance(p, str) for p in param_names) or len(set(param_names)) != len(param_names)):
            raise ValueError('param_names must contain unique nonempty parameter names')
        self.param_names = tuple(_name(p) for p in param_names)
        if not isinstance(param_ranges, Mapping) or set(param_ranges) != set(param_names):
            raise ValueError('param_ranges must specify exactly every named parameter')
        self.param_ranges = {key: _range(val) for key, val in param_ranges.items()}
        self.num_samples = _count(num_samples)
        self.values = {key: _grid(bounds, self.num_samples) for key, bounds in self.param_ranges.items()}
        self._configure(field, response_scale, baseline, protocol, runner, min_response)
        if self.baseline is not None:
            for key, (low, high) in self.param_ranges.items():
                if key not in self.baseline or not low <= self.baseline[key] <= high:
                    raise ValueError('baseline must contain every varied parameter inside its range')

    def run(self, device_builder):
        details = self._details()
        details.update(param_values={key: list(vals) for key, vals in self.values.items()},
                       metrics={}, sensitivities={}, sorted_params=[], ranking_validated=False)
        try:
            self._supported(details, baseline_required=True)
            instances, records, clock = [], [], []
            baseline = self._measure(device_builder, self.baseline, instances, records, clock)
            details['baseline_metric'] = baseline
            scores, shifts = {}, {}
            for key in self.param_names:
                values = details['metrics'][key] = []
                for value in self.values[key]:
                    params = dict(self.baseline, **{key: value})
                    values.append(self._measure(device_builder, params, instances, records, clock))
                shift = [_difference(value, baseline, self.response_scale) for value in values]
                shifts[key] = shift
                peak = max(map(abs, shift))
                scores[key] = peak*math.sqrt(sum((value/peak)**2 for value in shift)/len(shift)) if peak else 0.
                if not math.isfinite(scores[key]) or (peak and scores[key] == 0.):
                    raise ValueError('importance score is not representable')
            details['normalized_shifts'] = shifts
            if not any(max(map(abs, shift)) > self.min_response for shift in shifts.values()):
                details['inconclusive'] = True
                raise ValueError('all parameter responses are below the detection floor')
            details.update(sensitivities=scores, sorted_params=sorted(scores.items(), key=lambda item: item[1], reverse=True),
                           numerical_sweep_validated=True, ranking_validated=True)
            return ValidationResult(self.name, True, 'complete range-dependent OAT screening only', details)
        except Exception as error:
            return self._failure(error, details)
