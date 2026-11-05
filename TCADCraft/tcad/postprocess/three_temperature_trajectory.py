"""Independent cumulative energy balance of an accepted three-temperature path."""
from math import fsum
import numpy as np

from .three_temperature_energy import audit_three_temperature_energy,reference_band_edges
from .fermi_spectral_energy import reference_reservoir
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
from tcad.solver.cut_cell_transport import Q
from tcad.solver.adaptive_three_temperature import _scalar
from .three_temperature_cell_path import audit_cell_reservoir_path
from .three_temperature_charge_path import audit_charge_path


def _same_state(a, b):
    return a.time_s == b.time_s and all(np.array_equal(getattr(a, f), getattr(b, f))
        for f in ('n_m3', 'p_m3', 'temperature_K', 'electron_temperature_K',
                  'hole_temperature_K', 'trap_fraction'))


def _endpoint_storage(model, old, new, charge_atol_C):
    """Difference reservoirs before summing; do not subtract large device totals."""
    ld = np.longdouble; V = model.vol.astype(ld)
    increments = {}
    for label, density, temperature, index in (
            ('electrons', 'n_m3', 'electron_temperature_K', 0),
            ('holes', 'p_m3', 'hole_temperature_K', 1)):
        def u(state):
            band=reference_band_edges(model,state.temperature_K)[index]
            return np.array([reference_reservoir(n, t, e, model.valleys[label])['energy_density_J_m3']
                for n, t, e in zip(getattr(state, density), getattr(state, temperature), band)], dtype=ld)
        increments[label] = float(np.sum(V*(u(new)-u(old)), dtype=ld))
    increments['lattice'] = float(np.sum(V*model.capacity*(new.temperature_K.astype(ld)-old.temperature_K), dtype=ld))
    if model.trap_capture_law is not None:
        increments['traps']=float(np.sum(V*model.Nt*model.Et*(new.trap_fraction.astype(ld)-old.trap_fraction),dtype=ld))
    def electrostatic(state):
        r = solve_cut_cell_poisson(model.mesh, model.eps,
            model.rhofix.astype(ld)+Q*(state.p_m3-state.n_m3-model.Nt.astype(ld)*state.trap_fraction),
            dirichlet_V=model.bc, charge_atol_C=charge_atol_C)
        if not r['valid']:
            raise ValueError('trajectory endpoint Poisson audit failed')
        return ld(r['electrostatic_energy_J'])
    increments['electrostatic'] = float(electrostatic(new)-electrostatic(old))
    return increments


