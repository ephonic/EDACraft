from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from tcad.postprocess.boltzmann_owned_trajectory import (
    audit_mb_owned_trajectory as audit, audit_mb_trajectory_journal as journal,
)
from tcad.postprocess.boltzmann_rounded_trajectory import canonical_bytes, record_digest


@pytest.fixture(scope='module')
def evidence():
    path = Path(__file__).resolve().parents[1] / 'docs/validation/mb_temporal_refinement_20261024/journal_mixed_128_prefix.jsonl.gz'
    with gzip.open(path, 'rb') as stream:
        contract = json.loads(next(stream))['contract']
        rows = [json.loads(next(stream)) for _ in range(3)]
    # A declared prefix needs its own outer hash chain. Physical proofs are kept.
    contract['steps'] = 3
    previous = record_digest(contract)
    for row in rows:
        row['previous_sha256'] = previous
        row['sha256'] = record_digest({k: v for k, v in row.items() if k != 'sha256'})
        previous = row['sha256']
    return contract, rows


def encoded(contract, rows):
    yield canonical_bytes(dict(contract=contract, contract_sha256=record_digest(contract))) + b'\n'
    for row in rows:
        yield canonical_bytes(row) + b'\n'


def test_owned_and_native_journal_interfaces_have_identical_audits(evidence):
    c, rows = evidence
    result = audit(c, iter(rows), checkpoint_stride=1)
    assert result == journal(encoded(c, rows), checkpoint_stride=1)
    assert result['valid'] and result['accepted_steps'] == 3
    assert not result['physical_validated'] and not result['complete_device_energy']


def test_iterator_cannot_shorten_declared_trajectory(evidence):
    c, rows = deepcopy(evidence)
    def truncate():
        c['steps'] = 1
        yield rows[0]
    with pytest.raises(ValueError, match='missing records'):
        audit(c, truncate())


@pytest.mark.parametrize('damage', ['steps', 'initial_time', 'source', 'configuration', 'thermal'])
def test_contract_is_owned_before_iterator_callbacks(evidence, damage):
    c, rows = deepcopy(evidence)
    expected = audit(c, rows)
    def mutate():
        if damage == 'steps': c['steps'] = 1
        elif damage == 'initial_time': c['initial'][0]['time_s'] = 1.
        elif damage == 'source': c['impulses_J'][0][0] *= 2
        elif damage == 'configuration': c['configurations'][0]['parameters'][6] = '0.5'
        else: c['thermal_faces'][0]['geometry'][0] *= 2
        yield from rows
    assert audit(c, mutate()) == expected


@pytest.mark.parametrize('damage', ['time', 'endpoint', 'hash', 'report', 'clear'])
def test_previous_and_terminal_rows_are_private(evidence, damage):
    c, rows = deepcopy(evidence)
    expected = audit(c, rows, checkpoint_stride=1)
    def mutate():
        for row in rows:
            yield row
            if damage == 'time': row['new'][0]['time_s'] = 1.
            elif damage == 'endpoint': row['new'][0]['endpoint'] = c['initial'][0]['endpoint']
            elif damage == 'hash': row['sha256'] = '0' * 64
            elif damage == 'report': row['report'].clear()
            else: row.clear()
    assert audit(c, mutate(), checkpoint_stride=1) == expected


def test_controls_rejected_before_records_iter_is_called(evidence):
    c, rows = deepcopy(evidence); c['physical_validated'] = True
    class Forbidden:
        def __iter__(self): raise AssertionError('iterator consumed')
    with pytest.raises(ValueError): audit(c, Forbidden())


def test_single_pass_journal(evidence):
    c, rows = evidence
    class Once:
        def __init__(self): self.called = False
        def __iter__(self):
            assert not self.called; self.called = True
            yield from encoded(c, rows)
    assert journal(Once())['accepted_steps'] == 3


@pytest.mark.parametrize('damage', ['missing', 'extra', 'hash', 'endpoint'])
def test_bad_evidence_is_not_repaired_by_snapshotting(evidence, damage):
    c, rows = deepcopy(evidence)
    if damage == 'missing': rows.pop()
    elif damage == 'extra': rows.append(deepcopy(rows[-1]))
    elif damage == 'hash': rows[0]['sha256'] = '0' * 64
    else:
        rows[0]['new'][0]['endpoint'] = c['initial'][0]['endpoint']
        previous = record_digest(c)
        for row in rows:
            row['previous_sha256'] = previous
            row['sha256'] = record_digest({k: v for k, v in row.items() if k != 'sha256'})
            previous = row['sha256']
    with pytest.raises(ValueError): journal(encoded(c, rows))


@pytest.mark.parametrize('line', [b'', b'{', b'\xff', b'[]', b'null', b'{}', b'{"contract":{},"contract":{}}', b'{"x":NaN}'])
def test_invalid_header_bytes_are_rejected(line):
    with pytest.raises(ValueError): journal([line])


@pytest.mark.parametrize('damage', ['hash', 'extra', 'duplicate', 'nested_duplicate', 'text', 'mutable_bytes', 'oversize', 'blank_row'])
def test_journal_framing_and_member_ambiguities_fail(evidence, damage):
    c, rows = evidence; lines = list(encoded(c, rows))
    if damage == 'hash': lines[0] = canonical_bytes(dict(contract=c, contract_sha256='0' * 64))
    elif damage == 'extra': lines[0] = canonical_bytes(dict(contract=c, contract_sha256=record_digest(c), extra=0))
    elif damage == 'duplicate': lines[1] = b'{"index":0,' + lines[1][1:]
    elif damage == 'nested_duplicate': lines[1] = lines[1].replace(b'"index":0', b'"injected":{"x":0,"x":1},"index":0', 1)
    elif damage == 'text': lines[0] = lines[0].decode()
    elif damage == 'mutable_bytes': lines[1] = bytearray(lines[1])
    elif damage == 'oversize':
        with pytest.raises(ValueError, match='size exceeded'): journal(lines, max_line_bytes=len(lines[0]))
        return
    else: lines[1] = b'\n'
    with pytest.raises(ValueError): journal(lines)


@pytest.mark.parametrize('bound', [0, -1, True, 1.5, (64 << 20) + 1])
def test_line_limit_is_bounded_before_iterator_consumption(bound):
    class Forbidden:
        def __iter__(self): raise AssertionError('iterator consumed')
    with pytest.raises(ValueError): journal(Forbidden(), max_line_bytes=bound)


def test_empty_journal_is_rejected():
    with pytest.raises(ValueError, match='missing.*header'): journal(iter(()))
