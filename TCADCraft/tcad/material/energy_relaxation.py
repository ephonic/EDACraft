"""Explicit constitutive parameters, without inferred material calibration."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EnergyRelaxationPowerLaw:
    """tau=tau0*(Tl/Tref)^a*(Tc/Tref)^b*(density/nref)^c.

    tau0 is the existing per-cell energy relaxation time, distinct from SRH
    lifetime. No clipping or automatic material calibration is implied.
    """
    reference_temperature_K: float = 300.
    reference_density_m3: float = 1e25
    lattice_temperature_exponent: float = 0.
    carrier_temperature_exponent: float = 0.
    density_exponent: float = 0.

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            a=np.asarray(getattr(self,name))
            if (a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a)
                    or not np.isfinite(float(a)) or (name.startswith('reference_') and a<=0)):
                raise ValueError('finite real relaxation parameters and positive references required')
            object.__setattr__(self,name,float(a))

    def parameters(self):
        return tuple(getattr(self,name) for name in self.__dataclass_fields__)

    def evaluate(self,tau0_s,density_m3,carrier_temperature_K,lattice_temperature_K):
        """Reference orchestration only; native Newton evaluates its own C++ law."""
        raw=[np.asarray(v) for v in (tau0_s,density_m3,carrier_temperature_K,lattice_temperature_K)]
        if any(a.dtype.kind not in 'fiu' or np.any(~np.isfinite(a)) or np.any(a<=0) for a in raw):
            raise ValueError('positive finite relaxation state and reference time required')
        tau,n,Tc,Tl=np.broadcast_arrays(*[a.astype(np.longdouble) for a in raw])
        a,b,c=self.parameters()[2:]
        with np.errstate(over='ignore',under='ignore',invalid='ignore'):
            result=(tau if a==b==c==0 else np.exp(np.log(tau)+
                a*np.log(Tl/np.longdouble(self.reference_temperature_K))+
                b*np.log(Tc/np.longdouble(self.reference_temperature_K))+
                c*np.log(n/np.longdouble(self.reference_density_m3)))).astype(float)
        if np.any(~np.isfinite(result)) or np.any(result<=0):
            raise ValueError('effective relaxation time is outside positive float64 range')
        return result.copy()
