from decimal import Decimal,localcontext
import numpy as np
import pytest
from scipy.optimize import brentq
from tcad.core import native_precision
from tcad.core._bindings import native_boltzmann_energy_coordinates_raw as raw
from tcad.physics.native_boltzmann_energy import native_boltzmann_energy_coordinates as convert
from tcad.physics.native_fermi_local import _decimal
from tcad.postprocess.boltzmann_spectral_reference import boltzmann_reservoir,KB,Q
from tcad.physics.multivalley_thermionic import ThermionicValley

VS=(ThermionicValley('a',2,.916,.19,.19),ThermionicValley('b',4,.19,.916,.19,.03*Q,.03*Q),
    ThermionicValley('c',1,.4,.7,.7,.12*Q,.12*Q))
ONE=(ThermionicValley('one',1,.3,.3,.3),)
def packed(vs):return [_decimal(x) for v in vs for x in (v.mass_normal,v.dos_mass_ratio,v.degeneracy,v.band_offset_owner_J)]
def check(row):
    d=list(map(Decimal,row));assert abs(d[3])<=d[4] and d[5]>0 and 1<d[0]<100000
    return d


@pytest.mark.parametrize('density',[1e17,1e22,1e26])
@pytest.mark.parametrize('ref,T',[(300.,450.),(600.,250.),(303.,303.),(20.,99999.),(900.,1.01)])
def test_multivalley_roundtrip_against_independent_classical_EOS(density,ref,T):
    initial=raw(list(map(_decimal,(density,ref,T,.2*Q))),packed(VS),True)
    d=check(initial);assert float(d[0])==pytest.approx(T,rel=2e-13,abs=1e-12)
    replay=raw([_decimal(density),_decimal(ref),initial[2],_decimal(.2*Q)],packed(VS))
    check(replay);assert float(replay[0])==pytest.approx(T,rel=2e-13,abs=1e-12)
    expected=boltzmann_reservoir(density,T,.2*Q,VS)
    assert float(d[7])==pytest.approx(expected['energy_density_J_m3'],rel=2e-12)
    assert float(d[6])==pytest.approx(expected['chemical_potential_J'],rel=2e-12,abs=1e-32)
    # Independent reference uses its own floating EOS and bracketed root, no
    # native heat capacity/Newton/expm1 energy-difference implementation.
    u0=boltzmann_reservoir(density,ref,0.,VS)['energy_density_J_m3']
    target=float(d[2])
    decoded=brentq(lambda t:boltzmann_reservoir(density,t,0.,VS)['energy_density_J_m3']-u0-target,
                   1.,100000.,xtol=1e-9,rtol=1e-14)
    assert float(d[0])==pytest.approx(decoded,rel=3e-11,abs=1e-8)
    assert native_precision()['mantissa_bits']==113


@pytest.mark.parametrize('T',[10.,150.,300.,900.,10000.])
def test_heat_capacity_matches_independent_EOS_five_point_derivative(T):
    n=2e23;row=convert([n],[303.],[T],[0.],VS,initialize=True)[0];h=T*1e-3
    u=lambda t:boltzmann_reservoir(n,t,0.,VS)['energy_density_J_m3']
    derivative=(u(T-2*h)-8*u(T-h)+8*u(T+h)-u(T+2*h))/(12*h)
    assert row['heat_capacity_J_m3_K']==pytest.approx(derivative,rel=2e-10)
    assert row['heat_capacity_J_m3_K']>=1.5*n*KB


@pytest.mark.parametrize('energy',['1e-80','-1e-80','1e-300','-1e-300','1e-4900','-1e-4900'])
def test_sub_native_temperature_resolution_excess_remains_authoritative(energy):
    result=raw(['1e22','303',energy,'1e-16'],packed(VS));d=check(result)
    with localcontext() as ctx:
        ctx.prec=100
        assert d[0]==303 and abs(d[2]/Decimal(energy)-1)<Decimal('1e-32')
        assert d[3]==-d[2]
        assert abs(d[2])<d[4]
    # At n=1e22 the 1e-4900/n quotient remains representable in float128.
    # True quotient-underflow cases at n=1e100 are independently retained in
    # native_boltzmann_energy_range_20261023; the energy stays authoritative.


