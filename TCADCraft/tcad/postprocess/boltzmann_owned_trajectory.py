"""Snapshot caller-owned evidence before independent trajectory verification.

The sealed v1 arithmetic audit remains the numerical authority. These entry
points give it private controls and a private current row, so iterator callbacks
cannot change previously checked evidence or shorten the declared trajectory.
"""
import json
from .boltzmann_rounded_trajectory import (
    audit_mb_rounded_trajectory, canonical_bytes, record_digest,
)


def audit_mb_owned_trajectory(contract, records, *, checkpoint_stride=64):
    """Audit detached controls/rows; return the unchanged v1 audit schema.

    Controls are copied before invoking the iterator. Each yielded row is copied
    before validation and remains private after the iterator resumes. Full proof
    rows are streamed, while checkpoint metadata grows as steps/stride. This
    protects against synchronous iterator callbacks, not concurrent writes while
    a snapshot is being constructed.
    """
    if type(contract) is not dict:
        raise ValueError('explicit trajectory contract required')
    owned = json.loads(canonical_bytes(contract))

    def detached():
        for row in records:
            if type(row) is not dict:
                raise ValueError('explicit trajectory record required')
            yield json.loads(canonical_bytes(row))

    return audit_mb_rounded_trajectory(owned, detached(), checkpoint_stride=checkpoint_stride)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member in trajectory journal')
        result[key] = value
    return result


def audit_mb_trajectory_journal(lines, *, checkpoint_stride=64, max_line_bytes=16 << 20):
    """Audit immutable JSONL byte lines, including the exact native header.

    UTF-8, unique JSON object members and finite JSON values are required. The
    configurable per-line bound is at most 64 MiB. Readers should also bound
    their own readline allocation; this function bounds parsing of supplied
    lines. Empty, truncated and extra-record journals fail without a result.
    """
    if type(max_line_bytes) is not int or not 1 <= max_line_bytes <= 64 << 20:
        raise ValueError('bounded integer journal line size required')

    def decoded():
        for line in lines:
            if type(line) is not bytes:
                raise ValueError('immutable journal byte lines required')
            if len(line) > max_line_bytes:
                raise ValueError('trajectory journal line size exceeded')
            try:
                row = json.loads(line.decode('utf-8'), object_pairs_hook=_unique_object)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError('invalid UTF-8 JSON trajectory journal') from exc
            canonical_bytes(row)  # Reject non-finite JSON constants too.
            yield row

    records = iter(decoded())
    try:
        header = next(records)
    except StopIteration as exc:
        raise ValueError('missing trajectory journal header') from exc
    if type(header) is not dict or set(header) != {'contract', 'contract_sha256'}:
        raise ValueError('trajectory journal header coverage')
    if type(header['contract']) is not dict or header['contract_sha256'] != record_digest(header['contract']):
        raise ValueError('trajectory journal contract hash mismatch')
    return audit_mb_owned_trajectory(header['contract'], records, checkpoint_stride=checkpoint_stride)
