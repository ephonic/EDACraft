"""Midpoint insulator/semiconductor interfaces: independent full block solve."""
import numpy as np
import pytest
import json
from pathlib import Path
from scipy.optimize import root
from test_lk_carrier_material import device
from tcad.core import PyDeviceSimulator
from tcad.validation.conservation import TransientConservationTest
from test_lk_fixed_charge import widths
from test_transient_selfconsistent import QE, VT, bernoulli


def interface_device(axis=0, stretched=False, log_space=False, source=False):
    sim,spec=device(axis,stretched,log_space,source,False)
    blocked=np.arange(9)<4;mobile=~blocked;mask=blocked.astype(np.int8)
    nn=spec['nn'].copy();pp=spec['pp'].copy();nn[blocked]=0;pp[blocked]=0
    c=spec['c'].copy();c[blocked]=0
    sim.set_mobility(mobile.astype(float)*.1,mobile.astype(float)*.05)
    sim.set_doping(c);sim.set_ferroelectric_params(mask,1e8,1e12)
    sim.set_initial_guess(np.zeros(9),nn*spec['scale'],pp*spec['scale'])
    # The low-level BC setters merge entries; explicitly replace the inherited
    # gate reservoir with zero density on the blocked gate endpoint.
    sim.set_electron_bc({0:0.,8:spec['scale']});sim.set_hole_bc({0:0.,8:spec['scale']})
    tau=np.full(9,spec['tau']);tau[blocked]=1e100
    gen=np.full(9,spec['gen']);gen[blocked]=0
    sim.set_recombination(tau,tau);sim.set_optical_generation(gen)
    spec.update(mask=mask,c=c,nn=nn,pp=pp,tau=tau,gen=gen,blocked=blocked)
    return sim,spec


def independent_step(s,old,nn_old,pp_old,dt):
    x,eps,mask,scale,c,axis=[s[k] for k in ('x','eps','mask','scale','c','axis')]
    n=len(x);h=np.diff(x);w=widths(x);blocked=s['blocked'];mobile=~blocked
    edge=mobile[:-1]&mobile[1:];polar=(axis+1)%3
    def equations(y):
        p=y[:3*n].reshape(n,3);d=y[3*n:4*n-1];phi=y[4*n-1:5*n-1]
        nn=y[5*n-1:6*n-1];pp=y[6*n-1:]
        mean_d=(np.r_[h*d,0.]+np.r_[0.,h*d])/(2*w)
        field=np.zeros_like(p);field[:,axis]=(mean_d-p[:,axis])/eps
        if dt is None:lk=p-old
        else:
            lk=(1e8*p+1e12*p**3+.1/dt*(p-old)-field)/1e9
            lk[:,polar]+=(2e4+p[:,polar]/(30*8.854187817e-12))/1e9
            lk[mask==0]=p[mask==0]
        gauss=(np.diff(d)/w[1:-1]-QE*(c[1:-1]+scale*(pp[1:-1]-nn[1:-1])))/(QE*scale)
        drops=(phi[:-1]-phi[1:]-h/2*((d-p[:-1,axis])/eps[:-1]+(d-p[1:,axis])/eps[1:]))/VT
        fn=nn-nn_old;fp=pp-pp_old
        if dt is not None:
            delta=np.diff(phi)/VT
            bp=np.array([bernoulli(v) for v in delta]);bm=np.array([bernoulli(-v) for v in delta])
            jn=edge*.1*VT/h*(nn[:-1]*bm-nn[1:]*bp)
            jp=edge*.05*VT/h*(pp[:-1]*bp-pp[1:]*bm)
            rec=(nn*pp-1)/(s['tau']*(nn+pp+2))
            fn[1:-1]+=dt*(np.diff(jn)/w[1:-1]+rec[1:-1]-s['gen'][1:-1]/scale)
            fp[1:-1]+=dt*(np.diff(jp)/w[1:-1]+rec[1:-1]-s['gen'][1:-1]/scale)
        fn[blocked]=nn[blocked];fp[blocked]=pp[blocked]
        fn[-1]=nn[-1]-1;fp[-1]=pp[-1]-1
        return np.r_[lk.ravel(),gauss,drops,phi[0]/VT,(phi[-1]+.01)/VT,fn,fp]
    guess=np.r_[old.ravel(),np.zeros(n-1),-.01*x/x[-1],nn_old,pp_old]
    result=root(equations,guess,tol=1e-11)
    assert max(abs(equations(result.x)))<4e-11,result.message
    y=result.x
    return y[:3*n].reshape(n,3),y[3*n:4*n-1],y[4*n-1:5*n-1],y[5*n-1:6*n-1],y[6*n-1:]


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('log_space',[False,True])
@pytest.mark.parametrize('source',[False,True])
def test_interface_full_block_and_gauss(axis,stretched,log_space,source):
    sim,s=interface_device(axis,stretched,log_space,source)
    old=np.zeros((9,3));nn=s['nn'];pp=s['pp']
    states=sim.solve_transient()
    for state in states:
        assert state['valid'] and state['lk_material_field'] and state['lk_coupled']
        old,d,phi,nn,pp=independent_step(s,old,nn,pp,state['dt_s'] or None)
        np.testing.assert_allclose(state['P'].reshape(-1,3),old,rtol=4e-8,atol=3e-13)
        np.testing.assert_allclose(state['phi'],phi,rtol=3e-8,atol=3e-12)
        np.testing.assert_allclose(state['n']/s['scale'],nn,rtol=4e-9,atol=2e-12)
        np.testing.assert_allclose(state['p']/s['scale'],pp,rtol=4e-9,atol=2e-12)
        np.testing.assert_allclose(state['D_'+'xyz'[axis]][:-1],d,rtol=3e-8,atol=3e-15)
        free=QE*1e-14*np.dot(widths(s['x'])[1:-1],s['c'][1:-1]+s['scale']*(pp[1:-1]-nn[1:-1]))
        assert abs(sum(state['electrode_charges_C'])+free)<3e-26
    assert max(abs(old[:,axis]))>1e-8
    assert max(abs(nn-s['nn']))>.01
    assert all(state['charge_ledger_available'] for state in states)
    assert all('stored_charge_C' in state for state in states)
    verdict = TransientConservationTest(
        integration='backward_euler', charge_atol_C=0.0, tolerance=1e-5
    ).run(lambda: states)
    assert verdict.passed, verdict.message
    for state in states[1:]:
        currents=state['electrode_total_currents_A']
        assert abs(sum(currents))<1e-10*max(abs(currents))


