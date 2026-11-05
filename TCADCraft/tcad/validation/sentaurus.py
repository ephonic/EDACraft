"""Explicit unit/convention bridge for the shared, local cubic LK model.

Sentaurus Device W-2024.09 User Guide, chapter 29, equation (991):
rho*dP/dt + 2*alpha*P + 4*beta*P**3 + 6*gamma*P**5
             - 2*g*laplacian(P) - E = 0, in C/cm² and V/cm.
Native: fe_gamma*dP/dt + alpha*P + beta*P**3 - E = 0, in SI.
This bridge does not equate NLS/Preisach with LK or calibrate a material.
"""
from collections.abc import Mapping
import math
from decimal import Decimal, localcontext
from numbers import Real


def sentaurus_fn_to_native(parameters, *, barrier_eV, semiconductor_to_gate_sign):
    """Map explicit FowlerModel coefficients to high-level set_leakage kwargs.

    W-2024.09 UG Eq.832/Table147: J=A*F_ins**2*exp(-B/F_ins),
    F_ins in V/cm and J in A/cm². Native E is V/m and J is A/m²:
    A is unchanged and B_native*barrier_eV**1.5 = 100*B_sentaurus.
    A positive field from gate toward Si uses write (Aw,Bw); the opposite
    direction uses erase (Ae,Be). Declare whether Si->gate follows (+1)
    or opposes (-1) the native axis; no geometry/orientation is inferred.
    PF, field floor and conductivity cap are disabled for exact law matching.
    Gm!=1 needs carrier generation, which this local leakage path cannot map.
    This bridge does not implement interface carrier injection, direct or
    nonlocal tunneling, nor establish a physical ultrathin-oxide model.
    """
    expected={'Aw','Bw','Ae','Be','Gm'}
    if not isinstance(parameters, Mapping) or set(parameters)!=expected:
        raise ValueError('provide exactly Aw, Bw, Ae, Be and Gm')
    p={name:_scalar(value,name) for name,value in parameters.items()}
    barrier=_scalar(barrier_eV,'barrier_eV')
    orientation=_scalar(semiconductor_to_gate_sign,'semiconductor_to_gate_sign')
    if barrier<=0.: raise ValueError('barrier_eV must be positive')
    if orientation not in (-1.,1.): raise ValueError('semiconductor_to_gate_sign must be -1 or +1')
    if any(p[k]<0. for k in ('Aw','Bw','Ae','Be')):
        raise ValueError('Fowler coefficients must be nonnegative')
    if p['Gm']!=1.: raise ValueError('Gm!=1 requires unsupported carrier multiplication')
    def exponent(value):
        # Avoid overflow/underflow of barrier**1.5 as an intermediate.
        with localcontext() as context:
            context.prec=80
            phi=Decimal.from_float(barrier)
            scaled=Decimal.from_float(value)*100/(phi*phi.sqrt())
            result=float(scaled)
        if not math.isfinite(result): raise ValueError('FN conversion exceeds finite parameter range')
        if result==0. and scaled!=0: raise ValueError('FN conversion underflow loses a nonzero coefficient')
        return result
    erase=(p['Ae'],exponent(p['Be']));write=(p['Aw'],exponent(p['Bw']))
    positive,negative=(erase,write) if orientation==1. else (write,erase)
    return dict(pf_C=0.,pf_B=0.,pf_phi_t=0.,fn_C=0.,fn_B=0.,fn_phi_b=barrier,
        fn_C_positive=positive[0],fn_B_positive=positive[1],
        fn_C_negative=negative[0],fn_B_negative=negative[1],E_floor=0.,sigma_cap=0.)


def _scalar(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar")
    original = value
    try:
        value = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{name} must be a finite real scalar") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real scalar")
    if value == 0. and original != 0:
        raise ValueError(f"{name} underflow would change a nonzero coefficient to zero")
    return value


def native_lk_to_sentaurus(alpha, beta, fe_gamma):
    """Return a Sentaurus ``FEPolarization`` parameter dictionary.

    Native alpha [m/F], beta [m^5/(F C^2)], fe_gamma [ohm m].
    Output alpha [cm/F], beta [cm^5/(F C^2)], rho [ohm cm].
    Sentaurus gamma is a sixth-order energy coefficient, NOT native viscosity.
    Only beta > 0, fe_gamma > 0, and zero gradient/sextic terms are supported.
    """
    alpha, beta, viscosity = (_scalar(alpha, "alpha"), _scalar(beta, "beta"),
                              _scalar(fe_gamma, "fe_gamma"))
    if beta <= 0. or viscosity <= 0.:
        raise ValueError("cubic dynamic LK requires beta > 0 and fe_gamma > 0")
    result = dict(alpha=alpha*50., beta=beta*2.5e9,
                  gamma=0., g=0., rho=viscosity*100.)
    if any(not math.isfinite(v) for v in result.values()):
        raise ValueError("LK conversion exceeds the finite parameter range")
    if result["beta"] == 0. or result["rho"] == 0.:
        raise ValueError("LK conversion loses a positive parameter to underflow")
    return result


def sentaurus_lk_to_native(parameters):
    """Import explicit alpha/beta/gamma/g/rho; reject unsupported physics.

    No installed-tool defaults are assumed: all five coefficients are required.
    The returned ``fe_gamma`` configures native transient viscosity.
    """
    expected = {"alpha", "beta", "gamma", "g", "rho"}
    if not isinstance(parameters, Mapping) or set(parameters) != expected:
        raise ValueError("provide exactly alpha, beta, gamma, g and rho")
    p = {k: _scalar(v, k) for k, v in parameters.items()}
    if p["gamma"] != 0. or p["g"] != 0.:
        raise ValueError("native cubic LK import requires gamma=0 and g=0")
    if p["beta"] <= 0. or p["rho"] <= 0.:
        raise ValueError("cubic dynamic LK requires beta > 0 and rho > 0")
    result = dict(alpha=p["alpha"]/50., beta=p["beta"]/2.5e9,
                  fe_gamma=p["rho"]/100.)
    if (result["beta"] == 0. or result["fe_gamma"] == 0.
            or (p["alpha"] != 0. and result["alpha"] == 0.)):
        raise ValueError("LK conversion loses a positive parameter to underflow")
    return result