def audit_three_temperature_trajectory(model, initial_state, interval_reports, *,
        final_state, charge_atol_C, particle_atol, energy_atol_J,
        cumulative_energy_atol_J=None, cumulative_particle_atol=None, cumulative_charge_atol_C=None):
    """Reaudit accepted substeps, integrated work/ports and endpoint storage.

    The input is the adaptive API's accepted interval reports. Attached audit
    summaries and the trial-history ``attempts`` are not used as evidence.
    Each of the two accepted half steps is reconstructed independently, with
    exact five-field/trap/clock continuity. Discarded coarse and rejected trial
    solutions contribute nothing. No solver is advanced by this function.

    By default the cumulative bound is N times the caller's unchanged per-step
    energy/particle/charge budget (one budget for an empty path); separate positive
    finite bounds may be supplied explicitly. The particle bound covers both
    carrier and trap balances, including every cell. This sum of local budgets
    is not a temporal error estimate or general multiphysics qualification.
    """
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    if not isinstance(model, ThreeTemperatureElectrothermal):
        raise ValueError('three-temperature model required')
    charge = _scalar(charge_atol_C, 'charge budget')
    particle = _scalar(particle_atol, 'particle budget')
    energy = _scalar(energy_atol_J, 'energy budget')
    explicit = None if cumulative_energy_atol_J is None else _scalar(cumulative_energy_atol_J, 'cumulative energy budget')
    explicit_particle = None if cumulative_particle_atol is None else _scalar(
        cumulative_particle_atol, 'cumulative particle budget')
    explicit_charge = None if cumulative_charge_atol_C is None else _scalar(
        cumulative_charge_atol_C, 'cumulative charge budget')
    model._validate_state(initial_state); model._validate_state(final_state)
    intervals = tuple(interval_reports)
    ledgers = []; cell_ledgers = []; previous = initial_state
    maximum_cell = maximum_device = 0.
    for interval in intervals:
        if (interval.get('valid') is not True or
                interval.get('scope') != 'adaptive_FD_three_temperature_local_error_control' or
                not _same_state(previous, interval['initial_state'])):
            raise ValueError('accepted trajectory interval coverage or continuity mismatch')
        states = tuple(interval['substep_states']); reports = tuple(interval['substep_reports'])
        if len(states) != 2 or len(reports) != 2 or interval.get('accepted_native_substeps') != 2:
            raise ValueError('two accepted half steps per interval required')
        start = previous.time_s
        for state, report in zip(states, reports):
            audit = audit_three_temperature_energy(model, previous, state, report,
                charge_atol_C=charge, particle_atol=particle, energy_atol_J=energy)
            if not audit['valid']:
                raise ValueError('independent accepted substep audit failed')
            ledgers.append(audit['independently_reconstructed_ledger'])
            cell_ledgers.append(audit['independently_reconstructed_cell_ledger'])
            maximum_cell = max(maximum_cell, audit['max_cell_energy_residual_J'])
            maximum_device = max(maximum_device, abs(audit['energy_residual_J']))
            previous = state
        if previous.time_s-start != interval['accepted_interval_s']:
            raise ValueError('accepted interval duration mismatch')
    if not _same_state(previous, final_state):
        raise ValueError('trajectory final state does not match accepted path')
    count = len(ledgers)
    budget = explicit if explicit is not None else max(1, count)*energy
    if not np.isfinite(budget) or budget <= 0:
        raise ValueError('cumulative energy budget out of range')
    particle_budget = explicit_particle if explicit_particle is not None else max(1, count)*particle
    if not np.isfinite(particle_budget) or particle_budget <= 0:
        raise ValueError('cumulative particle budget out of range')
    charge_budget = explicit_charge if explicit_charge is not None else max(1, count)*charge
    if not np.isfinite(charge_budget) or charge_budget <= 0:
        raise ValueError('cumulative charge budget out of range')
    sum_map = lambda key, names: {name: fsum(v[key][name] for v in ledgers) for name in names}
    trapped=model.trap_capture_law is not None
    radiative=model.radiative_law is not None
    auger=model.auger_events is not None
    reservoirs = ('electrons', 'holes', 'lattice', 'electrostatic')+(('traps',) if trapped else ())
    carriers = reservoirs[:2]
    increments = sum_map('energy_increments_J', reservoirs)
    outward = sum_map('outward_energy_J', reservoirs[:3]+(('photons',) if radiative else ()))
    exchange = sum_map('carrier_exchange_to_lattice_J', carriers)
    carrier_work = sum_map('carrier_electrical_work_J', carriers)
    displacement = fsum(v['displacement_work_J'] for v in ledgers)
    conduction = fsum(v['conduction_work_J'] for v in ledgers)
    source = fsum((displacement, conduction))
    absorbed = fsum(v.get('absorbed_pair_energy_J',0.) for v in ledgers)
    pairs = fsum(v.get('generated_pairs',0.) for v in ledgers)
    injection = {s:fsum(v.get('pair_generation_energy_J',{}).get(s,0.) for v in ledgers) for s in carriers}
    terminal_charge = sum_map('terminal_charge_C', model.bc)
    endpoint = _endpoint_storage(model, initial_state, final_state, charge)
    telescoping = {s: fsum((increments[s], -endpoint[s])) for s in reservoirs}
    residual = fsum([displacement, conduction, absorbed, *(-v for v in increments.values()), *(-v for v in outward.values())])
    endpoint_residual = fsum([displacement, conduction, absorbed, *(-v for v in endpoint.values()), *(-v for v in outward.values())])
    channels = {s: fsum((increments[s], outward[s], -carrier_work[s], exchange[s])) for s in carriers}
    intercarrier = fsum(v.get('intercarrier_exchange_electron_to_hole_J',0.) for v in ledgers)
    channels['electrons'] = fsum((channels['electrons'],intercarrier,-injection['electrons']))
    channels['holes'] = fsum((channels['holes'],-intercarrier,-injection['holes']))
    channels['lattice'] = fsum((increments['lattice'], outward['lattice'], -exchange['electrons'], -exchange['holes']))
    band_work={s:fsum(v.get('band_work_from_lattice_J',{}).get(s,0.) for v in ledgers) for s in carriers}
    if model.temperature_dependent_bands:
        for s in carriers:channels[s]=fsum((channels[s],-band_work[s]))
        channels['lattice']=fsum((channels['lattice'],*band_work.values()))
    captured={s:fsum(v.get('trap_capture_counts',{}).get(s,0.) for v in ledgers) for s in carriers}
    trap_removed={s:fsum(v.get('trap_carrier_energy_removed_J',{}).get(s,0.) for v in ledgers) for s in carriers}
    trap_heat=fsum(v.get('trap_lattice_heat_J',0.) for v in ledgers)
    if trapped:
        for s in carriers:channels[s]=fsum((channels[s],trap_removed[s]))
        channels['lattice']=fsum((channels['lattice'],-trap_heat))
        channels['traps']=fsum((increments['traps'],-trap_removed['electrons'],-trap_removed['holes'],trap_heat))
    radiation_removed={s:fsum(v.get('radiative_carrier_energy_removed_J',{}).get(s,0.) for v in ledgers) for s in carriers}
    radiation_pairs=fsum(v.get('radiative_recombined_pairs',0.) for v in ledgers)
    if radiative:
        for s in carriers:channels[s]=fsum((channels[s],radiation_removed[s]))
        channels['photons']=fsum((outward['photons'],-radiation_removed['electrons'],-radiation_removed['holes']))
    summed_residual = fsum(v['energy_residual_J'] for v in ledgers)
    auger_added={s:fsum(v.get('auger_carrier_energy_added_J',{}).get(s,0.) for v in ledgers) for s in carriers}
    auger_pairs=fsum(v.get('auger_recombined_pairs',0.) for v in ledgers)
    if auger:
        for s in carriers:channels[s]=fsum((channels[s],-auger_added[s]))
        channels['auger_internal']=fsum(auger_added.values())
    electrical_residual = fsum((source, -increments['electrostatic'], *(-v for v in carrier_work.values())))
    values = [*increments.values(), *outward.values(), *endpoint.values(), *telescoping.values(),
              *exchange.values(), *carrier_work.values(), *terminal_charge.values(),
              displacement, conduction, source, residual, endpoint_residual, summed_residual,
              electrical_residual, intercarrier, absorbed, pairs, *injection.values(), *channels.values()]
    worst = max(map(abs, [residual, endpoint_residual, electrical_residual,
                         residual-summed_residual, *telescoping.values(), *channels.values()]))
    valid = bool(all(np.isfinite(v) for v in values) and worst <= budget)
    result = dict(valid=valid, scope='independent_accepted_path_three_temperature_energy_ledger',
        initial_time_s=initial_state.time_s, final_time_s=final_state.time_s,
        accepted_intervals=len(intervals), accepted_native_substeps=count,
        independently_reaudited_substeps=count, discarded_trials_included=False,
        energy_increments_J=increments, endpoint_energy_increments_J=endpoint,
        storage_telescoping_error_J=telescoping, outward_energy_J=outward,
        carrier_exchange_to_lattice_J=exchange, carrier_electrical_work_J=carrier_work,
        displacement_work_J=displacement, conduction_work_J=conduction,
        source_work_J=source, terminal_charge_C=terminal_charge,
        energy_residual_J=residual, endpoint_energy_residual_J=endpoint_residual,
        reservoir_energy_residuals_J=channels, electrical_work_residual_J=electrical_residual,
        summed_substep_energy_residual_J=summed_residual,
        maximum_substep_cell_energy_residual_J=maximum_cell,
        maximum_substep_device_energy_residual_J=maximum_device,
        per_substep_energy_atol_J=energy, cumulative_energy_atol_J=budget,
        per_substep_particle_atol=particle, cumulative_particle_atol=particle_budget,
        cumulative_particle_budget_policy='explicit' if explicit_particle is not None else 'sum_of_per_substep_budgets',
        per_substep_charge_atol_C=charge,
        cumulative_charge_budget_policy='explicit' if explicit_charge is not None else 'sum_of_per_substep_budgets',
        cumulative_budget_policy='explicit' if explicit is not None else 'sum_of_per_substep_budgets',
        modeled_device_energy_closed=valid, complete_device_energy=False,
        physical_validated=False, experimental_validated=False, global_temporal_error_bound=False)
    if np.any(model.intercarrier_conductance_W_m3_K != 0):
        result['intercarrier_exchange_electron_to_hole_J'] = intercarrier
    if model.temperature_dependent_bands:
        result['band_work_from_lattice_J']=band_work
        result['temperature_dependent_band_entropy_closed']=False
    if np.any(model.pair_generation_rate_m3_s != 0) or trapped or radiative or auger:
        result.update(generated_pairs=pairs,absorbed_pair_energy_J=absorbed,pair_generation_energy_J=injection)
        particle_increment={s:fsum(v['particle_increments'][s] for v in ledgers) for s in carriers}
        particle_out={s:fsum(v['outward_particles'][s] for v in ledgers) for s in carriers}
        endpoint_particle={s:float(np.sum(model.vol.astype(np.longdouble)*(after-before),dtype=np.longdouble))
            for s,after,before in (('electrons',final_state.n_m3,initial_state.n_m3),
                                  ('holes',final_state.p_m3,initial_state.p_m3))}
        particle_residual={s:fsum((endpoint_particle[s],particle_out[s],-pairs,captured[s],radiation_pairs,auger_pairs)) for s in carriers}
        particle_telescoping={s:fsum((particle_increment[s],-endpoint_particle[s])) for s in carriers}
        particle_values=[*particle_residual.values(),*particle_telescoping.values()]
        result.update(particle_increments=particle_increment,endpoint_particle_increments=endpoint_particle,
            outward_particles=particle_out,particle_balance_residuals=particle_residual,
            particle_telescoping_errors=particle_telescoping,cumulative_particle_atol=particle_budget)
        result['valid'] = result['modeled_device_energy_closed'] = bool(valid and
            np.isfinite(particle_budget) and all(np.isfinite(v) and abs(v)<=particle_budget for v in particle_values))
    if trapped:
        occupied=float(np.sum(model.vol.astype(np.longdouble)*model.Nt*(
            final_state.trap_fraction.astype(np.longdouble)-initial_state.trap_fraction),dtype=np.longdouble))
        summed_occupied=fsum(v['occupied_trap_increment'] for v in ledgers)
        trap_balance=fsum((occupied,-captured['electrons'],captured['holes']))
        trap_telescoping=fsum((summed_occupied,-occupied))
        charge_balance=Q*fsum((endpoint_particle['holes'],-endpoint_particle['electrons'],-occupied,
                              particle_out['holes'],-particle_out['electrons']))
        result.update(trap_capture_counts=captured,trap_carrier_energy_removed_J=trap_removed,
            trap_lattice_heat_J=trap_heat,occupied_trap_increment=occupied,
            trap_particle_balance_residual=trap_balance,trap_particle_telescoping_error=trap_telescoping,
            trap_entropy_production_J_K=fsum(v['trap_entropy_production_J_K'] for v in ledgers),
            total_charge_balance_residual_C=charge_balance,cumulative_charge_atol_C=charge_budget)
        result['valid']=result['modeled_device_energy_closed']=bool(result['valid'] and
            all(np.isfinite(v) and abs(v)<=particle_budget for v in (trap_balance,trap_telescoping)) and
            np.isfinite(charge_balance) and abs(charge_balance)<=charge_budget)
    if radiative:
        result.update(radiative_device_coupled=True,radiative_recombined_pairs=radiation_pairs,
            radiative_carrier_energy_removed_J=radiation_removed,radiative_photon_energy_J=outward['photons'],
            radiative_entropy_production_J_K=fsum(v['radiative_entropy_production_J_K'] for v in ledgers))
    if auger:
        result.update(auger_device_coupled=True,auger_material_calibrated=False,auger_continuum_kernel_integrated=False,
            auger_recombined_pairs=auger_pairs,auger_carrier_energy_added_J=auger_added,
            auger_entropy_production_J_K=fsum(v['auger_entropy_production_J_K'] for v in ledgers))
    cells=audit_cell_reservoir_path(model,initial_state,final_state,cell_ledgers,
        energy_budget_J=budget,particle_budget=particle_budget)
    result.update(cells)
    result['valid']=result['modeled_device_energy_closed']=bool(result['valid'] and cells['cell_reservoir_path_valid'])
    charges=audit_charge_path(model,initial_state,final_state,ledgers,cell_ledgers,charge_budget_C=charge_budget)
    result.update(charges)
    result['valid']=result['modeled_device_energy_closed']=bool(result['valid'] and charges['charge_path_valid'])
    return result
