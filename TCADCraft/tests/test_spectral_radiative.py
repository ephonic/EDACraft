from dataclasses import replace,FrozenInstanceError
import math
import numpy as np
import pytest
from tcad.physics.spectral_radiative import SpectralRadiativeState,spectral_radiative_source,FIELDS
from tcad.postprocess.spectral_radiative import audit_radiative_source
from tcad.physics.native_fermi_local import _decimal

Q=1.602176634e-19;KB=1.380649e-23;M0=9.1093837015e-31;H=6.62607015e-34
BASE=SpectralRadiativeState(700,430,300,.52*Q,.35*Q,.6*Q,.5*Q,.067,.45,1,2e8)


@pytest.mark.parametrize('changes',[
 {},dict(temperature_photon_K=3000),dict(mu_n_J=.9*Q,mu_p_J=.8*Q),
 dict(temperature_n_K=3,temperature_p_K=3000),dict(temperature_n_K=3000,temperature_p_K=3),
 dict(mass_n_ratio=.01,mass_p_ratio=3),dict(mass_n_ratio=3,mass_p_ratio=.01),
 dict(pair_degeneracy=6),dict(transition_rate_s=0),
 dict(Ec_J=.0001*Q,Eh_J=.0001*Q,mu_n_J=-.1*Q,mu_p_J=-.1*Q,temperature_photon_K=1200),
 dict(mu_n_J=3*Q,mu_p_J=2*Q,temperature_n_K=150,temperature_p_K=240),
 dict(temperature_n_K=300,temperature_p_K=300,mu_n_J=.03*Q,mu_p_J=-.03*Q),
 dict(temperature_photon_K=1),dict(mu_n_J=-1.5*Q,mu_p_J=-1.5*Q)])
def test_independent_infinite_tail_moments(changes):
    s=replace(BASE,**changes);r=spectral_radiative_source(s)
    audit=audit_radiative_source(s,r)
    assert audit['valid'],audit
    assert r['entropy_production_W_m3_K']>=0
    assert r['execution_backend']=='native'


@pytest.mark.parametrize('mu_eV',[-.4,0,.55,1.2])
def test_equilibrium_each_event_balances(mu_eV):
    s=replace(BASE,temperature_n_K=300,temperature_p_K=300,mu_n_J=mu_eV*Q,mu_p_J=-mu_eV*Q)
    r=spectral_radiative_source(s);gross=r['emission_rate_m3_s']+r['absorption_rate_m3_s']
    assert abs(r['net_recombination_rate_m3_s'])<1e-13*gross
    assert abs(r['photon_power_W_m3'])<1e-13*gross*Q
    assert r['entropy_production_W_m3_K']<1e-24*KB*gross


def test_absorption_direction_and_pauli_blocking():
    hot=replace(BASE,temperature_photon_K=3000)
    a=spectral_radiative_source(hot)
    b=spectral_radiative_source(replace(hot,mu_n_J=2*Q,mu_p_J=2*Q))
    assert a['net_recombination_rate_m3_s']<0
    assert a['electron_number_source_m3_s']>0 and a['photon_power_W_m3']<0
    assert b['absorption_rate_m3_s']<a['absorption_rate_m3_s']*.01
    assert b['net_recombination_rate_m3_s']>0


def test_dilute_spontaneous_closed_form_unequal_mass_temperature():
    s=replace(BASE,mu_n_J=-1.5*Q,mu_p_J=-1.5*Q,temperature_photon_K=1)
    r=spectral_radiative_source(s);an=float(s.mass_p_ratio/(s.mass_n_ratio+s.mass_p_ratio));ap=1-an
    effective=1/(an/float(s.temperature_n_K)+ap/float(s.temperature_p_K))
    mr=float(s.mass_n_ratio*s.mass_p_ratio/(s.mass_n_ratio+s.mass_p_ratio))
    pref=2*float(s.pair_degeneracy)*(2*math.pi*mr*M0*KB*effective/H**2)**1.5*float(s.transition_rate_s)
    expected=pref*math.exp(float((s.mu_n_J-s.Ec_J)/(KB*s.temperature_n_K)+(s.mu_p_J-s.Eh_J)/(KB*s.temperature_p_K)))
    assert r['spontaneous_rate_m3_s']==pytest.approx(expected,rel=2e-12)
    assert r['emission_energy_n_W_m3']/expected==pytest.approx(float(s.Ec_J)+1.5*an*KB*effective,rel=2e-12)
    assert r['emission_energy_p_W_m3']/expected==pytest.approx(float(s.Eh_J)+1.5*ap*KB*effective,rel=2e-12)
    assert r['stimulated_rate_m3_s']==0


