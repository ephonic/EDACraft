"""Independent energy audit for saved, possibly nonuniform accepted steps."""
from math import fsum
import numpy as np

from .three_temperature_energy import audit_three_temperature_energy
from .three_temperature_trajectory import _endpoint_storage, _same_state
from tcad.solver.adaptive_three_temperature import _scalar
from .three_temperature_cell_path import audit_cell_reservoir_path
from .three_temperature_charge_path import audit_charge_path


def audit_three_temperature_saved_path(model, initial_state, saved_steps, *,
        final_state, charge_atol_C, particle_atol, energy_atol_J,
        cumulative_energy_atol_J=None, cumulative_particle_atol=None, cumulative_charge_atol_C=None):
    """Reconstruct a contiguous path of ``(initial, final, report)`` triples.

    Supports explicit nonuniform steps without presenting them as adaptive
    half steps. Every local audit is recomputed; attached audit summaries do
    not establish acceptance. This operation advances no solver and supplies
    no time-discretization error bound or additional physical closure.
    Separate positive finite cumulative energy, particle and charge budgets may be
    supplied; defaults sum the unchanged per-step budgets (one if empty).
    """
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal
    if not isinstance(model, ThreeTemperatureElectrothermal):
        raise ValueError('three-temperature model required')
    charge = _scalar(charge_atol_C, 'charge budget')
    particle = _scalar(particle_atol, 'particle budget')
    energy = _scalar(energy_atol_J, 'energy budget')
    explicit = None if cumulative_energy_atol_J is None else _scalar(
        cumulative_energy_atol_J, 'cumulative energy budget')
    explicit_particle = None if cumulative_particle_atol is None else _scalar(
        cumulative_particle_atol, 'cumulative particle budget')
    explicit_charge = None if cumulative_charge_atol_C is None else _scalar(
        cumulative_charge_atol_C, 'cumulative charge budget')
    model._validate_state(initial_state); model._validate_state(final_state)
    previous = initial_state; audits = []; ledgers = []
    for item in saved_steps:
        if not isinstance(item, (tuple, list)) or len(item) != 3:
            raise ValueError('saved step requires initial state, final state and report')
        old, new, report = item
        if not _same_state(previous, old):
            raise ValueError('saved path initial state or continuity mismatch')
        audit = audit_three_temperature_energy(model, old, new, report,
            charge_atol_C=charge, particle_atol=particle, energy_atol_J=energy)
        if not audit['valid']:
            raise ValueError('independent saved step audit failed')
        audits.append(audit); ledgers.append(audit['independently_reconstructed_ledger'])
        previous = new
    if not _same_state(previous, final_state):
        raise ValueError('saved path final state mismatch')
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
    endpoint = _endpoint_storage(model, initial_state, final_state, charge)
    sums = lambda key, names: {n: fsum(v[key][n] for v in ledgers) for n in names}
    increments = sums('energy_increments_J', endpoint)
    outward = sums('outward_energy_J', ('electrons', 'holes', 'lattice')+
        (('photons',) if model.radiative_law is not None else ()))
    telescoping = {s: fsum((increments[s], -endpoint[s])) for s in endpoint}
    work = {s: fsum(v[s+'_work_J'] for v in ledgers) for s in ('displacement', 'conduction')}
    absorbed = fsum(v.get('absorbed_pair_energy_J', 0.) for v in ledgers)
    source = fsum(work.values())
    residual = fsum([source, absorbed, *(-v for v in increments.values()), *(-v for v in outward.values())])
    endpoint_residual = fsum([source, absorbed, *(-v for v in endpoint.values()), *(-v for v in outward.values())])
    summed_residual = fsum(v['energy_residual_J'] for v in ledgers)
    carriers = ('electrons', 'holes')
    exchange = sums('carrier_exchange_to_lattice_J', carriers)
    electrical = sums('carrier_electrical_work_J', carriers)
    optional_maps = ('pair_generation_energy_J', 'band_work_from_lattice_J',
        'trap_carrier_energy_removed_J', 'radiative_carrier_energy_removed_J',
        'auger_carrier_energy_added_J')
    terms = {key: {s: fsum(v.get(key, {}).get(s, 0.) for v in ledgers) for s in carriers} for key in optional_maps}
    intercarrier = fsum(v.get('intercarrier_exchange_electron_to_hole_J', 0.) for v in ledgers)
    trap_heat = fsum(v.get('trap_lattice_heat_J', 0.) for v in ledgers)
    channels = {s: fsum((increments[s], outward[s], -electrical[s], exchange[s],
        (1 if s == 'electrons' else -1)*intercarrier,
        -terms['pair_generation_energy_J'][s], -terms['band_work_from_lattice_J'][s],
        terms['trap_carrier_energy_removed_J'][s], terms['radiative_carrier_energy_removed_J'][s],
        -terms['auger_carrier_energy_added_J'][s])) for s in carriers}
    channels['lattice'] = fsum((increments['lattice'], outward['lattice'],
        *(-v for v in exchange.values()), *terms['band_work_from_lattice_J'].values(), -trap_heat))
    if model.trap_capture_law is not None:
        channels['traps'] = fsum((increments['traps'],
            *(-v for v in terms['trap_carrier_energy_removed_J'].values()), trap_heat))
    if model.radiative_law is not None:
        channels['photons'] = fsum((outward['photons'],
            *(-v for v in terms['radiative_carrier_energy_removed_J'].values())))
    if model.auger_events is not None:
        channels['auger_internal'] = fsum(terms['auger_carrier_energy_added_J'].values())
    electrical_residual = fsum((source, -increments['electrostatic'], *(-v for v in electrical.values())))
    tested = [residual, endpoint_residual, electrical_residual,
        fsum((residual, -summed_residual)), *telescoping.values(), *channels.values()]
    values = [*tested, *increments.values(), *endpoint.values(), *outward.values(),
        *work.values(), absorbed, *exchange.values(), *electrical.values()]
    valid = bool(all(np.isfinite(v) for v in values) and max(map(abs, tested)) <= budget)
    result = dict(valid=valid, scope='independent_saved_three_temperature_step_path',
        initial_time_s=initial_state.time_s, final_time_s=final_state.time_s,
        independently_reaudited_steps=count, saved_clock_continuity_valid=True,
        energy_increments_J=increments, endpoint_energy_increments_J=endpoint,
        storage_telescoping_error_J=telescoping, outward_energy_J=outward,
        electrical_work_J=work, absorbed_pair_energy_J=absorbed,
        carrier_exchange_to_lattice_J=exchange, carrier_electrical_work_J=electrical,
        mechanism_energy_terms_J=terms, intercarrier_exchange_electron_to_hole_J=intercarrier,
        trap_lattice_heat_J=trap_heat, reservoir_energy_residuals_J=channels,
        energy_residual_J=residual, endpoint_energy_residual_J=endpoint_residual,
        electrical_work_residual_J=electrical_residual, summed_step_energy_residual_J=summed_residual,
        maximum_step_energy_residual_J=max((abs(a['energy_residual_J']) for a in audits), default=0.),
        cumulative_energy_atol_J=budget, per_step_energy_atol_J=energy,
        cumulative_particle_atol=particle_budget, per_step_particle_atol=particle,
        cumulative_particle_budget_policy='explicit' if explicit_particle is not None else 'sum_of_per_step_budgets',
        per_step_charge_atol_C=charge,
        cumulative_charge_budget_policy='explicit' if explicit_charge is not None else 'sum_of_per_step_budgets',
        cumulative_budget_policy='explicit' if explicit is not None else 'sum_of_per_step_budgets',
        modeled_device_energy_closed=valid, complete_device_energy=False,
        physical_validated=False, experimental_validated=False, global_temporal_error_bound=False)
    cells=audit_cell_reservoir_path(model,initial_state,final_state,
        [a['independently_reconstructed_cell_ledger'] for a in audits],
        energy_budget_J=budget,particle_budget=particle_budget)
    result.update(cells)
    result['valid']=result['modeled_device_energy_closed']=bool(valid and cells['cell_reservoir_path_valid'])
    charges=audit_charge_path(model,initial_state,final_state,ledgers,
        [a['independently_reconstructed_cell_ledger'] for a in audits],charge_budget_C=charge_budget)
    result.update(charges)
    result['valid']=result['modeled_device_energy_closed']=bool(result['valid'] and charges['charge_path_valid'])
    return result
