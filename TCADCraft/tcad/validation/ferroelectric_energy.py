"""Independent source/storage/dissipation audit for a carrier-free local LK device."""

import numpy as np

from tcad.postprocess.terminal_trace import _real_array
from .electrode_charge import audit_electrode_charge_balance


def audit_ferroelectric_device_energy(times_s, electric_field_V_m,
        polarization_C_m2, cell_volumes_m3, permittivity_F_m,
        ferroelectric_mask, alpha, beta, viscosity,
        electrode_voltages_V, electrode_charges_C, *,
        boundary_coverage_complete, converged, energy_scale_J,
        lk_field_scale_V_m, charge_scale_C, energy_rtol=1e-6, energy_atol_J=0.,
        lk_rtol=1e-6, lk_atol_V_m=0., charge_rtol=1e-6, charge_atol_C=0.,
        dielectric_quadrature=None, electrode_charge_increments_C=None):
    """Audit BE work = dielectric + Landau storage + LK loss + BE corrections.

    E and P are (T,C,3) cell quadrature values on the SAME fixed geometry;
    volumes/absolute permittivity/mask are (C,). Material coefficients are
    scalars or (C,), constant in time, for the componentwise law
    E = alpha*P + beta*P**3 + viscosity*dP/dt inside FE cells. P must be zero
    outside FE cells. No gradient, carriers, free/trapped charge, imprint,
    additional depolarization, thermal or time-dependent material is included.

    Electrode voltages and charges are (T,K), K>=2. Charge is positive on
    the electrode (minus outward dielectric D flux). All driven boundaries
    must be included; the rest have zero normal D. Work uses ENDPOINT voltage
    times charge increment, matching backward Euler, including its signed
    Landau correction. It is NOT trapezoidal physical work. The dielectric
    correction is nonnegative; the Landau correction may be negative for a
    nonconvex free energy and must not be clipped or called dissipation.

    Caller-declared complete boundary coverage/convergence are required.
    Neither geometry coverage nor PDE convergence is inferred from balance.
    Independent charge reconstruction and space/time refinement remain needed.
    Absolute sum(Q)=0 is checked at every time with a separate fixed charge
    scale, including t=0. Zero-voltage work cannot hide unbalanced charge.
    Explicit fixed physical scales set separate energy, local LK and charge budgets;
    opposite terminal work or large background storage cannot hide residuals.
    Returns a closure check for this restricted model, never real-material or
    general whole-device validation. Inputs are read-only; all units are SI.
    Optional dielectric_quadrature=(E(T,H), volume(H), eps(H)) supplies
    material half-edge quadrature for dielectric terms only. Nodal E/P/volume
    still define the LK law; averaging E before squaring is not equivalent.
    Optional stable electrode increments (T-1,K) preserve work below absolute
    snapshot float64 resolution. Their agreement with Q differences is checked
    within an explicit float64 export allowance; absolute charge still audited.
    """
    def real(value, name):
        return _real_array(value, name).astype(np.longdouble)

    def scalar(value, name, positive=False):
        x=real(value, name)
        if x.shape!=() or (x<=0 if positive else x<0):
            raise ValueError(name+' must be a '+('positive' if positive else 'nonnegative')+' real scalar')
        return x[()]

    def export_scalar(value, name):
        result=float(value)
        if not np.isfinite(result) or (value!=0 and result==0):
            raise ValueError('energy audit result outside float64 range: '+name)
        return result

    t=real(times_s, 'times_s');e=real(electric_field_V_m, 'electric_field_V_m')
    p=real(polarization_C_m2, 'polarization_C_m2')
    volume=real(cell_volumes_m3, 'cell_volumes_m3')
    eps=real(permittivity_F_m, 'permittivity_F_m')
    v=real(electrode_voltages_V, 'electrode_voltages_V')
    q=real(electrode_charges_C, 'electrode_charges_C')
    mask=np.asarray(ferroelectric_mask)
    if (t.ndim!=1 or len(t)<2 or np.any(t<0) or np.any(np.diff(t)<=0)
            or e.ndim!=3 or e.shape[0]!=len(t) or e.shape[1]<1 or e.shape[2]!=3
            or p.shape!=e.shape or volume.shape!=(e.shape[1],) or eps.shape!=volume.shape
            or np.any(volume<=0) or np.any(eps<=0)
            or mask.dtype.kind!='b' or mask.shape!=volume.shape or not np.any(mask)
            or v.ndim!=2 or v.shape[0]!=len(t) or v.shape[1]<2 or q.shape!=v.shape):
        raise ValueError('require increasing T>=2 times, E/P (T,C,3), positive volumes/eps and boolean FE mask (C,), V/Q (T,K>=2)')
    if np.any(p[:,~mask]!=0):
        raise ValueError('non-FE cells must have zero polarization')
    if dielectric_quadrature is None:
        de_field=e; de_volume=volume[None,:,None]; de_eps=eps[None,:,None]
    else:
        if not isinstance(dielectric_quadrature,(tuple,list)) or len(dielectric_quadrature)!=3:
            raise ValueError('dielectric quadrature requires E, volume and permittivity')
        de_field,weights,dielectrics=[real(x,'dielectric_quadrature') for x in dielectric_quadrature]
        if (de_field.ndim!=2 or de_field.shape[0]!=len(t) or not de_field.shape[1]
                or weights.shape!=(de_field.shape[1],) or dielectrics.shape!=weights.shape
                or np.any(weights<=0) or np.any(dielectrics<=0)):
            raise ValueError('invalid material dielectric quadrature')
        de_volume=weights[None,:];de_eps=dielectrics[None,:]
    if not isinstance(boundary_coverage_complete,(bool,np.bool_)) or not boundary_coverage_complete:
        raise ValueError('boundary_coverage_complete must be explicitly True')
    status=np.asarray(converged)
    if status.dtype.kind!='b' or status.shape not in ((),t.shape) or not np.all(status):
        raise ValueError('converged must be explicitly True at every time')

    def coefficient(value, name):
        a=real(value,name)
        if a.shape not in ((),volume.shape):
            raise ValueError(name+' must be a real scalar or (C,) array')
        return np.broadcast_to(a,volume.shape)[mask,None]

    a=coefficient(alpha,'alpha');b=coefficient(beta,'beta');g=coefficient(viscosity,'viscosity')
    if np.any(b<0) or np.any(g<=0):
        raise ValueError('FE beta must be nonnegative and viscosity positive')
    scale=scalar(energy_scale_J,'energy_scale_J',True)
    field_scale=scalar(lk_field_scale_V_m,'lk_field_scale_V_m',True)
    er=scalar(energy_rtol,'energy_rtol');ea=scalar(energy_atol_J,'energy_atol_J')
    lr=scalar(lk_rtol,'lk_rtol');la=scalar(lk_atol_V_m,'lk_atol_V_m')
    if er>=1 or lr>=1:
        raise ValueError('relative tolerances must be less than one')
    budget=ea+er*scale;lk_budget=la+lr*field_scale
    charge=audit_electrode_charge_balance(times_s,electrode_charges_C,np.zeros(len(t)),
        boundary_coverage_complete=boundary_coverage_complete,converged=converged,
        charge_scale_C=charge_scale_C,charge_atol_C=charge_atol_C,charge_rtol=charge_rtol)
    dq=np.diff(q,axis=0)
    increment_allowance=np.zeros(dq.shape,dtype=np.longdouble)
    if electrode_charge_increments_C is not None:
        stable=real(electrode_charge_increments_C,'electrode_charge_increments_C')
        if stable.shape!=dq.shape: raise ValueError('electrode charge increments must have shape (T-1,K)')
        increment_allowance=8*np.finfo(float).eps*(abs(q[1:])+abs(q[:-1]))
        if np.any(abs(stable-dq)>increment_allowance):
            raise ValueError('stable charge increments disagree with absolute snapshots beyond export allowance')
        dq=stable
    # Long-double products and factored increments avoid subtracting large
    # nearly equal stored energies; fail if any exported value is out of range.
    with np.errstate(over='raise',invalid='raise',divide='raise',under='raise'):
        try:
            dt=np.diff(t)[:,None,None];de=np.diff(de_field,axis=0)
            old=p[:-1,mask];new=p[1:,mask];dp=new-old
            fvolume=volume[mask,None]
            df=dp*(a*(new+old)/2+b*(new+old)*(new*new+old*old)/4)
            force=a*new+b*new**3
            lk_residual=force+g*dp/dt-e[1:,mask]
            density=de_eps*de*(de_field[1:]+de_field[:-1])/2
            dielectric=np.sum(density*de_volume,axis=tuple(range(1,density.ndim)))
            landau=np.sum(df*fvolume,axis=(1,2))
            loss=np.sum(g*dp*dp/dt*fvolume,axis=(1,2))
            correction=de_eps*de*de/2*de_volume
            dielectric_be=np.sum(correction,axis=tuple(range(1,correction.ndim)))
            # f'(P_new)*dP - df, factored to retain a small BE correction.
            landau_be=np.sum(dp*dp*(a/2+b*(3*new*new+2*new*old+old*old)/4)*fvolume,axis=(1,2))
            work=np.sum(v[1:]*dq,axis=1)
            residual=work-dielectric-landau-loss-dielectric_be-landau_be
            local_max=np.max(abs(lk_residual),axis=(1,2))
            terms=dict(source_work_J=work,dielectric_storage_change_J=dielectric,
                landau_storage_change_J=landau,lk_dissipation_J=loss,
                dielectric_be_correction_J=dielectric_be,landau_be_correction_J=landau_be,
                energy_balance_residual_J=residual,lk_max_field_residual_V_m=local_max)
            result={}
            for name,values in terms.items():
                exported=np.asarray(values,dtype=float)
                if not np.all(np.isfinite(exported)) or np.any((values!=0)&(exported==0)):
                    raise ValueError('energy audit result outside float64 range: '+name)
                result[name]=exported
            for name,value in [('energy_budget_J',budget),('lk_field_budget_V_m',lk_budget)]:
                result[name]=export_scalar(value,name)
        except FloatingPointError as exc:
            raise ValueError('energy audit arithmetic outside supported range') from exc
    energy_ok=bool(np.all(abs(residual)<=budget));lk_ok=bool(np.all(local_max<=lk_budget))
    charge_ok=charge['charge_balance_compatible'] and bool(np.all(abs(dq.sum(axis=1))<=charge['charge_budget_C']))
    result.update(valid=energy_ok and lk_ok and charge_ok,energy_balance_compatible=energy_ok,
        local_lk_compatible=lk_ok,charge_balance_compatible=charge_ok,
        charge_balance_residual_C=charge['charge_balance_residual_C'],
        charge_budget_C=charge['charge_budget_C'],charge_scale_C=charge['charge_scale_C'],
        energy_balance_validated=energy_ok and lk_ok and charge_ok,
        energy_balance_scope='fixed_geometry_carrier_free_componentwise_local_LK_backward_Euler',
        complete_device_energy=False,physical_validated=False,
        boundary_coverage_declared_complete=True,pde_convergence_declared=True,
        geometry_coverage_verified=False,source_work_quadrature='backward_Euler_endpoint',
        energy_scale_J=float(scale),lk_field_scale_V_m=float(field_scale),
        max_energy_relative_residual=export_scalar(np.max(abs(residual))/scale,'max_energy_relative_residual'),
        max_lk_relative_residual=export_scalar(np.max(local_max)/field_scale,'max_lk_relative_residual'))
    result['stable_charge_increments_used']=electrode_charge_increments_C is not None
    result['charge_increment_snapshot_allowance_C']=np.asarray(increment_allowance,dtype=float)
    return result
