"""Independent kinetic-energy BE roots and rejection/rollback controls."""
from copy import deepcopy
import numpy as np
import pytest
from scipy.optimize import brentq
from test_band_trial_domain import boundary_case,BUDGET,DeviceThreeTemperature
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.core._bindings import native_three_temperature_dispatch_raw


def independent_temperatures(model,old,dt):
    n=[float(old.n_m3[0]),float(old.p_m3[0])]
    labels=('electrons','holes');tau=[model.tau_n[0],model.tau_p[0]]
    initial=[old.electron_temperature_K[0],old.hole_temperature_K[0]]
    def kinetic(k,T):
        return reference_reservoir(n[k],T,0.,model.valleys[labels[k]])['energy_density_J_m3']
    before=[kinetic(k,initial[k]) for k in range(2)]
    def targets(T):return [(before[k]+dt/tau[k]*kinetic(k,T))/(1+dt/tau[k]) for k in range(2)]
    def band_increment(k,T):
        alpha=model.band_varshni_alpha[k][0];beta=model.band_varshni_beta[k][0]
        slope=model.band_temperature_slopes[k][0];r=old.temperature_K[0]
        return (T-r)*slope-alpha*(T*T/(T+beta)-r*r/(r+beta))
    def balance(T):
        return model.capacity[0]*(T-old.temperature_K[0])+sum(n[k]*band_increment(k,T)+u-before[k] for k,u in enumerate(targets(T)))
    low,high=min(initial),old.temperature_K[0]
    assert balance(low)<0<balance(high)
    Tl=brentq(balance,low,high,xtol=1e-12)
    result=[brentq(lambda T:kinetic(k,T)-target,min(initial[k],Tl),max(initial[k],Tl),xtol=1e-12)
        for k,target in enumerate(targets(Tl))]
    return result+[Tl]


@pytest.mark.parametrize('kind',('gap','capacity'))
def test_new_accepted_state_matches_independent_FD_kinetic_root(kind):
    model,old=boundary_case(kind);new,report=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    expected=independent_temperatures(model,old,2e-13)
    np.testing.assert_allclose([new.electron_temperature_K[0],new.hole_temperature_K[0],new.temperature_K[0]],expected,rtol=0,atol=3e-6)
    np.testing.assert_array_equal(new.n_m3,old.n_m3);np.testing.assert_array_equal(new.p_m3,old.p_m3)


@pytest.mark.parametrize('kind',('gap','capacity'))
@pytest.mark.parametrize('budget',(1,3,10))
def test_shortened_probes_still_consume_original_budget_and_rollback(kind,budget):
    model,old=boundary_case(kind);device=DeviceThreeTemperature(model,old)
    accepted=device.state;before=deepcopy(device.native_state())
    with pytest.raises(RuntimeError,match='evaluation budget exhausted'):
        device.advance(2e-13,**BUDGET,max_nfev=budget)
    assert device.state is accepted and device.native_state()==before and device._pending_token is None
    a,_=device.advance(2e-13,**BUDGET);b,_=DeviceThreeTemperature(model,old).advance(2e-13,**BUDGET)
    for field in ('n_m3','p_m3','trap_fraction','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(a,field),getattr(b,field))


@pytest.mark.parametrize('kind',('gap','capacity'))
def test_invalid_initial_constitutive_state_remains_rejected_public_and_native(kind):
    model,old=boundary_case(kind)
    if kind=='gap':model.Eh=-model.Ec.copy()
    else:model.band_varshni_alpha=tuple(a*2 for a in model.band_varshni_alpha)
    with pytest.raises(ValueError,match='gap|capacity'):model.step(old,2e-13,**BUDGET)
    with pytest.raises(ValueError,match='gap|capacity'):
        native_three_temperature_dispatch_raw(*pack_three_temperature_inputs(model,old,2e-13,**BUDGET),600)
