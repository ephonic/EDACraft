"""Diffusion-enhanced SG for homogeneous isothermal ideal sheet statistics.

This modified SG scheme uses the secant of log(F(eta)); it is not the exact
non-Boltzmann edge boundary-value solution. The conductance form enforces
zero flux at equal quasi-Fermi levels and nonnegative edge dissipation.
"""
import numpy as np
from scipy.special import expit
from tcad.material.sheet import fermi_one


def _log_occupation(eta,dispersion):
    """log(F), its first and second eta derivatives (DOS prefactor excluded)."""
    eta=np.asarray(eta,dtype=float)
    value=np.empty_like(eta);first=np.empty_like(eta);second=np.empty_like(eta)
    tail=eta<-35.
    # Corrections in this Boltzmann tail are below 3.2e-16 in log(F).
    value[tail]=eta[tail];first[tail]=1.;second[tail]=0.
    e=eta[~tail];f0=np.logaddexp(0.,e);s=expit(e)
    if dispersion=='parabolic':f,df,ddf=f0,s,s*(1-s)
    elif dispersion=='dirac':f,df,ddf=fermi_one(e),f0,s
    else:raise ValueError('dispersion must be parabolic or dirac')
    value[~tail]=np.log(f);first[~tail]=df/f
    second[~tail]=ddf/f-(df/f)**2
    return value,first,second


def _thermal_voltage(a,b,vt,dispersion):
    """VT*g and derivatives wrt endpoint eta; regularized secant near equality."""
    a,b=np.broadcast_arrays(np.asarray(a,dtype=float),np.asarray(b,dtype=float))
    la,da,_=_log_occupation(a,dispersion);lb,db,_=_log_occupation(b,dispersion)
    delta=b-a;close=np.abs(delta)<1e-3
    h=np.empty_like(delta);ha=np.empty_like(delta);hb=np.empty_like(delta)
    far=~close
    h[far]=(lb[far]-la[far])/delta[far]
    ha[far]=(h[far]-da[far])/delta[far];hb[far]=(db[far]-h[far])/delta[far]
    ac,dc=a[close],delta[close]
    hc=np.zeros_like(ac);hac=np.zeros_like(ac);hbc=np.zeros_like(ac)
    for node,weight in ((-.8611363115940526,.3478548451374538),(-.3399810435848563,.6521451548625461),
                        (.3399810435848563,.6521451548625461),(.8611363115940526,.3478548451374538)):
        t=(1+node)/2;_,d,dd=_log_occupation(ac+t*dc,dispersion)
        hc+=weight/2*d;hac+=weight/2*dd*(1-t);hbc+=weight/2*dd*t
    h[close]=hc;ha[close]=hac;hb[close]=hbc
    if not np.all(np.isfinite(h)) or np.any(h<=0):raise FloatingPointError('diffusion enhancement is not representable and positive')
    return vt/h,-vt*ha/h**2,-vt*hb/h**2


def _log_exprel(x):
    """log(expm1(x)/x) and derivative, without large exponentials."""
    x=np.asarray(x,dtype=float);value=np.empty_like(x);derivative=np.empty_like(x)
    small=np.abs(x)<1e-3;pos=x>50;neg=x<-50;middle=~(small|pos|neg)
    t=x[small]
    value[small]=t/2+t*t/24-t**4/2880+t**6/181440
    derivative[small]=.5+t/12-t**3/720+t**5/30240
    t=x[pos];e=np.exp(-t)
    value[pos]=t+np.log1p(-e)-np.log(t);derivative[pos]=1/(1-e)-1/t
    t=x[neg];e=np.exp(t)
    value[neg]=np.log1p(-e)-np.log(-t);derivative[neg]=-e/(1-e)-1/t
    t=x[middle];em1=np.expm1(t)
    value[middle]=np.log(em1/t);derivative[middle]=(em1+1)/em1-1/t
    return value,derivative


def fitted_conductance(phi_i,phi_j,F_i,F_j,eta_i,eta_j,density_i,*,vt,dispersion,sign,prefactor):
    """Positive G and d(log G)/d(phi_i,phi_j,F_i,F_j); I=G*(F_j-F_i).

    prefactor is q*mobility*face_length/edge_length, SI. sign is +1 for
    electrons and -1 for holes in the electron-energy quasi-Fermi convention.
    Inputs are arrays of representable positive endpoint density_i.
    """
    if sign not in (-1,1):raise ValueError('carrier sign must be +1 or -1')
    effective,ri,rj=_thermal_voltage(eta_i,eta_j,vt,dispersion)
    _,li,_=_log_occupation(eta_i,dispersion)
    x=-sign*(phi_j-phi_i)/effective;t=sign*(F_j-F_i)/effective
    ex,dx=_log_exprel(x);et,dt=_log_exprel(t)
    if np.any(density_i<=0):raise FloatingPointError('sheet endpoint density is not representable and positive')
    logG=np.log(prefactor)+np.log(density_i)-ex+et
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        G=np.exp(logG)
        common=(dx*x-dt*t)/effective
        a=common*ri*sign/vt;b=common*rj*sign/vt
        derivatives=(sign*li/vt-sign*dx/effective+a,sign*dx/effective+b,
                     sign*li/vt-sign*dt/effective+a,sign*dt/effective+b)
    if not np.all(np.isfinite(G)) or np.any(G<=0) or not all(np.all(np.isfinite(d)) for d in derivatives):
        raise FloatingPointError('fitted sheet conductance or derivative is not representable')
    return G,derivatives
