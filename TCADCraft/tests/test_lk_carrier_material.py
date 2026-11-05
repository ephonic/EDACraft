"""Independent edge-D/vector-P/Poisson/SG/BE transport verification."""
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest
from scipy.optimize import root

from tcad.core import PyDeviceSimulator
from tcad.postprocess import audit_transient_lk_energy
from test_transient_selfconsistent import QE, VT, bernoulli
from test_lk_fixed_charge import widths


def device(axis=0, stretched=True, log_space=False, source=False, partial=True):
    n=9; shape=[1,1,1];shape[axis]=n
    x=(np.array([0.,.2,.7,1.4,2.5,4.,5.8,7.,8.]) if stretched else np.arange(n))*1e-7
    spacing=[1e-7]*3;sim=PyDeviceSimulator(*shape,*spacing)
    [sim.set_x_positions,sim.set_y_positions,sim.set_z_positions][axis](x)
    eps=8.854187817e-12*(10+np.arange(n));mask=np.ones(n,dtype=np.int8)
    if partial: mask[[0,4,8]]=0
    scale=1e19;c=np.r_[0.,np.linspace(-.1,.2,n-2),0.]*scale
    nn=1+.6*np.sin(np.pi*x/x[-1]);pp=1+.15*np.sin(np.pi*x/x[-1])
    tau=2e-10 if source else 1e100;gen=scale*2e8 if source else 0.
    sim.set_permittivity(eps);sim.set_mobility(np.full(n,.1),np.full(n,.05));sim.set_doping(c)
    sim.set_effective_dos(np.full(n,scale),np.full(n,scale));sim.set_bandgap(np.zeros(n))
    sim.set_thermal_voltage(VT);sim.set_recombination(np.full(n,tau),np.full(n,tau))
    sim.set_optical_generation(np.full(n,gen));sim.set_newton_use_log_space(log_space)
    sim.set_dirichlet_potential({0:0.,n-1:-.01})
    sim.set_electron_bc({0:scale,n-1:scale});sim.set_hole_bc({0:scale,n-1:scale})
    sim.set_initial_guess(np.zeros(n),nn*scale,pp*scale)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(mask,1e8,1e12)
    sim.set_ferroelectric_model(0);sim.set_ferroelectric_gamma(.1)
    sim.set_ferroelectric_polar_axis((axis+1)%3)
    sim.set_ferroelectric_builtin_field(2e4);sim.set_ferroelectric_depol(30.)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_transient_dt(1e-10);sim.set_transient_t_final(2.5e-10)
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-12)
    return sim,dict(x=x,eps=eps,mask=mask,scale=scale,c=c,nn=nn,pp=pp,tau=tau,gen=gen,axis=axis)


