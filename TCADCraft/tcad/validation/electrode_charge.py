"""Audit absolute electrode charge against explicitly enclosed free charge."""
from fractions import Fraction

import numpy as np

from tcad.postprocess.terminal_trace import _real_array, _fraction_float


def integrate_electrode_surface_charge(electric_field_V_m, polarization_C_m2,
        permittivity_F_m, outward_dielectric_normals, surface_weights_m2):
    """Integrate Q_electrode = -sum A*(eps*E+P).n over supplied surface samples.

    E, P and the unit normals are (N,3); absolute permittivity and positive area
    weights are (N,). Normals point outward from the dielectric into the metal.
    Weights are physical surface quadrature areas, including any 2-D extrusion.
    The caller must supply appropriate interface-side E/P and complete surface
    sampling. No interpolation, geometry inference, or charge offset is applied.
    Exact arithmetic retains products/cancellation before the float64 export.
    """
    e=_real_array(electric_field_V_m,'electric_field_V_m')
    p=_real_array(polarization_C_m2,'polarization_C_m2')
    eps=_real_array(permittivity_F_m,'permittivity_F_m')
    normals=_real_array(outward_dielectric_normals,'outward_dielectric_normals')
    area=_real_array(surface_weights_m2,'surface_weights_m2')
    if (e.ndim!=2 or e.shape[0]<1 or e.shape[1]!=3 or p.shape!=e.shape
            or normals.shape!=e.shape or eps.shape!=(len(e),) or area.shape!=eps.shape
            or np.any(eps<=0.) or np.any(area<=0.)):
        raise ValueError('require N>=1 E/P/unit normals (N,3), positive permittivity and area weights (N,)')
    if (np.any(np.abs(normals)>1.+1e-12)
            or np.any(np.abs(np.sum(normals*normals,axis=1)-1.)>1e-12)):
        raise ValueError('outward_dielectric_normals must be unit vectors')
    total=Fraction(0)
    for ei,pi,epsi,ni,ai in zip(e,p,eps,normals,area):
        total-=Fraction(float(ai))*sum(((Fraction(float(epsi))*Fraction(float(ec))+
            Fraction(float(pc)))*Fraction(float(nc)) for ec,pc,nc in zip(ei,pi,ni)),Fraction(0))
    return dict(surface_charge_C=_fraction_float(total),surface_samples=len(e),
        convention='minus D dot outward dielectric normal; D=epsilon E+P',
        scope='supplied physical surface quadrature; geometry and sampling declared by caller',
        physical_validated=False)


def audit_electrode_charge_balance(times_s, electrode_charges_C, enclosed_charge_C, *,
        boundary_coverage_complete, converged, charge_scale_C, charge_atol_C, charge_rtol):
    """Check sum(Q_electrodes) + Q_enclosed at every supplied time in SI.

    Electrode charges have shape (N, M), M>=2; times/enclosed charge are (N,).
    Q_enclosed is the signed free volume/interface charge, including fixed,
    mobile and trapped terms as applicable. Bound polarization charge must not
    be counted again when electrode charge is reconstructed from D=eps*E+P.

    The caller must declare complete boundary coverage: all electrode surfaces
    are included and the remaining boundary has zero normal D, or its flux has
    already been included as a boundary charge column. Convergence must be
    explicit True for all samples. The function cannot establish these facts.

    A caller-specified charge scale prevents large opposite terminal baselines
    from hiding missing small volume charge. The budget is atol+rtol*scale.
    Exact sums retain cancellation before the final float64 export. This checks
    supplied absolute charges only; passing does not certify current, geometry,
    unsampled times, a full transient solution, or material calibration.
    """
    t=_real_array(times_s,'times_s')
    q=_real_array(electrode_charges_C,'electrode_charges_C')
    enclosed=_real_array(enclosed_charge_C,'enclosed_charge_C')
    if (t.ndim!=1 or len(t)<1 or np.any(t<0.)
            or q.ndim!=2 or q.shape[0]!=len(t) or q.shape[1]<2
            or enclosed.shape!=t.shape):
        raise ValueError('require N>=1 times, N by M electrode charges (M>=2), and N enclosed charges')
    if any(right<=left for left,right in zip(t[:-1],t[1:])):
        raise ValueError('times_s must be strictly increasing')
    if (not isinstance(boundary_coverage_complete,(bool,np.bool_))
            or not boundary_coverage_complete):
        raise ValueError('boundary_coverage_complete must be explicitly True')
    status=np.asarray(converged)
    if status.dtype.kind!='b' or status.shape not in ((),t.shape) or not np.all(status):
        raise ValueError('converged must be explicitly True at every time')
    def scalar(value,name):
        a=_real_array(value,name)
        if a.shape!=():raise ValueError(name+' must be a real scalar')
        return float(a)
    scale=scalar(charge_scale_C,'charge_scale_C')
    atol=scalar(charge_atol_C,'charge_atol_C')
    rtol=scalar(charge_rtol,'charge_rtol')
    if scale<=0. or atol<0. or not 0.<=rtol<1.:
        raise ValueError('require positive charge scale, nonnegative atol and 0<=rtol<1')
    budget=Fraction(atol)+Fraction(rtol)*Fraction(scale)
    exported_budget=_fraction_float(budget)
    residuals=[sum((Fraction(float(value)) for value in row),Fraction(float(volume)))
        for row,volume in zip(q,enclosed)]
    exported=np.array([_fraction_float(value) for value in residuals])
    compatible=np.array([abs(value)<=budget for value in residuals],dtype=bool)
    return dict(charge_balance_compatible=bool(np.all(compatible)),
        sample_compatible=compatible,charge_balance_residual_C=exported,
        max_abs_charge_balance_residual_C=float(np.max(np.abs(exported))),
        charge_budget_C=exported_budget,charge_scale_C=scale,
        samples=len(t),electrodes=q.shape[1],
        boundary_coverage_declared_complete=True,
        scope='supplied absolute electrode and enclosed free charges; declared boundary coverage',
        trajectory_validated=False,physical_validated=False)
