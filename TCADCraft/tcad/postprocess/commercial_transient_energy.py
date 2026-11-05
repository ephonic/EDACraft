"""Independent SI ledger for a narrowly specified planar Sentaurus HD transient.

The caller supplies all solved BE times, all electrical/thermal ports, and an
orthogonal uniform-extrusion profile. No recombination, optical, trap, quantum,
ferroelectric, or other source/storage is implicit. Carrier kinetic storage is
Maxwell-Boltzmann, as in W-2024.09 User Guide equations 98--100. This is not a
general-device or experimental acceptance certificate.
"""
from collections.abc import Mapping
import numpy as np

Q=1.602176634e-19
KB=1.380649e-23


def audit_sentaurus_planar_transient(samples, *, x_m, cross_section_m2,
        heat_capacity_J_m3_K, permittivity_F_m, energy_atol_J,
        energy_rtol, particle_atol, particle_rtol, current_atol_A,
        source_contract, time_discretization):
    """Reconstruct BE storage/port ledgers, retaining a band-work defect.

    Samples have SI arrays n_m3,p_m3,Tn_K,Tp_K,Tl_K,phi_V,Ec_eV,Ev_eV,
    electric_field_V_m, plus time_s, joule_power_W and collision_power_W
    (each an electrons/holes/lattice mapping; lattice Joule power is zero).
    ``ports`` maps every port to phi_V, electron_current_A, hole_current_A,
    displacement_current_A,total_current_A,Ec_eV,Ev_eV and inward_heat_W
    (the latter has electrons/holes/lattice keys). All currents are positive
    inward, heat powers are SI and have already been integrated over depth.

    Only fixed electrical/contact band boundary values are supported. A common
    energy reference is frozen at the first left conduction edge. Volume band
    storage uses Ec+phi and -Ev-phi in eV. Full incoming power includes contact
    band work and electrostatic displacement work. A nonzero n*dEc+p*dEh
    defect is reported separately and never subtracted to make acceptance pass.
    Spatial trapezoids and BE right-endpoint time quadrature are explicit;
    refinement must be demonstrated externally. No global error bound follows.
    Collision powers describe internal exchange in this source-free contract.
    Their sum must integrate to zero on each interval and cumulative prefix,
    using energy_atol_J alone, without relative scaling by gross exchange.
    """
    if source_contract!='source_free_MB_HD_constant_capacity_planar':
        raise ValueError('explicit source-free MB planar storage contract required')
    if time_discretization!='backward_euler_all_solved_times':
        raise ValueError('all solved backward-Euler times required')
    def scalar(value,name,positive=False,nonnegative=False):
        a=np.asarray(value)
        if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a):
            raise ValueError(name+' must be a finite real scalar')
        v=np.longdouble(a)
        if (positive and v<=0) or (nonnegative and v<0):raise ValueError(name+' outside range')
        return v
    def array(value,name,size=None,positive=False):
        a=np.asarray(value)
        if a.ndim!=1 or a.dtype.kind not in 'fiu' or (size is not None and a.size!=size):
            raise ValueError(name+' must be a real profile')
        a=a.astype(np.longdouble)
        if np.any(~np.isfinite(a)) or (positive and np.any(a<=0)):raise ValueError(name+' outside range')
        return a
    x=array(x_m,'x_m')
    if x.size<2 or np.any(np.diff(x)<=0):raise ValueError('strictly increasing spatial coordinates required')
    area=scalar(cross_section_m2,'cross_section_m2',positive=True)
    capacity=scalar(heat_capacity_J_m3_K,'heat_capacity_J_m3_K',positive=True)
    eps=scalar(permittivity_F_m,'permittivity_F_m',positive=True)
    ea=scalar(energy_atol_J,'energy_atol_J',nonnegative=True)
    er=scalar(energy_rtol,'energy_rtol',nonnegative=True)
    pa=scalar(particle_atol,'particle_atol',nonnegative=True)
    pr=scalar(particle_rtol,'particle_rtol',nonnegative=True)
    ca=scalar(current_atol_A,'current_atol_A',nonnegative=True)
    try: rows=tuple(samples)
    except TypeError as exc:raise ValueError('a sequence of samples required') from exc
    if len(rows)<2:raise ValueError('at least two samples required')
    species=('electrons','holes','lattice');fields=('n_m3','p_m3','Tn_K','Tp_K','Tl_K','phi_V','Ec_eV','Ev_eV','electric_field_V_m')
    states=[];reference=None;ports_first=None
    integrate=lambda v:np.sum((v[:-1]+v[1:])*np.diff(x)/2,dtype=np.longdouble)*area
    for row in rows:
        if not isinstance(row,Mapping):raise ValueError('sample mapping required')
        v={k:array(row[k],k,x.size,positive=k in fields[:5]) for k in fields}
        if np.any(v['Ec_eV']<v['Ev_eV']):raise ValueError('positive band gap required')
        ports=row['ports']
        if not isinstance(ports,Mapping) or not ports or any(not isinstance(p,str) or not p for p in ports):
            raise ValueError('all named ports required')
        pvalues={}
        for name,p in ports.items():
            keys=('phi_V','Ec_eV','Ev_eV','electron_current_A','hole_current_A','displacement_current_A','total_current_A')
            pv={k:scalar(p[k],name+' '+k) for k in keys}
            if pv['Ec_eV']<pv['Ev_eV']:raise ValueError('positive contact band gap required')
            h=p['inward_heat_W']
            if not isinstance(h,Mapping) or set(h)!=set(species):raise ValueError('all three heat channels required')
            pv['inward_heat_W']={s:scalar(h[s],name+' '+s+' heat') for s in species}
            pvalues[name]=pv
        if ports_first is None:
            ports_first=pvalues;reference=next(iter(pvalues.values()))['Ec_eV']
        if set(pvalues)!=set(ports_first):raise ValueError('port coverage must remain fixed')
        for name,p in pvalues.items():
            for k in ('phi_V','Ec_eV','Ev_eV'):
                if p[k]!=ports_first[name][k]:raise ValueError('fixed contact potential and band energies required')
        powers={}
        for key in ('joule_power_W','collision_power_W'):
            m=row[key]
            if not isinstance(m,Mapping) or set(m)!=set(species):raise ValueError('all three volume power channels required')
            powers[key]={s:scalar(m[s],key+' '+s) for s in species}
        if powers['joule_power_W']['lattice']!=0:raise ValueError('lattice Joule term excluded by HD contract')
        bn=v['Ec_eV']+v['phi_V']-reference;bp=-v['Ev_eV']-v['phi_V']+reference
        storage=dict(electrons=integrate(1.5*KB*v['n_m3']*v['Tn_K']),
            holes=integrate(1.5*KB*v['p_m3']*v['Tp_K']),lattice=integrate(capacity*v['Tl_K']),
            material_bands=integrate(Q*(v['n_m3']*bn+v['p_m3']*bp)),
            electrostatic=integrate(eps*v['electric_field_V_m']**2/2))
        heat={s:sum(p['inward_heat_W'][s] for p in pvalues.values()) for s in species}
        contact=sum(-(p['Ec_eV']-reference)*p['electron_current_A']-(p['Ev_eV']-reference)*p['hole_current_A']+
            p['phi_V']*p['displacement_current_A'] for p in pvalues.values())
        composition=max(abs(p['electron_current_A']+p['hole_current_A']+p['displacement_current_A']-p['total_current_A']) for p in pvalues.values())
        kcl=abs(sum(p['total_current_A'] for p in pvalues.values()))
        states.append(dict(time=scalar(row['time_s'],'time_s',nonnegative=True),v=v,bn=bn,bp=bp,storage=storage,
            particles=dict(electrons=integrate(v['n_m3']),holes=integrate(v['p_m3'])),heat=heat,powers=powers,
            contact=contact,ports=pvalues,composition=composition,kcl=kcl))
    times=np.array([r['time'] for r in states],np.longdouble)
    if np.any(np.diff(times)<=0):raise ValueError('strictly increasing solved clocks required')
    initial=states[0];cum_work=np.longdouble(0);cum_heat={s:np.longdouble(0) for s in species}
    cum_channel={s:np.longdouble(0) for s in species};cum_particles={s:np.longdouble(0) for s in ('electrons','holes')}
    band_work=np.longdouble(0);out=[];collision_exchange=np.longdouble(0)
    for old,new,dt in zip(states[:-1],states[1:],np.diff(times)):
        step_collision=dt*sum(new['powers']['collision_power_W'].values())
        collision_exchange+=step_collision
        collision_ok=bool(np.isfinite(step_collision) and np.isfinite(collision_exchange)
            and abs(step_collision)<=ea and abs(collision_exchange)<=ea)
        cum_work+=dt*new['contact']
        for s in species:
            cum_heat[s]+=dt*new['heat'][s]
            cum_channel[s]+=dt*(new['heat'][s]+new['powers']['joule_power_W'][s]+new['powers']['collision_power_W'][s])
        cum_particles['electrons']+=dt*sum(-p['electron_current_A']/Q for p in new['ports'].values())
        cum_particles['holes']+=dt*sum(p['hole_current_A']/Q for p in new['ports'].values())
        band_work+=integrate(Q*((old['v']['n_m3']+new['v']['n_m3'])/2*(new['bn']-old['bn'])+
            (old['v']['p_m3']+new['v']['p_m3'])/2*(new['bp']-old['bp'])))
        increments={s:new['storage'][s]-initial['storage'][s] for s in new['storage']}
        channel_residual={s:increments[s]-cum_channel[s] for s in species}
        kinetic_lattice=sum(increments[s] for s in species)
        kinetic_drive=sum(cum_channel.values())
        net_drive=cum_work+sum(cum_heat.values())
        full_storage=sum(increments.values());residual=full_storage-net_drive
        budget=ea+er*max(abs(full_storage),abs(net_drive))
        particles={s:new['particles'][s]-initial['particles'][s]-cum_particles[s] for s in cum_particles}
        particle_ok=all(abs(particles[s])<=pa+pr*max(abs(new['particles'][s]-initial['particles'][s]),abs(cum_particles[s])) for s in particles)
        channel_budgets={s:ea+er*max(abs(increments[s]),abs(cum_channel[s])) for s in species}
        out.append(dict(time_s=float(new['time']),energy_increments_J={s:float(v) for s,v in increments.items()},
            step_internal_collision_residual_J=float(step_collision),
            cumulative_internal_collision_residual_J=float(collision_exchange),
            internal_collision_budget_J=float(ea),internal_collision_balance_valid=collision_ok,
            cumulative_contact_work_J=float(cum_work),cumulative_inward_heat_J={s:float(v) for s,v in cum_heat.items()},
            reservoir_residuals_J={s:float(v) for s,v in channel_residual.items()},
            reservoir_budgets_J={s:float(v) for s,v in channel_budgets.items()},
            reservoir_balances_valid=bool(all(abs(channel_residual[s])<=channel_budgets[s] for s in species)),
            kinetic_lattice_residual_J=float(kinetic_lattice-kinetic_drive),
            full_storage_residual_J=float(residual),energy_budget_J=float(budget),
            full_storage_balance_valid=bool(abs(residual)<=budget),
            cumulative_prescribed_band_work_J=float(band_work),
            residual_minus_band_work_J=float(residual-band_work),
            particle_residuals={s:float(v) for s,v in particles.items()},particle_balance_valid=bool(particle_ok)))
    current_ok=all(r['composition']<=ca and r['kcl']<=ca for r in states)
    collision_ok=all(r['internal_collision_balance_valid'] for r in out)
    accepted=bool(current_ok and collision_ok and all(r['particle_balance_valid'] and r['full_storage_balance_valid'] and r['reservoir_balances_valid'] for r in out))
    return dict(accepted=accepted,scope='source_free_MB_HD_constant_capacity_planar_fixed_boundaries',
        time_discretization=time_discretization,spatial_quadrature='profile_trapezoid',samples=len(states),
        current_balance_valid=bool(current_ok),maximum_current_component_residual_A=float(max(r['composition'] for r in states)),
        maximum_total_current_balance_A=float(max(r['kcl'] for r in states)),
        full_storage_balance_valid=bool(all(r['full_storage_balance_valid'] for r in out)),
        reservoir_balances_valid=bool(all(r['reservoir_balances_valid'] for r in out)),
        particle_balance_valid=bool(all(r['particle_balance_valid'] for r in out)),
        internal_collision_balance_valid=bool(collision_ok),
        maximum_full_storage_residual_J=max(abs(r['full_storage_residual_J']) for r in out),
        reference_energy_eV=float(reference),checkpoints=out,
        complete_device_energy=False,physical_validated=False,experimental_validated=False,
        commercial_transient_band_storage_validated=False,global_temporal_error_bound=False)
