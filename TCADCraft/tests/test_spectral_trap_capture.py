"""Independent DOS moments, thermal balance, source conservation and guards."""
from dataclasses import replace,FrozenInstanceError
import math
import numpy as np
import pytest
from scipy.special import expit
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.physics.spectral_trap_capture import SpectralTrapState,spectral_trap_capture,_valley_decimals
from tcad.physics.native_fermi_local import _decimal,native_fermi_reservoirs
from tcad.postprocess.spectral_trap_capture import reference_trap_capture,audit_spectral_trap_capture
from tcad.core._bindings import native_spectral_trap_capture_raw

Q=1.602176634e-19;KB=1.380649e-23
VN=(ThermionicValley('n0',2.,.19,.92,.19),
    ThermionicValley('n1',1.,.4,.6,.8,.07*Q,.07*Q))
VP=(ThermionicValley('p0',1.,.49,.49,.49),)


def state(**kw):
    base=SpectralTrapState(700.,430.,300.,.52*Q,.35*Q,.6*Q,.5*Q,2e22,.04*Q,3e-14,8e-15,.37)
    return replace(base,**kw)


@pytest.mark.parametrize('eta',[-25.,-3.,2.,35.,200.])
@pytest.mark.parametrize('ratio',[.01,1.,100.])
def test_independent_infinite_tail_DOS_and_separate_moments(eta,ratio):
    s=state(temperature_n_K=300.*ratio,mu_n_J=.6*Q+eta*KB*300.*ratio,
            temperature_p_K=500.,mu_p_J=.5*Q+eta*KB*500.)
    out=spectral_trap_capture(s,VN,VP)
    audit=audit_spectral_trap_capture(s,VN,VP,out)
    assert audit['valid'],audit
    assert out['entropy_production_W_m3_K']>=0
    activity=max(out['capture_n_m3_s'],out['emission_n_m3_s'],out['capture_p_m3_s'],out['emission_p_m3_s'])
    power=max(out['capture_energy_n_W_m3'],out['emission_energy_n_W_m3'],out['capture_energy_p_W_m3'],out['emission_energy_p_W_m3'])
    assert abs(out['total_energy_source_W_m3'])<=3e-15*power
    assert abs(out['total_charge_source_C_m3_s'])<=3e-15*Q*activity
    assert not out['device_coupled'] and not out['material_calibrated']


@pytest.mark.parametrize('T,mu',[(120.,-.04*Q),(300.,.03*Q),(1500.,.1*Q),(3000.,-.2*Q)])
def test_equilibrium_detailed_balance_both_carriers_and_energy(T,mu):
    f=expit((mu-.04*Q)/(KB*T))
    s=state(temperature_n_K=T,temperature_p_K=T,temperature_l_K=T,
            mu_n_J=mu,mu_p_J=-mu,occupancy=f)
    out=spectral_trap_capture(s,VN,VP)
    for c in ('n','p'):
        gross=max(out['capture_'+c+'_m3_s'],out['emission_'+c+'_m3_s'])
        assert abs(out['net_capture_'+c+'_m3_s'])<2e-12*gross
        assert abs(out[c=='n' and 'electron_energy_source_W_m3' or 'hole_energy_source_W_m3'])<2e-12*gross*Q
    assert audit_spectral_trap_capture(s,VN,VP,out)['valid']


@pytest.mark.parametrize('mu_n,mu_p,f',[(.7*Q,.6*Q,.1),(-.4*Q,-.4*Q,.9),(.7*Q,-.4*Q,.8),(-.4*Q,.6*Q,.2)])
def test_capture_and_reverse_emission_directions_with_unequal_rates(mu_n,mu_p,f):
    s=state(mu_n_J=mu_n,mu_p_J=mu_p,occupancy=f,temperature_n_K=300.,temperature_p_K=300.)
    o=spectral_trap_capture(s,VN,VP)
    assert math.copysign(1,o['net_capture_n_m3_s'])==math.copysign(1,mu_n)
    assert math.copysign(1,o['net_capture_p_m3_s'])==math.copysign(1,mu_p)
    assert o['net_capture_n_m3_s']!=o['net_capture_p_m3_s']
    assert audit_spectral_trap_capture(s,VN,VP,o)['valid']


@pytest.mark.parametrize('delta',[-2.*Q,.2*Q,3.*Q])
def test_material_reference_shift_moves_trap_storage_and_preserves_heat(delta):
    s=state();a=spectral_trap_capture(s,VN,VP)
    t=replace(s,Ec_J=s.Ec_J+delta,Eh_J=s.Eh_J-delta,mu_n_J=s.mu_n_J+delta,
              mu_p_J=s.mu_p_J-delta,trap_level_J=s.trap_level_J+delta)
    b=spectral_trap_capture(t,VN,VP)
    for name in ('net_capture_n_m3_s','net_capture_p_m3_s','occupancy_source_s',
                 'lattice_heat_W_m3','entropy_production_W_m3_K'):
        np.testing.assert_allclose(a[name],b[name],rtol=2e-13,atol=0.)
    np.testing.assert_allclose(b['trap_energy_source_W_m3']-a['trap_energy_source_W_m3'],
        delta*s.trap_density_m3*a['occupancy_source_s'],rtol=2e-13)
    assert audit_spectral_trap_capture(t,VN,VP,b)['valid']


def test_each_valley_offset_is_included_in_density_and_energy():
    s=state(mu_n_J=.8*Q)
    out=spectral_trap_capture(s,VN,VP)
    reference=reference_trap_capture(s,VN,VP)
    np.testing.assert_allclose(out['density_n_m3'],reference['density_n_m3'],rtol=3e-10)
    density=out['density_n_m3']
    reservoir=native_fermi_reservoirs([density],[s.temperature_n_K],[s.Ec_J],VN)[0]
    np.testing.assert_allclose(reservoir['chemical_potential_J'],s.mu_n_J,rtol=2e-13)


