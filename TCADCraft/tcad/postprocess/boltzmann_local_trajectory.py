"""Independent per-cell and global prefix closure on a fixed MB face graph.

This opt-in audit accepts the existing weak trajectory protocol. It adds local
initial-to-current balances, so internal faces remain in each cell's ledger
until the separately checked global sum cancels them. Fixed flat bands, constant
cell heat capacities, and all existing native range restrictions still apply.
"""
from decimal import Decimal
from fractions import Fraction
import json

from .boltzmann_weak_trajectory import weak_trajectory_contract, _ledger
from .boltzmann_weak_interval import audit_mb_weak_rounded_split
from .boltzmann_rounded_trajectory import canonical_bytes, record_digest, maintained_faces, _inventory
from .boltzmann_recomputed_transport import moment_wire, _values
from .boltzmann_recomputed_lattice_transport import face_values
from .boltzmann_weak_endpoint_collision import exchange_budget
from .boltzmann_scaled_split import _command, _display
from .boltzmann_product_range import _binary113
from .boltzmann_scaled_collision_trace import _multiply

ROWS = ['electron_particles', 'hole_particles', 'electron_energy',
        'hole_energy', 'lattice_energy', 'total_energy']
_DISPLAY_ENVELOPE = Fraction(1000000000002, 1000000000000)


def _sum(rows):
    return [sum(column, Fraction()) for column in zip(*rows)]


def _local_ledger(contract, report):
    """Outward transfers plus internal exchanges minus prescribed sources."""
    rows = [[Fraction()] * 6 for _ in contract['initial']]
    child = report['conducting']; base = child['carrier_split']
    dt = _binary113(_command(contract['dt_s']))
    for spec, proof in zip(contract['faces'], base['transport']['transfers']):
        values, _, _ = _values(moment_wire(proof['raw']), 'mb_scaled_moments_v1', 4)
        nn, np, un, up = [_multiply(x, dt) for x in values]
        transfer = [nn, np, un, up, Fraction(), un + up]
        i = spec['owner']; rows[i] = [a + b for a, b in zip(rows[i], transfer)]
        if 'neighbor' in spec:
            j = spec['neighbor']; rows[j] = [a - b for a, b in zip(rows[j], transfer)]
    for spec, proof in zip(contract['thermal_faces'], child['lattice']['faces']):
        _, values, _ = face_values(proof); heat = _multiply(values[4], dt)
        for k in (4, 5):
            rows[spec['owner']][k] += heat
            if 'neighbor' in spec: rows[spec['neighbor']][k] -= heat
    for i, (mid, collision, q) in enumerate(zip(base['transported_states'], base['collisions'], contract['impulses_J'])):
        exchange, _ = exchange_budget(mid['endpoint'], collision['command'], collision['root_packet'])
        q = list(map(_command, q))
        rows[i][2] += exchange[0] - q[0]; rows[i][3] += exchange[1] - q[1]
        rows[i][4] -= sum(exchange) + q[2]; rows[i][5] -= sum(q)
    if _sum(rows) != _ledger(contract, report):
        raise ValueError('local/global ledger ownership mismatch')
    return rows


def _upper(values):
    return [Fraction(Decimal(x)) * _DISPLAY_ENVELOPE for x in values]


def _prefix(actual, initial, ledger, budgets, limits, name):
    if any(b > cap for b, cap in zip(budgets, limits)):
        raise ValueError(name + ' cumulative error allowance exhausted')
    residual = [a - b + c for a, b, c in zip(actual, initial, ledger)]
    if any(abs(r) > b for r, b in zip(residual, budgets)):
        raise ValueError(name + ' actual prefix particle/energy gate failed')
    utilization = max((abs(r) / b if b else Fraction() for r, b in zip(residual, budgets)), default=Fraction())
    return residual, utilization


