"""Single-pass joint space/time differences for the uniform 1D MB control.

Native-cell temperatures and conservative base-grid restrictions are retained
at the same coarsest time samples. Each complete trajectory is audited once.
Observed refinement differences are not truncation-error estimates or bounds.
"""
import json
from fractions import Fraction
from .boltzmann_rounded_trajectory import canonical_bytes
from .boltzmann_owned_trajectory import audit_mb_owned_trajectory
from .boltzmann_spatial_refinement import _validated_contracts, _restricted_temperatures
from .boltzmann_recomputed_transport import point, scaled_value_fraction
from .boltzmann_scaled_split import _command, _display
from .boltzmann_time_refinement import _observed_order


def _validated_grid(contract_grid, length_m, area_m2):
    if type(contract_grid) not in (list, tuple) or not 3 <= len(contract_grid) <= 5:
        raise ValueError('three to five explicit spatial rows required')
    if any(type(row) not in (list, tuple) or not 3 <= len(row) <= 5 for row in contract_grid):
        raise ValueError('three to five explicit time levels per row required')
    times = len(contract_grid[0])
    if any(len(row) != times or any(type(c) is not dict for c in row) for row in contract_grid):
        raise ValueError('rectangular explicit contract grid required')
    # Own all controls before touching even the containers of record streams.
    grid = json.loads(canonical_bytes(contract_grid))
    for t in range(times):
        _validated_contracts([row[t] for row in grid], length_m, area_m2)
    for row in grid:
        base = row[0]; fixed = set(base) - {'steps', 'dt_s', 'impulses_J'}
        for t, c in enumerate(row):
            factor = 1 << t
            if c['steps'] != base['steps'] * factor or _command(c['dt_s']) * factor != _command(base['dt_s']):
                raise ValueError('factor-two time levels with identical exact duration required')
            if any(c[k] != base[k] for k in fixed):
                raise ValueError('fixed spatial-row controls or initial states differ')
            if any(_command(q[k]) * factor != _command(r[k])
                   for q, r in zip(c['impulses_J'], base['impulses_J']) for k in range(3)):
                raise ValueError('identical exact source power at every time level required')
    cells = [len(row[0]['initial']) for row in grid]; steps = grid[0][0]['steps']
    retained = steps * 3 * times * (sum(cells) + len(cells) * cells[0])
    if retained > 65536:
        raise ValueError('joint native/restricted temperature sample budget exceeded')
    return grid, retained


def _comparison(levels, component):
    maxima = [Fraction()] * (len(levels) - 1); peaks = [None] * len(maxima)
    contractions = [0] * (len(maxima) - 1); expansions = contractions.copy(); profile = []
    for step, rows in enumerate(zip(*levels), 1):
        clock = rows[0][0]
        if any(r[0] != clock for r in rows):
            raise ValueError('joint comparison exact common clock mismatch')
        differences = [max(abs(x - y) for x, y in zip(a[component], b[component]))
                       for a, b in zip(rows, rows[1:])]
        for i, delta in enumerate(differences):
            if delta > maxima[i]:
                maxima[i] = delta; peaks[i] = dict(common_step=step, time_s=float(clock))
        for i, (a, b) in enumerate(zip(differences, differences[1:])):
            contractions[i] += b < a; expansions[i] += b > a
        profile.append(dict(common_step=step, time_s=float(clock), maximum_temperature_differences_K=list(map(_display, differences))))
    ratios = [a / b if b else None for a, b in zip(maxima, maxima[1:])]
    return dict(maximum_temperature_differences_K=list(map(_display, maxima)), maximum_difference_locations=peaks,
        final_temperature_differences_K=list(map(_display, differences)),
        equal_grid_max_norm_ratios=[_display(r) if r is not None else None for r in ratios],
        observed_orders=[_observed_order(r) for r in ratios], pointwise_contractions=contractions,
        pointwise_expansions=expansions, common_time_profile=profile)


