"""Measured bounds and residual monotonicity under caller-declared limits."""
from collections.abc import Mapping
import numpy as np
from .base import BaseValidationTest, ValidationResult, measured_field
from .convergence import _callable


def _nonnegative(value, name):
    number = measured_field({'value': value}, 'value')
    if number.shape != () or number < 0.:
        raise ValueError(f'{name} must be a finite nonnegative real scalar')
    return float(number)


def _execute(builder, runner):
    sim = builder()
    return runner(sim) if runner is not None else sim.run()


def _details():
    return dict(physical_validated=False, bounds_validated=False,
                residual_monotonicity_validated=False, convergence_validated=False)


def _interval(values, lower, upper, rtol=0., atol=0.):
    """Check a closed interval with scaled arithmetic, including tiny signals.

    Relative slack scales with the declared endpoints, never the measurements.
    A zero lower endpoint therefore cannot hide negative density behind a large
    positive sample. Array bounds must match exactly; broadcasting is forbidden.
    """
    endpoints = [np.asarray(bound) for bound in (lower, upper) if bound is not None]
    for bound in endpoints:
        if bound.shape not in ((), values.shape):
            raise ValueError('array bounds must match the measurement shape exactly')
    for bound, is_lower in ((lower,True),(upper,False)):
        if bound is None: continue
        bound = np.asarray(bound)
        # Scale separately per sample AND endpoint: a large upper endpoint
        # must not erase a tiny positive lower endpoint or negative density.
        scale = np.maximum(np.maximum(np.abs(values),np.abs(bound)),atol)
        scale = np.where(scale == 0.,1.,scale)
        with np.errstate(under='ignore'):
            measured, endpoint = values/scale, bound/scale
            slack = atol/scale + rtol*np.abs(endpoint)
            valid = measured >= endpoint-slack if is_lower else measured <= endpoint+slack
        if not np.all(valid): return False
    return True


def _residuals(result, tolerance, atol):
    residuals = measured_field(result, 'iteration_residuals')
    if residuals.ndim != 1 or len(residuals) < 2 or np.any(residuals < 0.):
        raise ValueError('iteration_residuals must contain at least two nonnegative residuals')
    previous, following = residuals[:-1], residuals[1:]
    scale = np.maximum(np.maximum(previous, following), atol)
    scale = np.where(scale == 0., 1., scale)
    with np.errstate(under='ignore'):
        bad = following/scale > previous/scale + tolerance*(previous/scale) + atol/scale
    violations = (np.flatnonzero(bad)+1).tolist()
    return dict(num_iterations=len(residuals), final_residual=float(residuals[-1]),
                is_monotone=not violations, violations=violations)


