"""Range-safe matrix exponentials and whole-request state transactions."""
from decimal import Decimal, localcontext
import math
import numpy as np
import pytest
from tcad.physics.electron_counting import BirthDeathChain


def symmetric_three_state_reference(rate,time):
    # Independent spectral solution of the 3-node reflecting random walk.
    with localcontext() as ctx:
        ctx.prec=800
        x=Decimal.from_float(rate)*Decimal.from_float(time)
        a=(-x).exp();b=(-3*x).exp();one=Decimal(1)
        return np.array([float(one/3+a/2+b/6),float((one-b)/3),
                         float(one/3-a/2+b/6)])


@pytest.mark.parametrize('rate,time',[(1e308,1e-308),(1e-308,1e308),
    (np.finfo(float).max,np.nextafter(0.,1.)),(1e300,1e-300),(1e-300,1e300)])
def test_overflowing_exit_sum_matches_decimal_spectral_solution(rate,time):
    chain=BirthDeathChain(2,lambda n:rate,lambda n:rate);chain.initialize(count=0)
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        actual=chain.advance(time)
    expected=symmetric_three_state_reference(float(rate),float(time))
    np.testing.assert_allclose(actual,expected,rtol=3e-13,atol=0.)


@pytest.mark.parametrize('birth',[True,False])
@pytest.mark.parametrize('rate,time',[(1e200,1e200),(1e308,1e308),
                                    (np.finfo(float).max,np.finfo(float).max)])
def test_overflowing_rate_time_reaches_correct_absorbing_state(rate,time,birth):
    chain=BirthDeathChain(2,lambda n:rate if birth else 0.,lambda n:0. if birth else rate)
    chain.initialize(count=0 if birth else 2)
    expected=np.zeros(3);expected[2 if birth else 0]=1.
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        result=chain.advance(time)
    np.testing.assert_array_equal(result,expected)


@pytest.mark.parametrize('lam,mu,time',[(3e200,1e200,1e200),(1e308,1e308,1e308),
    (1e308,5e307,1e308),(1e308,1e-12,1e100)])
def test_long_hold_with_overflowing_product_retains_decimal_stationary_mass(lam,mu,time):
    chain=BirthDeathChain(1,lambda n:lam,lambda n:mu);chain.initialize(count=0)
    with localcontext() as ctx:
        ctx.prec=800
        a,b=Decimal.from_float(lam),Decimal.from_float(mu)
        expected=[float(b/(a+b)),float(a/(a+b))]
    actual=chain.advance(time)
    for got,want in zip(actual,expected):
        assert abs(got-want)<=max(16*math.ulp(want),3e-13*want)
    assert np.all(actual>0.)


@pytest.mark.parametrize('rate,time',[(1.,39.9),(1.,40.),(1.,40.1),(1.,4096.),
    (1.,4096.1),(1e200,1e-198),(1e-200,1e202)])
def test_small_blocked_and_scaled_paths_match_two_state_exponential(rate,time):
    chain=BirthDeathChain(1,lambda n:rate,lambda n:0.);chain.initialize(count=0)
    with localcontext() as ctx:
        ctx.prec=800
        a=(-(Decimal.from_float(rate)*Decimal.from_float(time))).exp()
        expected=[float(a),float(1-a)]
    result=chain.advance(time)
    np.testing.assert_allclose(result,expected,rtol=3e-13,atol=0.)


@pytest.mark.parametrize('time',[.3,100.,1e5])
def test_step_subdivision_matches_nontrivial_four_state_generator(time):
    from scipy.linalg import expm
    lam=np.array([.1,2.,.7,0.]);mu=np.array([0.,.2,.3,1.])
    q=np.diag(-lam-mu)+np.diag(lam[:-1],-1)+np.diag(mu[1:],1)
    initial=np.array([.1,.2,.3,.4]);expected=expm(q*time)@initial
    one=BirthDeathChain(3,lambda n:lam[n],lambda n:mu[n]);one.initialize(initial)
    split=BirthDeathChain(3,lambda n:lam[n],lambda n:mu[n]);split.initialize(initial)
    one.advance(time)
    for _ in range(7): split.advance(time/7)
    # scipy expm itself loses ~1e-11 mass for the largest Q*t; compare its
    # normalized stationary shape, and audit our probability mass separately.
    expected/=math.fsum(expected)
    np.testing.assert_allclose(one.state,expected,rtol=3e-11,atol=0.)
    np.testing.assert_allclose(split.state,one.state,rtol=2e-13,atol=0.)
    assert math.fsum(one.state)==pytest.approx(1.,abs=2e-15)


