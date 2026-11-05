"""Source-export checks through the Python API, with an independent log product."""
import math
import numpy as np
import pytest
from test_native_setter_exceptions import fixture

CASES=[(1e300,2,1e-300),(1e308,0,1e-300),(1e-300,80,1e-300),
       (1e-300,-38,1e300),(1e300,2,-1e-300),(1e-300,80,-1e-300),
       (0.,100,1.),(1e300,2,0.),(1e300,2,1.),(-1e280,2,1.),(1e16,2,1.)]

def run_case(case,segments,route):
    A,D,weight=case
    sim=fixture('btbt_nonlocal_params',0)
    sim.set_use_newton(route=='newton');sim.set_newton_primary(route=='newton')
    sim.set_btbt_params(A,2e9,D);sim.set_btbt_weight(np.full(9,weight))
    sim.set_btbt_nonlocal_params(.2,segments)
    state=sim.solve()
    assert state['converged']
    phi=np.asarray(state['phi']);actual=np.asarray(state['G_btbt'])
    expected=np.zeros(9)
    for i in range(1,8):
        field=abs((phi[i+1]-phi[i-1])/2e-9)
        length=min(2*1.12/field,i*1e-9,(8-i)*1e-9,.2*8e-9)
        if length<1e-12 or field<=1 or A==0 or weight==0:continue
        gap=1.12*1.602176634e-19
        def integrand(x):return math.sqrt(max(2*.25*9.1093837015e-31*(gap-1.602176634e-19*field*x),0))/1.054571817e-34
        if segments<4:action=integrand(0)*length
        else:
            h=length/segments
            action=h/3*sum((1 if s in [0,segments] else 4 if s%2 else 2)*integrand(s*h) for s in range(segments+1))
        if -2*action < -700:continue
        value=math.log(abs(A))+math.log(1e6)+D*math.log(field)-2*action+math.log(abs(weight))
        positive=(A>0)==(weight>0)
        expected[i]=1e50 if positive and value>=math.log(1e50) else (1 if positive else -1)*math.exp(value)
    assert np.all(np.isfinite(actual))
    np.testing.assert_allclose(actual,expected,rtol=4e-11,atol=0)
    return dict(case=list(case),segments=segments,route=route,phi=phi.tolist(),actual=actual.tolist(),expected=expected.tolist())

@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('segments',[2,32])
@pytest.mark.parametrize('route',['gummel','newton'])
def test_wkb_complete_product(case,segments,route):run_case(case,segments,route)
