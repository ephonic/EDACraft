"""Coupled spatial energy rows, blocked carrier faces, stiffness and ownership."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from scipy.optimize import root
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.three_temperature import ThreeTemperatureElectrothermal,ThreeTemperatureState
from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw as Law
from tcad.solver.lattice_excess import LatticeCoupledExcessRelaxation
from tcad.postprocess.lattice_excess import audit_lattice_excess_step
from tcad.postprocess.fermi_spectral_energy import reference_reservoir
from tcad.core._bindings import PyDeviceSimulator
from test_fermi_spectral import VALLEYS,BUDGET


def lattice_case(a=-20000.,c=20000.,count=2,graded=False,kappa=1000.):
    widths=np.linspace(.5,1.5,count)*1e-7 if graded else np.full(count,1e-7)
    mesh=region_cut_cells([np.r_[0.,np.cumsum(widths)],np.array([0.,1e-7]),np.array([0.,1e-7])],{'box':[[]]})
    internal=[i for i,f in enumerate(mesh.faces) if f.neighbor>=0]
    bc={i:0. for i,f in enumerate(mesh.faces) if f.neighbor<0}
    model=ThreeTemperatureElectrothermal(mesh,permittivity_F_m=1e-10,dirichlet_V=bc,
        mobility_n_m2_Vs=.01,mobility_p_m2_Vs=.01,Ec_J=0.,Eh_J=0.,valleys_n=VALLEYS,valleys_p=VALLEYS,
        heat_capacity_J_m3_K=1000.,thermal_conductivity_W_m_K=np.linspace(kappa,2*kappa,count),
        thermionic_faces=internal,emission_factor_n=0.,emission_factor_p=0.,
        relaxation_time_n_s=1e-13,relaxation_time_p_s=4e-13,
        relaxation_law_n=Law(150.,5e24,a,0.,c),relaxation_law_p=Law(150.,5e24,a,0.,c))
    T=np.linspace(300.,301.,count);density=np.full(count,1e25)
    state=ThreeTemperatureState(density,density,np.full(count,.5),T,0.,T+60.,T-40.)
    return model,state


@pytest.mark.parametrize('a,c',[(-20000.,20000.),(20000.,-20000.),(0.,0.)])
@pytest.mark.parametrize('count,graded',[(2,False),(2,True),(4,True)])
def test_actual_coupled_three_step_paths_close_local_faces_and_whole_device(a,c,count,graded):
    model,initial=lattice_case(a,c,count,graded);device=LatticeCoupledExcessRelaxation(model,initial)
    assert all(Decimal(c.parameters[0])==1000 for c in device.configuration.cells)
    for dt in (2e-14,5e-14,9e-14):
        old=device.state;new,r=device.advance(dt,**BUDGET)
        audit=audit_lattice_excess_step(device.configuration,old,new,r,**BUDGET)
        assert audit['valid']
        assert Decimal(audit['net_internal_face_divergence_J'])==0
        assert device.native_state()==dict(state=new.raw(),time_s=new.time_s)
        assert not r['complete_device_energy'] and not r['general_carrier_transport_integrated']
        assert max(abs(Decimal(v)) for v in r['face_energy_impulses_J'])>Decimal('1e-23')
    if a<0:assert all(0<abs(Decimal(c.electron_excess_energy_J_m3))<Decimal('1e-70') for c in new.cells)


def test_coupled_conduction_materially_changes_the_solution_from_nearly_insulated_faces():
    endpoints=[]
    for k in (1000.,1e-20):
        model,initial=lattice_case(kappa=k);d=LatticeCoupledExcessRelaxation(model,initial)
        new,r=d.advance(2e-14,**BUDGET);endpoints.append(float(new.cells[0].lattice_temperature_K))
    assert abs(endpoints[0]-endpoints[1])>.1


def test_moderate_blocked_device_matches_existing_general_native_solver():
    from tcad.solver.device_three_temperature import DeviceThreeTemperature
    model,old=lattice_case(-.4,.3);d=LatticeCoupledExcessRelaxation(model,old);general=DeviceThreeTemperature(model,old)
    new,r=d.advance(2e-14,**BUDGET);other,reference=general.advance(2e-14,**BUDGET)
    np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],other.temperature_K,atol=2e-6,rtol=0)
    for i,row in enumerate(r['cell_exchange_J']):
        for k,label in enumerate(('electrons','holes')):assert abs(float(row[k])-reference['cell_exchange_J'][label][i])<1e-25


def test_forced_coupled_solution_matches_independent_all_temperature_root():
    model,old=lattice_case(0.,0.,graded=True);device=LatticeCoupledExcessRelaxation(model,old)
    power=np.array([[1e-5,0.,2e-5],[0.,-1e-5,-2e-5]]);dt=2e-14
    new,r=device.advance(dt,source_power_W=power,**BUDGET)
    def U(i,k,T):return reference_reservoir(1e25,float(T),0.,VALLEYS)['energy_density_J_m3']
    u0=np.array([[U(i,k,T) for k,T in enumerate((old.electron_temperature_K[i],old.hole_temperature_K[i]))] for i in range(2)])
    f=model.internal[0];G=model.area[f]/(model.do[f]/model.conductivity[0]+model.dn[f]/model.conductivity[1])
    def residual(x):
        T=x.reshape(2,3);rows=[];flux=dt*G*(T[0,2]-T[1,2])
        for i in range(2):
            ex=np.array([dt/model.tau_n[i]*(U(i,0,T[i,0])-U(i,0,T[i,2])),
                         dt/model.tau_p[i]*(U(i,1,T[i,1])-U(i,1,T[i,2]))])
            rows.extend([U(i,k,T[i,k])-u0[i,k]+ex[k]-dt*power[i,k]/model.vol[i] for k in range(2)])
            rows.append(model.capacity[i]*(T[i,2]-old.temperature_K[i])-sum(ex)-dt*power[i,2]/model.vol[i]+(flux if i==0 else -flux)/model.vol[i])
        return rows
    answer=root(residual,np.array([[350.,265.,303.],[351.,266.,303.]]).ravel(),tol=1e-10)
    assert answer.success
    np.testing.assert_allclose([float(c.lattice_temperature_K) for c in new.cells],answer.x.reshape(2,3)[:,2],rtol=0,atol=2e-6)


@pytest.fixture(scope='module')
def accepted_step():
    model,initial=lattice_case();device=LatticeCoupledExcessRelaxation(model,initial);old=device.state
    power=np.array([[1e-5,0.,0.],[0.,-1e-5,0.]])
    new,r=device.advance(2e-14,source_power_W=power,**BUDGET)
    return device.configuration,old,new,r,power


@pytest.mark.parametrize('damage',['face','reverse_face','drop_face','cell_row','exchange','storage','lattice','tau',
    'power','source','scope','complete','carrier_claim','drop_excess','density','clock'])
def test_independent_audit_detects_forged_faces_states_and_external_work(accepted_step,damage):
    config,old,new,report,power=accepted_step;r=deepcopy(report)
    if damage=='face':r['face_energy_impulses_J'][0]='0'
    elif damage=='reverse_face':r['face_energy_impulses_J'][0]=str(-Decimal(r['face_energy_impulses_J'][0]))
    elif damage=='drop_face':r['face_energy_impulses_J']=[]
    elif damage=='cell_row':r['cell_energy_residuals_J'][0][2]='1e-20'
    elif damage=='exchange':r['cell_exchange_J'][0][0]='0'
    elif damage=='storage':r['cell_carrier_energy_increments_J'][0][0]='0'
    elif damage=='lattice':r['cell_lattice_energy_increments_J'][0]='0'
    elif damage=='tau':r['cell_effective_relaxation_times_s'][0][0]='1'
    elif damage=='power':r['source_power_W'][0][0]*=2
    elif damage=='source':r['source_impulses_J'][0][0]='0'
    elif damage=='scope':r['scope']='general'
    elif damage=='complete':r['complete_device_energy']=True
    elif damage=='carrier_claim':r['general_carrier_transport_integrated']=True
    elif damage in ('drop_excess','density'):
        change=dict(electron_excess_energy_J_m3='0') if damage=='drop_excess' else dict(density_n_m3='2e25')
        new=replace(new,cells=(replace(new.cells[0],**change),new.cells[1]))
    elif damage=='clock':new=replace(new,time_s=new.time_s*2,cells=tuple(replace(c,time_s=new.time_s*2) for c in new.cells))
    try:audit=audit_lattice_excess_step(config,old,new,r,source_power_W=power,**BUDGET)
    except (ValueError,KeyError):return
    assert not audit['valid']


@pytest.mark.parametrize('failure',['budget','audit','decode','interrupt','bracket'])
def test_failed_coupled_step_preserves_native_state_clock_and_retry(monkeypatch,failure):
    model,initial=lattice_case();d=LatticeCoupledExcessRelaxation(model,initial);before=d.native_state();old=d.state
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.lattice_excess.audit_lattice_excess_step',lambda *a,**k:dict(valid=False))
        if failure in ('decode','interrupt'):
            def fail(*a,**k):raise (KeyboardInterrupt if failure=='interrupt' else ValueError)('injected')
            patch.setattr(d,'_decode_candidate',fail)
        power=np.full((2,3),1e5) if failure=='bracket' else None
        with pytest.raises((RuntimeError,ValueError,KeyboardInterrupt)):
            d.advance(2e-14,source_power_W=power,max_nfev=1 if failure=='budget' else 600,**BUDGET)
    assert d.state is old and d.native_state()==before
    actual,_=d.advance(2e-14,**BUDGET);fresh=LatticeCoupledExcessRelaxation(model,initial);expected,_=fresh.advance(2e-14,**BUDGET)
    assert actual==expected


@pytest.mark.parametrize('damage',['open_n','open_p','bulk_face','bath','contact','b','generation','intercarrier'])
def test_unsupported_physics_is_rejected_before_native_initialization(damage):
    model,initial=lattice_case()
    if damage.startswith('open_'):model.emission['electrons' if damage=='open_n' else 'holes'][int(model.internal[0])]=1.
    elif damage=='bulk_face':model.thermionic_faces=()
    elif damage=='bath':model.bath={int(model.internal[0]):300.}
    elif damage=='contact':model.contacts={0:object()}
    elif damage=='b':model.relaxation_laws=(Law(150.,5e24,-.4,.1,.3),)*2
    elif damage=='generation':model.pair_generation_rate_m3_s=np.ones(2)
    else:model.intercarrier_conductance_W_m3_K=np.ones(2)
    with pytest.raises(ValueError):LatticeCoupledExcessRelaxation(model,initial)


def test_owned_configuration_and_native_transaction_tokens():
    model,initial=lattice_case();d=LatticeCoupledExcessRelaxation(model,initial);before=d.native_state()
    raw,token=d._backend.prepare_isolated_relaxation(2e-14,**BUDGET)
    assert d.native_state()==before
    with pytest.raises(RuntimeError,match='pending'):d._backend.prepare_isolated_relaxation(2e-14,**BUDGET)
    with pytest.raises(RuntimeError,match='stale'):d._backend.commit_isolated_relaxation(token+1)
    d._backend.discard_isolated_relaxation(token)
    model.conductivity=np.full(2,1e-30)
    new,r=d.advance(2e-14,**BUDGET);assert r['independent_audit']['valid']
    copy=d.native_state();copy['state'][2]='1';assert d.native_state()!=copy
    with pytest.raises((ValueError,RuntimeError)):d._backend.solve()


@pytest.mark.parametrize('invalid',[(2,3),[[True,False,False]]*2,[[float('nan'),0,0]]*2])
def test_invalid_source_matrix_is_rejected_without_advancing(invalid):
    model,initial=lattice_case();d=LatticeCoupledExcessRelaxation(model,initial);before=d.native_state()
    with pytest.raises(ValueError):d.advance(2e-14,source_power_W=invalid,**BUDGET)
    assert before==d.native_state()


@pytest.mark.parametrize('damage',['width','negative_G','self','duplicate','fractional','cell_count','capacity','clock'])
def test_native_configuration_failure_is_retryable(damage):
    model,initial=lattice_case();d=LatticeCoupledExcessRelaxation(model,initial);c=d.configuration
    raw_initial=[v for cell in c.cells for v in (*cell.initial_densities_m3,cell.initial_temperatures_K[2],*cell.initial_temperatures_K[:2])]
    params=[v for cell in c.cells for v in cell.parameters];faces=c.packed_faces();time=0.
    bad_initial=raw_initial.copy();bad_params=params.copy();bad_faces=faces.copy()
    if damage=='width':bad_faces=bad_faces[:-1]
    elif damage=='negative_G':bad_faces[2]='-1'
    elif damage=='self':bad_faces[1]=bad_faces[0]
    elif damage=='duplicate':bad_faces*=2
    elif damage=='fractional':bad_faces[0]='0.5'
    elif damage=='cell_count':bad_initial=bad_initial[:-1]
    elif damage=='capacity':bad_params[0]='0'
    else:time=float('nan')
    backend=PyDeviceSimulator(2,1,1,1.,1.,1.)
    with pytest.raises((ValueError,RuntimeError)):
        backend.configure_lattice_excess(bad_initial,bad_params,bad_faces,*c.cells[0].packed_valleys(),time)
    backend.configure_lattice_excess(raw_initial,params,faces,*c.cells[0].packed_valleys(),0.)
    assert backend.isolated_relaxation_state()==d.native_state()
    result,token=backend.prepare_isolated_relaxation(2e-14,**BUDGET);backend.discard_isolated_relaxation(token)
