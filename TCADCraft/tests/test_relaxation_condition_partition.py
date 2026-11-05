"""Whole-condition a/c holdouts cannot be created by renaming a trace."""
from dataclasses import replace
import hashlib
import numpy as np
import pytest
from test_multicondition_relaxation_calibration import traces,fit
from test_temperature_relaxation_calibration import analytic
from tcad.material import multicondition_relaxation_calibration as module


def cooling(trace,Tl,density,*,excess=290.,times=None):
    tau,a,b,c=(3e-13,.6,1,-.2) if trace.carrier=='electrons' else (2.5e-13,-.4,2,.3)
    time=trace.times_s if times is None else times
    effective=tau*(Tl/300.)**a*(density/1e22)**c
    return replace(trace,lattice_temperature_K=Tl,density_m3=density,times_s=time,
        temperatures_K=analytic(time,Tl+excess,Tl,effective,b))


def reused(data,index,variant):
    held=data[index];source=data[index-4]
    if variant=='renamed_export':return replace(held,lattice_temperature_K=source.lattice_temperature_K,
        density_m3=source.density_m3,times_s=source.times_s,temperatures_K=source.temperatures_K)
    time=held.times_s
    if variant=='different_clock':time=np.linspace(time[0],time[-1],37)
    if variant=='different_origin':time=time+4e-14
    return cooling(held,source.lattice_temperature_K,source.density_m3,times=time)


@pytest.mark.parametrize('index',[4,9])
@pytest.mark.parametrize('variant',['renamed_export','different_initial_temperature','different_clock','different_origin'])
def test_same_ac_condition_rejected_before_optimization(index,variant,monkeypatch):
    data=traces();data[index]=reused(data,index,variant)
    assert len({t.case_id for t in data})==len(data)
    assert len({t.source_sha256 for t in data})==len(data)
    def forbidden(*a,**kw):raise AssertionError('leaking conditions reached optimizer')
    monkeypatch.setattr(module,'least_squares',forbidden)
    with pytest.raises(ValueError,match='condition crosses calibration/holdout roles'):fit(data)


@pytest.mark.parametrize('index',[0,1,2,3,5,6,7,8])
def test_electron_and_hole_roles_cannot_split_one_condition(index,monkeypatch):
    data=traces();data[index]=replace(data[index],role='holdout')
    def forbidden(*a,**kw):raise AssertionError('cross-species leakage reached optimizer')
    monkeypatch.setattr(module,'least_squares',forbidden)
    with pytest.raises(ValueError,match='condition crosses calibration/holdout roles'):fit(data)


@pytest.mark.parametrize('Tl,density',[(400.,5e21),(350.,2e21)])
def test_a_new_pair_may_share_one_training_coordinate(Tl,density):
    data=traces()
    for index in (4,9):data[index]=cooling(data[index],Tl,density)
    assert fit(data)['fit_accepted']


@pytest.mark.parametrize('index',[0,4])
def test_repeated_measurements_stay_in_their_existing_role(index):
    data=traces();name='extra-'+data[index].case_id
    data.append(replace(data[index],case_id=name,source_sha256=hashlib.sha256(name.encode()).hexdigest()))
    result=fit(data);assert result['fit_accepted']
    groups=result['whole_condition_partition']['groups']
    group=next(g for g in groups if name in g['case_ids'])
    assert group['role']==data[index].role and len(group['case_ids'])==3


def test_report_retains_supplied_whole_condition_membership_without_certifying_it():
    result=fit(traces());partition=result['whole_condition_partition']
    assert result['whole_condition_holdout_checked'] and partition['grouped_across_carriers']
    assert partition['condition_axes']==['lattice_temperature_K','density_m3']
    assert partition['initial_temperature_and_clock_do_not_define_new_ac_condition']
    assert len(partition['groups'])==5
    assert all(g['carriers']==['electrons','holes'] and len(g['case_ids'])==2 for g in partition['groups'])
    held=[g for g in partition['groups'] if g['role']=='holdout']
    assert len(held)==1 and held[0]['lattice_temperature_K']==350. and held[0]['density_m3']==5e21
    assert not result['experimental_validated'] and not result['physical_validated']
    assert not result['provenance_authenticated'] and not result['state_dependent_relaxation_calibrated']


def test_group_membership_is_independent_of_trace_order():
    data=traces()
    assert fit(data)['whole_condition_partition']==fit(list(reversed(data)))['whole_condition_partition']


def test_unpaired_held_conditions_do_not_invent_missing_carrier_measurements():
    data=traces();data[9]=cooling(data[9],350.,4e21)
    result=fit(data);assert result['fit_accepted']
    held=[g for g in result['whole_condition_partition']['groups'] if g['role']=='holdout']
    assert len(held)==2 and all(len(g['carriers'])==1 for g in held)
    assert not result['experimental_validated']


def test_condition_partition_does_not_change_frozen_trace_arrays():
    data=traces();before=[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]
    fit(data)
    assert before==[(t.times_s.tobytes(),t.temperatures_K.tobytes()) for t in data]
    assert all(not t.times_s.flags.writeable and not t.temperatures_K.flags.writeable for t in data)
