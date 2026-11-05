"""Isothermal parabolic 2D edge emission with a pinned band-edge barrier.

One-way mode supply per width is q*g*sqrt(2*m)*(kT)**1.5/(2*pi**2*hbar**2)
times the unnormalized Fermi half integral. This is a lateral edge model,
not a vertical surface Richardson law, and contains no tunneling.
"""
import numpy as np
from scipy.special import expit
from tcad.material.sheet import Q, KB, HBAR, M0, _finite, _positive_scalar

_X,_W=np.polynomial.legendre.leggauss(32)


def half_difference(a,b,*,delta_eta=None):
    """H(a)-H(b), H'(a), without subtracting nearly equal supplies.

    t=u^2 removes the square-root endpoint. Composite Gaussian quadrature
    resolves both Fermi edges and truncates only beyond max(eta,0)+80.
    The explicitly qualified eta interval is [-600,200].
    """
    a,b=np.broadcast_arrays(_finite(a,'eta_sheet'),_finite(b,'eta_metal'))
    delta=a-b if delta_eta is None else np.broadcast_to(_finite(delta_eta,'delta_eta'),a.shape)
    if np.any(a < -600) or np.any(b < -600) or np.any(a > 200) or np.any(b > 200):
        raise FloatingPointError('thermionic eta outside qualified interval [-600,200]')
    difference=np.empty(a.shape);derivative=np.empty(a.shape)
    for index in np.ndindex(a.shape):
        x,y=float(a[index]),float(b[index]);high=max(x,y);low=min(x,y)
        knots=sorted(set([0.,max(high,0.)+80.]+[max(0.,z+d) for z in (x,y) for d in (-32.,-8.,0.,8.,32.)]))
        edges=np.sqrt(knots);u=(edges[:-1,None]+edges[1:,None])/2+(edges[1:,None]-edges[:-1,None])/2*_X
        weight=(edges[1:,None]-edges[:-1,None])/2*_W*2*u*u
        d=float(delta[index])
        occupation_delta=expit(high-u*u)*expit(u*u-low)*(-np.expm1(-abs(d)))
        difference[index]=np.sign(d)*np.sum(weight*occupation_delta)
        derivative[index]=np.sum(weight*expit(x-u*u)*expit(u*u-x))
    if not np.all(np.isfinite(difference)) or not np.all(np.isfinite(derivative)) or np.any(derivative<=0):
        raise FloatingPointError('thermionic supply is not representable')
    return difference,derivative


def thermionic_current(drop_eV,barrier_eV,*,temperature_K,mass_m0,degeneracy,width_m,sign):
    """Conventional current into sheet and positive dI/dF_sheet [A/V]."""
    temperature=_positive_scalar(temperature_K,'temperature_K')
    mass=_positive_scalar(mass_m0,'mass_m0');g=_positive_scalar(degeneracy,'degeneracy')
    width=_finite(width_m,'width_m');barrier=_finite(barrier_eV,'barrier_eV');drop=_finite(drop_eV,'drop_eV')
    if sign not in (-1,1) or np.any(width<=0) or np.any(barrier<0):
        raise ValueError('positive width, nonnegative barrier and carrier sign +/-1 required')
    vt=KB*temperature/Q;metal=-barrier/vt
    delta,derivative=half_difference(metal+sign*drop/vt,metal,delta_eta=sign*drop/vt)
    pref=Q*g*np.sqrt(2*mass*M0)*(KB*temperature)**1.5/(2*np.pi**2*HBAR**2)*width
    current=sign*pref*delta;slope=pref*derivative/vt
    if not np.all(np.isfinite(current)) or not np.all(np.isfinite(slope)) or np.any(slope<=0):
        raise FloatingPointError('thermionic current or slope is not representable')
    return current,slope
