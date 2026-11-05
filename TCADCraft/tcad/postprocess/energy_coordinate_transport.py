"""Adaptive DOS/face and Python HMM replay of energy-coordinate FD steps.

The signed energy is authoritative; temperatures are rounded transport views.
No native EOS, law, spectral face, residual or solver is called here.
"""
from decimal import Decimal,localcontext
import numpy as np
from .fermi_spectral_energy import reference_reservoir,reference_face
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
from tcad.solver.cut_cell_transport import Q,_array
from .native_energy_identity import same_native_energy
from .energy_coordinate_generation import generation_increments
from .energy_coordinate_exchange import exchange_increments
from .energy_coordinate_radiative import radiative_increments


def _require_finite_native_record(value):
    """Validate decimal/native records without narrowing their stored values."""
    if isinstance(value,dict):
        for child in value.values():_require_finite_native_record(child)
    elif isinstance(value,(list,tuple)):
        for child in value:_require_finite_native_record(child)
    else:
        try:
            with np.errstate(over='ignore',invalid='ignore'):
                finite=np.all(np.isfinite(np.asarray(value,np.longdouble)))
        except (TypeError,ValueError,OverflowError) as error:
            raise ValueError('finite numeric native energy-coordinate record required') from error
        if not finite:raise ValueError('finite numeric native energy-coordinate record required')


