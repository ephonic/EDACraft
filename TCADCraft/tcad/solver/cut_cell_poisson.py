"""Conservative hybrid mimetic Poisson solve on shared convex cut cells.

Cell and face potentials are independent unknowns. Linear-consistent gradient
plus face residual stabilization handles skew cut faces without a two-point
orthogonality assumption. Scalar epsilon, fixed rho and cell-constant vector P;
no carrier transport, dynamic FE law or native SG coupling is implied.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def solve_cut_cell_poisson(mesh, permittivity_F_m, charge_density_C_m3, *,
                           dirichlet_V, polarization_C_m2=None,
                           charge_atol_C):
    """Return potentials and one owner-oriented integrated D flux per face.

    ``dirichlet_V`` maps boundary face indices to centroid potential in volts.
    Other boundaries have zero normal D. Explicit absolute charge budget checks
    both local Gauss balance and opposite face fluxes reconstructed per cell.
    """
    from tcad.mesh.polyhedral_cut_cell import CutCellMesh
    if not isinstance(mesh,CutCellMesh) or not len(mesh.volumes_m3):
        raise ValueError('nonempty shared cut-cell mesh required')
    nc=len(mesh.volumes_m3);nf=len(mesh.faces)
    def array(value,shape,name):
        raw=np.asarray(value)
        if raw.dtype.kind not in 'fiu':raise ValueError(name+' must be real')
        a=np.broadcast_to(raw,shape).astype(float).copy()
        if not np.all(np.isfinite(a)):raise ValueError(name+' must be finite')
        return a
    eps=array(permittivity_F_m,(nc,),'permittivity');rho=array(charge_density_C_m3,(nc,),'charge')
    p=array(np.zeros((nc,3)) if polarization_C_m2 is None else polarization_C_m2,(nc,3),'polarization')
    if np.any(eps<=0):raise ValueError('positive scalar cell permittivity required')
    if (isinstance(charge_atol_C,(bool,np.bool_)) or not np.isscalar(charge_atol_C)
            or not np.isfinite(charge_atol_C) or charge_atol_C<0):
        raise ValueError('nonnegative charge budget required')
    if not isinstance(dirichlet_V,dict) or not dirichlet_V: raise ValueError('Dirichlet boundary reference required')
    for f,value in dirichlet_V.items():
        if (isinstance(f,bool) or not isinstance(f,(int,np.integer)) or not 0<=f<nf or mesh.faces[f].neighbor>=0
                or isinstance(value,(bool,np.bool_)) or not np.isscalar(value) or not np.isfinite(value)):
            raise ValueError('Dirichlet map requires boundary face indices and finite voltages')
    incident=[[] for _ in range(nc)]
    for f,face in enumerate(mesh.faces):
        incident[face.owner].append((f,1.))
        if face.neighbor>=0:incident[face.neighbor].append((f,-1.))
    rows=[];cols=[];values=[];rhs=np.r_[rho*mesh.volumes_m3,np.zeros(nf)]
    locals=[]
    for c,neighbors in enumerate(incident):
        ids=np.array([c]+[nc+f for f,_ in neighbors])
        av=np.array([mesh.faces[f].area_vector_m2*sign for f,sign in neighbors])
        dx=np.array([mesh.faces[f].centroid_m-mesh.centroids_m[c] for f,_ in neighbors])
        areas=np.linalg.norm(av,axis=1);distance=np.sum(av*dx,axis=1)/areas
        if np.any(distance<=0):raise ValueError('cut-cell centroid must lie strictly inside its faces')
        gradient=np.column_stack((-av.sum(axis=0),av.T))/mesh.volumes_m3[c]
        difference=np.column_stack((-np.ones(len(neighbors)),np.eye(len(neighbors))))
        residual=difference-dx@gradient
        local=eps[c]*(mesh.volumes_m3[c]*(gradient.T@gradient)+residual.T@((areas/distance)[:,None]*residual))
        load=mesh.volumes_m3[c]*gradient.T@p[c]
        rhs[ids]+=load
        rows.extend(np.repeat(ids,len(ids)));cols.extend(np.tile(ids,len(ids)));values.extend(local.ravel())
        locals.append((ids,local,load,neighbors))
    matrix=coo_matrix((values,(rows,cols)),shape=(nc+nf,nc+nf)).tocsr()
    fixed=np.array([nc+f for f in dirichlet_V],dtype=int)
    free=np.setdiff1d(np.arange(nc+nf),fixed)
    potential=np.zeros(nc+nf);potential[fixed]=list(dirichlet_V.values())
    # Uniform row scaling keeps SI capacitances away from solver absolute scales.
    reduced=matrix[free][:,free];diagonal=reduced.diagonal()
    if np.any(diagonal<=0):raise ValueError('singular cut-cell operator')
    from scipy.sparse import diags
    potential[free]=spsolve(diags(1/diagonal)@reduced,
        (rhs[free]-matrix[free][:,fixed]@potential[fixed])/diagonal)
    if not np.all(np.isfinite(potential)):raise ValueError('nonfinite cut-cell Poisson result')
    flux=np.zeros(nf);opposite=np.zeros(nf);electric=np.empty((nc,3))
    for c,(ids,local,load,neighbors) in enumerate(locals):
        outward=-(local@potential[ids]-load)[1:]
        av=np.array([mesh.faces[f].area_vector_m2*sign for f,sign in neighbors])
        electric[c]=-np.sum(av*(potential[ids][1:]-potential[c])[:,None],axis=0)/mesh.volumes_m3[c]
        for q,(f,sign) in zip(outward,neighbors):
            if sign>0:flux[f]=q
            else:opposite[f]=q
    mismatch=np.array([flux[f]+opposite[f] for f,face in enumerate(mesh.faces) if face.neighbor>=0])
    charge=mesh.audit_gauss(flux,rho,charge_atol_C=charge_atol_C)
    remaining=matrix@potential-rhs
    return dict(cell_potential_V=potential[:nc],face_potential_V=potential[nc:],
        electric_field_V_m=electric,integrated_D_flux_C=flux,gauss_audit=charge,
        shared_flux_mismatch_C=mismatch,algebraic_residual_C=remaining[free],
        electrostatic_energy_J=float(np.longdouble(.5)*np.sum(potential.astype(np.longdouble)*(matrix@potential))),
        valid=bool(charge['valid'] and np.all(abs(mismatch)<=charge_atol_C)
                   and np.all(abs(remaining[free])<=charge_atol_C)),
        scope='convex_cut_cell_scalar_epsilon_fixed_rho_P_hybrid_mimetic_Poisson',
        physical_validated=False,transport_coupled=False)
