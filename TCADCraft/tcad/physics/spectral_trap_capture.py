"""Energy-resolved local trap source, separate from the device timestepper.

The reverse kernel enforces local detailed balance with a lattice bath:
electron emission has vacancy*exp[-(E-Et)/kTl], hole emission has
vacancy*exp[-(E+Et)/kTl]. Coefficients are caller supplied constants,
in m^3/s, not measured lifetimes. Spin is included in the bulk 3D DOS.
"""
from dataclasses import dataclass
import numpy as np
from .fermi_spectral import validate_valleys
from .native_fermi_local import _decimal


FIELDS=('capture_n_m3_s','emission_n_m3_s','capture_p_m3_s','emission_p_m3_s',
 'capture_energy_n_W_m3','emission_energy_n_W_m3','capture_energy_p_W_m3','emission_energy_p_W_m3',
 'net_capture_n_m3_s','net_capture_p_m3_s','electron_number_source_m3_s',
 'hole_number_source_m3_s','occupancy_source_s',
 'electron_energy_source_W_m3','hole_energy_source_W_m3','trap_energy_source_W_m3',
 'lattice_heat_W_m3','trap_charge_source_C_m3_s','total_charge_source_C_m3_s',
 'total_energy_source_W_m3','entropy_production_W_m3_K','density_n_m3','density_p_m3')


def _scalar(value):
    a=np.asarray(value)
    if a.ndim or a.dtype.kind not in 'iuf' or not np.isfinite(a):
        raise ValueError('finite real scalar trap parameters required')
    return np.longdouble(value)


@dataclass(frozen=True)
class SpectralTrapState:
    temperature_n_K: float
    temperature_p_K: float
    temperature_l_K: float
    mu_n_J: float
    mu_p_J: float
    Ec_J: float
    Eh_J: float
    trap_density_m3: float
    trap_level_J: float
    capture_n_m3_s: float
    capture_p_m3_s: float
    occupancy: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self,name,_scalar(getattr(self,name)))
        if min(self.temperature_n_K,self.temperature_p_K,self.temperature_l_K)<=0:
            raise ValueError('positive trap reservoir temperatures required')
        if min(self.trap_density_m3,self.capture_n_m3_s,self.capture_p_m3_s)<0:
            raise ValueError('nonnegative trap density and capture coefficients required')
        if not 0<self.occupancy<1:
            raise ValueError('open trap occupancy required for finite entropy production')


def _valley_decimals(valleys):
    return [_decimal(x) for v in valleys for x in
            (v.mass_normal,v.dos_mass_ratio,v.degeneracy,v.band_offset_owner_J)]


def spectral_trap_capture(state, valleys_n, valleys_p):
    """Return instantaneous number/energy/charge/entropy source densities.

    This native operator does not update n/p/T/f, solve Poisson, or establish
    a dynamic device energy closure. Trap level must lie within every valley
    gap. Empty/full occupancy endpoints are rejected, not clipped. A coupled
    implicit solver must supply a valid interior candidate and add trap
    charge/storage; applying a source explicitly can deplete a reservoir.
    """
    if not isinstance(state,SpectralTrapState):
        raise TypeError('SpectralTrapState required')
    vn=validate_valleys(valleys_n);vp=validate_valleys(valleys_p)
    from tcad.core._bindings import native_spectral_trap_capture_raw
    values=native_spectral_trap_capture_raw(
        [_decimal(getattr(state,n)) for n in state.__dataclass_fields__],
        _valley_decimals(vn),_valley_decimals(vp))
    if len(values)!=len(FIELDS) or not np.all(np.isfinite(values)):
        raise ValueError('invalid native trap source output')
    return dict(zip(FIELDS,values),execution_backend='native',
                law='constant_capture_coefficient_FD_DOS_local_detailed_balance_v1',
                device_coupled=False,material_calibrated=False)
