"""Independent scalar Poisson/SG/WKB reference for nonzero feedback."""
import math
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator,native_constants
from test_newton_zero_population import configured,bernoulli,carrier_matrix,MU,VT

EPS=11.7*8.854187817e-12

def wkb(phi,x,A,D,mass,fraction,segments,weight):
    # A separate polynomial fit and Simpson quadrature, not the core helper.
    c=np.polynomial.polynomial.polyfit(x/1e-8,phi,2) if len(x)==3 else None
    field=abs(np.gradient(phi,x))
    if c is not None:field[1]=abs((c[1]+2*c[2]*(x[1]/1e-8))/1e-8)
    result=np.zeros(len(x));segments+=segments%2 if segments>=4 else 0
    gap=1.12*1.602176634e-19
    for i in range(1,len(x)-1):
        e=field[i]
        if e<=1:continue
        length=min(2*1.12/e,x[i]-x[0],x[-1]-x[i])
        if fraction>0:length=min(length,fraction*(x[-1]-x[0]))
        if length<1e-12:continue
        def integrand(v):return math.sqrt(max(2*mass*9.1093837015e-31*(gap-1.602176634e-19*e*v),0))/1.054571817e-34
        if segments<4:action=integrand(0)*length
        else:
            h=length/segments;action=h/3*sum((1 if j in [0,segments] else 4 if j%2 else 2)*integrand(j*h) for j in range(segments+1))
        if -2*action>=-700:result[i]=min(1e50,A*1e6*e**D*math.exp(-2*action)*weight[i])
    return result

def fixture(mesh,segments,fraction,pattern,route):
    x=np.array([0.,.7,2.1] if mesh else [0.,1.,2.])*1e-8
    sim=PyDeviceSimulator(3,1,1,1e-8,1.,1.)
    if mesh:sim.set_x_positions(x)
    sim.set_quantum_enabled(False);sim.set_thermal_voltage(VT)
    sim.set_permittivity(np.full(3,EPS));sim.set_doping(np.zeros(3))
    sim.set_mobility(np.full(3,.1),np.full(3,.05));sim.set_effective_dos(np.full(3,1e3),np.full(3,1e3))
    sim.set_bandgap(np.full(3,1.12));sim.set_recombination(np.full(3,1e100),np.full(3,1e100))
    sim.set_dirichlet_potential({0:0.,2:-2.});sim.set_electron_bc({0:1e20,2:1e20});sim.set_hole_bc({0:1e20,2:1e20})
    sim.set_initial_guess(np.array([0.,-.8,-2.]),np.full(3,1e20),np.full(3,1e20))
    sim.set_btbt_enabled(True);sim.set_btbt_use_nonlocal(True);sim.set_btbt_params(1e14,2e9,2.)
    sim.set_btbt_nonlocal_params(fraction,segments);sim.set_btbt_nonlocal_mass(.01);sim.set_btbt_continuity_scale(.1)
    weights=[[],[.3,.2,1.7],[.3,-.02,1.7]][pattern]
    sim.set_btbt_weight(np.array(weights,dtype=float));sim.set_use_newton(route!='gummel');sim.set_newton_primary(route=='primary')
    sim.set_gummel_max_iter(60);sim.set_tolerance(1e-11);sim.set_nonlinear_history_enabled(True)
    return sim,x,np.array(weights if pattern else [1.,1.,1.])

def observe(mesh,segments,fraction,pattern,route):
    sim,x,weights=fixture(mesh,segments,fraction,pattern,route);z=sim.solve()
    assert z['converged'],(mesh,segments,fraction,pattern,route)
    if route=='primary':assert any(h['solver']=='newton' and h['converged'] for h in z['nonlinear_history']) and all(h['solver']!='gummel' for h in z['nonlinear_history'])
    q=float(native_constants()['elementary_charge_C']);h=np.diff(x);width=sum(h)/2
    def evaluate(middle):
        phi=np.array([0.,middle,-2.]);g=.1*wkb(phi,x,1e14,2.,.01,fraction,segments,weights)[1];densities=[]
        for mu,sign in [(.1,1),(.05,-1)]:
            d=sign*(phi[[0,2]]-middle)/VT
            incoming=np.array([bernoulli(v) for v in d]);outgoing=np.array([bernoulli(-v) for v in d])
            densities.append((g*width/(mu*VT)+1e20*sum(incoming/h))/sum(outgoing/h))
        n,p=densities;poisson=EPS*((phi[2]-middle)/h[1]-(middle-phi[0])/h[0])/width+q*(p-n)
        return poisson,phi,np.array([1e20,n,1e20]),np.array([1e20,p,1e20])
    lo,hi=-2.5,.5;assert evaluate(lo)[0]>0>evaluate(hi)[0]
    for _ in range(100):
        mid=(lo+hi)/2
        if evaluate(mid)[0]>0:lo=mid
        else:hi=mid
    _,phi,n,p=evaluate((lo+hi)/2)
    expected=wkb(z['phi'],x,1e14,2.,.01,fraction,segments,weights)
    np.testing.assert_allclose(z['G_btbt'],expected,rtol=3e-8,atol=0.)
    np.testing.assert_allclose(z['phi'],phi,rtol=0.,atol=3e-9)
    for k,v in [('n',n),('p',p)]:np.testing.assert_allclose(z[k],v,rtol=3e-8)
    return dict(mesh=mesh,segments=segments,fraction=fraction,pattern=pattern,route=route,x=x.tolist(),weight=weights.tolist(),numeric={k:z[k].tolist() for k in ['phi','n','p','G_btbt']},expected=dict(phi=phi.tolist(),n=n.tolist(),p=p.tolist()),history=z['nonlinear_history'])

@pytest.mark.parametrize('mesh',[0,1])
@pytest.mark.parametrize('segments',[2,5,32])
@pytest.mark.parametrize('fraction',[0.,.08])
@pytest.mark.parametrize('pattern',range(3))
@pytest.mark.parametrize('route',['primary','hybrid','gummel'])
def test_nonzero_wkb_feedback(mesh,segments,fraction,pattern,route):observe(mesh,segments,fraction,pattern,route)

@pytest.mark.parametrize('mesh',[0,1])
@pytest.mark.parametrize('species',range(3))
def test_wkb_feedback_zero_seed(mesh,species):
    sim,x,_=configured(0,mesh,'nonlocal_export',species)
    sim.set_btbt_continuity_scale(.1);sim.set_recombination(np.full(9,1e100),np.full(9,1e100))
    state=sim.solve();assert state['converged']
    source=.1*wkb(state['phi'],x,1e-4,2.,.25,.2,32,np.ones(9));width=(x[2:]-x[:-2])/2
    for name,sign in [('n',1),('p',-1)]:
        expected=np.linalg.solve(carrier_matrix(state['phi'],x,sign),source[1:-1]*width)
        np.testing.assert_allclose(state[name][1:-1],expected,rtol=3e-8)
    assert any(h['solver']=='newton' and h['converged'] for h in state['nonlinear_history'])
