"""Transactional time stepping for the restricted native lattice heat model.

The carrier subsystem stays quasistatic at fixed reference statistics/VT.
Only lattice-dependent mobility feeds temperature back to the electrical solve.
Acceptance validates that declared model, not complete device energy physics.
"""
from copy import deepcopy
from collections.abc import Mapping

import numpy as np

from tcad.postprocess.device_energy import _scalar
from tcad.postprocess.native_thermal import (
    _array, audit_native_lattice_step, audit_native_lattice_mobility)


class LatticeStepRejected(RuntimeError):
    """An attempted step failed convergence or independent acceptance.

    ``attempt`` retains the returned candidate and any completed audits.
    The simulator, accepted temperature and time have already been restored.
    """
    def __init__(self, reason, attempt):
        super().__init__(reason)
        self.attempt = deepcopy(attempt)


class LatticeTimeStepper:
    """Own accepted thermal history; commit each step only after both audits.

    Supply geometry, material and mobility inputs independently of solver
    reports. Inputs are copied. Budgets have no defaults or adaptive floors.
    ``step`` returns an owned result/report copy. Public state properties also
    return copies, so editing a returned array cannot alter the next step.
    Transport charge is taken from the simulator's read-only kernel constant
    and retained with the audit contract.

    Do not reconfigure physics during a step or wrap steps in external
    simulator transactions: driver-owned time/history are outside those
    checkpoints. Configuration may change between steps only if it still
    matches this fixed audit contract. Create a new driver after remeshing or
    changing the contract. Earlier accepted steps survive a later rejection.
    """
    def __init__(self, simulator, initial_temperature_K, heat_capacity_J_m3_K, *,
                 axes_m, extrusion_m, conductivity_W_m_K, thermal_dirichlet_K,
                 base_mobility_n, base_mobility_p, doping_m3, mobility_model,
                 reference_temperature_K, reference_VT_V, power_atol_W,
                 temperature_atol_K, fixed_point_atol_K, current_rtol,
                 current_atol_A_m2, initial_time_s=0.):
        from tcad.simulator import Simulator
        if not isinstance(simulator, Simulator):
            raise TypeError('a Simulator instance is required')
        size = simulator.mesh.npts()
        if not isinstance(axes_m, (list, tuple)) or len(axes_m) != 3:
            raise ValueError('three coordinate axes required')
        mesh_axes = simulator.mesh.axis_coordinates()
        axes = tuple(_array(a, len(m), 'coordinate axis').copy() for a, m in zip(axes_m, mesh_axes))
        if any(not np.array_equal(a, m) for a, m in zip(axes, mesh_axes)):
            raise ValueError('independent axes must match the simulator mesh')
        extrusion = _array(extrusion_m, 3, 'extrusion_m', positive=True).copy()
        # Native singleton spacings determine extrusion; active spacings are
        # reconstructed from the independent axes by the audit.
        for a, e, spacing in zip(axes, extrusion, (simulator.mesh.dx, simulator.mesh.dy, simulator.mesh.dz)):
            if len(a) == 1 and e != spacing:
                raise ValueError('singleton extrusion must match simulator spacing')
        if not isinstance(thermal_dirichlet_K, Mapping) or not thermal_dirichlet_K:
            raise ValueError('explicit thermal bath mapping required')
        bath = {}
        for node, temperature in thermal_dirichlet_K.items():
            if isinstance(node, (bool, np.bool_)) or not isinstance(node, (int, np.integer)) or not 0 <= node < size:
                raise ValueError('thermal bath node outside mesh')
            value = _scalar(temperature, 'bath temperature')
            if value <= 0:
                raise ValueError('positive bath temperature required')
            bath[int(node)] = value
        if mobility_model not in ('constant', 'arora', 'low_temp'):
            raise ValueError('unknown mobility model')
        positive = dict(reference_temperature_K=reference_temperature_K, reference_VT_V=reference_VT_V,
                        power_atol_W=power_atol_W)
        nonnegative = dict(temperature_atol_K=temperature_atol_K, fixed_point_atol_K=fixed_point_atol_K,
                          current_rtol=current_rtol, current_atol_A_m2=current_atol_A_m2)
        scalars = {k: _scalar(v, k) for k, v in {**positive, **nonnegative}.items()}
        if any(scalars[k] <= 0 for k in positive) or any(scalars[k] < 0 for k in nonnegative):
            raise ValueError('positive references/power budget and nonnegative other budgets required')
        mn = _array(base_mobility_n, size, 'base electron mobility').copy()
        mp = _array(base_mobility_p, size, 'base hole mobility').copy()
        if np.any(mn < 0) or np.any(mp < 0):
            raise ValueError('nonnegative mobilities required')
        self._temperature = _array(initial_temperature_K, size, 'initial temperature', positive=True).copy()
        self._capacity = _array(heat_capacity_J_m3_K, size, 'heat capacity', positive=True).copy()
        self._time = _scalar(initial_time_s, 'initial time')
        if self._time < 0:
            raise ValueError('nonnegative initial time required')
        self._simulator = simulator
        self._mesh = simulator.mesh
        self._axes, self._extrusion, self._kappa, self._bath = axes, extrusion, _array(
            conductivity_W_m_K, size, 'conductivity', positive=True).copy(), bath
        self._mobility = dict(base_mobility_n=mn, base_mobility_p=mp,
            elementary_charge_C=simulator.elementary_charge_C,
            doping_m3=_array(doping_m3, size, 'doping').copy(), mobility_model=mobility_model,
            **{k: scalars[k] for k in ('reference_temperature_K', 'reference_VT_V',
                                      'fixed_point_atol_K', 'current_rtol', 'current_atol_A_m2')})
        self._budgets = {k: scalars[k] for k in ('power_atol_W', 'temperature_atol_K')}
        self._accepted_steps = 0
        self._last_report = None

    @property
    def time_s(self):
        return self._time

    @property
    def temperature_K(self):
        return self._temperature.copy()

    @property
    def accepted_steps(self):
        return self._accepted_steps

    @property
    def last_report(self):
        return deepcopy(self._last_report)

    def step(self, dt_s):
        """Attempt one interval; raise on rejection without advancing history.

        Solve with ``(time + dt) - time`` so storage and reported clock use
        the same representable interval. An unrepresentable endpoint raises
        before any solve. Invalid configuration/native exceptions propagate
        after rollback; physical rejection raises :class:`LatticeStepRejected`.
        """
        requested_dt = _scalar(dt_s, 'dt_s')
        endpoint = self._time + requested_dt
        if requested_dt <= 0 or not np.isfinite(endpoint) or endpoint <= self._time:
            raise ValueError('positive representable time interval required')
        dt = endpoint - self._time
        simulator = self._simulator
        if simulator.mesh is not self._mesh or any(not np.array_equal(a, m) for a, m in
                zip(self._axes, simulator.mesh.axis_coordinates())):
            raise ValueError('mesh changed; create a new lattice time driver')
        attempt = dict(start_time_s=self._time, end_time_s=endpoint, dt_s=dt,
                       requested_dt_s=requested_dt, accepted=False,
                       complete_device_energy=False, physical_validated=False)
        with simulator.reliability_transaction():
            result = simulator.run_lattice_step(self._temperature.copy(), self._capacity.copy(), dt)
            attempt['result'] = result
            if result.get('converged') is not True:
                raise LatticeStepRejected('lattice solve did not converge', attempt)
            if result.get('thermal_ledger', {}).get('mobility_feedback') is not True:
                raise LatticeStepRejected('lattice mobility feedback must be enabled', attempt)
            power = audit_native_lattice_step(result, self._axes, self._kappa, self._bath,
                self._temperature, self._capacity, dt, extrusion_m=self._extrusion, **self._budgets)
            mobility = audit_native_lattice_mobility(result, self._axes, **self._mobility)
            attempt.update(power_audit=power, mobility_audit=mobility)
            if power['valid'] is not True or mobility['valid'] is not True:
                raise LatticeStepRejected('independent lattice acceptance failed', attempt)
            next_temperature = _array(result['temperature'], self._temperature.size,
                                      'accepted temperature', positive=True).copy()
            attempt['accepted'] = True
            # Finish allocation/copy work before committing either owner.
            saved_report = deepcopy(attempt)
            returned_report = deepcopy(attempt)
        self._time = endpoint
        self._temperature = next_temperature
        self._accepted_steps += 1
        self._last_report = saved_report
        return returned_report
