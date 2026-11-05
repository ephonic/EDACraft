"""Measured refinement checks; numerical agreement does not certify physics."""
import inspect
import numpy as np
from .base import BaseValidationTest, ValidationResult, measured_field
from .cross_validation import _tolerance


def _sequence(values, default, minimum, *, positive=False, direction=None, integer=False):
    values = default if values is None else values
    array = np.asarray(values)
    if (array.ndim != 1 or len(array) < minimum or array.dtype.kind not in 'iuf'
            or any(isinstance(v, (bool, np.bool_)) for v in values)):
        raise ValueError('provide enough finite real refinement values')
    with np.errstate(over='ignore', under='ignore'):
        numeric = array.astype(float)
    if (not np.all(np.isfinite(numeric)) or np.any((numeric == 0.) & (array != 0.))
            or (positive and np.any(numeric <= 0.))
            or (integer and (np.any(numeric < 3) or np.any(numeric != np.floor(numeric))))):
        raise ValueError('invalid or unrepresentable refinement values')
    increasing = np.all(numeric[1:] > numeric[:-1])
    decreasing = np.all(numeric[1:] < numeric[:-1])
    if ((direction == 'up' and not increasing) or (direction == 'down' and not decreasing)
            or (direction is None and not (increasing or decreasing))):
        raise ValueError('refinement values must be strictly ordered without repeats')
    return [int(v) if integer else float(v) for v in numeric]


