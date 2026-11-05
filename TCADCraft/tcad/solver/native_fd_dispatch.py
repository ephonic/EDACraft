"""Pack native FD inputs once and assemble reports from actual native outputs."""
from types import SimpleNamespace
import numpy as np
from tcad.physics.native_fermi_local import _decimal
from .cut_cell_transport import Q


def pack_native_fd_inputs(model,old,dt,charge_atol_C,particle_atol,energy_atol_J):
    cells=[]
    for i in range(model.nc):
        cells.extend(_decimal(v) for v in (model.vol[i],model.eps[i],model.rhofix[i],old.n_m3[i],old.p_m3[i],
            model.Nt[i],old.trap_fraction[i],*model.mesh.centroids_m[i],old.temperature_K[i],model.capacity[i],
            model.conductivity[i],model.Ec[i],model.Eh[i],model.mn[i],model.mp[i]))
    faces=[]
    for f,face in enumerate(model.mesh.faces):
        contact=model.contacts.get(f)
        faces.extend(_decimal(v) for v in (face.owner,face.neighbor,*face.area_vector_m2,*face.centroid_m,
            int(f in model.bc),model.bc.get(f,0.),model.area[f],model.do[f],model.dn[f],
            int(f in model.bath),model.bath.get(f,0.),int(contact is not None),
            0. if contact is None else contact.n_m3,0. if contact is None else contact.p_m3,
            0. if contact is None else contact.temperature_K,int(f in model.thermionic_faces),
            model.emission['electrons'].get(f,0.),model.emission['holes'].get(f,0.)))
    valleys=[[v for valley in model.valleys[label] for v in (valley.mass_normal,valley.dos_mass_ratio,
        valley.degeneracy,valley.band_offset_owner_J)] for label in ('electrons','holes')]
    return cells,faces,*valleys,[float(v) for v in (dt,charge_atol_C,particle_atol,energy_atol_J,
        model.T,model.mn_exponent,model.mp_exponent)]


def _poisson_output(model,values,n,p,trap,charge_atol_C):
    potential,electric,flux,mismatch,algebraic,_,metrics=map(np.asarray,values)
    rho=model.rhofix.astype(np.longdouble)+Q*(p-n-model.Nt.astype(np.longdouble)*trap)
    audit=model.mesh.audit_gauss(flux,rho,charge_atol_C=charge_atol_C)
    return dict(cell_potential_V=potential[:model.nc],face_potential_V=potential[model.nc:],
        electric_field_V_m=electric.reshape(model.nc,3),integrated_D_flux_C=flux,
        shared_flux_mismatch_C=mismatch,algebraic_residual_C=algebraic,gauss_audit=audit,
        electrostatic_energy_J=float(metrics[0]),
        valid=bool(metrics[4]==1 and audit['valid'] and np.all(abs(mismatch)<=charge_atol_C) and
            np.all(abs(algebraic)<=charge_atol_C)),execution_backend='native',physical_validated=False)


def native_fd_step(model,old,dt,charge_atol_C,particle_atol,energy_atol_J,max_nfev):
    from tcad.core._bindings import native_fermi_dispatch_raw
    if (model.spectral_backend,model.local_backend,model.poisson_backend,model.nonlinear_backend)!=('native',)*4:
        raise ValueError('native residual backend requires all physics and nonlinear backends native')
    raw=native_fermi_dispatch_raw(*pack_native_fd_inputs(model,old,dt,charge_atol_C,particle_atol,energy_atol_J),max_nfev)
    if raw['density_mantissa_bits']!=np.finfo(np.longdouble).nmant+1:
        raise ValueError('native and NumPy density precision mismatch')
    n=np.asarray(raw['n'],np.longdouble);p=np.asarray(raw['p'],np.longdouble)
    T=np.asarray(raw['temperature'],float)
    a=_poisson_output(model,raw['old_poisson'],old.n_m3.astype(np.longdouble),old.p_m3.astype(np.longdouble),
        old.trap_fraction,charge_atol_C)
    b=_poisson_output(model,raw['new_poisson'],n,p,old.trap_fraction,charge_atol_C)
    if not a['valid'] or not b['valid']:raise ValueError('native FD exported Poisson budget failed')
    local=np.asarray(raw['local'],float);nc=model.nc;nf=len(model.mesh.faces)
    cache={key:local[k*nc:(k+1)*nc] for k,key in enumerate(('rn','rp','delta_u','delta_t','work','energy'))}
    records={}
    for label_index,label in enumerate(('electrons','holes')):
        rows={}
        for f,moments in enumerate(raw['moments'][label_index*nf:(label_index+1)*nf]):
            if not moments:continue
            rows[f]=dict(particle_flux_s=moments[0],total_energy_flux_W=moments[1],material_energy_flux_W=moments[2],
                entropy_production_W_K=moments[3],trace_occupation_min=moments[4],trace_occupation_max=moments[5],
                valley_moments=[dict(name=valley.name,particle_flux_s=moments[6+2*k],total_energy_flux_W=moments[7+2*k])
                    for k,valley in enumerate(model.valleys[label])],trace_closure='energy_resolved_nonthermal_occupations',
                statistics='fermi_dirac',execution_backend='native')
        records[label]=rows
    cache.update(n=n,p=p,T=T,b=b,fn=np.asarray(raw['fn']),fp=np.asarray(raw['fp']),
        eflux=np.asarray(raw['energy_flux']),heat=local[6*nc:],records=records)
    energy=lambda values:dict(zip(('carrier_J','thermal_J','electrostatic_J'),map(float,values)))
    x,stats,history=raw['newton']
    fit=SimpleNamespace(x=np.asarray(x),success=True,nfev=int(stats[0]))
    return cache,energy(raw['old_energy']),a,energy(raw['new_energy']),b,fit,stats,history
