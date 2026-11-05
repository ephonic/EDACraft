"""Limit checks must measure the stated condition instead of inventing data."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
from tcad.validation import LimitingCaseTest, ValidationFramework

KINDS=['no_ferroelectric','no_traps','high_temperature','thin_oxide']


@pytest.mark.parametrize('kind',KINDS)
def test_unspecified_limit_execution_cannot_pass_or_run(kind):
    def forbidden(): pytest.fail('must reject absent controls before building')
    result=LimitingCaseTest(kind).run(forbidden)
    assert not result.passed and result.details['unsupported']
    assert not result.details['physical_validated']


def measurements(kind,side,coordinate=None):
    result=dict(phi=[0.,1.],n=[1e16,2e16],p=[2e16,1e16],P=[0.,0.],converged=True)
    if kind=='no_ferroelectric':
        result.update(ferroelectric_enabled=side=='limit',ferroelectric_active_nodes=0)
    elif kind=='no_traps':
        result.update(traps_enabled=side=='limit',trap_density_m2_eV=0.,oxide_trap_charge_C_m3=[0.,0.])
    elif kind=='high_temperature':
        result.update(temperature_K=1000.,quantum_enabled=side=='limit')
    else:
        result.update(oxide_thickness_m=coordinate,bias_V=1.,tunneling_current_A=1e-9*np.exp(-coordinate/1e-9))
    return result


def check(kind,mutation=None,**kwargs):
    def limit(sim,*coords):
        r=measurements(kind,'limit',*coords)
        if mutation: mutation(r)
        return r
    def reference(sim,*coords): return measurements(kind,'reference',*coords)
    config=dict(runners={'limit':limit,'reference':reference},reference_source='independent measured reference')
    config.update(kwargs)
    return LimitingCaseTest(kind,**config).run(object)


@pytest.mark.parametrize('kind',KINDS)
def test_explicit_matched_conditions_pass_without_certifying_physics(kind):
    result=check(kind)
    assert result.passed, result.message
    assert result.details['numerical_agreement_validated']
    assert not result.details['physical_validated']
    assert not result.details['reference_authenticity_validated']
    assert not result.details['constitutive_equivalence_validated']


@pytest.mark.parametrize('kind',KINDS)
@pytest.mark.parametrize('mutation',[lambda r:r.update(converged=False),lambda r:r.clear()])
def test_failed_or_missing_results_cannot_pass(kind,mutation):
    assert not check(kind,mutation).passed


@pytest.mark.parametrize('field',['n','p'])
def test_high_temperature_compares_both_carriers_at_the_same_temperature(field):
    assert not check('high_temperature',lambda r:r.update(temperature_K=300.)).passed
    assert not check('high_temperature',lambda r:r[field].__setitem__(0,9e16)).passed


@pytest.mark.parametrize('kind,field',[('high_temperature','quantum_enabled'),
    ('no_ferroelectric','ferroelectric_enabled'),('no_traps','traps_enabled')])
@pytest.mark.parametrize('bad',[False,1,'true'])
def test_condition_switch_must_be_explicit_and_correct(kind,field,bad):
    assert not check(kind,lambda r:r.update({field:bad})).passed


@pytest.mark.parametrize('kind,mutation',[
    ('no_ferroelectric',lambda r:r.update(ferroelectric_active_nodes=1)),
    ('no_ferroelectric',lambda r:r.update(P=[1e-9,0.])),
    ('no_traps',lambda r:r.update(trap_density_m2_eV=1.)),
    ('thin_oxide',lambda r:r.update(oxide_thickness_m=1e-8)),
    ('thin_oxide',lambda r:r.update(bias_V=2.)),
    ('thin_oxide',lambda r:r.update(tunneling_current_A=1e-9)),
    ('thin_oxide',lambda r:r.update(tunneling_current_A=np.nan)),
    ('thin_oxide',lambda r:r.update(tunneling_current_A=[1e-9])),
])
def test_wrong_limit_or_measured_current_is_rejected(kind,mutation):
    assert not check(kind,mutation).passed


@pytest.mark.parametrize('kind',KINDS)
def test_reused_simulator_cannot_be_an_independent_limit(kind):
    sim=object()
    runners={side:(lambda s,*coords,side=side:measurements(kind,side,*coords)) for side in ['limit','reference']}
    assert not LimitingCaseTest(kind,runners=runners,reference_source='test').run(lambda:sim).passed


@pytest.mark.parametrize('value',[0.,-1.,True,np.inf,np.nan,'0.1'])
def test_invalid_limit_tolerances_are_rejected(value):
    with pytest.raises(ValueError): LimitingCaseTest('high_temperature',tolerance=value)


@pytest.mark.parametrize('kwargs',[dict(runners={}),dict(runners={'limit':None,'reference':None}),
    dict(limit_params={'unused':1}),dict(limit_params={'temperature_K':0}),
    dict(limit_params={'temperature_K':True}),dict(limit_params={'temperature_K':np.nan}),
    dict(fields=('phi',)),dict(reference_source='')])
def test_invalid_limit_configuration_is_rejected(kwargs):
    config=dict(runners={'limit':lambda s:{},'reference':lambda s:{}},reference_source='test')
    config.update(kwargs)
    with pytest.raises(ValueError): LimitingCaseTest('high_temperature',**config)


@pytest.mark.parametrize('kind',['nls_to_lk','preisach_to_lk'])
def test_explicit_runners_cannot_override_undefined_constitutive_equivalence(kind):
    def forbidden(*args): pytest.fail('undefined equation mapping must never run')
    result=LimitingCaseTest(kind,runners={'limit':forbidden,'reference':lambda s:{}},reference_source='test').run(object)
    assert not result.passed and result.details['unsupported']


def test_framework_exposes_limit_runners_and_explicit_budgets():
    framework=ValidationFramework(object)
    framework.add_limiting_case_test('high_temperature',runners={
        side:lambda sim,side=side:measurements('high_temperature',side) for side in ['limit','reference']},
        reference_source='test',atol={'n':0.,'p':0.})
    assert framework.run_all()[0].passed


@pytest.mark.parametrize('kind,kwargs',[
    ('thin_oxide',{'thicknesses_m':[]}),('thin_oxide',{'thicknesses_m':[1e-9,2e-9,3e-9]}),
    ('thin_oxide',{'bias_V':0.}),('thin_oxide',{'bias_V':True}),
    ('thin_oxide',{'bias_V':np.nan}),('no_traps',{'D_it':0.})])
def test_bad_or_unused_limit_parameters_are_rejected(kind,kwargs):
    with pytest.raises(ValueError): LimitingCaseTest(kind,limit_params=kwargs)


@pytest.mark.parametrize('current',[0.,1e-9])
def test_constant_thin_oxide_reference_is_inconclusive(current):
    def runner(sim,thickness):
        result=measurements('thin_oxide','limit',thickness)
        result['tunneling_current_A']=current
        return result
    report=LimitingCaseTest('thin_oxide',runners={'limit':runner,'reference':lambda s,t:runner(s,t)},
        reference_source='constant control').run(object)
    assert not report.passed and report.details['inconclusive']


@pytest.mark.parametrize('kind',KINDS)
def test_solver_exception_cannot_pass(kind):
    def broken(*args): raise RuntimeError('solver failed')
    result=LimitingCaseTest(kind,runners={'limit':broken,'reference':lambda *args:{}},
        reference_source='failure').run(object)
    assert not result.passed and not result.details['numerical_agreement_validated']


def native_limit_check(kind,axis,perturb=False):
    from tcad.core import PyDeviceSimulator
    count=9
    def builder():
        dims=[1,1,1];dims[axis]=count
        sim=PyDeviceSimulator(*dims,1e-8,1e-8,1e-8)
        sim.set_permittivity(np.full(count,8.854187817e-12*11.7))
        sim.set_mobility(np.full(count,.1),np.full(count,.05))
        sim.set_doping(np.zeros(count))
        sim.set_effective_dos(np.full(count,1e16),np.full(count,1e16))
        sim.set_bandgap(np.full(count,6.))
        sim.set_recombination(np.full(count,1e100),np.full(count,1e100))
        sim.set_dirichlet_potential({0:0.,count-1:.001})
        sim.set_electron_bc({0:1e16,count-1:1e16});sim.set_hole_bc({0:1e16,count-1:1e16})
        sim.set_initial_guess(np.linspace(0.,.001,count),np.full(count,1e16),np.full(count,1e16))
        sim.set_tolerance(1e-12);sim.set_gummel_max_iter(100)
        return sim
    def run(sim,side):
        if kind=='no_ferroelectric':
            sim.set_ferroelectric_enabled(side=='limit')
            sim.set_ferroelectric_params(np.zeros(count,dtype=np.int8),-1e8,1e12)
        elif kind=='no_traps':
            mask=np.ones(count,dtype=np.int8) if side=='limit' else np.zeros(count,dtype=np.int8)
            sim.set_interface_traps(mask,0.,.15)
            sim.set_oxide_traps(np.zeros(count))
        else:
            sim.set_temperature(1000.);sim.set_ambient_temperature(1000.)
            sim.set_quantum_enabled(side=='limit')
        result=sim.solve()
        actual={field:result[field] for field in ['phi','n','p','P','converged']}
        metadata=measurements(kind,side)
        for key in ['phi','n','p','P','converged']:metadata.pop(key)
        actual.update(metadata)
        if kind=='no_traps':actual['oxide_trap_charge_C_m3']=np.zeros(count)
        if perturb and side=='limit':actual['n']=actual['n']*1.01
        return actual
    fields=LimitingCaseTest._fields[kind]
    budgets={field:{'phi':1e-12,'n':1e4,'p':1e4,'P':0.}[field] for field in fields}
    return LimitingCaseTest(kind,tolerance=1e-8,atol=budgets,
        runners={side:lambda sim,side=side:run(sim,side) for side in ['limit','reference']},
        reference_source='native explicit zero-volume/zero-trap or uniform-density quantum identity').run(builder)


@pytest.mark.parametrize('kind',['no_ferroelectric','no_traps','high_temperature'])
@pytest.mark.parametrize('axis',[0,1,2])
def test_native_configured_limits_preserve_phi_and_both_carriers(kind,axis):
    result=native_limit_check(kind,axis)
    assert result.passed,result.message+str(result.details)


@pytest.mark.parametrize('kind',['no_ferroelectric','no_traps','high_temperature'])
def test_native_carrier_corruption_is_rejected_in_each_limit(kind):
    assert not native_limit_check(kind,0,perturb=True).passed


@pytest.mark.parametrize('kind',['no_ferroelectric','no_traps','high_temperature'])
@pytest.mark.parametrize('field',['n','p'])
def test_negative_carrier_measurement_is_rejected(kind,field):
    assert not check(kind,lambda r:r.update({field:[-1.,1.]})).passed


@pytest.mark.parametrize('charge',[None,[1e-10,0.],[np.nan,0.],[0.],0.])
def test_zero_interface_density_does_not_hide_bulk_trap_charge(charge):
    def corrupt(result):
        if charge is None:result.pop('oxide_trap_charge_C_m3')
        else:result['oxide_trap_charge_C_m3']=charge
    assert not check('no_traps',corrupt).passed
