"""Independent Fowler unit/polarity bridge and new commercial MOS evidence."""
from functools import lru_cache
import json, math
from pathlib import Path
import numpy as np
import pytest
from tcad.validation import sentaurus_fn_to_native, LimitingCaseTest
from tcad.core import PyDeviceSimulator

PARAMETERS=dict(Aw=1.23e-6,Bw=2.37e8,Ae=1.87e-7,Be=1.88e8,Gm=1.)


@pytest.mark.parametrize('sign',[-1,1])
@pytest.mark.parametrize('barrier',[.5,1.,3.15,10.])
def test_bridge_matches_cgs_law_and_write_erase_orientation(sign,barrier):
    config=sentaurus_fn_to_native(PARAMETERS,barrier_eV=barrier,semiconductor_to_gate_sign=sign)
    for field in [-2e9,-6e8,6e8,2e9]:
        branch='positive' if field>0 else 'negative'
        C=config['fn_C_'+branch];B=config['fn_B_'+branch]
        native=C*field**2*math.exp(-B*barrier**1.5/abs(field))
        suffix='e' if field*sign>0 else 'w'
        cgs_field=abs(field)/100
        commercial=PARAMETERS['A'+suffix]*cgs_field**2*math.exp(-PARAMETERS['B'+suffix]/cgs_field)*1e4
        assert native==pytest.approx(commercial,rel=2e-13,abs=0.)
    assert config['pf_C']==config['E_floor']==config['sigma_cap']==0.


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('orientation',[-1,1])
@pytest.mark.parametrize('field',[-5e8,5e8])
def test_bridge_drives_actual_native_flux_through_high_level_api(axis,orientation,field):
    from tcad import Simulator
    from tcad.mesh.structured_grid import StructuredGrid
    dimensions=[1,1,1];dimensions[axis]=3
    bounds=[(0.,1e-7),(0.,1e-7),(0.,1e-7)];bounds[axis]=(0.,2e-9)
    sim=Simulator(StructuredGrid(tuple(bounds),*dimensions));core=sim._sim
    core.set_mobility(np.zeros(3),np.zeros(3));core.set_doping(np.zeros(3))
    core.set_effective_dos(np.full(3,1e16),np.full(3,1e16));core.set_bandgap(np.full(3,6.))
    core.set_initial_guess(np.zeros(3),np.zeros(3),np.zeros(3))
    core.set_dirichlet_potential({0:0.,2:-field*2e-9})
    core.set_gummel_max_iter(50);core.set_tolerance(1e-12)
    sim.set_leakage(**sentaurus_fn_to_native(PARAMETERS,barrier_eV=3.15,
        semiconductor_to_gate_sign=orientation),leak_mask_override=np.ones(3,dtype=np.int8))
    state=core.solve();assert state['converged']
    suffix='e' if field*orientation>0 else 'w'
    expected=math.copysign(PARAMETERS['A'+suffix]*field**2*
                          math.exp(-100*PARAMETERS['B'+suffix]/abs(field)),field)
    np.testing.assert_allclose(state['Jleak_'+'xyz'[axis]][:-1],expected,rtol=2e-12,atol=0.)


@pytest.mark.parametrize('field',['Aw','Bw','Ae','Be','Gm'])
@pytest.mark.parametrize('bad',[True,np.nan,np.inf,-1.,'1'])
def test_invalid_or_unrepresentable_fowler_coefficients_are_rejected(field,bad):
    p=dict(PARAMETERS);p[field]=bad
    with pytest.raises(ValueError): sentaurus_fn_to_native(p,barrier_eV=3.15,semiconductor_to_gate_sign=1)


@pytest.mark.parametrize('bad',[{},dict(PARAMETERS,unused=0),dict(PARAMETERS,Gm=2.)])
def test_unsupported_mapping_is_not_silently_accepted(bad):
    with pytest.raises(ValueError): sentaurus_fn_to_native(bad,barrier_eV=3.15,semiconductor_to_gate_sign=1)


@pytest.mark.parametrize('barrier',[0.,-1.,True,np.nan,np.inf])
def test_invalid_barriers_are_rejected(barrier):
    with pytest.raises(ValueError): sentaurus_fn_to_native(PARAMETERS,barrier_eV=barrier,semiconductor_to_gate_sign=1)


