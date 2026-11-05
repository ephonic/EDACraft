"""Matched direct-gap radiative source with independent FD temperatures.

Instantaneous constant per-state rate model, not a material optical spectrum.
Photon momentum is neglected. Two spin branches are counted once in the joint
DOS. A maintained positive-temperature Planck bath has zero photon chemical
potential. Photon power must be included in any subsequent device ledger.
"""
from dataclasses import dataclass
import numpy as np
from .native_fermi_local import _decimal

FIELDS=('spontaneous_rate_m3_s','stimulated_rate_m3_s','absorption_rate_m3_s',
 'emission_rate_m3_s','net_recombination_rate_m3_s',
 'emission_energy_n_W_m3','emission_energy_p_W_m3',
 'absorption_energy_n_W_m3','absorption_energy_p_W_m3',
 'electron_number_source_m3_s','hole_number_source_m3_s','photon_number_source_m3_s',
 'electron_energy_source_W_m3','hole_energy_source_W_m3','photon_power_W_m3',
 'lattice_heat_W_m3','total_charge_source_C_m3_s','total_energy_source_W_m3',
 'entropy_production_W_m3_K')
LAW='matched_direct_gap_constant_state_rate_FD_Planck_v1'


@dataclass(frozen=True)
class SpectralRadiativeState:
    temperature_n_K: float
    temperature_p_K: float
    temperature_photon_K: float
    mu_n_J: float
    mu_p_J: float
    Ec_J: float
    Eh_J: float
    mass_n_ratio: float
    mass_p_ratio: float
    pair_degeneracy: float
    transition_rate_s: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value=getattr(self,name);a=np.asarray(value)
            if a.ndim or a.dtype.kind not in 'iuf' or not np.isfinite(a):
                raise ValueError('finite real scalar radiative parameters required')
            object.__setattr__(self,name,np.longdouble(value))
        if min(self.temperature_n_K,self.temperature_p_K,self.temperature_photon_K)<=0:
            raise ValueError('positive carrier and photon bath temperatures required')
        if min(self.mass_n_ratio,self.mass_p_ratio,self.pair_degeneracy)<=0:
            raise ValueError('positive masses and pair degeneracy required')
        if self.pair_degeneracy!=np.floor(self.pair_degeneracy):
            raise ValueError('integer matched pair degeneracy required')
        if self.Ec_J+self.Eh_J<=0 or self.transition_rate_s<0:
            raise ValueError('positive direct gap and nonnegative transition rate required')


def spectral_radiative_source(state):
    """Return instantaneous event rates (m^-3 s^-1), powers and entropy.

    Positive net recombination removes one electron/hole and emits one photon.
    A hot bath can reverse the net rate; final-state Pauli vacancies are used.
    Energy sources are W/m^3 and entropy production is W/m^3/K. Temperatures,
    populations, electrostatics and photon bath are not advanced by this API.
    """
    if not isinstance(state,SpectralRadiativeState):
        raise TypeError('SpectralRadiativeState required')
    from tcad.core._bindings import native_spectral_radiative_raw
    values=native_spectral_radiative_raw([_decimal(getattr(state,n)) for n in state.__dataclass_fields__])
    if len(values)!=len(FIELDS) or not np.all(np.isfinite(values)):
        raise ValueError('invalid native radiative output')
    return dict(zip(FIELDS,values),execution_backend='native',law=LAW,
                device_coupled=False,material_calibrated=False)
