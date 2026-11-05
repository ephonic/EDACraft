"""Owned, streaming prefix audit of the supported fixed-band FD device model.

Every supplied native substep is independently replayed once. Initial-to-current
local matter/particle balances and global matter/field/source balances are
checked before requesting another row. This adds no new physical channel.
"""
from copy import deepcopy
import numpy as np
from .device_energy_coordinate_transport import audit_device_energy_coordinate_step
from .energy_coordinate_transport import audit_energy_coordinate_step
from .energy_coordinate_trajectory import _same, _storage, _ports, _poisson
from .energy_coordinate_generation import generation_increments
from .energy_coordinate_exchange import exchange_increments
from .energy_coordinate_radiative import radiative_increments
from tcad.solver.cut_cell_transport import Q
from tcad.solver.adaptive_three_temperature import _scalar


class EnergyCoordinatePrefixError(ValueError):
    """A failed prefix, retained as a diagnostic and never an accepted result."""
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__('independent energy-coordinate prefix failed at step ' + str(diagnostic['step']))


def _finite(*values):
    if not all(np.all(np.isfinite(np.asarray(v, np.longdouble))) for v in values):
        raise ValueError('finite independently reconstructed prefix terms required')


def audit_energy_coordinate_prefixes(model, initial_state, records, *, final_state, steps,
        charge_atol_C, particle_atol, energy_atol_J, cumulative_energy_atol_J=None,
        cumulative_particle_atol=None, checkpoint_stride=64):
    """Accept exactly ``steps`` indexed ``{'index','new','report'}`` rows.

    The model/endpoints and each row are privately deep-copied. Cumulative caps
    default to one substep's cap, never steps times that cap. Explicit cumulative
    caps may be tighter. Hard maxima are 2e-28 C, 1e-9 particles and 1e-27 J.
    Field energy is global; carrier electrical work is resolved per cell.
    Checkpoint metadata and numeric accumulator bit/storage costs are bounded
    by the declared finite controls, not by a constant-memory guarantee.
    """
    from tcad.solver.energy_coordinate_transport import _pack, EnergyCoordinateState
    if type(steps) is not int or not 0 <= steps <= 16384:
        raise ValueError('bounded integer prefix step count required')
    if type(checkpoint_stride) is not int or not 1 <= checkpoint_stride <= 16384:
        raise ValueError('bounded checkpoint stride required')
    charge = _scalar(charge_atol_C, 'charge budget')
    particle = _scalar(particle_atol, 'particle budget'); energy = _scalar(energy_atol_J, 'energy budget')
    if charge > 2e-28 or particle > 1e-9 or energy > 1e-27:
        raise ValueError('prefix hard physical budgets cannot be enlarged')
    eb = energy if cumulative_energy_atol_J is None else _scalar(cumulative_energy_atol_J, 'cumulative energy budget')
    pb = particle if cumulative_particle_atol is None else _scalar(cumulative_particle_atol, 'cumulative particle budget')
    if eb > energy or pb > particle: raise ValueError('cumulative budgets may only tighten substep caps')
    model, initial, final = deepcopy((model, initial_state, final_state))
    for state in (initial, final):
        if type(state) is not EnergyCoordinateState: raise ValueError('energy-coordinate endpoints required')
        _, digest = _pack(model, state.thermal, 1., charge, particle, energy)
        if digest != state.configuration_sha256: raise ValueError('prefix endpoint configuration mismatch')
    ld = np.longdouble; nc = model.nc; V = model.vol.astype(ld)
    zero = lambda: np.zeros(nc, ld)
    transport = {s: zero() for s in ('electrons', 'holes', 'lattice')}
    particles = [zero(), zero()]; created = zero(); removed = zero()
    injection = [zero(), zero()]; radiation = [zero(), zero()]
    relaxed = [zero(), zero()]; electrical = [zero(), zero()]
    exchange = zero(); allowance = zero(); photons = zero()
    increments = {s: zero() for s in transport}; field_increment = ld(0); source = ld(0)
    old = initial; count = 0; checkpoints = []; last = None
    maxima = dict(energy_J=0., particles=0., charge_C=0.)
    before_field = _poisson(model, initial, charge)
    for supplied in records:
        if count >= steps: raise ValueError('prefix extra record')
        if type(supplied) is not dict or set(supplied) != {'index', 'new', 'report'}:
            raise ValueError('exact prefix record coverage required')
        row = deepcopy(supplied)
        if type(row['index']) is not int or row['index'] != count: raise ValueError('prefix record sequence mismatch')
        new = row['new']; report = row['report']
        if type(new) is not EnergyCoordinateState: raise ValueError('typed prefix state required')
        auditor = audit_device_energy_coordinate_step if report.get('native_device_session_integrated') is True else audit_energy_coordinate_step
        checked = auditor(model, old, new, report, charge_atol_C=charge, particle_atol=particle, energy_atol_J=energy)
        if not checked['valid']: raise ValueError('independent prefix substep audit failed: ' + str(checked.get('failures')))
        dt = new.thermal.time_s - old.thermal.time_s
        _, ports, work = _ports(model, old, new, charge)
        generated, deposited = generation_increments(model, dt)
        recombined, carrier, photon, _ = radiative_increments(model, new.thermal, dt)
        transfer, rounding = exchange_increments(model, new.thermal, dt)
        created += generated; removed += recombined; exchange += transfer; allowance += rounding; photons += photon
        source += ld(checked['source_work_J']); field_increment += ld(checked['electrostatic_increment_J'])
        for s, label in enumerate(('electrons', 'holes')):
            particles[s] += ports['particle_' + label]
            injection[s] += deposited[s]; radiation[s] += carrier[s]; electrical[s] += work[s]
            relaxed[s] += np.asarray(checked['reconstructed_exchange_J'][s], ld)
            increments[label] += np.asarray(checked['reconstructed_carrier_storage_J'][s], ld)
        increments['lattice'] += np.asarray(checked['reconstructed_lattice_storage_J'], ld)
        for label in transport: transport[label] += ports[label]
        endpoint, cells = _storage(model, initial, new, charge)
        particle_rows = [V * (getattr(new.thermal, name) - getattr(initial.thermal, name))
                         + particles[s] - created + removed for s, name in enumerate(('n_m3', 'p_m3'))]
        energy_rows = {label: cells[label] + transport[label] + relaxed[s] - electrical[s]
                      + (1 if s == 0 else -1) * exchange - injection[s] - radiation[s]
                      for s, label in enumerate(('electrons', 'holes'))}
        energy_rows['lattice'] = cells['lattice'] + transport['lattice'] - relaxed[0] - relaxed[1]
        telescoping = {s: increments[s] - cells[s] for s in transport}
        field_telescope = field_increment - ld(endpoint['electrostatic'])
        outward = {s: np.sum(v, dtype=ld) for s, v in transport.items()}
        generation = sum(np.sum(v, dtype=ld) for v in injection)
        photon_total = np.sum(photons, dtype=ld)
        balance = source + generation - sum(ld(v) for v in endpoint.values()) - sum(outward.values()) - photon_total
        charge_balance = ld(Q) * np.sum(particle_rows[1] - particle_rows[0], dtype=ld)
        after_field = _poisson(model, new, charge)
        terminal_charge = -sum(ld(after_field['integrated_D_flux_C'][f]) - ld(before_field['integrated_D_flux_C'][f]) for f in model.bc)
        terminal_charge -= ld(Q) * np.sum(particles[1] - particles[0], dtype=ld)
        _finite(*particle_rows, *energy_rows.values(), *telescoping.values(), allowance, photons,
                source, generation, *outward.values(), *endpoint.values(), field_telescope, balance, charge_balance, terminal_charge)
        energy_error = max(abs(balance), abs(field_telescope),
            *(np.max(abs(v) + allowance, initial=ld(0)) for v in energy_rows.values()),
            *(abs(np.sum(v, dtype=ld)) + np.sum(allowance, dtype=ld) for v in energy_rows.values()),
            *(np.max(abs(v), initial=ld(0)) for v in telescoping.values()))
        particle_error = max(*(np.max(abs(v), initial=ld(0)) for v in particle_rows),
                             *(abs(np.sum(v, dtype=ld)) for v in particle_rows))
        charge_error = max(abs(charge_balance), abs(terminal_charge))
        last = dict(step=count+1, time_s=new.thermal.time_s,
            cell_particle_residuals=[list(map(float, v)) for v in particle_rows],
            cell_energy_residuals_J={s: list(map(float, v)) for s, v in energy_rows.items()},
            cell_intercarrier_rounding_allowance_J=list(map(float, allowance)),
            global_energy_residual_J=float(balance), charge_residual_C=float(charge_balance), terminal_KCL_C=float(terminal_charge),
            endpoint_energy_increments_J=endpoint, outward_energy_J={s:float(v) for s,v in outward.items()},
            source_work_J=float(source), generation_energy_J=float(generation), photon_energy_J=float(photon_total),
            generated_pairs=list(map(float, created)), radiative_recombined_pairs=list(map(float, removed)),
            maximum_energy_error_J=float(energy_error), maximum_particle_error=float(particle_error), maximum_charge_error_C=float(charge_error),
            cumulative_energy_atol_J=eb, cumulative_particle_atol=pb, charge_atol_C=charge,
            valid=bool(energy_error<=eb and particle_error<=pb and charge_error<=charge))
        if not last['valid']: raise EnergyCoordinatePrefixError(last)
        maxima = {key:max(maxima[key], float(value)) for key,value in zip(maxima, (energy_error, particle_error, charge_error))}
        count += 1; old = new
        if count % checkpoint_stride == 0 or count == steps: checkpoints.append(last)
    if count != steps: raise ValueError('prefix missing records')
    if not _same(old, final): raise ValueError('prefix final state differs from declared endpoint')
    return dict(valid=True, scope='owned_fixed_band_FD_all_native_prefixes_v1', accepted_native_substeps=count,
        audited_cell_substeps=count*nc, independently_reaudited_substeps=count, checkpoints=checkpoints, final=last,
        maximum_prefix_errors=maxima, cumulative_budget_policy='fixed_cap_at_every_native_substep',
        all_local_matter_and_particle_prefixes_closed=True, all_global_field_energy_and_charge_prefixes_closed=True,
        field_energy_allocation='global_HMM_storage_with_cell_carrier_electrical_work',
        producer_audit_claims_used=False, native_physics_used=False, complete_device_energy=False,
        general_complex_physics_closed=False, physical_validated=False, experimental_validated=False)