@pytest.mark.parametrize('orientation',[0,2,True,'1',np.nan])
def test_orientation_must_be_explicit_and_signed(orientation):
    with pytest.raises(ValueError): sentaurus_fn_to_native(PARAMETERS,barrier_eV=3.15,semiconductor_to_gate_sign=orientation)


def test_conversion_does_not_lose_representable_results_to_intermediate_range_errors():
    p=dict(PARAMETERS,Bw=1e308,Be=1e308)
    result=sentaurus_fn_to_native(p,barrier_eV=1e300,semiconductor_to_gate_sign=1)
    assert result['fn_B_positive']==pytest.approx(1e-140,rel=1e-14,abs=0.)
    result=sentaurus_fn_to_native(dict(PARAMETERS,Bw=1e-300,Be=1e-300),
        barrier_eV=1e-300,semiconductor_to_gate_sign=1)
    assert result['fn_B_positive']==pytest.approx(1e152,rel=1e-14,abs=0.)


@pytest.mark.parametrize('value,barrier',[(1e-300,1e300),(1e300,1e-300)])
def test_unrepresentable_final_conversion_is_rejected(value,barrier):
    with pytest.raises(ValueError): sentaurus_fn_to_native(dict(PARAMETERS,Bw=value,Be=value),
        barrier_eV=barrier,semiconductor_to_gate_sign=1)


def fixture():
    return json.loads((Path(__file__).parent/'data/sentaurus_thin_oxide.json').read_text())


def build_mos(case,axis=0,h=5e-11):
    nsi=round(1e-8/h);nox=round(case['oxide_thickness_m']/h);size=nsi+nox+1
    shape=[1,1,1];shape[axis]=size
    spacing=[h]*3
    for coordinate,value in zip([i for i in range(3) if i!=axis],(1e-7,1e-6)):
        spacing[coordinate]=value
    sim=PyDeviceSimulator(*shape,*spacing);x=np.arange(size)*h
    getattr(sim,'set_'+'xyz'[axis]+'_positions')(x)
    active=np.arange(size)<=nsi;oxide=np.arange(size)>nsi
    eps=np.where(active,11.7,3.9)*8.8542e-12;sim.set_permittivity(eps)
    plus=np.r_[np.where(np.arange(size-1)<nsi,11.7,3.9)*8.8542e-12,eps[-1]]
    minus=np.r_[eps[0],plus[:-1]]
    arrays=[np.array([],dtype=float) for _ in range(6)];arrays[2*axis]=plus;arrays[2*axis+1]=minus
    sim.set_edge_permittivity(*arrays)
    fraction=active.astype(float);fraction[nsi]=.5;sim.set_charge_volume_fraction(fraction)
    sim.set_mobility(active*.1,active*.05);sim.set_doping(active*1e24)
    sim.set_effective_dos(np.full(size,2.8e25),np.full(size,1.04e25));sim.set_bandgap(np.full(size,1.12))
    sim.set_recombination(np.full(size,1e100),np.full(size,1e100))
    sim.set_thermal_voltage(1.380649e-23*300/1.602176634e-19)
    body=case['phi_body_V'];nn=case['body_n_m3'];pp=case['body_p_m3']
    sim.set_electron_bc({0:nn});sim.set_hole_bc({0:pp})
    sim.set_initial_guess(np.full(size,body),active*nn,active*pp)
    sim.set_gummel_max_iter(150);sim.set_tolerance(1e-10);sim.set_use_newton(True)
    config=sentaurus_fn_to_native(PARAMETERS,barrier_eV=3.15,semiconductor_to_gate_sign=1)
    sim.set_leakage(oxide.astype(np.int8),0,0,0,0,0,config['fn_phi_b'],0,0)
    sim.set_leakage_fn_polarity(*(config[k] for k in
        ['fn_C_positive','fn_B_positive','fn_C_negative','fn_B_negative']))
    return sim,x,nsi


