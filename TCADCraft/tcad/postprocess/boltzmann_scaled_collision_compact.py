"""Replay residual checkpoints with the complete independent operation graph."""
from .boltzmann_scaled_arithmetic import _tokens, _count, scaled_value_fraction
from .boltzmann_scaled_collision_trace import _expected, _wire


def _kind(label):
    if label.startswith('aggregate.'):
        return 'aggregate_value'
    if label in ('qold','capacity0','capacity1','source0','source1','source2'):
        return 'division_remainder'
    if label.startswith('lineage') and label.split('.')[1] in ('1','3','5','13'):
        return 'division_remainder'
    return None


def audit_mb_scaled_collision_compact(endpoint,command,wire):
    _tokens(wire,20000)
    if len(wire)<9 or tuple(wire[:2]) != ('mb_scaled_collision_compact_v1','113'):
        raise ValueError('compact collision version/precision mismatch')
    status=wire[2]
    if status not in ('complete','evidence_budget_exceeded'):
        raise ValueError('compact collision status invalid')
    records=_count(wire[3],128);stored=_count(wire[4],29)
    declared=_count(wire[5],4096);expanded_count=_count(wire[6],99999)
    requested=_count(wire[8],8192)
    expected=_expected(endpoint,command)
    cursor=9;payload=expanded=checkpoints=divisions=nonzero=lineages=0
    for _ in range(records):
        try: label,q,r=next(expected)
        except StopIteration as exc: raise ValueError('unexpected compact operation count') from exc
        expanded+=int(_wire(q)[2])+int(_wire(r)[2])
        lineages+=label.startswith('lineage') and label.endswith('.19')
        kind=_kind(label)
        if kind is None:
            continue
        value=q if kind=='aggregate_value' else r
        if cursor+3>len(wire) or list(wire[cursor:cursor+2]) != [label,kind]:
            raise ValueError('compact checkpoint provenance or coverage mismatch')
        size=_count(wire[cursor+2],8195)
        raw=list(wire[cursor+3:cursor+3+size]);cursor+=3+size
        if len(raw)!=size or raw != _wire(value):
            raise ValueError('compact exact remainder or aggregate mismatch')
        scaled_value_fraction(raw)
        payload+=int(raw[2]);checkpoints+=1
        divisions+=kind=='division_remainder'
        nonzero+=kind=='division_remainder' and bool(value)
        if payload>4096:
            raise ValueError('compact cumulative saved evidence budget exceeded')
    if cursor!=len(wire) or payload!=declared or expanded!=expanded_count or checkpoints!=stored:
        raise ValueError('compact checkpoint counts or evidence coverage mismatch')
    if status=='complete':
        if wire[7]!='-' or requested:
            raise ValueError('complete compact collision has false blocker')
        try: next(expected)
        except StopIteration as done: details=done.value
        else: raise ValueError('compact collision falsely claims completion')
    else:
        try: label,q,r=next(expected)
        except StopIteration as exc: raise ValueError('false compact budget exhaustion') from exc
        kind=_kind(label)
        if kind is None:
            raise ValueError('compact budget blocker is not a stored checkpoint')
        cost=int(_wire(q if kind=='aggregate_value' else r)[2])
        if wire[7]!=label or requested!=payload+cost or requested<=4096:
            raise ValueError('compact budget blocker or requested evidence mismatch')
        details={}
    return dict(scope='scaled_fixed_tau_collision_residual_checkpoints',status=status,
                arithmetic_records_independently_recomputed=records,saved_checkpoints=checkpoints,
                evidence_components=payload,saved_evidence_budget=4096,
                expanded_trace_components=expanded,expanded_trace_fits_legacy_budget=expanded<=4096,
                division_remainder_checkpoints=divisions,nonzero_division_remainders=nonzero,
                completed_lineages=lineages,first_blocked_operation=wire[7],requested_components=requested,
                all_division_remainders_retained=status=='complete',
                full_fixed_tau_trace_audited=status=='complete',
                full_fixed_tau_energy_gate_passed=details.get('energy_gate_passed',False),
                full_final_temperature_bounds_passed=details.get('final_temperature_bounds_passed',False),
                state_committed=False,physical_time_advanced=False,nonlinear_root_audited=False,
                physical_validated=False)
