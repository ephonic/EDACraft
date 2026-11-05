"""Constant-tau training-model mismatch cannot be rescued by held-out matches."""
from dataclasses import replace
import hashlib,importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
from tcad.material import carrier_relaxation_calibration as current
from test_carrier_relaxation_calibration import traces

OUT=Path(__file__).resolve().parents[1]/'docs/validation/decay_training_gate_20261022'
ADDED={'training_checks','training_accepted','accepted'}


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=previous
    return module


def manufactured(carrier='electrons',fraction=.08,scale=1.):
    return load('frozen_decay_probe',OUT/'frozen_probe.py').make(carrier,fraction,scale)


def old_fit(data,**kwargs):
    mod=load('frozen_decay_parent',OUT/'before/tcad/material/carrier_relaxation_calibration.py')
    rows=[mod.CommercialDecayTrace(**{k:getattr(t,k) for k in mod.CommercialDecayTrace.__dataclass_fields__}) for t in data]
    return mod.calibrate_commercial_relaxation(rows,**kwargs)


@pytest.mark.parametrize('carrier',['electrons','holes'])
@pytest.mark.parametrize('scale',[1.,1e-4])
def test_old_success_with_large_training_mismatch_is_rejected(carrier,scale):
    data=manufactured(carrier,scale=scale)
    before=[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]
    old=old_fit(data,minimum_signal_K=1e-5)
    assert old['commercial_relaxation_calibrated'] and old['holdouts_accepted']
    assert old['parameters'][carrier]['maximum_training_normalized_error']>.08
    with pytest.raises(ValueError,match='constant-tau decay exceeds training gate'):
        current.calibrate_commercial_relaxation(data,minimum_signal_K=1e-5)
    assert before==[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]


@pytest.mark.parametrize('carrier',['electrons','holes'])
@pytest.mark.parametrize('fraction',[.005,.009,.011,.08])
def test_default_one_percent_gate_applies_to_each_species(carrier,fraction):
    data=manufactured(carrier,fraction)
    old=old_fit(data)
    if old['parameters'][carrier]['maximum_training_normalized_error']>.01:
        with pytest.raises(ValueError,match='training gate'):current.calibrate_commercial_relaxation(data)
    else:
        report=current.calibrate_commercial_relaxation(data)
        assert report['training_accepted'] and report['accepted']
        check=next(r for r in report['training_checks'] if r['carrier']==carrier)
        assert check['maximum_peak_normalized_error']<=.01
        assert {k:v for k,v in report.items() if k not in ADDED}==old


@pytest.mark.parametrize('value',[True,0.,-1.,np.inf,np.nan,1j,[.01]])
def test_training_gate_requires_positive_finite_real_scalar(value):
    with pytest.raises(ValueError):current.calibrate_commercial_relaxation(traces(),training_relative_gate=value)


@pytest.mark.parametrize('carrier',['electrons','holes'])
def test_both_training_checks_precede_any_holdout_prediction(monkeypatch,carrier):
    data=manufactured(carrier)
    for i,t in enumerate(data):
        if t.role=='holdout':
            tau=3e-13 if t.carrier=='electrons' else 2.5e-13
            times=np.linspace(0.,1.8*tau,43)
            data[i]=replace(t,times_s=times,temperatures_K=300+2*np.exp(-times/tau))
    original=np.exp
    def prohibit_holdout(argument,*args,**kwargs):
        assert np.asarray(argument).shape!=(43,),'holdout prediction before both training laws qualify'
        return original(argument,*args,**kwargs)
    monkeypatch.setattr(current.np,'exp',prohibit_holdout)
    with pytest.raises(ValueError,match='training gate'):current.calibrate_commercial_relaxation(data)


def test_reports_each_training_curve_and_preserves_flags():
    data=traces();result=current.calibrate_commercial_relaxation(data)
    assert result['training_accepted'] and result['accepted']
    assert len(result['training_checks'])==2
    for r in result['training_checks']:
        t=next(t for t in data if t.case_id==r['case_id'])
        assert t.role=='calibration' and r['source_sha256']==t.source_sha256 and r['accepted']
    assert not any(result[k] for k in ('experimental_validated','physical_validated','spatial_transport_validated','complete_device_energy'))


def test_explicit_training_gate_does_not_change_parameters_or_holdout_gate():
    data=manufactured();old=old_fit(data)
    report=current.calibrate_commercial_relaxation(data,training_relative_gate=.1)
    assert report['accepted'] and report['holdouts_accepted']
    assert {k:v for k,v in report.items() if k not in ADDED}==old


@pytest.mark.parametrize('kind',['base','failed_holdout','nonzero_origin','multiple_training_lengths'])
def test_all_old_report_fields_exact_on_valid_training(kind):
    data=traces()
    if kind=='failed_holdout':
        t=data[1];data[1]=replace(t,temperatures_K=350+4*np.exp(-(t.times_s-t.times_s[0])/1.3e-13))
    elif kind=='nonzero_origin':data=[replace(t,times_s=t.times_s+3e-12) for t in data]
    elif kind=='multiple_training_lengths':
        for carrier,tau in (('electrons',3e-13),('holes',2.5e-13)):
            t=next(t for t in data if t.carrier==carrier and t.role=='calibration')
            name=carrier+'replicate';times=np.linspace(0,1e-12,31)
            data.append(replace(t,case_id=name,source_sha256=hashlib.sha256(name.encode()).hexdigest(),
                times_s=times,temperatures_K=300+.4*np.exp(-times/tau)))
    before=current.calibrate_commercial_relaxation(data)
    assert {k:v for k,v in before.items() if k not in ADDED}==old_fit(data)
    assert before['accepted']==before['holdouts_accepted']
    assert len(before['training_checks'])==sum(t.role=='calibration' for t in data)
