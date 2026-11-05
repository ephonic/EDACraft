"""Uniform cubic-LK ferroelectric in series with a linear dielectric.

This explicit reduced model is independent of the spatial TCAD solver. It
assumes ideal electrodes, no free interface charge, uniform polarization,
and no leakage, channel, traps, gradient energy, or material calibration.
"""
from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import brentq

from tcad.postprocess.terminal_trace import _real_array, _real_scalar


@dataclass(frozen=True)
class SeriesFerroelectricStack:
    """SI parameters; drive=phi_bottom-phi_top, positive P along bottom->top.

    ``epsilon_fe`` is the background permittivity, not a differential LK
    permittivity. A zero oxide thickness selects the uniform-film limit.
    The returned electrode charge/current use the top-electrode sign.
    """
    thickness_fe: float
    thickness_oxide: float
    epsilon_fe: float
    epsilon_oxide: float
    alpha: float
    beta: float
    viscosity: float
    area: float

    def __post_init__(self):
        for name in ('thickness_fe', 'epsilon_fe', 'epsilon_oxide', 'beta', 'viscosity', 'area'):
            object.__setattr__(self, name, _real_scalar(getattr(self, name), name, positive=True))
        for name in ('alpha', 'thickness_oxide'):
            object.__setattr__(self, name, _real_scalar(getattr(self, name), name))
        if self.thickness_oxide < 0.:
            raise ValueError('thickness_oxide must be nonnegative')
        compliance = self.thickness_fe/self.epsilon_fe + self.thickness_oxide/self.epsilon_oxide
        denominator = self.thickness_fe + self.epsilon_fe*(self.thickness_oxide/self.epsilon_oxide)
        depol = (self.thickness_oxide/self.epsilon_oxide)/denominator
        if (not all(math.isfinite(v) for v in (compliance, denominator, depol))
                or compliance <= 0. or denominator <= 0.
                or (self.thickness_oxide > 0. and depol <= 0.)):
            raise ValueError('series coefficients exceed the representable range')
        object.__setattr__(self, '_denominator', denominator)
        object.__setattr__(self, '_depolarization', depol)

    @property
    def effective_alpha(self):
        value = self.alpha + self._depolarization
        if not math.isfinite(value):
            raise ValueError('effective alpha exceeds the representable range')
        return value

    def electrostatics(self, polarization, drive_voltage):
        """Compute constant D and both layer drops from a declared uniform P.

        Initial/final charges do not certify a switched state or retention.
        Two array inputs must have identical shapes; scalar broadcasting is
        allowed. Nonzero underflow/overflow of returned observables is rejected.
        """
        p = _real_array(polarization, 'polarization')
        v = _real_array(drive_voltage, 'drive_voltage')
        if p.ndim and v.ndim and p.shape != v.shape:
            raise ValueError('polarization and drive_voltage shapes must match')
        # longdouble intermediates prevent avoidable float64 product overflow.
        # This is a reduced diagnostic model, not the native quad backend.
        with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
            pl, vl = p.astype(np.longdouble), v.astype(np.longdouble)
            field = vl/np.longdouble(self._denominator) - pl*np.longdouble(self._depolarization)
            displacement = np.longdouble(self.epsilon_fe)*field + pl
            oxide_field = displacement/np.longdouble(self.epsilon_oxide)
            outputs = dict(field_fe_V_m=field, field_oxide_V_m=oxide_field,
                displacement_C_m2=displacement, voltage_fe_V=field*self.thickness_fe,
                voltage_oxide_V=oxide_field*self.thickness_oxide, top_charge_C=-displacement*self.area)
            result = {}
            for key, value in outputs.items():
                converted = np.asarray(value, dtype=float)
                if not np.all(np.isfinite(converted)) or np.any((converted == 0.) & (value != 0.)):
                    raise ValueError(f'{key} is not representable in float64')
                result[key] = converted
        return result

    def solve_backward_euler(self, times_s, drive_voltage_V, *, initial_polarization=0.):
        """Solve the unique monotone BE cubic at each supplied endpoint.

        No internal time-step control or interpolation is performed. Require
        alpha_eff+viscosity/dt>0; ambiguous multi-root steps are rejected. A
        local root budget does not establish continuous-time accuracy.
        """
        times = _real_array(times_s, 'times_s')
        voltage = _real_array(drive_voltage_V, 'drive_voltage_V')
        initial = _real_scalar(initial_polarization, 'initial_polarization')
        if (times.ndim != 1 or len(times) < 2 or voltage.shape != times.shape
                or times[0] != 0. or np.any(np.diff(times) <= 0.)):
            raise ValueError('provide matching 1D clock/drive, starting at zero and strictly increasing')
        p = np.empty(len(times)); p[0] = initial
        max_root_residual = 0.
        for index, dt in enumerate(np.diff(times), 1):
            rate = self.viscosity/dt
            linear = self.effective_alpha + rate
            target = rate*p[index-1] + voltage[index]/self._denominator
            if not math.isfinite(linear) or not math.isfinite(target) or linear <= 0.:
                raise ValueError('BE requires finite coefficients and positive alpha_eff+viscosity/dt')
            if target == 0.:
                p[index] = 0.
                continue
            # A monotone positive polynomial has a root below both these
            # bounds. Scale by the bound so the solve is dimensionless.
            bound = min(abs(target)/linear, math.exp((math.log(abs(target))-math.log(self.beta))/3.))
            if not math.isfinite(bound) or bound <= 0.:
                raise ValueError('BE root scale is not representable')
            a = linear*(bound/abs(target))
            b = self.beta*bound*(bound/abs(target))*bound
            if not math.isfinite(a+b) or a+b < .5:
                raise ValueError('BE scaled cubic is not representable')
            # Roundoff can put the upper bound a few ULPs below the root.
            root = brentq(lambda z: (b*z*z+a)*z-1., 0., 1.+1e-14,
                          xtol=1e-15, rtol=4*np.finfo(float).eps)
            residual = abs((b*root*root+a)*root-1.)
            if residual > 1e-12:
                raise ValueError('BE scaled cubic did not meet its root residual budget')
            max_root_residual = max(max_root_residual, residual)
            p[index] = math.copysign(bound*root, target)
            if p[index] == 0.:
                raise ValueError('BE nonzero polarization underflows float64')
        states = self.electrostatics(p, voltage)
        with np.errstate(over='ignore', invalid='ignore'):
            current = np.r_[0., np.diff(states['top_charge_C'])/np.diff(times)]
        if not np.all(np.isfinite(current)):
            raise ValueError('top current is not representable')
        return dict(times_s=times.copy(), drive_voltage_V=voltage.copy(), polarization_C_m2=p,
            **states, top_current_A=current, initial_current_available=False,
            valid=True, converged=True, max_scaled_root_residual=max_root_residual,
            numerical_scheme='BE on supplied endpoints; float64 reduced model',
            scope='uniform FE + linear oxide, ideal electrodes, no free interface charge',
            physical_validated=False, spatial_solver_validated=False)

    def audit_uniform_history(self, history, *, polar_axis, reference_polarization,
                              polarization_rtol, charge_rtol):
        """Reject nonuniform/spurious spatial histories for THIS uniform target.

        The caller supplies a nonzero P scale and independent error budgets.
        Only the supplied snapshots are checked. The mask is declared geometry
        supplied by the caller, not inferred from P. This cannot validate a
        multidomain, trapped-charge or channel device, or unsampled times.
        """
        scale = _real_scalar(reference_polarization, 'reference_polarization', positive=True)
        prtol = _real_scalar(polarization_rtol, 'polarization_rtol', positive=True)
        qrtol = _real_scalar(charge_rtol, 'charge_rtol', positive=True)
        axis_value = np.asarray(polar_axis)
        if axis_value.shape != () or axis_value.dtype.kind not in 'iu' or polar_axis not in (0, 1, 2):
            raise ValueError('polar_axis must be 0, 1 or 2')
        states = list(history)
        if len(states) < 2:
            raise ValueError('at least two ordered spatial snapshots are required')
        spreads, charge_errors, times = [], [], []
        charge_scale = self.area*scale
        declared_mask = None
        for state in states:
            if state.get('valid') is not True or state.get('converged') is not True:
                raise ValueError('failed or unverified spatial state')
            if state.get('electrode_charge_available') is not True:
                raise ValueError('spatial electrode charge is unavailable')
            time = _real_scalar(state['time_s'], 'time_s')
            if (not times and time != 0.) or (times and time <= times[-1]):
                raise ValueError('spatial clock must start at zero and increase')
            times.append(time)
            mask = np.asarray(state['fe_mask'])
            p = _real_array(state['P'], 'P')
            voltage = _real_array(state['electrode_voltages_V'], 'electrode_voltages_V')
            charge = _real_array(state['electrode_charges_C'], 'electrode_charges_C')
            if (mask.ndim != 1 or mask.dtype.kind not in 'biu' or not np.all(np.isin(mask,[0,1]))
                    or not np.any(mask) or p.size != 3*len(mask)
                    or voltage.shape != (2,) or charge.shape != (2,)):
                raise ValueError('uniform audit requires explicit FE mask, vector P and two ordered electrodes')
            if declared_mask is not None and not np.array_equal(mask, declared_mask):
                raise ValueError('declared material geometry changes within history')
            declared_mask = mask.copy()
            pfe = p.reshape(-1,3)[mask.astype(bool), int(polar_axis)]
            spread = float(np.ptp(pfe)/scale)
            if spread > prtol:
                raise ValueError('spatial polarization violates the declared uniform-film target')
            center_p = float(np.mean(pfe))
            top_q = float(self.electrostatics(center_p, voltage[0]-voltage[1])['top_charge_C'])
            error = max(abs(charge[1]-top_q), abs(charge[0]+top_q))/charge_scale
            if error > qrtol:
                raise ValueError('spatial charge violates the uniform series-stack voltage partition')
            spreads.append(spread); charge_errors.append(float(error))
        return dict(valid=True, max_polarization_spread_normalized=max(spreads),
            max_charge_error_normalized=max(charge_errors), samples=len(states),
            physical_validated=False, scope='uniform target consistency only')
