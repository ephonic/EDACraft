"""Declared field parity must be checked against measured, independent runs."""
from types import SimpleNamespace
import json
from pathlib import Path
import numpy as np
import pytest
from tcad.validation.symmetry import SymmetryTest
from tcad.validation.reference import ReferenceComparisonTest


def execute(check,result):
    return check.run(lambda:SimpleNamespace(run=lambda:result))


@pytest.mark.parametrize('kind',['geometric','voltage_reversal','ferroelectric'])
def test_unconfigured_symmetry_never_executes_a_default_model(kind):
    calls=[]
    def builder():
        calls.append(1)
        return SimpleNamespace(run=lambda:SimpleNamespace())
    report=SymmetryTest(kind).run(builder)
    assert not report.passed and not calls


@pytest.mark.parametrize('shape',[(2,2),(2,3,4)])
def test_multidimensional_asymmetry_cannot_return_zero_error(shape):
    result=SimpleNamespace(phi=np.arange(np.prod(shape)).reshape(shape))
    assert not execute(SymmetryTest('geometric'),result).passed


@pytest.mark.parametrize('value',[np.nan,np.inf,-1.,0.,True])
def test_invalid_tolerance_is_rejected(value):
    with pytest.raises(ValueError):SymmetryTest('geometric',tolerance=value)


def test_unknown_symmetry_is_configuration_error():
    with pytest.raises(ValueError):SymmetryTest('unknown')


def geometric(result,**kwargs):
    config=dict(relations={'phi':('phi',1)},protocol='declared uniform-grid reflection',axis=0,tolerance=1e-8)
    config.update(kwargs)
    return execute(SymmetryTest('geometric',**config),result)


def measurements(kind,side):
    sign=1. if side=='positive' else -1.
    if kind=='voltage_reversal':
        return dict(phi=sign*np.array([.1,.2]),n=np.array([1.,2.] if sign>0 else [3.,4.]),
                    p=np.array([3.,4.] if sign>0 else [1.,2.]),bias_V=sign*np.array([1.,.5]),valid=True)
    return dict(P=sign*np.array([0.,.2,-.1]),Q=sign*np.array([0.,1e-18,-2e-18]),
                voltage_V=sign*np.array([0.,1.,-1.]),times_s=np.array([0.,1.,2.]),valid=True)


def paired(kind='voltage_reversal',corrupt=None,**kwargs):
    relations=({'phi':('phi',-1),'n':('p',1),'p':('n',1)} if kind=='voltage_reversal'
               else {'P':('P',-1),'Q':('Q',-1)})
    def run(sim,side):
        result=measurements(kind,side)
        if side=='negative' and corrupt:corrupt(result)
        return result
    config=dict(relations=relations,protocol='synthetic explicitly symmetric control',tolerance=1e-8,
        runners={side:lambda sim,side=side:run(sim,side) for side in ('positive','negative')})
    config.update(kwargs)
    return SymmetryTest(kind,**config).run(object)


@pytest.mark.parametrize('shape,axis',[( (2,3),0),((2,3),1),((3,4,5),0),((3,4,5),1),((3,4,5),2),((2,3,4,5),-1)])
def test_multidimensional_reflection_checks_actual_field_and_detects_damage(shape,axis):
    values=np.arange(np.prod(shape),dtype=float).reshape(shape)+1.
    values+=np.flip(values,axis=axis)
    assert geometric({'phi':values},axis=axis).passed
    values.flat[0]*=1.01
    assert not geometric({'phi':values},axis=axis).passed


@pytest.mark.parametrize('count',[2,3,4,5,8])
@pytest.mark.parametrize('sign',[-1,1])
def test_scalar_even_and_odd_reflections_include_all_nodes(count,sign):
    x=np.linspace(-1.,1.,count)
    values=x if sign<0 else x*x
    assert geometric({'phi':values},relations={'phi':('phi',sign)}).passed
    values[0]+=.01
    assert not geometric({'phi':values},relations={'phi':('phi',sign)}).passed


def test_odd_center_is_checked_instead_of_being_truncated():
    assert not geometric({'phi':[-1.,.01,1.]},relations={'phi':('phi',-1)}).passed


def test_reflection_field_component_parities_are_explicit():
    result=dict(phi=[1.,2.,1.],Ex=[-1.,0.,1.],Ey=[2.,3.,2.])
    relations={'phi':('phi',1),'Ex':('Ex',-1),'Ey':('Ey',1)}
    assert geometric(result,relations=relations).passed
    result['Ex'][1]=.01
    assert not geometric(result,relations=relations).passed


