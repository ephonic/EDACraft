"""Explicit fixed-band b=0 native FD transport in signed energy coordinates.

Functional steps return a new immutable state after an independent audit.
There is no automatic switch from DeviceThreeTemperature and no native device
prepare/commit session in this API. Model inputs are snapshotted for each call.
"""
from copy import deepcopy
from dataclasses import dataclass,replace
import hashlib
import re
import numpy as np
from .three_temperature import ThreeTemperatureElectrothermal,ThreeTemperatureState
from .native_fd_dispatch import pack_native_fd_inputs
from .cut_cell_transport import _array
from tcad.physics.native_fermi_local import _decimal
from tcad.postprocess.native_energy_identity import same_native_energy

SCOPE='fixed_band_b0_native_FD_energy_coordinate_transport'
_ENERGY_DECIMAL=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',re.ASCII)


@dataclass(frozen=True)
class EnergyCoordinateState:
    thermal: ThreeTemperatureState
    excess_J_m3: tuple
    configuration_sha256: str

    def __post_init__(self):
        if type(self.thermal) is not ThreeTemperatureState:raise ValueError('explicit three-temperature view required')
        values=tuple(self.excess_J_m3)
        if len(values)!=2*len(self.thermal.n_m3):raise ValueError('two signed energy coordinates per cell required')
        for value in values:
            if not isinstance(value,str) or _ENERGY_DECIMAL.fullmatch(value) is None or not same_native_energy(value,value):
                raise ValueError('finite native-range decimal energy coordinates required; nonzero energy must not round to zero')
        if not isinstance(self.configuration_sha256,str) or len(self.configuration_sha256)!=64 or any(c not in '0123456789abcdef' for c in self.configuration_sha256):
            raise ValueError('configuration fingerprint required')
        object.__setattr__(self,'thermal',replace(self.thermal))
        object.__setattr__(self,'excess_J_m3',values)


def _pack(model,state,dt,charge_atol_C,particle_atol,energy_atol_J):
    if type(model) is not ThreeTemperatureElectrothermal:raise ValueError('unmodified ThreeTemperatureElectrothermal model required')
    model._validate_state(state)
    if model.contact_carrier_temperature_K:
        raise ValueError('independent carrier contact temperatures are not supported by energy-coordinate transport')
    if (model.temperature_dependent_bands or model.trap_capture_law is not None
        or model.auger_events is not None or np.any(model.Nt!=0)):
        raise ValueError('energy-coordinate transport currently requires fixed bands without coupled source channels')
    if not 1<=model.nc<=64:raise ValueError('1..64 energy-coordinate cells required')
    laws=[];p=model.relaxation_parameters()
    if p[3]!=0 or p[8]!=0:raise ValueError('energy-coordinate transport requires b_Tc=0')
    for i in range(model.nc):
        for s,tau in enumerate((model.tau_n[i],model.tau_p[i])):
            b=5*s;laws.extend(_decimal(v) for v in (tau,p[b],p[b+1],p[b+2],p[b+4]))
    coupled=bool(np.any(model.intercarrier_conductance_W_m3_K!=0))
    radiation=model.radiative_parameters()
    if radiation is not None:
        rate,en,ep=model.pair_generation_parameters()
        conductance=_array(model.intercarrier_conductance_W_m3_K,model.nc,'intercarrier conductance',nonnegative=True)
        bath,transition=radiation
        laws.append('-3')  # Pair triples, conductance, maintained photon bath, transition rate.
        laws.extend(_decimal(v) for row in zip(rate,en,ep,conductance,bath,transition) for v in row)
    elif coupled:
        rate,en,ep=model.pair_generation_parameters()
        conductance=_array(model.intercarrier_conductance_W_m3_K,model.nc,'intercarrier conductance',nonnegative=True)
        laws.append('-2')  # Pair triples plus conductance; legacy packets stay exact.
        laws.extend(_decimal(v) for row in zip(rate,en,ep,conductance) for v in row)
    elif np.any(model.pair_generation_rate_m3_s!=0):
        rate,en,ep=model.pair_generation_parameters()
        laws.append('-1')  # Explicit prescribed pair-source schema, after the old laws.
        laws.extend(_decimal(v) for row in zip(rate,en,ep) for v in row)
    c,f,vn,vp,parameters=pack_native_fd_inputs(model,state,dt,charge_atol_C,particle_atol,energy_atol_J)
    if model.bulk_potential_path=='linear_series':
        for face in range(len(model.mesh.faces)):
            if face not in model.thermionic_faces:f[22*face+19]='2'
    material=[v for i,v in enumerate(c) if i%17 not in (3,4,6,10)]
    fingerprint=hashlib.sha256(repr((material,f,vn,vp,parameters[4:],laws)).encode('ascii')).hexdigest()
    return (c,f,vn,vp,parameters,laws),fingerprint


