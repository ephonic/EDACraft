"""Independent probability-tail, communicating-class and invalid-state checks."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import numpy as np
import pytest
from tcad.physics.electron_counting import BirthDeathChain


@pytest.mark.parametrize('mass',[1e-20,1e-100,1e-300,float.fromhex('0x0.0000000000001p-1022')])
def test_lower_tail_preserves_representable_mass_below_unit_roundoff(mass):
    chain=BirthDeathChain(2,lambda n:0.,lambda n:0.)
    chain.initialize(np.array([mass,0.,1.]))
    assert chain.tail_below(1)==mass
    assert chain.tail_below(2)==mass
    assert chain.survival(1)==1.
    assert chain.tail_below(0)==0.


@pytest.mark.parametrize('time',[1e-20,1e-100,1e-300])
def test_tiny_pure_death_probability_matches_independent_exponential(time):
    chain=BirthDeathChain(1,lambda n:0.,lambda n:1.)
    chain.initialize(count=1);chain.advance(time)
    expected=-math.expm1(-time)
    assert chain.tail_below(1)==pytest.approx(expected,rel=5e-15,abs=0.)


@pytest.mark.parametrize('time',[1e-20,1e-100,1e-300])
def test_retention_distribution_to_decoder_keeps_rare_encoded_ber(time):
    from tcad.physics.storage_readout import decode_distributions
    chain=BirthDeathChain(1,lambda n:0.,lambda n:1.)
    chain.initialize(count=1);chain.advance(time)
    result=decode_distributions(np.array([[1.,0.],chain.state]),[1.])
    expected=-math.expm1(-time)/2
    assert result.symbol_error_rate==pytest.approx(expected,rel=5e-15,abs=0.)
    assert result.bit_error_rate==pytest.approx(expected,rel=5e-15,abs=0.)


@pytest.mark.parametrize('start',[0,1,2,3])
@pytest.mark.parametrize('birth',[False,True])
def test_unique_absorbing_stationary_state_matches_long_hold(start,birth):
    chain=BirthDeathChain(3,lambda n:float(birth),lambda n:float(not birth))
    expected=np.zeros(4);expected[3 if birth else 0]=1.
    np.testing.assert_array_equal(chain.stationary(),expected)
    chain.initialize(count=start);chain.advance(100.)
    np.testing.assert_allclose(chain.state,expected,rtol=0.,atol=1e-14)


def test_unique_interior_closed_class_has_zero_transient_mass():
    # 0 -> 1 <-> 2 <- 3; local detailed balance gives pi1:pi2 = 3:2.
    chain=BirthDeathChain(3,lambda n:[4.,2.,0.,0.][n],lambda n:[0.,0.,3.,5.][n])
    expected=np.array([0.,.6,.4,0.])
    np.testing.assert_allclose(chain.stationary(),expected,rtol=2e-15,atol=0.)
    for start in range(4):
        chain.initialize(count=start);chain.advance(50.)
        np.testing.assert_allclose(chain.state,expected,rtol=0.,atol=1e-14)


@pytest.mark.parametrize('mask',range(64))
def test_all_four_state_zero_rate_topologies_against_exact_generator_nullspace(mask):
    # Independent rational row reduction of Q*pi=0, sum(pi)=1. No graph
    # classification or detailed-balance product is used in this reference.
    lam=[(i+2) if mask & (1<<i) else 0 for i in range(3)]+[0]
    mu=[0]+[(i+7) if mask & (1<<(i+3)) else 0 for i in range(3)]
    q=[[Fraction(0) for _ in range(5)] for _ in range(4)]
    for i in range(4):
        q[i][i]=Fraction(-lam[i]-mu[i])
        if i<3: q[i+1][i]=Fraction(lam[i])
        if i: q[i-1][i]=Fraction(mu[i])
    q.append([Fraction(1) for _ in range(5)])
    rank=0
    for column in range(4):
        pivot=next((row for row in range(rank,5) if q[row][column]),None)
        if pivot is None: continue
        q[rank],q[pivot]=q[pivot],q[rank]
        divisor=q[rank][column];q[rank]=[v/divisor for v in q[rank]]
        for row in range(5):
            if row!=rank:
                multiplier=q[row][column]
                q[row]=[a-multiplier*b for a,b in zip(q[row],q[rank])]
        rank+=1
    chain=BirthDeathChain(3,lambda n:lam[n],lambda n:mu[n])
    if rank<4:
        with pytest.raises(ValueError,match='not unique'): chain.stationary()
    else:
        expected=np.array([float(q[i][-1]) for i in range(4)])
        np.testing.assert_allclose(chain.stationary(),expected,rtol=2e-14,atol=0.)


@pytest.mark.parametrize('kind',['all_absorbing','two_sinks','two_closed_intervals'])
def test_nonunique_stationary_mixture_is_explicitly_rejected(kind):
    if kind=='all_absorbing': lam=[0.]*4;mu=[0.]*4
    elif kind=='two_sinks': lam=[0.,1.,1.,0.];mu=[0.,1.,1.,0.]
    else: lam=[1.,0.,1.,0.];mu=[0.,1.,0.,1.]
    chain=BirthDeathChain(3,lambda n:lam[n],lambda n:mu[n])
    chain.initialize(count=1);before=chain.state.copy()
    with pytest.raises(ValueError,match='not unique'): chain.stationary()
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('lam,mu',[(1e300,1e-20),(1e-300,1e20),(3e-210,7e110),
                                  (1e200,1e-100),(1e-100,1e200),(2.,3.)])
def test_stationary_two_state_against_decimal_even_when_rate_ratio_overflows(lam,mu):
    chain=BirthDeathChain(1,lambda n:lam,lambda n:mu)
    with localcontext() as ctx:
        ctx.prec=800
        a=Decimal.from_float(lam);b=Decimal.from_float(mu)
        expected=[float(b/(a+b)),float(a/(a+b))]
    actual=chain.stationary()
    for got,want in zip(actual,expected):
        assert abs(got-want)<=max(16*math.ulp(want),2e-12*want)
    assert math.fsum(actual)==pytest.approx(1.,abs=2e-15)


def test_unrepresentable_positive_stationary_mass_is_not_silently_zeroed():
    chain=BirthDeathChain(1,lambda n:1e300,lambda n:1e-300)
    with pytest.raises(ValueError,match='not representable'): chain.stationary()


@pytest.mark.parametrize('invalid',[
    [np.nan,1.],[np.inf,0.],[-1e-20,1.],[0.,1.1],[0.,.8],
    [[0.,1.]],[False,True],[0j,1+0j],['0','1'],[1.],
])
def test_invalid_initial_probabilities_do_not_replace_accepted_state(invalid):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:1.)
    chain.initialize(count=1);before=chain.state.copy()
    with pytest.raises(ValueError): chain.initialize(invalid)
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('observer',['mean','tail_below','survival','advance'])
@pytest.mark.parametrize('bad',[np.nan,-1e-20])
def test_publicly_mutated_invalid_state_is_rejected_before_observation_or_update(observer,bad):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:1.)
    chain.initialize(count=1);chain.state[0]=bad;before=chain.state.copy()
    with pytest.raises(ValueError):
        getattr(chain,observer)(*([] if observer=='mean' else [1]))
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('bad',[True,np.bool_(False),1.5,'1',-1,3])
def test_counts_and_tail_thresholds_are_discrete_valid_indices(bad):
    chain=BirthDeathChain(2,lambda n:1.,lambda n:1.)
    chain.initialize(count=0)
    for method in (chain.survival,chain.tail_below):
        with pytest.raises(ValueError): method(bad)
    before=chain.state.copy()
    with pytest.raises(ValueError): chain.initialize(count=bad)
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('bad',[True,1.5,'2',0])
def test_chain_size_is_a_positive_integer(bad):
    with pytest.raises(ValueError): BirthDeathChain(bad,lambda n:0.,lambda n:0.)


def test_extended_input_probability_cannot_disappear_during_float64_export():
    if np.finfo(np.longdouble).tiny>=np.finfo(float).tiny:
        pytest.skip('platform has no wider exponent range')
    chain=BirthDeathChain(1,lambda n:1.,lambda n:1.)
    chain.initialize(count=1);before=chain.state.copy()
    with pytest.raises(ValueError,match='not representable'):
        chain.initialize(np.array([np.longdouble('1e-400'),1],dtype=np.longdouble))
    np.testing.assert_array_equal(chain.state,before)
