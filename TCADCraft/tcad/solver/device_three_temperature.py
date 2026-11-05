"""Audited explicit-cell three-temperature mode owned by C++ DeviceSimulator.

This adapter takes a snapshot of an existing scoped FD model. It does not map
legacy StructuredGrid nodes to finite-volume cells or mix legacy coefficients.
"""
from copy import deepcopy
from dataclasses import replace
from threading import RLock
import numpy as np

from .three_temperature import ThreeTemperatureElectrothermal
from .native_three_temperature_dispatch import pack_three_temperature_inputs, decode_three_temperature_output


class _DeviceModel(ThreeTemperatureElectrothermal):
    def _native_step(self, state, dt, charge_atol_C, particle_atol, energy_atol_J, max_nfev):
        device = self._device
        raw, device._pending_token = device._backend.prepare_three_temperature(
            dt, charge_atol_C, particle_atol, energy_atol_J, max_nfev)
        return decode_three_temperature_output(self, state, raw, charge_atol_C, particle_atol, energy_atol_J, dt_s=dt)


class DeviceThreeTemperature:
    """One fixed model and one accepted state, with audited atomic advance.

    ``DeviceThreeTemperature(model, initial_state).advance(dt_s, **budgets)``
    returns the accepted immutable state and its independent energy audit.
    Candidate state is held in the native device until all public gates pass.
    """
    def __init__(self, model, initial_state):
        if type(model) is not ThreeTemperatureElectrothermal or model.residual_orchestration != 'native':
            raise ValueError('an unmodified native ThreeTemperatureElectrothermal model is required')
        model._validate_state(initial_state)
        self._lock = RLock()
        self._pending_token = None
        self._model = _DeviceModel.__new__(_DeviceModel)
        self._model.__dict__.update(deepcopy(model.__dict__))
        self._initial_state = replace(initial_state)
        self._state = replace(initial_state)
        self._configuration = self._pack_configuration()
        from tcad.core._bindings import PyDeviceSimulator
        # Storage count only: actual cell centers, faces and half distances are
        # in the explicit native configuration, not these dummy nodal spacings.
        self._backend = PyDeviceSimulator(model.nc, 1, 1, 1., 1., 1.)
        self._backend.configure_three_temperature(*self._configuration, initial_state.time_s)
        self._model._device = self

    def _pack_configuration(self):
        return tuple(tuple(values) for values in pack_three_temperature_inputs(
            self._model, self._initial_state, 1., 2e-28, 1e-9, 1e-27))

    @property
    def state(self):
        return self._state

    def native_state(self):
        """Copy of the C++ accepted state; densities retain decimal precision."""
        with self._lock:
            return self._backend.three_temperature_state()

    def _check_owned_state(self):
        raw = self.native_state()
        for key, field, dtype in (('n','n_m3',np.longdouble), ('p','p_m3',np.longdouble),
                ('temperature_n','electron_temperature_K',float), ('temperature_p','hole_temperature_K',float),
                ('temperature_l','temperature_K',float)):
            if not np.array_equal(np.asarray(raw[key], dtype), getattr(self._state, field)):
                raise ValueError('public and native accepted three-temperature states differ')
        if raw['time_s'] != self._state.time_s:
            raise ValueError('public and native accepted physical clocks differ')
        if self._model.trap_capture_law is not None and not np.array_equal(
                np.asarray(raw['trap_fraction'],float),self._state.trap_fraction):
            raise ValueError('public and native accepted trap occupancy differs')

    def _decorate_report(self, report):
        """Adapter-specific metadata must be allocated before publishing state."""

    def advance_adaptive(self, dt_s, *, temperature_atol_K, temperature_rtol,
                         density_atol_m3, density_rtol, minimum_step_s,
                         charge_atol_C, particle_atol, energy_atol_J,
                         max_retries=12, max_nfev=600):
        """Try one interval with step doubling; shrink on error/audit failure.

        The returned report contains both accepted half-step states/reports and
        every trial. The accepted interval may be shorter than dt_s. Temperature
        relative error scales with each field's own change during this interval.
        A local estimate does not guarantee a global trajectory error bound.
        """
        from .adaptive_three_temperature import advance_adaptive
        return advance_adaptive(self,dt_s,temperature_atol_K=temperature_atol_K,
            temperature_rtol=temperature_rtol,density_atol_m3=density_atol_m3,density_rtol=density_rtol,
            minimum_step_s=minimum_step_s,charge_atol_C=charge_atol_C,particle_atol=particle_atol,
            energy_atol_J=energy_atol_J,max_retries=max_retries,max_nfev=max_nfev)

    def run_transient(self, output_times_s, *, initial_step_s, maximum_step_s,
                      minimum_step_s, temperature_atol_K, temperature_rtol,
                      density_atol_m3, density_rtol, charge_atol_C, particle_atol,
                      energy_atol_J, cumulative_energy_atol_J=None, cumulative_particle_atol=None,
                      cumulative_charge_atol_C=None,
                      max_intervals=10000, max_retries=12, max_nfev=600):
        """Run an entire audited trajectory atomically, at exact output clocks.

        Returns output states and all adaptive interval/trial reports. Failure
        leaves this device at its original accepted state; diagnostic partial
        history is carried by ThreeTemperatureTransientError.diagnostics.
        Optional cumulative_energy_atol_J, cumulative_particle_atol and
        cumulative_charge_atol_C gate the whole-path conservation ledger without changing
        per-substep budgets or requesting refinement.
        None retains the sum of accepted substep budgets; the final ledger,
        when available, is also retained in failure diagnostics.
        """
        from .transient_three_temperature import run_transient
        return run_transient(self, output_times_s, initial_step_s=initial_step_s,
            maximum_step_s=maximum_step_s, minimum_step_s=minimum_step_s,
            temperature_atol_K=temperature_atol_K, temperature_rtol=temperature_rtol,
            density_atol_m3=density_atol_m3, density_rtol=density_rtol,
            charge_atol_C=charge_atol_C, particle_atol=particle_atol, energy_atol_J=energy_atol_J,
            cumulative_energy_atol_J=cumulative_energy_atol_J,
            cumulative_particle_atol=cumulative_particle_atol,
            cumulative_charge_atol_C=cumulative_charge_atol_C,
            max_intervals=max_intervals, max_retries=max_retries, max_nfev=max_nfev)

    def advance(self, dt_s, *, charge_atol_C, particle_atol, energy_atol_J, max_nfev=600):
        with self._lock:
            if self._pack_configuration() != self._configuration:
                raise ValueError('device three-temperature configuration is immutable')
            self._check_owned_state()
            try:
                new, report = self._model.step(self._state, dt_s, charge_atol_C=charge_atol_C,
                    particle_atol=particle_atol, energy_atol_J=energy_atol_J, max_nfev=max_nfev)
                report.update(device_state_owner='C++ DeviceSimulator', device_mesh_mode='explicit_cells',
                    device_transaction='independently_audited_prepare_commit',
                    main_DeviceSimulator_scoped_three_temperature_integrated=True,
                    legacy_StructuredGrid_three_temperature_integrated=False)
                report['missing_physics'].remove('main_DeviceSimulator_integration')
                report['missing_physics'].append('legacy_StructuredGrid_three_temperature_conversion')
                self._decorate_report(report)
                # Nothing visible advances until the independent audit in step
                # and every Python allocation above have succeeded.
                self._backend.commit_three_temperature(self._pending_token)
            except BaseException:
                if self._pending_token is not None:
                    self._backend.discard_three_temperature(self._pending_token)
                self._pending_token = None
                raise
            self._pending_token = None
            self._state = new
            return new, report
