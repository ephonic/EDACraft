"""Native configuration inheritance and independently audited nodal migration."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from tcad.physics.multivalley_thermionic import ThermionicValley
from tcad.physics.fermi_spectral import valley_dos
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.postprocess.structured_three_temperature import audit_structured_three_temperature_transfer
from test_device_three_temperature import assert_owned
from test_three_temperature import BUDGET

VALLEYS=(ThermionicValley('isotropic',1.,.5,.5,.5),)
Q=1.602176634e-19


def structured_case(shape=(3,1,1), *, contacts=True, scale=1., uniform=False, voltage=.002):
    bbox=((2e-8,1.2e-7),(-2e-8,8e-8),(1e-8,1.1e-7))
    axes=[lo+(hi-lo)*np.linspace(0,1,n)**1.4 if n>1 else np.array([(lo+hi)/2])
          for n,(lo,hi) in zip(shape,bbox)]
    grid=StructuredGrid(bbox,*shape,axes=axes)
    source=Simulator(grid)
    n=grid.npts();s=np.zeros(n) if uniform else np.linspace(0,1,n)
    grid.fields['doping']=np.zeros(n)
    source._sim.set_effective_dos(np.full(n,sum(valley_dos(300.,VALLEYS))),np.full(n,sum(valley_dos(300.,VALLEYS))))
    source._sim.set_bandgap(np.full(n,.04))
    source._sim.set_permittivity((1+s*.2)*1e-10)
    source._sim.set_mobility((1+s*.2)*.014,(1+s*.1)*.0045)
    source.set_thermal_coupling(True,thermal_conductivity=.001*(1+s),ambient_temperature=300.)
    axis=next(a for a,nx in enumerate(shape) if nx>1)
    for label,side,V in [('left',0,0.),('right',-1,voltage)]:
        mask=grid.flat_coords()[axis]==axes[axis][side]
        grid.fields['contact_'+label]=mask
        source.set_contact(label,V)
    if contacts:
        nodes=np.flatnonzero(grid.fields['contact_left']|grid.fields['contact_right'])
        source._sim.set_electron_bc({int(i):1e25*scale for i in nodes})
        source._sim.set_hole_bc({int(i):1e25*scale for i in nodes})
    state=ThreeTemperatureState(1e25*scale*(1+.1*s),1e25*scale*(1+.1*s),np.full(n,.5),
        300.+4*s,2e-12,360.+20*s,260.+10*s)
    options=dict(valleys_n=VALLEYS,valleys_p=VALLEYS,Ec_J=.02*Q,Eh_J=.02*Q,
        heat_capacity_J_m3_K=1e6*(1+s),relaxation_time_n_s=1e-13,relaxation_time_p_s=4e-13,**BUDGET)
    return source,state,options


@pytest.mark.parametrize('shape',[(4,1,1),(1,4,1),(1,1,4),(3,3,1),(3,1,3),(1,3,3),(3,3,3)])
def test_graded_shifted_mesh_migration_preserves_particles_and_three_material_energies(shape):
    source,old,options=structured_case(shape)
    before=deepcopy(source._sim.structured_three_temperature_seed())
    calls=repr(source.configuration_snapshot())
    device=source.to_three_temperature(old,**options)
    report=device.migration_report
    assert report['audit']['valid'] and report['legacy_StructuredGrid_three_temperature_integrated']
    assert not report['physical_time_advanced'] and not report['audit']['electrostatic_energy_preserved']
    assert not report['audit']['complete_device_energy']
    assert report['target_cells']==np.prod([max(n-1,1) for n in shape])
    assert before==source._sim.structured_three_temperature_seed()
    assert calls==repr(source.configuration_snapshot()) and source.results is None
    assert not source._configuration_state_advanced
    assert_owned(device,device.state)
    corners=report['cell_corner_nodes'];cap=options['heat_capacity_J_m3_K']
    np.testing.assert_allclose(device.state.temperature_K,
        np.mean((cap*old.temperature_K)[corners],axis=1)/np.mean(cap[corners],axis=1),rtol=1e-14)
    assert max(abs(device.state.temperature_K-np.mean(old.temperature_K[corners],axis=1)))>1e-4
    assert max(abs(device.state.electron_temperature_K-np.mean(old.electron_temperature_K[corners],axis=1)))>1e-3
    # Returned reports and original native setters cannot mutate the new device.
    report['native_seed']['epsilon'][0]=999
    assert device.migration_report['native_seed']['epsilon'][0]!=999
    source._sim.set_permittivity(np.full(source.mesh.npts(),2e-10))
    np.testing.assert_allclose(device._model.eps,np.mean(np.asarray(before['epsilon'])[corners],axis=1))


@pytest.mark.parametrize('shape,contacts,scale',[
    ((3,1,1),False,1.),((3,1,1),True,10.),((3,3,1),True,1.),((3,3,3),True,1.)])
def test_migrated_device_two_actual_steps_close_energy_and_own_state(shape,contacts,scale):
    source,old,options=structured_case(shape,contacts=contacts,scale=scale)
    device=source.to_three_temperature(old,**options)
    for i in range(2):
        state,report=device.advance(2e-13,**BUDGET)
        assert report['independent_audit']['valid'] and report['modeled_device_energy_closed']
        assert report['legacy_StructuredGrid_three_temperature_integrated']
        assert not report['legacy_run_three_temperature_replaced']
        assert not report['complete_device_energy'] and not report['physical_validated']
        assert 'legacy_StructuredGrid_three_temperature_conversion' not in report['missing_physics']
        assert state.time_s==old.time_s+(i+1)*2e-13
        assert_owned(device,state)
    assert source.results is None and not source._configuration_state_advanced


@pytest.mark.parametrize('failure',['newton','audit'])
def test_failed_step_preserves_migrated_device_and_source(monkeypatch,failure):
    source,old,options=structured_case()
    device=source.to_three_temperature(old,**options);before=deepcopy(device.native_state())
    seed=deepcopy(source._sim.structured_three_temperature_seed())
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',
                                         lambda *a,**k:dict(valid=False,reason='injected'))
        with pytest.raises((RuntimeError,ValueError)):
            device.advance(2e-13,**BUDGET,max_nfev=1 if failure=='newton' else 600)
    assert device.native_state()==before and source._sim.structured_three_temperature_seed()==seed
    state,report=device.advance(2e-13,**BUDGET)
    fresh,_=source.to_three_temperature(old,**options).advance(2e-13,**BUDGET)
    for key in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(state,key),getattr(fresh,key))


@pytest.mark.parametrize('damage',['quantum','thermal','DOS','bandgap','SRH','generation','fraction','transaction','positions',
                                  'partial_contact','extra_phi','one_density','varying_phi','Schottky','capacity','tau','budget',
                                  'waveform','native_waveform','pending_ramp','freeze','thermal_voltage','transient'])
def test_unsupported_or_inconsistent_native_configurations_rejected_without_mutation(damage):
    source,old,options=structured_case((3,3,1));n=source.mesh.npts()
    if damage=='quantum':source._sim.set_quantum_enabled(True)
    elif damage=='thermal':source._sim.set_thermal_coupling_enabled(False)
    elif damage=='DOS':source._sim.set_effective_dos(np.full(n,1e25),np.full(n,1e25))
    elif damage=='bandgap':source._sim.set_bandgap(np.full(n,.08))
    elif damage=='SRH':source._sim.set_recombination(np.full(n,1e-6),np.full(n,1e-6))
    elif damage=='generation':source._sim.set_optical_generation(np.full(n,1e10))
    elif damage=='fraction':source._sim.set_charge_volume_fraction(np.full(n,.5))
    elif damage=='transaction':source._sim.begin_reliability_transaction()
    elif damage=='positions':source._sim.set_x_positions(np.array([0.,3e-8,1e-7]))
    elif damage=='partial_contact':source.mesh.fields['contact_left'][0]=False
    elif damage=='extra_phi':source._sim.set_dirichlet_potential({4:.001})
    elif damage=='one_density':
        source,old,options=structured_case((3,3,1),contacts=False)
        source._sim.set_electron_bc({int(i):1e25 for i in np.flatnonzero(
            source.mesh.fields['contact_left']|source.mesh.fields['contact_right'])})
    elif damage=='varying_phi':source._sim.set_dirichlet_potential({0:.01,3:0.,6:0.,2:.002,5:.002,8:.002})
    elif damage=='Schottky':source._contact_workfunctions={'left':4.5}
    elif damage=='capacity':options['heat_capacity_J_m3_K']=np.nan
    elif damage=='tau':options['relaxation_time_n_s']=0.
    elif damage=='waveform':source.set_transient_contact_waveforms([0.,1e-12],{'left':[0.,.001]})
    elif damage=='native_waveform':source._sim.set_transient_voltage_waveforms([0.,1e-12],{0:[0.,.001]})
    elif damage=='pending_ramp':source._pending_contact_ramps={'left':(0.,2.)}
    elif damage=='freeze':source._sim.set_newton_freeze_n(True)
    elif damage=='thermal_voltage':source._sim.set_thermal_voltage(.03)
    elif damage=='transient':source._sim.set_transient_enabled(True)
    else:options['energy_atol_J']=True
    calls=repr(source.configuration_snapshot())
    with pytest.raises((RuntimeError,ValueError)):
        source.to_three_temperature(old,**options)
    assert source.results is None and calls==repr(source.configuration_snapshot())


@pytest.mark.parametrize('damage',['n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K','capacity','clock'])
def test_independent_transfer_audit_rejects_forged_projection(damage):
    source,old,options=structured_case()
    device=source.to_three_temperature(old,**options);model=device._model;new=device.state
    cap=model.capacity.copy()
    if damage=='capacity':cap[0]*=1.01
    elif damage=='clock':new=replace(new,time_s=new.time_s+1e-13)
    else:
        value=getattr(new,damage).copy();value[0]*=1.01;new=replace(new,**{damage:value})
    args=(source.mesh,old,model.mesh,new,options['heat_capacity_J_m3_K'],cap,VALLEYS,VALLEYS,.02*Q,.02*Q)
    if damage=='clock':
        with pytest.raises(ValueError,match='time'):audit_structured_three_temperature_transfer(*args,**BUDGET)
    else:assert not audit_structured_three_temperature_transfer(*args,**BUDGET)['valid']


def test_actual_native_boundary_override_is_inherited_and_thermal_explicit_subset_is_preserved():
    source,old,options=structured_case((3,3,1))
    source._sim.set_dirichlet_potential({0:.003,3:.003,6:.003,2:.005,5:.005,8:.005})
    source.set_thermal_dirichlet({0:310.,3:310.,6:310.})
    device=source.to_three_temperature(old,**options);model=device._model
    for f in device.migration_report['terminal_faces']['left']:
        assert model.bc[f]==.003 and model.bath[f]==310.
    for f in device.migration_report['terminal_faces']['right']:
        assert model.bc[f]==.005 and f not in model.bath


def test_dense_limit_rejected_before_native_seed_read(monkeypatch):
    grid=StructuredGrid(((0.,1.),)*3,1000,1,1)
    source=Simulator(grid);old=ThreeTemperatureState(np.ones(1000),np.ones(1000),np.full(1000,.5),
        np.full(1000,300.),0.,np.full(1000,360.),np.full(1000,260.))
    def forbidden(*a,**k):raise AssertionError('must reject dense dimensions before native read')
    monkeypatch.setattr(source._sim,'structured_three_temperature_seed',forbidden)
    with pytest.raises(ValueError,match='dense'):
        source.to_three_temperature(old,valleys_n=VALLEYS,valleys_p=VALLEYS,Ec_J=0.,Eh_J=0.,
            heat_capacity_J_m3_K=1e6,relaxation_time_n_s=1e-13,relaxation_time_p_s=1e-13)
