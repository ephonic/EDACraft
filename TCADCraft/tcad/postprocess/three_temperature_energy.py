"""Independent adaptive DOS/spectral integration and five-equation energy audit."""
import numpy as np

from tcad.solver.cut_cell_transport import Q, _array
from .fermi_spectral_energy import reference_reservoir, reference_face


def _reference_relaxation_times(tau, density, carrier_temperature, lattice_temperature, law):
    """Independent powers, with Decimal reconstruction of overflowing factors.

    A finite product must not be rejected because individual powers exceed the
    extended-precision range. Preserve the established direct path otherwise.
    Neither the native law nor the Python production evaluator is called.
    """
    ld = np.longdouble
    tau, density, carrier_temperature, lattice_temperature = np.broadcast_arrays(
        *[np.asarray(x, ld) for x in (tau, density, carrier_temperature, lattice_temperature)])
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        result = tau*(lattice_temperature/ld(law.reference_temperature_K))**law.lattice_temperature_exponent
        result = result*(carrier_temperature/ld(law.reference_temperature_K))**law.carrier_temperature_exponent
        result = result*(density/ld(law.reference_density_m3))**law.density_exponent
    bad = ~np.isfinite(result) | (result <= 0)
    if np.any(bad):
        from decimal import Decimal, DecimalException, localcontext
        # Decimal arithmetic is independent of native real_t and NumPy power.
        # Enough digits to retain all supported longdouble input significands.
        d = lambda x: Decimal(np.format_float_scientific(ld(x), precision=36, unique=False))
        result = result.copy()
        with localcontext() as context:
            context.prec = 80
            for index in zip(*np.nonzero(bad)) if bad.ndim else [()]:
                try:
                    correction = sum((d(exponent)*(d(value[index])/d(reference)).ln()
                        for value, reference, exponent in (
                            (lattice_temperature, law.reference_temperature_K, law.lattice_temperature_exponent),
                            (carrier_temperature, law.reference_temperature_K, law.carrier_temperature_exponent),
                            (density, law.reference_density_m3, law.density_exponent))), Decimal(0))
                    logtau = d(tau[index]).ln() + correction
                    # Avoid exp on an unbounded exponent; this is rejection,
                    # never clipping to an admissible relaxation time.
                    if not Decimal(-750) < logtau < Decimal(711):
                        raise ValueError('independent effective relaxation time out of range')
                    result[index] = ld(str(logtau.exp()))
                except DecimalException as error:
                    raise ValueError('independent effective relaxation time out of range') from error
    return result


def reference_band_edges(model,lattice_temperature_K):
    """Audit-side reconstruction, independent of the solver band evaluator."""
    ld=np.longdouble
    t=np.asarray(lattice_temperature_K,ld);r=ld(model.T)
    # Expanded divided difference in extended precision, evaluated separately
    # from the production evaluator's normalized ratio factorization.
    return tuple(np.asarray(np.asarray(edge,ld)+(t-r)*(np.asarray(slope,ld)-
        np.asarray(alpha,ld)*(t*r+np.asarray(beta,ld)*(t+r))/
        ((t+np.asarray(beta,ld))*(r+np.asarray(beta,ld)))),float)
        for edge,slope,alpha,beta in zip((model.Ec,model.Eh),model.band_temperature_slopes,
            model.band_varshni_alpha,model.band_varshni_beta))