def _field(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('field must be a nonempty measurement name')
    return value


def _callable(value, name):
    if value is not None and not callable(value):
        raise ValueError(f'{name} must be callable')
    return value


def _fresh(builder, instances, **kwargs):
    sim = builder(**kwargs)
    if any(sim is previous for previous in instances):
        raise ValueError('builder must return fresh simulator instances')
    instances.append(sim)  # Retain ownership, including for native extensions.
    return sim


def _record(result, records):
    if any(result is previous for previous in records):
        raise ValueError('each refinement must return a distinct result')
    records.append(result)


def _failure(test, error, details):
    return ValidationResult(test.name, False, f'unavailable/failed refinement evidence: {error}', details)


class GridConvergenceTest(BaseValidationTest):
    """Compare nodal RMS error against explicit reference(n, measured_result).

    Default builder(nx=n, ny=n) refines a fixed unit domain with h=1/(n-1).
    Supply spacing(n) for actual mesh spacing, runner(sim) for native APIs,
    and reference(n, result) for values at EXACTLY the same sample locations.
    The caller owns fixed geometry, units, reference provenance and sampling;
    this class performs no interpolation, spatial weighting or material audit.
    All pairwise error orders must match; zero errors cannot identify an order.
    """
    def __init__(self, mesh_sizes=None, expected_order=2., tolerance=.3, *,
                 reference=None, spacing=None, runner=None, field='phi'):
        super().__init__('Grid Convergence Test')
        self.mesh_sizes = _sequence(mesh_sizes, [20,40,80,160], 3,
                                    positive=True, direction='up', integer=True)
        self.expected_order = _tolerance(expected_order)
        self.tolerance = _tolerance(tolerance)
        self.field = _field(field)
        self.reference = _callable(reference, 'reference')
        self.spacing = _callable(spacing, 'spacing')
        self.runner = _callable(runner, 'runner')

    def run(self, device_builder):
        details = dict(mesh_sizes=list(self.mesh_sizes), field=self.field, errors=[],
            pairwise_orders=[], physical_validated=False, grid_order_validated=False,
            reference_authenticity_validated=False, error_norm='unweighted nodal RMS')
        try:
            if self.reference is None:
                details['unsupported'] = True
                raise ValueError('an explicit analytic or numerical reference is required')
            spacings = [self.spacing(n) if self.spacing else 1./(n-1) for n in self.mesh_sizes]
            spacings = _sequence(spacings, None, 3, positive=True, direction='down')
            details['spacings'] = spacings
            # Binding validates the required controls before any solver runs.
            inspect.signature(device_builder).bind(nx=self.mesh_sizes[0], ny=self.mesh_sizes[0])
            instances, records = [], []
            for n in self.mesh_sizes:
                sim = _fresh(device_builder, instances, nx=n, ny=n)
                actual = self.runner(sim) if self.runner else sim.run()
                _record(actual, records)
                reference = self.reference(n, actual)
                if actual is reference:
                    raise ValueError('grid result cannot be its own reference')
                error = self._compute_l2_error(actual, reference, self.field)
                if not np.isfinite(error):
                    raise ValueError('reference error exceeds representable range')
                details['errors'].append(error)
            errors = details['errors']
            if not all(e > 0. for e in errors):
                details['inconclusive'] = True
                raise ValueError('zero error cannot establish an observed convergence order')
            # Differences of logs avoid error/spacing ratio overflow.
            orders = [(np.log(errors[i])-np.log(errors[i+1])) /
                (np.log(spacings[i])-np.log(spacings[i+1])) for i in range(len(errors)-1)]
            details.update(pairwise_orders=[float(p) for p in orders],
                convergence_rate=float(np.mean(orders)),
                is_monotone=all(a>b for a,b in zip(errors,errors[1:])),
                order_ok=all(np.isfinite(p) and abs(p-self.expected_order)<=self.tolerance for p in orders))
            passed = details['is_monotone'] and details['order_ok']
            details['grid_order_validated'] = passed
            return ValidationResult(self.name, passed, f'observed pairwise orders: {details["pairwise_orders"]}', details)
        except Exception as error:
            return _failure(self, error, details)


class TimeConvergenceTest(BaseValidationTest):
    """Check endpoint stability on decreasing steps, not a global error bound.

    runner(sim, dt, t_final) must return measured fields and time_s=t_final.
    Raw histories must be checked/extracted explicitly by that runner. Without
    a runner the legacy run_transient(dt=..., t_final=...) API is used.
    """
    def __init__(self, dt_values=None, t_final=1e-6, tolerance=.1, *, runner=None, field='phi'):
        super().__init__('Time Convergence Test')
        self.dt_values = _sequence(dt_values, [1e-6,5e-7,1e-7,5e-8], 3, positive=True,direction='down')
        self.t_final = _tolerance(t_final)
        if self.dt_values[0] > self.t_final:
            raise ValueError('time steps must not exceed t_final')
        self.tolerance = _tolerance(tolerance)
        self.runner = _callable(runner, 'runner')
        self.field = _field(field)

    def run(self, device_builder):
        details = dict(dt_values=list(self.dt_values),t_final=self.t_final,field=self.field,
            differences=[],physical_validated=False,endpoint_stability_validated=False,
            global_temporal_error_validated=False,temporal_order_validated=False)
        try:
            instances, results = [], []
            for dt in self.dt_values:
                sim = _fresh(device_builder,instances)
                result = (self.runner(sim,dt,self.t_final) if self.runner else
                          sim.run_transient(dt=dt,t_final=self.t_final))
                measured_field(result,self.field)
                clock = measured_field(result,'time_s')
                if clock.shape != () or float(clock) != self.t_final:
                    raise ValueError('all endpoint measurements must have time_s=t_final')
                _record(result,results)
            differences = [self._compute_relative_error(a,b,self.field) for a,b in zip(results,results[1:])]
            details.update(differences=differences,
                is_monotone=all(a>=b for a,b in zip(differences,differences[1:])),
                final_diff_ok=bool(np.isfinite(differences[-1]) and differences[-1]<=self.tolerance))
            passed = details['is_monotone'] and details['final_diff_ok']
            details['endpoint_stability_validated'] = passed
            return ValidationResult(self.name,passed,f'endpoint relative differences: {differences}',details)
        except Exception as error:
            return _failure(self,error,details)


class ParameterConvergenceTest(BaseValidationTest):
    """Compare parameter-sweep stability; it does not certify a continuum limit."""
    def __init__(self,param_name,param_values,tolerance=.05,*,runner=None,field='phi'):
        super().__init__(f'Parameter Convergence Test ({param_name})')
        self.param_name = _field(param_name)
        self.param_values = _sequence(param_values,None,2)
        self.tolerance = _tolerance(tolerance)
        self.runner = _callable(runner,'runner')
        self.field = _field(field)

    def run(self,device_builder):
        details = dict(param_name=self.param_name,param_values=list(self.param_values),field=self.field,
            differences=[],physical_validated=False,parameter_stability_validated=False,
            discretization_convergence_validated=False)
        try:
            instances,results = [],[]
            for value in self.param_values:
                sim = _fresh(device_builder,instances,**{self.param_name:value})
                result = self.runner(sim) if self.runner else sim.run()
                measured_field(result,self.field)
                _record(result,results)
            differences = [self._compute_relative_error(a,b,self.field) for a,b in zip(results,results[1:])]
            passed = all(np.isfinite(diff) and diff<=self.tolerance for diff in differences)
            details.update(differences=differences,all_ok=passed,parameter_stability_validated=passed)
            return ValidationResult(self.name,passed,f'parameter relative differences: {differences}',details)
        except Exception as error:
            return _failure(self,error,details)
