"""Independent accepted-path fixed-band signed-energy conservation audit."""
from math import fsum
import numpy as np
from .fermi_spectral_energy import reference_reservoir,reference_face
from .device_energy_coordinate_transport import audit_device_energy_coordinate_step
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
from tcad.solver.cut_cell_transport import Q
from tcad.solver.adaptive_three_temperature import _scalar
from .energy_coordinate_generation import generation_increments
from .energy_coordinate_exchange import exchange_increments
from .energy_coordinate_radiative import radiative_increments


def _same(a,b):
    return (a.configuration_sha256==b.configuration_sha256 and a.excess_J_m3==b.excess_J_m3
        and a.thermal.time_s==b.thermal.time_s and all(np.array_equal(getattr(a.thermal,f),getattr(b.thermal,f))
        for f in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K','trap_fraction')))


def _poisson(model,state,charge):
    s=state.thermal;ld=np.longdouble
    result=solve_cut_cell_poisson(model.mesh,model.eps,model.rhofix.astype(ld)+Q*(s.p_m3-s.n_m3),
        dirichlet_V=model.bc,charge_atol_C=charge)
    if not result['valid']:raise ValueError('trajectory independent Poisson audit failed')
    return result


def _storage(model,old,new,charge):
    """Use lattice-equilibrium FD energy plus authoritative excess, never Tc."""
    ld=np.longdouble;V=model.vol.astype(ld);out={};cells={}
    for s,(label,field,band) in enumerate((('electrons','n_m3',model.Ec),('holes','p_m3',model.Eh))):
        def eq(state):
            t=state.thermal
            return np.array([reference_reservoir(n,T,b,model.valleys[label])['energy_density_J_m3']
                for n,T,b in zip(getattr(t,field),t.temperature_K,band)],ld)
        delta=eq(new)-eq(old)+np.array(new.excess_J_m3[s::2],ld)-np.array(old.excess_J_m3[s::2],ld)
        cells[label]=V*delta
        out[label]=float(np.sum(cells[label],dtype=ld))
    cells['lattice']=V*model.capacity*(new.thermal.temperature_K.astype(ld)-old.thermal.temperature_K)
    out['lattice']=float(np.sum(cells['lattice'],dtype=ld))
    out['electrostatic']=float(ld(_poisson(model,new,charge)['electrostatic_energy_J'])-ld(_poisson(model,old,charge)['electrostatic_energy_J']))
    return out,cells


def _ports(model,old,new,charge):
    """Reintegrate every face and cell electrical work; ignore native ledgers."""
    state=new.thermal;dt=state.time_s-old.thermal.time_s;field=_poisson(model,new,charge);result={};cells={};work=[]
    before=_poisson(model,old,charge)
    midphi=(before['cell_potential_V']+field['cell_potential_V'])/2
    midface=(before['face_potential_V']+field['face_potential_V'])/2
    wanted=set(map(int,model.internal))|set(map(int,model.contact_faces))
    for label,density,T,z,band,base,exponent in (
        ('electrons',state.n_m3,state.electron_temperature_K,-1,model.Ec,model.mn,model.mn_exponent),
        ('holes',state.p_m3,state.hole_temperature_K,1,model.Eh,model.mp,model.mp_exponent)):
        reservoirs=[reference_reservoir(density[i],T[i],band[i],model.valleys[label]) for i in range(model.nc)]
        flux=np.zeros(len(model.mesh.faces));energy=np.zeros_like(flux)
        for f in sorted(wanted):
            face=model.mesh.faces[f];i,j=face.owner,face.neighbor
            if j>=0:
                two=reservoirs[j];phi=field['cell_potential_V'][j];mu=base[j]*(model.T/state.temperature_K[j])**exponent
            else:
                contact=model.contacts[f]
                two=reference_reservoir(contact.n_m3 if z<0 else contact.p_m3,contact.temperature_K,band[i],model.valleys[label])
                phi=model.bc[f];mu=base[i]*(model.T/contact.temperature_K)**exponent
            ref=reference_face(reservoirs[i],two,model.valleys[label],phi_o=field['cell_potential_V'][i],phi_n=phi,
                phi_f=field['face_potential_V'][f],z=z,mu_o=base[i]*(model.T/state.temperature_K[i])**exponent,
                mu_n=mu,area=model.area[f],do=model.do[f],dn=model.dn[f],
                A=model.emission[label].get(f),bulk_potential_path=model.bulk_potential_path)
            flux[f]=ref['particle_flux_s'];energy[f]=ref['material_energy_flux_W']
        result[label]=fsum(dt*energy[f] for f in model.contact_faces)
        cells[label]=dt*model.mesh.divergence_integrals(energy)
        cells['particle_'+label]=np.longdouble(dt)*model.mesh.divergence_integrals(flux).astype(np.longdouble)
        current=z*Q*flux
        work.append(dt*(midphi*model.mesh.divergence_integrals(current)-model.mesh.divergence_integrals(midface*current)))
    heat=np.zeros(len(model.mesh.faces))
    for f,face in enumerate(model.mesh.faces):
        i,j=face.owner,face.neighbor
        if j>=0:heat[f]=model.area[f]/(model.do[f]/model.conductivity[i]+model.dn[f]/model.conductivity[j])*(state.temperature_K[i]-state.temperature_K[j])
        elif f in model.bath:heat[f]=model.area[f]*model.conductivity[i]/model.do[f]*(state.temperature_K[i]-model.bath[f])
    result['lattice']=fsum(dt*heat[f] for f in model.bath)
    cells['lattice']=dt*model.mesh.divergence_integrals(heat)
    return result,cells,work


def _particle_path(model,initial,final,increments,transport,generated,budget):
    """Check each cell before species sums; use density, never rounded Tc."""
    ld=np.longdouble;labels=('electrons','holes');V=model.vol.astype(ld)
    def total(rows):
        arrays=[np.asarray(v,ld) for v in rows]
        if any(v.shape!=(model.nc,) or not np.all(np.isfinite(v)) for v in arrays):
            raise ValueError('finite complete independently reconstructed particle path required')
        result=np.sum(arrays,axis=0,dtype=ld) if arrays else np.zeros(model.nc,ld)
        if not np.all(np.isfinite(result)):
            raise ValueError('finite independently accumulated particle path required')
        return result
    endpoint={s:V*(getattr(final.thermal,f)-getattr(initial.thermal,f))
              for s,f in zip(labels,('n_m3','p_m3'))}
    injected=total(generated)
    telescoping={s:total(v[s] for v in increments)-endpoint[s] for s in labels}
    rows={s:endpoint[s]+total(v[s] for v in transport)-injected for s in labels}
    summed={s:np.sum(v,dtype=ld) for s,v in rows.items()}
    terms=[*endpoint.values(),*telescoping.values(),*rows.values(),injected,*summed.values()]
    finite=all(np.all(np.isfinite(v)) for v in terms)
    worst=max([*(np.max(abs(v),initial=ld(0)) for v in (*rows.values(),*telescoping.values())),
               *(abs(v) for v in summed.values())])
    vectors=lambda m:{s:list(map(float,v)) for s,v in m.items()}
    return dict(particle_path_valid=bool(finite and worst<=budget),
        independently_reintegrated_particle_ports=True,
        cell_endpoint_particle_increments=vectors(endpoint),
        cell_particle_telescoping_errors=vectors(telescoping),
        cell_particle_balance_residuals=vectors(rows),
        particle_balance_residuals={s:float(v) for s,v in summed.items()},
        cell_generated_pairs=list(map(float,injected)),
        maximum_cumulative_particle_error=float(worst),cumulative_particle_atol=budget)


def audit_energy_coordinate_trajectory(model,initial_state,interval_reports,*,final_state,
        charge_atol_C,particle_atol,energy_atol_J,cumulative_energy_atol_J=None,
        cumulative_particle_atol=None):
    """Reaudit both accepted halves, endpoint storage and integrated ports.

    Cached audits, error summaries and rejected/coarse trial states supply no
    conservation evidence. This proves the modeled fixed-band path only.
    Temporal error estimates are not independently certified by this audit.
    """
    from tcad.solver.energy_coordinate_transport import _pack,EnergyCoordinateState
    from tcad.solver.adaptive_energy_coordinate import SCOPE
    charge=_scalar(charge_atol_C,'charge budget');particle=_scalar(particle_atol,'particle budget')
    energy=_scalar(energy_atol_J,'energy budget')
    explicit=None if cumulative_energy_atol_J is None else _scalar(cumulative_energy_atol_J,'cumulative energy budget')
    explicit_particle=None if cumulative_particle_atol is None else _scalar(cumulative_particle_atol,'cumulative particle budget')
    for state in (initial_state,final_state):
        if type(state) is not EnergyCoordinateState:raise ValueError('energy-coordinate endpoints required')
        _,fingerprint=_pack(model,state.thermal,1.,charge,particle,energy)
        if fingerprint!=state.configuration_sha256:raise ValueError('trajectory endpoint configuration mismatch')
    intervals=tuple(interval_reports);previous=initial_state;audits=[];ports=[];generated=[];absorbed=[]
    coupled=bool(np.any(model.intercarrier_conductance_W_m3_K!=0))
    transfers=[];rounding=[];injected=[[],[]];cell_ports=[];cell_work=[]
    radiative=model.radiative_law is not None
    photon_ports=[];radiative_pairs=[];radiative_sources=[[],[]];radiative_entropy=[];created_pairs=[]
    particle_increments=[];particle_ports=[];particle_generation=[]
    for interval in intervals:
        if (interval.get('valid') is not True or interval.get('scope')!=SCOPE or not _same(previous,interval['initial_state'])
            or interval.get('accepted_native_substeps')!=2):raise ValueError('accepted interval coverage or continuity mismatch')
        states=tuple(interval['substep_states']);reports=tuple(interval['substep_reports'])
        if len(states)!=2 or len(reports)!=2:raise ValueError('two accepted half steps required')
        start=previous.thermal.time_s
        for state,report in zip(states,reports):
            checked=audit_device_energy_coordinate_step(model,previous,state,report,
                charge_atol_C=charge,particle_atol=particle,energy_atol_J=energy)
            if not checked['valid']:raise ValueError('independent accepted energy substep audit failed')
            audits.append(checked)
            boundary,transport,work=_ports(model,previous,state,charge)
            ports.append(boundary);cell_ports.append(transport);cell_work.append(work)
            particle_increments.append({s:model.vol.astype(np.longdouble)*
                (getattr(state.thermal,f)-getattr(previous.thermal,f))
                for s,f in (('electrons','n_m3'),('holes','p_m3'))})
            particle_ports.append({s:transport['particle_'+s] for s in ('electrons','holes')})
            count,deposited=generation_increments(model,state.thermal.time_s-previous.thermal.time_s)
            rcount,renergy,rphotons,rentropy=radiative_increments(model,state.thermal,
                state.thermal.time_s-previous.thermal.time_s)
            particle_generation.append(count-rcount)
            created_pairs.append(count)
            photon_ports.append(rphotons);radiative_pairs.append(rcount);radiative_entropy.append(rentropy)
            for s in (0,1):radiative_sources[s].append(renergy[s])
            generated.append(float(np.sum(count,dtype=np.longdouble)))
            absorbed.append(float(sum(np.sum(v,dtype=np.longdouble) for v in deposited)))
            exchange,bound=exchange_increments(model,state.thermal,state.thermal.time_s-previous.thermal.time_s)
            transfers.append(exchange);rounding.append(bound)
            for s in (0,1):injected[s].append(deposited[s])
            previous=state
        if previous.thermal.time_s-start!=interval['accepted_interval_s']:raise ValueError('accepted interval duration mismatch')
    if not _same(previous,final_state):raise ValueError('trajectory final energy state does not match accepted path')
    n=len(audits);budget=explicit if explicit is not None else max(1,n)*energy
    if not np.isfinite(budget):raise ValueError('cumulative energy budget out of range')
    particle_budget=explicit_particle if explicit_particle is not None else max(1,n)*particle
    if not np.isfinite(particle_budget):raise ValueError('cumulative particle budget out of range')
    particles=_particle_path(model,initial_state,final_state,particle_increments,particle_ports,
        particle_generation,particle_budget)
    increments={label:fsum(fsum(a['reconstructed_carrier_storage_J'][s]) for a in audits)
        for s,label in enumerate(('electrons','holes'))}
    increments['lattice']=fsum(fsum(a['reconstructed_lattice_storage_J']) for a in audits)
    increments['electrostatic']=fsum(a['electrostatic_increment_J'] for a in audits)
    endpoint,endpoint_cells=_storage(model,initial_state,final_state,charge)
    telescoping={key:fsum((increments[key],-endpoint[key])) for key in endpoint}
    outward={key:fsum(p[key] for p in ports) for key in ('electrons','holes','lattice')}
    if radiative:outward['photons']=fsum(float(np.sum(v,dtype=np.longdouble)) for v in photon_ports)
    source=fsum(a['source_work_J'] for a in audits)
    generation=fsum(absorbed)
    residual=fsum([source,generation,*(-v for v in increments.values()),*(-v for v in outward.values())])
    endpoint_residual=fsum([source,generation,*(-v for v in endpoint.values()),*(-v for v in outward.values())])
    summed=fsum(a['energy_residual_J'] for a in audits)
    values=[*increments.values(),*endpoint.values(),*telescoping.values(),*outward.values(),source,residual,endpoint_residual,summed]
    worst=max(map(abs,[residual,endpoint_residual,residual-summed,*telescoping.values()]))
    # Sum each cell over the accepted physical path before summing cells or
    # reservoirs. A cancelling total is insufficient evidence of closure.
    ld=np.longdouble
    def total(rows):
        return np.sum(np.asarray(rows,ld),axis=0,dtype=ld) if rows else np.zeros(model.nc,ld)
    exchange_cells=total(transfers);bound_cells=total(rounding)
    relaxation=[total([a['reconstructed_exchange_J'][s] for a in audits]) for s in (0,1)]
    electrical=[total([w[s] for w in cell_work]) for s in (0,1)]
    transport={label:total([p[label] for p in cell_ports]) for label in endpoint_cells}
    reservoirs_cells={label:endpoint_cells[label]+transport[label]+relaxation[s]-electrical[s]
                       +(1 if s==0 else -1)*exchange_cells-total(injected[s])-total(radiative_sources[s])
                       for s,label in enumerate(('electrons','holes'))}
    reservoirs_cells['lattice']=endpoint_cells['lattice']+transport['lattice']-relaxation[0]-relaxation[1]
    reservoirs={label:float(np.sum(v,dtype=ld)) for label,v in reservoirs_cells.items()}
    exchange=float(np.sum(exchange_cells,dtype=ld));allowance=float(np.sum(bound_cells,dtype=ld))
    cell_worst=max(float(np.max(abs(v)+bound_cells,initial=0)) for v in reservoirs_cells.values())
    values.extend([exchange,allowance,*bound_cells,*reservoirs.values(),
                   *(v for row in reservoirs_cells.values() for v in row)])
    worst=max(worst,cell_worst,max(map(abs,reservoirs.values()))+allowance)
    valid=all(np.isfinite(v) for v in values) and worst<=budget and particles['particle_path_valid']
    checked=dict(valid=bool(valid),scope='independent_accepted_path_fixed_band_energy_coordinate_ledger',
        initial_time_s=initial_state.thermal.time_s,final_time_s=final_state.thermal.time_s,
        accepted_intervals=len(intervals),accepted_native_substeps=n,independently_reaudited_substeps=n,
        discarded_trials_included=False,temperature_view_used_as_energy=False,
        energy_increments_J=increments,endpoint_energy_increments_J=endpoint,storage_telescoping_error_J=telescoping,
        outward_energy_J=outward,source_work_J=source,energy_residual_J=residual,endpoint_energy_residual_J=endpoint_residual,
        summed_substep_energy_residual_J=summed,maximum_balance_error_J=worst,
        per_substep_energy_atol_J=energy,cumulative_energy_atol_J=budget,
        cumulative_budget_policy='explicit' if explicit is not None else 'sum_of_per_substep_budgets',
        reservoir_energy_residuals_J=reservoirs,
        cell_reservoir_energy_residuals_J={label:list(map(float,v)) for label,v in reservoirs_cells.items()},
        cell_intercarrier_temperature_rounding_bound_J=list(map(float,bound_cells)),
        independently_reintegrated_all_face_ports=True,
        modeled_fixed_band_energy_closed=bool(valid),complete_device_energy=False,physical_validated=False,
        experimental_validated=False,global_temporal_error_bound=False)
    checked.update(particles)
    checked.update(per_substep_particle_atol=particle,
        cumulative_particle_budget_policy='explicit' if explicit_particle is not None else 'sum_of_per_substep_budgets')
    if np.any(model.pair_generation_rate_m3_s!=0):
        checked.update(generation_law='prescribed_pair_rate_and_injected_material_energy',
            generated_pairs=fsum(generated),absorbed_generation_energy_J=generation)
    if coupled:
        checked.update(intercarrier_exchange_law='linear_temperature_conductance_with_rounding_budget',
            intercarrier_exchange_electron_to_hole_J=exchange,
            intercarrier_temperature_rounding_bound_J=allowance,
            reservoir_energy_residuals_J=reservoirs)
    if radiative:
        checked['cell_net_pair_source']=checked['cell_generated_pairs']
        checked['cell_generated_pairs']=list(map(float,total(created_pairs)))
        checked.update(radiative_law=model.radiative_law,
            radiative_recombined_pairs=float(np.sum(total(radiative_pairs),dtype=ld)),
            cell_radiative_recombined_pairs=list(map(float,total(radiative_pairs))),
            cell_radiative_carrier_source_J=[list(map(float,total(v))) for v in radiative_sources],
            radiative_photon_energy_J=outward['photons'],
            cell_radiative_photon_energy_J=list(map(float,total(photon_ports))),
            radiative_entropy_production_J_K=float(np.sum(total(radiative_entropy),dtype=ld)),
            photon_bath_law='maintained_Planck_zero_chemical_potential',radiative_material_calibrated=False)
    return checked
