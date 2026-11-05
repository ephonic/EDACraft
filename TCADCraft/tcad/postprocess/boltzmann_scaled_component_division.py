"""Independent exact replay of partition-preserving binary113 division.

The input atom partition is authoritative. Neither an energy tolerance nor
aggregate cancellation permits dropping a nonzero per-atom residual.
"""
from fractions import Fraction

from .boltzmann_product_range import _binary113
from .boltzmann_scaled_arithmetic import _count, _tokens, scaled_value_fraction


def audit_mb_scaled_component_division(atoms, divisor, wire):
    if not isinstance(atoms, (list, tuple)) or len(atoms) > 4096:
        raise ValueError('bounded numerator atom list required')
    inputs = []
    evidence = 0
    for atom in atoms:
        inputs.append(scaled_value_fraction(atom))
        if int(atom[2]) > 1:
            raise ValueError('one binary113 numerator atom required')
        evidence += int(atom[2])
    b = scaled_value_fraction(divisor)
    if not b:
        raise ValueError('scaled component division by zero')
    evidence += int(divisor[2])
    _tokens(wire, 70000)
    if len(wire) < 3 or tuple(wire[:2]) != ('mb_scaled_component_division_v1', '113'):
        raise ValueError('component division version/precision mismatch')
    if _count(wire[2], 4096) != len(inputs):
        raise ValueError('component division atom provenance mismatch')
    cursor = 3

    def take():
        nonlocal cursor, evidence
        if cursor >= len(wire):
            raise ValueError('missing component division value')
        size = _count(wire[cursor], 8195)
        raw = wire[cursor + 1:cursor + 1 + size]
        if len(raw) != size:
            raise ValueError('component division value coverage mismatch')
        result = scaled_value_fraction(raw)
        evidence += int(raw[2])
        if evidence > 4096:
            raise ValueError('original cumulative component evidence budget exceeded')
        cursor += size + 1
        return result

    q, residual = take(), take()
    terms, residuals = [], []
    for a in inputs:
        first, second, rest = take(), take(), take()
        expected_first = _binary113(a / b)
        expected_second = _binary113((a - b * expected_first) / b)
        if first != expected_first or second != expected_second:
            raise ValueError('component division rounding or partition mismatch')
        if a != b * (first + second) + rest:
            raise ValueError('component division exact residual mismatch')
        if abs(rest) > abs(a) / (1 << 226):
            raise ValueError('component division residual bound exceeded')
        terms.append(first + second)
        residuals.append(rest)
    if cursor != len(wire):
        raise ValueError('unexpected component division tokens')
    if q != sum(terms, Fraction()) or residual != sum(residuals, Fraction()):
        raise ValueError('component division exact aggregate mismatch')
    if sum(inputs, Fraction()) != b * q + residual:
        raise ValueError('component division aggregate identity mismatch')
    if abs(residual) > sum(map(abs, inputs), Fraction()) / (1 << 226):
        raise ValueError('component division absolute-input residual bound exceeded')
    return dict(scope='partition_preserving_scaled_component_division',
                atoms_audited=len(inputs), evidence_components=evidence,
                nonzero_atom_remainders=sum(bool(r) for r in residuals),
                aggregate_remainder_is_zero=residual == 0,
                aggregate_differs_from_sum_first_roundings=q != sum((_binary113(a / b) for a in inputs), Fraction()),
                exact_atom_identities=True, exact_aggregate_identity=True,
                original_atom_partition_preserved=True,
                remainder_bound_bits=226, state_committed=False,
                physical_time_advanced=False, full_collision_audited=False,
                physical_validated=False)
