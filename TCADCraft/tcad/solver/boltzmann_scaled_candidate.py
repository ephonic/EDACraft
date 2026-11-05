"""Immutable saved collision candidate; production state submission is separate."""
from dataclasses import dataclass
from tcad.postprocess.boltzmann_scaled_powerlaw import (
    audit_mb_scaled_powerlaw,split_mb_scaled_powerlaw,scaled_powerlaw_aggregates,
)


@dataclass(frozen=True)
class MBScaledCollisionCandidate:
    source_endpoint: tuple
    command: tuple
    source_clock: tuple
    lattice_increment: tuple
    electron_energy_increment: tuple
    hole_energy_increment: tuple
    start_clock: tuple
    end_clock: tuple
    root_packet: tuple

    def __post_init__(self):
        for key in self.__dataclass_fields__:
            raw=tuple(getattr(self,key))
            if any(type(token) is not str for token in raw):
                raise ValueError('immutable string candidate fields required')
            object.__setattr__(self,key,raw)


def audit_mb_scaled_candidate(state):
    if type(state) is not MBScaledCollisionCandidate:
        raise ValueError('saved scaled collision candidate required')
    parts=split_mb_scaled_powerlaw(state.root_packet)
    values=scaled_powerlaw_aggregates(parts['proof'])
    if [list(state.lattice_increment),list(state.electron_energy_increment),list(state.hole_energy_increment)] != [values[k] for k in ('aggregate.L','aggregate.un','aggregate.up')]:
        raise ValueError('scaled candidate increment/proof mismatch')
    if list(state.start_clock)!=parts['start'] or list(state.end_clock)!=parts['end']:
        raise ValueError('scaled candidate clock/proof mismatch')
    return audit_mb_scaled_powerlaw(list(state.source_endpoint),list(state.command),list(state.source_clock),list(state.root_packet))


def scaled_candidate_from_saved(endpoint,command,clock,wire):
    """Build only after independent actual-state audit; no producer is called."""
    report=audit_mb_scaled_powerlaw(endpoint,command,clock,wire)
    parts=split_mb_scaled_powerlaw(wire);values=scaled_powerlaw_aggregates(parts['proof'])
    state=MBScaledCollisionCandidate(tuple(endpoint),tuple(command),tuple(clock),
        *(tuple(values[k]) for k in ('aggregate.L','aggregate.un','aggregate.up')),
        tuple(parts['start']),tuple(parts['end']),tuple(wire))
    return state,report
