"""Independent discrete PB solutions and honest, transactional seed acceptance."""
import math
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator

VT=0.02585
T=300.
Q=1.602176634e-19
KB_EV=8.617333262e-5


def manufactured(axis=0,amplitude=.4,sign=1,insulator=False):
    size=11;dimensions=[1,1,1];dimensions[axis]=size
    x=np.array([0.,.3,.9,1.7,2.6,3.8,5.2,6.1,7.,8.6,10.])*5e-9
    sim=PyDeviceSimulator(*dimensions,5e-9,5e-9,5e-9)
    getattr(sim,'set_'+'xyz'[axis]+'_positions')(x)
    faces=8.854187817e-12*np.array([11.7]*5+[3.9]*5)
    eps=np.full(size,8.854187817e-12*10.)
    sim.set_permittivity(eps)
    arrays=[np.array([],dtype=float) for _ in range(6)]
    arrays[2*axis]=np.r_[faces,faces[-1]];arrays[2*axis+1]=np.r_[faces[0],faces]
    sim.set_edge_permittivity(*arrays)
    fraction=np.ones(size);fraction[5]=.5
    if insulator: fraction[:]=0.
    sim.set_charge_volume_fraction(fraction)
    matrix=np.zeros((size,size));matrix[0,0]=matrix[-1,-1]=1.
    for i in range(1,size-1):
        width=(x[i+1]-x[i-1])/2
        left=faces[i-1]/((x[i]-x[i-1])*width)
        right=faces[i]/((x[i+1]-x[i])*width)
        matrix[i,i-1]=left;matrix[i,i+1]=right;matrix[i,i]=-left-right
    target=sign*(amplitude*np.sin(np.pi*x/x[-1])+.03*x/x[-1])
    if insulator:
        target=np.r_[0.,np.cumsum(np.diff(x)/faces)]
        target*=.3/target[-1]
    ni=1e22*math.exp(-.5/(2*KB_EV*T))
    n=ni*np.exp(target/VT);p=ni*np.exp(-target/VT)
    doping=n-p
    if not insulator:
        doping[1:-1]-=(matrix@target)[1:-1]/(Q*fraction[1:-1])
    else: doping[:]=0.
    sim.set_mobility(np.zeros(size),np.zeros(size));sim.set_doping(doping)
    sim.set_temperature(T);sim.set_thermal_voltage(VT)
    sim.set_effective_dos(np.full(size,1e22),np.full(size,1e22));sim.set_bandgap(np.full(size,.5))
    sim.set_dirichlet_potential({0:float(target[0]),size-1:float(target[-1])})
    return sim,dict(x=x,matrix=matrix,ni=ni,doping=doping,fraction=fraction,target=target)


def independent_residual(state,data):
    phi=state['phi'];n=state['n'];p=state['p'];A=data['matrix'];f=data['fraction'];d=data['doping']
    rhs=-Q*f*(p-n+d);rhs[0]=data['target'][0];rhs[-1]=data['target'][-1]
    scale=VT*np.sum(abs(A),axis=1)+Q*f*(n+p+abs(d))
    scale[[0,-1]]=VT
    return float(np.max(abs(A@phi-rhs)/scale))


def inspect_seed(sim):
    sim.set_use_newton(True);sim.set_newton_primary(True);sim.set_gummel_max_iter(0)
    return sim.solve()


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('amplitude',[.02,.4])
@pytest.mark.parametrize('sign',[-1,1])
def test_manufactured_pb_state_satisfies_independent_equations(axis,amplitude,sign):
    sim,data=manufactured(axis,amplitude,sign)
    r=sim.solve_equilibrium()
    assert r['converged'] and r['initial_guess_committed'] and r['status']=='converged'
    assert r['iterations']>1 and len(r['residual_history'])==r['iterations']+1
    assert len(r['update_history_V'])==len(r['damping_history'])==r['iterations']
    assert r['residual_history'][-1]<=1e-10 and r['update_history_V'][-1]<=VT*1e-10
    assert np.all((r['damping_history']>0)&(r['damping_history']<=1))
    np.testing.assert_allclose(r['phi'],data['target'],rtol=0,atol=2e-11)
    np.testing.assert_allclose(r['n'],data['ni']*np.exp(r['phi']/VT),rtol=3e-14)
    np.testing.assert_allclose(r['p'],data['ni']*np.exp(-r['phi']/VT),rtol=3e-14)
    assert independent_residual(r,data)<1.01e-10
    assert not r['physical_validated']


