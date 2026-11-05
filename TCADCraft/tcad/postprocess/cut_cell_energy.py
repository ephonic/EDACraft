"""Independent state/flux audit of the scoped cut-cell multiphysics step."""
import numpy as np
from tcad.solver.cut_cell_transport import CutCellTransport,Q,_array


def audit_cut_cell_energy(model,old,new,step_report,*,charge_atol_C,particle_atol,energy_atol_J):
    """Recompute constitutive fluxes, capture heat, storage and boundary work.

    Does not trust report validity flags, supplied energy increments or total
    heat. Absolute gates apply to cell particle and thermal equations, global
    energy, and independently recomputed report values. Electronic temperature
    remains fixed; full native thermodynamic coupling is still unavailable.
    """
    if not isinstance(model,CutCellTransport):raise ValueError('CutCellTransport model required')
    from tcad.solver.electrothermal_cut_cell import ElectrothermalCutCellTransport
    if isinstance(model,ElectrothermalCutCellTransport):
        from .electrothermal_energy import audit_electrothermal_cut_cell_energy
        return audit_electrothermal_cut_cell_energy(model,old,new,step_report,
            charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J)
    for name,value in dict(charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J).items():
        _array(value,1,name,positive=True)
    model._validate_state(old);model._validate_state(new)
    dt=new.time_s-old.time_s
    if dt<=0:raise ValueError('strictly increasing state clock required')
    _,a=model.energies(old,charge_atol_C=charge_atol_C)
    _,b=model.energies(new,charge_atol_C=charge_atol_C)
    increments=model.energy_increments(old,new,a,b)
    nf=len(model.mesh.faces);nc=model.nc;vol=model.vol
    fn=_array(step_report['integrated_electron_particle_flux_s'],nf,'electron face flux')
    fp=_array(step_report['integrated_hole_particle_flux_s'],nf,'hole face flux')
    rn=_array(step_report['trap_electron_capture_rate_s'],nc,'electron capture')
    rp=_array(step_report['trap_hole_capture_rate_s'],nc,'hole capture')
    boundary=np.array([f for f,face in enumerate(model.mesh.faces) if face.neighbor<0],int)
    closed=bool(np.all(fn[boundary]==0) and np.all(fp[boundary]==0))
    divergence_n=model.mesh.divergence_integrals(fn);divergence_p=model.mesh.divergence_integrals(fp)
    particle=np.r_[vol*(new.n_m3-old.n_m3+dt*model.Nt*rn)+dt*divergence_n,
        vol*(new.p_m3-old.p_m3+dt*model.Nt*rp)+dt*divergence_p,
        vol*model.Nt*(new.trap_fraction-old.trap_fraction-dt*(rn-rp))]
    qn=model._quantum(new.n_m3,model.kn);qp=model._quantum(new.p_m3,model.kp)
    expected_fn=model._flux(new.n_m3,b['cell_potential_V'],model.Ec,model.Nc,model.mn,-1,qn)
    expected_fp=model._flux(new.p_m3,b['cell_potential_V'],model.Eh,model.Nv,model.mp,1,qp)
    n1=model.Nc*np.exp(np.clip((model.Et-model.Ec-qn)/model.kt,-690,690))
    p1=model.Nv*np.exp(np.clip((-model.Et-model.Eh-qp)/model.kt,-690,690))
    expected_rn=model.cn*(new.n_m3*(1-new.trap_fraction)-n1*new.trap_fraction)
    expected_rp=model.cp*(new.p_m3*new.trap_fraction-p1*(1-new.trap_fraction))
    constitutive=np.r_[dt*(fn[model.internal]-expected_fn),dt*(fp[model.internal]-expected_fp),
        dt*vol*model.Nt*(rn-expected_rn),dt*vol*model.Nt*(rp-expected_rp)]
    midphi=(a['cell_potential_V']+b['cell_potential_V'])/2
    qndg=model._quantum(new.n_m3,model.kn,old.n_m3);qpdg=model._quantum(new.p_m3,model.kp,old.p_m3)
    en=model.Ec+1.5*model.kt+qndg-Q*midphi;ep=model.Eh+1.5*model.kt+qpdg+Q*midphi
    i,j=model.i,model.j
    face_heat=dt*(fn[model.internal]*(en[i]-en[j])+fp[model.internal]*(ep[i]-ep[j]))
    capture_heat=dt*vol*model.Nt*(rn*(model.Ec+1.5*model.kt+qndg-model.Et)+
        rp*(model.Eh+1.5*model.kt+qpdg+model.Et))
    heat=capture_heat+np.bincount(i,face_heat/2,minlength=nc)+np.bincount(j,face_heat/2,minlength=nc)
    ka,kb=model.conductivity[i],model.conductivity[j]
    conducted=2*ka*kb/(ka+kb)*model.metric*(new.temperature_K[i]-new.temperature_K[j])
    thermal=vol*model.capacity*(new.temperature_K-old.temperature_K)+dt*model._div(conducted)-heat
    heat_out=0.
    for f,temp in model.bath.items():
        face=model.mesh.faces[f];c=face.owner;area=np.linalg.norm(face.area_vector_m2)
        dist=np.dot(face.area_vector_m2,face.centroid_m-model.mesh.centroids_m[c])/area
        outgoing=dt*model.conductivity[c]*area/dist*(new.temperature_K[c]-temp)
        thermal[c]+=outgoing;heat_out+=outgoing
    source=sum(-v*(b['integrated_D_flux_C'][f]-a['integrated_D_flux_C'][f]) for f,v in model.bc.items())
    residual=float(np.longdouble(source)-sum(map(np.longdouble,increments.values()))-np.longdouble(heat_out))
    expected=dict(source_work_J=source,outward_heat_J=heat_out,transport_heat_J=face_heat.sum(),
        capture_heat_J=capture_heat.sum(),energy_residual_J=residual)
    report_errors={k:float(step_report[k])-float(v) for k,v in expected.items()}
    report_errors.update({'increment_'+k:float(step_report['energy_increments_J'][k])-v for k,v in increments.items()})
    if not np.all(np.isfinite(list(report_errors.values()))):raise ValueError('nonfinite reported energy')
    valid=(closed and a['valid'] and b['valid'] and np.max(abs(particle),initial=0)<=particle_atol
        and np.max(abs(constitutive),initial=0)<=particle_atol and np.max(abs(thermal),initial=0)<=energy_atol_J
        and abs(residual)<=energy_atol_J and max(map(abs,report_errors.values()),default=0)<=energy_atol_J)
    return dict(valid=bool(valid),complete_device_energy=False,physical_validated=False,
        scope='independent_state_flux_SG_SRH_graph_DG_lattice_heat_audit',
        energy_increments_J=increments,energy_residual_J=residual,thermal_cell_residuals_J=thermal,
        particle_cell_residuals=particle,constitutive_particle_residuals=constitutive,
        report_errors_J=report_errors,closed_particle_boundaries=closed,
        missing_physics=list(step_report.get('missing_physics',[])))
