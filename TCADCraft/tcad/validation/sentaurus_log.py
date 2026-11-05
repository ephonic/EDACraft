"""Strict audit of the nonlinear tables in a Sentaurus Device text log.

The supported table is the Bank/Rose format recorded with W-2024.09. This
checks the reported solve history, independently of field/reference accuracy.
An absolute RHS exit with a large relative error is not a strict pass.
"""
import math
import re
from decimal import Decimal, InvalidOperation


def _failure_diagnostic(log, position, index, rows, malformed, termination):
    """Describe printed evidence without changing the convergence decision."""
    if malformed:
        kind='malformed_table'
    elif re.match(r'Finished, because(?:\.\.\.)?\s*#iterations larger than\s+\d+',termination):
        kind='iteration_limit'
    elif rows and rows[-1]['relative_error'] is not None and rows[-1]['relative_error']>1:
        kind='update_error_above_tolerance'
    else:
        kind='missing_or_unsupported_termination'
    # A later standalone Coupled solve must not inherit the last ramp's step.
    problem=log.rfind('Starting solve of next problem:',0,position)
    step=None
    step_pattern=re.compile(r'^Computing step from t=(\S+) to t=(\S+) \(Stepsize:\s*(\S+)\)\s*:',re.M)
    if problem>=0 and log[problem+len('Starting solve of next problem:'):].lstrip().startswith('Quasistationary'):
        matches=list(step_pattern.finditer(log,problem,position))
        if matches:
            match=matches[-1]
            step=dict(start_t=match[1],target_t=match[2],step_size_t=match[3])
    tail=rows[-8:]
    # This is a pattern in rounded, printed residuals, not a theorem about the
    # nonlinear map or evidence of a unique physical root.
    rhs=[r['rhs'] for r in tail]
    cycle=False
    if len(rhs)==8 and all(v>0 for v in rhs) and all(r['relative_error'] is not None and r['relative_error']>1 for r in tail):
        even=rhs[::2];odd=rhs[1::2]
        cycle=(max(even)/min(even)<=1.01 and max(odd)/min(odd)<=1.01 and
               abs(even[-1]-odd[-1])/max(even[-1],odd[-1])>.05)
    return dict(table_index=index,line_number=log.count('\n',0,position)+1,
        failure_kind=kind,quasistationary_step=step,physical_voltage_inferred=False,
        tail_rows=tail,two_cycle_in_reported_rhs=bool(cycle),
        numerical_cycle_proven=False,acceptance_criteria_changed=False)


def audit_sentaurus_nonlinear_convergence(log, *, initial_rhs_tolerance=0.0):
    """Require each reported nonlinear table to finish with error <= 1.

    An exactly zero initial RHS also passes without an update/error column.
    An explicit initial_rhs_tolerance <= 1e-35 permits a zero-update RHS exit
    only below its printed bound, itself <= that tolerance. The default stays
    exact zero. Failure diagnostics never change acceptance criteria.
    Nonzero initial RHS without an error, malformed/truncated tables, negative
    or nonfinite numbers, failed attempts, and missing final completion fail.
    Even a rejected attempt followed by a successful retry remains visible and
    fails this deliberately strict reference gate. No authenticity, spatial or
    temporal convergence, or physical calibration is inferred from this audit.
    """
    try:
        tolerance=Decimal(str(initial_rhs_tolerance))
    except InvalidOperation as exc:
        raise ValueError('initial RHS tolerance must be finite in [0, 1e-35]') from exc
    if not tolerance.is_finite() or tolerance<0 or tolerance>Decimal('1e-35'):
        raise ValueError('initial RHS tolerance must be finite in [0, 1e-35]')
    if not isinstance(log,str):
        raise ValueError('log must be text')
    header=re.compile(r'^Iteration\s+\|Rhs\|\s+factor\s+\|step\|\s+error\s+#inner\s+#iterative\s+time\s*$',re.M)
    starts=list(header.finditer(log));tables=[];failures=[]
    unsupported=max(0,len(re.findall(r'^Iteration\s+',log,re.M))-len(starts))
    for index,match in enumerate(starts):
        end=starts[index+1].start() if index+1<len(starts) else len(log)
        block=log[match.end():end]
        finish=block.find('Finished, because')
        body=block[:finish] if finish>=0 else block
        termination=block[finish:] if finish>=0 else ''
        reason=re.match(r'Finished, because(?:\.\.\.)?\s*(Error smaller than 1[^\n]*|\|RHS\| (?:is )?less than [^\n]+)',termination)
        rows=[];malformed=False
        for line in body.splitlines():
            if not line.strip() or set(line.strip())=={'-'}:continue
            if not re.match(r'^\s*\d+\s+',line):
                malformed=True
                continue
            words=line.split()
            try:
                if len(words) not in (3,8):raise ValueError('unexpected table columns')
                decimal_values=[Decimal(v.replace('D','E').replace('d','e')) for v in words]
                values=[float(v) for v in decimal_values]
                if not all(math.isfinite(v) and v>=0 for v in values):raise ValueError('invalid table value')
                if any(v==0 and d!=0 for v,d in zip(values,decimal_values)):raise ValueError('table value underflow')
                if not words[0].isdigit():raise ValueError('noninteger iteration')
                if int(values[0])!=values[0]:raise ValueError('noninteger iteration')
                if not rows and values[0]!=0:raise ValueError('missing initial iteration')
                if rows and values[0]!=rows[-1]['iteration']+1:raise ValueError('missing iteration')
                if rows and len(words)!=8:raise ValueError('missing relative error')
                rows.append(dict(iteration=int(values[0]),rhs=values[1],relative_error=values[4] if len(words)==8 else None))
            except (ValueError,OverflowError,InvalidOperation):malformed=True
        last=rows[-1] if rows else None
        initial_small=False
        if tolerance>0 and last and last['iteration']==0 and last['relative_error'] is None:
            limit=re.match(r'Finished, because(?:\.\.\.)?\s*\|RHS\| (?:is )?less than ([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?)(?:\.\s*|\s*)$',termination.splitlines()[0] if termination.splitlines() else '')
            if limit:
                bound=Decimal(limit.group(1).replace('D','E').replace('d','e'))
                initial_small=bound.is_finite() and 0<bound<=tolerance and Decimal(str(last['rhs']))<bound
        valid=bool(reason and not malformed and last and
            ((last['relative_error'] is not None and last['relative_error']<=1.) or
             (last['iteration']==0 and last['relative_error'] is None and (last['rhs']==0. or initial_small))))
        tables.append(dict(index=index,valid=valid,malformed=malformed,
            termination_present=bool(reason),iterations=len(rows),final=last))
        if not valid:
            failures.append(_failure_diagnostic(log,match.start(),index,rows,malformed,termination))
    last_header=starts[-1].start() if starts else 0
    complete=(log.rfind('Sentaurus Device simulation finished')>last_header and
              log.rfind('Good Bye !')>log.rfind('Sentaurus Device simulation finished'))
    return dict(valid=bool(complete and tables and not unsupported and all(t['valid'] for t in tables)),
        completed=complete,table_count=len(tables),tables=tables,
        unsupported_table_headers=unsupported,
        rejected_table_indices=[t['index'] for t in tables if not t['valid']],
        failure_diagnostics=failures,
        scope='reported_bank_rose_nonlinear_convergence',physical_validated=False,
        spatial_convergence_validated=False,temporal_convergence_validated=False,
        reference_authenticity_validated=False)