@pytest.mark.parametrize('axis',[0,1,2])
def test_zero_budget_reports_actual_initial_residual_and_does_not_commit(axis):
    sim,data=manufactured(axis)
    r=sim.solve_equilibrium(max_iter=0)
    assert not r['converged'] and not r['initial_guess_committed'] and r['status']=='max_iter'
    assert r['iterations']==0 and len(r['residual_history'])==1
    assert r['update_history_V'].size==r['damping_history'].size==0
    assert r['residual_history'][0]==pytest.approx(independent_residual(r,data),rel=2e-12,abs=2e-15)
    assert r['residual_history'][0]>1e-3


@pytest.mark.parametrize('axis',[0,1,2])
def test_success_commits_a_copy_and_failed_budget_preserves_previous_seed(axis):
    sim,data=manufactured(axis)
    accepted=sim.solve_equilibrium();assert accepted['converged']
    saved={key:accepted[key].copy() for key in ('phi','n','p')}
    for key in saved: accepted[key][:]=-999
    failed=sim.solve_equilibrium(max_iter=1)
    assert not failed['converged'] and not failed['initial_guess_committed']
    state=inspect_seed(sim)
    for key in saved: np.testing.assert_array_equal(state[key],saved[key])


@pytest.mark.parametrize('axis',[0,1,2])
def test_dielectric_series_capacitor_has_no_spurious_mobile_charge(axis):
    sim,data=manufactured(axis,insulator=True)
    r=sim.solve_equilibrium();assert r['converged']
    np.testing.assert_allclose(r['phi'],data['target'],rtol=0,atol=1e-13)
    np.testing.assert_array_equal(r['n'],np.zeros(11));np.testing.assert_array_equal(r['p'],np.zeros(11))


@pytest.mark.parametrize('sign',[-1,1])
def test_no_density_floor_or_exponent_clipping_is_substituted_for_pb(sign):
    sim=PyDeviceSimulator(5,1,1,1e-9,1e-9,1e-9)
    sim.set_temperature(T);sim.set_thermal_voltage(VT)
    sim.set_effective_dos(np.full(5,1e15),np.full(5,1e15));sim.set_bandgap(np.full(5,2.))
    ni=1e15*math.exp(-2./(2*KB_EV*T));net=sign*1e24
    majority=.5*(abs(net)+math.sqrt(net*net+4*ni*ni))
    phi=sign*VT*math.log(majority/ni)
    assert abs(phi/VT)>50
    sim.set_doping(np.full(5,net));sim.set_dirichlet_potential({0:phi,4:phi})
    r=sim.solve_equilibrium();assert r['converged']
    np.testing.assert_allclose(r['phi'],phi,rtol=0,atol=1e-13)
    minority=r['p'] if sign>0 else r['n']
    assert np.all((minority>0)&(minority<1))
    np.testing.assert_allclose(r['n']*r['p'],ni*ni,rtol=2e-14,atol=0.)


def test_representable_wide_gap_intrinsic_density_is_not_replaced_by_a_floor():
    sim=PyDeviceSimulator(3,1,1,1e-9,1e-9,1e-9)
    sim.set_temperature(T);sim.set_thermal_voltage(VT)
    sim.set_effective_dos(np.full(3,1e25),np.full(3,1e25));sim.set_bandgap(np.full(3,30.))
    sim.set_dirichlet_potential({0:0.,2:0.})
    ni=math.exp(math.log(1e25)-30./(2*KB_EV*T))
    assert 0<ni<1e-200
    r=sim.solve_equilibrium();assert r['converged'] and r['iterations']==0
    np.testing.assert_allclose(r['n'],ni,rtol=2e-12,atol=0.)
    np.testing.assert_allclose(r['p'],ni,rtol=2e-12,atol=0.)


@pytest.mark.parametrize('axis',[0,1,2])
def test_inactive_dielectric_does_not_require_semiconductor_dos(axis):
    sim,data=manufactured(axis,insulator=True)
    sim.set_effective_dos(np.zeros(11),np.zeros(11))
    r=sim.solve_equilibrium();assert r['converged']
    np.testing.assert_allclose(r['phi'],data['target'],rtol=0,atol=1e-13)
    np.testing.assert_array_equal(r['n'],np.zeros(11))


@pytest.mark.parametrize('value',[-1,True,1.5,'2',np.nan])
def test_invalid_budget_rejected(value):
    sim,_=manufactured()
    with pytest.raises(ValueError): sim.solve_equilibrium(max_iter=value)


@pytest.mark.parametrize('value',[0.,-1.,True,np.nan,np.inf,'1e-10'])
def test_invalid_tolerance_rejected(value):
    sim,_=manufactured()
    with pytest.raises(ValueError): sim.solve_equilibrium(tolerance=value)


