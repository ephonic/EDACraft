"""80-digit edge references, exact Boltzmann barriers and coupled refinements."""
import itertools
import mpmath as mp
import numpy as np
import pytest
from dataclasses import replace
from tcad.material import graphene_sheet,mos2_sheet
from tcad.material.sheet import Q,KB
from tcad.solver.sheet_flux import _log_exprel,_thermal_voltage,fitted_conductance
from tcad.solver.sheet_drift_diffusion import SheetDriftDiffusion
from tcad.solver.sheet_dielectric import DielectricSheetDriftDiffusion
from test_sheet_drift_diffusion import ledgers

mp.mp.dps=80;VT=KB*300/Q

def occ(kind,x):
    return mp.log1p(mp.exp(x)) if kind=='parabolic' else -mp.polylog(2,-mp.exp(x))

def exprel(x):return mp.expm1(x)/x if x else mp.mpf(1)

@pytest.mark.parametrize('x',[-1000.,-100.,-50.,-1.,-.001,-.0001,-1e-12,0.,1e-12,.0001,.001,1.,50.,100.,1000.])
def test_log_exprel_against_80_digit_reference(x):
    actual,derivative=_log_exprel(np.array([x]));t=mp.mpf(x)
    expected=mp.log(exprel(t));d=mp.diff(lambda z:mp.log(exprel(z)),t)
    assert actual[0]==pytest.approx(float(expected),rel=2e-13,abs=1e-15)
    assert derivative[0]==pytest.approx(float(d),rel=2e-11,abs=1e-13)

@pytest.mark.parametrize('kind,pair',itertools.product(('parabolic','dirac'),[
    (-200.,-199.),(-30.,-5.),(-2.,3.),(0.,0.),(4.,4.+1e-8),(-35.0001,-34.9999),(20.,80.),(-200.,200.)]))
def test_diffusion_enhancement_secant_and_derivatives(kind,pair):
    a,b=map(mp.mpf,pair)
    def voltage(x,y):
        return mp.mpf(VT)*(y-x)/(mp.log(occ(kind,y))-mp.log(occ(kind,x))) if x!=y else mp.mpf(VT)*occ(kind,x)/mp.diff(lambda t:occ(kind,t),x)
    r,da,db=_thermal_voltage(np.array([float(a)]),np.array([float(b)]),VT,kind)
    expected=voltage(a,b)
    if a==b:
        d=mp.diff(lambda t:mp.mpf(VT)*occ(kind,t)/mp.diff(lambda z:occ(kind,z),t),a)/2;ea=eb=d
    else:ea=mp.diff(lambda t:voltage(t,b),a);eb=mp.diff(lambda t:voltage(a,t),b)
    assert r[0]==pytest.approx(float(expected),rel=1e-10)
    assert da[0]==pytest.approx(float(ea),rel=2e-7,abs=1e-10)
    assert db[0]==pytest.approx(float(eb),rel=2e-7,abs=1e-10)

CASES=[(-120.,-20.,80.),(-40.,10.,-30.),(-2.,3.,10.),(20.,80.,40.),(2.,2.,-20.),
       (1.,1.+1e-9,20.),(-200.,200.,600.),(-10.,10.,20.),(1.,1.+1e-12,0.)]
@pytest.mark.parametrize('kind,sign,case',itertools.product(('parabolic','dirac'),(-1,1),CASES))
def test_edge_flux_strong_field_degeneracy_reversal_and_dissipation(kind,sign,case):
    ai,aj,field=case;a,b=mp.mpf(ai),mp.mpf(aj)
    pi,pj=0.,field*VT;fi,fj=0.,sign*VT*(aj-ai)-pj
    ni,nj=float(1e16*occ(kind,a)),float(1e16*occ(kind,b));pref=Q*.02*.7
    def calc(p0,p1,f0,f1,e0,e1,n0):
        return fitted_conductance(np.array([p0]),np.array([p1]),np.array([f0]),np.array([f1]),
            np.array([e0]),np.array([e1]),np.array([n0]),vt=VT,dispersion=kind,sign=sign,prefactor=pref)[0][0]
    G=calc(pi,pj,fi,fj,ai,aj,ni)
    r=mp.mpf(VT)*(b-a)/(mp.log(occ(kind,b))-mp.log(occ(kind,a))) if a!=b else mp.mpf(VT)*occ(kind,a)/mp.diff(lambda t:occ(kind,t),a)
    expected=mp.mpf(pref)*mp.mpf(ni)/exprel(-sign*mp.mpf(pj-pi)/r)*exprel(sign*mp.mpf(fj-fi)/r)
    assert G==pytest.approx(float(expected),rel=1e-10)
    reverse=calc(pj,pi,fj,fi,aj,ai,nj)
    assert reverse==pytest.approx(G,rel=1e-10)
    assert np.isfinite(G) and G>0 and G*(fj-fi)**2>=0
    if aj-ai==sign*field:assert G*(fj-fi)==0.

