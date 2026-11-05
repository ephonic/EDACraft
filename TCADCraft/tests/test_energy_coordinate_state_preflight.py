"""Functional states obey the same rounded temperature contract as restart."""
from dataclasses import replace
import numpy as np
import pytest
import tcad.core._bindings as native
from test_energy_coordinate_transport import transport_case,BUDGET
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device


@pytest.mark.parametrize('count,cell',[(1,0),(2,0),(2,1)])
@pytest.mark.parametrize('field',['electron_temperature_K','hole_temperature_K'])
@pytest.mark.parametrize('delta',['ulp_up','ulp_down','kelvin_up','kelvin_down'])
def test_inconsistent_view_rejects_before_transport_and_matches_restart(monkeypatch,count,cell,field,delta):
    model,initial=transport_case(count)
    old=initialize_energy_coordinates(model,initial)
    values=getattr(old.thermal,field).copy()
    values[cell]=(np.nextafter(values[cell],np.inf if delta=='ulp_up' else -np.inf)
                  if delta.startswith('ulp') else values[cell]+(1 if delta=='kelvin_up' else -1))
    bad=replace(old,thermal=replace(old.thermal,**{field:values}))
    before=(old.thermal.n_m3.tobytes(),getattr(old.thermal,field).tobytes(),old.excess_J_m3)
    def deny(*a,**k):raise AssertionError('transport solve reached for inconsistent initial view')
    with monkeypatch.context() as patch:
        patch.setattr(native,'native_energy_coordinate_transport_raw',deny)
        with pytest.raises(ValueError,match='initial thermal view'):
            energy_coordinate_step(model,bad,2e-14,**BUDGET)
    with pytest.raises(ValueError,match='initial thermal view'):Device(model,bad)
    assert before==(old.thermal.n_m3.tobytes(),getattr(old.thermal,field).tobytes(),old.excess_J_m3)


@pytest.mark.parametrize('species',[0,1])
@pytest.mark.parametrize('energy',['1e10','-1e10'])
def test_energy_outside_temperature_domain_rejects_before_transport(monkeypatch,species,energy):
    model,initial=transport_case(count=1)
    old=initialize_energy_coordinates(model,initial);values=list(old.excess_J_m3);values[species]=energy
    bad=replace(old,excess_J_m3=tuple(values))
    def deny(*a,**k):raise AssertionError('transport solve reached for out-of-domain energy')
    monkeypatch.setattr(native,'native_energy_coordinate_transport_raw',deny)
    with pytest.raises(ValueError):energy_coordinate_step(model,bad,2e-14,**BUDGET)


def test_configuration_rejection_precedes_native_temperature_decoding(monkeypatch):
    model,initial=transport_case(count=1)
    old=initialize_energy_coordinates(model,initial);model.capacity[0]*=2
    def deny(*a,**k):raise AssertionError('native call reached for changed configuration')
    monkeypatch.setattr(native,'native_fermi_energy_coordinates_raw',deny)
    monkeypatch.setattr(native,'native_energy_coordinate_transport_raw',deny)
    with pytest.raises(ValueError,match='configuration changed'):
        energy_coordinate_step(model,old,2e-14,**BUDGET)


@pytest.mark.parametrize('energy',['0','-0','1e-120','-1e-120','1e-4965','-1e-4965'])
def test_same_temperature_tiny_energy_is_not_reconstructed_or_erased(monkeypatch,energy):
    model,initial=transport_case(count=1,a=0,c=0)
    thermal=replace(initial,electron_temperature_K=initial.temperature_K,hole_temperature_K=initial.temperature_K)
    old=replace(initialize_energy_coordinates(model,thermal),excess_J_m3=(energy,energy))
    # Inspect the actual argument at the transport boundary, after real EOS decoding.
    class ReachedTransport(Exception):pass
    def inspect(*args,**kwargs):
        assert args[6] is old.excess_J_m3 and args[6]==(energy,energy)
        raise ReachedTransport
    monkeypatch.setattr(native,'native_energy_coordinate_transport_raw',inspect)
    with pytest.raises(ReachedTransport):energy_coordinate_step(model,old,2e-14,**BUDGET)
    assert old.excess_J_m3==(energy,energy)


@pytest.mark.parametrize('field',['n_m3','p_m3','temperature_K'])
def test_thermodynamic_inputs_cannot_change_with_an_outdated_temperature_view(monkeypatch,field):
    model,initial=transport_case(count=1)
    old=initialize_energy_coordinates(model,initial);values=getattr(old.thermal,field).copy();values[0]*=1.01
    bad=replace(old,thermal=replace(old.thermal,**{field:values}))
    def deny(*a,**k):raise AssertionError('transport solve reached for inconsistent thermodynamic state')
    monkeypatch.setattr(native,'native_energy_coordinate_transport_raw',deny)
    with pytest.raises(ValueError,match='initial thermal view'):
        energy_coordinate_step(model,bad,2e-14,**BUDGET)


def test_consistent_retry_after_rejection_matches_fresh_step_exactly():
    model,initial=transport_case(count=1)
    old=initialize_energy_coordinates(model,initial)
    bad=replace(old,thermal=replace(old.thermal,electron_temperature_K=old.thermal.electron_temperature_K+1))
    with pytest.raises(ValueError,match='initial thermal view'):energy_coordinate_step(model,bad,2e-14,**BUDGET)
    actual,report=energy_coordinate_step(model,old,2e-14,**BUDGET)
    expected,reference=energy_coordinate_step(model,initialize_energy_coordinates(model,initial),2e-14,**BUDGET)
    assert report==reference and actual.excess_J_m3==expected.excess_J_m3
    for field in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(actual.thermal,field),getattr(expected.thermal,field))