def block_step(spec,old,nn_old,pp_old,dt,top=-.01):
    """Solve all 7N-1 unknowns, without eliminating polarization or carriers."""
    x,eps,mask,scale,c,axis=[spec[k] for k in ('x','eps','mask','scale','c','axis')]
    n=len(x);h=np.diff(x);w=widths(x);polar=(axis+1)%3
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
            jn=.1*VT/h*(nn[:-1]*bm-nn[1:]*bp)
            jp=.05*VT/h*(pp[:-1]*bp-pp[1:]*bm)
            rec=(nn*pp-1)/(spec['tau']*(nn+pp+2))
            fn[1:-1]+=dt*(np.diff(jn)/w[1:-1]+rec[1:-1]-spec['gen']/scale)
            fp[1:-1]+=dt*(np.diff(jp)/w[1:-1]+rec[1:-1]-spec['gen']/scale)
        fn[[0,-1]]=nn[[0,-1]]-1;fp[[0,-1]]=pp[[0,-1]]-1
        return np.r_[lk.ravel(),gauss,drops,phi[0]/VT,(phi[-1]-top)/VT,fn,fp]
    guess=np.r_[old.ravel(),np.zeros(n-1),top*x/x[-1],nn_old,pp_old]
    result=root(equations,guess,tol=1e-11)
    assert np.max(np.abs(equations(result.x)))<3e-11, result.message
    y=result.x
    return y[:3*n].reshape(n,3),y[3*n:4*n-1],y[4*n-1:5*n-1],y[5*n-1:6*n-1],y[6*n-1:]


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('log_space',[False,True])
@pytest.mark.parametrize('source',[False,True])
@pytest.mark.parametrize('partial',[False,True])
def test_transport_material_lk_matches_independent_seven_block_system(axis,stretched,log_space,source,partial):
    sim,spec=device(axis,stretched,log_space,source,partial)
    states=sim.solve_transient();old=np.zeros((9,3));nn=spec['nn'];pp=spec['pp']
    for s in states:
        assert s['valid'] and s['lk_coupled'] and s['lk_material_field']
        assert not s['phi_frozen'] and not s['majority_frozen']
        old,d,phi,nn,pp=block_step(spec,old,nn,pp,s['dt_s'] or None)
        np.testing.assert_allclose(s['P'].reshape(-1,3),old,rtol=3e-8,atol=2e-13)
        np.testing.assert_allclose(s['phi'],phi,rtol=3e-8,atol=2e-12)
        np.testing.assert_allclose(s['n']/spec['scale'],nn,rtol=3e-9,atol=1e-12)
        np.testing.assert_allclose(s['p']/spec['scale'],pp,rtol=3e-9,atol=1e-12)
        np.testing.assert_allclose(s['D_'+'xyz'[axis]][:-1],d,rtol=3e-8,atol=2e-15)
        free=QE*1e-14*np.dot(widths(spec['x'])[1:-1],
            spec['c'][1:-1]+spec['scale']*(pp[1:-1]-nn[1:-1]))
        np.testing.assert_allclose(s['electrode_charges_C'],1e-14*np.array([d[0],-d[-1]]),rtol=3e-8,atol=2e-27)
        assert abs(sum(s['electrode_charges_C'])+free)<2e-26
    assert audit_transient_lk_energy(states)['valid']
    assert np.max(abs(states[-1]['n']-states[0]['n']))/spec['scale']>.01


@pytest.mark.parametrize('log_space',[False,True])
def test_transport_failure_rolls_back_and_retry_matches_fresh(log_space):
    sim,_=device(log_space=log_space);sim.set_nonlinear_history_enabled(True);sim.set_gummel_max_iter(0)
    failed=sim.solve_transient()
    assert not failed[-1]['valid'] and failed[-1]['dt_s']==0.
    for key in ('phi','n','p','P'):np.testing.assert_array_equal(failed[-1][key],failed[0][key])
    trial=sim.get_transient_attempt_history()[0]['trials'][0]
    assert trial['solver']=='newton' and trial['solver_called']
    sim.set_gummel_max_iter(100);retry=sim.solve_transient();fresh,_=device(log_space=log_space)
    for a,b in zip(retry,fresh.solve_transient()):
        for key in ('phi','n','p','P'):np.testing.assert_array_equal(a[key],b[key])


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('cells',[8,16,32])
@pytest.mark.parametrize('log_space',[False,True])
def test_mobile_uniform_film_has_no_alternating_polarization(axis,cells,log_space):
    shape=[1,1,1];shape[axis]=cells+1;spacing=[1e-7]*3;spacing[axis]=20e-9/cells
    sim=PyDeviceSimulator(*shape,*spacing);n=cells+1;zero=np.zeros(n);density=np.full(n,1e16)
    sim.set_permittivity(np.full(n,15*8.854187817e-12));sim.set_mobility(np.full(n,.1),np.full(n,.05))
    sim.set_doping(zero);sim.set_effective_dos(density,density);sim.set_bandgap(zero);sim.set_thermal_voltage(VT)
    sim.set_dirichlet_potential({0:0.,n-1:0.});sim.set_electron_bc({0:1e16,n-1:1e16});sim.set_hole_bc({0:1e16,n-1:1e16})
    sim.set_initial_guess(zero,density,density);sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    alpha,beta,gamma=-649519052.838329,331387271.85629034,.1
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(np.ones(n,dtype=np.int8),alpha,beta)
    sim.set_ferroelectric_model(0);sim.set_ferroelectric_gamma(gamma);sim.set_ferroelectric_polar_axis(axis)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True);sim.set_newton_use_log_space(log_space)
    t=np.linspace(0.,2e-10,9);top=-2*np.sin(2*np.pi*t/t[-1])
    sim.set_transient_voltage_waveforms(t,{n-1:top});sim.set_transient_dt(2.5e-11);sim.set_transient_t_final(t[-1])
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-12)
    states=sim.solve_transient();previous=0.
    for s in states:
        assert s['valid'] and s['lk_material_field']
        if s['dt_s']:
            rate=gamma/s['dt_s'];field=-np.interp(s['time_s'],t,top)/20e-9
            roots=np.roots([beta,0.,alpha+rate,-(rate*previous+field)])
            previous=next(z.real for z in roots if abs(z.imag)<1e-10)
        p=s['P'].reshape(-1,3)[:,axis]
        np.testing.assert_allclose(p,previous,rtol=1e-9,atol=2e-11)
        assert np.ptp(p)<2e-11
        np.testing.assert_allclose(s['n']/1e16,1.,rtol=2e-8,atol=2e-10)
        np.testing.assert_allclose(s['p']/1e16,1.,rtol=2e-8,atol=2e-10)
    assert audit_transient_lk_energy(states)['valid']


