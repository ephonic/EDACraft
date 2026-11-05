"""Single-level four-rate sheet traps with backward-Euler elimination.

Capture coefficients multiply sheet carrier density (m^-2), hence are m^2/s.
Emission rates are s^-1. These are supplied kinetic parameters, not automatic
band-energy/SRH detailed-balance or degenerate Pauli-blocking calibration.
"""
from dataclasses import dataclass
import numpy as np
from tcad.material.sheet import _finite, Q


@dataclass(frozen=True)
class SheetTrap:
    density_m2: object
    capture_n_m2_s: object
    capture_p_m2_s: object
    emission_n_s: object
    emission_p_s: object
    kind: str = 'acceptor'

    def __post_init__(self):
        if self.kind not in ('acceptor','donor'):
            raise ValueError('trap kind must be acceptor or donor')
        for name in ('density_m2','capture_n_m2_s','capture_p_m2_s','emission_n_s','emission_p_s'):
            value=np.array(_finite(getattr(self,name),name),copy=True)
            if np.any(value<0):raise ValueError(name+' must be nonnegative')
            value.setflags(write=False);object.__setattr__(self,name,value)

    def bind(self,shape):
        values={}
        for name in ('density_m2','capture_n_m2_s','capture_p_m2_s','emission_n_s','emission_p_s'):
            try:values[name]=np.broadcast_to(getattr(self,name),shape).copy().ravel()
            except ValueError as exc:raise ValueError(name+' must be scalar or sheet-shaped') from exc
        return SheetTrap(**values,kind=self.kind)

    def evaluate(self,n,p,old_occupancy,dt_s=None):
        """Return eliminated f, rates per trap, and analytic n/p derivatives.

        dt_s=None freezes the supplied occupancy for externally prepared DC
        initialization. The caller must then omit capture terms in continuity.
        """
        n,p,f0=np.broadcast_arrays(_finite(n,'n'),_finite(p,'p'),_finite(old_occupancy,'old_occupancy'))
        if np.any(n<0) or np.any(p<0) or np.any(f0<0) or np.any(f0>1):
            raise ValueError('densities must be nonnegative and occupancy in [0,1]')
        cn,cp,en,ep=self.capture_n_m2_s,self.capture_p_m2_s,self.emission_n_s,self.emission_p_s
        with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
            a=cn*n+ep;b=en+cp*p
            if dt_s is None:
                f=f0.copy();empty=1-f;dn=np.zeros_like(f);dp=np.zeros_like(f)
            else:
                raw=_finite(dt_s,'dt_s')
                if raw.ndim or raw<=0 or raw<1/np.finfo(float).max:
                    raise ValueError('dt_s must be positive with a representable inverse')
                h=1/float(raw);den=h+a+b
                if not np.all(np.isfinite(den)) or np.any(den<=0):
                    raise FloatingPointError('trap rate denominator is not representable')
                f=(h*f0+a)/den;empty=(h*(1-f0)+b)/den
                dn=cn*empty/den;dp=-cp*f/den
            rn=cn*n*empty-en*f;rp=cp*p*f-ep*empty
            kn=cn*n+en;kp=cp*p+ep
            out=dict(occupancy=f,empty=empty,df_dn=dn,df_dp=dp,
                charge_C_m2=Q*self.density_m2*((1. if self.kind=='donor' else 0.)-f),
                electron_capture_s=rn,hole_capture_s=rp,
                drn_dn=cn*empty-kn*dn,drn_dp=-kn*dp,
                drp_dn=kp*dn,drp_dp=cp*f+kp*dp,
                electron_activity_s=cn*n*empty+en*f,hole_activity_s=cp*p*f+ep*empty)
        if not all(np.all(np.isfinite(v)) for v in out.values()) or np.any(f<0) or np.any(f>1):
            raise FloatingPointError('trap state or rate is not representable')
        return out
