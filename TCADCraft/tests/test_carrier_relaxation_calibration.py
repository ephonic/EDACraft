"""Recover relaxation times and reject leakage, unidentifiable data and bad units."""
from dataclasses import replace
import hashlib
import numpy as np
import pytest
from tcad.material.carrier_relaxation_calibration import CommercialDecayTrace,calibrate_commercial_relaxation


def traces():
    rows=[]
    for carrier,tau in [('electrons',3e-13),('holes',2.5e-13)]:
        for i,bath,amplitude in [(0,300.,2.),(1,350.,4.),(2,300.,.4)]:
            name=carrier+str(i);t=np.linspace(3e-14,1.03e-12,101)
            rows.append(CommercialDecayTrace(name,carrier,'calibration' if i==0 else 'holdout',t,
                bath+amplitude*np.exp(-(t-t[0])/tau),bath,hashlib.sha256(name.encode()).hexdigest(),'test-Silicon'))
    return rows


def test_recover_two_times_and_validate_whole_unseen_conditions():
    result=calibrate_commercial_relaxation(traces())
    assert result['holdouts_accepted'] and result['commercial_relaxation_calibrated']
    for c,tau in [('electrons',3e-13),('holes',2.5e-13)]:
        assert result['parameters'][c]['tau_s']==pytest.approx(tau,rel=1e-9)
        assert len(result['parameters'][c]['calibration_case_ids'])==1
    assert max(r['maximum_peak_normalized_error'] for r in result['holdouts'])<1e-10
    assert not result['experimental_validated'] and not result['spatial_transport_validated']
    assert not result['physical_validated'] and not result['complete_device_energy']


def test_holdout_slope_never_changes_calibration_and_bad_holdout_is_reported():
    data=traces();before=calibrate_commercial_relaxation(data)
    old=data[1];t=old.times_s
    data[1]=replace(old,temperatures_K=350+4*np.exp(-(t-t[0])/1.3e-13))
    after=calibrate_commercial_relaxation(data)
    assert after['parameters']==before['parameters']
    assert after['holdouts_accepted'] is False
    assert any(not h['accepted'] for h in after['holdouts'])


@pytest.mark.parametrize('change',[
    {'source_sha256':'a'},{'times_s':[0,0,1,2,3,4]},
    {'times_s':np.linspace(0,1,101).astype(complex)},
    {'times_s':np.ones(101,dtype=bool)}, {'temperatures_K':np.full(101,np.nan)},
    {'lattice_temperature_K':300+1j},{'lattice_temperature_K':True},
    {'role':'experiment'},{'carrier':'all'}, {'material_model':''}])
def test_bad_trace_input_rejected(change):
    with pytest.raises(ValueError):replace(traces()[0],**change)


@pytest.mark.parametrize('kind',['duplicate_source','duplicate_case','changed_material','no_holdout',
 'one_carrier','no_signal','flat','bound_fit'])
def test_unidentified_or_leaking_calibration_rejected(kind):
    data=traces();kwargs={}
    if kind=='duplicate_source':data[1]=replace(data[1],source_sha256=data[0].source_sha256)
    if kind=='duplicate_case':data[1]=replace(data[1],case_id=data[0].case_id)
    if kind=='changed_material':data[1]=replace(data[1],material_model='other')
    if kind=='no_holdout':data=[t for t in data if t.role=='calibration']
    if kind=='one_carrier':data=[t for t in data if t.carrier=='electrons']
    if kind=='no_signal':data[0]=replace(data[0],temperatures_K=300+.01*np.exp(-(data[0].times_s-3e-14)/3e-13))
    if kind=='flat':data[0]=replace(data[0],temperatures_K=np.full(101,302.))
    if kind=='bound_fit':kwargs['tau_bounds_s']=(1e-15,1e-13)
    with pytest.raises(ValueError):calibrate_commercial_relaxation(data,**kwargs)


def test_inputs_are_owned_readonly_and_not_rewritten_by_fit():
    data=traces();old=[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]
    calibrate_commercial_relaxation(data)
    assert old==[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]
    assert all(not t.times_s.flags.writeable and not t.temperatures_K.flags.writeable for t in data)