@pytest.mark.parametrize('bad',['n','p','generation','srh_n','srh_p','unpaired','negative','tiny','n_bc','p_bc'])
def test_blocked_input_is_not_silently_discarded(bad):
    sim,s=interface_device()
    if bad in ('n','p'):
        nn=s['nn'].copy()*s['scale'];pp=s['pp'].copy()*s['scale']
        (nn if bad=='n' else pp)[2]=1.
        sim.set_initial_guess(np.zeros(9),nn,pp)
    elif bad=='generation':
        gen=np.zeros(9);gen[2]=1.;sim.set_optical_generation(gen)
    elif bad.startswith('srh'):
        tn=np.full(9,1e100);tp=tn.copy();(tn if bad=='srh_n' else tp)[2]=1.
        sim.set_recombination(tn,tp)
    elif bad.endswith('_bc'):
        (sim.set_electron_bc if bad=='n_bc' else sim.set_hole_bc)({0:1.})
    else:
        mn=(~s['blocked']).astype(float)*.1;mp=mn/2
        mn[2]={'unpaired':.1,'negative':-.1,'tiny':1e-30}[bad]
        sim.set_mobility(mn,mp)
    with pytest.raises(ValueError,match='paired positive mobilities'):
        sim.solve_transient()


@pytest.mark.parametrize('log_space',[False,True])
def test_interface_failure_rollback_and_retry(log_space):
    sim,_=interface_device(log_space=log_space);sim.set_gummel_max_iter(0)
    failed=sim.solve_transient()
    assert not failed[-1]['valid'] and failed[-1]['dt_s']==0.
    for k in ['P','phi','n','p']:np.testing.assert_array_equal(failed[0][k],failed[-1][k])
    sim.set_gummel_max_iter(100);retry=sim.solve_transient()
    fresh,_=interface_device(log_space=log_space)
    for a,b in zip(retry,fresh.solve_transient()):
        for k in ['P','phi','n','p']:np.testing.assert_array_equal(a[k],b[k])