def test_unstructured_node_order_needs_explicit_involutive_permutation():
    result={'phi':[1.,2.,1.,2.]}
    assert geometric(result,permutation=[2,3,0,1]).passed
    assert not geometric(result).passed


@pytest.mark.parametrize('bad',[None,[],[np.nan,1.],[np.inf,1.],[True,False],['1','2']])
def test_geometric_fields_must_be_actual_finite_real_measurements(bad):
    result={} if bad is None else {'phi':bad}
    assert not geometric(result).passed


@pytest.mark.parametrize('field',['valid','converged'])
@pytest.mark.parametrize('value',[False,1,None,'true'])
def test_supplied_failure_or_nonboolean_status_is_rejected(field,value):
    assert not geometric({'phi':[1.,1.],field:value}).passed
    assert not paired(corrupt=lambda r:r.update({field:value})).passed


@pytest.mark.parametrize('kind',['voltage_reversal','ferroelectric'])
def test_paired_measurements_pass_without_certifying_physical_hypothesis(kind):
    report=paired(kind)
    assert report.passed,report.message
    assert report.details['numerical_symmetry_validated']
    for key in ('physical_validated','symmetry_hypothesis_validated','global_temporal_error_validated'):
        assert not report.details[key]


@pytest.mark.parametrize('kind,field',[('voltage_reversal','phi'),('voltage_reversal','n'),
    ('voltage_reversal','p'),('ferroelectric','P'),('ferroelectric','Q')])
@pytest.mark.parametrize('bad',[None,[np.nan],[]])
def test_missing_or_invalid_paired_fields_never_become_zero(kind,field,bad):
    def corrupt(result):
        if bad is None:result.pop(field)
        else:result[field]=bad
    assert not paired(kind,corrupt=corrupt).passed


@pytest.mark.parametrize('kind,field',[('voltage_reversal','phi'),('voltage_reversal','n'),
    ('ferroelectric','P'),('ferroelectric','Q')])
def test_paired_shape_broadcasting_is_forbidden(kind,field):
    assert not paired(kind,corrupt=lambda r:r.update({field:r[field][:1]})).passed


@pytest.mark.parametrize('kind',['voltage_reversal','ferroelectric'])
@pytest.mark.parametrize('fault',['missing','same_sign','zero','shape'])
def test_drive_metadata_must_match_actual_opposite_nonzero_controls(kind,fault):
    field='bias_V' if kind=='voltage_reversal' else 'voltage_V'
    def corrupt(result):
        if fault=='missing':result.pop(field)
        elif fault=='same_sign':result[field]*=-1.
        elif fault=='zero':result[field]*=0.
        else:result[field]=result[field][:1]
    assert not paired(kind,corrupt=corrupt).passed


@pytest.mark.parametrize('clock',[None,[0.,1.,3.],[0.,1.,1.],[-1.,1.,2.],[.1,1.,2.],[0.,1.]])
def test_fe_histories_require_the_same_strict_clock_starting_at_zero(clock):
    def corrupt(result):
        if clock is None:result.pop('times_s')
        else:result['times_s']=clock
    assert not paired('ferroelectric',corrupt=corrupt).passed


def test_a_reversed_hysteresis_branch_is_not_a_paired_drive_experiment():
    def reverse(result):
        result['P']=result['P'][::-1]
        result['voltage_V']=result['voltage_V'][::-1]
    assert not paired('ferroelectric',corrupt=reverse).passed


@pytest.mark.parametrize('kind,key',[('voltage_reversal','phi'),('ferroelectric','P')])
def test_all_zero_response_is_inconclusive(kind,key):
    def run(side):
        result=measurements(kind,side);result[key]*=0.
        return result
    report=paired(kind,runners={side:lambda sim,side=side:run(side) for side in ('positive','negative')})
    assert not report.passed and report.details['inconclusive']


def test_electron_hole_exchange_is_not_assumed_when_only_potential_is_declared():
    def run(side):
        result=measurements('voltage_reversal',side)
        result.pop('n');result.pop('p')
        return result
    report=paired(relations={'phi':('phi',-1)},runners={
        side:lambda sim,side=side:run(side) for side in ('positive','negative')})
    assert report.passed,report.message


