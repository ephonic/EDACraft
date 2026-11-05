"""Restricted FE domain-wall and Landau energy closure audit."""
import numpy as np


def audit_domain_energy(times_s, polarization_C_m2, polarization_gradient,
                        cell_volumes_m3, kappa_J_m3, alpha, beta, viscosity,
                        electric_field_V_m, *, converged,
                        energy_scale_J, energy_rtol=1e-6, energy_atol_J=0.):
    """Audit endpoint electric work against Landau, gradient and LK terms.

    ``polarization_gradient`` has shape ``(T,C,3,3)``: time, cell,
    polarization component, spatial derivative.  This explicitly includes
    domain-wall gradient storage; carrier, thermal, trap, leakage and
    electrostatic boundary energies remain outside the declared scope.
    """
    t=np.asarray(times_s,dtype=float); p=np.asarray(polarization_C_m2,dtype=float)
    g=np.asarray(polarization_gradient,dtype=float); vol=np.asarray(cell_volumes_m3,dtype=float)
    e=np.asarray(electric_field_V_m,dtype=float)
    if (t.ndim!=1 or len(t)<2 or not np.all(np.isfinite(t)) or np.any(np.diff(t)<=0)
            or p.ndim!=3 or p.shape[0]!=len(t) or p.shape[2]!=3
            or g.shape!=(len(t),p.shape[1],3,3) or e.shape!=p.shape
            or vol.shape!=(p.shape[1],) or np.any(~np.isfinite(vol)) or np.any(vol<=0)
            or np.any(~np.isfinite(g)) or np.any(~np.isfinite(p)) or np.any(~np.isfinite(e))):
        raise ValueError('invalid FE domain history shapes or nonfinite values')
    if not isinstance(converged,(bool,np.bool_)) and not (np.asarray(converged).dtype==bool and np.asarray(converged).shape==t.shape):
        raise ValueError('converged must be boolean')
    if not np.all(np.asarray(converged)):
        raise ValueError('every domain state must be converged')
    kap=np.asarray(kappa_J_m3,dtype=float)
    if kap.ndim==0: kap=np.full((3,3),float(kap))
    elif kap.shape==(3,): kap=np.diag(kap)
    if kap.shape!=(3,3) or np.any(~np.isfinite(kap)) or np.any(kap<0):
        raise ValueError('kappa must be scalar, (3,), or nonnegative (3,3)')
    a=np.broadcast_to(np.asarray(alpha,dtype=float),vol.shape)
    b=np.broadcast_to(np.asarray(beta,dtype=float),vol.shape)
    gamma=np.broadcast_to(np.asarray(viscosity,dtype=float),vol.shape)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)) or np.any(~np.isfinite(gamma)) or np.any(b<0) or np.any(gamma<=0):
        raise ValueError('invalid Landau coefficients or viscosity')
    scale=float(energy_scale_J); rtol=float(energy_rtol); atol=float(energy_atol_J)
    if not np.isfinite(scale) or scale<=0 or not 0<=rtol<1 or not np.isfinite(atol) or atol<0:
        raise ValueError('invalid explicit energy budgets')
    # Componentwise quadratic terms and full isotropic quartic term.
    landau_density=(.5*a[None,:,None]*p*p).sum(axis=2)+.25*b[None,:]*(np.sum(p*p,axis=2)**2)
    landau_energy=np.sum(landau_density*vol[None,:],axis=1)
    gradient_energy=np.einsum('tcij,ij,tcij,c->t',g,kap,g,vol)*.5
    total_storage=landau_energy+gradient_energy
    dt=np.diff(t)[:,None,None]; dp=np.diff(p,axis=0)
    loss=np.sum(gamma[None,:,None]*dp*dp/dt*vol[None,:,None],axis=(1,2))
    work=np.sum(e[1:]*dp*vol[None,:,None],axis=(1,2))
    storage=np.diff(total_storage)
    residual=work-storage-loss
    budget=atol+rtol*scale
    valid=bool(np.all(np.abs(residual)<=budget))
    return dict(valid=valid, energy_balance_compatible=valid,
        source_work_J=work, landau_storage_change_J=np.diff(landau_energy),
        domain_gradient_storage_change_J=np.diff(gradient_energy),
        lk_dissipation_J=loss, energy_balance_residual_J=residual,
        energy_budget_J=budget, domain_gradient_energy_J=gradient_energy,
        domain_gradient_scope='componentwise_P_gradient_with_full_3x3_kappa',
        complete_device_energy=False, physical_validated=False,
        unavailable_components=['mobile_carrier_free_energy','thermal_storage_and_heat_flux',
            'trap_energy','electrostatic_boundary_work','quantum_energy'])
