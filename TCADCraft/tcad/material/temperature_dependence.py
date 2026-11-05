"""Traceable temperature-dependent material laws with guarded extrapolation."""
from dataclasses import dataclass
import math
import numpy as np


def _temperature(values):
    t=np.asarray(values,dtype=float)
    if t.ndim==0: t=t.reshape(1)
    if not np.all(np.isfinite(t)) or np.any(t<=0): raise ValueError('temperature must be finite and positive')
    return t


@dataclass(frozen=True)
class TemperatureDependentMaterial:
    """Varshni bandgap, power-law mobility and power-law lattice conductivity."""
    name: str
    source: str
    reference_temperature_K: float
    bandgap_0_eV: float
    varshni_alpha_eV_K: float
    varshni_beta_K: float
    mobility_ref_m2_Vs: float
    mobility_exponent: float
    conductivity_ref_W_m_K: float
    conductivity_exponent: float
    valid_temperature_range_K: tuple=(200.,600.)

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name.strip() or not isinstance(self.source,str) or not self.source.strip():
            raise ValueError('material name and source provenance are required')
        vals=(self.reference_temperature_K,self.bandgap_0_eV,self.varshni_alpha_eV_K,
              self.varshni_beta_K,self.mobility_ref_m2_Vs,self.conductivity_ref_W_m_K)
        if any(not np.isfinite(x) for x in vals) or self.reference_temperature_K<=0 or self.bandgap_0_eV<=0 or self.varshni_alpha_eV_K<0 or self.varshni_beta_K<0 or self.mobility_ref_m2_Vs<=0 or self.conductivity_ref_W_m_K<=0:
            raise ValueError('invalid temperature-law coefficients')
        lo,hi=self.valid_temperature_range_K
        if not np.isfinite(lo) or not np.isfinite(hi) or not (0<lo<hi): raise ValueError('invalid temperature range')

    def _check(self, temperature_K, extrapolate):
        t=_temperature(temperature_K);lo,hi=self.valid_temperature_range_K
        if not extrapolate and (np.any(t<lo) or np.any(t>hi)): raise ValueError('temperature outside calibrated range; pass extrapolate=True')
        return t

    def evaluate(self, temperature_K, *, extrapolate=False):
        t=self._check(temperature_K,extrapolate)
        tr=self.reference_temperature_K
        eg=self.bandgap_0_eV-self.varshni_alpha_eV_K*t*t/(t+self.varshni_beta_K)
        mobility=self.mobility_ref_m2_Vs*(t/tr)**(-self.mobility_exponent)
        conductivity=self.conductivity_ref_W_m_K*(t/tr)**(-self.conductivity_exponent)
        if np.any(~np.isfinite(eg)) or np.any(eg<=0) or np.any(~np.isfinite(mobility)) or np.any(mobility<=0) or np.any(~np.isfinite(conductivity)) or np.any(conductivity<=0):
            raise ValueError('temperature-law evaluation became nonphysical')
        return dict(temperature_K=t,bandgap_eV=eg,mobility_m2_Vs=mobility,
            conductivity_W_m_K=conductivity,source=self.source,name=self.name,
            extrapolated=bool(extrapolate and (np.any(t<self.valid_temperature_range_K[0]) or np.any(t>self.valid_temperature_range_K[1]))),
            physical_validated=False)

    def report(self):
        return dict(name=self.name,source=self.source,reference_temperature_K=self.reference_temperature_K,
            valid_temperature_range_K=self.valid_temperature_range_K,law='Varshni+power_mobility+power_conductivity',
            calibrated_observables=['bandgap','mobility','lattice_conductivity'],
            dynamic_device_validated=False,physical_validated=False)


def fit_power_temperature_law(temperatures_K, values, *, source, name, valid_temperature_range_K=None):
    """Fit ``value(T)=value(Tref)*(T/Tref)^(-exponent)`` in log space."""
    if not isinstance(source, str) or not source.strip() or not isinstance(name, str) or not name.strip():
        raise ValueError('fit provenance name and source are required')
    t=_temperature(temperatures_K); y=np.asarray(values,dtype=float)
    if y.shape!=t.shape or np.any(~np.isfinite(y)) or np.any(y<=0) or len(t)<2 or len(np.unique(t))<2: raise ValueError('positive paired temperature samples required')
    x=np.log(t); z=np.log(y); slope,intercept=np.polyfit(x,z,1); tref=float(np.exp(np.mean(x))); ref=float(np.exp(intercept+slope*np.log(tref)))
    lo,hi=(float(np.min(t)),float(np.max(t))) if valid_temperature_range_K is None else valid_temperature_range_K
    return dict(name=name,source=source,reference_temperature_K=tref,reference_value=ref,exponent=float(-slope),valid_temperature_range_K=(lo,hi),fit_rmse=float(np.sqrt(np.mean((np.exp(intercept+slope*x)-y)**2))))
