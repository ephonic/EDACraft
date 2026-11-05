"""Integral preservation, remesh energy, transactional import and clock restart."""
from copy import deepcopy
import numpy as np
import pytest
from tcad.mesh.conservative_transfer import conservative_lk_transfer,dual_faces


@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('shape',[(5,1,1),(4,3,1),(3,3,3)])
def test_signed_components_nonuniform_overlap_conserves_and_bounds(shape,reverse):
    source=[np.linspace(0,1,n+1)**1.3 for n in shape]
    target=[np.linspace(0,1,n*2+1)**1.6 for n in shape]
    if reverse: source,target=target,source
    n=int(np.prod([len(f)-1 for f in source]));nt=int(np.prod([len(f)-1 for f in target]))
    p=np.random.default_rng(42).normal(0,.01,(n,3));copy=p.copy()
    out,report=conservative_lk_transfer(p,source,target,source_mask=np.ones(n,bool),
        target_mask=np.ones(nt,bool),alpha=-1e8,beta=1e12,max_landau_energy_change_J=1e9)
    np.testing.assert_array_equal(p,copy)
    np.testing.assert_allclose(report['source_integral_P_dV_C_m'],report['target_integral_P_dV_C_m'],rtol=1e-13)
    assert np.all(out>=p.min(axis=0)-1e-16) and np.all(out<=p.max(axis=0)+1e-16)


def test_material_interface_and_explicit_energy_budget_rejections():
    source=[np.array([0.,.5,1.]),np.array([0.,1.]),np.array([0.,1.])]
    target=[np.array([0.,.4,.8,1.]),*source[1:]]
    args=dict(polarization=np.array([[.1,0,0],[0,0,0]]),source_faces=source,target_faces=target,
        source_mask=np.array([True,False]),target_mask=np.array([True,False,False]),
        alpha=-1e8,beta=1e12,max_landau_energy_change_J=1e10)
    with pytest.raises(ValueError,match='material'):conservative_lk_transfer(**args)
    args.update(polarization=np.array([[.1,0,0],[-.1,0,0]]),source_mask=np.ones(2,bool),target_mask=np.ones(3,bool),max_landau_energy_change_J=0.)
    with pytest.raises(ValueError,match='energy'):conservative_lk_transfer(**args)
    args['target_faces']=[np.array([0.,.5,1.01]),*source[1:]]
    with pytest.raises(ValueError,match='boundaries'):conservative_lk_transfer(**args)


def test_material_interface_fixed_under_refinement():
    source=[np.array([0.,.5,1.]),np.array([0.,1.]),np.array([0.,1.])]
    target=[np.array([0.,.25,.5,.75,1.]),*source[1:]]
    out,report=conservative_lk_transfer(np.array([[.1,.2,-.3],[0,0,0]]),source,target,
        source_mask=np.array([True,False]),target_mask=np.array([True,True,False,False]),
        alpha=1.,beta=1.,max_landau_energy_change_J=1e-16)
    np.testing.assert_array_equal(out[0],out[1]);assert not np.any(out[2:])
    assert report['source_FE_volume_m3']==report['target_FE_volume_m3']==.5


def test_natural_boundary_requires_same_physical_support():
    a=dual_faces([np.array([0.,1.,2.]),np.array([0.]),np.array([0.])],[1,1,1],'xX')
    b=dual_faces([np.array([0.,.5,1.,1.5,2.]),np.array([0.]),np.array([0.])],[1,1,1],'xX')
    assert a[0][0]!=b[0][0]
    with pytest.raises(ValueError,match='boundaries'):
        conservative_lk_transfer(np.zeros((3,3)),a,b,source_mask=np.ones(3,bool),target_mask=np.ones(5,bool),alpha=1,beta=1,max_landau_energy_change_J=0)


