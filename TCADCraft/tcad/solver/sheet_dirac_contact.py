"""Ideal gapless Dirac edge mode supply; no extra Schottky barrier/filter.

M(E)/width=g*abs(E-ED)/(pi*hbar*vF), with separate conduction/valence
supplies, unit transmission and an abundant isothermal metal reservoir.
"""
import numpy as np
from scipy.special import expit
from tcad.material.sheet import Q,KB,HBAR,_finite,_positive_scalar

_X,_W=np.polynomial.legendre.leggauss(32)


def linear_difference(a,b,*,delta_eta=None):
    """F1(a)-F1(b), F1'(a), by direct integration of the occupation difference."""
    a,b=np.broadcast_arrays(_finite(a,'eta_sheet'),_finite(b,'eta_metal'))
    delta=a-b if delta_eta is None else np.broadcast_to(_finite(delta_eta,'delta_eta'),a.shape)
    if np.any(a < -600) or np.any(b < -600) or np.any(a > 200) or np.any(b > 200):
        raise FloatingPointError('Dirac contact eta outside qualified interval [-600,200]')
    difference=np.empty(a.shape)
    for index in np.ndindex(a.shape):
        x,y=float(a[index]),float(b[index]);high=max(x,y);low=min(x,y)
        knots=sorted(set([0.,max(high,0.)+80.]+[max(0.,z+d) for z in (x,y) for d in (-32.,-8.,0.,8.,32.)]))
        edges=np.array(knots);half=(edges[1:]-edges[:-1])/2
        t=(edges[:-1,None]+edges[1:,None])/2+half[:,None]*_X
        weight=half[:,None]*_W*t;d=float(delta[index])
        occupation_delta=expit(high-t)*expit(t-low)*(-np.expm1(-abs(d)))
        difference[index]=np.sign(d)*np.sum(weight*occupation_delta)
    derivative=np.logaddexp(0.,a)
    if not np.all(np.isfinite(difference)) or not np.all(np.isfinite(derivative)) or np.any(derivative<=0):
        raise FloatingPointError('Dirac mode supply is not representable')
    return difference,derivative


def dirac_edge_current(drop_eV,edge_offset_eV,*,temperature_K,fermi_velocity_m_s,degeneracy,width_m,sign):
    """Conventional current into sheet, dI/dF_sheet; signed carrier edge offset."""
    temperature=_positive_scalar(temperature_K,'temperature_K')
    velocity=_positive_scalar(fermi_velocity_m_s,'fermi_velocity_m_s')
    g=_positive_scalar(degeneracy,'degeneracy');width=_finite(width_m,'width_m')
    offset=_finite(edge_offset_eV,'edge_offset_eV');drop=_finite(drop_eV,'drop_eV')
    if isinstance(sign,(bool,np.bool_)) or sign not in (-1,1) or np.any(width<=0):
        raise ValueError('positive width and carrier sign +/-1 required')
    vt=KB*temperature/Q;metal=-offset/vt
    delta,derivative=linear_difference(metal+sign*drop/vt,metal,delta_eta=sign*drop/vt)
    pref=Q*g*(KB*temperature)**2/(2*np.pi**2*HBAR**2*velocity)*width
    current=sign*pref*delta;slope=pref*derivative/vt
    if not np.all(np.isfinite(current)) or not np.all(np.isfinite(slope)) or np.any(slope<=0):
        raise FloatingPointError('Dirac contact current or slope is not representable')
    return current,slope