@pytest.mark.parametrize('log_space',[False,True])
def test_adaptive_commits_satisfy_transport_and_material_lk(log_space):
    from test_transient_lk_error_control import controlled
    from tcad.postprocess import audit_transient_lk_electrical_error_control
    sim,spec=device(log_space=log_space,source=True)
    controlled(sim,rtol=1e-3,atol=1e-8)
    sim.set_transient_lk_electrical_error_control(phi_atol=1e-5,carrier_rtol=1e-3,carrier_atol=1e10)
    states=sim.solve_transient();old=np.zeros((9,3));nn=spec['nn'];pp=spec['pp']
    for s in states:
        assert s['valid'] and s['lk_material_field']
        old,_,phi,nn,pp=block_step(spec,old,nn,pp,s['dt_s'] or None)
        np.testing.assert_allclose(s['phi'],phi,rtol=3e-8,atol=2e-12)
        np.testing.assert_allclose(s['n']/spec['scale'],nn,rtol=3e-9)
        np.testing.assert_allclose(s['p']/spec['scale'],pp,rtol=3e-9)
        np.testing.assert_allclose(s['P'].reshape(-1,3),old,rtol=3e-8,atol=2e-13)
    assert audit_transient_lk_energy(states)['valid']
    assert audit_transient_lk_electrical_error_control(states)['valid']


def commercial_control(case,cells):
    """Zero-FE control: the commercial Silicon probe never activated GLK."""
    raw=case['raw'];n=cells+1;times=np.array(raw['time']);voltage=np.array(raw['top OuterVoltage'])
    nn=raw['Pos(0,5) eDensity'][0]*1e6;pp=raw['Pos(0,5) hDensity'][0]*1e6
    sim=PyDeviceSimulator(n,1,1,.8e-6/cells,1e-5,1e-6);zero=np.zeros(n)
    sim.set_permittivity(np.full(n,11.7*8.8542e-12));sim.set_mobility(np.full(n,.1),np.full(n,.05));sim.set_doping(zero)
    sim.set_effective_dos(np.full(n,nn),np.full(n,pp));sim.set_bandgap(zero)
    sim.set_thermal_voltage(300*8.617333262145e-5);sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_initial_guess(zero,np.full(n,nn),np.full(n,pp));sim.set_dirichlet_potential({0:0.,n-1:0.})
    sim.set_electron_bc({0:nn,n-1:nn});sim.set_hole_bc({0:pp,n-1:pp})
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(np.zeros(n,dtype=np.int8),1e8,1e12)
    sim.set_ferroelectric_model(0);sim.set_ferroelectric_gamma(.1)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    sim.set_transient_voltage_waveforms(times,{n-1:voltage});sim.set_transient_dt(times[-1]);sim.set_transient_t_final(times[-1])
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12)
    return sim.solve_transient()


