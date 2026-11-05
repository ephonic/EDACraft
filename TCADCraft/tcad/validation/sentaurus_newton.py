"""Audit W-2024.09 single-device Poisson/Electron/Hole Newton diagnostics.

Only complete, recognized diagnostic blocks are removed before the existing
strict convergence audit. Unknown text remains in the table and fails that
audit. Positions refer to the original log; diagnostics never relax a gate.
"""
import math
import re
from decimal import Decimal, InvalidOperation

if __package__:
    from .sentaurus_log import audit_sentaurus_nonlinear_convergence
else:  # Standalone copies in sealed validation bundles.
    from sentaurus_log import audit_sentaurus_nonlinear_convergence

_FLOAT = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?'
_HEADER = re.compile(r'^Iteration\s+\|Rhs\|\s+factor\s+\|step\|\s+error\s+#inner\s+#iterative\s+time\s*$')
_RHS = re.compile(rf'^\s*({_FLOAT})\s*:\s*(\d+)\s*:\s*({_FLOAT})\s*:\s*:\s*(Poisson|Electron|Hole)\s*:\s*\(([^()]*)\)\s*$')
_CNORM = re.compile(rf'^\s*(poisson|electron|hole):\s*({_FLOAT})\s+(\d+)\s+\(([^()]*)\)\s*({_FLOAT})\s*$')
_RHS_HEADER = 'max-norm : imax : l2-norm : inst : pde : imax-coords (um)'
_CNORM_HEADER = 'C-norm_equation max_error vertex coordinate [um] value'
_NEWTONPLOT = re.compile(r'^writing ([^\s]+\.tdr) \(TDR format\) \.\.\. done\.$')


def _number(text, nonnegative=False):
    d = Decimal(text.replace('d', 'e').replace('D', 'E'))
    v = float(d)
    if not d.is_finite() or not math.isfinite(v) or (v == 0 and d != 0) or (nonnegative and d < 0):
        raise ValueError('nonfinite, underflowed or negative diagnostic value')
    return v


def _coordinates(text):
    parts = text.replace(',', ' ').split()
    if len(parts) not in (2, 3):
        raise ValueError('expected two or three coordinates')
    return [_number(v) for v in parts]


def audit_sentaurus_newton_diagnostics(log, *, initial_rhs_tolerance=0.0):
    """Return strict history and equation maxima, without granting physics qualification.

    ``following_c_norm`` means printed after that iteration row; no unprinted
    Newton state, equation scaling, physical cause or physical bias is inferred.
    Supported systems are Poisson alone, or Poisson/Electron/Hole together.
    """
    if not isinstance(log, str):
        raise ValueError('log must be text')
    lines = log.splitlines(keepends=True)
    canonical = list(lines)
    records, issues = [], []
    table = -1
    active = False
    record = None
    mode = None
    block_count = 0
    block_header_line = None

    def close_block():
        if mode is not None and block_count == 0:
            issues.append(dict(line=block_header_line, reason='empty diagnostic block'))

    for line_number, raw in enumerate(lines, 1):
        line = raw.rstrip('\r\n')
        stripped = line.strip()
        if _HEADER.fullmatch(line):
            close_block()
            table += 1
            active, record, mode = True, None, None
            continue
        if not active:
            continue
        if stripped.startswith('Finished, because'):
            close_block()
            active, mode = False, None
            continue
        if re.match(rf'^\s*\d+\s+{_FLOAT}\s+', line):
            close_block()
            words = line.split()
            if len(words) in (3, 8):
                record = dict(table_index=table, iteration=int(words[0]), line_number=line_number,
                              reported_rhs=words[1], rhs_per_equation={}, following_c_norm={})
                records.append(record)
            else:
                record = None
            mode = None
            continue
        normalized = ' '.join(stripped.split())
        recognized = False
        plot = _NEWTONPLOT.fullmatch(line)
        if plot and record is not None:
            if 'newtonplot_output' in record:
                issues.append(dict(line=line_number, reason='duplicate NewtonPlot output for iteration'))
            else:
                record['newtonplot_output'] = dict(filename=plot[1], line_number=line_number)
                recognized = True
        elif stripped == 'k_error_per_object:' or normalized == _CNORM_HEADER:
            close_block()
            if record is None:
                issues.append(dict(line=line_number, reason='diagnostic without iteration'))
            mode = 'rhs_header' if stripped == 'k_error_per_object:' else 'cnorm'
            block_count, block_header_line = 0, line_number
            recognized = True
        elif mode == 'rhs_header' and normalized == _RHS_HEADER:
            mode = 'rhs'
            recognized = True
        elif mode in ('rhs', 'cnorm') and stripped:
            match = (_RHS if mode == 'rhs' else _CNORM).fullmatch(line)
            if match and record is not None:
                try:
                    if mode == 'rhs':
                        norm, imax, l2, equation, coords = match.groups()
                        values = dict(max_norm=_number(norm, True), imax=int(imax), l2_norm=_number(l2, True),
                                      coordinates_um=_coordinates(coords), line_number=line_number)
                        target = record['rhs_per_equation']
                    else:
                        equation, error, vertex, coords, value = match.groups()
                        values = dict(max_error=_number(error, True), vertex=int(vertex), coordinates_um=_coordinates(coords),
                                      reported_value=_number(value, equation != 'poisson'), line_number=line_number)
                        target = record['following_c_norm']
                    equation = equation.lower()
                    if equation in target:
                        raise ValueError('duplicate equation diagnostic')
                    target[equation] = values
                    block_count += 1
                    recognized = True
                except (ValueError, InvalidOperation, OverflowError) as exc:
                    issues.append(dict(line=line_number, reason=str(exc)))
        if recognized:
            # Preserve original line numbers for strict failures and diagnostics.
            canonical[line_number - 1] = '\n' if raw.endswith('\n') else ''
    close_block()
    available = any(r['rhs_per_equation'] or r['following_c_norm'] for r in records)
    if available:
        for r in records:
            rhs, cnorm = r['rhs_per_equation'], r['following_c_norm']
            if set(rhs) not in ({'poisson'}, {'poisson', 'electron', 'hole'}) or (cnorm and set(cnorm) != set(rhs)):
                issues.append(dict(line=r['line_number'], reason='incomplete or unsupported equation set'))
                continue
            try:
                printed = _number(r['reported_rhs'], True)
                largest = max(v['max_norm'] for v in rhs.values())
                if abs(printed - largest) > .01 * max(printed, largest):
                    issues.append(dict(line=r['line_number'], reason='collective RHS disagrees with equation maximum'))
            except (ValueError, InvalidOperation, OverflowError) as exc:
                issues.append(dict(line=r['line_number'], reason=str(exc)))
    history = audit_sentaurus_nonlinear_convergence(''.join(canonical), initial_rhs_tolerance=initial_rhs_tolerance)
    failures = []
    for failure in history['failure_diagnostics']:
        tail = [r for r in records if r['table_index'] == failure['table_index']][-8:]
        failures.append(dict(table_index=failure['table_index'], tail_iterations=tail))
    return dict(valid=history['valid'] and not issues, history=history, diagnostics_valid=not issues,
                diagnostics_available=available, issues=issues, records=records, failures=failures,
                scope='reported_w2024_09_single_device_equation_diagnostics', coordinate_unit='um',
                physical_voltage_inferred=False, root_cause_proven=False, acceptance_criteria_changed=False,
                physical_validated=False, complete_sentaurus_alignment=False)
