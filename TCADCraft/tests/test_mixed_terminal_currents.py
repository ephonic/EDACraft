"""Independent mixed-grid electrode charge, Ampere current and commercial controls."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.postprocess import integrate_transient_terminal_history
from tcad.validation.electrode_charge import audit_electrode_charge_balance
from test_transient_mixed_volumes import CASES, SCALE, QE, EPS, mixed_device, face_rates
from test_transient_selfconsistent import central_cell
from test_transient_displacement import film


def port_reconstruction(states, spec, require_export=True):
    """Reconstruct boundary D and SG directly from potentials/densities/geometry."""
    charge = {'si': 1.602176634e-19, 'legacy-charge': 1.602192e-19}[native_constants()['profile']]
    i,j=spec['i'],spec['j']; contacts=spec['contacts'];free=~contacts
    left=contacts[i]&~contacts[j];right=~contacts[i]&contacts[j]
    area=spec['area'];distance=spec['distance']
    def boundary(values):return np.array([values[left].sum(),-values[right].sum()])
    enclosed=[];charges=[];kcl=[];increment_error=[]
    for index,state in enumerate(states):
        assert state['valid'] and state['electrode_charge_available']
        expected=boundary(-EPS*np.diff(state['phi'][np.c_[i,j]],axis=1).ravel()/distance*area)
        np.testing.assert_allclose(state['electrode_charges_C'],expected,rtol=2e-10,atol=1e-35)
        q=charge*np.dot((state['p']-state['n'])[free],spec['volume'][free])
        enclosed.append(q);charges.append(expected)
        if not index:
            assert not state['displacement_current_available']
            assert not state['total_terminal_current_available']
            continue
        previous=states[index-1];dt=state['dt_s']
        rn,rp=face_rates(spec,state['phi'],state['n']/SCALE,state['p']/SCALE)
        conduction=boundary(charge*SCALE*(-rn+rp))
        delta_phi=state['phi']-previous['phi']
        displacement=boundary(-EPS*(delta_phi[j]-delta_phi[i])/distance*area/dt)
        total=conduction+displacement
        scale=max(np.max(np.abs(conduction)),np.max(np.abs(displacement)))
        assert scale>0.
        kcl.append(float(abs(total.sum())/scale))
        assert kcl[-1]<1e-7
        if require_export:
            assert state['total_terminal_current_available']
            for key,reference in [('conduction',conduction),('displacement',displacement),('total',total)]:
                actual=state['electrode_'+key+'_currents_A']
                assert np.max(np.abs(actual-reference))/scale<2e-9
            np.testing.assert_array_equal(state['electrode_polarization_currents_A'],0.)
            np.testing.assert_array_equal(state['electrode_dielectric_currents_A'],
                                          state['electrode_displacement_currents_A'])
            expected_increment=dt*displacement
            error=np.max(np.abs(state['electrode_charge_increments_C']-expected_increment))
            increment_error.append(float(error/(dt*scale)))
            assert increment_error[-1]<2e-9
            assert not state['dielectric_energy_available']
    enclosed=np.array(enclosed);charges=np.array(charges)
    audit=audit_electrode_charge_balance([s['time_s'] for s in states],charges,enclosed,
        boundary_coverage_complete=True,converged=True,charge_scale_C=max(abs(enclosed)),
        charge_atol_C=0.,charge_rtol=1e-7)
    assert audit['charge_balance_compatible']
    if require_export:
        integrated=integrate_transient_terminal_history(states)
        assert not integrated['energy_balance_validated'] and not integrated['physical_validated']
    return dict(max_gauss_normalized_error=float(max(abs(charges.sum(axis=1)+enclosed))/max(abs(enclosed))),
        max_kcl_normalized_error=max(kcl),max_increment_scaled_error=max(increment_error,default=0.))


@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('log_space',[False,True])
def test_mixed_space_charge_has_independent_gauss_and_ampere(case,stretched,log_space):
    sim,spec=mixed_device(case,stretched,log_space,True)
    states=sim.solve_transient();port_reconstruction(states,spec)
    altered=deepcopy(states)
    altered[-1]['electrode_total_currents_A'][0]*=1.2
    with pytest.raises(AssertionError):port_reconstruction(altered,spec)


@pytest.mark.parametrize('defect',[
    'frozen','fraction','carrier_contact','single_blocked','nonzero_blocked_charge',
    'blocked_generation','blocked_srh','partial_potential_contact',
])
@pytest.mark.parametrize('log_space',[False,True])
def test_mixed_terminal_scope_rejects_inconsistent_rows(defect,log_space):
    sim,spec=mixed_device(CASES[0],True,log_space,True)
    blocked=np.flatnonzero(spec['blocked']&~spec['contacts'])[0]
    mobile=np.flatnonzero(~spec['blocked']&~spec['contacts'])[0]
    if defect=='frozen':sim.set_newton_freeze_phi(True)
    elif defect=='fraction':
        fraction=np.ones(len(spec['n']));fraction[mobile]=.5;sim.set_charge_volume_fraction(fraction)
    elif defect=='carrier_contact':sim.set_electron_bc({int(mobile):float(spec['n'][mobile]*SCALE)})
    elif defect=='single_blocked':
        mu=spec['mu_p'].copy();mu[mobile]=0.;sim.set_mobility(spec['mu_n'],mu)
    elif defect=='nonzero_blocked_charge':
        n=spec['n']*SCALE;n[blocked]=5e-21
        sim.set_initial_guess(np.zeros(len(n)),n,spec['p']*SCALE)
    elif defect=='blocked_generation':
        g=spec['generation']*SCALE;g[blocked]=1.;sim.set_optical_generation(g)
    elif defect=='blocked_srh':
        tau=spec['tau'].copy();tau[blocked]=1.;sim.set_recombination(tau,tau)
    else:sim.set_dirichlet_potential({int(mobile):0.})
    states=sim.solve_transient()
    assert all(s['valid'] for s in states)
    assert not states[1]['total_terminal_current_available']
    assert 'electrode_total_currents_A' not in states[1]
    with pytest.raises(ValueError):integrate_transient_terminal_history(states[:2])


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('log_space',[False,True])
@pytest.mark.parametrize('defect',['negative_generation','negative_lifetime'])
def test_active_terminal_scope_rejects_invalid_pair_sources(axis,log_space,defect):
    sim,*_=central_cell(1e16,log_space,axis,True)
    if defect=='negative_generation':sim.set_optical_generation(np.full(3,-1.))
    else:sim.set_recombination(np.full(3,-1e100),np.full(3,-1e100))
    states=sim.solve_transient()
    assert all(s['valid'] for s in states)
    assert not any(s['total_terminal_current_available'] for s in states)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('log_space',[False,True])
def test_dielectric_interval_does_not_erase_blocked_net_charge(axis,log_space):
    sim,*_=film(axis,2,True)
    n=np.zeros(9);n[4]=5e-21
    sim.set_initial_guess(np.zeros(9),n,np.zeros(9))
    sim.set_newton_use_log_space(log_space)
    states=sim.solve_transient()
    assert all(s['valid'] for s in states)
    assert not states[1]['total_terminal_current_available']


def parallel_device(case,axis,log_space):
    raw=case['raw'];transverse=(axis+1)%3
    shape=[1,1,1];shape[axis]=9;shape[transverse]=6
    spacings=[1e-6]*3;spacings[axis]=.075e-6;spacings[transverse]=.1e-6
    sim=PyDeviceSimulator(*shape,*spacings)
    positions=[np.array([0.]) for _ in range(3)]
    positions[axis]=np.linspace(0,.6e-6,9)
    positions[transverse]=(np.arange(6)+.5)*.1e-6
    for x,setter in zip(positions,[sim.set_x_positions,sim.set_y_positions,sim.set_z_positions]):setter(x)
    xyz=np.array([(i,j,k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    mobile=xyz[:,transverse]<4;left=xyz[:,axis]==0;right=xyz[:,axis]==8
    ni=np.sqrt(raw['Pos(0.3,0.2) eDensity'][0]*raw['Pos(0.3,0.2) hDensity'][0])*1e6
    size=len(xyz);zero=np.zeros(size);density=ni*mobile
    sim.set_permittivity(np.where(mobile,11.7,3.9)*8.8542e-12)
    sim.set_mobility(mobile*.1,mobile*.05);sim.set_doping(zero)
    sim.set_effective_dos(np.full(size,ni),np.full(size,ni));sim.set_bandgap(zero)
    sim.set_recombination(np.full(size,1e100),np.full(size,1e100))
    sim.set_thermal_voltage(300*8.617333262145e-5)
    sim.set_initial_guess(zero,density,density)
    contacts=np.flatnonzero(left|right)
    sim.set_dirichlet_potential({int(i):0. for i in contacts})
    sim.set_electron_bc({int(i):float(density[i]) for i in contacts})
    sim.set_hole_bc({int(i):float(density[i]) for i in contacts})
    times=np.array(raw['time'])
    sim.set_transient_voltage_waveforms(times,{int(i):np.array(raw['left OuterVoltage']) for i in np.flatnonzero(left)})
    sim.set_transient_dt(times[-1]);sim.set_transient_t_final(times[-1])
    sim.set_newton_use_log_space(log_space);sim.set_gummel_max_iter(80);sim.set_tolerance(1e-13)
    return sim,dict(mobile=mobile,ni=ni,axis=axis,xyz=xyz)


def parallel_errors(case,states,spec):
    raw=case['raw'];errors={}
    for port,index in [('left',0),('right',1)]:
        for label,key in [('total','TotalCurrent'),('displacement','DisplacementCurrent'),('conduction',None)]:
            expected=np.array(raw[port+' '+key]) if key else np.array(raw[port+' eCurrent'])+raw[port+' hCurrent']
            actual=np.r_[0.,[s['electrode_'+label+'_currents_A'][index] for s in states[1:]]]
            errors[port+'_'+label]=float(max(abs(actual-expected))/max(abs(expected)))
        expected=np.array(raw[port+' Charge']);actual=np.array([s['electrode_charges_C'][index] for s in states])
        errors[port+'_charge']=float(max(abs(actual-expected))/max(abs(expected)))
    for name in ['n','p']:
        reference=np.array(raw['Pos(0.3,0.2) '+('eDensity' if name=='n' else 'hDensity')])*1e6
        actual=np.array([np.mean(s[name][spec['mobile']]) for s in states])
        errors[name]=float(max(abs(actual-reference))/max(abs(reference)))
    coordinate=spec['xyz'][:,spec['axis']]/8
    for s,v in zip(states,raw['left OuterVoltage']):
        assert np.max(np.abs(s['phi']-v*(1-coordinate)))<1e-11
    return errors


@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('log_space',[False,True])
def test_actual_sentaurus_parallel_mixed_terminal_components(index,axis,log_space):
    data=json.loads((Path(__file__).parent/'data/sentaurus_parallel_mixed.json').read_text())
    case=data['cases'][index];sim,spec=parallel_device(case,axis,log_space)
    states=sim.solve_transient()
    assert len(states)==len(case['raw']['time'])==21
    assert all(s['valid'] for s in states)
    assert all(s['total_terminal_current_available'] for s in states[1:])
    errors=parallel_errors(case,states,spec)
    assert max(errors.values())<data['plan']['waveform_peak_normalized_budget']
    for state in states[1:]:
        currents=state['electrode_total_currents_A']
        assert abs(sum(currents))<1e-8*max(abs(currents))
    result=integrate_transient_terminal_history(states)
    assert not result['energy_balance_validated'] and not result['physical_validated']