def initialize_energy_coordinates(model,initial):
    model=deepcopy(model)
    packed,fingerprint=_pack(model,initial,1.,2e-28,1e-9,1e-27)
    from tcad.core._bindings import native_fermi_energy_coordinates_raw
    e=[None]*(2*model.nc)
    for s,(density,T,band) in enumerate(((initial.n_m3,initial.electron_temperature_K,model.Ec),
                                        (initial.p_m3,initial.hole_temperature_K,model.Eh))):
        values=[_decimal(v) for row in zip(density,initial.temperature_K,T,band) for v in row]
        raw=native_fermi_energy_coordinates_raw(values,packed[2+s],True)
        for i in range(model.nc):e[2*i+s]=raw[6*i+2]
    return EnergyCoordinateState(initial,tuple(e),fingerprint)


def _validate_temperature_view(model,state,packed):
    """Check the rounded view without reconstructing authoritative energy."""
    from tcad.core._bindings import native_fermi_energy_coordinates_raw
    thermal=state.thermal
    for s,(density,T,band) in enumerate(((thermal.n_m3,thermal.electron_temperature_K,model.Ec),
                                        (thermal.p_m3,thermal.hole_temperature_K,model.Eh))):
        values=[]
        for i in range(model.nc):
            values.extend((_decimal(density[i]),_decimal(thermal.temperature_K[i]),
                           state.excess_J_m3[2*i+s],_decimal(band[i])))
        raw=native_fermi_energy_coordinates_raw(values,packed[2+s],False)
        if len(raw)!=6*model.nc or not np.array_equal(np.asarray(raw[::6],float),T):
            raise ValueError('initial thermal view differs from authoritative energy-coordinate state')


def energy_coordinate_step(model,old,dt_s,*,charge_atol_C,particle_atol,energy_atol_J,max_nfev=600):
    if type(old) is not EnergyCoordinateState:raise ValueError('EnergyCoordinateState required')
    for name,value in (('timestep',dt_s),('charge budget',charge_atol_C),('particle budget',particle_atol),('energy budget',energy_atol_J)):
        _array(value,1,name,positive=True)
    next_time=old.thermal.time_s+float(dt_s);dt=next_time-old.thermal.time_s
    if not np.isfinite(next_time) or dt<=0:raise ValueError('physical clock cannot advance')
    model=deepcopy(model)
    packed,fingerprint=_pack(model,old.thermal,dt,charge_atol_C,particle_atol,energy_atol_J)
    if fingerprint!=old.configuration_sha256:raise ValueError('energy-coordinate model configuration changed')
    _validate_temperature_view(model,old,packed)
    from tcad.core._bindings import native_energy_coordinate_transport_raw
    raw=native_energy_coordinate_transport_raw(*packed,old.excess_J_m3,max_nfev)
    t=raw['transport']
    view=ThreeTemperatureState(np.asarray(t['n'],np.longdouble),np.asarray(t['p'],np.longdouble),old.thermal.trap_fraction,
        t['temperature_l'],next_time,t['temperature_n'],t['temperature_p'])
    new=EnergyCoordinateState(view,tuple(raw['excess']),fingerprint)
    report=dict(scope=SCOPE,dt_s=dt,raw=raw,shared_max_nfev=int(max_nfev),
        complete_device_energy=False,physical_validated=False,native_device_session_integrated=False)
    from tcad.postprocess.energy_coordinate_transport import audit_energy_coordinate_step
    checked=audit_energy_coordinate_step(model,old,new,report,charge_atol_C=charge_atol_C,
        particle_atol=particle_atol,energy_atol_J=energy_atol_J)
    if not checked['valid']:raise ValueError('independent energy-coordinate transport audit failed: '+str(checked))
    report['independent_audit']=checked
    return new,report
