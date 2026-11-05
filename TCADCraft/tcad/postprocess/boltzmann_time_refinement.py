"""Independently audit rounded trajectories before comparing common times.

Arithmetic closure and measured discretization differences are separate results.
Only common-grid temperatures are retained; complete proof rows are streamed.
"""
import json,math
from .boltzmann_rounded_trajectory import trajectory_contract,audit_mb_rounded_trajectory,canonical_bytes
from .boltzmann_recomputed_transport import point,scaled_value_fraction
from .boltzmann_scaled_split import _command,_display


def _observed_order(ratio):
    if ratio is None or ratio<=0:return None
    return math.log2(ratio.numerator)-math.log2(ratio.denominator)


def audit_mb_time_refinement(contracts,record_streams):
    """Audit 3..5 factor-two levels and measure differences on one common grid.

    All levels must share initial state, material, geometry, controls, duration,
    budgets and exactly equal source power. This is an observed comparison, not
    a proof of temporal order, a truncation-error bound or physical validation.
    At most 65536 common-grid scalar temperatures are retained.
    """
    contracts=tuple(contracts);record_streams=tuple(record_streams)
    if not 3<=len(contracts)<=5 or len(record_streams)!=len(contracts):
        raise ValueError('three to five complete time levels required')
    if any(type(c) is not dict for c in contracts):raise ValueError('explicit time refinement contract required')
    # Detach controls before consuming arbitrary caller-owned iterators.
    contracts=tuple(json.loads(canonical_bytes(c)) for c in contracts)
    for c in contracts:
        if type(c) is not dict:raise ValueError('explicit time refinement contract required')
        try:
            expected=trajectory_contract(c['configurations'],c['initial'],c['faces'],c['thermal_faces'],c['dt_s'],c['steps'],
                impulses_J=c['impulses_J'],particle_atol=c['particle_atol'],energy_atol_J=c['energy_atol_J'])
        except (KeyError,TypeError) as exc:raise ValueError('time refinement contract coverage') from exc
        if c!=expected:raise ValueError('time refinement contract metadata mismatch')
    base=contracts[0];n=len(base['initial']);count=base['steps']
    if count*n*3*len(contracts)>65536:raise ValueError('common-grid temperature sample budget exceeded')
    fixed=set(base)-{'steps','dt_s','impulses_J'}
    for level,c in enumerate(contracts):
        factor=1<<level
        if c['steps']!=count*factor or _command(c['dt_s'])*factor!=_command(base['dt_s']):
            raise ValueError('factor-two steps and identical exact duration required')
        if any(c[k]!=base[k] for k in fixed):raise ValueError('time refinement controls/initial/budgets differ')
        if any(_command(x)*factor!=_command(y) for q,r in zip(c['impulses_J'],base['impulses_J']) for x,y in zip(q,r)):
            raise ValueError('identical exact source power required')
    samples=[];audits=[]
    for level,(c,stream) in enumerate(zip(contracts,record_streams)):
        factor=1<<level;level_samples=[]
        def checked_records():
            for index,row in enumerate(stream):
                row=json.loads(canonical_bytes(row))
                # Resume only after the independent full interval/prefix audit
                # has accepted this row. No claimed saved audit is consulted.
                yield row
                if (index+1)%factor==0:
                    states=row['new'];values=tuple(t for s in states for t in point(s['endpoint'])['temperatures'])
                    clock=scaled_value_fraction(states[0]['physical_clock'])
                    level_samples.append((clock,values))
        check=audit_mb_rounded_trajectory(c,checked_records(),checkpoint_stride=16)
        if len(level_samples)!=count:raise ValueError('common-time sample coverage')
        audits.append(check);samples.append(level_samples)
    maxima=[0]*(len(contracts)-1);peaks=[None]*len(maxima);profile=[];final=None
    contractions=[0]*(len(maxima)-1);expansions=[0]*len(contractions)
    for step,rows in enumerate(zip(*samples),1):
        clock=rows[0][0]
        if any(r[0]!=clock for r in rows):raise ValueError('exact common physical clock mismatch')
        differences=[max(abs(x-y) for x,y in zip(a[1],b[1])) for a,b in zip(rows,rows[1:])]
        for i,d in enumerate(differences):
            if d>maxima[i]:maxima[i]=d;peaks[i]=dict(common_step=step,time_s=float(clock))
        for i,(a,b) in enumerate(zip(differences,differences[1:])):
            contractions[i]+=b<a;expansions[i]+=b>a
        profile.append(dict(common_step=step,time_s=float(clock),maximum_temperature_differences_K=list(map(_display,differences))))
        final=differences
    ratios=[a/b if b else None for a,b in zip(maxima,maxima[1:])]
    orders=[_observed_order(r) for r in ratios]
    return dict(valid=True,scope='independently_audited_common_time_refinement',levels=len(contracts),
        steps=[c['steps'] for c in contracts],dt_s=[c['dt_s'] for c in contracts],common_time_samples=count,
        start_time_s=audits[0]['start_time_s'],end_time_s=audits[0]['end_time_s'],
        maximum_temperature_differences_K=list(map(_display,maxima)),maximum_difference_locations=peaks,
        final_temperature_differences_K=list(map(_display,final)),
        equal_grid_max_norm_ratios=[_display(r) if r is not None else None for r in ratios],observed_orders=orders,
        pointwise_contractions=contractions,pointwise_expansions=expansions,common_time_profile=profile,
        independent_trajectory_audits=audits,all_actual_prefix_energy_closed=True,
        cumulative_error_allowance_enforced=True,full_interval_proofs_recomputed=True,
        exact_source_power_matched=True,exact_common_clocks_matched=True,retained_scalar_temperature_samples=count*n*3*len(contracts),
        temporal_order_qualified=False,discretization_error_bound_established=False,spatial_convergence_qualified=False,
        new_commercial_full_profile_accepted=False,exact_recurrence_preserved=False,
        general_complex_physics_closed=False,complete_device_energy=False,physical_validated=False)