def audit_three_temperature_energy(model, old, new, report, *, charge_atol_C, particle_atol,
                                  energy_atol_J, particle_flux_atol_s=1e4,
                                  energy_flux_atol_W=1e-17, entropy_atol_W_K=1e-19, relaxation_rtol=1e-12):
    """Reconstruct every carrier/lattice row and terminal balance independently.

    Uses adaptive DOS/face integration and Python HMM Poisson, never the native
    production thermodynamics, spectral, Poisson, residual or energies methods.
    Checks relaxation to a same-density FD state at Tl, and its entropy sign.
    """
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
    if not isinstance(model, ThreeTemperatureElectrothermal):
        raise ValueError('three-temperature model required')
    for value in (charge_atol_C, particle_atol, energy_atol_J, particle_flux_atol_s,
                  energy_flux_atol_W, entropy_atol_W_K, relaxation_rtol):
        _array(value, 1, 'independent audit budget', positive=True)
    model._validate_state(old); model._validate_state(new)
    if report.get('bulk_potential_path','endpoint_barrier')!=model.bulk_potential_path:
        raise ValueError('spectral bulk potential path descriptor mismatch')
    dt = new.time_s-old.time_s
    if not np.isfinite(dt) or dt <= 0 or report['dt_s'] != dt:
        raise ValueError('matching increasing physical interval required')
    trapped=model.trap_capture_law is not None
    radiative=model.radiative_law is not None
    auger=model.auger_events is not None
    # Every physical channel in a report must belong to the configured ledger.
    # Otherwise an extra reservoir can be silently omitted from reconstruction
    # while the report still claims that all modeled energy has been checked.
    carriers={'electrons','holes'}
    reservoirs=carriers|{'lattice','electrostatic'}|({'traps'} if trapped else set())
    ports=carriers|{'lattice'}|({'photons'} if radiative else set())
    channel_maps={
        'energy_increments_J':reservoirs, 'outward_energy_J':ports,
        'integrated_particle_flux_s':carriers, 'integrated_carrier_energy_flux_W':carriers,
        'face_moments':carriers, 'cell_exchange_J':carriers, 'cell_electrical_work_J':carriers,
    }
    if 'cell_pair_generation_energy_J' in report:
        channel_maps['cell_pair_generation_energy_J']=carriers
    if model.temperature_dependent_bands:
        channel_maps['cell_band_work_from_lattice_J']=carriers
    trap_keys=('trap_capture_law','cell_trap_moments','cell_trap_particle_residuals',
        'cell_trap_capture_counts','cell_trap_carrier_energy_removed_J',
        'cell_trap_energy_increment_J','cell_trap_lattice_heat_J',
        'cell_trap_entropy_production_J_K','dynamic_trap_device_coupled')
    if trapped:
        channel_maps.update(cell_trap_capture_counts=carriers,cell_trap_carrier_energy_removed_J=carriers)
    elif any(key in report for key in trap_keys):
        raise ValueError('unconfigured trap report')
    if radiative:
        channel_maps['cell_radiative_carrier_energy_removed_J']=carriers
    if auger:
        channel_maps['cell_auger_carrier_energy_added_J']=carriers
    for name,expected in channel_maps.items():
        given=report.get(name)
        if not isinstance(given,dict) or set(given)!=expected:
            raise ValueError(name+' channel coverage mismatch')
    if not trapped and not np.array_equal(old.trap_fraction, new.trap_fraction):
        raise ValueError('unmodeled trap change')
    if trapped and np.any((model.Nt==0)&(old.trap_fraction!=new.trap_fraction)):
        raise ValueError('unoccupied zero-density trap field must remain fixed')
    nc = model.nc; nf = len(model.mesh.faces); ld = np.longdouble; V = model.vol.astype(ld)
    def electrostatic(s):
        return solve_cut_cell_poisson(model.mesh, model.eps,
            model.rhofix.astype(ld)+Q*(s.p_m3-s.n_m3-model.Nt.astype(ld)*s.trap_fraction),
            dirichlet_V=model.bc, charge_atol_C=charge_atol_C)
    a, b = electrostatic(old), electrostatic(new)
    states, u = [], []
    band_history=[reference_band_edges(model,state.temperature_K) for state in (old,new)]
    for state in (old, new):
        bands=band_history[0 if state is old else 1]
        r = {label: [reference_reservoir(density[c], T[c], band[c], model.valleys[label]) for c in range(nc)]
             for label, density, T, band in (
                 ('electrons', state.n_m3, state.electron_temperature_K, bands[0]),
                 ('holes', state.p_m3, state.hole_temperature_K, bands[1]))}
        states.append(r)
        u.append({s: np.array([v['energy_density_J_m3'] for v in rows], dtype=ld) for s, rows in r.items()})
    reconstructed=model.transport_reconstruction!='cell_mean'
    if reconstructed:
        from .three_temperature_reconstruction_audit import (reconstruct_reference_centers,
            reference_reconstructed_face,check_reconstructed_face_report)
        from tcad.solver.reconstruction_configuration import validate_reconstruction
        validate_reconstruction(model)
        if (report.get('transport_reconstruction')!=model.transport_reconstruction or
            report.get('reconstruction_storage')!='unchanged_cell_mean_FD' or
            report.get('fully_discrete_entropy_closed') is not False):
            raise ValueError('reconstruction report descriptor mismatch')
        center_states,center_lattice=reconstruct_reference_centers(model,new,states[1])
    elif any(k in report for k in ('transport_reconstruction','reconstruction_storage','fully_discrete_entropy_closed')):
        raise ValueError('unconfigured reconstruction report')
    fluxes, energies, du, exchange, work, local = {}, {}, {}, {}, {}, {}
    errors, flux_errors, energy_errors, entropy_errors = [], [], [], []
    entropy = []; coverage = True; occupation_valid = True
    tau_errors=[]
    reported_tau=report.get('cell_relaxation_time_s')
    if reported_tau is None and any(law is not None for law in model.relaxation_laws):
        raise ValueError('effective relaxation times required for configured laws')
    if reported_tau is not None and set(reported_tau)!= {'electrons','holes'}:
        raise ValueError('effective relaxation time coverage mismatch')
    midphi = (a['cell_potential_V']+b['cell_potential_V'])/2
    midface = (a['face_potential_V']+b['face_potential_V'])/2
    wanted = set(map(int, model.internal)) | set(map(int, model.contact_faces))
    for s, density, T, band, base, exponent, z, tau in (
            ('electrons', new.n_m3, new.electron_temperature_K, band_history[1][0], model.mn, model.mn_exponent, -1, model.tau_n),
            ('holes', new.p_m3, new.hole_temperature_K, band_history[1][1], model.mp, model.mp_exponent, 1, model.tau_p)):
        law=model.relaxation_laws[0 if s=='electrons' else 1]
        tau=np.asarray(tau,ld)
        if law is not None:
            tau=_reference_relaxation_times(tau,density,T,new.temperature_K,law)
        if np.any(~np.isfinite(tau)) or np.any(tau<=0) or np.any(~np.isfinite(tau.astype(float))) or np.any(tau.astype(float)<=0):
            raise ValueError('independent effective relaxation time out of range')
        if reported_tau is not None:
            given_tau=_array(reported_tau[s],nc,'reported effective relaxation time',positive=True)
            # A positive float64 subnormal can have a large relative rounding
            # error. Compare its export against the correctly rounded reference,
            # while retaining unrounded tau below for the physical exchange.
            comparison_tau=tau
            subnormal=tau.astype(float)<np.finfo(float).tiny
            if np.any(subnormal):
                comparison_tau=tau.copy()
                comparison_tau[subnormal]=tau.astype(float)[subnormal]
            tau_errors.extend(given_tau.astype(ld)/comparison_tau-1)
        flux = np.zeros(nf); energy = np.zeros(nf)
        rows = report['face_moments'][s]; coverage &= set(rows) == wanted
        for f in wanted:
            face = model.mesh.faces[f]; i, j = face.owner, face.neighbor
            area = np.linalg.norm(face.area_vector_m2); normal = face.area_vector_m2/area
            do = (face.centroid_m-model.mesh.centroids_m[i])@normal
            if j >= 0:
                two = states[1][s][j]; potential = b['cell_potential_V'][j]
                mu = base[j]*(model.T/new.temperature_K[j])**exponent
                dn = (model.mesh.centroids_m[j]-face.centroid_m)@normal
            else:
                contact = model.contacts[f]; d = contact.n_m3 if s == 'electrons' else contact.p_m3
                contact_band=reference_band_edges(model,np.full(nc,contact.temperature_K))[0 if s=='electrons' else 1][i]
                from tcad.solver.three_temperature_contacts import carrier_contact_temperature
                two = reference_reservoir(d, carrier_contact_temperature(model,f,s), contact_band, model.valleys[s])
                potential = model.bc[f]; dn = 0.; mu = base[i]*(model.T/contact.temperature_K)**exponent
            target = reference_face(states[1][s][i], two, model.valleys[s],
                phi_o=b['cell_potential_V'][i], phi_n=potential, phi_f=b['face_potential_V'][f], z=z,
                mu_o=base[i]*(model.T/new.temperature_K[i])**exponent, mu_n=mu,
                area=area, do=do, dn=dn, A=model.emission[s].get(f),bulk_potential_path=model.bulk_potential_path)
            if reconstructed:
                target=reference_reconstructed_face(model,s,f,target,states[1][s][i],two,
                    center_states[s][i],center_states[s][j] if j>=0 else two,new,a,b,center_lattice,base,exponent,z)
                check_reconstructed_face_report(rows[f],target,particle_flux_atol_s,energy_flux_atol_W,entropy_atol_W_K)
            elif any(key in rows[f] for key in ('low_order_face','reconstructed_face','high_order_fraction')):
                raise ValueError('unconfigured spectral mixture report')
            flux[f] = target['particle_flux_s']; energy[f] = target['material_energy_flux_W']
            row = rows[f]
            flux_errors.append(float(row['particle_flux_s'])-flux[f])
            for key in ('material_energy_flux_W', 'total_energy_flux_W'):
                energy_errors.append(float(row[key])-target[key])
            entropy_errors.append(float(row['entropy_production_W_K'])-target['entropy_production_W_K'])
            entropy.append(target['entropy_production_W_K'])
            occupation_valid &= 0 <= float(row['trace_occupation_min']) <= float(row['trace_occupation_max']) <= 1
            if len(row['valley_moments']) != len(target['valley_moments']):
                raise ValueError('valley moment coverage mismatch')
            for given, expected in zip(row['valley_moments'], target['valley_moments']):
                coverage &= given['name'] == expected['name']
                flux_errors.append(float(given['particle_flux_s'])-expected['particle_flux_s'])
                energy_errors.append(float(given['total_energy_flux_W'])-expected['total_energy_flux_W'])
        given_flux = _array(report['integrated_particle_flux_s'][s], nf, 'reported particle flux')
        given_energy = _array(report['integrated_carrier_energy_flux_W'][s], nf, 'reported carrier energy flux')
        flux_errors.extend(given_flux-flux); energy_errors.extend(given_energy-energy)
        fluxes[s], energies[s] = flux, energy
        du[s] = V*(u[1][s]-u[0][s])
        equilibrium = np.array([reference_reservoir(density[c], new.temperature_K[c], band[c],
                                 model.valleys[s])['energy_density_J_m3'] for c in range(nc)], dtype=ld)
        exchange[s] = dt*V*(u[1][s]-equilibrium)/tau
        errors.extend(_array(report['cell_exchange_J'][s], nc, 'reported relaxation')-exchange[s])
        entropy.extend(exchange[s]/dt*(1/new.temperature_K-1/T))
        current = z*Q*flux
        work[s] = dt*(midphi*model.mesh.divergence_integrals(current)-
                       model.mesh.divergence_integrals(midface*current))
        errors.extend(_array(report['cell_electrical_work_J'][s], nc, 'reported work')-work[s])
        local[s] = du[s]+dt*model.mesh.divergence_integrals(energy)-work[s]+exchange[s]
    # Reconstruct the new-state local channel without production assembly.
    conductance = _array(model.intercarrier_conductance_W_m3_K,nc,
                         'intercarrier conductance',nonnegative=True).astype(ld)
    intercarrier = ld(dt)*V*conductance*(new.electron_temperature_K.astype(ld)-new.hole_temperature_K)
    coupled = np.any(conductance != 0)
    given_exchange = report.get('cell_intercarrier_exchange_J')
    if coupled and given_exchange is None:
        raise ValueError('configured intercarrier exchange report required')
    if given_exchange is not None:
        errors.extend(_array(given_exchange,nc,'reported intercarrier exchange')-intercarrier)
    if coupled and report.get('intercarrier_exchange_law') != 'linear_temperature_conductance':
        raise ValueError('intercarrier exchange law mismatch')
    local['electrons'] += intercarrier
    local['holes'] -= intercarrier
    entropy.extend(intercarrier/ld(dt)*(1/new.hole_temperature_K.astype(ld)-1/new.electron_temperature_K))
    # Reconstruct the external pair and absorbed energy source from configuration,
    # never from a reported deposit or the production parameter helper.
    rate=_array(model.pair_generation_rate_m3_s,nc,'pair generation rate',nonnegative=True).astype(ld)
    generated=bool(np.any(rate != 0));pairs=ld(dt)*V*rate
    injection={}
    for s,band,kinetic in (('electrons',band_history[1][0],model.pair_generation_kinetic_n_J),
                            ('holes',band_history[1][1],model.pair_generation_kinetic_p_J)):
        edge=min(v.band_offset_owner_J for v in model.valleys[s])
        injection[s]=pairs*(band.astype(ld)+ld(edge)+np.asarray(kinetic,ld))
        local[s]-=injection[s]
    absorbed=sum(np.sum(v,dtype=ld) for v in injection.values())
    pair_errors=[]
    if generated or any(k in report for k in ('cell_generated_pairs','cell_pair_generation_energy_J',
                                               'absorbed_pair_energy_J','pair_generation_law')):
        if report.get('pair_generation_law')!='prescribed_constant_pair_rate_and_mean_injection_energy':
            raise ValueError('prescribed pair generation law mismatch')
        given=report.get('cell_pair_generation_energy_J')
        if not isinstance(given,dict) or set(given)!=set(injection):
            raise ValueError('pair generation energy channel coverage mismatch')
        pair_errors.extend(_array(report['cell_generated_pairs'],nc,'reported generated pairs')-pairs)
        for s in injection:
            errors.extend(_array(given[s],nc,'reported pair generation energy')-injection[s])
        errors.append(float(report['absorbed_pair_energy_J'])-absorbed)
    # Independently reconstruct lattice Fourier flux from face geometry.
    heat = np.zeros(nf)
    for f, face in enumerate(model.mesh.faces):
        i, j = face.owner, face.neighbor; area = np.linalg.norm(face.area_vector_m2)
        normal = face.area_vector_m2/area
        do = (face.centroid_m-model.mesh.centroids_m[i])@normal
        if j >= 0:
            dn = (model.mesh.centroids_m[j]-face.centroid_m)@normal
            heat[f] = area/(do/model.conductivity[i]+dn/model.conductivity[j])*(new.temperature_K[i]-new.temperature_K[j])
        elif f in model.bath:
            heat[f] = model.conductivity[i]*area/do*(new.temperature_K[i]-model.bath[f])
    energy_errors.extend(_array(report['integrated_heat_flux_W'], nf, 'reported lattice heat')-heat)
    dl = V*model.capacity*(new.temperature_K.astype(ld)-old.temperature_K)
    local['lattice'] = dl+dt*model.mesh.divergence_integrals(heat)-exchange['electrons']-exchange['holes']
    band_work={}
    band_keys=('band_temperature_law','band_work_law','cell_band_work_from_lattice_J',
               'temperature_dependent_band_energy_coupled','temperature_dependent_band_entropy_closed')
    if model.temperature_dependent_bands:
        wanted_law=('affine_plus_Varshni_lattice_temperature' if any(np.any(a!=0) for a in model.band_varshni_alpha)
                    else 'affine_lattice_temperature')
        if (report.get('band_temperature_law')!=wanted_law or
                report.get('band_work_law')!='symmetric_density_times_band_increment' or
                report.get('temperature_dependent_band_energy_coupled') is not True or
                report.get('temperature_dependent_band_entropy_closed') is not False):
            raise ValueError('configured temperature-dependent band work report required')
        given=report.get('cell_band_work_from_lattice_J')
        if not isinstance(given,dict) or set(given)!={'electrons','holes'}:
            raise ValueError('band work carrier coverage mismatch')
        for index,(s,before,after) in enumerate((('electrons',old.n_m3,new.n_m3),('holes',old.p_m3,new.p_m3))):
            t=new.temperature_K.astype(ld);r=old.temperature_K.astype(ld)
            alpha=np.asarray(model.band_varshni_alpha[index],ld);beta=np.asarray(model.band_varshni_beta[index],ld)
            # Divided difference avoids subtracting almost identical band edges.
            delta=(t-r)*(np.asarray(model.band_temperature_slopes[index],ld)-
                alpha*(t*r+beta*(t+r))/((t+beta)*(r+beta)))
            band_work[s]=V*(before.astype(ld)+after)/2*delta
            local[s]-=band_work[s];local['lattice']+=band_work[s]
            errors.extend(_array(given[s],nc,'reported band work')-band_work[s])
    elif any(k in report for k in band_keys):raise ValueError('unconfigured band work report')
    trap_counts={s:np.zeros(nc,ld) for s in ('electrons','holes')}
    trap_removed={s:np.zeros(nc,ld) for s in trap_counts}
    trap_heat=np.zeros(nc,ld);trap_du=np.zeros(nc,ld);trap_row=np.zeros(nc,ld)
    trap_entropy=np.zeros(nc,ld);trap_moment_error=0.
    if trapped:
        from tcad.physics.spectral_trap_capture import SpectralTrapState,FIELDS
        from .spectral_trap_capture import audit_spectral_trap_capture
        given=report.get('cell_trap_moments')
        if (report.get('trap_capture_law')!=model.trap_capture_law or
                report.get('dynamic_trap_device_coupled') is not True or
                not isinstance(given,(list,tuple)) or len(given)!=nc):
            raise ValueError('configured dynamic trap report required')
        for i,row in enumerate(given):
            if not isinstance(row,dict) or set(row)!=set(FIELDS):
                raise ValueError('trap source moment coverage mismatch')
            s=SpectralTrapState(new.electron_temperature_K[i],new.hole_temperature_K[i],new.temperature_K[i],
                states[1]['electrons'][i]['chemical_potential_J'],states[1]['holes'][i]['chemical_potential_J'],
                band_history[1][0][i],band_history[1][1][i],model.Nt[i],model.Et[i],model.cn[i],model.cp[i],new.trap_fraction[i])
            # Reuse only the independent source-moment audit, describing that
            # sub-operator as standalone; device coupling is checked here.
            audit=audit_spectral_trap_capture(s,model.valleys['electrons'],model.valleys['holes'],dict(row,
                law='constant_capture_coefficient_FD_DOS_local_detailed_balance_v1',
                device_coupled=False,material_calibrated=False))
            if not audit['valid']:raise ValueError('independent trap source audit failed: '+str(audit['failures']))
            trap_moment_error=max(trap_moment_error,audit['maximum_moment_scaled_error'])
            ref=audit['reference'];factor=ld(dt)*V[i]
            for label,c in (('electrons','n'),('holes','p')):
                trap_counts[label][i]=factor*ld(ref['net_capture_'+c+'_m3_s'])
                trap_removed[label][i]=-factor*ld(ref['electron_energy_source_W_m3' if c=='n' else 'hole_energy_source_W_m3'])
            trap_heat[i]=factor*ld(ref['lattice_heat_W_m3'])
            trap_entropy[i]=factor*ld(ref['entropy_production_W_m3_K'])
        occupied=V*model.Nt.astype(ld)*(new.trap_fraction.astype(ld)-old.trap_fraction)
        trap_du=occupied*model.Et.astype(ld)
        trap_row=occupied-trap_counts['electrons']+trap_counts['holes']
        for label in trap_counts:
            local[label]+=trap_removed[label]
            errors.extend(_array(report['cell_trap_carrier_energy_removed_J'][label],nc,'trap removed energy')-trap_removed[label])
            pair_errors.extend(_array(report['cell_trap_capture_counts'][label],nc,'trap capture counts')-trap_counts[label])
        local['lattice']-=trap_heat
        errors.extend(_array(report['cell_trap_energy_increment_J'],nc,'trap storage increment')-trap_du)
        errors.extend(_array(report['cell_trap_lattice_heat_J'],nc,'trap lattice heat')-trap_heat)
        # Entropy is checked as W/K independently from the energy error array.
        entropy_errors.extend((_array(report['cell_trap_entropy_production_J_K'],nc,'trap entropy')-trap_entropy)/dt)
        entropy.extend(trap_entropy/dt)
        pair_errors.extend(_array(report['cell_trap_particle_residuals'],nc,'trap particle residual')-trap_row)
    elif any(k in report for k in ('trap_capture_law','cell_trap_moments','dynamic_trap_device_coupled')):
        raise ValueError('unconfigured trap report')
    radiative_pairs=np.zeros(nc,ld);radiative_photons=np.zeros(nc,ld)
    radiative_removed={s:np.zeros(nc,ld) for s in ('electrons','holes')}
    radiative_entropy=np.zeros(nc,ld);radiative_moment_error=0.
    if radiative:
        from tcad.physics.spectral_radiative import SpectralRadiativeState,FIELDS
        from .spectral_radiative import audit_radiative_source
        given=report.get('cell_radiative_moments')
        if (report.get('radiative_law')!=model.radiative_law or report.get('radiative_device_coupled') is not True or
            report.get('photon_bath_law')!='maintained_Planck_zero_chemical_potential' or
            not isinstance(given,(list,tuple)) or len(given)!=nc):
            raise ValueError('configured radiative device report required')
        vn=model.valleys['electrons'][0];vp=model.valleys['holes'][0]
        for i,row in enumerate(given):
            if not isinstance(row,dict) or set(row)!=set(FIELDS):raise ValueError('radiative source moment coverage mismatch')
            state=SpectralRadiativeState(new.electron_temperature_K[i],new.hole_temperature_K[i],
                model.photon_bath_temperature_K[i],states[1]['electrons'][i]['chemical_potential_J'],
                states[1]['holes'][i]['chemical_potential_J'],band_history[1][0][i],band_history[1][1][i],
                vn.mass_normal,vp.mass_normal,vn.degeneracy,model.radiative_transition_rate_s[i])
            audit=audit_radiative_source(state,dict(row,law='matched_direct_gap_constant_state_rate_FD_Planck_v1',
                device_coupled=False,material_calibrated=False))
            if not audit['valid']:raise ValueError('independent radiative source audit failed: '+str(audit['failures']))
            radiative_moment_error=max(radiative_moment_error,audit['maximum_moment_scaled_error'])
            ref=audit['reference'];factor=ld(dt)*V[i]
            radiative_pairs[i]=factor*ld(ref['net_recombination_rate_m3_s'])
            radiative_photons[i]=factor*ld(ref['photon_power_W_m3'])
            radiative_entropy[i]=factor*ld(ref['entropy_production_W_m3_K'])
            for label,key in (('electrons','electron_energy_source_W_m3'),('holes','hole_energy_source_W_m3')):
                radiative_removed[label][i]=-factor*ld(ref[key])
        for label in radiative_removed:
            local[label]+=radiative_removed[label]
            errors.extend(_array(report['cell_radiative_carrier_energy_removed_J'][label],nc,'radiative removed energy')-radiative_removed[label])
        pair_errors.extend(_array(report['cell_radiative_recombined_pairs'],nc,'radiative pairs')-radiative_pairs)
        errors.extend(_array(report['cell_radiative_photon_energy_J'],nc,'radiative photon energy')-radiative_photons)
        entropy_errors.extend((_array(report['cell_radiative_entropy_production_J_K'],nc,'radiative entropy')-radiative_entropy)/dt)
        entropy.extend(radiative_entropy/dt)
    elif any(k in report for k in ('radiative_law','radiative_device_coupled','cell_radiative_moments','photon_bath_law',
            'cell_radiative_recombined_pairs','cell_radiative_carrier_energy_removed_J','cell_radiative_photon_energy_J',
            'cell_radiative_entropy_production_J_K')):
        raise ValueError('unconfigured radiative report')
    auger_pairs=np.zeros(nc,ld);auger_entropy=np.zeros(nc,ld);auger_moment_error=0.
    auger_added={s:np.zeros(nc,ld) for s in ('electrons','holes')}
    auger_keys=('auger_law','auger_device_coupled','auger_material_calibrated','auger_continuum_kernel_integrated',
        'cell_auger_moments','cell_auger_recombined_pairs','cell_auger_carrier_energy_added_J','cell_auger_entropy_production_J_K')
    if auger:
        from tcad.physics.spectral_auger import SpectralAugerState
        from .spectral_auger import audit_auger_source
        given=report.get('cell_auger_moments')
        law='on_shell_parabolic_Auger_impact_event_table_v1'
        if (report.get('auger_law')!=law or report.get('auger_device_coupled') is not True or
            report.get('auger_material_calibrated') is not False or report.get('auger_continuum_kernel_integrated') is not False or
            not isinstance(given,(list,tuple)) or len(given)!=nc):
            raise ValueError('configured Auger device report required')
        vn=model.valleys['electrons'][0];vp=model.valleys['holes'][0]
        for i,row in enumerate(given):
            if not isinstance(row,dict):raise ValueError('Auger moment mapping required')
            state=SpectralAugerState(new.electron_temperature_K[i],new.hole_temperature_K[i],
                states[1]['electrons'][i]['chemical_potential_J'],states[1]['holes'][i]['chemical_potential_J'],
                band_history[1][0][i],band_history[1][1][i],vn.mass_normal,vp.mass_normal)
            audit=audit_auger_source(state,model.auger_events[i],dict(row,law=law,execution_backend='native',
                device_coupled=False,material_calibrated=False,continuum_kernel_integrated=False),rtol=3e-10)
            if not audit['valid']:raise ValueError('independent Auger source audit failed: '+str(audit['failures']))
            ref=audit['reference']
            if set(row)!=set(ref):raise ValueError('Auger source moment coverage mismatch')
            auger_moment_error=max(auger_moment_error,audit['maximum_moment_scaled_error'])
            factor=ld(dt)*V[i];auger_pairs[i]=factor*ld(ref['net_recombination_rate_m3_s'])
            auger_entropy[i]=factor*ld(ref['entropy_production_W_m3_K'])
            for label,key in (('electrons','electron_energy_source_W_m3'),('holes','hole_energy_source_W_m3')):
                auger_added[label][i]=factor*ld(ref[key])
        if set(report['cell_auger_carrier_energy_added_J'])!=set(auger_added):
            raise ValueError('Auger energy channel coverage mismatch')
        for label in auger_added:
            local[label]-=auger_added[label]
            errors.extend(_array(report['cell_auger_carrier_energy_added_J'][label],nc,'Auger added energy')-auger_added[label])
        pair_errors.extend(_array(report['cell_auger_recombined_pairs'],nc,'Auger pairs')-auger_pairs)
        entropy_errors.extend((_array(report['cell_auger_entropy_production_J_K'],nc,'Auger entropy')-auger_entropy)/dt)
        entropy.extend(auger_entropy/dt)
    elif any(k in report for k in auger_keys):raise ValueError('unconfigured Auger report')
    rows = np.r_[local['electrons'], local['holes'], local['lattice']]
    errors.extend(_array(report['cell_energy_residuals_J'], 3*nc, 'reported local energy')-rows)
    particles = np.r_[V*(new.n_m3-old.n_m3)+dt*model.mesh.divergence_integrals(fluxes['electrons'])-pairs+trap_counts['electrons']+radiative_pairs+auger_pairs,
                      V*(new.p_m3-old.p_m3)+dt*model.mesh.divergence_integrals(fluxes['holes'])-pairs+trap_counts['holes']+radiative_pairs+auger_pairs]
    if trapped:particles=np.r_[particles,trap_row]
    particle_reports = _array(report['particle_residuals'], (3 if trapped else 2)*nc, 'reported particle residuals')
    qflux = Q*(fluxes['holes']-fluxes['electrons'])
    boundary = np.array([f for f, face in enumerate(model.mesh.faces) if face.neighbor < 0], int)
    dq = b['integrated_D_flux_C']-a['integrated_D_flux_C']
    terminals = {f: float(-dq[f]/dt-qflux[f]) for f in model.bc}
    displacement = -sum(v*dq[f] for f, v in model.bc.items())
    conduction = -dt*sum(v*qflux[f] for f, v in model.bc.items())
    increments = {s: float(np.sum(du[s], dtype=ld)) for s in ('electrons', 'holes')}
    increments.update(lattice=float(np.sum(dl, dtype=ld)),
        electrostatic=float(ld(b['electrostatic_energy_J'])-ld(a['electrostatic_energy_J'])))
    if trapped:increments['traps']=float(np.sum(trap_du,dtype=ld))
    outward = {s: dt*float(np.sum(energies[s][boundary], dtype=ld)) for s in ('electrons', 'holes')}
    outward['lattice'] = dt*float(np.sum(heat[boundary], dtype=ld))
    if radiative:outward['photons']=float(np.sum(radiative_photons,dtype=ld))
    if set(report['outward_energy_J'])!=set(outward):raise ValueError('outward energy port coverage mismatch')
    residual = float(ld(displacement)+ld(conduction)+absorbed-sum(map(ld, increments.values()))-sum(map(ld, outward.values())))
    charge = float(Q*np.sum(V*(new.p_m3-old.p_m3-new.n_m3+old.n_m3-
                   model.Nt.astype(ld)*(new.trap_fraction.astype(ld)-old.trap_fraction)), dtype=ld)+dt*np.sum(qflux[boundary], dtype=ld))
    for key, value in increments.items():
        errors.append(float(report['energy_increments_J'][key])-value)
    for key, value in outward.items():
        errors.append(float(report['outward_energy_J'][key])-value)
    for key, value in dict(source_work_J=displacement+conduction, displacement_work_J=displacement,
                           conduction_work_J=conduction, energy_residual_J=residual).items():
        errors.append(float(report[key])-value)
    if set(report['terminal_currents_A']) != set(terminals):
        raise ValueError('terminal coverage mismatch')
    charge_errors = [float(report['charge_balance_residual_C'])-charge]
    charge_errors.extend(dt*(report['terminal_currents_A'][f]-value) for f, value in terminals.items())
    worst = lambda a: float(np.max(abs(np.asarray(a)), initial=0.))
    finite = all(np.all(np.isfinite(v)) for v in (rows, particles, errors, pair_errors, flux_errors, energy_errors, entropy, charge_errors))
    valid = bool(finite and a['valid'] and b['valid'] and coverage and occupation_valid and
        max(worst(rows), worst(errors), abs(residual)) <= energy_atol_J and
        max(worst(particles), worst(particle_reports-particles), worst(pair_errors), dt*worst(flux_errors)) <= particle_atol and
        worst(flux_errors) <= particle_flux_atol_s and worst(energy_errors) <= energy_flux_atol_W and
        worst(entropy_errors) <= entropy_atol_W_K and min(entropy, default=0.) >= -entropy_atol_W_K and
        max(abs(charge), abs(dt*sum(terminals.values())), worst(charge_errors)) <= charge_atol_C and
        report.get('scope') == 'FD_spectral_three_temperature_energy_transport' and
        report.get('mobility_temperature') == 'lattice' and
        worst(tau_errors)<=relaxation_rtol and
        report.get('relaxation_law') == model.relaxation_law_descriptor and
        report.get('residual_backend') == model.residual_backend and report.get('physics_backend') == 'native' and
        report.get('local_conservation_backend') == 'native' and
        report.get('residual_orchestration') == model.residual_orchestration and
        report.get('native_residual_dispatch') is (model.residual_orchestration == 'native') and
        report.get('valid') is True and report.get('state_advanced') is True and
        report.get('modeled_device_energy_closed') is True and
        report.get('complete_device_energy') is False and report.get('physical_validated') is False)
    # These values are reconstructed above, never copied from production or
    # from a previously attached audit. They also support accepted-path sums.
    ledger = dict(energy_increments_J=increments, outward_energy_J=outward,
        displacement_work_J=float(displacement), conduction_work_J=float(conduction),
        source_work_J=float(displacement+conduction), energy_residual_J=residual,
        carrier_exchange_to_lattice_J={s: float(np.sum(exchange[s], dtype=ld)) for s in exchange},
        carrier_electrical_work_J={s: float(np.sum(work[s], dtype=ld)) for s in work},
        terminal_charge_C={f: float(dt*v) for f, v in terminals.items()})
    if coupled:
        ledger['intercarrier_exchange_electron_to_hole_J'] = float(np.sum(intercarrier,dtype=ld))
    if band_work:
        ledger['band_work_from_lattice_J']={s:float(np.sum(v,dtype=ld)) for s,v in band_work.items()}
    if generated or trapped or radiative or auger:
        ledger.update(generated_pairs=float(np.sum(pairs,dtype=ld)),absorbed_pair_energy_J=float(absorbed),
            pair_generation_energy_J={s:float(np.sum(v,dtype=ld)) for s,v in injection.items()},
            particle_increments={s:float(np.sum(V*(after-before),dtype=ld)) for s,after,before in (
                ('electrons',new.n_m3,old.n_m3),('holes',new.p_m3,old.p_m3))},
            outward_particles={s:float(ld(dt)*np.sum(fluxes[s][boundary],dtype=ld)) for s in injection})
    if trapped:
        ledger.update(trap_capture_counts={s:float(np.sum(v,dtype=ld)) for s,v in trap_counts.items()},
            trap_carrier_energy_removed_J={s:float(np.sum(v,dtype=ld)) for s,v in trap_removed.items()},
            trap_lattice_heat_J=float(np.sum(trap_heat,dtype=ld)),
            occupied_trap_increment=float(np.sum(occupied,dtype=ld)),
            trap_entropy_production_J_K=float(np.sum(trap_entropy,dtype=ld)))
    if radiative:
        ledger.update(radiative_recombined_pairs=float(np.sum(radiative_pairs,dtype=ld)),
            radiative_carrier_energy_removed_J={s:float(np.sum(v,dtype=ld)) for s,v in radiative_removed.items()},
            radiative_photon_energy_J=float(np.sum(radiative_photons,dtype=ld)),
            radiative_entropy_production_J_K=float(np.sum(radiative_entropy,dtype=ld)))
    if auger:
        ledger.update(auger_recombined_pairs=float(np.sum(auger_pairs,dtype=ld)),
            auger_carrier_energy_added_J={s:float(np.sum(v,dtype=ld)) for s,v in auger_added.items()},
            auger_entropy_production_J_K=float(np.sum(auger_entropy,dtype=ld)))
    # Keep cell identity until whole-path endpoint balances have been tested.
    # All values below come from independent reconstruction above, never from
    # attached audit summaries or native source/flux ledgers.
    vector=lambda v:list(map(float,v))
    vectors=lambda values:{s:vector(v) for s,v in values.items()}
    cell_storage=dict(du,lattice=dl)
    if trapped:cell_storage['traps']=trap_du
    cell_ledger=dict(energy_increments_J=vectors(cell_storage),
        transport_energy_J=vectors(dict({s:dt*model.mesh.divergence_integrals(energies[s]) for s in du},
            lattice=dt*model.mesh.divergence_integrals(heat))),
        carrier_exchange_to_lattice_J=vectors(exchange),carrier_electrical_work_J=vectors(work),
        intercarrier_exchange_J=vector(intercarrier),pair_generation_energy_J=vectors(injection),
        band_work_from_lattice_J=vectors({s:band_work.get(s,np.zeros(nc,ld)) for s in du}),
        trap_carrier_energy_removed_J=vectors(trap_removed),trap_lattice_heat_J=vector(trap_heat),
        radiative_carrier_energy_removed_J=vectors(radiative_removed),
        radiative_photon_energy_J=vector(radiative_photons),
        auger_carrier_energy_added_J=vectors(auger_added),
        particle_increments=vectors({s:V*(after-before) for s,after,before in (
            ('electrons',new.n_m3,old.n_m3),('holes',new.p_m3,old.p_m3))}),
        particle_transport=vectors({s:dt*model.mesh.divergence_integrals(fluxes[s]) for s in du}),
        generated_pairs=vector(pairs),trap_capture_counts=vectors(trap_counts),
        radiative_recombined_pairs=vector(radiative_pairs),auger_recombined_pairs=vector(auger_pairs))
    if trapped:cell_ledger['occupied_trap_increment']=vector(occupied)
    return dict(valid=valid, modeled_device_energy_closed=valid, complete_device_energy=False, physical_validated=False,
        independently_reconstructed_ledger=ledger,
        independently_reconstructed_cell_ledger=cell_ledger,
        max_cell_energy_residual_J=worst(rows), max_report_energy_error_J=worst(errors),
        max_particle_residual=worst(particles), energy_residual_J=residual,
        max_relaxation_relative_error=worst(tau_errors),
        max_trap_moment_scaled_error=trap_moment_error,
        max_radiative_moment_scaled_error=radiative_moment_error,
        max_auger_moment_scaled_error=auger_moment_error,
        max_constitutive_particle_error_s=worst(flux_errors), max_constitutive_energy_error_W=worst(energy_errors),
        min_entropy_W_K=float(min(entropy, default=0.)), terminal_KCL_residual_C=float(dt*sum(terminals.values())),
        charge_balance_residual_C=charge, trace_occupation_bounds_valid=bool(occupation_valid))