@lru_cache(None)
def measure(name,axis=0,h=5e-11):
    case=next(c for c in fixture()['cases'] if c['name']==name)
    sim,x,interface=build_mos(case,axis,h)
    for voltage in np.linspace(0,case['bias_V'],6):
        sim.set_dirichlet_potential({0:case['phi_body_V'],len(x)-1:float(voltage)})
        state=sim.solve();assert state['converged'],(name,axis,voltage)
    field=-np.diff(state['phi'])[interface:]/np.diff(x)[interface:]
    leak=state['Jleak_'+'xyz'[axis]][interface:-1]
    np.testing.assert_allclose(field,np.full(len(field),field[-1]),rtol=1e-9,atol=0.)
    return dict(oxide_thickness_m=case['oxide_thickness_m'],bias_V=case['bias_V'],
        tunneling_current_A=float(-leak[-1]*case['area_m2']),oxide_field_V_m=float(field[-1]),
        interface_potential_V=float(state['phi'][interface]),converged=True)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('thickness',[5.,2.,1.,.5])
@pytest.mark.parametrize('voltage',[1.,-1.])
def test_real_mos_native_field_and_gate_fn_current_against_sentaurus(axis,thickness,voltage):
    case=next(c for c in fixture()['cases'] if c['model']=='fn' and np.isclose(c['mesh_max_step_m'],5e-11,rtol=1e-14,atol=0.)
              and c['oxide_thickness_m']==pytest.approx(thickness*1e-9,rel=1e-14) and c['bias_V']==voltage)
    measured=measure(case['name'],axis)
    assert measured['oxide_field_V_m']==pytest.approx(case['oxide_field_V_m'],rel=.003,abs=0.)
    assert measured['tunneling_current_A']==pytest.approx(case['gate_current_A'],rel=.15,abs=0.)


def test_direct_tunneling_reference_exposes_the_missing_constitutive_model():
    data=fixture();direct=[c for c in data['cases'] if c['model']=='direct']
    direct.sort(key=lambda c:c['oxide_thickness_m'],reverse=True)
    by_thickness={c['oxide_thickness_m']:c for c in direct}
    positive={c['oxide_thickness_m']:c for c in data['cases'] if c['model']=='fn' and c['bias_V']==1.
              and np.isclose(c['mesh_max_step_m'],5e-11,rtol=1e-14,atol=0.)}
    result=LimitingCaseTest('thin_oxide',tolerance=.15,limit_params=dict(
        thicknesses_m=[c['oxide_thickness_m'] for c in direct],bias_V=1.),runners=dict(
        limit=lambda sim,t:dict(measure(positive[t]['name'])),
        reference=lambda sim,t:dict(oxide_thickness_m=t,bias_V=1.,
            tunneling_current_A=by_thickness[t]['gate_current_A'],converged=True)),
        reference_source=data['source']+'; explicit Schenk DirectTunneling parameters').run(object)
    assert not result.passed and not result.details['numerical_agreement_validated']
    assert len(result.details['comparisons'])==4


def fn_limit_report(bias=1.,damage=False):
    data=fixture()
    cases=[c for c in data['cases'] if c['model']=='fn' and c['bias_V']==bias
           and np.isclose(c['mesh_max_step_m'],5e-11,rtol=1e-14,atol=0.)]
    cases.sort(key=lambda c:c['oxide_thickness_m'],reverse=True)
    lookup={c['oxide_thickness_m']:c for c in cases}
    def reference(sim,t):
        case=lookup[t]
        current=case['gate_current_A']*(100. if damage and t==cases[1]['oxide_thickness_m'] else 1.)
        return dict(oxide_thickness_m=t,bias_V=bias,tunneling_current_A=current,converged=True)
    return LimitingCaseTest('thin_oxide',tolerance=.15,limit_params=dict(
        thicknesses_m=[c['oxide_thickness_m'] for c in cases],bias_V=bias),runners=dict(
        limit=lambda sim,t:dict(measure(lookup[t]['name'])),reference=reference),
        reference_source=data['source']+'; matched local Fowler law, no direct-tunneling equivalence').run(object)


@pytest.mark.parametrize('bias',[1.,-1.])
def test_explicit_real_device_fn_limit_passes_and_middle_sample_damage_fails(bias):
    good=fn_limit_report(bias);bad=fn_limit_report(bias,True)
    assert good.passed,good.message
    assert good.details['numerical_agreement_validated'] and not good.details['physical_validated']
    assert not bad.passed and len(bad.details['comparisons'])==4
