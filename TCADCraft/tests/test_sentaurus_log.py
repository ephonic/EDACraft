"""Reject prematurely terminated or incomplete commercial reference solves."""
from pathlib import Path
import os

import pytest

from tcad.validation import audit_sentaurus_nonlinear_convergence as audit

HEADER='Iteration   |Rhs|      factor     |step|     error   #inner  #iterative  time\n----\n'
INITIAL='    0      1.00e-03   0.00\n'
ROW='    1      1.00e-12   1.00e+00   2.00e-08   0.50   0   7   0.04\n'
FINISH='Finished, because...\nError smaller than 1 ( 5.0000E-01 ).\n'
COMPLETE='Sentaurus Device simulation finished\nGood Bye !\n'


def test_relative_converged_table():
    result=audit(HEADER+INITIAL+ROW+FINISH+COMPLETE)
    assert result['valid'] and result['table_count']==1
    assert not result['physical_validated']
    assert not result['spatial_convergence_validated']


def test_zero_initial_rhs_does_not_require_an_update():
    assert audit(HEADER+'0 0.00e+00 0.00\nFinished, because |RHS| is less than 1.0000e-35.\n'+COMPLETE)['valid']


def test_default_absolute_rhs_exit_with_large_error_is_rejected():
    row=ROW.replace('0.50','1.48e+06')
    result=audit(HEADER+INITIAL+row+'Finished, because...\n|RHS| less than 1.0000E-05.\n'+COMPLETE)
    assert not result['valid'] and result['rejected_table_indices']==[0]


@pytest.mark.parametrize('row',[
    ROW.replace('0.50','nan'),ROW.replace('0.50','inf'),ROW.replace('0.50','-0.1'),
    ROW.replace('0.50','1.01'),ROW.replace('    1','    2'),ROW.replace('1.00e-12','bad'),
    ROW.replace('1.00e-12','-1.0'),ROW.replace('   7',''),
    '1 0.0 0.04\n',
])
def test_invalid_final_rows(row):
    assert not audit(HEADER+INITIAL+row+FINISH+COMPLETE)['valid']


@pytest.mark.parametrize('log',[
    '',COMPLETE,HEADER+INITIAL+ROW,HEADER+INITIAL+ROW+FINISH,
    HEADER+INITIAL+ROW+COMPLETE,
    HEADER+INITIAL+FINISH+COMPLETE,
    HEADER+ROW+FINISH+COMPLETE,
    HEADER+INITIAL+ROW+'Finished, because...\nMaximum iterations reached.\n'+COMPLETE,
])
def test_missing_or_truncated_evidence(log):
    assert not audit(log)['valid']


def test_later_success_cannot_hide_earlier_unconverged_table():
    bad=HEADER+INITIAL+ROW.replace('0.50','100')+'Finished, because...\n|RHS| less than 1e-5.\n'
    result=audit(bad+HEADER+INITIAL+ROW+FINISH+COMPLETE)
    assert result['table_count']==2 and result['rejected_table_indices']==[0]


def test_fortran_exponents_are_supported():
    assert audit(HEADER+INITIAL+ROW.replace('e-','D-')+FINISH+COMPLETE)['valid']


def test_text_required():
    with pytest.raises(ValueError,match='text'):audit(b'log')


def test_unknown_row_cannot_hide_after_an_exact_zero_initial_residual():
    text=HEADER+'0 0.00e+00 0.00\nNaN bad row\nFinished, because |RHS| less than 1e-5.\n'+COMPLETE
    assert not audit(text)['valid']


def test_completion_marker_must_follow_the_last_table():
    assert not audit(COMPLETE+HEADER+INITIAL+ROW+FINISH)['valid']


def test_unsupported_later_table_header_cannot_be_ignored():
    good=HEADER+INITIAL+ROW+FINISH
    bad_header=HEADER.replace('factor','other')
    result=audit(good+bad_header+INITIAL+ROW+FINISH+COMPLETE)
    assert not result['valid'] and result['unsupported_table_headers']==1


def test_nonzero_initial_rhs_underflow_is_not_exact_zero():
    log=HEADER+'0 1.0e-999 0.00\nFinished, because |RHS| less than 1e-5.\n'+COMPLETE
    assert not audit(log)['valid']


@pytest.mark.parametrize('cells',[8,16,32])
def test_actual_3d_default_rhs_logs_are_rejected(cells):
    out=Path(os.environ.get('TCAD_REFERENCE_ROOT',Path(__file__).resolve().parents[1]))/'docs/validation/nonuniform_fe_3d_20261017'
    result=audit((out/f'commercial_m{cells}/sdevice_run.log').read_text())
    assert result['completed'] and result['table_count']==9
    assert not result['valid'] and result['rejected_table_indices']


@pytest.mark.parametrize('cells',[8,16])
def test_actual_3d_tight_logs_have_all_nine_solves_converged(cells):
    out=Path(os.environ.get('TCAD_REFERENCE_ROOT',Path(__file__).resolve().parents[1]))/'docs/validation/nonuniform_fe_3d_20261017'
    result=audit((out/f'commercial_tight_m{cells}/sdevice_run.log').read_text())
    assert result['valid'] and result['table_count']==9


def test_timed_out_strict_3d_reference_is_unavailable():
    out=Path(os.environ.get('TCAD_REFERENCE_ROOT',Path(__file__).resolve().parents[1]))/'docs/validation/nonuniform_fe_3d_20261017'
    result=audit((out/'commercial_tight_m32/sdevice_run.log').read_text())
    assert not result['valid'] and not result['completed']


def test_strict_direct_reference_at_16_is_converged():
    out=Path(os.environ.get('TCAD_REFERENCE_ROOT',Path(__file__).resolve().parents[1]))/'docs/validation/nonuniform_fe_3d_20261017'
    result=audit((out/'commercial_direct_m16/sdevice_run.log').read_text())
    assert result['valid'] and result['table_count']==9