class BoundednessTest(BaseValidationTest):
    """Check measured fields against explicit bounds, not universal physics.

    Potential bounds are a scalar (lower, upper) pair in V. Polarization limits
    are nonnegative scalar or pointwise values in C/m^2; there is no universal
    Ps cap for all FE constitutive laws. Without a component axis, P denotes a
    signed scalar polarization field. Set polarization_component_axis for a
    length-three vector axis, whose Euclidean magnitude is bounded instead.

    tolerance is a dimensionless endpoint-relative slack. atol may specify
    absolute n/p [m^-3], phi [V], P [C/m^2] budgets for enabled checks (default 0).
    Residual monotonicity uses its own absolute residual_atol. A pass certifies
    only these declared inequalities; it does not prove solver convergence.
    runner(sim) adapts APIs such as solve() without guessing their controls.
    """
    def __init__(self, check_positive_carriers=True, check_potential_bounds=True,
                 check_monotone_convergence=True, check_ferroelectric_bounds=True,
                 tolerance=1e-10, *, potential_bounds_V=None,
                 polarization_limit_C_m2=None, polarization_component_axis=None,
                 atol=None, residual_atol=0., runner=None):
        super().__init__('Boundedness and Monotonicity Test')
        flags = (check_positive_carriers, check_potential_bounds,
                 check_monotone_convergence, check_ferroelectric_bounds)
        if any(not isinstance(flag, (bool, np.bool_)) for flag in flags) or not any(flags):
            raise ValueError('enable at least one check using boolean flags')
        (self.check_positive_carriers, self.check_potential_bounds,
         self.check_monotone_convergence, self.check_ferroelectric_bounds) = map(bool, flags)
        self.tolerance = _nonnegative(tolerance, 'tolerance')
        self.residual_atol = _nonnegative(residual_atol, 'residual_atol')
        self.runner = _callable(runner, 'runner')
        self.potential_bounds_V = None
        if potential_bounds_V is not None:
            limits = measured_field({'limits': potential_bounds_V}, 'limits')
            if (limits.shape != (2,) or limits[0] > limits[1] or
                    any(isinstance(v, (bool,np.bool_)) for v in potential_bounds_V)):
                raise ValueError('potential_bounds_V must be an ordered finite scalar pair')
            self.potential_bounds_V = tuple(map(float, limits))
        self.polarization_limit_C_m2 = None
        if polarization_limit_C_m2 is not None:
            limit = measured_field({'limit': polarization_limit_C_m2}, 'limit')
            if np.any(limit < 0.):
                raise ValueError('polarization limits must be nonnegative')
            self.polarization_limit_C_m2 = limit.copy()
        if polarization_component_axis is not None and (
                not isinstance(polarization_component_axis, (int,np.integer)) or
                isinstance(polarization_component_axis, (bool,np.bool_))):
            raise ValueError('polarization_component_axis must be an integer or None')
        self.polarization_component_axis = None if polarization_component_axis is None else int(polarization_component_axis)
        enabled = set()
        if self.check_positive_carriers: enabled.update(('n','p'))
        if self.check_potential_bounds: enabled.add('phi')
        if self.check_ferroelectric_bounds: enabled.add('P')
        if atol is None: atol = {}
        if not isinstance(atol, Mapping) or set(atol)-enabled:
            raise ValueError('atol may only specify fields used by enabled checks')
        self.atol = {field:_nonnegative(atol.get(field,0.), f'atol[{field}]') for field in enabled}

    def run(self, device_builder):
        details = _details()
        details.update(checks={},rtol=self.tolerance,atol=dict(self.atol),residual_atol=self.residual_atol)
        if ((self.check_potential_bounds and self.potential_bounds_V is None) or
                (self.check_ferroelectric_bounds and self.polarization_limit_C_m2 is None)):
            details['unsupported'] = True
            return ValidationResult(self.name,False,'Provide explicit potential and polarization limits for enabled checks',details)
        try:
            result = _execute(device_builder,self.runner)
            fields = {}
            if self.check_positive_carriers:
                for field in ('n','p'):
                    values = measured_field(result,field); fields[field] = values
                    details['checks'][field] = _interval(values,0.,None,atol=self.atol[field])
            if self.check_potential_bounds:
                fields['phi'] = measured_field(result,'phi')
                details['potential_bounds_V'] = list(self.potential_bounds_V)
                details['checks']['phi'] = _interval(fields['phi'],*self.potential_bounds_V,
                    rtol=self.tolerance,atol=self.atol['phi'])
            if self.check_ferroelectric_bounds:
                values = measured_field(result,'P')
                axis = self.polarization_component_axis
                if axis is not None:
                    if not -values.ndim <= axis < values.ndim or values.shape[axis] != 3:
                        raise ValueError('polarization component axis must have length three')
                    with np.errstate(over='ignore',under='ignore'):
                        values = np.hypot.reduce(values,axis=axis)
                    if not np.all(np.isfinite(values)):
                        raise ValueError('polarization magnitude exceeds finite range')
                else:
                    values = np.abs(values)
                fields['P'] = values
                details['polarization_limit_C_m2'] = self.polarization_limit_C_m2.tolist()
                details['polarization_component_axis'] = axis
                details['checks']['P'] = _interval(values,0.,self.polarization_limit_C_m2,
                    rtol=self.tolerance,atol=self.atol['P'])
            if len({value.shape for value in fields.values()}) > 1:
                raise ValueError('all enabled pointwise fields must have identical shapes after vector reduction')
            if self.check_monotone_convergence:
                details['residuals'] = _residuals(result,self.tolerance,self.residual_atol)
                details['residual_monotonicity_validated'] = details['residuals']['is_monotone']
                details['checks']['residual_monotonicity'] = details['residuals']['is_monotone']
            passed = all(details['checks'].values())
            details['bounds_validated'] = bool(fields) and all(details['checks'][field] for field in fields)
            return ValidationResult(self.name,passed,'Declared bounds/residual checks: '+str(details['checks']),details)
        except Exception as error:
            return ValidationResult(self.name,False,f'unavailable/failed bounds evidence: {error}',details)


