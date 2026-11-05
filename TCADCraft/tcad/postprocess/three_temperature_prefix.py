"""Fixed-budget prefixes of general supported FD three-temperature records.

All step ledgers are freshly reconstructed. Dynamic traps, discrete Auger,
radiation, prescribed generation, intercarrier exchange and nonlinear band work
retain the applicability restrictions of the existing independent step auditor.
"""
from copy import deepcopy
import numpy as np
from .three_temperature_energy import audit_three_temperature_energy
from .three_temperature_trajectory import _same_state, _endpoint_storage
from .three_temperature_cell_path import audit_cell_reservoir_path
from .three_temperature_charge_path import audit_charge_path
from tcad.solver.adaptive_three_temperature import _scalar


class ThreeTemperaturePrefixError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__('independent three-temperature prefix failed at step '+str(diagnostic['step']))


def _accumulate(previous, value):
    if isinstance(value, dict):
        if previous is not None and set(previous) != set(value):
            raise ValueError('independent prefix ledger schema changed')
        return {k: _accumulate(None if previous is None else previous[k], v) for k, v in value.items()}
    array = np.asarray(value, np.longdouble)
    if not np.all(np.isfinite(array)):
        raise ValueError('finite independently reconstructed prefix terms required')
    if previous is not None and previous.shape != array.shape:
        raise ValueError('independent prefix ledger shape changed')
    result = array.copy() if previous is None else previous+array
    if not np.all(np.isfinite(result)):
        raise ValueError('prefix accumulator overflow')
    return result


