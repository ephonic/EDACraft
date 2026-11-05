"""Export quantization must not alter the independent physical relaxation rate."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy,_reference_relaxation_times
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from test_three_temperature import case,BUDGET


def subnormal_case(sign=-1,deep=False,count=1):
    model,old=case(count=count,uniform=True)
    T=(310.9 if deep else 310.8) if sign<0 else (289.5 if deep else 289.6)
    model.relaxation_laws=(Law(150.,5e24,sign*20000.,0.,-sign*20000.),)*2
    old=replace(old,temperature_K=np.full(count,T),electron_temperature_K=np.full(count,T),hole_temperature_K=np.full(count,T))
    model._validate_state(old)
    return model,old


@pytest.mark.parametrize('sign',(-1,1))
@pytest.mark.parametrize('deep',(False,True))
@pytest.mark.parametrize('count',(1,2))
def test_actual_equilibrium_steps_accept_correctly_rounded_positive_subnormal_times(sign,deep,count):
    model,old=subnormal_case(sign,deep,count);device=DeviceThreeTemperature(model,old)
    for dt in (2e-14,5e-14):
        old=device.state;new,report=device.advance(dt,**BUDGET,max_nfev=1)
        assert report['independent_audit']['valid'] and report['nonlinear_statistics'][0]==1
        for s,f in (('electrons','n_m3'),('holes','p_m3')):
            k=0 if s=='electrons' else 1
            exact=_reference_relaxation_times((model.tau_n,model.tau_p)[k],getattr(new,f),new.temperature_K,new.temperature_K,model.relaxation_laws[k])
            given=report['cell_relaxation_time_s'][s]
            assert np.all((given>0)&(given<np.finfo(float).tiny))
            np.testing.assert_array_equal(given,exact.astype(float))
            assert np.max(abs(given.astype(np.longdouble)/exact-1))>1e-12
            np.testing.assert_array_equal(getattr(new,f),getattr(old,f))
        for f in ('temperature_K','electron_temperature_K','hole_temperature_K'):
            np.testing.assert_array_equal(getattr(new,f),getattr(old,f))
        assert not report['physical_validated'] and not report['complete_device_energy']


@pytest.mark.parametrize('sign',(-1,1))
@pytest.mark.parametrize('s',('electrons','holes'))
def test_forged_positive_subnormal_export_remains_rejected(sign,s):
    model,old=subnormal_case(sign);new,report=DeviceThreeTemperature(model,old).advance(2e-14,**BUDGET)
    bad=deepcopy(report);bad['cell_relaxation_time_s'][s]*=2
    audit=audit_three_temperature_energy(model,old,new,bad,**BUDGET)
    assert not audit['valid'] and audit['max_relaxation_relative_error']>.5


@pytest.mark.parametrize('sign',(-1,1))
def test_physical_exchange_uses_unrounded_reference_time_and_rejects_nonequilibrium_forgery(sign):
    model,old=subnormal_case(sign);new,report=DeviceThreeTemperature(model,old).advance(2e-14,**BUDGET)
    altered=replace(new,electron_temperature_K=new.electron_temperature_K+1e-5)
    audit=audit_three_temperature_energy(model,old,altered,report,**BUDGET)
    assert not audit['valid'] and audit['max_relaxation_relative_error']==0
    u=lambda T:reference_reservoir(new.n_m3[0],T,np.float64(0),model.valleys['electrons'])['energy_density_J_m3']
    delta=np.longdouble(u(altered.electron_temperature_K[0]))-np.longdouble(u(new.temperature_K[0]))
    tau=_reference_relaxation_times(model.tau_n,new.n_m3,altered.electron_temperature_K,new.temperature_K,model.relaxation_laws[0])[0]
    expected=float((new.time_s-old.time_s)*np.longdouble(model.vol[0])*delta/tau)
    rounded=float((new.time_s-old.time_s)*np.longdouble(model.vol[0])*delta/np.longdouble(float(tau)))
    actual=audit['independently_reconstructed_ledger']['carrier_exchange_to_lattice_J']['electrons']
    assert actual==expected and abs(actual/rounded-1)>1e-12


def test_independent_subnormal_reaudit_never_calls_native_physics_or_production_law(monkeypatch):
    model,old=subnormal_case();new,report=DeviceThreeTemperature(model,old).advance(2e-14,**BUDGET)
    def deny(*a,**k):raise AssertionError('production physics in independent audit')
    import tcad.core as public
    import tcad.core._bindings as native
    for module in (public,native):
        for name in dir(module):
            if name.startswith(('native_','three_temperature_')) and callable(getattr(module,name)):
                monkeypatch.setattr(module,name,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