def audit_energy_coordinate_step(model,old,new,report,*,charge_atol_C,particle_atol,energy_atol_J):
    from tcad.solver.energy_coordinate_transport import EnergyCoordinateState,SCOPE
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    if type(model) is not ThreeTemperatureElectrothermal or type(old) is not EnergyCoordinateState or type(new) is not EnergyCoordinateState:
        raise ValueError('explicit energy-coordinate model and states required')
    if model.contact_carrier_temperature_K:
        raise ValueError('independent carrier contact temperatures are not supported by energy-coordinate audit')
    for value in (charge_atol_C,particle_atol,energy_atol_J):_array(value,1,'audit budget',positive=True)
    if (model.temperature_dependent_bands or model.trap_capture_law is not None
        or model.auger_events is not None or np.any(model.Nt!=0)
        or model.kn!=0 or model.kp!=0):
        raise ValueError('unmodeled energy-coordinate source or band channel')
    if any(law is not None and law.carrier_temperature_exponent!=0 for law in model.relaxation_laws):
        raise ValueError('b_Tc=0 required')
    astate,bstate=old.thermal,new.thermal;nc=model.nc;nf=len(model.mesh.faces);ld=np.longdouble
    dt=bstate.time_s-astate.time_s
    if not np.isfinite(dt) or dt<=0 or report['dt_s']!=dt:raise ValueError('matching increasing physical time required')
    generating=bool(np.any(model.pair_generation_rate_m3_s!=0))
    counts,deposited=generation_increments(model,dt)
    coupled=bool(np.any(model.intercarrier_conductance_W_m3_K!=0))
    transfer,rounding=exchange_increments(model,bstate,dt)
    net=[deposited[0]-transfer,deposited[1]+transfer] if coupled else deposited
    if old.configuration_sha256!=new.configuration_sha256 or not np.array_equal(astate.trap_fraction,bstate.trap_fraction):
        raise ValueError('configuration or unmodeled trap change')
    allowed={'scope','dt_s','raw','shared_max_nfev','complete_device_energy','physical_validated','native_device_session_integrated'}
    if set(report)-{'independent_audit'}!=allowed:raise ValueError('exact energy-coordinate report coverage required')
    raw=report['raw'];t=raw['transport'];failures=[]
    radiative=model.radiative_law is not None
    recombined,rad_energy,photons,rad_entropy=radiative_increments(model,bstate,dt,t.get('radiative_moments'))
    if radiative:
        if 'radiative_moments' not in t:raise ValueError('configured radiative moments required')
        counts=counts-recombined
        net=[net[s]+rad_energy[s] for s in (0,1)]
    if set(raw)!={'transport','excess','ledger','local_cells','local_faces','temperature_cells','seed_evaluations'}:
        raise ValueError('exact raw energy-coordinate coverage required')
    if set(t)!=({'n','p','temperature_n','temperature_p','temperature_l','tau_n','tau_p','local','fn','fp',
                'energy_n','energy_p','old_poisson','new_poisson','moments','newton','density_mantissa_bits'}
                | ({'radiative_moments'} if radiative else set())):
        raise ValueError('unconfigured native transport channel')
    # NaN comparisons are false, and a later NaN in max(finite, NaN) can be
    # ignored. Require finite evidence before either operation can mask it.
    _require_finite_native_record(raw)
    if report['scope']!=SCOPE or any(report[k] is not False for k in ('complete_device_energy','physical_validated','native_device_session_integrated')):
        failures.append('scope')
    for key,field,dtype in (('n','n_m3',ld),('p','p_m3',ld),('temperature_n','electron_temperature_K',float),
                           ('temperature_p','hole_temperature_K',float),('temperature_l','temperature_K',float)):
        if not np.array_equal(np.asarray(t[key],dtype),getattr(bstate,field)):failures.append('state '+key)
    if tuple(raw['excess'])!=new.excess_J_m3:failures.append('excess state')
    if t['local']:failures.append('unconfigured float64 local operator')
    native_cells=np.asarray(raw['local_cells'],ld);native_faces=np.asarray(raw['local_faces'],ld)
    codec=np.asarray(raw['temperature_cells'],ld)
    if native_cells.shape!=(34*nc,) or native_faces.shape!=(13*nf,) or codec.shape!=(12*nc,):
        raise ValueError('exact native cell/face/temperature coverage required')
    native_cells=native_cells.reshape(nc,34);native_faces=native_faces.reshape(nf,13);codec=codec.reshape(nc,2,6)
    if np.any(native_cells[:,31:]!=0) or (not generating and not coupled and not radiative and np.any(native_cells[:,27:]!=0)):
        failures.append('unconfigured native source')
    for i in range(nc):
        for s in (0,1):
            values=codec[i,s]
            if (values[0]!=(bstate.electron_temperature_K if s==0 else bstate.hole_temperature_K)[i] or
                values[2]!=ld(new.excess_J_m3[2*i+s]) or not values[4]<=values[2]<=values[5]):failures.append('temperature codec')
    if t['density_mantissa_bits']!=np.finfo(ld).nmant+1:failures.append('density precision')
    stats=t['newton'][1];seed=raw['seed_evaluations']
    if len(stats)!=4 or not 0<seed+stats[0]<=report['shared_max_nfev'] or seed<nc:failures.append('evaluation budget')
    def poisson(state):
        return solve_cut_cell_poisson(model.mesh,model.eps,model.rhofix.astype(ld)+Q*(state.p_m3-state.n_m3),
            dirichlet_V=model.bc,charge_atol_C=charge_atol_C)
    a,b=poisson(astate),poisson(bstate)
    if not a['valid'] or not b['valid']:failures.append('Poisson')
    for ref,given in ((a,t['old_poisson']),(b,t['new_poisson'])):
        if (np.max(abs(np.asarray(given[0])-np.r_[ref['cell_potential_V'],ref['face_potential_V']]),initial=0)>1e-10 or
            np.max(abs(np.asarray(given[2])-ref['integrated_D_flux_C']),initial=0)>charge_atol_C):failures.append('native field')
    reservoirs=[];eq=[];view_error=[]
    for st,energy in ((astate,old.excess_J_m3),(bstate,new.excess_J_m3)):
        rs=[];es=[]
        for s,(density,T,band) in enumerate(((st.n_m3,st.electron_temperature_K,model.Ec),(st.p_m3,st.hole_temperature_K,model.Eh))):
            label=('electrons','holes')[s];valleys=model.valleys[label]
            rs.append([reference_reservoir(density[i],T[i],band[i],valleys) for i in range(nc)])
            es.append(np.array([reference_reservoir(density[i],st.temperature_K[i],band[i],valleys)['energy_density_J_m3'] for i in range(nc)],ld))
            for i in range(nc):view_error.append(model.vol[i]*(ld(rs[s][i]['energy_density_J_m3'])-es[s][i]-ld(energy[2*i+s])))
        reservoirs.append(rs);eq.append(es)
    flux=np.zeros((2,nf));eflux=np.zeros((2,nf));heat=np.zeros(nf);entropy=[];particle_error=[];face_energy_error=[]
    wanted=set(map(int,model.internal))|set(map(int,model.contact_faces))
    for s,(base,exponent,z,band) in enumerate(((model.mn,model.mn_exponent,-1,model.Ec),(model.mp,model.mp_exponent,1,model.Eh))):
        label=('electrons','holes')[s]
        for f in range(nf):
            row=t['moments'][s*nf+f]
            if f not in wanted:
                if row:failures.append('unconfigured face moments')
                continue
            face=model.mesh.faces[f];i,j=face.owner,face.neighbor
            if j>=0:
                two=reservoirs[1][s][j];phi=b['cell_potential_V'][j];mu=base[j]*(model.T/bstate.temperature_K[j])**exponent
            else:
                contact=model.contacts[f];density=contact.n_m3 if s==0 else contact.p_m3
                two=reference_reservoir(density,contact.temperature_K,band[i],model.valleys[label]);phi=model.bc[f]
                mu=base[i]*(model.T/contact.temperature_K)**exponent
            target=reference_face(reservoirs[1][s][i],two,model.valleys[label],phi_o=b['cell_potential_V'][i],phi_n=phi,
                phi_f=b['face_potential_V'][f],z=z,mu_o=base[i]*(model.T/bstate.temperature_K[i])**exponent,mu_n=mu,
                area=model.area[f],do=model.do[f],dn=model.dn[f],A=model.emission[label].get(f),bulk_potential_path=model.bulk_potential_path)
            if len(row)!=6+2*len(model.valleys[label]):raise ValueError('complete spectral moment coverage required')
            flux[s,f]=target['particle_flux_s'];eflux[s,f]=target['material_energy_flux_W'];entropy.append(target['entropy_production_W_K'])
            particle_error.append(row[0]-flux[s,f]);face_energy_error.extend((row[1]-target['total_energy_flux_W'],row[2]-eflux[s,f]))
            if not 0<=row[4]<=row[5]<=1:failures.append('occupation bounds')
            if abs(row[3]-target['entropy_production_W_K'])>1e-19:failures.append('face entropy')
            for v,target_v in enumerate(target['valley_moments']):
                particle_error.append(row[6+2*v]-target_v['particle_flux_s']);face_energy_error.append(row[7+2*v]-target_v['total_energy_flux_W'])
        particle_error.extend(np.asarray(t['fn' if s==0 else 'fp'])-flux[s])
        face_energy_error.extend(np.asarray(t['energy_n' if s==0 else 'energy_p'])-eflux[s])
    for f,face in enumerate(model.mesh.faces):
        i,j=face.owner,face.neighbor
        if j>=0:heat[f]=model.area[f]/(model.do[f]/model.conductivity[i]+model.dn[f]/model.conductivity[j])*(bstate.temperature_K[i]-bstate.temperature_K[j])
        elif f in model.bath:heat[f]=model.area[f]*model.conductivity[i]/model.do[f]*(bstate.temperature_K[i]-model.bath[f])
    V=model.vol.astype(ld);du=[];ex=[];work=[];carrier_rows=[];particle_rows=[];tau=[]
    def decimal(value):return Decimal(np.format_float_scientific(ld(value),precision=35,unique=False))
    with localcontext() as ctx:
        ctx.prec=90
        for s,(before,after,z) in enumerate(((astate.n_m3,bstate.n_m3,-1),(astate.p_m3,bstate.p_m3,1))):
            eold=np.array(old.excess_J_m3[s::2],ld);enew=np.array(new.excess_J_m3[s::2],ld)
            du.append(V*((eq[1][s]-eq[0][s])+(enew-eold)));exchanged=[];ts=[]
            law=model.relaxation_laws[s]
            for i in range(nc):
                logtau=decimal((model.tau_n,model.tau_p)[s][i]).ln()
                if law is not None:
                    logtau+=decimal(law.lattice_temperature_exponent)*(decimal(bstate.temperature_K[i])/decimal(law.reference_temperature_K)).ln()
                    logtau+=decimal(law.density_exponent)*(decimal(after[i])/decimal(law.reference_density_m3)).ln()
                value=logtau.exp()
                if not 0<float(value)<float('inf'):raise ValueError('independent relaxation outside positive float64 range')
                ts.append(str(value));exchanged.append(ld(str(decimal(dt)*decimal(V[i])*Decimal(new.excess_J_m3[2*i+s])/value)))
                entropy.append(float(exchanged[-1]/dt*(1/bstate.temperature_K[i]-1/(bstate.electron_temperature_K if s==0 else bstate.hole_temperature_K)[i])))
            tau.append(ts);ex.append(np.array(exchanged,ld))
            midphi=(a['cell_potential_V']+b['cell_potential_V'])/2;midface=(a['face_potential_V']+b['face_potential_V'])/2
            current=z*Q*flux[s]
            work.append(dt*(midphi*model.mesh.divergence_integrals(current)-model.mesh.divergence_integrals(midface*current)))
            carrier_rows.append(du[s]+dt*model.mesh.divergence_integrals(eflux[s])-work[s]+ex[s]-net[s])
            particle_rows.append(V*(after-before)+dt*model.mesh.divergence_integrals(flux[s])-counts)
    dl=V*model.capacity*(bstate.temperature_K.astype(ld)-astate.temperature_K)
    lattice=dl+dt*model.mesh.divergence_integrals(heat)-ex[0]-ex[1]
    ledger=np.asarray(raw['ledger'],ld)
    if ledger.shape!=(20*nc+nf,):raise ValueError('native energy ledger coverage invalid')
    rows=ledger[:20*nc].reshape(nc,20);errors=[];perrors=[]
    for i in range(nc):
        if (np.max(abs(native_cells[i,14:16]-np.asarray((a['cell_potential_V'][i],b['cell_potential_V'][i]),ld)))>1e-10):
            failures.append('native local potential')
        expected=(astate.n_m3[i],astate.p_m3[i],astate.temperature_K[i],bstate.n_m3[i],bstate.p_m3[i],bstate.temperature_K[i])
        if not np.array_equal(native_cells[i,:6],np.asarray(expected,ld)):failures.append('native local state')
        if not np.array_equal(native_cells[i,12:14],np.asarray((model.vol[i],model.capacity[i]),ld)) or native_cells[i,16]!=ld(model.conductivity[i]):
            failures.append('native local material')
        for s in (0,1):
            perrors.append(rows[i,s]-particle_rows[s][i]);errors.extend((rows[i,4+s]-du[s][i],rows[i,7+s]-ex[s][i],rows[i,9+s]-work[s][i],rows[i,11+s]-carrier_rows[s][i]))
            if rows[i,2+s]!=ld(new.excess_J_m3[2*i+s]):failures.append('ledger excess')
            if abs(rows[i,14+s]/ld(tau[s][i])-1)>1e-12:failures.append('ledger tau')
            if not np.isfinite(t['tau_n' if s==0 else 'tau_p'][i]) or abs(ld(t['tau_n' if s==0 else 'tau_p'][i])/ld(tau[s][i])-1)>1e-12:
                failures.append('transport tau')
            expected_retained=ld(tau[s][i])/(ld(tau[s][i])+ld(dt))
            if abs(rows[i,16+s]/expected_retained-1)>1e-12:failures.append('ledger retained')
            drive=(eq[0][s][i]-eq[1][s][i])+ld(old.excess_J_m3[2*i+s])+(work[s][i]-dt*model.mesh.divergence_integrals(eflux[s])[i]+net[s][i])/V[i]
            errors.append(V[i]*(rows[i,18+s]-drive))
            errors.extend((V[i]*(native_cells[i,6+3*s]-eq[0][s][i]),V[i]*(native_cells[i,7+3*s]-eq[1][s][i]),
                           V[i]*(codec[i,s,1]-eq[1][s][i])))
            if not same_native_energy(raw['local_cells'][34*i+8+3*s],old.excess_J_m3[2*i+s]):failures.append('native old excess')
            # Also bind each decimal relaxation record to the snapshotted model.
            law=model.relaxation_laws[s]
            wanted=((model.tau_n,model.tau_p)[s][i],300 if law is None else law.reference_temperature_K,
                1e25 if law is None else law.reference_density_m3,0 if law is None else law.lattice_temperature_exponent,
                0 if law is None else law.density_exponent)
            if not np.array_equal(native_cells[i,17+5*s:22+5*s],np.asarray(wanted,ld)):failures.append('native local law')
        errors.extend((rows[i,6]-dl[i],rows[i,13]-lattice[i]))
        if generating or coupled or radiative:
            perrors.extend(native_cells[i,27:29]-counts[i])
            errors.extend(native_cells[i,29:31]-np.asarray((net[0][i],net[1][i]),ld))
    for f,face in enumerate(model.mesh.faces):
        if np.max(abs(native_faces[f,6:8]-np.asarray((a['face_potential_V'][f],b['face_potential_V'][f]),ld)))>1e-10:
            failures.append('native local face potential')
        expected=(face.owner,face.neighbor,t['fn'][f],t['fp'][f],t['energy_n'][f],t['energy_p'][f])
        if not np.array_equal(native_faces[f,:6],np.asarray(expected,ld)):failures.append('native local face')
        if not np.array_equal(native_faces[f,8:],np.asarray((model.area[f],model.do[f],model.dn[f],model.bath.get(f,0),int(f in model.bath)),ld)):
            failures.append('native local face material')
    face_energy_error.extend(ledger[20*nc:]-heat)
    boundary=[f for f,face in enumerate(model.mesh.faces) if face.neighbor<0]
    dq=b['integrated_D_flux_C']-a['integrated_D_flux_C'];qflux=Q*(flux[1]-flux[0])
    source=-sum(v*dq[f]+dt*v*qflux[f] for f,v in model.bc.items())
    field=ld(b['electrostatic_energy_J'])-ld(a['electrostatic_energy_J'])
    absorbed=sum(np.sum(v,dtype=ld) for v in deposited)
    residual=ld(source)+absorbed-np.sum(photons,dtype=ld)-sum(np.sum(v,dtype=ld) for v in (*du,dl))-field-ld(dt)*sum(np.sum(v[boundary],dtype=ld) for v in (*eflux,heat))
    charge=Q*np.sum(V*(bstate.p_m3-astate.p_m3-bstate.n_m3+astate.n_m3),dtype=ld)+dt*np.sum(qflux[boundary],dtype=ld)
    kcl=sum(-dq[f]-dt*qflux[f] for f in model.bc)
    reconstructed=(*carrier_rows,lattice,errors,view_error,*particle_rows,perrors,
        particle_error,face_energy_error,entropy,charge,kcl,residual,rounding)
    if not all(np.all(np.isfinite(np.asarray(v,ld))) for v in reconstructed):
        raise ValueError('nonfinite independently reconstructed energy-coordinate audit terms')
    worst=lambda v:float(np.max(abs(np.asarray(v,ld)),initial=0))
    energy_max=max(worst(carrier_rows),worst(lattice),worst(errors),worst(view_error),abs(float(residual)))
    if coupled:
        # Spend this allowance inside the existing budget, even if the rounded
        # temperatures coincide and the reported transfer is exactly zero.
        energy_max+=worst(rounding)
        entropy.extend(transfer/ld(dt)*(1/bstate.hole_temperature_K.astype(ld)-1/bstate.electron_temperature_K))
    if radiative:entropy.extend(rad_entropy/ld(dt))
    particle_max=max(worst(particle_rows),worst(perrors),dt*worst(particle_error))
    if energy_max>energy_atol_J:failures.append('energy')
    if particle_max>particle_atol:failures.append('particles')
    if max(abs(float(charge)),abs(float(kcl)))>charge_atol_C:failures.append('charge')
    if worst(particle_error)>1e4 or worst(face_energy_error)>1e-17:failures.append('face constitutive')
    if min(entropy,default=0)<-1e-19:failures.append('entropy')
    if not np.isfinite(energy_max+particle_max+worst(face_energy_error)+worst(particle_error)):failures.append('finite')
    checked=dict(valid=not failures,failures=failures,max_energy_error_J=energy_max,max_particle_error=particle_max,
        energy_residual_J=float(residual),charge_residual_C=float(charge),terminal_KCL_C=float(kcl),
        max_particle_flux_error_s=worst(particle_error),max_energy_flux_error_W=worst(face_energy_error),
        max_temperature_view_energy_error_J=worst(view_error),
        reconstructed_carrier_storage_J=[list(map(float,v)) for v in du],reconstructed_exchange_J=[list(map(str,v)) for v in ex],
        reconstructed_lattice_storage_J=list(map(float,dl)),source_work_J=float(source),electrostatic_increment_J=float(field),
        seed_evaluations=int(seed),newton_evaluations=int(stats[0]),total_evaluations=int(seed+stats[0]),
        modeled_fixed_band_energy_closed=not failures,complete_device_energy=False,physical_validated=False)
    if generating:
        checked.update(generation_law='prescribed_pair_rate_and_injected_material_energy',
            reconstructed_generated_pairs=list(map(float,counts+recombined)),
            reconstructed_generation_energy_J=[list(map(float,v)) for v in deposited],
            absorbed_generation_energy_J=float(absorbed))
    if coupled:
        checked.update(intercarrier_exchange_law='linear_temperature_conductance_with_rounding_budget',
            reconstructed_intercarrier_exchange_J=list(map(float,transfer)),
            intercarrier_temperature_rounding_bound_J=list(map(float,rounding)),
            reconstructed_electrical_work_J=[list(map(float,v)) for v in work])
    if radiative:
        checked.update(radiative_law=model.radiative_law,
            reconstructed_radiative_recombined_pairs=list(map(float,recombined)),
            reconstructed_radiative_carrier_source_J=[list(map(float,v)) for v in rad_energy],
            radiative_photon_energy_J=float(np.sum(photons,dtype=ld)),
            radiative_entropy_production_J_K=float(np.sum(rad_entropy,dtype=ld)),
            photon_bath_law='maintained_Planck_zero_chemical_potential',
            radiative_material_calibrated=False)
    return checked
