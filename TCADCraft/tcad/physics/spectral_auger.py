"""On-shell parabolic Auger/impact event tables with independent FD reservoirs.

Weights include all phase-space, spin and identical-particle normalization.
This API neither constructs a continuum/material kernel nor advances a device.
"""
from dataclasses import dataclass
import numpy as np
from .native_fermi_local import _decimal

LAW='on_shell_parabolic_Auger_impact_event_table_v1'
FIELDS=('auger_rate_m3_s','impact_rate_m3_s','net_recombination_rate_m3_s',
 'eeh_net_rate_m3_s','hhe_net_rate_m3_s','electron_number_source_m3_s','hole_number_source_m3_s',
 'electron_energy_source_W_m3','hole_energy_source_W_m3','lattice_heat_W_m3',
 'total_charge_source_C_m3_s','total_energy_source_W_m3','entropy_production_W_m3_K','maximum_kinematic_scaled_defect')
EVENT_FIELDS=('auger_rate_m3_s','impact_rate_m3_s','net_recombination_rate_m3_s',
 'electron_energy_source_W_m3','hole_energy_source_W_m3','entropy_production_W_m3_K',
 'kinetic_1_J','kinetic_2_J','kinetic_3_J','kinetic_4_J','wavevector_scale_m_inv','log_forward_reverse_ratio','on_shell_defect_J')

def scalar(v):
    a=np.asarray(v)
    if a.ndim or a.dtype.kind not in 'iuf' or not np.isfinite(a):raise ValueError('finite real scalar required')
    return np.longdouble(v)

@dataclass(frozen=True)
class SpectralAugerState:
    temperature_n_K: float
    temperature_p_K: float
    mu_n_J: float
    mu_p_J: float
    Ec_J: float
    Eh_J: float
    mass_n_ratio: float
    mass_p_ratio: float

    def __post_init__(self):
        for n in self.__dataclass_fields__:object.__setattr__(self,n,scalar(getattr(self,n)))
        if min(self.temperature_n_K,self.temperature_p_K,self.mass_n_ratio,self.mass_p_ratio)<=0 or self.Ec_J+self.Eh_J<=0:
            raise ValueError('positive temperatures, masses and gap required')

@dataclass(frozen=True)
class AugerEvent:
    channel: str
    momentum_shape: tuple
    weight_m3_s: float

    def __post_init__(self):
        if self.channel not in ('eeh','hhe'):raise ValueError('eeh or hhe channel required')
        a=np.asarray(self.momentum_shape)
        if a.shape!=(3,3) or a.dtype.kind not in 'iuf' or not np.all(np.isfinite(a)) or not np.any(a):
            raise ValueError('nonzero finite real3x3 momentum shape required')
        a=a.astype(np.longdouble);a=a/np.max(abs(a))
        if np.array_equal(a[0],a[1]):raise ValueError('distinct initial majority momenta required')
        if tuple(a[0])>tuple(a[1]):a=a[[1,0,2]]
        object.__setattr__(self,'momentum_shape',tuple(tuple(v for v in row) for row in a))
        object.__setattr__(self,'weight_m3_s',scalar(self.weight_m3_s))
        if self.weight_m3_s<0:raise ValueError('nonnegative event weight required')

def packed(state,events):
    if not isinstance(state,SpectralAugerState):raise TypeError('SpectralAugerState required')
    events=tuple(events)
    if not 1<=len(events)<=4096 or any(not isinstance(e,AugerEvent) for e in events):
        raise ValueError('1..4096 AugerEvent objects required')
    keys=[(e.channel,e.momentum_shape) for e in events]
    if len(set(keys))!=len(keys):raise ValueError('duplicate normalized event')
    return ([_decimal(getattr(state,n)) for n in state.__dataclass_fields__],
        [_decimal(v) for e in events for v in ((0 if e.channel=='eeh' else 1),e.weight_m3_s,*np.array(e.momentum_shape).ravel())])

def spectral_auger_source(state,events):
    """Evaluate both directions using the same supplied on-shell event weight."""
    from tcad.core._bindings import native_spectral_auger_raw
    s,e=packed(state,events);rows=native_spectral_auger_raw(s,e)
    if len(rows)!=len(e)//11+1 or len(rows[0])!=len(FIELDS) or any(len(v)!=len(EVENT_FIELDS) for v in rows[1:]) or any(not np.all(np.isfinite(v)) for v in rows):
        raise ValueError('invalid native Auger report')
    return dict(zip(FIELDS,rows[0]),event_moments=[dict(zip(EVENT_FIELDS,row)) for row in rows[1:]],
        law=LAW,execution_backend='native',device_coupled=False,material_calibrated=False,continuum_kernel_integrated=False)