def test_energy_reference_covariance():
    delta=-2*Q
    shifted=replace(BASE,Ec_J=BASE.Ec_J+delta,Eh_J=BASE.Eh_J-delta,
                    mu_n_J=BASE.mu_n_J+delta,mu_p_J=BASE.mu_p_J-delta)
    a=spectral_radiative_source(BASE);b=spectral_radiative_source(shifted)
    assert audit_radiative_source(shifted,b)['valid']
    for name in ('net_recombination_rate_m3_s','photon_power_W_m3','entropy_production_W_m3_K'):
        assert b[name]==pytest.approx(a[name],rel=3e-13)
    assert b['electron_energy_source_W_m3']==pytest.approx(a['electron_energy_source_W_m3']-delta*a['net_recombination_rate_m3_s'],rel=3e-13)
    assert b['hole_energy_source_W_m3']==pytest.approx(a['hole_energy_source_W_m3']+delta*a['net_recombination_rate_m3_s'],rel=3e-13)


def test_energy_is_not_bandgap_only_or_equal_split():
    r=spectral_radiative_source(BASE)
    assert abs(r['photon_power_W_m3']/(float(BASE.Ec_J+BASE.Eh_J)*r['net_recombination_rate_m3_s'])-1)>.01
    assert abs(r['electron_energy_source_W_m3']/r['hole_energy_source_W_m3']-1)>.01


@pytest.mark.parametrize('name',FIELDS)
def test_forged_report_rejected(name):
    r=spectral_radiative_source(BASE)
    activity=max(r['emission_rate_m3_s'],r['absorption_rate_m3_s'])
    energy=max(abs(r[k]) for k in ('emission_energy_n_W_m3','emission_energy_p_W_m3',
                                 'absorption_energy_n_W_m3','absorption_energy_p_W_m3'))
    if name.endswith('W_m3'):scale=max(abs(r[name]),energy)
    elif name.endswith('C_m3_s'):scale=Q*activity
    elif name.endswith('W_m3_K'):scale=max(abs(r[name]),KB*activity)
    else:scale=max(abs(r[name]),activity)
    r[name]+=scale*.01
    assert not audit_radiative_source(BASE,r)['valid']


@pytest.mark.parametrize('value',[True,np.nan,np.inf,1j,[],[1],'300',None])
def test_malformed_state_scalar(value):
    with pytest.raises((ValueError,TypeError)):
        replace(BASE,temperature_n_K=value)


@pytest.mark.parametrize('changes',[
 dict(temperature_n_K=0),dict(temperature_p_K=-1),dict(temperature_photon_K=0),
 dict(mass_n_ratio=0),dict(mass_p_ratio=-1),dict(pair_degeneracy=0),
 dict(pair_degeneracy=1.5),dict(transition_rate_s=-1),dict(Eh_J=-BASE.Ec_J)])
def test_invalid_domain_both_boundaries(changes):
    with pytest.raises(ValueError):replace(BASE,**changes)
    from tcad.core._bindings import native_spectral_radiative_raw
    values=[_decimal(changes.get(n,getattr(BASE,n))) for n in BASE.__dataclass_fields__]
    with pytest.raises(ValueError):native_spectral_radiative_raw(values)


@pytest.mark.parametrize('bad',[[],['1']*10,['1']*12,['nan']*11,['inf']*11,['1x']*11])
def test_raw_schema_rejected(bad):
    from tcad.core._bindings import native_spectral_radiative_raw
    with pytest.raises(ValueError):native_spectral_radiative_raw(bad)


def test_scalar_ownership_and_immutable_configuration():
    buffer=np.array(700.)
    s=replace(BASE,temperature_n_K=buffer);buffer[()]=1
    assert s.temperature_n_K==700
    with pytest.raises(FrozenInstanceError):s.temperature_n_K=1
    with pytest.raises(TypeError):spectral_radiative_source({})


@pytest.mark.parametrize('rtol',[True,0,-1,np.inf,np.nan,1e-5,[1]])
def test_audit_tolerance_rejected(rtol):
    with pytest.raises(ValueError):audit_radiative_source(BASE,{},rtol=rtol)


def test_zero_rate_all_moments_zero():
    r=spectral_radiative_source(replace(BASE,transition_rate_s=0))
    assert all(r[k]==0 for k in FIELDS)


def test_linear_state_rate_and_pair_multiplicity():
    a=spectral_radiative_source(BASE)
    b=spectral_radiative_source(replace(BASE,transition_rate_s=BASE.transition_rate_s*3,pair_degeneracy=2))
    for name in FIELDS:assert b[name]==pytest.approx(6*a[name],rel=3e-14,abs=1e-300)
