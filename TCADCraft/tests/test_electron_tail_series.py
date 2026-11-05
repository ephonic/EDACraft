"""Remote-state tails must survive series cutoffs even with unit total mass."""
from decimal import Decimal, localcontext
import math
import numpy as np
import pytest
from tcad.physics.electron_counting import BirthDeathChain


def poisson_absorbing_reference(count,alpha):
    """800-digit exact Poisson probabilities with a positive absorbing tail."""
    with localcontext() as ctx:
        ctx.prec=800;a=Decimal.from_float(alpha);w=(-a).exp();values=[w]
        for k in range(1,count):
            w*=a/Decimal(k);values.append(w)
        w*=a/Decimal(count);tail=w
        for k in range(count+1,count+601):
            w*=a/Decimal(k);tail+=w
        values.append(tail)
        return np.array([float(v) for v in values])


CASES=[(60,.1),(80,.1),(100,.1),(120,.1),
       (60,1.),(80,1.),(100,1.),(140,1.),(170,1.),
       (100,10.),(160,10.),(220,10.),(280,10.),
       (170,40.),(240,40.),(320,40.),(400,40.),(450,40.)]


@pytest.mark.parametrize('count,time',CASES)
@pytest.mark.parametrize('birth',[False,True])
def test_remote_absorbing_tail_against_decimal_poisson(count,time,birth):
    chain=BirthDeathChain(count,lambda n:float(birth),lambda n:float(not birth))
    chain.initialize(count=0 if birth else count)
    expected=poisson_absorbing_reference(count,time)
    if not birth: expected=expected[::-1]
    result=chain.advance(time)
    for got,want in zip(result,expected):
        assert abs(got-want)<=max(16*math.ulp(want),2e-12*want)
    tail=result[-1] if birth else chain.tail_below(1)
    reference=expected[-1] if birth else expected[0]
    assert reference>0. and tail>0.
    assert abs(tail-reference)<=max(16*math.ulp(reference),2e-12*reference)
    assert math.fsum(result)==pytest.approx(1.,abs=2e-15)


@pytest.mark.parametrize('count,alpha',[(80,.5),(100,1.),(120,1.)])
@pytest.mark.parametrize('squarings',[0,1,3])
@pytest.mark.parametrize('birth',[False,True])
def test_scaling_kernel_initial_series_against_independent_poisson(count,alpha,squarings,birth):
    # Exercise the base transition series used by the public long-hold path;
    # its old fixed 64 terms lost representable remote transition entries.
    chain=BirthDeathChain(count,lambda n:float(birth),lambda n:float(not birth))
    initial=np.zeros(count+1);initial[0 if birth else count]=1.
    b=np.ones(count+1) if birth else np.zeros(count+1);b[-1]=0.
    d=np.zeros(count+1) if birth else np.ones(count+1);d[0]=0.
    result=chain._advance_scaled(initial,alpha,squarings,b,d,1-b-d)
    expected=poisson_absorbing_reference(count,alpha*2**squarings)
    if not birth: expected=expected[::-1]
    np.testing.assert_allclose(result,expected,rtol=3e-12,atol=0.)
    assert np.all(result>0.)


@pytest.mark.parametrize('count,time',[(100,1.),(220,10.),(320,40.)])
def test_public_subdivision_preserves_remote_tail(count,time):
    one=BirthDeathChain(count,lambda n:1.,lambda n:0.);one.initialize(count=0)
    split=BirthDeathChain(count,lambda n:1.,lambda n:0.);split.initialize(count=0)
    one.advance(time)
    for _ in range(4): split.advance(time/4)
    expected=poisson_absorbing_reference(count,time)[-1]
    assert one.state[-1]==pytest.approx(expected,rel=2e-12,abs=0.)
    assert split.state[-1]==pytest.approx(expected,rel=2e-12,abs=0.)


def test_generated_remote_count_probability_reaches_encoded_error_metric():
    from tcad.physics.storage_readout import decode_distributions
    count=100;chain=BirthDeathChain(count,lambda n:1.,lambda n:0.);chain.initialize(count=0)
    chain.advance(1.)
    stable=np.zeros(count+1);stable[-1]=1.
    result=decode_distributions(np.array([chain.state,stable]),[float(count)])
    expected=poisson_absorbing_reference(count,1.)[-1]/2
    assert result.bit_error_rate==pytest.approx(expected,rel=2e-12,abs=0.)
    assert result.symbol_error_rate==pytest.approx(expected,rel=2e-12,abs=0.)
