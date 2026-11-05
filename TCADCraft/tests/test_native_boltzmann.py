"""Independent classical DOS and spectral integration, precision and domain checks."""
from decimal import Decimal, localcontext
import numpy as np
import pytest
from tcad.core import native_precision
from tcad.core._bindings import native_boltzmann_reservoir_raw,native_boltzmann_bulk_face_raw
from tcad.physics.native_boltzmann import native_boltzmann_reservoirs,native_boltzmann_bulk_face
from tcad.postprocess.boltzmann_spectral_reference import boltzmann_reservoir,boltzmann_bulk_face,KB,Q
from tcad.physics.multivalley_thermionic import ThermionicValley

VS=(ThermionicValley('a',2,.916,.19,.19),ThermionicValley('b',4,.19,.916,.19,.03*Q,.03*Q))
ONE=(ThermionicValley('flat',1,.3,.3,.3),)
G=dict(potential_owner_V=.01,potential_neighbor_V=-.02,potential_face_V=-.005,charge_sign=-1,
       mobility_owner_m2_Vs=.03,mobility_neighbor_m2_Vs=.02,area_m2=1e-13,distance_owner_m=2e-9,distance_neighbor_m=3e-9)


def refgeom(kwargs):
    return dict(zip(('phi_o','phi_n','phi_f','z','mu_o','mu_n','area','do','dn'),
        [kwargs[k] for k in ('potential_owner_V','potential_neighbor_V','potential_face_V','charge_sign',
            'mobility_owner_m2_Vs','mobility_neighbor_m2_Vs','area_m2','distance_owner_m','distance_neighbor_m')]),
        bulk_potential_path=kwargs.get('bulk_potential_path','linear_series'))


@pytest.mark.parametrize('n',[1e17,1e22,1e26])
@pytest.mark.parametrize('t',[300.,600.,900.])
def test_native_reservoirs_match_independent_MB_DOS(n,t):
    actual=native_boltzmann_reservoirs([n,n/2],[t,t+20],[.2*Q,-.03*Q],VS)
    for row,density,temperature,band in zip(actual,[n,n/2],[t,t+20],[.2*Q,-.03*Q]):
        reference=boltzmann_reservoir(density,temperature,band,VS)
        for key in ('chemical_potential_J','energy_density_J_m3','density_m3'):
            assert row[key]==pytest.approx(reference[key],rel=2e-12,abs=1e-32)
        assert row['valley_densities_m3']==pytest.approx(reference['valley_populations_m3'],rel=2e-12)
        assert len(row['native_decimal'])==5 and row['statistics']=='boltzmann'
    assert native_precision()['mantissa_bits']==113


@pytest.mark.parametrize('path',['linear_series','endpoint_barrier'])
@pytest.mark.parametrize('z',[-1,1])
@pytest.mark.parametrize('dn',[0.,3e-9])
def test_native_face_matches_adaptive_independent_MB(path,z,dn):
    one,two=(2e22,750.,.2*Q),(1e22,500.,.24*Q)
    kwargs=dict(G,charge_sign=z,distance_neighbor_m=dn,bulk_potential_path=path)
    got=native_boltzmann_bulk_face(one,two,VS,**kwargs)
    expected=boltzmann_bulk_face(boltzmann_reservoir(*one,VS),boltzmann_reservoir(*two,VS),VS,**refgeom(kwargs))
    for key in ('particle_flux_s','total_energy_flux_W','material_energy_flux_W','entropy_production_W_K'):
        assert got[key]==pytest.approx(expected[key],rel=2e-10,abs=1e-30),key
    assert got['entropy_production_W_K']>=0
    assert got['execution_backend']=='native' and not got['device_statistics_selected']
    for a,b in zip(got['valley_moments'],expected['valley_moments']):
        assert a['particle_flux_s']==pytest.approx(b['particle_flux_s'],rel=2e-10)
        assert a['total_energy_flux_W']==pytest.approx(b['total_energy_flux_W'],rel=2e-10)


@pytest.mark.parametrize('to,tn,no,nn',[(600.,600.,2e21,1e21),(900.,450.,1e21,2e21),(450.,900.,2e21,1e21),(600.,600.,1e21,1e21)])
def test_flat_potential_analytic_particle_energy_entropy(to,tn,no,nn):
    band=.5*Q
    kwargs=dict(G,potential_owner_V=0.,potential_neighbor_V=0.,potential_face_V=0.)
    got=native_boltzmann_bulk_face((no,to,band),(nn,tn,band),ONE,**kwargs)
    factor=G['area_m2']/(G['distance_owner_m']/G['mobility_owner_m2_Vs']+G['distance_neighbor_m']/G['mobility_neighbor_m2_Vs'])*KB/Q
    rate=factor*(no*to-nn*tn);energy=band*rate+2.5*KB*factor*(no*to**2-nn*tn**2)
    pscale=factor*(no*to+nn*tn)
    assert abs(got['particle_flux_s']-rate)<=2e-14*pscale
    assert abs(got['material_energy_flux_W']-energy)<=2e-14*(abs(band)*pscale+2.5*KB*factor*(no*to**2+nn*tn**2))
    if no==nn and to==tn:
        assert all(got[k]==0 for k in ('particle_flux_s','total_energy_flux_W','entropy_production_W_K'))