@pytest.mark.parametrize('field,value',[('VT',0.),('VT',np.nan),('temperature',0.),
    ('Nc',0.),('Nv',-1.),('Eg',-1.),('doping',np.nan),('eps',np.nan),('fraction',np.nan)])
def test_invalid_material_fields_rejected_without_replacing_seed(field,value):
    sim,_=manufactured()
    accepted=sim.solve_equilibrium();assert accepted['converged']
    setters=dict(VT=lambda:sim.set_thermal_voltage(value),temperature=lambda:sim.set_temperature(value),
        Nc=lambda:sim.set_effective_dos(np.full(11,value),np.full(11,1e22)),
        Nv=lambda:sim.set_effective_dos(np.full(11,1e22),np.full(11,value)),
        Eg=lambda:sim.set_bandgap(np.full(11,value)),doping=lambda:sim.set_doping(np.full(11,value)),
        eps=lambda:sim.set_permittivity(np.full(11,value)),
        fraction=lambda:sim.set_charge_volume_fraction(np.full(11,value)))
    if field in ('VT','temperature','doping','eps','fraction'):
        with pytest.raises(ValueError): setters[field]()
    else:
        setters[field]()
        with pytest.raises(ValueError): sim.solve_equilibrium()
    sim.set_temperature(T);sim.set_thermal_voltage(VT)
    sim.set_effective_dos(np.full(11,1e22),np.full(11,1e22));sim.set_bandgap(np.full(11,.5))
    _,data=manufactured()
    sim.set_doping(data['doping']);sim.set_permittivity(np.full(11,8.854187817e-12*10.))
    sim.set_charge_volume_fraction(data['fraction'])
    state=inspect_seed(sim)
    for key in ('phi','n','p'): np.testing.assert_array_equal(state[key],accepted[key])


@pytest.mark.parametrize('kind',['fd','ohmic','no_anchor','nonfinite_bc','n_bc','p_bc','interior_bc','unrepresentable'])
def test_unsupported_or_incompatible_equilibrium_configuration_rejected(kind):
    sim,_=manufactured()
    if kind=='fd': sim.set_statistics_type(1)
    elif kind=='ohmic': sim.set_ohmic_contacts([0],{0:0.},{0:0.},1.)
    elif kind=='no_anchor': sim=PyDeviceSimulator(3,1,1,1e-9,1e-9,1e-9)
    elif kind=='nonfinite_bc':
        with pytest.raises(ValueError): sim.set_dirichlet_potential({0:np.nan,10:0.})
        return
    elif kind=='n_bc': sim.set_electron_bc({0:1e30})
    elif kind=='p_bc': sim.set_hole_bc({0:1e30})
    elif kind=='interior_bc': sim.set_electron_bc({5:1.})
    else: sim.set_dirichlet_potential({0:100.,10:0.})
    with pytest.raises(ValueError): sim.solve_equilibrium()


def mos_pb_case(case,axis=0):
    from test_sentaurus_fn import build_mos
    sim,x,interface=build_mos(case,axis)
    vt=1.380649e-23*T/Q
    ni=math.sqrt(2.8e25*1.04e25)*math.exp(-1.12/(2*KB_EV*T))
    # Native and SDevice fundamental constants give a ~7 ppm difference in
    # the minority reservoir. Declare the native PB reservoir analytically;
    # share the electrostatic boundary, without fitting any material parameter.
    sim.set_electron_bc({0:ni*math.exp(case['phi_body_V']/vt)})
    sim.set_hole_bc({0:ni*math.exp(-case['phi_body_V']/vt)})
    sim.set_dirichlet_potential({0:case['phi_body_V'],len(x)-1:case['bias_V']})
    return sim,x,interface


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('thickness',[5.,2.,1.,.5])
@pytest.mark.parametrize('bias',[1.,-1.])
def test_pb_mos_electrostatics_against_actual_sentaurus_reference(axis,thickness,bias):
    from test_sentaurus_fn import fixture
    case=next(c for c in fixture()['cases'] if c['model']=='fn' and c['bias_V']==bias
        and np.isclose(c['oxide_thickness_m'],thickness*1e-9,rtol=1e-14,atol=0.)
        and np.isclose(c['mesh_max_step_m'],5e-11,rtol=1e-14,atol=0.))
    sim,x,interface=mos_pb_case(case,axis)
    r=sim.solve_equilibrium();assert r['converged'],(case['name'],r['status'])
    field=-np.diff(r['phi'])[interface:]/np.diff(x)[interface:]
    np.testing.assert_allclose(field,case['oxide_field_V_m'],rtol=.003,atol=0.)
    np.testing.assert_allclose(field,field[-1],rtol=1e-9,atol=0.)