def commercial_device(case,cells,log_space=False):
    raw=case['raw'];h=.8e-6/cells
    x=np.r_[0.,(np.arange(cells)+.5)*h,.8e-6];n=len(x)
    mask=(x<.2e-6).astype(np.int8);mobile=1-mask;zero=np.zeros(n)
    nn=raw['Pos(0.8,5) eDensity'][0]*1e6;pp=raw['Pos(0.8,5) hDensity'][0]*1e6
    sim=PyDeviceSimulator(n,1,1,h,1e-5,1e-6);sim.set_x_positions(x)
    sim.set_permittivity(np.where(mask,15.,11.7)*8.8542e-12)
    sim.set_mobility(mobile*.1,mobile*.05);sim.set_doping(zero)
    sim.set_effective_dos(np.full(n,nn),np.full(n,pp));sim.set_bandgap(zero)
    sim.set_thermal_voltage(300*8.617333262145e-5)
    sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_initial_guess(zero,mobile*nn,mobile*pp);sim.set_dirichlet_potential({0:0.,n-1:0.})
    sim.set_electron_bc({n-1:nn});sim.set_hole_bc({n-1:pp})
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(mask,1e8,1e12)
    sim.set_ferroelectric_model(0);sim.set_ferroelectric_gamma(.1)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_newton_use_log_space(log_space)
    t=np.array(raw['time']);sim.set_transient_voltage_waveforms(t,{0:np.array(raw['gate OuterVoltage'])})
    sim.set_transient_dt(t[-1]);sim.set_transient_t_final(t[-1])
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-14)
    return sim,x


def commercial_errors(case,states,x):
    raw=case['raw'];actual={};expected={}
    for coord in ['0.1','0.4','0.6']:
        for field,dataset,unit in [('Ex','ElectricField/x',100.)]:
            key=dataset+'_'+coord
            actual[key]=np.array([np.interp(float(coord)*1e-6,x,s[field]) for s in states])
            expected[key]=np.array(raw[f'Pos({coord},5) {dataset}'])*unit
    for coord in ['0.4','0.6','0.8']:
        for field,dataset in [('n','eDensity'),('p','hDensity')]:
            key=dataset+'_'+coord
            actual[key]=np.array([np.interp(float(coord)*1e-6,x,s[field]) for s in states])
            expected[key]=np.array(raw[f'Pos({coord},5) {dataset}'])*1e6
    for coord in ['0.1','0.4','0.6']:
        key='potential_'+coord
        actual[key]=np.array([np.interp(float(coord)*1e-6,x,s['phi']) for s in states])
        expected[key]=np.array(raw[f'Pos({coord},5) ElectrostaticPotential'])
    actual['polarization']=np.array([np.interp(.1e-6,x,s['P'].reshape(-1,3)[:,0]) for s in states])
    expected['polarization']=np.array(raw['Pos(0.1,5) FEPolarization'])*1e4
    # Commercial raw Charge is not a physical free-charge Gauss ledger for
    # this charged stack; keep its rejection separate from waveform acceptance.
    for i,name in enumerate(['gate','substrate']):
        key=name+'_total_current'
        actual[key]=np.r_[0.,[s['electrode_total_currents_A'][i] for s in states[1:]]]
        expected[key]=np.array(raw[name+' TotalCurrent'])
    return {k:float(np.max(abs(v-expected[k]))/np.max(abs(expected[k]))) for k,v in actual.items()}


@pytest.mark.parametrize('index',[0,1])
@pytest.mark.parametrize('cells',[32,64])
@pytest.mark.parametrize('log_space',[False,True])
def test_actual_sentaurus_nonzero_fe_insulator_silicon(index,cells,log_space):
    data=json.loads((Path(__file__).parent/'data/sentaurus_fe_si_interface.json').read_text())
    case=data['cases'][index]
    assert max(abs(np.array(case['raw']['Pos(0.1,5) FEPolarization'])))>1e-12
    sim,x=commercial_device(case,cells,log_space);states=sim.solve_transient()
    assert len(states)==len(case['raw']['time']) and all(s['valid'] for s in states)
    errors=commercial_errors(case,states,x)
    assert max(errors.values())<data['predeclared_waveform_peak_normalized_budget'],errors
    for s in states:
        free=QE*1e-11*np.dot(widths(x)[1:-1],(s['p']-s['n'])[1:-1])
        assert abs(sum(s['electrode_charges_C'])+free)<1e-29