@pytest.mark.parametrize('kind',['voltage_reversal','ferroelectric'])
def test_reusing_simulator_or_result_is_rejected(kind):
    same=object()
    config=dict(relations={'phi':('phi',-1)} if kind=='voltage_reversal' else {'P':('P',-1)},
        protocol='alias check',runners={side:lambda sim,side=side:measurements(kind,side) for side in ('positive','negative')})
    assert not SymmetryTest(kind,**config).run(lambda:same).passed
    shared=measurements(kind,'positive')
    config['runners']={'positive':lambda sim:shared,'negative':lambda sim:shared}
    assert not SymmetryTest(kind,**config).run(object).passed


@pytest.mark.parametrize('scale',[1e-300,1e300])
def test_signal_budget_has_no_implicit_unit_floor_or_subtraction_overflow(scale):
    assert geometric({'phi':[scale,scale]}).passed
    assert not geometric({'phi':[scale,.99*scale]}).passed
    report=geometric({'phi':[scale,.99*scale]},atol={'phi':.02*scale})
    assert report.passed


def test_geometric_history_reflects_space_and_preserves_time():
    result=dict(phi=[[1.,2.,1.],[3.,4.,3.]],times_s=[0.,1.])
    assert geometric(result,axis=1).passed
    assert not geometric(result,axis=0).passed


@pytest.mark.parametrize('kwargs',[
    {'relations':{}},{'relations':{'phi':('phi',0)}},{'relations':{'phi':('phi',True)}},
    {'relations':{'phi':('phi',1.)}},{'relations':{'n':('p',1)}},
    {'relations':{'n':('p',1),'p':('n',-1)}},{'relations':{'time_s':('time_s',1)}},
    {'axis':True},{'axis':.5},{'permutation':[0,0]},{'permutation':[1.,0.]},
    {'permutation':[0,1]},{'permutation':[1,2,0]},{'protocol':''},
    {'runner':1},{'atol':{'phi':np.nan}},{'atol':{'other':0.}}])
def test_invalid_mapping_and_budget_configuration_is_rejected(kwargs):
    config=dict(relations={'phi':('phi',1)},axis=0,protocol='test')
    config.update(kwargs)
    with pytest.raises(ValueError):SymmetryTest('geometric',**config)


@pytest.mark.parametrize('axis',[-3,2,3])
def test_out_of_range_axes_fail_without_guessing_layout(axis):
    assert not geometric({'phi':np.zeros((2,2))},axis=axis).passed


def test_permutation_length_cannot_be_broadcast():
    assert not geometric({'phi':[1.,1.,1.]},permutation=[1,0]).passed


def test_scalar_and_single_node_fields_cannot_establish_geometric_reflection():
    for value in (1.,[1.]):assert not geometric({'phi':value}).passed


def test_framework_forwards_explicit_protocol_and_native_runner():
    from tcad.validation import ValidationFramework
    class NativeAPI:
        def solve(self):return {'phi':[1.,2.,1.]}
    framework=ValidationFramework(NativeAPI)
    framework.add_symmetry_test('geometric',relations={'phi':('phi',1)},axis=0,
        protocol='declared mirror plane',runner=lambda sim:sim.solve(),atol={'phi':0.})
    assert framework.run_all()[0].passed


def native_spatial_check(axis,corrupt=False):
    from tcad.core import PyDeviceSimulator
    shape=[3,3,3];shape[axis]=9
    count=int(np.prod(shape));spacing=1e-8;length=8*spacing
    z,y,x=np.indices(tuple(shape[::-1]));coordinate=(x,y,z)[axis].reshape(-1)*spacing
    amplitude,eps,q=1e-3,8.854187817e-12*11.7,1.602176634e-19
    k=np.pi/length;source=eps*k*k*amplitude/q*np.sin(k*coordinate)
    sim=PyDeviceSimulator(*shape,spacing,spacing,spacing)
    sim.set_permittivity(np.full(count,eps));sim.set_mobility(np.zeros(count),np.zeros(count))
    sim.set_doping(source);sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16))
    sim.set_bandgap(np.full(count,6.));sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
    boundary=np.flatnonzero((coordinate==0.)|(coordinate==length))
    sim.set_dirichlet_potential({int(i):0. for i in boundary})
    sim.set_electron_bc({int(i):0. for i in boundary});sim.set_hole_bc({int(i):0. for i in boundary})
    sim.set_initial_guess(np.zeros(count),np.zeros(count),np.zeros(count))
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-12)
    actual=sim.solve();assert actual['converged']
    expected=amplitude*np.sin(k*coordinate)*(k*spacing)**2/(4*np.sin(k*spacing/2)**2)
    np.testing.assert_allclose(actual['phi'],expected,atol=1e-12,rtol=1e-8)
    actual={key:actual[key].reshape(tuple(shape[::-1])) for key in ('phi','Ex','Ey','Ez')}
    if corrupt:actual['phi'].flat[0]=amplitude*.01
    relations={'phi':('phi',1),**{field:(field,-1 if i==axis else 1) for i,field in enumerate(('Ex','Ey','Ez'))}}
    return SymmetryTest('geometric',relations=relations,axis=2-axis,
        protocol='uniform Cartesian Poisson sine source, symmetric boundary planes; x-fast layout reshaped z/y/x',
        tolerance=1e-8,atol={'phi':1e-12,'Ex':1e-6,'Ey':1e-6,'Ez':1e-6},
        runner=lambda sim:actual).run(object)