def device(kind='graphene',dielectric=True,nx=9,nz=7,*,intrinsic=False):
    x=(.5-.5*np.cos(np.linspace(0,np.pi,nx)))*200e-9;y=np.linspace(0,100e-9,3)
    mat=graphene_sheet() if kind=='graphene' else mos2_sheet(reference_eV=0. if intrinsic else -.9)
    seed=mat.statistics();kw=dict(mobility_n_m2_Vs=.02,mobility_p_m2_Vs=.01,
        doping_m2=float(seed.n_m2-seed.p_m2),sheet_permittivity_F=4e-20,transport_scheme='diffusion_enhanced')
    if dielectric:
        z=np.linspace(-16e-9,16e-9,nz)
        epsilon=np.ones((nz-1,2,nx-1))*8.8541878128e-12
        epsilon[:nz//2]*=3.9;epsilon[nz//2:]*=9.
        return DielectricSheetDriftDiffusion(x,y,z,mat,sheet_index=nz//2,permittivity_F_m=epsilon,**kw)
    return SheetDriftDiffusion(x,y,mat,gate_capacitance_F_m2=.006,**kw)

def drive(sim,dielectric,amplitude=-.12):
    gate=amplitude*np.broadcast_to(np.sin(np.pi*sim.x/sim.x[-1])**2,sim.shape)
    return dict(top_gate_voltage_V=gate,bottom_gate_voltage_V=0.) if dielectric else dict(gate_voltage_V=gate)

@pytest.mark.parametrize('kind,dielectric',itertools.product(('graphene','mos2'),(False,True)))
def test_fitted_full_analytic_jacobian(kind,dielectric):
    sim=device(kind,dielectric,nx=5);N=sim.size;rng=np.random.default_rng(501)
    u=rng.normal(0,.025,3*N);direction=rng.normal(0,1,3*N)
    gate=sim.dielectric.gate_drive(top_gate_voltage_V=-.1,bottom_gate_voltage_V=0.) if dielectric else np.full(N,-.1)
    bc=(np.zeros(len(sim.contacts)),)*3
    _,scale,J,*_=sim._evaluate(u,gate,bc);h=2e-7
    fd=(sim._evaluate(u+h*direction,gate,bc,False)[0]-sim._evaluate(u-h*direction,gate,bc,False)[0])/(2*h)
    assert np.max(abs((J@direction-fd)/scale))<2e-5

@pytest.mark.parametrize('kind,dielectric',itertools.product(('graphene','mos2'),(False,True)))
def test_nonuniform_large_gate_equilibrium_has_exactly_zero_flux(kind,dielectric):
    sim=device(kind,dielectric,intrinsic=True)
    result=sim.solve(**drive(sim,dielectric,amplitude=-.3),max_iter=120)
    ledgers(result);assert result['transport_scheme']=='diffusion_enhanced'
    assert np.max(abs(result['phi_V']))>.01
    assert np.max(abs(result['edge_currents_A']))<1e-25

@pytest.mark.parametrize('kind,sign,nx',itertools.product(('parabolic','dirac'),(-1,1),(3,5,9)))
def test_deep_piecewise_linear_boltzmann_barrier_exact_current_on_coarse_mesh(kind,sign,nx):
    x=np.linspace(0.,200e-9,nx);height=.6;phi=-sign*height*(1-abs(2*x/x[-1]-1))
    # Analytic integral of exp(-sign*phi/VT) for each linear barrier segment.
    weights=[];thermal=mp.mpf(VT)
    for j in range(nx-1):
        a=-sign*mp.mpf(float(phi[j]))/thermal;b=-sign*mp.mpf(float(phi[j+1]))/thermal
        weights.append(mp.mpf(float(x[j+1]-x[j]))*mp.exp(a)*exprel(b-a))
    resistance=[mp.mpf(0)]
    for weight in weights:resistance.append(resistance[-1]+weight)
    activity_change=mp.expm1(-mp.mpf('.25')/thermal)
    # 80-digit state construction and stronger nonequilibrium bias keep the
    # endpoint float64 F differences representable at the fixed 1e-10 gate.
    F=np.array([float(sign*thermal*mp.log1p(activity_change*r/resistance[-1])) for r in resistance])
    eta=sign*(phi+F)/VT-50.
    density=np.array([float(1e16*occ(kind,mp.mpf(e))) for e in eta])
    G,_=fitted_conductance(phi[:-1],phi[1:],F[:-1],F[1:],eta[:-1],eta[1:],density[:-1],
        vt=VT,dispersion=kind,sign=sign,prefactor=Q*.02*100e-9/np.diff(x))
    expected=float(sign*mp.mpf(Q*.02)*thermal*mp.mpf('1e16')*mp.exp(-50)*activity_change*mp.mpf('1e-7')/resistance[-1])
    current=G*np.diff(F)
    np.testing.assert_allclose(current,expected,rtol=1e-10,atol=0)
    if nx==3:
        midpoint=Q*.02*100e-9/np.diff(x)*(density[:-1]+density[1:])/2*np.diff(F)
        assert np.max(abs(midpoint/expected))>1e6

@pytest.mark.parametrize('kind',['graphene','mos2'])
def test_coupled_fet_xz_refinement_and_ledger(kind):
    currents=[]
    for nx,nz in ((17,5),(33,9),(65,17)):
        sim=device(kind,True,nx=nx,nz=nz)
        result=sim.solve(**drive(sim,True),drain_voltage_V=.02,max_iter=120,tolerance=1e-12)
        ledgers(result);currents.append(result['terminal_currents_into_sheet_A']['drain'])
    assert abs(currents[2]-currents[1])<.7*abs(currents[1]-currents[0]),currents
    assert abs(currents[2]-currents[1])<.01*abs(currents[2]),currents

def test_invalid_scheme_rejected_and_zero_density_is_not_silently_clipped():
    with pytest.raises(ValueError):
        SheetDriftDiffusion([0.,1.],[0.,1.],graphene_sheet(),gate_capacitance_F_m2=.01,
            mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,transport_scheme='unknown')
    with pytest.raises(FloatingPointError):
        fitted_conductance(np.zeros(1),np.zeros(1),np.zeros(1),np.zeros(1),np.zeros(1),np.zeros(1),np.zeros(1),
            vt=VT,dispersion='parabolic',sign=1,prefactor=1.)