@pytest.mark.parametrize('z',[-1,1])
def test_reversal_and_common_potential_gauge(z):
    one,two=(2e22,750.,.2*Q),(1e22,500.,.2*Q)
    kwargs=dict(G,charge_sign=z)
    a=native_boltzmann_bulk_face(one,two,VS,**kwargs)
    reverse=dict(kwargs,potential_owner_V=G['potential_neighbor_V'],potential_neighbor_V=G['potential_owner_V'],
        mobility_owner_m2_Vs=G['mobility_neighbor_m2_Vs'],mobility_neighbor_m2_Vs=G['mobility_owner_m2_Vs'],
        distance_owner_m=G['distance_neighbor_m'],distance_neighbor_m=G['distance_owner_m'])
    b=native_boltzmann_bulk_face(two,one,VS,**reverse)
    c=native_boltzmann_bulk_face(one,two,VS,**dict(kwargs,potential_owner_V=.21,potential_neighbor_V=.18,potential_face_V=.195))
    for k in ('particle_flux_s','material_energy_flux_W'):
        assert a[k]==pytest.approx(-b[k],rel=2e-12)
        assert a[k]==pytest.approx(c[k],rel=2e-12)
    assert a['entropy_production_W_K']==pytest.approx(b['entropy_production_W_K'],rel=2e-12)


def test_raw_decimal_weak_drive_below_float64_and_longdouble_density_resolution():
    n='10000000000000000000000000';next_n='10000000000000000000000001'
    assert np.longdouble(n)==np.longdouble(next_n)
    raw=native_boltzmann_bulk_face_raw([next_n,'600','0',n,'600','0'],
        ['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0'])
    with localcontext() as context:
        context.prec=60
        expected=Decimal('1e-13')/(Decimal('1e-8')/Decimal('.01'))*Decimal('1.380649e-23')/Decimal('1.602176634e-19')*600
        actual=Decimal(raw[0])
        assert actual>0 and abs(actual/expected-1)<Decimal('1e-7')
    assert Decimal(raw[3])>0


def test_MB_occupation_is_not_clipped_to_one():
    a=native_boltzmann_bulk_face((1e27,600.,0.),(2e27,600.,0.),ONE,**G)
    assert a['trace_occupation_max']>1 and a['entropy_production_W_K']>0


def test_public_float64_view_rejects_native_nonzero_below_longdouble_range():
    raw=native_boltzmann_bulk_face_raw(['1e22','701','0','1e22','99999','0'],
        ['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0'])
    assert Decimal(raw[4])>0 and np.longdouble(raw[4])==0
    with pytest.raises(ValueError,match='float64 view'):
        native_boltzmann_bulk_face((1e22,701.,0.),(1e22,99999.,0.),ONE,
            **dict(G,potential_owner_V=0.,potential_neighbor_V=0.,potential_face_V=0.,
                   mobility_owner_m2_Vs=.01,mobility_neighbor_m2_Vs=.01,distance_owner_m=1e-8,distance_neighbor_m=0.))


def test_native_has_no_python_thermodynamic_or_flux_fallback(monkeypatch):
    def deny(*a,**kw):raise AssertionError('Python physics fallback used')
    for name in ('boltzmann_reservoir','boltzmann_bulk_face'):
        monkeypatch.setattr('tcad.postprocess.boltzmann_spectral_reference.'+name,deny)
    monkeypatch.setattr('tcad.physics.fermi_spectral.fermi_reservoir',deny)
    a=native_boltzmann_reservoirs([1e22],[600.],[0.],ONE)
    b=native_boltzmann_bulk_face((1e22,600.,0.),(2e22,700.,0.),ONE,**G)
    assert a[0]['density_m3']>0 and b['entropy_production_W_K']>0


@pytest.mark.parametrize('state,geometry,valleys',[
    ([],['0']*10,['.3','.3','1','0']),
    (['1e22','600','0']*2,['0']*9,['.3','.3','1','0']),
    (['1e22','600','0']*2,['0','0','0','-1','.01','.01','1e-13','1e-8','0','1'],['.3','.3','1','0']),
    (['0','600','0']*2,['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0']),
    (['1e22','1','0']*2,['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0']),
    (['1e22','600','0']*2,['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','0','1','0']),
    (['nan','600','0']*2,['0','0','0','-1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0']),
    (['1e-4960','600','0']*2,['0','0','0','1','.01','.01','1e-13','1e-8','0','2'],['.3','.3','1','0'])])
def test_invalid_raw_packets_and_unrepresentable_population_are_rejected(state,geometry,valleys):
    with pytest.raises(ValueError):native_boltzmann_bulk_face_raw(state,geometry,valleys)


@pytest.mark.parametrize('key,value',[('charge_sign',True),('distance_neighbor_m',-1),('area_m2',0),
                                    ('bulk_potential_path','thermionic'),('potential_owner_V',complex(0,1))])
def test_wrapper_rejects_invalid_geometry(key,value):
    with pytest.raises(ValueError):
        native_boltzmann_bulk_face((1e22,600.,0.),(2e22,700.,0.),ONE,**dict(G,**{key:value}))
