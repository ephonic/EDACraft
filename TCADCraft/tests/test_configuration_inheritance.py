"""Configuration survives remeshing and affects actual native solutions."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.core import SolverType, native_constants
from tcad.geometry.device_builder import Box, Device, Material, Region
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.mesh.structured_grid import StructuredGrid
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from test_adaptive_dimensions import CASES


def setup(layout=(0,), axis=0, *, dielectric=False, ferroelectric=False):
    mat = Material('base', epsilon_r=3.9 if dielectric else 11.7,
        Eg=6. if dielectric else 0., Nc=1. if dielectric else 1e10,
        Nv=1. if dielectric else 1e10, mu_n=0. if dielectric else 1000.,
        mu_p=0. if dielectric else 500., fe_alpha=1e8 if ferroelectric else 0.,
        fe_beta=1e10 if ferroelectric else 0.)
    device = Device().add_region(Region('base', Box(0,1e-6,0,1e-6,0,1e-6), mat))
    for name, interval, voltage in [('low',(-1e-12,1e-12),0.),
            ('high',(1e-6-1e-12,1e-6+1e-12),.01)]:
        bounds=[(-1e-12,1e-6+1e-12)]*3; bounds[axis]=interval
        device.add_contact(name,Box(*(v for b in bounds for v in b)),voltage=voltage)
    shape=tuple(5 if a==axis else 3 if a in layout else 1 for a in range(3))
    refiner=AdaptiveRefiner(device,base_shape=shape)
    mesh=refiner.generate_feature_refined_mesh(0)
    sim=Simulator(mesh);sim.set_material_from_mesh()
    sim.set_contact('low',0.);sim.set_contact('high',.01)
    if dielectric:
        zero=np.zeros(mesh.npts());sim._sim.set_initial_guess(zero,zero,zero)
    return device,refiner,sim


@pytest.mark.parametrize('layout,axis',CASES)
def test_adaptive_keeps_runtime_bias_models_and_original_simulator(layout,axis):
    _,refiner,sim=setup(layout,axis,dielectric=True)
    sim.set_contact('high',.025)
    sim.set_quantum(False)
    sim.set_solver_type(SolverType.CG,SolverType.BICGSTAB)
    sim.set_use_newton(True)
    sim.set_newton_options(damping=.7,use_log_space=True)
    before=repr(sim.configuration_snapshot()); original=sim.mesh
    grids,states,history=refiner.run_adaptive_solve(sim,max_rounds=2,
        initial_level=0,error_fields=['phi'],verbose=False,
        sim_kwargs=dict(max_iter=100,tol=1e-10))
    assert len(states)==2 and all(s['converged'] for s in states)
    assert sim.mesh is original and sim.results is None
    assert repr(sim.configuration_snapshot())==before
    for mesh,state in zip(grids,states):
        np.testing.assert_allclose(state['phi'],.025*mesh.flat_coords()[axis]/1e-6,
            rtol=3e-9,atol=3e-12)


@pytest.mark.parametrize('layout,axis',CASES)
def test_native_fixed_charge_override_reaches_every_adaptive_round(layout,axis):
    _,refiner,sim=setup(layout,axis,dielectric=True)
    eps=3.9*8.854187817e-12
    # phi = V*x/L + A*x*(L-x)/L^2; positive uniform fixed charge.
    amplitude=.02
    doping=2*eps*amplitude/1e-12/float(native_constants()['elementary_charge_C'])
    sim._sim.set_doping(np.full(sim.mesh.npts(),doping))
    zero=np.zeros(sim.mesh.npts())
    sim._sim.set_initial_guess(zero,zero,zero)
    grids,states,_=refiner.run_adaptive_solve(sim,max_rounds=2,initial_level=0,
        error_fields=['phi'],error_mode='residual',verbose=False,
        sim_kwargs=dict(max_iter=100,tol=1e-12))
    assert len(states)==2
    for mesh,state in zip(grids,states):
        assert state['converged']
        s=mesh.flat_coords()[axis]/1e-6
        np.testing.assert_allclose(state['phi'],.01*s+amplitude*s*(1-s),atol=3e-12,rtol=3e-9)


class NativeCapture:
    def __init__(self,backend):self.backend=backend;self.calls=[]
    def __getattr__(self,name):
        method=getattr(self.backend,name)
        if not callable(method):return method
        def call(*a,**k):
            self.calls.append((name,deepcopy(a),deepcopy(k)))
            return method(*a,**k)
        return call


@pytest.fixture
def capture(monkeypatch):
    import tcad.simulator as module
    native=module.PyDeviceSimulator
    monkeypatch.setattr(module,'PyDeviceSimulator',lambda *a,**k:NativeCapture(native(*a,**k)))


def fine_mesh(refiner,source):
    markers={a:np.zeros((4,1,1),dtype=bool) for a in 'xyz'}
    markers['x'][:]=True
    return refiner._refine_from_markers(source,markers,1)


@pytest.mark.parametrize('setter,args,expected',[
    ('set_quantum',(False,),{'set_quantum_enabled':(False,)}),
    ('set_solver_type',(SolverType.CG,SolverType.GMRES),{'set_poisson_solver_type':(3,),'set_continuity_solver_type':(2,)}),
    ('set_statistics',('fermi_dirac',),{'set_statistics_type':(1,)}),
    ('set_mobility_model',('arora',),{'set_mobility_model':(1,)}),
    ('set_use_newton',(True,),{'set_use_newton':(True,)}),
    ('set_newton_log_space',(True,),{'set_newton_use_log_space':(True,),'set_newton_use_log_damping':(True,)}),
    ('set_freeze_phi',(True,),{'set_newton_freeze_phi':(True,)}),
    ('set_freeze_n',(True,),{'set_newton_freeze_n':(True,)}),
    ('set_freeze_p',(True,),{'set_newton_freeze_p':(True,)}),
    ('set_density_gradient_coefficients',(1e-20,2e-20),{'set_density_gradient_coefficients':(1e-20,2e-20)}),
    ('set_ferroelectric_builtin_field',(2e5,),{'set_ferroelectric_builtin_field':(2e5,)}),
    ('set_ferroelectric_depol',(12.,),{'set_ferroelectric_depol':(12.,)}),
    ('set_ferroelectric_polar_axis',('z',),{'set_ferroelectric_polar_axis':(2,)}),
    ('set_ferroelectric_nls_dwell_time',(2e-8,),{'set_ferroelectric_nls':(1e-6,2e9,2e-8)}),
    ('set_nonlinear_history_enabled',(True,),{'set_nonlinear_history_enabled':(True,)}),
    ('set_transient',(1e-10,4e-10,.2),{'set_transient_dt':(1e-10,),'set_transient_t_final':(4e-10,),'set_ferroelectric_gamma':(.2,)}),
])
def test_nondefault_settings_reach_fresh_native_backend(capture,setter,args,expected):
    _,refiner,sim=setup()
    getattr(sim,setter)(*args)
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    calls={name:(a,k) for name,a,k in clone._sim.backend.calls}
    for name,values in expected.items():
        assert calls[name]==(values,{})


@pytest.mark.parametrize('setter,native,key',[
    ('set_optical_generation','set_optical_generation','G_opt'),
    ('set_btbt_weight','set_btbt_weight','weight'),
    ('set_charge_volume_fraction','set_charge_volume_fraction','fraction'),
    ('set_oxide_traps','set_oxide_traps','Q_ot'),
    ('set_thermal_coupling','set_thermal_conductivity','thermal_conductivity'),
])
def test_spatial_overrides_interpolate_physical_coordinates_and_own_arrays(capture,setter,native,key):
    _,refiner,sim=setup()
    x=sim.mesh.flat_coords()[0]/1e-6
    values=.1+.4*x
    getattr(sim,setter)(**{key:values})
    values[:]=100. # caller mutation must not change the stored recipe
    mesh=fine_mesh(refiner,sim.mesh);clone=sim.clone_on_mesh(mesh)
    found=[a[0] for name,a,k in clone._sim.backend.calls if name==native][-1]
    np.testing.assert_allclose(found,.1+.4*mesh.flat_coords()[0]/1e-6,rtol=2e-15)


@pytest.mark.parametrize('setter,key,native',[
    ('set_ferroelectric','fe_mask_override','set_ferroelectric_params'),
    ('set_leakage','leak_mask_override','set_leakage'),
    ('set_interface_traps','trap_mask_override','set_interface_traps'),
])
def test_binary_overrides_are_not_smeared(capture,setter,key,native):
    _,refiner,sim=setup(ferroelectric=setter=='set_ferroelectric')
    mask=np.array([0,0,1,1,0],dtype=np.int8)
    getattr(sim,setter)(**{key:mask})
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    found=[a[0] for name,a,k in clone._sim.backend.calls if name==native][-1]
    assert set(found)=={0,1} and found.size==9
    np.testing.assert_array_equal(found[::2],mask)


def test_workfunction_and_voltage_update_survive_without_source_state_mutation(capture):
    _,refiner,sim=setup()
    sim.set_contact('high',.01,workfunction=4.4)
    sim.results={'converged':False}
    sim.update_contact('high',.04)
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    assert clone._contact_voltages['high']==.04
    assert clone._contact_workfunctions['high']==4.4
    assert clone._pending_contact_ramps=={}
    assert sim.results=={'converged':False}


def test_waveform_time_samples_not_mistaken_for_spatial_arrays(capture):
    _,refiner,sim=setup()
    times=np.linspace(0,4e-10,5)
    volts=np.array([0.,.02,.01,.03,.01])
    sim.set_transient_contact_waveforms(times,{'high':volts})
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    np.testing.assert_array_equal(clone._transient_contact_waveforms[0],times)
    np.testing.assert_array_equal(clone._transient_contact_waveforms[1]['high'],volts)


def test_direct_native_recombination_and_node_pins_remap(capture):
    _,refiner,sim=setup()
    tau=np.linspace(1e-8,2e-8,5)
    sim._sim.set_recombination(tau,tau*2)
    sim.set_thermal_dirichlet({4:350.})
    mesh=fine_mesh(refiner,sim.mesh);clone=sim.clone_on_mesh(mesh)
    calls={n:a for n,a,k in clone._sim.backend.calls}
    np.testing.assert_allclose(calls['set_recombination'][0],np.linspace(1e-8,2e-8,9))
    assert calls['set_thermal_dirichlet']==({8:350.},)


def test_run_internals_not_appended_to_configuration_and_initial_guess_is_owned():
    _,refiner,sim=setup()
    before=repr(sim.configuration_snapshot())
    state=sim.run(max_iter=80,tol=1e-10,physical_step=False)
    assert state['converged'] and repr(sim.configuration_snapshot())==before
    snapshot=sim.configuration_snapshot();snapshot.clear()
    mesh=fine_mesh(refiner,sim.mesh);clone=sim.clone_on_mesh(mesh)
    assert clone.configuration_snapshot()
    found=clone.run(max_iter=80,tol=1e-10,physical_step=False)
    assert found['converged']
    np.testing.assert_allclose(found['phi'],.01*mesh.flat_coords()[0]/1e-6,atol=2e-12)


def test_failed_configuration_is_not_saved():
    _,_,sim=setup();before=repr(sim.configuration_snapshot())
    with pytest.raises(ValueError):sim.set_statistics('typo')
    assert repr(sim.configuration_snapshot())==before and sim._configuration_depth==0


@pytest.mark.parametrize('setter', ['set_edge_permittivity','set_ohmic_contacts','set_x_positions'])
def test_unsupported_native_geometry_is_rejected_on_remesh(setter):
    _,refiner,sim=setup()
    if setter=='set_edge_permittivity':getattr(sim._sim,setter)(*[np.full(5,1e-10)]*6)
    elif setter=='set_ohmic_contacts':getattr(sim._sim,setter)([0,4],{0:0.,4:0.},{0:0.,4:0.},1e16)
    else:getattr(sim._sim,setter)(sim.mesh.axis_coordinates()[0])
    with pytest.raises(ValueError,match='cannot be interpolated|explicit redefinition'):
        sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))


def test_solved_fe_history_requires_explicit_physical_restart():
    _,refiner,sim=setup(dielectric=True,ferroelectric=True)
    sim.set_ferroelectric(fe_mask_override=np.ones(5,dtype=np.int8),alpha=1e8,beta=1e10)
    state=sim.run(max_iter=100,tol=1e-10,physical_step=False)
    assert state['converged']
    mesh=fine_mesh(refiner,sim.mesh)
    with pytest.raises(ValueError,match='history cannot be remeshed'):sim.clone_on_mesh(mesh)
    clone=sim.clone_on_mesh(mesh,include_initial_guess=False)
    assert clone._fe_node_mask.size==9 and clone.results is None


def test_public_adaptive_entry_keeps_singleton_axes():
    device,_,sim=setup()
    sim.set_contact('high',.02)
    grids,states,_=sim.run_adaptive(device,max_rounds=2,initial_level=0,
        verbose=False,error_fields=['phi'],max_iter=80,tol=1e-10)
    assert [g.shape() for g in grids]==[(5,1,1),(9,1,1)]
    assert all(s['converged'] for s in states)


def test_remap_rejects_changed_domain_and_dimensions():
    _,_,sim=setup()
    with pytest.raises(ValueError,match='bounding boxes'):
        sim.clone_on_mesh(StructuredGrid(((0.,2e-6),)*3,9,1,1))
    with pytest.raises(ValueError,match='active axes'):
        sim.clone_on_mesh(StructuredGrid(((0.,1e-6),)*3,9,3,1))


def test_explicit_mesh_material_edits_are_owned_and_affect_native_solution():
    _,refiner,sim=setup(dielectric=True)
    s=sim.mesh.flat_coords()[0]/1e-6;amplitude=.004;eps=3.9*8.854187817e-12
    sim.mesh.fields['doping'][:]=6*eps*amplitude*s/1e-12/float(native_constants()['elementary_charge_C'])/1e6
    sim.set_material_from_mesh()
    # The material setter has already consumed its inputs. A later caller edit
    # must not rewrite that configuration retroactively.
    sim.mesh.fields['doping'][:]=0.
    mesh=fine_mesh(refiner,sim.mesh);clone=sim.clone_on_mesh(mesh)
    state=clone.run(max_iter=100,tol=1e-12,physical_step=False)
    assert state['converged']
    s=mesh.flat_coords()[0]/1e-6
    np.testing.assert_allclose(state['phi'],.01*s+amplitude*(s-s**3),rtol=2e-9,atol=2e-12)


def test_default_material_recipe_resamples_a_previously_unsampled_film(capture):
    base=Material('base',epsilon_r=3.9);film=Material('film',epsilon_r=15.)
    device=Device().add_region(Region('base',Box(0,1e-6,0,1e-6,0,1e-6),base))
    device.add_region(Region('film',Box(.23e-6,.27e-6,0,1e-6,0,1e-6),film))
    source=structured_mesh_from_device(device,nx=3,ny=1,nz=1)
    target=structured_mesh_from_device(device,nx=5,ny=1,nz=1)
    sim=Simulator(source);sim.set_material_from_mesh();clone=sim.clone_on_mesh(target)
    found=[a[0] for name,a,k in clone._sim.backend.calls if name=='set_permittivity'][-1]
    np.testing.assert_array_equal(found,target.fields['epsilon'])
    assert found[1]==15.*8.854187817e-12 and found[0]==3.9*8.854187817e-12


def test_same_mesh_clone_does_not_share_mesh_arrays():
    _,_,sim=setup();clone=sim.clone_on_mesh(sim.mesh)
    clone.mesh.fields['doping'][:]=3.
    assert not np.any(sim.mesh.fields['doping'])


def test_removed_material_field_is_not_silently_reintroduced(capture):
    _,refiner,sim=setup()
    del sim.mesh.fields['Eg'];sim.set_material_from_mesh()
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    assert 'Eg' not in clone.mesh.fields


def test_transaction_rollback_removes_trial_configuration_from_inheritance():
    _,refiner,sim=setup()
    before=repr(sim.configuration_snapshot())
    with sim.reliability_transaction(commit=False):
        sim.set_contact('high',.03)
        sim.set_oxide_traps(np.full(5,1e19))
    assert repr(sim.configuration_snapshot())==before
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    assert clone._contact_voltages['high']==.01


def test_pending_continuation_and_accepted_electronic_guess_survive_remesh():
    _,refiner,sim=setup()
    state=sim.run(max_iter=80,tol=1e-10,physical_step=False);assert state['converged']
    sim.update_contact('high',1.5)
    clone=sim.clone_on_mesh(fine_mesh(refiner,sim.mesh))
    assert clone._pending_contact_ramps=={'high':(.01,1.5)}
    assert clone._accepted_contact_voltages==sim._accepted_contact_voltages
    assert all(v.size==9 for v in clone._accepted_initial_guess)
