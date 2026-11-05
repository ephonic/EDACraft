"""Explicit isolated-cell FD relaxation with carrier energy excess as state.

This mode has no faces, density-changing sources, temperature-dependent bands
or b exponent. Prescribed signed external powers may drive the reservoirs.
It is an explicit restricted DeviceSimulator mode, never an automatic fallback.
Temperatures below absolute-temperature resolution remain implicit in U-Ueq.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from threading import RLock
import numpy as np
from tcad.physics.native_fermi_local import _decimal


@dataclass(frozen=True)
class IsolatedRelaxationState:
    density_n_m3: str
    density_p_m3: str
    lattice_temperature_K: str
    electron_excess_energy_J_m3: str
    hole_excess_energy_J_m3: str
    time_s: float
    configuration_sha256: str

    def __post_init__(self):
        for key in ('density_n_m3','density_p_m3','lattice_temperature_K',
                    'electron_excess_energy_J_m3','hole_excess_energy_J_m3'):
            value=getattr(self,key)
            if not isinstance(value,str) or not Decimal(value).is_finite():
                raise ValueError('finite decimal-string isolated state required')
        if any(Decimal(getattr(self,k))<=0 for k in ('density_n_m3','density_p_m3','lattice_temperature_K')):
            raise ValueError('positive isolated density and lattice temperature required')
        if isinstance(self.time_s,(bool,np.bool_)) or not np.isfinite(self.time_s) or self.time_s<0:
            raise ValueError('finite nonnegative isolated physical clock required')
        if not isinstance(self.configuration_sha256,str) or len(self.configuration_sha256)!=64:
            raise ValueError('isolated configuration fingerprint required')

    def raw(self):
        return [self.density_n_m3,self.density_p_m3,self.lattice_temperature_K,
                self.electron_excess_energy_J_m3,self.hole_excess_energy_J_m3]


@dataclass(frozen=True)
class IsolatedRelaxationConfiguration:
    parameters: tuple  # first sixteen native parameters, all decimal strings
    valleys_n: tuple
    valleys_p: tuple
    initial_densities_m3: tuple
    initial_temperatures_K: tuple  # Tn,Tp,Tl
    initial_time_s: float

    @property
    def sha256(self):
        return sha256(json.dumps(dict(parameters=self.parameters,
            valleys=[[vars(v) for v in a] for a in (self.valleys_n,self.valleys_p)],
            density=self.initial_densities_m3,temperatures=self.initial_temperatures_K,
            time_s=self.initial_time_s),sort_keys=True).encode()).hexdigest()

    def packed_valleys(self):
        return tuple(tuple(x for v in a for x in
            (v.mass_normal,v.dos_mass_ratio,v.degeneracy,v.band_offset_owner_J))
            for a in (self.valleys_n,self.valleys_p))


class IsolatedThreeTemperatureRelaxation:
    """Audited C++ BE energy-excess path for a closed single FD cell.

    Construct from the SAME model/initial state used by DeviceThreeTemperature.
    This deliberately distinct state type cannot be fed to the general device.
    """
    def __init__(self,model,initial_state,*,temperature_bounds_K=None):
        from .three_temperature import ThreeTemperatureElectrothermal
        if type(model) is not ThreeTemperatureElectrothermal:
            raise ValueError('unmodified three-temperature model required')
        model._validate_state(initial_state)
        if (model.nc!=1 or len(model.internal) or model.contacts or model.bath or
            model.temperature_dependent_bands or model.trap_capture_law is not None or
            model.radiative_law is not None or model.auger_events is not None or
            np.any(model.intercarrier_conductance_W_m3_K) or np.any(model.pair_generation_rate_m3_s)):
            raise ValueError('isolated mode requires one closed fixed-band cell without other sources')
        laws=[]
        for law in model.relaxation_laws:
            if law is not None and law.carrier_temperature_exponent!=0:
                raise ValueError('isolated eliminated relaxation requires carrier exponent b=0')
            laws.extend((model.T,1.,0.,0.) if law is None else
                (law.reference_temperature_K,law.reference_density_m3,
                 law.lattice_temperature_exponent,law.density_exponent))
        T=tuple(_decimal(float(getattr(initial_state,k)[0])) for k in
            ('electron_temperature_K','hole_temperature_K','temperature_K'))
        values=tuple(map(float,T));lo,hi=min(values),max(values)
        if lo==hi:lo*=.5;hi*=1.5
        if temperature_bounds_K is not None:
            bounds=tuple(temperature_bounds_K)
            if (len(bounds)!=2 or any(isinstance(v,(bool,np.bool_)) or not np.isfinite(v) or v<=0 for v in bounds)
                    or bounds[0]>=bounds[1] or bounds[0]>min(values) or bounds[1]<max(values)):
                raise ValueError('positive increasing temperature bounds must enclose all initial temperatures')
            lo,hi=map(float,bounds)
        params=tuple(_decimal(v) for v in (model.capacity[0],model.vol[0],model.Ec[0],model.Eh[0],
            model.tau_n[0],model.tau_p[0],*laws,lo,hi))
        densities=tuple(_decimal(a[0]) for a in (initial_state.n_m3,initial_state.p_m3))
        self._configuration=IsolatedRelaxationConfiguration(params,
            deepcopy(tuple(model.valleys['electrons'])),deepcopy(tuple(model.valleys['holes'])),
            densities,T,float(initial_state.time_s))
        from tcad.core._bindings import PyDeviceSimulator
        self._backend=PyDeviceSimulator(1,1,1,1.,1.,1.)
        self._backend.configure_isolated_relaxation([*densities,T[2],T[0],T[1]],
            params,*self._configuration.packed_valleys(),float(initial_state.time_s))
        accepted=self._backend.isolated_relaxation_state()
        self._state=IsolatedRelaxationState(*accepted['state'],accepted['time_s'],self._configuration.sha256)
        self._lock=RLock()

    @property
    def configuration(self):return self._configuration

    @property
    def state(self):return self._state

    def native_state(self):
        """Atomic copy of accepted native coordinates and physical clock."""
        return self._backend.isolated_relaxation_state()

    def _check_owned_state(self):
        if self._state.configuration_sha256!=self._configuration.sha256:
            raise ValueError('isolated configuration changed after native initialization')
        accepted=self.native_state()
        if accepted['state']!=self._state.raw() or accepted['time_s']!=self._state.time_s:
            raise ValueError('isolated native/Python accepted state mismatch')

    def _decode_candidate(self,old,raw,time,dt):
        if len(raw)!=14:raise ValueError('isolated native output coverage mismatch')
        new=IsolatedRelaxationState(old.density_n_m3,old.density_p_m3,*raw[:3],time,old.configuration_sha256)
        report=dict(scope='isolated_single_cell_FD_energy_excess_BE',dt_s=dt,
            configuration_sha256=self._configuration.sha256,execution_backend='native',
            thermodynamic_state='same_density_FD_equilibrium_at_Tl_plus_signed_carrier_energy_excess',
            exchange_J=raw[3:5],carrier_energy_increments_J=raw[5:7],lattice_energy_increment_J=raw[7],
            energy_residuals_J=raw[8:11],effective_relaxation_times_s=raw[11:13],
            residual_evaluations=int(Decimal(raw[13])),complete_device_energy=False,physical_validated=False,
            measured_ac_material_calibration=False,main_DeviceSimulator_integrated=False,
            carrier_temperature_exponent_supported=0,
            state_owner='C++ DeviceSimulator::isolated_relaxation',
            main_DeviceSimulator_scoped_isolated_relaxation_integrated=True,
            state_transaction='prepare-independent-audit-commit')
        return new,report

    def advance(self,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=256,source_power_W=(0.,0.,0.)):
        """BE step with prescribed constant external (electron,hole,lattice) W.

        Powers are total cell powers, signed positive into each reservoir.
        They do not model absorption, Joule heating, generation or recombination.
        The caller supplies those physical models separately in general modes.
        """
        budgets=(charge_atol_C,particle_atol,energy_atol_J)
        if any(isinstance(v,(bool,np.bool_)) or not np.isfinite(v) or v<=0 for v in (*budgets,dt_s)):
            raise ValueError('finite positive timestep and budgets required')
        power=tuple(source_power_W)
        if len(power)!=3 or any(isinstance(v,(bool,np.bool_)) or not np.isfinite(v) for v in power):
            raise ValueError('three finite signed reservoir powers required')
        power=tuple(map(float,power))
        with self._lock:
            self._check_owned_state()
            old=self._state;time=old.time_s+float(dt_s);dt=time-old.time_s
            if not np.isfinite(time) or dt<=0:raise ValueError('isolated physical clock cannot advance')
            with localcontext() as context:
                context.prec=90
                impulses=[str(Decimal.from_float(v)*Decimal.from_float(dt)) for v in power]
            token=None
            try:
                raw,token=self._backend.prepare_isolated_relaxation(float(dt_s),*budgets,max_nfev=max_nfev,
                    source_impulses_J=impulses if any(power) else ())
                new,report=self._decode_candidate(old,raw,time,dt)
                if any(power):
                    report.update(scope='driven_single_cell_FD_energy_excess_BE',
                        source_power_W=list(power),source_impulses_J=impulses,
                        source_model='prescribed_constant_reservoir_power',
                        source_order=['electrons','holes','lattice'])
                from tcad.postprocess.isolated_relaxation import audit_isolated_relaxation_step,audit_isolated_relaxation_initial
                if old.time_s==self._configuration.initial_time_s:
                    initial=audit_isolated_relaxation_initial(self._configuration,old,energy_atol_J=energy_atol_J)
                    if not initial['valid']:raise ValueError('isolated initial independent audit failed: '+str(initial))
                audit=audit_isolated_relaxation_step(self._configuration,old,new,report,
                    charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J,
                    source_power_W=power)
                if not audit['valid']:raise ValueError('isolated independent audit failed: '+str(audit))
                report['independent_audit']=audit
                self._backend.commit_isolated_relaxation(token)
            except BaseException:
                if token is not None:self._backend.discard_isolated_relaxation(token)
                raise
            self._state=new
            return new,report
