"""Per-cell endpoint balances of independently reaudited general 3T steps."""
import numpy as np
from .three_temperature_energy import reference_band_edges
from .fermi_spectral_energy import reference_reservoir


def endpoint_cell_storage(model, old, new):
    """Independent material storage; electrostatic energy stays in device audit."""
    ld=np.longdouble;V=model.vol.astype(ld);out={}
    for index,(label,density,temperature) in enumerate((
            ('electrons','n_m3','electron_temperature_K'),('holes','p_m3','hole_temperature_K'))):
        def u(state):
            band=reference_band_edges(model,state.temperature_K)[index]
            return np.array([reference_reservoir(n,t,e,model.valleys[label])['energy_density_J_m3']
                for n,t,e in zip(getattr(state,density),getattr(state,temperature),band)],ld)
        out[label]=V*(u(new)-u(old))
    out['lattice']=V*model.capacity*(new.temperature_K.astype(ld)-old.temperature_K)
    if model.trap_capture_law is not None:
        out['traps']=V*model.Nt*model.Et*(new.trap_fraction.astype(ld)-old.trap_fraction)
    return out


def audit_cell_reservoir_path(model, initial, final, cell_ledgers, *, energy_budget_J,
                             particle_budget):
    """Accumulate every cell before any spatial or species sum.

    Inputs must be freshly reconstructed by the independent step auditor.
    No physical or temporal certification is established by these balances.
    Each material balance uses endpoint storage, not a sum of step storage.
    """
    ld=np.longdouble;nc=model.nc;V=model.vol.astype(ld);ledgers=tuple(cell_ledgers)
    carriers=('electrons','holes');trapped=model.trap_capture_law is not None
    endpoint=endpoint_cell_storage(model,initial,final)
    def total(key, label=None):
        values=[]
        for ledger in ledgers:
            item=ledger[key] if label is None else ledger[key][label]
            value=np.asarray(item,ld)
            if value.shape!=(nc,) or not np.all(np.isfinite(value)):
                raise ValueError('invalid independently reconstructed cell ledger: '+key)
            values.append(value)
        return np.sum(values,axis=0,dtype=ld) if values else np.zeros(nc,ld)
    storage={s:total('energy_increments_J',s) for s in endpoint}
    telescoping={s:storage[s]-endpoint[s] for s in endpoint}
    exchange={s:total('carrier_exchange_to_lattice_J',s) for s in carriers}
    band={s:total('band_work_from_lattice_J',s) for s in carriers}
    trap={s:total('trap_carrier_energy_removed_J',s) for s in carriers}
    radiation={s:total('radiative_carrier_energy_removed_J',s) for s in carriers}
    auger={s:total('auger_carrier_energy_added_J',s) for s in carriers}
    intercarrier=total('intercarrier_exchange_J');heat=total('trap_lattice_heat_J')
    residuals={s:endpoint[s]+total('transport_energy_J',s)-total('carrier_electrical_work_J',s)+exchange[s]
        +(1 if s=='electrons' else -1)*intercarrier-total('pair_generation_energy_J',s)-band[s]
        +trap[s]+radiation[s]-auger[s] for s in carriers}
    residuals['lattice']=endpoint['lattice']+total('transport_energy_J','lattice')-sum(exchange.values())+sum(band.values())-heat
    if trapped:residuals['traps']=endpoint['traps']-sum(trap.values())+heat
    if model.radiative_law is not None:
        residuals['photons']=total('radiative_photon_energy_J')-sum(radiation.values())
    if model.auger_events is not None:residuals['auger_internal']=sum(auger.values())
    endpoint_particles={s:V*(after-before) for s,after,before in (
        ('electrons',final.n_m3,initial.n_m3),('holes',final.p_m3,initial.p_m3))}
    particle_telescoping={s:total('particle_increments',s)-endpoint_particles[s] for s in carriers}
    particle_rows={s:endpoint_particles[s]+total('particle_transport',s)-total('generated_pairs')
        +total('trap_capture_counts',s)+total('radiative_recombined_pairs')+total('auger_recombined_pairs') for s in carriers}
    if trapped:
        occupied=V*model.Nt*(final.trap_fraction.astype(ld)-initial.trap_fraction)
        particle_rows['traps']=occupied-total('trap_capture_counts','electrons')+total('trap_capture_counts','holes')
        particle_telescoping['traps']=total('occupied_trap_increment')-occupied
    maximum=lambda rows:max((float(np.max(abs(v),initial=0)) for v in rows.values()),default=0.)
    energy_worst=max(maximum(residuals),maximum(telescoping))
    particle_worst=max(maximum(particle_rows),maximum(particle_telescoping))
    global_particles={s:float(np.sum(v,dtype=ld)) for s,v in particle_rows.items()}
    global_telescoping={s:float(np.sum(v,dtype=ld)) for s,v in particle_telescoping.items()}
    particle_path_worst=max(particle_worst,*(abs(v) for v in global_particles.values()),
        *(abs(v) for v in global_telescoping.values()))
    particle_valid=bool(np.isfinite(particle_budget) and
        all(np.all(np.isfinite(v)) for group in (particle_rows,particle_telescoping) for v in group.values()) and
        all(np.isfinite(v) for v in (*global_particles.values(),*global_telescoping.values())) and
        particle_path_worst<=particle_budget)
    finite=all(np.all(np.isfinite(v)) for group in (endpoint,residuals,telescoping,particle_rows,particle_telescoping) for v in group.values())
    vector_maps=lambda values:{s:list(map(float,v)) for s,v in values.items()}
    return dict(cell_reservoir_path_valid=bool(finite and np.isfinite(energy_budget_J) and
        energy_worst<=energy_budget_J and particle_valid),
        independently_reaudited_cell_reservoirs=True,
        cell_endpoint_energy_increments_J=vector_maps(endpoint),
        cell_storage_telescoping_error_J=vector_maps(telescoping),
        cell_reservoir_energy_residuals_J=vector_maps(residuals),
        cell_particle_balance_residuals=vector_maps(particle_rows),
        cell_particle_telescoping_errors=vector_maps(particle_telescoping),
        maximum_cumulative_cell_energy_error_J=energy_worst,
        maximum_cumulative_cell_particle_error=particle_worst,
        cell_particle_path_valid=particle_valid,
        global_particle_balance_from_cells=global_particles,
        global_particle_telescoping_from_cells=global_telescoping,
        maximum_cumulative_particle_error=particle_path_worst,
        cumulative_cell_particle_atol=particle_budget)
