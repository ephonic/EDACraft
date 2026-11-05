"""Envelope, equilibrium and multivalley controls for the new restricted mode."""
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pytest
from test_isolated_relaxation import solver
from test_three_temperature import BUDGET
from tcad.solver.isolated_relaxation import IsolatedThreeTemperatureRelaxation
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.physics.multivalley_thermionic import ThermionicValley


@pytest.mark.parametrize('temperatures',[(300,300,300),(260,270,300),(310,308,300),(280,290,305),(350,260,300)])
def test_original_extreme_negative_law_preserves_cold_hot_and_equilibrium_envelopes(temperatures):
    _,model,initial=solver()
    initial=replace(initial,electron_temperature_K=np.array([float(temperatures[0])]),
        hole_temperature_K=np.array([float(temperatures[1])]),temperature_K=np.array([float(temperatures[2])]))
    device=IsolatedThreeTemperatureRelaxation(model,initial)
    for _ in range(2):
        state,report=device.advance(2e-14,**BUDGET)
        assert report['independent_audit']['valid']
        assert min(temperatures)<=float(state.lattice_temperature_K)<=max(temperatures)
        for k,excess in enumerate((state.electron_excess_energy_J_m3,state.hole_excess_energy_J_m3)):
            valleys=(device.configuration.valleys_n,device.configuration.valleys_p)[k]
            U=lambda T:reference_reservoir(1e25,T,0.,valleys)['energy_density_J_m3']
            energy=U(float(state.lattice_temperature_K))+float(excess)
            assert U(min(temperatures))-1e-6<=energy<=U(max(temperatures))+1e-6
        if len(set(temperatures))==1:
            assert report['residual_evaluations']==1
            assert Decimal(state.electron_excess_energy_J_m3)==Decimal(state.hole_excess_energy_J_m3)==0


@pytest.mark.parametrize('temperatures',[(360,350,300),(320,330,360)])
def test_unrepresentable_final_tau_is_rejected_without_committing_or_clipping(temperatures):
    _,model,initial=solver()
    initial=replace(initial,electron_temperature_K=np.array([float(temperatures[0])]),
        hole_temperature_K=np.array([float(temperatures[1])]),temperature_K=np.array([float(temperatures[2])]))
    device=IsolatedThreeTemperatureRelaxation(model,initial);before=device.state
    with pytest.raises(ValueError,match='outside positive float64 range'):
        device.advance(2e-14,**BUDGET)
    assert device.state is before


def test_multivalley_offsets_distinct_densities_and_fixed_bands_close_independently():
    _,model,initial=solver(.6,-.2)
    model.valleys={'electrons':(ThermionicValley('a',2,.4,.5,.6),ThermionicValley('b',1,.8,.9,1.,1e-21,1e-21)),
                  'holes':(ThermionicValley('c',1,.7,.8,.9),ThermionicValley('d',2,1.,1.1,1.2,2e-21,2e-21))}
    model.Ec=np.array([2e-20]);model.Eh=np.array([3e-20])
    initial=replace(initial,n_m3=np.array([2e25]),p_m3=np.array([8e24]))
    device=IsolatedThreeTemperatureRelaxation(model,initial)
    for dt in (2e-14,5e-14):
        state,report=device.advance(dt,**BUDGET)
        assert report['independent_audit']['valid']
        assert float(state.density_n_m3)==2e25 and float(state.density_p_m3)==8e24
