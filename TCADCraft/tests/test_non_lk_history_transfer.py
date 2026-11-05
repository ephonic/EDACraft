"""Actual native ensemble memory survives restart, remesh and reversals."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.ensemble_transfer import conservative_ensemble_transfer


@pytest.mark.parametrize('model',[1,2,3])
def test_native_export_restart_and_atomic_rejection(model):
    from test_transient_displacement import film
    def setup():
        sim,*_=film(0,model,True,False)
        sim.set_ferroelectric_preisach(1e-5,1e5,1e5)
        sim.set_ferroelectric_nls(1e-9,1e5,1e-10)
        return sim
    source=setup()
    for v in (.02,-.015,.008):
        source.set_dirichlet_potential({0:0.,8:v});assert source.solve()['converged']
    history=source.get_ferroelectric_ensemble_history();clone=setup()
    clone.set_ferroelectric_ensemble_history(history)
    for key in ('polarization','play'):np.testing.assert_array_equal(history[key],clone.get_ferroelectric_ensemble_history()[key])
    for key in ('parameters','polarization','play'):
        bad=deepcopy(history)
        if bad[key].size:bad[key].flat[0]=np.nan
        else:bad[key]=np.array([1.])
        with pytest.raises(ValueError):clone.set_ferroelectric_ensemble_history(bad)
        np.testing.assert_array_equal(clone.get_ferroelectric_history(),history['polarization'])
    source.begin_reliability_transaction()
    for v in (-.025,.03,0.):
        for sim in (source,clone):sim.set_dirichlet_potential({0:0.,8:v})
        a,b=source.solve(),clone.solve()
        assert a['converged'] and b['converged']
        np.testing.assert_allclose(a['P'],b['P'],rtol=2e-12,atol=1e-18)
    source.rollback_reliability_transaction()
    np.testing.assert_array_equal(source.get_ferroelectric_history(),history['polarization'])


@pytest.mark.parametrize('model',[1,2,3])
def test_conservative_ensemble_refinement_and_coarsening(model):
    from test_transient_displacement import film
    from tcad.mesh.conservative_transfer import dual_faces
    sim,*_=film(0,model,True,False)
    sim.set_dirichlet_potential({0:0.,8:.01});assert sim.solve()['converged']
    state=sim.get_ferroelectric_ensemble_history()
    source=dual_faces([np.linspace(0,1,9),np.array([0.]),np.array([0.])],[1,1,1])
    target=dual_faces([np.linspace(0,1,17),np.array([0.]),np.array([0.])],[1,1,1])
    mapped,report=conservative_ensemble_transfer(state,source,target,target_mask=np.ones(17,bool))
    back,_=conservative_ensemble_transfer(mapped,target,source,target_mask=state['mask'])
    np.testing.assert_array_equal(back['polarization'],state['polarization'])
    np.testing.assert_array_equal(back['play'],state['play'])
    np.testing.assert_allclose(report['source_integral_P_dV_C_m'],report['target_integral_P_dV_C_m'],rtol=1e-14)
    state['polarization'][4,0]*=.5
    with pytest.raises(ValueError,match='incompatible'):conservative_ensemble_transfer(state,source,target,target_mask=np.ones(17,bool))


@pytest.mark.parametrize('model',['preisach','nls','sentaurus_preisach'])
def test_high_level_actual_remesh_reversal_preserves_source(model):
    from test_configuration_inheritance import setup
    _,refiner,source=setup(dielectric=True,ferroelectric=True)
    source.set_ferroelectric(model=model,Ps=1e-6,Ec=1e4,Escale=1e4,nls_tau0=1e-9,nls_E0=1e4,nls_dt=1e-10)
    accepted=source.run(max_iter=100,tol=1e-11);assert accepted['converged']
    original=source._sim.get_ferroelectric_ensemble_history()
    shape=tuple(max(n-1,1) for n in source.mesh.shape())
    target=refiner._refine_from_markers(source.mesh,{a:np.full(shape,source.mesh.shape()[i]>1,bool) for i,a in enumerate('xyz')},1)
    clone=source.clone_on_mesh(target,fe_history='conservative_ensemble')
    assert clone.fe_history_transfer_report()['model']=={'preisach':1,'nls':2,'sentaurus_preisach':3}[model]
    for v in (-.01,.02):
        source.set_contact('high',v);clone.set_contact('high',v)
        a,b=source.run(max_iter=100,tol=1e-11),clone.run(max_iter=100,tol=1e-11)
        assert a['converged'] and b['converged']
        np.testing.assert_allclose(a['P'][0],b['P'][0],rtol=2e-7,atol=1e-16)
    assert original['polarization'].shape[0]!=clone.mesh.npts()
    source._sim.set_ferroelectric_builtin_field(4.)
    with pytest.raises(ValueError,match='unchanged'):source.clone_on_mesh(target,fe_history='conservative_ensemble')


@pytest.mark.parametrize('case_index',range(5))
def test_sentaurus_turning_stack_restart_keeps_commercial_nested_loop(case_index):
    from test_sentaurus_preisach_history import REFERENCE
    from tcad.core import PyDeviceSimulator
    case=REFERENCE['cases'][case_index];count=9
    def setup():
        sim=PyDeviceSimulator(count,1,1,REFERENCE['length_m']/(count-1),1.,1.)
        sim.set_permittivity(np.full(count,8.854187817e-12*25))
        sim.set_mobility(np.zeros(count),np.zeros(count));sim.set_doping(np.zeros(count))
        sim.set_effective_dos(np.full(count,2.8e25),np.full(count,1.04e25));sim.set_bandgap(np.full(count,5.8))
        sim.set_thermal_voltage(.025852);sim.set_electron_bc({0:0.,8:0.});sim.set_hole_bc({0:0.,8:0.})
        sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(np.ones(count,dtype=np.int8),-1e8,1e18)
        sim.set_ferroelectric_model(3)
        width=2*case['Ec']/np.log((case['Ps']+case['Pr'])/(case['Ps']-case['Pr']))
        sim.set_ferroelectric_preisach(case['Ps'],case['Ec'],width);sim.set_gummel_max_iter(20);sim.set_tolerance(1e-10)
        return sim
    sim=setup();split=len(case['points'])//2
    for k,point in enumerate(case['points']):
        if k==split:
            state=sim.get_ferroelectric_ensemble_history();sim=setup();sim.set_ferroelectric_ensemble_history(state)
        sim.set_dirichlet_potential({0:point['voltage_V'],8:0.});result=sim.solve();assert result['converged']
        np.testing.assert_allclose(result['P'][4,0],point['polarization_C_per_m2'],rtol=1e-6,atol=1e-9)


def test_nls_transient_absolute_clock_restart_keeps_kinetic_age():
    from test_transient_displacement import film
    def setup():
        sim,*_=film(0,2,True,False)
        sim.set_ferroelectric_nls(1e-9,1e5,1e-15)
        sim.set_transient_voltage_waveforms(np.array([0.,1e-10,2e-10,3e-10]),
            {8:np.array([0.,.01,-.02,.015])})
        sim.set_transient_t_final(3e-10);return sim
    full=setup().solve_transient();prefix=setup();prefix.set_transient_t_final(1e-10)
    first=prefix.solve_transient()[-1];tail=setup()
    tail.set_ferroelectric_ensemble_history(prefix.get_ferroelectric_ensemble_history())
    tail.set_initial_guess(first['phi'],first['n'],first['p']);tail.set_transient_start_time(first['time_s'])
    resumed=tail.solve_transient();assert resumed[0]['time_s']==1e-10
    for key in ('phi','P','electrode_charges_C'):
        np.testing.assert_allclose(resumed[-1][key],full[-1][key],rtol=1e-10,atol=1e-25)
