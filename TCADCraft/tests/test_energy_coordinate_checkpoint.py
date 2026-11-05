"""Reject erased coordinates before solving; retain native subnormal identity."""
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from test_fermi_energy_coordinates import PACKED
from test_device_energy_coordinate_transport import assert_owned
from tcad.core._bindings import PyDeviceSimulator,native_fermi_energy_coordinates_raw as raw,native_energy_coordinate_transport_raw
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,EnergyCoordinateState,_pack
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.postprocess.native_energy_identity import same_native_energy,_binary128_key
from tcad.physics.native_energy_encoding import native_energy_literal


@pytest.fixture(scope='module')
def checkpoint():
    model,thermal=transport_case(count=1)
    thermal=replace(thermal,electron_temperature_K=thermal.temperature_K,hole_temperature_K=thermal.temperature_K)
    return model,initialize_energy_coordinates(model,thermal)


@pytest.mark.parametrize('value',['1e-6000','-1e-6000','1e-4966','-1e-4966',
    '1e6000','-1e6000','1e999999999','1e-999999999','nan','inf','sNaN',
    '',' ',' 1','1 ','1_0','１２','0x1p-100','1e','1\x00'])
def test_invalid_checkpoint_rejects_before_native_configuration(checkpoint,monkeypatch,value):
    model,initial=checkpoint
    def deny(*a,**k):raise AssertionError('invalid checkpoint reached native configuration')
    monkeypatch.setattr('tcad.core._bindings.PyDeviceSimulator',deny)
    with pytest.raises(ValueError,match='native-range'):
        Device(model,replace(initial,excess_J_m3=(value,'0')))


@pytest.mark.parametrize('value',['1e-6000','-1e-6000','1e-4966','-1e-4966','1e6000','-1e6000'])
def test_raw_EOS_and_transport_reject_erasure_before_native_solve(checkpoint,value):
    model,initial=checkpoint
    with pytest.raises(ValueError):raw(['1e25','300',value,'0'],PACKED)
    packed,_=_pack(model,initial.thermal,2e-14,**BUDGET)
    # max_nfev=1 would fail the solve: invalid coordinate parsing must come first.
    with pytest.raises(ValueError):native_energy_coordinate_transport_raw(*packed,(value,'0'),1)


@pytest.mark.parametrize('value',['1e-6000','-1e-6000','1e-4966','1e6000'])
def test_invalid_native_configuration_leaves_session_retryable(checkpoint,value):
    model,initial=checkpoint;packed,_=_pack(model,initial.thermal,1.,**BUDGET)
    backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_energy_coordinate(*packed,(value,'0'),0.)
    backend.configure_energy_coordinate(*packed,initial.excess_J_m3,0.)
    assert backend.energy_coordinate_state()['raw']['excess']==list(initial.excess_J_m3)


@pytest.mark.parametrize('value',['4e-4966','-4e-4966','1e-4950','-1e-4950','1e-4932','-1e-4932',
    '0','-0','0e-999999999','-0e999999999','.0','+1.00e-120'])
def test_representable_subnormals_and_exact_zero_restart_without_energy_erasure(checkpoint,value):
    model,initial=checkpoint;initial=replace(initial,excess_J_m3=(value,'-'+value if value[0].isdigit() else value))
    # The second coordinate may share the first sign; identity, not sign symmetry,
    # is the restart contract checked here.
    device=Device(model,initial);assert_owned(device)
    for source,stored in zip(initial.excess_J_m3,device.state.excess_J_m3):
        assert same_native_energy(source,stored)
        assert bool(Decimal(source))==bool(Decimal(stored))
    assert np.array_equal(device.state.thermal.electron_temperature_K,initial.thermal.temperature_K)
    restarted=Device(model,device.state)
    assert restarted.state.excess_J_m3==device.state.excess_J_m3
    assert restarted.native_state()==device.native_state()


@pytest.mark.parametrize('damage',['erasure','adjacent','missing'])
def test_restart_rejects_changed_native_authoritative_energy(checkpoint,monkeypatch,damage):
    model,initial=checkpoint;initial=replace(initial,excess_J_m3=('1e-120','-1e-120'))
    real=PyDeviceSimulator
    class Damaged:
        def __init__(self,*a):self.native=real(*a)
        def configure_energy_coordinate(self,*a):return self.native.configure_energy_coordinate(*a)
        def energy_coordinate_state(self):
            result=self.native.energy_coordinate_state();values=result['raw']['excess']
            if damage=='erasure':values[0]='0'
            elif damage=='adjacent':values[0]='1.000000000000000000000000000000001e-120'
            else:values.pop()
            return result
    monkeypatch.setattr('tcad.core._bindings.PyDeviceSimulator',Damaged)
    with pytest.raises(ValueError,match='authoritative|two signed'):Device(model,initial)


def test_exact_subnormal_midpoints_and_overflow_boundary(checkpoint):
    model,initial=checkpoint
    with localcontext() as context:
        context.prec=20000
        q=Decimal(2)**-16494;half=q/2
        # Exact tie rounds to even zero and must be refused as nonzero input.
        for value in (half,-half,half-Decimal(10)**-17000):
            text=str(value)
            assert not same_native_energy(text,text)
            with pytest.raises(ValueError):replace(initial,excess_J_m3=(text,'0'))
            with pytest.raises(ValueError):raw(['1e25','300',text,'0'],PACKED)
        for source,expected in ((q,q),(half+Decimal(10)**-17000,q),(q+half,2*q),(-q-half,-2*q)):
            text=str(source);result=raw(['1e25','300',text,'0'],PACKED)
            assert same_native_energy(result[2],str(expected))
            assert _binary128_key(result[2])==_binary128_key(text)
            replace(initial,excess_J_m3=(text,'0'))
        for k in (3,5,7,9,-3,-5,-7,-9):
            source=q*k/2
            even=round(Decimal(k)/2)
            result=raw(['1e25','300',str(source),'0'],PACKED)
            assert same_native_energy(result[2],str(q*even))
        maximum=(2-Decimal(2)**-112)*Decimal(2)**16383
        replace(initial,excess_J_m3=(str(maximum),'0'))
        overflow=maximum+Decimal(2)**16270
        assert not same_native_energy(str(overflow),str(overflow))
        with pytest.raises(ValueError):replace(initial,excess_J_m3=(str(overflow),'0'))


def test_decimal_exponent_limits_do_not_construct_unbounded_integers():
    for value in ('1e999999999','1e-999999999','-1e999999999','-1e-999999999'):
        assert not same_native_energy(value,value)
    assert same_native_energy('0e999999999','-0e-999999999')


@pytest.mark.parametrize('source',['1e-120','-1e-120','4e-4966','-4e-4966','+0','-0'])
def test_native_literal_identity_does_not_depend_on_Decimal_context(source):
    expected=_binary128_key(source)
    with localcontext() as context:
        context.prec=3
        encoded=native_energy_literal(source)
    if expected==(0,0):
        assert encoded==('-0' if Decimal(source).is_signed() else '0')
    else:
        integer,exponent=encoded.split('p')
        assert (int(integer,16),int(exponent))==expected
