"""Independent BE ledgers from explicitly integrated commercial mesh quantities.

Only a source-free, fixed-material-band MB hydrodynamic control is covered.
The caller must establish units, quadrature and complete solved-time coverage.
No field energy, missing heat channel or source is inferred from other totals.
"""
from collections.abc import Mapping
import numpy as np

Q=1.602176634e-19
SPECIES=('electrons','holes','lattice')
STORAGE=SPECIES+('material_bands','electrostatic')


def audit_sentaurus_mesh_integrals(samples, *, reference_energy_eV,
        energy_atol_J, energy_rtol, particle_atol, particle_rtol,
        current_atol_A, source_contract, time_discretization, field_energy_contract):
    """Check SI mesh-integrated storage, particles, port work and all heat channels.

    Each sample supplies time_s, storage_J (all five STORAGE entries),
    particles (electrons/holes), joule_power_W, collision_power_W (all three
    SPECIES), and all ports. Port fields match the planar transient auditor:
    phi_V,Ec_eV,Ev_eV,electron_current_A,hole_current_A,
    displacement_current_A,total_current_A,inward_heat_W (three species).

    Material-band storage must use the supplied fixed energy reference:
    q*integral[n*(Ec+phi-ref)+p*(-Ev-phi+ref)]. Contact work uses that same
    reference. Allowed field energies are explicitly identified vertex-field
    quadrature or uniform-permittivity discrete box energy; neither is inferred.
    All energy gates use own storage/net drive, never gross channel turnover.
    Collision powers are internal exchange in this source-free contract: their
    sum must integrate to zero on every BE interval and cumulative prefix.
    Both use energy_atol_J alone; relative tolerance cannot scale a zero target.
    """
    if source_contract!='source_free_MB_HD_fixed_material_bands_mesh_integrals':
        raise ValueError('explicit fixed-material-band MB mesh contract required')
    if time_discretization!='backward_euler_all_solved_times':
        raise ValueError('all solved BE clocks required')
    if field_energy_contract not in ('mesh_vertex_electric_field_quadrature','uniform_permittivity_discrete_box'):
        raise ValueError('explicit field energy discretization required')
    def scalar(v,name,nonnegative=False,positive=False):
        a=np.asarray(v)
        if a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a):
            raise ValueError(name+' must be a finite real scalar')
        x=np.longdouble(a)
        if (nonnegative and x<0) or (positive and x<=0):raise ValueError(name+' outside range')
        return x
    def mapping(v,keys,name):
        if not isinstance(v,Mapping) or set(v)!=set(keys):raise ValueError(name+' requires complete exact coverage')
        return {k:scalar(v[k],name+' '+k) for k in keys}
    ref=scalar(reference_energy_eV,'reference_energy_eV')
    ea=scalar(energy_atol_J,'energy_atol_J',nonnegative=True)
    er=scalar(energy_rtol,'energy_rtol',nonnegative=True)
    pa=scalar(particle_atol,'particle_atol',nonnegative=True)
    pr=scalar(particle_rtol,'particle_rtol',nonnegative=True)
    ca=scalar(current_atol_A,'current_atol_A',nonnegative=True)
    rows=tuple(samples)
    if len(rows)<2:raise ValueError('at least two solved samples required')
    states=[];initial_ports=None
    for row in rows:
        if not isinstance(row,Mapping):raise ValueError('sample mapping required')
        storage=mapping(row['storage_J'],STORAGE,'storage_J')
        if any(storage[k]<0 for k in SPECIES+('electrostatic',)):
            raise ValueError('kinetic, lattice and field storage must be nonnegative')
        particles=mapping(row['particles'],SPECIES[:2],'particles')
        if any(v<=0 for v in particles.values()):raise ValueError('positive particle counts required')
        powers={k:mapping(row[k],SPECIES,k) for k in ('joule_power_W','collision_power_W')}
        if powers['joule_power_W']['lattice']!=0:raise ValueError('HD lattice Joule term must be zero')
        ports=row['ports']
        if not isinstance(ports,Mapping) or not ports or any(not isinstance(k,str) or not k for k in ports):
            raise ValueError('all named ports required')
        pp={}
        for name,p in ports.items():
            if not isinstance(p,Mapping):raise ValueError('port mapping required')
            v={k:scalar(p[k],name+' '+k) for k in ('phi_V','Ec_eV','Ev_eV',
                'electron_current_A','hole_current_A','displacement_current_A','total_current_A')}
            if v['Ec_eV']<=v['Ev_eV']:raise ValueError('positive contact band gap required')
            v['inward_heat_W']=mapping(p['inward_heat_W'],SPECIES,'inward_heat_W')
            pp[name]=v
        if initial_ports is None:initial_ports=pp
        if set(pp)!=set(initial_ports):raise ValueError('fixed complete port coverage required')
        for name,p in pp.items():
            if any(p[k]!=initial_ports[name][k] for k in ('phi_V','Ec_eV','Ev_eV')):
                raise ValueError('fixed boundary potentials and band energies required')
        heat={s:sum(p['inward_heat_W'][s] for p in pp.values()) for s in SPECIES}
        work=sum(-(p['Ec_eV']-ref)*p['electron_current_A']-(p['Ev_eV']-ref)*p['hole_current_A']+
                 p['phi_V']*p['displacement_current_A'] for p in pp.values())
        composition=max(abs(p['electron_current_A']+p['hole_current_A']+p['displacement_current_A']-p['total_current_A']) for p in pp.values())
        kcl=abs(sum(p['total_current_A'] for p in pp.values()))
        states.append(dict(time=scalar(row['time_s'],'time_s',nonnegative=True),storage=storage,particles=particles,
            powers=powers,ports=pp,heat=heat,work=work,composition=composition,kcl=kcl))
    times=np.array([s['time'] for s in states],dtype=np.longdouble)
    if np.any(np.diff(times)<=0):raise ValueError('strictly increasing solved clocks required')
    cw=np.longdouble(0);ch={s:np.longdouble(0) for s in SPECIES}
    cc=ch.copy();cp={s:np.longdouble(0) for s in SPECIES[:2]};checkpoints=[]
    collision_exchange=np.longdouble(0)
    for state,dt in zip(states[1:],np.diff(times)):
        step_collision=dt*sum(state['powers']['collision_power_W'].values())
        collision_exchange+=step_collision
        collision_ok=bool(np.isfinite(step_collision) and np.isfinite(collision_exchange)
            and abs(step_collision)<=ea and abs(collision_exchange)<=ea)
        cw+=dt*state['work']
        for s in SPECIES:
            ch[s]+=dt*state['heat'][s]
            cc[s]+=dt*(state['heat'][s]+state['powers']['joule_power_W'][s]+state['powers']['collision_power_W'][s])
        cp['electrons']+=dt*sum(-p['electron_current_A']/Q for p in state['ports'].values())
        cp['holes']+=dt*sum(p['hole_current_A']/Q for p in state['ports'].values())
        increments={s:state['storage'][s]-states[0]['storage'][s] for s in STORAGE}
        residuals={s:increments[s]-cc[s] for s in SPECIES}
        budgets={s:ea+er*max(abs(increments[s]),abs(cc[s])) for s in SPECIES}
        full=sum(increments.values());drive=cw+sum(ch.values());residual=full-drive
        budget=ea+er*max(abs(full),abs(drive))
        particles={s:state['particles'][s]-states[0]['particles'][s]-cp[s] for s in cp}
        pok=all(abs(particles[s])<=pa+pr*max(abs(state['particles'][s]-states[0]['particles'][s]),abs(cp[s])) for s in cp)
        checkpoints.append(dict(time_s=float(state['time']),energy_increments_J={k:float(v) for k,v in increments.items()},
            step_internal_collision_residual_J=float(step_collision),
            cumulative_internal_collision_residual_J=float(collision_exchange),
            internal_collision_budget_J=float(ea),internal_collision_balance_valid=collision_ok,
            cumulative_contact_work_J=float(cw),cumulative_inward_heat_J={k:float(v) for k,v in ch.items()},
            reservoir_residuals_J={k:float(v) for k,v in residuals.items()},reservoir_budgets_J={k:float(v) for k,v in budgets.items()},
            reservoir_balances_valid=bool(all(abs(residuals[s])<=budgets[s] for s in SPECIES)),
            full_storage_residual_J=float(residual),energy_budget_J=float(budget),full_storage_balance_valid=bool(abs(residual)<=budget),
            particle_residuals={k:float(v) for k,v in particles.items()},particle_balance_valid=bool(pok)))
    current_ok=all(s['composition']<=ca and s['kcl']<=ca for s in states)
    full_ok=all(c['full_storage_balance_valid'] for c in checkpoints)
    reservoir_ok=all(c['reservoir_balances_valid'] for c in checkpoints)
    particle_ok=all(c['particle_balance_valid'] for c in checkpoints)
    collision_ok=all(c['internal_collision_balance_valid'] for c in checkpoints)
    return dict(accepted=bool(current_ok and full_ok and reservoir_ok and particle_ok and collision_ok),
        scope=source_contract,time_discretization=time_discretization,field_energy_contract=field_energy_contract,
        spatial_quadrature='explicit_commercial_mesh_integrals',samples=len(states),reference_energy_eV=float(ref),
        current_balance_valid=bool(current_ok),full_storage_balance_valid=bool(full_ok),
        reservoir_balances_valid=bool(reservoir_ok),particle_balance_valid=bool(particle_ok),
        internal_collision_balance_valid=bool(collision_ok),
        maximum_current_component_residual_A=float(max(s['composition'] for s in states)),
        maximum_total_current_balance_A=float(max(s['kcl'] for s in states)),
        maximum_full_storage_residual_J=max(abs(c['full_storage_residual_J']) for c in checkpoints),
        checkpoints=checkpoints,complete_device_energy=False,physical_validated=False,experimental_validated=False,
        general_complex_physics_closed=False,global_temporal_error_bound=False)
