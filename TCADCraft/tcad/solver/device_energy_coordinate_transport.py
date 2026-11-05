"""Explicit C++ device-owned signed-energy transport, with audited commit."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from threading import RLock
import numpy as np
from .energy_coordinate_transport import EnergyCoordinateState,initialize_energy_coordinates,_pack
from .three_temperature import ThreeTemperatureState
from tcad.postprocess.device_energy_coordinate_transport import DEVICE_SCOPE,METADATA
from tcad.postprocess.native_energy_identity import same_native_energy


def _view(raw,old,time_s):
    t=raw['transport']
    thermal=ThreeTemperatureState(np.asarray(t['n'],np.longdouble),np.asarray(t['p'],np.longdouble),
        old.thermal.trap_fraction,t['temperature_l'],time_s,t['temperature_n'],t['temperature_p'])
    return EnergyCoordinateState(thermal,tuple(raw['excess']),old.configuration_sha256)


class DeviceEnergyCoordinateTransport:
    """Own a fixed explicit-cell model and one audited accepted energy state.

    Accepts a ThreeTemperatureState or an existing EnergyCoordinateState for
    restart without erasing excess energies below temperature resolution.
    There is no automatic conversion from legacy nodal device coefficients.
    """
    def __init__(self,model,initial):
        self._lock=RLock();self._model=deepcopy(model)
        if type(initial) is ThreeTemperatureState:
            initial=initialize_energy_coordinates(self._model,initial)
        if type(initial) is not EnergyCoordinateState:raise ValueError('explicit initial thermal or energy-coordinate state required')
        self._initial=replace(initial)
        packed,fingerprint=_pack(self._model,self._initial.thermal,1.,2e-28,1e-9,1e-27)
        if fingerprint!=initial.configuration_sha256:raise ValueError('initial energy-coordinate model configuration differs')
        self._fingerprint=fingerprint
        from tcad.core._bindings import PyDeviceSimulator
        self._backend=PyDeviceSimulator(self._model.nc,1,1,1.,1.,1.)
        self._backend.configure_energy_coordinate(*packed,initial.excess_J_m3,initial.thermal.time_s)
        snapshot=self._backend.energy_coordinate_state()
        self._state=_view(snapshot['raw'],initial,snapshot['time_s'])
        if len(self._state.excess_J_m3)!=len(initial.excess_J_m3) or any(
            not same_native_energy(stored,supplied) for stored,supplied in zip(self._state.excess_J_m3,initial.excess_J_m3)):
            raise ValueError('initial authoritative energy differs from native energy-coordinate state')
        # In particular reject a forged temperature view in a supplied energy
        # checkpoint; the native EOS reconstructs the actual temperature view.
        for name in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
            if not np.array_equal(getattr(self._state.thermal,name),getattr(initial.thermal,name)):
                raise ValueError('initial thermal view differs from native energy-coordinate state')

    @property
    def state(self):
        with self._lock:return self._state

    def native_state(self):
        """Detached accepted native snapshot, including authoritative excesses."""
        with self._lock:return self._backend.energy_coordinate_state()

    def _check_configuration(self):
        _,fingerprint=_pack(self._model,self._initial.thermal,1.,2e-28,1e-9,1e-27)
        if fingerprint!=self._fingerprint:raise ValueError('device energy-coordinate configuration is immutable')

    def advance_adaptive(self,dt_s,**options):
        """Step doubling in isolated sessions, including signed-energy errors."""
        from .adaptive_energy_coordinate import advance_adaptive
        return advance_adaptive(self,dt_s,**options)

    def run_transient(self,output_times_s,**options):
        """Audit the entire requested path before adopting its final session."""
        from .transient_energy_coordinate import run_transient
        return run_transient(self,output_times_s,**options)

    def _check_owned_state(self):
        snapshot=self._backend.energy_coordinate_state();raw=snapshot['raw'];t=raw['transport']
        for key,field,dtype in (('n','n_m3',np.longdouble),('p','p_m3',np.longdouble),
            ('temperature_n','electron_temperature_K',float),('temperature_p','hole_temperature_K',float),('temperature_l','temperature_K',float)):
            if not np.array_equal(np.asarray(t[key],dtype),getattr(self._state.thermal,field)):
                raise ValueError('public and native accepted energy-coordinate states differ')
        if tuple(raw['excess'])!=self._state.excess_J_m3 or snapshot['time_s']!=self._state.thermal.time_s:
            raise ValueError('public and native accepted energy coordinates or clocks differ')

    def _publication(self,new,report):
        """Allocate the return object before the native commit can be visible."""
        return new,report

    def _trajectory_publication(self,report):
        """Finish constructing the trajectory result before session adoption."""
        return report

    def advance(self,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=600):
        with self._lock:
            _,fingerprint=_pack(self._model,self._initial.thermal,1.,2e-28,1e-9,1e-27)
            if fingerprint!=self._fingerprint:raise ValueError('device energy-coordinate configuration is immutable')
            self._check_owned_state();token=None
            try:
                snapshot,token=self._backend.prepare_energy_coordinate(dt_s,charge_atol_C,particle_atol,energy_atol_J,max_nfev)
                old=self._state;raw=snapshot['raw'];new=_view(raw,old,snapshot['time_s'])
                report=dict(scope=DEVICE_SCOPE,dt_s=new.thermal.time_s-old.thermal.time_s,raw=raw,
                    shared_max_nfev=int(max_nfev),complete_device_energy=False,physical_validated=False,
                    native_device_session_integrated=True,**METADATA)
                from tcad.postprocess.device_energy_coordinate_transport import audit_device_energy_coordinate_step
                checked=audit_device_energy_coordinate_step(self._model,old,new,report,charge_atol_C=charge_atol_C,
                    particle_atol=particle_atol,energy_atol_J=energy_atol_J)
                if not checked['valid']:raise ValueError('independent device energy-coordinate audit failed: '+str(checked))
                report['independent_audit']=checked
                published=self._publication(new,report)
                self._backend.commit_energy_coordinate(token)
            except BaseException:
                if token is not None:self._backend.discard_energy_coordinate(token)
                raise
            self._state=new
            return published
