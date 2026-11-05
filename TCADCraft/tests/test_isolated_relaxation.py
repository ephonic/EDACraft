"""Stiff FD excess states retain unscaled BE residuals and strict scope."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from test_three_temperature import case,BUDGET
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.isolated_relaxation import IsolatedThreeTemperatureRelaxation
from tcad.postprocess.isolated_relaxation import audit_isolated_relaxation_step,audit_isolated_relaxation_initial


def solver(a=-20000.,c=20000.):
    model,old=case(count=1,uniform=True)
    model.relaxation_laws=(Law(150.,1e25/2,a,0,c),)*2
    return IsolatedThreeTemperatureRelaxation(model,old),model,old


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
def test_three_original_low_capacity_steps_pass_unscaled_independent_energy_gates(a,c,monkeypatch):
    device,model,initial=solver(a,c);assert model.capacity[0]==1000
    config=device.configuration;assert audit_isolated_relaxation_initial(config,device.state,energy_atol_J=1e-27)['valid']
    saved=[]
    for dt in (2e-14,5e-14,9e-14):
        old=device.state;new,report=device.advance(dt,**BUDGET)
        saved.append((old,new,report));assert device.state is new
        assert report['independent_audit']['valid'] and report['residual_evaluations']<=256
        assert new.density_n_m3==old.density_n_m3 and new.density_p_m3==old.density_p_m3
        assert not report['complete_device_energy'] and not report['physical_validated']
    if a<0:
        first=saved[0][1]
        assert abs(float(first.lattice_temperature_K)-302.9182948437794)<2e-6
        assert Decimal('1e-84')<abs(Decimal(first.electron_excess_energy_J_m3))<Decimal('1e-77')
        assert Decimal(first.hole_excess_energy_J_m3)<0
        assert min(map(Decimal,saved[0][2]['effective_relaxation_times_s']))<Decimal('1e-90')
    # Neither native kernels nor the production law may supply offline proof.
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('native or production law used by independent audit')
    for module in (public,native):
        for name in dir(module):
            if (name.startswith('native_') or name.startswith('three_temperature_')) and callable(getattr(module,name)):
                monkeypatch.setattr(module,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    for old,new,report in saved:
        assert audit_isolated_relaxation_step(config,old,new,report,**BUDGET)['valid']


@pytest.mark.parametrize('a,c',[(0.,0.),(.6,-.2),(-.4,.3)])
def test_resolved_constant_and_moderate_laws_match_general_native_device(a,c):
    from tcad.solver.device_three_temperature import DeviceThreeTemperature
    device,model,initial=solver(a,c);general=DeviceThreeTemperature(model,initial)
    for dt in (2e-14,5e-14):
        new,report=device.advance(dt,**BUDGET);other,reference=general.advance(dt,**BUDGET)
        assert abs(float(new.lattice_temperature_K)-other.temperature_K[0])<2e-6
        for k,label in enumerate(('electrons','holes')):
            assert abs(float(report['exchange_J'][k])-reference['cell_exchange_J'][label][0])<1e-25


@pytest.fixture(scope='module')
def stiff_step():
    device,_,_=solver();old=device.state;new,report=device.advance(2e-14,**BUDGET)
    return device.configuration,old,new,report


@pytest.mark.parametrize('damage',['drop_excess','double_excess','exchange','storage','lattice','local',
    'tau','density','clock','fingerprint','scope','backend','complete','validated','integrated','nan','coverage'])
def test_independent_audit_rejects_corrupted_split_state_and_reports(stiff_step,damage):
    config,old,new,source=stiff_step;report=deepcopy(source)
    if damage in ('drop_excess','double_excess'):
        value='0' if damage=='drop_excess' else str(Decimal(new.electron_excess_energy_J_m3)*2)
        new=replace(new,electron_excess_energy_J_m3=value)
        report['independent_audit']={'valid':True} # forged summary is ignored
    elif damage=='exchange':report['exchange_J'][0]='1e-20'
    elif damage=='storage':report['carrier_energy_increments_J'][0]='1e-20'
    elif damage=='lattice':report['lattice_energy_increment_J']='1e-20'
    elif damage=='local':report['energy_residuals_J'][0]='1e-20'
    elif damage=='tau':report['effective_relaxation_times_s'][0]=str(Decimal(report['effective_relaxation_times_s'][0])*2)
    elif damage=='density':new=replace(new,density_n_m3='2e25')
    elif damage=='clock':new=replace(new,time_s=new.time_s*2)
    elif damage=='fingerprint':report['configuration_sha256']='0'*64
    elif damage=='scope':report['scope']='complete_device'
    elif damage=='backend':report['execution_backend']='python'
    elif damage=='complete':report['complete_device_energy']=True
    elif damage=='validated':report['physical_validated']=True
    elif damage=='integrated':report['main_DeviceSimulator_integrated']=True
    elif damage=='nan':report['exchange_J'][0]='NaN'
    elif damage=='coverage':report['exchange_J']=[]
    try:valid=audit_isolated_relaxation_step(config,old,new,report,**BUDGET)['valid']
    except ValueError:valid=False
    assert not valid


@pytest.mark.parametrize('option',['cells','contacts','bath','band','generation','exchange','trap','radiation','auger','b'])
def test_unsupported_physics_is_rejected_instead_of_silently_omitted(option):
    model,old=case(count=2 if option=='cells' else 1,uniform=True,contacts=option=='contacts')
    if option=='bath':model.bath={0:300.}
    elif option=='band':model.band_temperature_slopes=(np.ones(model.nc)*1e-24,np.zeros(model.nc))
    elif option=='generation':model.pair_generation_rate_m3_s=np.ones(model.nc)
    elif option=='exchange':model.intercarrier_conductance_W_m3_K=np.ones(model.nc)
    elif option=='trap':model.trap_capture_law='configured'
    elif option=='radiation':model.radiative_law='configured'
    elif option=='auger':model.auger_events=((),)
    elif option=='b':model.relaxation_laws=(Law(300.,1e25,0,1,0),None)
    with pytest.raises(ValueError):IsolatedThreeTemperatureRelaxation(model,old)


def test_budget_failure_and_independent_audit_failure_leave_state_unchanged(monkeypatch):
    device,_,_=solver();old=device.state
    with pytest.raises(RuntimeError,match='budget exhausted'):device.advance(2e-14,max_nfev=1,**BUDGET)
    assert device.state is old
    import tcad.postprocess.isolated_relaxation as audit
    with monkeypatch.context() as patch:
        patch.setattr(audit,'audit_isolated_relaxation_step',lambda *a,**k:dict(valid=False))
        with pytest.raises(ValueError,match='independent audit failed'):device.advance(2e-14,**BUDGET)
    assert device.state is old
    retried,report=device.advance(2e-14,**BUDGET);fresh,_,_=solver();expected,_=fresh.advance(2e-14,**BUDGET)
    assert retried==expected and report['independent_audit']['valid']


def test_configuration_and_state_are_immutable_and_detached_from_source():
    from dataclasses import FrozenInstanceError
    device,model,initial=solver();fingerprint=device.configuration.sha256
    model.relaxation_laws=(None,None)
    assert device.configuration.sha256==fingerprint
    with pytest.raises(FrozenInstanceError):device.state.lattice_temperature_K='301'
    with pytest.raises(FrozenInstanceError):device.configuration.parameters=()


@pytest.mark.parametrize('budget',[True,1.5,0,-1])
def test_raw_integer_evaluation_budget_contract(budget):
    device,_,_=solver()
    from tcad.core._bindings import native_isolated_relaxation_raw
    with pytest.raises((ValueError,RuntimeError)):
        native_isolated_relaxation_raw(device.state.raw(),[*device.configuration.parameters,'2e-14','1e-27'],
            *device.configuration.packed_valleys(),max_nfev=budget)
