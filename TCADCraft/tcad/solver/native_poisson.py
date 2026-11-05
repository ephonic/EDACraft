"""Native scalar HMM Poisson assembly, factorization, fields and energy."""
import numpy as np
from .cut_cell_transport import _array,Q
from tcad.physics.native_fermi_local import _decimal


def solve_native_state_poisson(mesh,permittivity_F_m,fixed_charge_C_m3,n_m3,p_m3,
        trap_density_m3,trap_fraction,*,dirichlet_V,charge_atol_C):
    from tcad.core._bindings import native_hybrid_poisson_raw
    from tcad.mesh.polyhedral_cut_cell import CutCellMesh
    if not isinstance(mesh,CutCellMesh) or not len(mesh.volumes_m3):
        raise ValueError('nonempty shared cut-cell mesh required')
    nc=len(mesh.volumes_m3);nf=len(mesh.faces)
    if nc+nf>512:raise ValueError('native dense Poisson supports at most 512 cell+face unknowns')
    eps=_array(permittivity_F_m,nc,'native epsilon',positive=True)
    fixed=_array(fixed_charge_C_m3,nc,'fixed charge')
    Nt=_array(trap_density_m3,nc,'trap density',nonnegative=True)
    values=[]
    for value in (n_m3,p_m3,trap_fraction):
        raw=np.asarray(value)
        if raw.dtype.kind not in 'fiu':raise ValueError('finite real native charge state required')
        try:a=np.broadcast_to(raw,(nc,)).astype(np.longdouble)
        except ValueError:raise ValueError('native charge state shape mismatch') from None
        if not np.all(np.isfinite(a)):raise ValueError('finite native charge state required')
        values.append(a)
    n,p,trap=values
    if np.any(n<0) or np.any(p<0) or np.any(trap<0) or np.any(trap>1):
        raise ValueError('native charge densities and trap fraction out of range')
    if (isinstance(charge_atol_C,(bool,np.bool_)) or not np.isscalar(charge_atol_C) or
            not np.isreal(charge_atol_C) or not np.isfinite(charge_atol_C) or charge_atol_C<0):
        raise ValueError('nonnegative native charge budget required')
    if not isinstance(dirichlet_V,dict) or not dirichlet_V:
        raise ValueError('Dirichlet boundary reference required')
    for f,value in dirichlet_V.items():
        if (isinstance(f,(bool,np.bool_)) or not isinstance(f,(int,np.integer)) or not 0<=f<nf or
                mesh.faces[f].neighbor>=0 or isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or
                not np.isreal(value) or not np.isfinite(value)):
            raise ValueError('finite voltage on boundary face required')
    cells=[]
    for c in range(nc):
        cells.extend(_decimal(v) for v in (mesh.volumes_m3[c],eps[c],fixed[c],n[c],p[c],Nt[c],trap[c],
            *mesh.centroids_m[c]))
    faces=[]
    for f,face in enumerate(mesh.faces):
        faces.extend(_decimal(v) for v in (face.owner,face.neighbor,*face.area_vector_m2,*face.centroid_m,
            int(f in dirichlet_V),dirichlet_V.get(f,0.)))
    potential,electric,flux,mismatch,algebraic,gauss,metrics=map(np.asarray,
        native_hybrid_poisson_raw(cells,faces,float(charge_atol_C)))
    # Recheck exported fluxes in the caller's density precision. The native
    # pre-export gate alone cannot validate a lossy public output boundary.
    rho=fixed.astype(np.longdouble)+Q*(p-n-Nt.astype(np.longdouble)*trap)
    audit=mesh.audit_gauss(flux,rho,charge_atol_C=charge_atol_C)
    valid=bool(metrics[4]==1 and audit['valid'] and np.all(abs(mismatch)<=charge_atol_C)
        and np.all(abs(algebraic)<=charge_atol_C))
    return dict(cell_potential_V=potential[:nc],face_potential_V=potential[nc:],
        electric_field_V_m=electric.reshape(nc,3),integrated_D_flux_C=flux,gauss_audit=audit,
        shared_flux_mismatch_C=mismatch,algebraic_residual_C=algebraic,
        electrostatic_energy_J=float(metrics[0]),valid=valid,execution_backend='native',
        scope='native_scalar_epsilon_zero_polarization_hybrid_mimetic_Poisson',
        physical_validated=False,transport_coupled=False)


def solve_native_cut_cell_poisson(mesh,permittivity_F_m,charge_density_C_m3,*,dirichlet_V,charge_atol_C):
    """Standalone fixed-rho entry; no polarization or silent Python fallback."""
    return solve_native_state_poisson(mesh,permittivity_F_m,charge_density_C_m3,0.,0.,0.,.5,
        dirichlet_V=dirichlet_V,charge_atol_C=charge_atol_C)
