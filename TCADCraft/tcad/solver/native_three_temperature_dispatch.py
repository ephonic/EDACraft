"""Pack one native three-temperature call and decode its accepted output."""
import numpy as np
from tcad.physics.native_fermi_local import _decimal
from .native_fd_dispatch import pack_native_fd_inputs, _poisson_output
from .cut_cell_transport import Q


def pack_three_temperature_inputs(model, old, dt, charge_atol_C, particle_atol, energy_atol_J):
    from .three_temperature_contacts import normalize_contact_temperatures, carrier_contact_temperature
    contact_temperatures = normalize_contact_temperatures(model.contacts, model.contact_carrier_temperature_K)
    from .reconstruction_configuration import validate_reconstruction
    validate_reconstruction(model)
    shared, faces, vn, vp, parameters = pack_native_fd_inputs(
        model, old, dt, charge_atol_C, particle_atol, energy_atol_J)
    if model.bulk_potential_path not in ('endpoint_barrier','linear_series'):
        raise ValueError('invalid bulk_potential_path')
    if model.bulk_potential_path=='linear_series':
        for f in range(len(model.mesh.faces)):
            if f not in model.thermionic_faces:faces[22*f+19]=_decimal(2)
    cells = []
    for i in range(model.nc):
        cells.extend(shared[17*i:17*(i+1)])
        cells.extend(_decimal(v) for v in (old.electron_temperature_K[i], old.hole_temperature_K[i],
                                         model.tau_n[i], model.tau_p[i]))
    coupled = np.any(model.intercarrier_conductance_W_m3_K != 0)
    generated = np.any(model.pair_generation_rate_m3_s != 0)
    trapped=model.trap_capture_law is not None
    radiative=model.radiative_law is not None
    auger=model.auger_events is not None
    if coupled or generated or trapped or radiative or auger or any(law is not None for law in model.relaxation_laws):
        parameters.extend(model.relaxation_parameters())
    if auger:
        parameters.append(-6.-int(trapped)-2*int(radiative))
        for i,events in enumerate(model.auger_parameters()):
            parameters.extend(a[i] for a in (model.intercarrier_conductance_W_m3_K,
                model.pair_generation_rate_m3_s,model.pair_generation_kinetic_n_J,model.pair_generation_kinetic_p_J))
            parameters.extend((model.Et[i],model.cn[i],model.cp[i]) if trapped else (0.,0.,0.))
            parameters.extend((model.photon_bath_temperature_K[i],model.radiative_transition_rate_s[i]) if radiative else (0.,0.))
            parameters.extend((len(events)//11,*events))
    elif radiative:
        parameters.append(-5. if trapped else -4.)
        for i in range(model.nc):
            parameters.extend(a[i] for a in (model.intercarrier_conductance_W_m3_K,
                model.pair_generation_rate_m3_s,model.pair_generation_kinetic_n_J,model.pair_generation_kinetic_p_J))
            if trapped:parameters.extend(a[i] for a in (model.Et,model.cn,model.cp))
            parameters.extend((model.photon_bath_temperature_K[i],model.radiative_transition_rate_s[i]))
    elif trapped:
        parameters.append(-3.)
        parameters.extend(v for row in zip(model.intercarrier_conductance_W_m3_K,
            model.pair_generation_rate_m3_s,model.pair_generation_kinetic_n_J,
            model.pair_generation_kinetic_p_J,model.Et,model.cn,model.cp) for v in row)
    elif generated:
        parameters.append(-2.)
        parameters.extend(v for row in zip(model.intercarrier_conductance_W_m3_K,
            model.pair_generation_rate_m3_s,model.pair_generation_kinetic_n_J,
            model.pair_generation_kinetic_p_J) for v in row)
    elif coupled:
        parameters.extend([-1., *model.intercarrier_conductance_W_m3_K])
    if model.temperature_dependent_bands:
        # Preserve the first seven runtime parameters (owned-device updates dt
        # and budgets in place). Negative sentinel cannot be a legacy Tref.
        arrays=model.band_temperature_slopes
        if model.nonlinear_temperature_bands:arrays=arrays+model.band_varshni_alpha+model.band_varshni_beta
        parameters=parameters[:7]+[-11. if model.nonlinear_temperature_bands else -10.,len(parameters)-7]+parameters[7:]+[model.T]+[
            float(v) for a in arrays for v in a]
    if model.transport_reconstruction!='cell_mean':
        parameters=parameters[:7]+[-12.,len(parameters)-7]+parameters[7:]
    if contact_temperatures:
        temperatures = [carrier_contact_temperature(model,f,s) if f in model.contacts else 0.
                        for f in range(len(model.mesh.faces)) for s in ('electrons','holes')]
        parameters = parameters[:7]+[-13.,len(parameters)-7]+parameters[7:]+temperatures
    return cells, faces, vn, vp, parameters


def native_three_temperature_step(model, old, dt, charge_atol_C, particle_atol, energy_atol_J, max_nfev):
    from tcad.core._bindings import native_three_temperature_dispatch_raw
    if (model.spectral_backend, model.local_backend, model.poisson_backend, model.nonlinear_backend,
            model.residual_backend) != ('native',)*5:
        raise ValueError('native three-temperature dispatch requires all native backends')
    raw = native_three_temperature_dispatch_raw(*pack_three_temperature_inputs(
        model, old, dt, charge_atol_C, particle_atol, energy_atol_J), max_nfev)
    return decode_three_temperature_output(model, old, raw, charge_atol_C, particle_atol, energy_atol_J, dt_s=dt)


def decode_three_temperature_output(model, old, raw, charge_atol_C, particle_atol, energy_atol_J, *, dt_s):
    if raw['density_mantissa_bits'] != np.finfo(np.longdouble).nmant+1:
        raise ValueError('native and NumPy density precision mismatch')
    n = np.asarray(raw['n'], np.longdouble); p = np.asarray(raw['p'], np.longdouble)
    trapped=model.trap_capture_law is not None
    fraction=np.asarray(raw['trap_fraction'],float) if trapped else old.trap_fraction
    if fraction.shape!=(model.nc,) or np.any(~np.isfinite(fraction)) or np.any(fraction<=0) or np.any(fraction>=1):
        raise ValueError('native trap occupancy coverage or bounds invalid')
    a = _poisson_output(model, raw['old_poisson'], old.n_m3, old.p_m3, old.trap_fraction, charge_atol_C)
    b = _poisson_output(model, raw['new_poisson'], n, p, fraction, charge_atol_C)
    if not a['valid'] or not b['valid']:
        raise ValueError('native three-temperature exported Poisson budget failed')
    nc = model.nc; nf = len(model.mesh.faces); local = np.asarray(raw['local'], float)
    radiative=model.radiative_law is not None
    auger=model.auger_events is not None
    generated = np.any(model.pair_generation_rate_m3_s != 0) or trapped or radiative or auger
    coupled = np.any(model.intercarrier_conductance_W_m3_K != 0) or generated
    offset=12*nc+nf
    banded=model.temperature_dependent_bands
    if local.shape != (offset+(nc if coupled else 0)+(3*nc if generated else 0)+(8*nc if trapped else 0)+(5*nc if radiative else 0)+(4*nc if auger else 0)+(2*nc if banded else 0),):
        raise ValueError('native three-temperature local output coverage mismatch')
    blocks = [local[k*nc:(k+1)*nc] for k in range(12)]
    records = {}
    for k, label in enumerate(('electrons', 'holes')):
        rows = {}
        for f, moments in enumerate(raw['moments'][k*nf:(k+1)*nf]):
            if not moments:
                continue
            width=6+2*len(model.valleys[label])
            if len(moments)!=(width if model.transport_reconstruction=='cell_mean' else 3*width+2):
                raise ValueError('native face moment coverage mismatch')
            rows[f] = dict(particle_flux_s=moments[0], total_energy_flux_W=moments[1],
                material_energy_flux_W=moments[2], entropy_production_W_K=moments[3],
                trace_occupation_min=moments[4], trace_occupation_max=moments[5],
                valley_moments=[dict(name=v.name, particle_flux_s=moments[6+2*j],
                    total_energy_flux_W=moments[7+2*j]) for j,v in enumerate(model.valleys[label])],
                trace_closure='energy_resolved_nonthermal_occupations', statistics='fermi_dirac', execution_backend='native')
        if model.transport_reconstruction!='cell_mean':
            width=6+2*len(model.valleys[label])
            for f,row in rows.items():
                packet=raw['moments'][k*nf+f]
                if len(packet)!=3*width+2:raise ValueError('native reconstruction branch coverage mismatch')
                def branch(v):
                    return dict(particle_flux_s=v[0],total_energy_flux_W=v[1],material_energy_flux_W=v[2],
                        entropy_production_W_K=v[3],trace_occupation_min=v[4],trace_occupation_max=v[5],
                        valley_moments=[dict(name=a.name,particle_flux_s=v[6+2*j],total_energy_flux_W=v[7+2*j]) for j,a in enumerate(model.valleys[label])],
                        trace_closure='energy_resolved_nonthermal_occupations',statistics='fermi_dirac',execution_backend='native')
                row.update(low_order_face=branch(packet[width:2*width]),reconstructed_face=branch(packet[2*width:3*width]),
                    high_order_fraction=packet[-2],entropy_pairing_potential='midpoint_work',single_spectral_reservoir_pair=False,
                    trace_closure='convex_mixture_of_two_spectral_faces')
        records[label] = rows
    pair = lambda i: dict(electrons=blocks[i], holes=blocks[i+1])
    rows = np.r_[blocks[9], blocks[10], blocks[11]]
    trap_offset=offset+4*nc
    trap_row=local[trap_offset:trap_offset+nc] if trapped else np.zeros(nc)
    merit = max(float(np.max(abs(blocks[0])))/particle_atol, float(np.max(abs(blocks[1])))/particle_atol,
                float(np.max(abs(trap_row)))/particle_atol,
                float(np.max(abs(rows)))/energy_atol_J,
                abs(float(Q*np.sum(blocks[1].astype(np.longdouble)-blocks[0]-trap_row, dtype=np.longdouble)))/charge_atol_C)
    cache = dict(n=n, p=p, Tn=np.asarray(raw['temperature_n']), Tp=np.asarray(raw['temperature_p']),
        tau=dict(electrons=np.asarray(raw['tau_n']),holes=np.asarray(raw['tau_p'])),
        Tl=np.asarray(raw['temperature_l']), poisson=b, du=pair(2), dl=blocks[4], exchange=pair(5), work=pair(7),
        rn=blocks[0], rp=blocks[1], rows=rows, heat=local[12*nc:12*nc+nf], records=records, merit=merit,
        intercarrier_exchange_J=(local[offset:offset+nc] if coupled else np.zeros(nc)),
        generated_pairs=(local[offset+nc:offset+2*nc] if generated else np.zeros(nc)),
        generation_energy_J=dict(electrons=(local[offset+2*nc:offset+3*nc] if generated else np.zeros(nc)),
                                 holes=(local[offset+3*nc:offset+4*nc] if generated else np.zeros(nc))),
        rates=dict(electrons=np.asarray(raw['fn']), holes=np.asarray(raw['fp'])),
        energies=dict(electrons=np.asarray(raw['energy_n']), holes=np.asarray(raw['energy_p'])))
    if trapped:
        from tcad.physics.spectral_trap_capture import FIELDS
        moments=np.asarray(raw['trap_moments'],float)
        if moments.shape!=(nc,len(FIELDS)) or np.any(~np.isfinite(moments)):
            raise ValueError('native trap moment coverage invalid')
        tail=[local[trap_offset+k*nc:trap_offset+(k+1)*nc] for k in range(8)]
        cache.update(trap_fraction=fraction,trap_moments=[dict(zip(FIELDS,row)) for row in moments],
            trap_particle_residuals=tail[0],trap_energy_increment_J=tail[1],
            trap_capture_counts=dict(electrons=tail[2],holes=tail[3]),
            trap_carrier_energy_removed_J=dict(electrons=tail[4],holes=tail[5]),
            trap_lattice_heat_J=tail[6],trap_entropy_J_K=tail[7])
    if radiative:
        from tcad.physics.spectral_radiative import FIELDS
        moments=np.asarray(raw.get('radiative_moments'),float)
        if moments.shape!=(nc,len(FIELDS)) or np.any(~np.isfinite(moments)):
            raise ValueError('native radiative moment coverage invalid')
        start=trap_offset+(8*nc if trapped else 0)
        tail=[local[start+k*nc:start+(k+1)*nc] for k in range(5)]
        cache.update(radiative_moments=[dict(zip(FIELDS,row)) for row in moments],radiative_pairs=tail[0],
            radiative_carrier_energy_removed_J=dict(electrons=tail[1],holes=tail[2]),
            radiative_photon_energy_J=tail[3],radiative_entropy_J_K=tail[4])
    if auger:
        from tcad.physics.spectral_auger import FIELDS,EVENT_FIELDS
        moments=raw.get('auger_moments')
        if not isinstance(moments,(list,tuple)) or len(moments)!=nc:
            raise ValueError('native Auger cell moment coverage invalid')
        reports=[]
        for events,rows in zip(model.auger_events,moments):
            if (not isinstance(rows,(list,tuple)) or len(rows)!=len(events)+1 or len(rows[0])!=len(FIELDS) or
                any(len(row)!=len(EVENT_FIELDS) for row in rows[1:]) or any(not np.all(np.isfinite(row)) for row in rows)):
                raise ValueError('native Auger event moment coverage invalid')
            reports.append(dict(zip(FIELDS,rows[0]),event_moments=[dict(zip(EVENT_FIELDS,row)) for row in rows[1:]]))
        start=trap_offset+(8*nc if trapped else 0)+(5*nc if radiative else 0)
        tail=[local[start+k*nc:start+(k+1)*nc] for k in range(4)]
        cache.update(auger_moments=reports,auger_pairs=tail[0],
            auger_carrier_energy_added_J=dict(electrons=tail[1],holes=tail[2]),auger_entropy_J_K=tail[3])
    elif raw.get('auger_moments'):
        raise ValueError('unconfigured native Auger moments')
    if banded:
        cache['band_work_J']=dict(electrons=local[-2*nc:-nc],holes=local[-nc:])
    from .three_temperature_merit import global_conservation_merit
    cache['merit'] = max(cache['merit'], global_conservation_merit(
        model, old, cache, a, dt_s, charge_atol_C, energy_atol_J))
    _, statistics, history = raw['newton']
    return cache, a, statistics, history
