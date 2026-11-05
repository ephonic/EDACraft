"""Domain safeguards preserve the original low-capacity model and budgets."""
from copy import deepcopy
import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.special import expit
from test_three_temperature import case,BUDGET
from test_device_three_temperature import assert_owned
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.postprocess.three_temperature_energy import audit_three_temperature_energy

def reference_step(model,old,dt):
    labels=('electrons','holes');initial=(old.electron_temperature_K[0],old.hole_temperature_K[0])
    def U(T,label):return reference_reservoir(float(old.n_m3[0]),T,0.,model.valleys[label])['energy_density_J_m3']
    before=np.array([U(T,label) for T,label in zip(initial,labels)])
    def target(Tl):
        weights=expit(np.log(dt)-np.log([1e-13,4e-13])-20000*np.log(Tl/300.))
        return (1-weights)*before+weights*np.array([U(Tl,label) for label in labels])
    def balance(Tl):return model.capacity[0]*(Tl-old.temperature_K[0])+sum(target(Tl)-before)
    lower=min(*initial,old.temperature_K[0]);upper=max(*initial,old.temperature_K[0])
    lattice=brentq(balance,lower,upper,xtol=5e-13)
    energies=target(lattice)
    carriers=[brentq(lambda T:U(T,label)-energy,min(T0,lattice),max(T0,lattice),xtol=5e-13)
        for label,energy,T0 in zip(labels,energies,initial)]
    return [*carriers,lattice]

def test_original_positive_exponent_low_capacity_three_steps_match_independent_BE_roots(monkeypatch):
    model,old=case(count=1,uniform=True);assert model.capacity[0]==1e3
    model.relaxation_laws=(Law(150.,1e25/2,20000,0,-20000),)*2
    device=DeviceThreeTemperature(model,old);saved=[]
    for dt in (2e-14,5e-14,9e-14):
        expected=reference_step(model,old,dt);new,report=device.advance(dt,**BUDGET)
        np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],
            expected,rtol=0,atol=2e-6)
        assert report['independent_audit']['valid'] and report['nonlinear_statistics'][0]<=600
        assert_owned(device,new);saved.append((old,new,report));old=new
    import tcad.core as public
    import tcad.core._bindings as native
    def deny(*a,**k):raise AssertionError('native or production law used in independent audit')
    for module in (public,native):
        for key in dir(module):
            if (key.startswith('native_') or key.startswith('three_temperature_')) and callable(getattr(module,key)):
                monkeypatch.setattr(module,key,deny)
    monkeypatch.setattr(Law,'evaluate',deny)
    for old,new,report in saved:
        assert audit_three_temperature_energy(model,old,new,report,**BUDGET)['valid']
        assert not report['complete_device_energy'] and not report['physical_validated']

def test_unresolved_negative_exponent_stiff_state_is_never_committed_or_clipped():
    model,old=case(count=1,uniform=True)
    model.relaxation_laws=(Law(150.,1e25/2,-20000,0,20000),)*2
    device=DeviceThreeTemperature(model,old);before=deepcopy(device.native_state())
    with pytest.raises(RuntimeError,match='line search failed physical budgets'):
        device.advance(2e-14,**BUDGET)
    assert str(device.native_state())==str(before);assert_owned(device,device.state)
    assert device.state.time_s==0
