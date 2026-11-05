"""Reconstruct monolithic open-contact energy/charge/heat balances from states."""
import numpy as np
from tcad.solver.cut_cell_transport import Q,KB,_array
from tcad.solver.electrothermal_cut_cell import ElectrothermalCutCellTransport


def audit_electrothermal_cut_cell_energy(model,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J):
    if not isinstance(model,ElectrothermalCutCellTransport):raise ValueError('electrothermal cut-cell model required')
    for name,value in dict(charge_atol_C=charge_atol_C,particle_atol=particle_atol,energy_atol_J=energy_atol_J).items():
        _array(value,1,name,positive=True)
    model._validate_state(old);model._validate_state(new);dt=new.time_s-old.time_s
    if not np.isfinite(dt) or dt<=0:raise ValueError('strictly increasing state clock required')
    _,a=model.energies(old,charge_atol_C=charge_atol_C);_,b=model.energies(new,charge_atol_C=charge_atol_C)
    increments=model.energy_increments(old,new,a,b);nc=model.nc;nf=len(model.mesh.faces);vol=model.vol
    fn=_array(report['integrated_electron_particle_flux_s'],nf,'electron face flux')
    fp=_array(report['integrated_hole_particle_flux_s'],nf,'hole face flux')
    energy_flux=_array(report['integrated_carrier_energy_flux_W'],nf,'carrier energy flux')
    heat_flux=_array(report['integrated_heat_flux_W'],nf,'heat flux')
    rn=_array(report['trap_electron_capture_rate_s'],nc,'electron capture rate')
    rp=_array(report['trap_hole_capture_rate_s'],nc,'hole capture rate')
    expected_fn,expected_fp,expected_rn,expected_rp,_,_=model.transport(new.n_m3,new.p_m3,new.trap_fraction,new.temperature_K,b)
    constitutive=np.r_[dt*(fn-expected_fn),dt*(fp-expected_fp),dt*vol*model.Nt*(rn-expected_rn),dt*vol*model.Nt*(rp-expected_rp)]
    particle=np.r_[vol*(new.n_m3-old.n_m3+dt*model.Nt*rn)+dt*model.mesh.divergence_integrals(fn),
        vol*(new.p_m3-old.p_m3+dt*model.Nt*rp)+dt*model.mesh.divergence_integrals(fp),
        vol*model.Nt*(new.trap_fraction-old.trap_fraction-dt*(rn-rp))]
    midT=(old.temperature_K+new.temperature_K)/2
    midphi=(a['cell_potential_V']+b['cell_potential_V'])/2
    facephi=(a['face_potential_V']+b['face_potential_V'])/2
    qn,qp=model.quantum_potentials(new.n_m3,new.p_m3,old.n_m3,old.p_m3)
    en=model.Ec+1.5*KB*midT+qn-Q*midphi;ep=model.Eh+1.5*KB*midT+qp+Q*midphi
    capture=dt*vol*model.Nt*(rn*(model.Ec+1.5*KB*midT+qn-model.Et)+rp*(model.Eh+1.5*KB*midT+qp+model.Et))
    # Independently form the divergence of transported energy, rather than
    # taking the step's assembled heat vector or its global heat totals.
    heat=(dt*en*model.mesh.divergence_integrals(fn)+dt*ep*model.mesh.divergence_integrals(fp)-
        dt*model.mesh.divergence_integrals(energy_flux+Q*facephi*(fp-fn))+capture)
    capacity=vol*(model.capacity+1.5*KB*(new.n_m3+old.n_m3+new.p_m3+old.p_m3)/2)
    thermal=capacity*(new.temperature_K-old.temperature_K)+dt*model.mesh.divergence_integrals(heat_flux)-heat
    _,expected_transport_heat,expected_capture_heat,expected_carrier_out,expected_eflux=model.heat_terms(
        old,new.n_m3,new.p_m3,new.temperature_K,a,b,expected_fn,expected_fp,expected_rn,expected_rp,dt)
    expected_conduction=model.conduction(new.temperature_K)
    energy_flux_error=dt*(energy_flux-expected_eflux);heat_flux_error=dt*(heat_flux-expected_conduction)
    boundary=np.array([f for f,face in enumerate(model.mesh.faces) if face.neighbor<0],int)
    reflecting=np.array([f for f in boundary if f not in model.contacts],int)
    reflecting_valid=bool(np.all(fn[reflecting]==0) and np.all(fp[reflecting]==0))
    dq=b['integrated_D_flux_C']-a['integrated_D_flux_C'];qflux=Q*(fp-fn)
    terminal={int(f):-dq[f]/dt-qflux[f] for f in model.bc}
    given=report['terminal_currents_A']
    if not isinstance(given,dict) or set(given)!=set(terminal):raise ValueError('terminal current coverage mismatch')
    current_error=np.array([dt*(float(given[f])-value) for f,value in terminal.items()])
    if not np.all(np.isfinite(current_error)):raise ValueError('nonfinite terminal current')
    displacement=-sum(v*dq[f] for f,v in model.bc.items())
    conduction=-dt*sum(v*qflux[f] for f,v in model.bc.items());source=displacement+conduction
    carrier_out=dt*float(np.sum(energy_flux[boundary],dtype=np.longdouble))
    heat_out=dt*float(np.sum(heat_flux[boundary],dtype=np.longdouble))
    residual=float(np.longdouble(source)-sum(map(np.longdouble,increments.values()))-np.longdouble(carrier_out)-np.longdouble(heat_out))
    charge=float(Q*np.sum(vol.astype(np.longdouble)*(new.p_m3.astype(np.longdouble)-old.p_m3-new.n_m3.astype(np.longdouble)+old.n_m3-
        model.Nt.astype(np.longdouble)*(new.trap_fraction.astype(np.longdouble)-old.trap_fraction)))+
        dt*np.sum(qflux[boundary],dtype=np.longdouble))
    expected=dict(source_work_J=source,displacement_work_J=displacement,conduction_work_J=conduction,
        outward_carrier_energy_J=carrier_out,outward_heat_J=heat_out,energy_residual_J=residual,
        transport_heat_J=expected_transport_heat,capture_heat_J=expected_capture_heat)
    errors={key:float(report[key])-float(value) for key,value in expected.items()}
    errors.update({'increment_'+key:float(report['energy_increments_J'][key])-value for key,value in increments.items()})
    if not np.all(np.isfinite(list(errors.values()))):raise ValueError('nonfinite reported energy')
    quantum_chain=float(np.sum(vol.astype(np.longdouble)*(qn.astype(np.longdouble)*(new.n_m3.astype(np.longdouble)-old.n_m3)+
        qp.astype(np.longdouble)*(new.p_m3.astype(np.longdouble)-old.p_m3)))-increments['quantum_J'])
    valid=(a['valid'] and b['valid'] and reflecting_valid and np.max(abs(particle),initial=0)<=particle_atol
        and np.max(abs(constitutive),initial=0)<=particle_atol and np.max(abs(thermal),initial=0)<=energy_atol_J
        and max(np.max(abs(energy_flux_error),initial=0),np.max(abs(heat_flux_error),initial=0),abs(quantum_chain),
            abs(residual),max(map(abs,errors.values()),default=0))<=energy_atol_J
        and max(abs(charge),abs(dt*sum(terminal.values())),np.max(abs(current_error),initial=0))<=charge_atol_C)
    named_audit=None
    groups=getattr(model,'terminal_groups',None)
    if groups is not None:
        from .cut_cell_terminals import integrate_cut_cell_terminals,audit_named_terminals
        expected_named=integrate_cut_cell_terminals(model.mesh,model.bc,groups,a,b,fn,fp,energy_flux,heat_flux,dt)
        coverage=report.get('terminal_groups')=={name:list(faces) for name,faces in groups.items()}
        named_audit=audit_named_terminals(expected_named,report.get('terminals'),dt_s=dt,
            charge_atol_C=charge_atol_C,energy_atol_J=energy_atol_J)
        valid=valid and coverage and named_audit['valid']
    elif 'terminals' in report or 'terminal_groups' in report:
        valid=False
    return dict(valid=bool(valid),named_terminal_audit=named_audit,complete_device_energy=False,physical_validated=False,
        scope='independent_monolithic_open_contact_electrothermal_energy',temperature_feedback=True,
        energy_increments_J=increments,energy_residual_J=residual,source_work_J=float(source),
        outward_heat_J=heat_out,outward_carrier_energy_J=carrier_out,cell_heat_residuals_J=np.asarray(thermal,float),
        particle_residuals=np.asarray(particle,float),constitutive_particle_residuals=np.asarray(constitutive,float),
        carrier_energy_flux_errors_J=energy_flux_error,heat_flux_errors_J=heat_flux_error,report_errors_J=errors,
        quantum_chain_rule_residual_J=quantum_chain,charge_balance_residual_C=charge,
        terminal_KCL_residual_C=float(dt*sum(terminal.values())),reflecting_boundaries_valid=reflecting_valid,
        missing_physics=list(report.get('missing_physics',[])))