def audit_three_temperature_prefixes(model, initial_state, records, *, final_state, steps,
        charge_atol_C, particle_atol, energy_atol_J, cumulative_energy_atol_J=None,
        cumulative_particle_atol=None, cumulative_charge_atol_C=None, checkpoint_stride=64):
    """Audit indexed raw native steps, stopping at the first failed prefix.

    Records contain exactly index, new and report. Configuration/endpoints are
    owned before iteration, and each supplied record is copied before checking.
    Cumulative budgets default to one substep cap and can only be tightened.
    This explicit audit does not roll back already computed caller states.
    Field storage is global; no per-cell Poynting certification is implied.
    """
    from tcad.solver.three_temperature import ThreeTemperatureElectrothermal, ThreeTemperatureState
    if type(steps) is not int or not 0 <= steps <= 16384:
        raise ValueError('bounded integer prefix step count required')
    if type(checkpoint_stride) is not int or not 1 <= checkpoint_stride <= 16384:
        raise ValueError('bounded checkpoint stride required')
    caps = []
    for value, cumulative, hard, name in (
            (energy_atol_J, cumulative_energy_atol_J, 1e-27, 'energy'),
            (particle_atol, cumulative_particle_atol, 1e-9, 'particle'),
            (charge_atol_C, cumulative_charge_atol_C, 2e-28, 'charge')):
        cap = _scalar(value, name+' budget')
        bound = cap if cumulative is None else _scalar(cumulative, 'cumulative '+name+' budget')
        if cap > hard or bound > cap:
            raise ValueError('prefix hard budgets cannot be enlarged')
        caps.append((cap, bound))
    (energy, eb), (particle, pb), (charge, qb) = caps
    model, initial, final = deepcopy((model, initial_state, final_state))
    if type(model) is not ThreeTemperatureElectrothermal or not 1 <= model.nc <= 64:
        raise ValueError('unmodified three-temperature model with 1..64 cells required')
    for state in (initial, final):
        if type(state) is not ThreeTemperatureState:
            raise ValueError('explicit three-temperature endpoints required')
        model._validate_state(state)
    previous = initial
    ledger = cells = None
    checkpoints = []
    last = None
    maxima = dict(energy_J=0., particles=0., charge_C=0.)
    count = 0
    ld = np.longdouble
    for supplied in records:
        if count >= steps:
            raise ValueError('prefix extra record')
        if type(supplied) is not dict or set(supplied) != {'index', 'new', 'report'}:
            raise ValueError('exact prefix record coverage required')
        row = deepcopy(supplied)
        if type(row['index']) is not int or row['index'] != count:
            raise ValueError('prefix record sequence mismatch')
        new = row['new']
        if type(new) is not ThreeTemperatureState:
            raise ValueError('explicit three-temperature record state required')
        checked = audit_three_temperature_energy(model, previous, new, row['report'],
            charge_atol_C=charge, particle_atol=particle, energy_atol_J=energy)
        if not checked['valid']:
            raise ValueError('independent prefix substep audit failed')
        ledger = _accumulate(ledger, checked['independently_reconstructed_ledger'])
        cells = _accumulate(cells, checked['independently_reconstructed_cell_ledger'])
        local = audit_cell_reservoir_path(model, initial, new, [cells],
            energy_budget_J=eb, particle_budget=pb)
        charges = audit_charge_path(model, initial, new, [ledger], [cells], charge_budget_C=qb)
        endpoint = _endpoint_storage(model, initial, new, charge)
        increments = ledger['energy_increments_J']
        telescope = {s: increments[s]-ld(endpoint[s]) for s in endpoint}
        source = ld(ledger['source_work_J'])
        injected = ld(ledger.get('absorbed_pair_energy_J', 0.))
        outward = sum(ledger['outward_energy_J'].values(), ld(0))
        balance = source+injected-sum(map(ld, endpoint.values()), ld(0))-outward
        field_work = source-ld(endpoint['electrostatic'])-sum(ledger['carrier_electrical_work_J'].values(), ld(0))
        # Check spatially summed reservoir rows too: local residuals can share a sign.
        global_rows = {s: np.sum(v, dtype=ld) for s, v in local['cell_reservoir_energy_residuals_J'].items()}
        ee = max(abs(balance), abs(field_work), *(abs(v) for v in telescope.values()),
            *(abs(v) for v in global_rows.values()), ld(local['maximum_cumulative_cell_energy_error_J']))
        pe = ld(local['maximum_cumulative_particle_error'])
        qe = ld(charges['maximum_cumulative_charge_error_C'])
        finite = all(np.isfinite(v) for v in (ee, pe, qe))
        last = dict(step=count+1, time_s=new.time_s, **local, **charges,
            endpoint_energy_increments_J=endpoint,
            storage_telescoping_error_J={s:float(v) for s,v in telescope.items()},
            global_reservoir_energy_residuals_J={s:float(v) for s,v in global_rows.items()},
            global_energy_residual_J=float(balance), electrical_work_residual_J=float(field_work),
            maximum_energy_error_J=float(ee), maximum_particle_error=float(pe), maximum_charge_error_C=float(qe),
            cumulative_energy_atol_J=eb, cumulative_particle_atol=pb,
            valid=bool(finite and local['cell_reservoir_path_valid'] and charges['charge_path_valid']
                and ee <= eb and pe <= pb and qe <= qb))
        if not last['valid']:
            raise ThreeTemperaturePrefixError(last)
        for key, value in zip(maxima, (ee, pe, qe)):
            maxima[key] = max(maxima[key], float(value))
        previous = new
        count += 1
        if count % checkpoint_stride == 0 or count == steps:
            checkpoints.append(last)
    if count != steps:
        raise ValueError('prefix missing records')
    if not _same_state(previous, final):
        raise ValueError('prefix final state differs from declared endpoint')
    return dict(valid=True, scope='owned_general_FD_three_temperature_prefixes_v1',
        accepted_native_substeps=count, independently_reaudited_substeps=count,
        audited_cell_substeps=count*model.nc, checkpoints=checkpoints, final=last,
        maximum_prefix_errors=maxima, cumulative_budget_policy='fixed_cap_at_every_native_substep',
        native_physics_used=False, producer_audit_claims_used=False,
        field_energy_allocation='global_HMM_storage_with_cell_carrier_electrical_work',
        complete_device_energy=False, general_complex_physics_closed=False,
        physical_validated=False, experimental_validated=False)
