"""Finite scalar inputs must not qualify an unrepresentable flux calculation."""
from copy import deepcopy
import hashlib,importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
from tcad.postprocess import spatial_energy_transport as current
from test_frozen_spatial_energy_flux import sample,COEFF
from test_spatial_energy_transport import profile


def parent_module():
    path=Path(__file__).resolve().parents[1]/'docs/validation/frozen_flux_finite_20261022/before/tcad/postprocess/spatial_energy_transport.py'
    spec=importlib.util.spec_from_file_location('frozen_flux_parent',path)
    mod=importlib.util.module_from_spec(spec)
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(mod)
    finally:sys.dont_write_bytecode=previous
    return mod


def ramp(sign=1.):
    x=np.linspace(0,1e-7,9)
    p=dict(case_id='finite-control',role='holdout',source_sha256=hashlib.sha256(b'finite-control').hexdigest(),
           material_model='synthetic ramp',units='SI',x_m=x)
    for k in ('Tn_K','Tp_K','Tl_K'):p[k]=600+sign*x/1e-7
    for k in ('n_m3','p_m3'):p[k]=np.full(9,1e21)
    for k in ('mu_n_m2_Vs','mu_p_m2_Vs'):p[k]=np.full(9,.003)
    for k in ('Fn_m2_s','Fp_m2_s'):p[k]=np.full(9,-sign*1e22)
    for k in ('Sn_W_m2','Sp_W_m2'):p[k]=np.full(9,1e6)
    return p


@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('kind',['coefficient','prediction','difference'])
def test_nonfinite_error_cannot_pass_nonfinite_budget(kind,sign):
    p=ramp(sign)
    if kind=='coefficient':coeff={s:dict(r=1e307,hf=1e307) for s in COEFF}
    elif kind=='prediction':coeff={s:dict(r=1e307,hf=1.) for s in COEFF}
    else:
        # Finite predicted and observed fluxes, overflowing only subtraction.
        for k in ('Tn_K','Tp_K'):p[k][:]=600.
        # Keep inputs finite by placing amplification in the coefficient.
        for k in ('Fn_m2_s','Fp_m2_s'):p[k][:]=1e22
        for k in ('Sn_W_m2','Sp_W_m2'):p[k][:]=-1.2e308
        coeff={s:dict(r=1.2e308/(2.5*current.KB*600*1e22),hf=1.) for s in COEFF}
    assert all(np.all(np.isfinite(v)) for v in p.values() if isinstance(v,np.ndarray))
    with np.errstate(all='ignore'):
        old=parent_module().check_spatial_energy_flux([p],coeff,relative_gate=1e308)
    assert old['accepted'] and all(c['maximum_error_W_m2']==np.inf for c in old['checks'])
    with pytest.raises(ValueError,match='finite'):
        current.check_spatial_energy_flux([p],coeff,relative_gate=1e308)


def test_overflowed_budget_rejected_even_with_finite_prediction():
    p=sample()
    assert parent_module().check_spatial_energy_flux([p],COEFF,relative_gate=1e308)['accepted']
    with pytest.raises(ValueError,match='budget'):
        current.check_spatial_energy_flux([p],COEFF,relative_gate=1e308)


@pytest.mark.parametrize('carrier',['electrons','holes'])
@pytest.mark.parametrize('key',['r','hf'])
@pytest.mark.parametrize('value',['1e400','1e-400'])
def test_extended_scalar_must_survive_float64_conversion(carrier,key,value):
    coeff=deepcopy(COEFF);coeff[carrier][key]=np.longdouble(value)
    assert np.isfinite(coeff[carrier][key]) and coeff[carrier][key]>0
    with pytest.raises(ValueError):current.check_spatial_energy_flux([sample()],coeff)


@pytest.mark.parametrize('key',['relative_gate','minimum_peak_flux_W_m2'])
@pytest.mark.parametrize('value',['1e400','1e-400'])
def test_extended_gate_must_survive_float64_conversion(key,value):
    with pytest.raises(ValueError):current.check_spatial_energy_flux([sample()],COEFF,**{key:np.longdouble(value)})


def test_nonzero_diffusive_coefficient_cannot_underflow_to_zero():
    coeff={s:dict(r=1e-200,hf=1e-200) for s in COEFF}
    with pytest.raises(ValueError,match='diffusive coefficient'):
        current.check_spatial_energy_flux([sample()],coeff)


@pytest.mark.parametrize('field',['Fn_m2_s','Fp_m2_s','n_m3','p_m3'])
def test_nonfinite_derived_design_is_rejected(field):
    p=ramp();p[field][:]=np.finfo(float).max
    # Advective T*F remains finite after k; increase T to provoke overflow.
    if field in ('Fn_m2_s','Fp_m2_s'):
        p['Tn_K' if field=='Fn_m2_s' else 'Tp_K'][:]=1e30
    else:
        p['mu_n_m2_Vs' if field=='n_m3' else 'mu_p_m2_Vs'][:]=1e100
    with pytest.raises(ValueError,match='design'):
        current.check_spatial_energy_flux([p],COEFF)


@pytest.mark.parametrize('changed',[False,True])
def test_normal_frozen_reports_remain_exact_and_inputs_unchanged(changed):
    p=sample();coeff=deepcopy(COEFF)
    if changed:p['Sp_W_m2'][60]*=2.
    before=deepcopy(p)
    assert current.check_spatial_energy_flux([p],coeff)==parent_module().check_spatial_energy_flux([p],coeff)
    for k,v in p.items():np.testing.assert_equal(v,before[k])
    assert coeff==COEFF


def test_fitted_normal_report_remains_exact():
    data=[profile('a','calibration'),profile('b','calibration',-1),profile('c','holdout',-.5)]
    assert current.fit_spatial_energy_flux(data)==parent_module().fit_spatial_energy_flux(data)


def test_large_finite_mismatch_remains_a_reported_rejection():
    coeff={s:dict(r=1e300,hf=1.) for s in COEFF}
    report=current.check_spatial_energy_flux([sample()],coeff)
    assert report==parent_module().check_spatial_energy_flux([sample()],coeff)
    assert not report['accepted']
    assert all(np.isfinite(c['maximum_error_W_m2']) and np.isfinite(c['maximum_peak_relative_error']) for c in report['checks'])


def test_zero_signal_unresolved_report_remains_exact():
    p=sample()
    for k in ('Tn_K','Tp_K'):p[k][:]=600.
    for k in ('Fn_m2_s','Fp_m2_s','Sn_W_m2','Sp_W_m2'):p[k][:]=0.
    report=current.check_spatial_energy_flux([p],COEFF)
    assert report==parent_module().check_spatial_energy_flux([p],COEFF)
    assert not report['accepted'] and all(c['maximum_peak_relative_error'] is None for c in report['checks'])