def test_later_local_block_exception_leaves_original_state_object(monkeypatch):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:0.);chain.initialize(count=0)
    before=chain.state.copy();state_object=chain.state;original=chain._uniformization_step;calls=0
    def fail_later(*args):
        nonlocal calls
        calls+=1
        np.testing.assert_array_equal(chain.state,before)
        if calls==2: raise RuntimeError('later block failed')
        return original(*args)
    monkeypatch.setattr(chain,'_uniformization_step',fail_later)
    with pytest.raises(RuntimeError,match='later block'): chain.advance(100.)
    assert calls==2 and chain.state is state_object
    np.testing.assert_array_equal(chain.state,before)


def test_later_matrix_squaring_exception_leaves_original_state_object(monkeypatch):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:.5);chain.initialize(count=0)
    before=chain.state.copy();state_object=chain.state;original=chain._normalize_transition;calls=0
    def fail_later(matrix, *args):
        nonlocal calls
        calls+=1
        np.testing.assert_array_equal(chain.state,before)
        if calls==3: raise RuntimeError('later squaring failed')
        return original(matrix, *args)
    monkeypatch.setattr(chain,'_normalize_transition',fail_later)
    with pytest.raises(RuntimeError,match='later squaring'): chain.advance(1e5)
    assert calls==3 and chain.state is state_object
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('time',[1.,100.,1e5])
@pytest.mark.parametrize('invalid',[[np.nan,1.],[-1e-20,1.],[0.,.5],[0.,1.,0.]])
def test_invalid_candidate_never_commits(monkeypatch,time,invalid):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:0.);chain.initialize(count=0)
    before=chain.state.copy();state_object=chain.state
    kernel='_advance_scaled' if time>4096 else '_uniformization_step'
    monkeypatch.setattr(chain,kernel,lambda *args:np.array(invalid))
    with pytest.raises(ValueError): chain.advance(time)
    assert chain.state is state_object
    np.testing.assert_array_equal(chain.state,before)


@pytest.mark.parametrize('rate,time',[(0.,1.),(1.,.3),(1.,100.),(1.,1e5)])
def test_returned_distribution_does_not_alias_accepted_state(rate,time):
    chain=BirthDeathChain(1,lambda n:rate,lambda n:.5*rate);chain.initialize(count=0)
    result=chain.advance(time);accepted=chain.state.copy()
    assert not np.shares_memory(result,chain.state)
    result[:]=np.nan
    np.testing.assert_array_equal(chain.state,accepted)


@pytest.mark.parametrize('birth',[False,True])
def test_absorbing_state_survives_local_series_roundoff_for_100_durations(birth):
    chain=BirthDeathChain(1,lambda n:float(birth),lambda n:float(not birth))
    expected=np.array([0.,1.]) if birth else np.array([1.,0.])
    for time in np.linspace(.01,40.,100):
        chain.initialize(count=1 if birth else 0)
        np.testing.assert_array_equal(chain.advance(float(time)),expected)


@pytest.mark.parametrize('bad',[True,np.bool_(False),'1',1j,[1.],np.array([1.]),
                                np.nan,np.inf,0.,-1.,10**400])
def test_invalid_duration_is_rejected_without_state_change(bad):
    chain=BirthDeathChain(1,lambda n:1.,lambda n:1.);chain.initialize(count=1)
    before=chain.state.copy()
    with pytest.raises(ValueError): chain.advance(bad)
    np.testing.assert_array_equal(chain.state,before)


def test_unrepresentable_positive_rate_time_is_rejected_without_commit():
    chain=BirthDeathChain(1,lambda n:0.,lambda n:1e-200);chain.initialize(count=1)
    before=chain.state.copy()
    with pytest.raises(ValueError,match='rate-time product.*not representable'): chain.advance(1e-200)
    np.testing.assert_array_equal(chain.state,before)


def test_unrepresentable_normalized_positive_rate_is_rejected_without_commit():
    chain=BirthDeathChain(1,lambda n:1e308,lambda n:1e-308);chain.initialize(count=0)
    before=chain.state.copy()
    with pytest.raises(ValueError,match='normalized transition rates.*not representable'): chain.advance(1.)
    np.testing.assert_array_equal(chain.state,before)