def test_native_temperature_below_longdouble_spacing_and_closed_form_energy():
    tc='303.000000000000000000000000001'
    result=raw(['1e22','303',tc,'0'],packed(ONE),True);d=check(result)
    with localcontext() as ctx:
        ctx.prec=100
        capacity=Decimal('1.5')*Decimal('1.380649e-23')*Decimal('1e22')
        assert abs(d[0]-Decimal(tc))<Decimal('1e-29') and d[0]!=303
        assert abs(d[2]/(capacity*(Decimal(tc)-303))-1)<Decimal('1e-4')
        assert abs(d[5]/capacity-1)<Decimal('1e-32')
    assert np.longdouble(tc)==np.longdouble(303)


@pytest.mark.parametrize('band',['0','-1e-16','1e-16','1e20'])
def test_energy_origin_cannot_erase_thermal_state_or_valley_splitting(band):
    baseline=raw(['1e22','303','617.25','0'],packed(VS),True)
    row=raw(['1e22','303','617.25',band],packed(VS),True)
    for key in (0,1,2,3,4,5,9):assert row[key]==baseline[key]


def test_valley_permutation_and_uniform_shift_preserve_energy_coordinate():
    baseline=raw(['1e22','303','817.5','0'],packed(VS),True)
    shifted=tuple(ThermionicValley(v.name,v.degeneracy,v.mass_normal,v.mass_tangent_1,v.mass_tangent_2,
        v.band_offset_owner_J+.01*Q,v.band_offset_neighbor_J+.01*Q) for v in reversed(VS))
    row=raw(['1e22','303','817.5','0'],packed(shifted),True)
    for key in (0,1,2,5):assert float(row[key])==pytest.approx(float(baseline[key]),rel=2e-14)


def test_no_Python_physics_or_FD_fallback(monkeypatch):
    def deny(*a,**kw):raise AssertionError('non-MB/native fallback')
    monkeypatch.setattr('tcad.postprocess.boltzmann_spectral_reference.boltzmann_reservoir',deny)
    monkeypatch.setattr('tcad.physics.fermi_spectral.fermi_reservoir',deny)
    row=convert([1e22],[303.],[701.],[.1*Q],VS,initialize=True)[0]
    assert row['statistics']=='boltzmann' and row['excess_authoritative'] and not row['device_statistics_selected']
    assert row['temperature_K']==pytest.approx(701.)


@pytest.mark.parametrize('state',[
    [],['1e22','303','0'],['0','303','0','0'],['1e22','1','0','0'],['1e22','100000','0','0'],
    ['1e22','303','nan','0'],['1e22','303','1e10','0'],['1e22','303','-1e10','0'],
    ['1e22','303','1e-9999','0'],['1e-4960','303','0','0']])
def test_invalid_or_unrepresentable_raw_states_rejected(state):
    with pytest.raises(ValueError):raw(state,packed(VS))


@pytest.mark.parametrize('budget',[0,-1,513,True,1.5])
def test_invalid_iteration_budget_rejected(budget):
    with pytest.raises(ValueError):raw(['1e22','303','0','0'],packed(VS),max_iterations=budget)


def test_unconverged_inversion_raises_without_a_state():
    with pytest.raises(ValueError,match='exhausted'):raw(['1e22','2','30000','0'],packed(VS),True,1)


@pytest.mark.parametrize('values',[[True],[complex(1,1)],[],[300.,400.]])
def test_public_vectors_reject_invalid_inputs(values):
    with pytest.raises(ValueError):convert([1e22],[303.],values,[0.],VS,initialize=True)


def test_public_batch_can_encode_and_decode_both_signs():
    encoded=convert([1e22,2e22],[303.,600.],[400.,250.],[0.,.1*Q],VS,initialize=True)
    decoded=convert([1e22,2e22],[303.,600.],[r['excess_energy_J_m3'] for r in encoded],[0.,.1*Q],VS)
    assert encoded[0]['excess_energy_J_m3']>0>encoded[1]['excess_energy_J_m3']
    assert [r['temperature_K'] for r in decoded]==pytest.approx([400.,250.])