class MonotoneConvergenceTest(BaseValidationTest):
    """Audit nonincreasing measured residuals, without claiming convergence.

    The default calls run(); use runner(sim) to request/extract actual solver
    history. Missing history is a failure, never a successful skipped check.
    """
    def __init__(self, tolerance=1e-6, *, residual_atol=0., runner=None):
        super().__init__('Monotone Residual History Test')
        self.tolerance = _nonnegative(tolerance,'tolerance')
        self.residual_atol = _nonnegative(residual_atol,'residual_atol')
        self.runner = _callable(runner,'runner')

    def run(self, device_builder):
        details = _details()
        details.update(rtol=self.tolerance,residual_atol=self.residual_atol)
        try:
            details.update(_residuals(_execute(device_builder,self.runner),self.tolerance,self.residual_atol))
            details['residual_monotonicity_validated'] = details['is_monotone']
            return ValidationResult(self.name,details['is_monotone'],'Measured residual monotonicity only',details)
        except Exception as error:
            return ValidationResult(self.name,False,f'unavailable/failed residual evidence: {error}',details)


class PhysicalBoundsTest(BaseValidationTest):
    """Audit declared carrier [m^-3] and field magnitude [V/m] intervals.

    These are user-selected operating limits, not material validity or a proof
    of breakdown. All n/p/Ex/Ey/Ez fields must be present with matching shapes.
    """
    def __init__(self, max_carrier_density=1e26, min_carrier_density=1.,
                 max_electric_field=1e9, *, runner=None):
        super().__init__('Declared Physical Bounds Test')
        self.max_carrier_density = _nonnegative(max_carrier_density,'max_carrier_density')
        self.min_carrier_density = _nonnegative(min_carrier_density,'min_carrier_density')
        self.max_electric_field = _nonnegative(max_electric_field,'max_electric_field')
        if self.min_carrier_density > self.max_carrier_density:
            raise ValueError('min_carrier_density must not exceed max_carrier_density')
        self.runner = _callable(runner,'runner')

    def run(self, device_builder):
        details = _details()
        details.update(carrier_bounds_m3=[self.min_carrier_density,self.max_carrier_density],
                       max_electric_field_V_m=self.max_electric_field)
        try:
            result = _execute(device_builder,self.runner)
            fields = {field:measured_field(result,field) for field in ('n','p','Ex','Ey','Ez')}
            if len({value.shape for value in fields.values()}) != 1:
                raise ValueError('n/p/Ex/Ey/Ez must have identical shapes')
            checks = {field:_interval(fields[field],self.min_carrier_density,self.max_carrier_density)
                      for field in ('n','p')}
            for field in ('n','p'):
                details['min_'+field] = float(np.min(fields[field]))
                details['max_'+field] = float(np.max(fields[field]))
            scale = max(self.max_electric_field,*[float(np.max(np.abs(fields[field]))) for field in ('Ex','Ey','Ez')])
            if scale == 0.:
                max_scaled = 0.
                checks['electric_field'] = True
            else:
                with np.errstate(under='ignore'):
                    max_scaled = float(np.max(np.hypot(np.hypot(fields['Ex']/scale,fields['Ey']/scale),fields['Ez']/scale)))
                    checks['electric_field'] = max_scaled <= self.max_electric_field/scale
            overflow = max_scaled > 1. and scale > np.finfo(float).max/max_scaled
            details['max_E'] = None if overflow else max_scaled*scale
            details['max_E_overflow'] = bool(overflow)
            details['checks'] = checks
            passed = all(checks.values())
            details['bounds_validated'] = passed
            return ValidationResult(self.name,passed,'Declared carrier and vector-field bounds: '+str(checks),details)
        except Exception as error:
            return ValidationResult(self.name,False,f'unavailable/failed physical bounds evidence: {error}',details)
