"""Independent refinement comparison for homogeneous uniform 1D MB controls.

All meshes use the same physical section for carrier and lattice transport.
Restriction sums extensive inventories before recovering three temperatures.
This measures mesh differences, without certifying spatial order or accuracy.
"""
import json
from fractions import Fraction
from .boltzmann_rounded_trajectory import canonical_bytes, trajectory_contract
from .boltzmann_owned_trajectory import audit_mb_owned_trajectory
from .boltzmann_recomputed_transport import point, scaled_value_fraction
from .boltzmann_scaled_split import ALPHA, _command, _display
from .boltzmann_product_range import _vector
from .boltzmann_time_refinement import _observed_order


def _extensive(state):
    p = point(state['endpoint']); f = p['frame']; volume = f[4]
    return [volume * x for x in (
        *p['n'], p['K'][0] + f[5] * p['n'][0],
        p['K'][1] + f[6] * p['n'][1], f[3] * p['Tl'],
    )]


def _restricted_inventory(states, cells):
    factor = len(states) // cells
    inventories = [_extensive(s) for s in states]
    return [[sum((v[k] for v in inventories[i * factor:(i + 1) * factor]), Fraction())
             for k in range(5)] for i in range(cells)]


def _restricted_temperatures(states, cells):
    factor = len(states) // cells; result = []
    for i, values in enumerate(_restricted_inventory(states, cells)):
        group = states[i * factor:(i + 1) * factor]
        f = point(group[0]['endpoint'])['frame']
        volume = sum((point(s['endpoint'])['frame'][4] for s in group), Fraction())
        nn, np, un, up, lattice = values
        result.extend((lattice / (f[3] * volume),
                       (un - f[5] * nn) / (ALPHA * nn),
                       (up - f[6] * np) / (ALPHA * np)))
    return tuple(result)