def test_final_state_Pauli_blocking_cannot_be_replaced_by_one():
    s=state(mu_n_J=.9*Q,temperature_n_K=300.)
    out=spectral_trap_capture(s,VN,VP)
    # A very empty electron reservoir has negligible blocking. At fixed Tl,
    # f and trap energy, the degenerate reservoir suppresses electron emission.
    dilute=spectral_trap_capture(replace(s,mu_n_J=-.2*Q),VN,VP)
    assert out['emission_n_m3_s']<dilute['emission_n_m3_s']*1e-3
    assert out['capture_n_m3_s']>dilute['capture_n_m3_s']


def test_energy_moments_include_capture_and_emission_spectra_separately():
    s=state(mu_n_J=.7*Q,temperature_n_K=1200.,temperature_l_K=80.)
    out=spectral_trap_capture(s,VN,VP)
    mean_capture=out['capture_energy_n_W_m3']/out['capture_n_m3_s']
    mean_emission=out['emission_energy_n_W_m3']/out['emission_n_m3_s']
    assert mean_capture-mean_emission>.05*Q
    assert audit_spectral_trap_capture(s,VN,VP,out)['valid']


@pytest.mark.parametrize('kw',[dict(trap_density_m3=0.),dict(capture_n_m3_s=0.,capture_p_m3_s=0.),
                              dict(capture_n_m3_s=0.),dict(capture_p_m3_s=0.)])
def test_zero_channels_retain_DOS_and_disable_only_requested_process(kw):
    s=state(**kw);out=spectral_trap_capture(s,VN,VP)
    assert out['density_n_m3']>0 and out['density_p_m3']>0
    assert audit_spectral_trap_capture(s,VN,VP,out)['valid']
    if s.trap_density_m3==0 or s.capture_n_m3_s==0:assert out['capture_n_m3_s']==out['emission_n_m3_s']==0.
    if s.trap_density_m3==0 or s.capture_p_m3_s==0:assert out['capture_p_m3_s']==out['emission_p_m3_s']==0.


@pytest.mark.parametrize('field',[
 'capture_n_m3_s','emission_n_m3_s','capture_energy_n_W_m3','net_capture_p_m3_s',
 'electron_number_source_m3_s','occupancy_source_s','electron_energy_source_W_m3',
 'trap_energy_source_W_m3','lattice_heat_W_m3','trap_charge_source_C_m3_s',
 'total_energy_source_W_m3','entropy_production_W_m3_K','density_n_m3'])
def test_independent_audit_rejects_corrupted_moment_even_with_claimed_zero_totals(field):
    s=state();out=spectral_trap_capture(s,VN,VP)
    scale=max(abs(out[k]) for k in ('capture_energy_n_W_m3','capture_energy_p_W_m3')) if field=='total_energy_source_W_m3' else abs(out[field])
    out[field]+=max(scale*.01,1.)
    assert not audit_spectral_trap_capture(s,VN,VP,out)['valid']


@pytest.mark.parametrize('change',[dict(law='SRH'),dict(device_coupled=True),dict(material_calibrated=True),
                                  dict(capture_n_m3_s=float('nan')),dict(density_n_m3=True)])
def test_metadata_and_invalid_values_are_not_acceptance(change):
    s=state();out=spectral_trap_capture(s,VN,VP);out.update(change)
    assert not audit_spectral_trap_capture(s,VN,VP,out)['valid']


def test_reference_audit_does_not_call_production(monkeypatch):
    import tcad.core._bindings as native
    s=state();out=spectral_trap_capture(s,VN,VP)
    def fail(*a,**kw):raise AssertionError('production called by independent audit')
    monkeypatch.setattr(native,'native_spectral_trap_capture_raw',fail)
    assert audit_spectral_trap_capture(s,VN,VP,out)['valid']


@pytest.mark.parametrize('kw',[dict(occupancy=0.),dict(occupancy=1.),dict(occupancy=-.1),
 dict(temperature_l_K=0.),dict(capture_n_m3_s=-1.),dict(trap_density_m3=-1.),
 dict(mu_n_J=float('nan')),dict(occupancy=True),dict(Ec_J=[1.])])
def test_state_rejects_invalid_unclipped_inputs(kw):
    with pytest.raises(ValueError):state(**kw)


@pytest.mark.parametrize('level',[.61*Q,-.51*Q])
def test_outside_gap_trap_level_rejected(level):
    with pytest.raises(ValueError,match='gap'):spectral_trap_capture(state(trap_level_J=level),VN,VP)


def test_frozen_state_detaches_caller_scalar_buffer():
    a=np.array(.37);s=state(occupancy=a);a[()]=.9
    assert float(s.occupancy)==.37
    with pytest.raises(FrozenInstanceError):s.occupancy=.8


@pytest.mark.parametrize('index,value',[(0,'0'),(7,'-1'),(9,'-1'),(11,'1'),(8,'1'),(2,'nan')])
def test_raw_native_guards_cannot_be_bypassed(index,value):
    s=state();raw=[_decimal(getattr(s,n)) for n in s.__dataclass_fields__];raw[index]=value
    with pytest.raises(ValueError):native_spectral_trap_capture_raw(raw,_valley_decimals(VN),_valley_decimals(VP))


def test_raw_dimensions_and_valley_signs_rejected():
    s=state();raw=[_decimal(getattr(s,n)) for n in s.__dataclass_fields__]
    for n,p in (([],_valley_decimals(VP)),(['1'],_valley_decimals(VP)),
                (['1','-1','1','0'],_valley_decimals(VP))):
        with pytest.raises(ValueError):native_spectral_trap_capture_raw(raw,n,p)
