"""Failure localization must never soften the commercial convergence gate."""
from pathlib import Path
import os

import pytest

from tcad.validation import audit_sentaurus_nonlinear_convergence as audit

HEADER='Iteration   |Rhs|      factor     |step|     error   #inner  #iterative  time\n----\n'
COMPLETE='Sentaurus Device simulation finished\nGood Bye !\n'
RAMP='Starting solve of next problem:\nQuasistationary (\n)\nComputing step from t=0.0258852 to t=0.0283852 (Stepsize: 2.5000e-03) :\n'


def failed_table(rhs=None):
    rhs=rhs or [1e-7,2e-7]*4
    rows='0 1e-3 0.00\n'+''.join(f'{i} {v} 1.0 1e-7 1e7 0 1 .1\n' for i,v in enumerate(rhs,1))
    return HEADER+rows+'Finished, because...\n#iterations larger than 8.\n'


def test_iteration_limit_localized_without_acceptance():
    report=audit(RAMP+failed_table()+COMPLETE)
    assert not report['valid'] and report['rejected_table_indices']==[0]
    failure=report['failure_diagnostics'][0]
    assert failure['failure_kind']=='iteration_limit'
    assert failure['quasistationary_step']==dict(start_t='0.0258852',target_t='0.0283852',step_size_t='2.5000e-03')
    assert failure['line_number']==5 and len(failure['tail_rows'])==8
    assert failure['two_cycle_in_reported_rhs']
    assert not failure['physical_voltage_inferred'] and not failure['numerical_cycle_proven']
    assert not failure['acceptance_criteria_changed']


@pytest.mark.parametrize('rhs',[[1e-7]*8,[8e-7,7e-7,6e-7,5e-7,4e-7,3e-7,2e-7,1e-7],[1e-7,2e-7,3e-7]*2,[0,2e-7]*4])
def test_contraction_constant_short_and_zero_tails_are_not_a_two_cycle(rhs):
    failure=audit(RAMP+failed_table(rhs)+COMPLETE)['failure_diagnostics'][0]
    assert not failure['two_cycle_in_reported_rhs']


def test_standalone_solve_does_not_inherit_stale_ramp_step():
    text=RAMP+'Starting solve of next problem:\nCoupled ( )\n'+failed_table()+COMPLETE
    assert audit(text)['failure_diagnostics'][0]['quasistationary_step'] is None


def test_rhs_exit_with_large_update_is_still_rejected():
    text=failed_table().replace('#iterations larger than 8.','|RHS| less than 1e-5.')
    report=audit(text+COMPLETE)
    assert not report['valid'] and report['failure_diagnostics'][0]['failure_kind']=='update_error_above_tolerance'


def test_malformed_table_does_not_become_a_cycle_diagnosis_of_convergence():
    text=failed_table().replace('1 1e-07','1 nan')
    report=audit(text+COMPLETE)
    assert not report['valid'] and report['failure_diagnostics'][0]['failure_kind']=='malformed_table'


def test_exact_zero_and_explicit_installed_tolerance_compatibility():
    def log(rhs,bound):return HEADER+f'0 {rhs} .0\nFinished, because |RHS| less than {bound}.\n'+COMPLETE
    assert audit(log('0','1e-35'))['valid']
    assert not audit(log('1e-36','1e-35'))['valid']
    assert audit(log('1e-36','1e-35'),initial_rhs_tolerance=1e-35)['valid']
    assert not audit(log('1e-36','1e-5'),initial_rhs_tolerance=1e-35)['valid']


@pytest.mark.parametrize('value',[-1,1e-34,float('nan'),float('inf'),'bad'])
def test_invalid_tolerance_rejected(value):
    with pytest.raises(ValueError):audit('',initial_rhs_tolerance=value)


def test_real_uniform_and_segmented_failures_are_localized():
    root=Path(os.environ.get('TCAD_REFERENCE_ROOT',Path(__file__).resolve().parents[1]))/'docs/validation/hfs_unequal_contacts_20261029'
    for relative,indices in [('commercial_m256_s-1_qf1_o1',[17]),('revisions/segmented_protocol/commercial_m256_s-1_qf1_o1',[97,108,122,123])]:
        report=audit((root/relative/'sample.log_des.log').read_text(),initial_rhs_tolerance=1e-35)
        assert not report['valid'] and report['rejected_table_indices']==indices
        assert [r['table_index'] for r in report['failure_diagnostics']]==indices
        assert all(r['quasistationary_step'] is not None for r in report['failure_diagnostics'])