def control_errors(case,states):
    raw=case['raw'];actual={};expected={}
    for key,native_key in [('charge','electrode_charges_C'),('total_current','electrode_total_currents_A'),('conduction_current','electrode_conduction_currents_A')]:
        actual[key]=(np.array([s[native_key] for s in states]) if key=='charge' else
            np.vstack([np.zeros(2),*[s[native_key] for s in states[1:]]]))
        if key=='charge':expected[key]=np.column_stack([raw[f'{side} Charge'] for side in ('bottom','top')])
        elif key=='total_current':expected[key]=np.column_stack([raw[f'{side} TotalCurrent'] for side in ('bottom','top')])
        else:expected[key]=np.column_stack([np.array(raw[f'{side} eCurrent'])+raw[f'{side} hCurrent'] for side in ('bottom','top')])
    x=np.linspace(0.,.8e-6,len(states[0]['phi']))
    for coord in ['0.2','0.4','0.6']:
        for key,native_key,unit in [('field','Ex',100),('electron','n',1e6),('hole','p',1e6)]:
            k=key+'_'+coord;actual[k]=np.array([np.interp(float(coord)*1e-6,x,s[native_key]) for s in states])
            dataset={'field':'ElectricField/x','electron':'eDensity','hole':'hDensity'}[key]
            expected[k]=np.array(raw[f'Pos({coord},5) {dataset}'])*unit
    return {k:float(np.max(abs(v-expected[k]))/np.max(abs(expected[k]))) for k,v in actual.items()}


@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('cells',[32,64])
def test_actual_sentaurus_zero_fe_transport_control_and_rejected_fe_reference(index,cells):
    data=json.loads((Path(__file__).parent/'data/sentaurus_carrier_control.json').read_text())
    case=data['cases'][index]
    assert not case['nonzero_fe_reference_accepted']
    assert all(not any(v) for k,v in case['raw'].items() if 'FEPolarization' in k)
    states=commercial_control(case,cells)
    assert all(s['valid'] and s['lk_material_field'] for s in states)
    assert max(control_errors(case,states).values())<data['predeclared_waveform_peak_normalized_budget']
    assert all(np.count_nonzero(s['P'])==0 for s in states)


@pytest.fixture(scope='module')
def quad_response_probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('native C++ probe requires GCC')
    project=Path(__file__).resolve().parents[1];exe=tmp_path_factory.mktemp('carrier_material')/'probe'
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals','-I'+str(project/'src'),
        str(project/'tests/cpp/lk_material_response_probe.cpp'),'-lquadmath','-o',str(exe)],check=True,capture_output=True,text=True)
    return exe


@pytest.mark.parametrize('sign',[-1,1])
def test_quad_material_response_and_full_implicit_derivative(quad_response_probe,sign):
    import mpmath as mp
    lines=subprocess.check_output([str(quad_response_probe),str(sign)],text=True).splitlines()
    assert int(lines[0])==113
    with mp.workdps(90):
        v=list(map(mp.mpf,lines[1:]));x=v[:7];eps=v[7:14];old=v[14:35];phi=v[35:42];p=v[42:63];jac=v[63:]
        mask=[1,1,0,1,1,1,0];w=[((x[i]-x[i-1] if i else 0)+(x[i+1]-x[i] if i<6 else 0))/2 for i in range(7)]
        def equations(pol,potential):
            d=[2*eps[i]*eps[i+1]/(eps[i]+eps[i+1])*((potential[i]-potential[i+1])/(x[i+1]-x[i])+
                (pol[i]/eps[i]+pol[i+1]/eps[i+1])/2) for i in range(6)]
            field=[(((x[i]-x[i-1])*d[i-1] if i else 0)+((x[i+1]-x[i])*d[i] if i<6 else 0))/(2*w[i]) for i in range(7)]
            return mp.matrix([(mp.mpf('9e8')*pol[i]+mp.mpf('1e12')*pol[i]**3-mp.mpf('1e9')*old[3*i]-
                (field[i]-pol[i])/eps[i]) if mask[i] else pol[i] for i in range(7)])
        actual=[p[3*i] for i in range(7)]
        expected=mp.findroot(lambda *z:equations(z,phi),tuple(actual),tol=mp.mpf('1e-80'))
        assert max(abs(actual[i]-expected[i]) for i in range(7))<mp.mpf('1e-28')
        jp=mp.matrix([[mp.diff(lambda z:equations([expected[k] if k!=j else z for k in range(7)],phi)[i],expected[j]) for j in range(7)] for i in range(7)])
        for col in range(7):
            rhs=mp.matrix([-mp.diff(lambda z:equations(expected,[phi[k] if k!=col else z for k in range(7)])[i],phi[col]) for i in range(7)])
            response=mp.lu_solve(jp,rhs)
            assert max(abs(jac[row*7+col]-response[row]) for row in range(7))<mp.mpf('1e-26')
        # A potential far from a node has a real nonlocal P response.
        assert abs(jac[3*7+6])>mp.mpf('1e-7')