def test_native_state_import_is_atomic_and_read_only():
    from test_lk_material_multidimensional import device
    sim,_=device((4,3,1),True,0)
    assert sim.get_ferroelectric_history().shape==(0,3)
    mask=sim.get_ferroelectric_mask();p=np.zeros((12,3));p[mask]=[.001,-.002,.003]
    sim.set_ferroelectric_history(p);p[:]=9
    saved=sim.get_ferroelectric_history();assert not np.any(saved[~mask])
    for bad in (np.full((12,3),np.nan),np.ones((12,3)),np.zeros((12,2))):
        with pytest.raises(ValueError): sim.set_ferroelectric_history(bad)
        np.testing.assert_array_equal(saved,sim.get_ferroelectric_history())
    sim.begin_reliability_transaction();sim.set_ferroelectric_history(np.zeros((12,3)))
    sim.set_transient_start_time(1e-10);sim.rollback_reliability_transaction()
    np.testing.assert_array_equal(saved,sim.get_ferroelectric_history())
    assert sim.solve_transient()[0]['time_s']==0
    accepted=sim.get_ferroelectric_history()
    sim.set_transient_start_time(3e-10)
    with pytest.raises(ValueError,match='exceed'):sim.solve_transient()
    np.testing.assert_array_equal(accepted,sim.get_ferroelectric_history())
    sim.set_transient_start_time(2.1e-10)
    initial_only=sim.solve_transient()
    assert len(initial_only)==1 and initial_only[0]['time_s']==2.1e-10
    np.testing.assert_array_equal(accepted,sim.get_ferroelectric_history())


def test_native_split_at_absolute_time_matches_uninterrupted_waveform():
    from test_lk_material_multidimensional import device
    def setup():
        sim,_=device((4,3,1),False,0)
        sim.set_ferroelectric_builtin_field(0.);sim.set_ferroelectric_depol(0.)
        sim.set_transient_voltage_waveforms(np.array([0.,1e-10,2e-10,3e-10]),
            {int(i):np.array([0.,.01,-.01,.02]) for i in (3,7,11)})
        sim.set_transient_t_final(3e-10);return sim
    full=setup().solve_transient();sim=setup();sim.set_transient_t_final(1e-10)
    prefix=sim.solve_transient();last=prefix[-1];p=last['P'].reshape(-1,3)
    resumed=setup();resumed.set_ferroelectric_history(p)
    resumed.set_initial_guess(last['phi'],last['n'],last['p']);resumed.set_transient_start_time(last['time_s'])
    states=resumed.solve_transient();assert states[0]['time_s']==last['time_s']
    np.testing.assert_array_equal(states[0]['P'],last['P'])
    for key in ('P','phi','electrode_charges_C'):
        # Restart imports float64 into quad and repeats initial Gauss projection.
        # Bound absolute transverse noise as well as relative resolved values.
        np.testing.assert_allclose(states[-1][key],full[-1][key],rtol=2e-12,
            atol=1e-18 if key=='P' else 1e-28)
    from tcad.postprocess.lk_energy import audit_transient_lk_energy
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('layout',[(0,),(0,1,2)])
def test_high_level_clone_conserves_history_and_owns_state(layout):
    from test_configuration_inheritance import setup,fine_mesh
    _,refiner,source=setup(layout,0,dielectric=True,ferroelectric=True)
    source.set_ferroelectric()
    source.set_transient_lk_coupled(True);source.set_transient_lk_material_field(True)
    source.set_transient(dt=1e-10,t_final=2e-10,fe_gamma=.1)
    states=source.run_transient(max_iter=80,tol=1e-12);assert states[-1]['valid']
    before=deepcopy(source.results)
    shape=tuple(max(n-1,1) for n in source.mesh.shape())
    target=refiner._refine_from_markers(source.mesh,{a:np.full(shape,source.mesh.shape()[i]>1,bool)
        for i,a in enumerate('xyz')},1)
    # A previous DC seed must not override the accepted transient carriers.
    source._accepted_initial_guess=tuple(np.full(source.mesh.npts(),1e12) for _ in range(3))
    clone=source.clone_on_mesh(target,fe_history='conservative',max_landau_energy_change_J=1e-25)
    report=clone.fe_history_transfer_report()
    np.testing.assert_array_equal(clone._accepted_initial_guess[1],np.full(target.npts(),before['n'][0]))
    np.testing.assert_allclose(report['source_integral_P_dV_C_m'],report['target_integral_P_dV_C_m'],rtol=1e-13)
    clone.set_transient(dt=1e-10,t_final=3e-10,fe_gamma=.1)
    continuation=clone.run_transient(max_iter=80,tol=1e-12)
    assert continuation[0]['time_s']==2e-10 and continuation[-1]['time_s']==3e-10
    np.testing.assert_array_equal(source.results['P'],before['P'])
    with pytest.raises(ValueError,match='budget'):source.clone_on_mesh(target,fe_history='conservative')
    report['source_integral_P_dV_C_m'][0]=99
    assert clone.fe_history_transfer_report()['source_integral_P_dV_C_m'][0]!=99
    source._sim.set_ferroelectric_gamma(.2)
    with pytest.raises(ValueError,match='coefficients'):source.clone_on_mesh(target,
        fe_history='conservative',max_landau_energy_change_J=1e-25)
