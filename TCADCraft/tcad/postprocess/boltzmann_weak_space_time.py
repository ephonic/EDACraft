"""Joint numerical comparison of legacy and weak nonconstant MB trajectories."""
import json
from .boltzmann_rounded_trajectory import canonical_bytes
from .boltzmann_owned_trajectory import audit_mb_owned_trajectory
from .boltzmann_weak_trajectory import SCOPE, weak_trajectory_contract, audit_mb_weak_trajectory
from .boltzmann_space_time_refinement import _validated_grid as _legacy_grid, _comparison, _interactions
from .boltzmann_spatial_refinement import _restricted_temperatures
from .boltzmann_recomputed_transport import point, scaled_value_fraction
from .boltzmann_product_range import _vector

LEGACY_SCOPE='accounted_rounded_trajectory_v1'

def _validated_grid(contract_grid, length_m, area_m2):
    if type(contract_grid) not in (list,tuple) or any(type(row) not in (list,tuple) for row in contract_grid):
        raise ValueError('explicit weak space/time grid required')
    owned=json.loads(canonical_bytes(contract_grid))
    normalized=json.loads(canonical_bytes(owned));scopes=set()
    for row,normal in zip(owned,normalized):
        for c,n in zip(row,normal):
            if type(c) is not dict or c.get('scope') not in (SCOPE,LEGACY_SCOPE):
                raise ValueError('supported explicit trajectory version required')
            scopes.add(c['scope'])
            if c['scope']==SCOPE:
                try:
                    expected=weak_trajectory_contract(c['configurations'],c['initial'],c['faces'],c['thermal_faces'],c['dt_s'],c['steps'],impulses_J=c['impulses_J'],particle_atol=c['particle_atol'],energy_atol_J=c['energy_atol_J'])
                except (KeyError,TypeError) as exc:
                    raise ValueError('weak trajectory contract coverage') from exc
                if c!=expected:raise ValueError('weak trajectory contract metadata mismatch')
                n['scope']=LEGACY_SCOPE
    normal,retained=_legacy_grid(normalized,length_m,area_m2)
    if len(scopes)>1:
        for row in owned:
            for c in row:
                for cfg in c['configurations']:
                    p=_vector(cfg['parameters'])
                    if not (p[6] or p[7]) or not (p[10] or p[11]):
                        raise ValueError('mixed-version comparison requires nonconstant laws for both carriers')
    return owned,retained

def _audit_versioned(contract, records, *, checkpoint_stride):
    audit=audit_mb_weak_trajectory if contract['scope']==SCOPE else audit_mb_owned_trajectory
    return audit(contract,records,checkpoint_stride=checkpoint_stride)

def audit_mb_weak_space_time_refinement(contract_grid, record_grid, *, length_m, area_m2):
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
            spatial_audits.append(_audit_versioned(contract, records(), checkpoint_stride=16))
            if len(selected) != steps:
                raise ValueError('joint common-time sample coverage mismatch')
            spatial_samples.append(selected)
        samples.append(spatial_samples); audits.append(spatial_audits)
    temporal = [dict(cells=count, native_cell_comparison=_comparison(row, 1),
                     conservative_restricted_comparison=_comparison(row, 2)) for count, row in zip(cells, samples)]
    spatial = [dict(dt_s=grid[0][t]['dt_s'], steps=grid[0][t]['steps'],
                    conservative_restricted_comparison=_comparison([row[t] for row in samples], 2)) for t in range(times)]
    return dict(valid=True, scope='independently_audited_weak_uniform_1d_joint_space_time_refinement',
        cells=cells, steps=[c['steps'] for c in grid[0]], dt_s=[c['dt_s'] for c in grid[0]],
        start_time_s=audits[0][0]['start_time_s'], end_time_s=audits[0][0]['end_time_s'],
        length_m=float(length_m), area_m2=float(area_m2), common_time_samples=steps,
        retained_scalar_temperature_samples=retained, trajectories_audited_once=len(grid) * times,
        weak_trajectories=sum(c['scope']==SCOPE for row in grid for c in row),
        legacy_trajectories=sum(c['scope']==LEGACY_SCOPE for row in grid for c in row),
        audited_intervals=sum(a['accepted_steps'] for row in audits for a in row), independent_trajectory_audits=audits,
        temporal_comparisons=temporal, spatial_comparisons=spatial, observed_interactions=_interactions(samples),
        native_cell_temperatures_compared=True, conservative_restriction=True, all_actual_prefix_energy_closed=True,
        exact_source_power_matched=True, exact_common_clocks_matched=True, full_interval_proofs_recomputed=True,
        spatial_convergence_qualified=False, temporal_convergence_qualified=False, temporal_error_bound_established=False,
        discretization_error_bound_established=False, exact_recurrence_preserved=False, physical_validated=False,
        new_commercial_full_profile_accepted=False, general_complex_physics_closed=False, complete_device_energy=False)