def _interactions(samples):
    result = []
    for s in range(len(samples) - 1):
        for t in range(len(samples[0]) - 1):
            norm_change = mixed = temporal_sum = Fraction()
            for a, b, c, d in zip(samples[s][t], samples[s + 1][t], samples[s][t + 1], samples[s + 1][t + 1]):
                if not a[0] == b[0] == c[0] == d[0]:
                    raise ValueError('space/time interaction clock mismatch')
                coarse = tuple(x - y for x, y in zip(a[2], b[2]))
                fine = tuple(x - y for x, y in zip(c[2], d[2]))
                change = abs(max(map(abs, coarse)) - max(map(abs, fine)))
                cross = max(abs(x - y) for x, y in zip(coarse, fine))
                observed = max(abs(x - y) for x, y in zip(a[2], c[2])) + max(abs(x - y) for x, y in zip(b[2], d[2]))
                if not change <= cross <= observed:
                    raise ValueError('exact observed refinement triangle inequality failed')
                norm_change = max(norm_change, change); mixed = max(mixed, cross); temporal_sum = max(temporal_sum, observed)
            result.append(dict(spatial_pair=[s, s + 1], time_pair=[t, t + 1],
                maximum_spatial_norm_change_K=_display(norm_change), maximum_mixed_difference_K=_display(mixed),
                maximum_observed_temporal_sum_K=_display(temporal_sum), triangle_inequalities_checked=True,
                truncation_error_bound_established=False))
    return result


def audit_mb_uniform_space_time_refinement(contract_grid, record_grid, *, length_m, area_m2):
    """Audit a 3..5 by 3..5 grid once, then compare all common physical times.

    Rows refine space; columns halve dt and double steps at equal exact duration.
    Input grids are explicit list/tuple containers; each record stream is single
    pass. The scope is the homogeneous uniform chain of the spatial-only API.
    Native and restricted scalar temperature samples jointly total at most 65536.
    """
    grid, retained = _validated_grid(contract_grid, length_m, area_m2)
    if type(record_grid) not in (list, tuple) or len(record_grid) != len(grid) or any(
        type(row) not in (list, tuple) or len(row) != len(grid[0]) for row in record_grid
    ):
        raise ValueError('one explicit rectangular record stream grid required')
    cells = [len(row[0]['initial']) for row in grid]; steps = grid[0][0]['steps']; times = len(grid[0])
    samples = []; audits = []
    for row, streams in zip(grid, record_grid):
        spatial_samples = []; spatial_audits = []
        for t, (contract, stream) in enumerate(zip(row, streams)):
            factor = 1 << t; selected = []
            def records():
                for index, raw in enumerate(stream):
                    raw = json.loads(canonical_bytes(raw))
                    yield raw
                    if (index + 1) % factor == 0:
                        states = raw['new']; clock = scaled_value_fraction(states[0]['physical_clock'])
                        native = tuple(value for state in states for value in point(state['endpoint'])['temperatures'])
                        restricted = _restricted_temperatures(states, cells[0])
                        selected.append((clock, native, restricted))
            spatial_audits.append(audit_mb_owned_trajectory(contract, records(), checkpoint_stride=16))
            if len(selected) != steps:
                raise ValueError('joint common-time sample coverage mismatch')
            spatial_samples.append(selected)
        samples.append(spatial_samples); audits.append(spatial_audits)
    temporal = [dict(cells=count, native_cell_comparison=_comparison(row, 1),
                     conservative_restricted_comparison=_comparison(row, 2)) for count, row in zip(cells, samples)]
    spatial = [dict(dt_s=grid[0][t]['dt_s'], steps=grid[0][t]['steps'],
                    conservative_restricted_comparison=_comparison([row[t] for row in samples], 2)) for t in range(times)]
    return dict(valid=True, scope='independently_audited_uniform_1d_joint_space_time_refinement',
        cells=cells, steps=[c['steps'] for c in grid[0]], dt_s=[c['dt_s'] for c in grid[0]],
        start_time_s=audits[0][0]['start_time_s'], end_time_s=audits[0][0]['end_time_s'],
        length_m=float(length_m), area_m2=float(area_m2), common_time_samples=steps,
        retained_scalar_temperature_samples=retained, trajectories_audited_once=len(grid) * times,
        audited_intervals=sum(a['accepted_steps'] for row in audits for a in row), independent_trajectory_audits=audits,
        temporal_comparisons=temporal, spatial_comparisons=spatial, observed_interactions=_interactions(samples),
        native_cell_temperatures_compared=True, conservative_restriction=True, all_actual_prefix_energy_closed=True,
        exact_source_power_matched=True, exact_common_clocks_matched=True, full_interval_proofs_recomputed=True,
        spatial_convergence_qualified=False, temporal_convergence_qualified=False, temporal_error_bound_established=False,
        discretization_error_bound_established=False, exact_recurrence_preserved=False, physical_validated=False,
        new_commercial_full_profile_accepted=False, general_complex_physics_closed=False, complete_device_energy=False)