def audit_mb_weak_local_trajectory(contract, records, *, checkpoint_stride=64):
    """Audit each interval once and every local/global initial-to-current prefix.

    Controls and rows are privately detached before callbacks can resume.
    Local budgets use fresh child audit results, never producer audit claims.
    Each cell and the global sum retain the original hard 1e-9 particle and
    1e-27 J caps (or tighter contract caps). Checkpoint metadata grows with
    cells * steps / stride; full proof rows stream once.
    """
    if type(contract) is not dict: raise ValueError('explicit trajectory contract required')
    c = json.loads(canonical_bytes(contract))
    try:
        expected = weak_trajectory_contract(c['configurations'], c['initial'], c['faces'], c['thermal_faces'],
            c['dt_s'], c['steps'], impulses_J=c['impulses_J'], particle_atol=c['particle_atol'], energy_atol_J=c['energy_atol_J'])
    except (KeyError, TypeError) as exc: raise ValueError('trajectory contract coverage') from exc
    if c != expected: raise ValueError('trajectory contract metadata/coverage mismatch')
    if type(checkpoint_stride) is not int or not 1 <= checkpoint_stride <= 16384:
        raise ValueError('bounded checkpoint stride required')
    pa = min(_command(c['particle_atol']), Fraction(1, 10**9))
    ea = min(_command(c['energy_atol_J']), Fraction(1, 10**27))
    limits = [pa, pa, ea, ea, ea, ea]; old = c['initial']; n = len(old)
    initial = [_inventory([s])[0] for s in old]
    global_initial, frames = _inventory(old)
    ledger = [[Fraction()] * 6 for _ in old]; budgets = [[Fraction()] * 6 for _ in old]
    global_budget = [Fraction()] * 6; previous = record_digest(c)
    count = 0; maximum = Fraction(); checkpoints = []; last = None
    for supplied in records:
        if count >= c['steps']: raise ValueError('trajectory extra record')
        if type(supplied) is not dict: raise ValueError('explicit trajectory record required')
        row = json.loads(canonical_bytes(supplied))
        if set(row) != {'index', 'previous_sha256', 'new', 'report', 'sha256'}:
            raise ValueError('trajectory record coverage')
        if (type(row['index']) is not int or row['index'] != count or row['previous_sha256'] != previous
                or row['sha256'] != record_digest({k: v for k, v in row.items() if k != 'sha256'})):
            raise ValueError('trajectory record sequence/hash chain mismatch')
        check = audit_mb_weak_rounded_split(c['configurations'], old, row['new'], row['report'],
            faces=maintained_faces(c, old), thermal_faces=c['thermal_faces'], dt_s=c['dt_s'],
            impulses_J=c['impulses_J'], particle_atol=1e-9, energy_atol_J=1e-27)
        if not check['valid'] or len(check['cells']) != n: raise ValueError('trajectory child audit failed')
        actual, newframes = _inventory(row['new'])
        if frames != newframes: raise ValueError('trajectory changed frozen material/geometric frames')
        transfers = _local_ledger(c, row['report']); cells = []
        for i, state in enumerate(row['new']):
            ledger[i] = [a + b for a, b in zip(ledger[i], transfers[i])]
            budgets[i] = [a + b for a, b in zip(budgets[i], _upper(check['cells'][i]['budgets']))]
            residual, use = _prefix(_inventory([state])[0], initial[i], ledger[i], budgets[i], limits, 'cell ' + str(i))
            maximum = max(maximum, use)
            cells.append(dict(cell=i, residuals=list(map(_display, residual)), budgets=list(map(_display, budgets[i]))))
        global_budget = [a + b for a, b in zip(global_budget, _upper(check['global_budgets']))]
        residual, use = _prefix(actual, global_initial, _sum(ledger), global_budget, limits, 'global')
        maximum = max(maximum, use); count += 1; previous = row['sha256']; old = row['new']
        last = dict(step=count, time_s=old[0]['time_s'], cells=cells,
                    global_residuals=list(map(_display, residual)), global_budgets=list(map(_display, global_budget)))
        if count % checkpoint_stride == 0 or count == c['steps']: checkpoints.append(last)
    if count != c['steps']: raise ValueError('trajectory missing records')
    return dict(valid=True, scope='streamed_independent_weak_local_trajectory_v1', accepted_steps=count,
        cell_intervals=count*n, contract_sha256=record_digest(c), last_record_sha256=previous,
        row_order=ROWS.copy(), checkpoints=checkpoints, final=last,
        maximum_local_or_global_prefix_budget_utilization=_display(maximum),
        all_actual_cell_prefixes_closed=True, all_actual_global_prefixes_closed=True,
        internal_face_ownership_checked=True, local_cumulative_error_allowance_enforced=True,
        fresh_interval_audits=count, native_physics_used=False, field_work_included=False,
        complete_device_energy=False, physical_validated=False)