@pytest.mark.parametrize('axis',[0,1,2])
def test_native_3d_sine_potential_and_vector_field_reflection(axis):
    report=native_spatial_check(axis)
    assert report.passed,report.message+str(report.details)


@pytest.mark.parametrize('axis',[0,1,2])
def test_native_asymmetry_damage_is_rejected_in_each_spatial_direction(axis):
    assert not native_spatial_check(axis,True).passed


def native_voltage_check(axis,corrupt=False):
    from tcad.core import PyDeviceSimulator
    count,length=9,8e-8
    field=('Ex','Ey','Ez')[axis]
    def builder():
        shape=[1,1,1];shape[axis]=count
        sim=PyDeviceSimulator(*shape,1e-8,1e-8,1e-8)
        sim.set_permittivity(np.full(count,8.854187817e-12*11.7))
        sim.set_mobility(np.zeros(count),np.zeros(count));sim.set_doping(np.zeros(count))
        sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16));sim.set_bandgap(np.full(count,6.))
        sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
        sim.set_electron_bc({0:0.,count-1:0.});sim.set_hole_bc({0:0.,count-1:0.})
        sim.set_gummel_max_iter(100);sim.set_tolerance(1e-12)
        return sim
    def run(sim,side):
        voltage=.2 if side=='positive' else -.2
        sim.set_dirichlet_potential({0:0.,count-1:voltage})
        sim.set_initial_guess(np.linspace(0.,voltage,count),np.zeros(count),np.zeros(count))
        result=sim.solve();assert result['converged']
        np.testing.assert_allclose(result['phi'],np.linspace(0.,voltage,count),rtol=1e-12,atol=1e-14)
        np.testing.assert_allclose(result[field],-voltage/length,rtol=1e-12,atol=1e-6)
        result['bias_V']=voltage
        if corrupt and side=='negative':result['phi'][count//2]*=1.01
        return result
    return SymmetryTest('voltage_reversal',relations={'phi':('phi',-1),field:(field,-1)},
        protocol='independent zero-net-space-charge dielectric runs, same mesh, opposite boundary voltage, zero potential origin',
        tolerance=1e-8,atol={'phi':1e-12,field:1e-6},runners={
            side:lambda sim,side=side:run(sim,side) for side in ('positive','negative')}).run(builder)


@pytest.mark.parametrize('axis',[0,1,2])
def test_native_voltage_reversal_in_each_direction(axis):
    report=native_voltage_check(axis)
    assert report.passed,report.message+str(report.details)


@pytest.mark.parametrize('axis',[0,1,2])
def test_native_paired_potential_damage_is_rejected(axis):
    assert not native_voltage_check(axis,True).passed


COMMERCIAL=json.loads((Path(__file__).parent/'data/sentaurus_lk_symmetry.json').read_text())


def build_native_lk(case):
    from tcad.core import PyDeviceSimulator
    sim=PyDeviceSimulator(9,1,1,COMMERCIAL['length_m']/8,1e-7,1e-6)
    sim.set_permittivity(np.full(9,COMMERCIAL['epsilon_F_m']))
    sim.set_mobility(np.zeros(9),np.zeros(9));sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9,1e16),np.full(9,1e16));sim.set_bandgap(np.full(9,6.))
    sim.set_recombination(np.full(9,1e100),np.full(9,1e100));sim.set_dirichlet_potential({0:0.,8:0.})
    sim.set_initial_guess(np.zeros(9),np.zeros(9),np.zeros(9));sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_model(0);sim.set_ferroelectric_polar_axis(0)
    sim.set_ferroelectric_params(np.ones(9,dtype=np.int8),case['alpha'],case['beta'])
    sim.set_ferroelectric_gamma(case['rho']);sim.set_transient_lk_coupled(True)
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    return sim