def _validated_contracts(contracts, length_m, area_m2):
    if not 3 <= len(contracts) <= 5 or any(type(c) is not dict for c in contracts):
        raise ValueError('three to five explicit uniform spatial contracts required')
    contracts = tuple(json.loads(canonical_bytes(c)) for c in contracts)
    length, area = _command(length_m), _command(area_m2)
    if min(length, area) <= 0:
        raise ValueError('positive uniform domain length and common section required')
    for c in contracts:
        try:
            expected = trajectory_contract(c['configurations'], c['initial'], c['faces'], c['thermal_faces'],
                c['dt_s'], c['steps'], impulses_J=c['impulses_J'],
                particle_atol=c['particle_atol'], energy_atol_J=c['energy_atol_J'])
        except (KeyError, TypeError) as exc:
            raise ValueError('spatial contract coverage') from exc
        if c != expected:
            raise ValueError('spatial contract metadata mismatch')
    base = contracts[0]; cells = len(base['initial']); steps = base['steps']
    if cells < 2:
        raise ValueError('at least two coarsest spatial cells required')
    if cells * steps * 3 * len(contracts) > 65536:
        raise ValueError('common spatial temperature sample budget exceeded')
    fixed = set(base) - {'configurations', 'initial', 'faces', 'thermal_faces', 'impulses_J'}
    reference = point(base['initial'][0]['endpoint'])['frame']
    cfg = base['configurations'][0]
    if not base['faces'] or not base['thermal_faces']:
        raise ValueError('uniform carrier and Fourier topology required')
    try:
        mobility = _command(base['faces'][0]['geometry'][3])
        conductivity = _command(base['thermal_faces'][0]['geometry'][3])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError('uniform transport coefficients required') from exc
    if min(mobility, conductivity) <= 0:
        raise ValueError('positive uniform transport coefficients required')
    initial_inventory = _restricted_inventory(base['initial'], cells)
    for level, c in enumerate(contracts):
        factor = 1 << level; count = cells * factor
        if len(c['initial']) != count or any(c[k] != base[k] for k in fixed):
            raise ValueError('factor-two cells with identical time controls and budgets required')
        volume = area * length / count; half = length / (2 * count)
        for state, configuration in zip(c['initial'], c['configurations']):
            frame = point(state['endpoint'])['frame']; parameters = configuration['parameters']
            if frame[:4] + frame[5:] != reference[:4] + reference[5:] or frame[4] != volume:
                raise ValueError('uniform frozen frame or geometric volume mismatch')
            if any(configuration[k] != cfg[k] for k in ('valleys_n', 'valleys_p')) or (
                parameters[:1] + parameters[2:] != cfg['parameters'][:1] + cfg['parameters'][2:]
            ) or _vector(parameters)[1] != volume or _vector(parameters)[0] != frame[3]:
                raise ValueError('homogeneous material or configuration volume mismatch')
        if len(c['faces']) != count + 1 or len(c['thermal_faces']) != count + 1:
            raise ValueError('complete uniform chain and two end boundaries required')
        for faces, coefficient, thermal in ((c['faces'], mobility, False),
                                             (c['thermal_faces'], conductivity, True)):
            for i, face in enumerate(faces):
                boundary = i >= count - 1
                owner = i if not boundary else (0 if i == count - 1 else count - 1)
                keys = {'owner', 'geometry', ('bath_temperature_K' if thermal else 'reservoir') if boundary else 'neighbor'}
                if set(face) != keys or face['owner'] != owner or (not boundary and face['neighbor'] != i + 1):
                    raise ValueError('uniform oriented chain topology mismatch')
                expected_geometry = [area, half, Fraction() if boundary else half, coefficient, coefficient]
                if list(map(_command, face['geometry'])) != expected_geometry:
                    raise ValueError('common carrier/lattice section or center distance mismatch')
                if boundary:
                    key = 'bath_temperature_K' if thermal else 'reservoir'
                    parent_face = (base['thermal_faces'] if thermal else base['faces'])[-2 if i == count - 1 else -1]
                    if face[key] != parent_face[key]:
                        raise ValueError('identical maintained boundary data required')
        if _restricted_inventory(c['initial'], cells) != initial_inventory:
            raise ValueError('conservative initial particle/energy restriction mismatch')
        if any(_command(q[k]) * factor != _command(base['impulses_J'][i // factor][k])
               for i, q in enumerate(c['impulses_J']) for k in range(3)):
            raise ValueError('identical source density on refined cells required')
        if any(s['physical_clock'] != base['initial'][0]['physical_clock'] or
               s['time_s'] != base['initial'][0]['time_s'] for s in c['initial']):
            raise ValueError('identical initial physical clocks required')
    return contracts


def audit_mb_uniform_spatial_refinement(contracts, record_streams, *, length_m, area_m2):
    """Audit 3..5 complete trajectories, then compare conservative restrictions.

    This bounded API admits a homogeneous uniform oriented chain, two maintained
    carrier contacts, two thermal baths, constant mobility/conductivity and exact
    volume=area*width geometry. All levels share dt, steps and source density.
    Initial extensive quantities must restrict exactly to the base grid; this
    alone does not identify a unique underlying continuous initial field.
    """
    contracts = tuple(contracts); record_streams = tuple(record_streams)
    if len(record_streams) != len(contracts):
        raise ValueError('one spatial stream per contract required')
    contracts = _validated_contracts(contracts, length_m, area_m2)
    cells = len(contracts[0]['initial']); steps = contracts[0]['steps']
    samples = []; audits = []
    for c, stream in zip(contracts, record_streams):
        level_samples = []
        def records():
            for row in stream:
                row = json.loads(canonical_bytes(row))
                yield row  # Resume only after the complete interval is accepted.
                level_samples.append((scaled_value_fraction(row['new'][0]['physical_clock']),
                                      _restricted_temperatures(row['new'], cells)))
        audits.append(audit_mb_owned_trajectory(c, records(), checkpoint_stride=16))
        if len(level_samples) != steps:
            raise ValueError('complete common spatial/time sample coverage required')
        samples.append(level_samples)
    maxima = [Fraction()] * (len(contracts) - 1); peaks = [None] * len(maxima)
    profile = []; contractions = [0] * (len(maxima) - 1); expansions = contractions.copy()
    for step, rows in enumerate(zip(*samples), 1):
        clock = rows[0][0]
        if any(r[0] != clock for r in rows):
            raise ValueError('identical exact common clocks required')
        differences = [max(abs(x - y) for x, y in zip(a[1], b[1])) for a, b in zip(rows, rows[1:])]
        for i, delta in enumerate(differences):
            if delta > maxima[i]:
                maxima[i] = delta; peaks[i] = dict(step=step, time_s=float(clock))
        for i, (a, b) in enumerate(zip(differences, differences[1:])):
            contractions[i] += b < a; expansions[i] += b > a
        profile.append(dict(step=step, time_s=float(clock), maximum_restricted_temperature_differences_K=list(map(_display, differences))))
    ratios = [a / b if b else None for a, b in zip(maxima, maxima[1:])]
    return dict(valid=True, scope='independently_audited_uniform_1d_conservative_spatial_refinement',
        cells=[len(c['initial']) for c in contracts], steps=steps, dt_s=contracts[0]['dt_s'],
        length_m=float(length_m), area_m2=float(area_m2), common_base_cells=cells, common_time_samples=steps,
        maximum_restricted_temperature_differences_K=list(map(_display, maxima)), maximum_difference_locations=peaks,
        final_restricted_temperature_differences_K=list(map(_display, differences)),
        final_restricted_temperatures_K=[list(map(_display, s[-1][1])) for s in samples],
        equal_grid_max_norm_ratios=[_display(r) if r is not None else None for r in ratios],
        observed_orders=[_observed_order(r) for r in ratios], pointwise_contractions=contractions,
        pointwise_expansions=expansions, common_time_profile=profile, independent_trajectory_audits=audits,
        retained_scalar_temperature_samples=cells * steps * 3 * len(contracts),
        initial_extensive_restriction_matched=True, exact_geometric_volumes_matched=True,
        common_carrier_and_lattice_section_matched=True, exact_source_density_matched=True,
        full_interval_proofs_recomputed=True, all_actual_prefix_energy_closed=True,
        spatial_convergence_qualified=False, temporal_convergence_qualified=False,
        discretization_error_bound_established=False, exact_recurrence_preserved=False,
        physical_validated=False, new_commercial_full_profile_accepted=False,
        general_complex_physics_closed=False, complete_device_energy=False)