def run_native_lk(sim,case,side):
    data=case[side];times=np.array(data['times_s']);voltage=np.array(data['voltage_V'])
    sim.set_transient_dt(float(times[-1]));sim.set_transient_t_final(float(times[-1]))
    sim.set_transient_voltage_waveforms(times,{8:voltage})
    states=sim.solve_transient()
    assert all(state['valid'] for state in states)
    np.testing.assert_array_equal([state['time_s'] for state in states],times)
    full_p=np.array([state['P'].reshape(9,3)[:,0] for state in states])
    mean=full_p.mean(axis=1)
    np.testing.assert_allclose(full_p,np.repeat(mean[:,None],9,axis=1),rtol=1e-12,atol=1e-15)
    return dict(P=mean,Q=np.array([state['electrode_charges_C'][1] for state in states]),
        I=np.array([state['electrode_total_currents_A'][1] for state in states[1:]]),
        times_s=times,interval_times_s=times[1:],voltage_V=voltage,valid=True)


def commercial_measurement(case,side):
    data=case[side]
    return dict(P=np.array(data['sentaurus_P_C_m2']),Q=np.array(data['sentaurus_top_Q_C']),
        I=np.array(data['sentaurus_interval_I_A']),times_s=np.array(data['times_s']),
        interval_times_s=np.array(data['interval_times_s']),voltage_V=np.array(data['voltage_V']),valid=True)


def commercial_symmetry_check(case,engine='sentaurus',damage=None):
    def runner(sim,side):
        result=run_native_lk(sim,case,side) if engine=='native' else commercial_measurement(case,side)
        if damage and side=='negative':result[damage][len(result[damage])//2]+=.01*max(abs(result[damage]))
        return result
    return SymmetryTest('ferroelectric',relations={'P':('P',-1),'Q':('Q',-1)},tolerance=1e-7,
        protocol='independent zero-initial-P cubic local LK, g=sextic=0; centrosymmetric free energy; opposite full waveforms',
        runners={side:lambda sim,side=side:runner(sim,side) for side in ('positive','negative')}
        ).run((lambda:build_native_lk(case)) if engine=='native' else object)


@pytest.mark.parametrize('case',COMMERCIAL['cases'],ids=lambda c:c['name'])
@pytest.mark.parametrize('engine',['sentaurus','native'])
def test_independent_commercial_and_native_histories_obey_declared_symmetry(case,engine):
    report=commercial_symmetry_check(case,engine)
    assert report.passed,report.message+str(report.details)


@pytest.mark.parametrize('case',COMMERCIAL['cases'],ids=lambda c:c['name'])
@pytest.mark.parametrize('field',['P','Q'])
def test_one_percent_commercial_measurement_damage_breaks_declared_symmetry(case,field):
    assert not commercial_symmetry_check(case,damage=field).passed


@pytest.mark.parametrize('case',COMMERCIAL['cases'],ids=lambda c:c['name'])
@pytest.mark.parametrize('side',['positive','negative'])
def test_native_matches_new_commercial_polarization_charge_and_interval_current(case,side):
    actual=run_native_lk(build_native_lk(case),case,side);reference=commercial_measurement(case,side)
    check=ReferenceComparisonTest(lambda:actual,lambda:reference,fields=('P','Q'),rtol=1e-7,
        reference_source='new independent opposite-drive Sentaurus W-2024.09 run').run()
    assert check.passed,check.message
    check=ReferenceComparisonTest(
        lambda:dict(I=actual['I'],times_s=actual['interval_times_s']),
        lambda:dict(I=reference['I'],times_s=reference['interval_times_s']),fields=('I',),rtol=1e-7,
        reference_source='raw commercial current on accepted noninitial BE intervals').run()
    assert check.passed,check.message


@pytest.mark.parametrize('case',COMMERCIAL['cases'],ids=lambda c:c['name'])
@pytest.mark.parametrize('damage',[False,True])
def test_commercial_interval_current_symmetry_excludes_undefined_initial_current(case,damage):
    positive=commercial_measurement(case,'positive');negative=commercial_measurement(case,'negative')
    if damage:negative['I'][len(negative['I'])//2]+=.01*max(abs(negative['I']))
    report=ReferenceComparisonTest(
        lambda:dict(I=positive['I'],times_s=positive['interval_times_s']),
        lambda:dict(I=-negative['I'],times_s=negative['interval_times_s']),fields=('I',),rtol=1e-7,
        reference_source='independent sign-reversed commercial currents, excluding initial state').run()
    assert report.passed is not damage,report.message
