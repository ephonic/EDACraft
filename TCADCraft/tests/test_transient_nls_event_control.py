"""Public NLS event binding: independent FV/Merz and native-double parity."""
from copy import deepcopy
from functools import lru_cache
import itertools,json,math,os
from pathlib import Path

import numpy as np
import pytest
from tcad.core import PyDeviceSimulator,native_constants
from tcad.simulator import Simulator
from tcad.mesh.structured_grid import StructuredGrid
from tcad.configuration import clone_on_mesh
from test_transient_preflight_history import assert_exact

T,B,S,PS=2.**-40,2.**-25,2.**66,2.**-20
WIDTHS=(2.**-60,2.**-66)
KEYS=('dimension','logarithmic','family','protocol','level')

def voltage(t,protocol):
    if protocol:
        if t<=T:return 2.**-13*t/T
        if t<=1.5*T:return 2.**-13
        if t<=2*T:return 2.**-13+(2.**-10-2.**-13)*(t-1.5*T)/(.5*T)
    return 2.**-10*t/(2*T) if t<=2*T else 2.**-10-2.**-9*(t-2*T)/(2*T)

def configured(dimension=2,logarithmic=False,family=0,protocol=0,level=0,*,manual=False,enable=True):
    nz=3 if dimension==3 else 1;N=9*nz
    sim=PyDeviceSimulator(3,3,nz,B,B,B)
    axes=[np.array([0.,3.,8.])*B,np.array([0.,5.,11.])*B,np.array([0.,2.,7.])*B if nz==3 else np.array([0.])]
    sim.set_x_positions(axes[0]);sim.set_y_positions(axes[1])
    if nz==3:sim.set_z_positions(axes[2])
    coords=[(i,j,k) for k in range(nz) for j in range(3) for i in range(3)]
    eps=np.array([2.**-33*(1+j*.25+k*.5) for i,j,k in coords]);dop=np.array([S*(.125-i*.03125) for i,j,k in coords])
    n=np.array([S*(1+j*.0625+k*.03125+(0 if i!=1 else .5)) for i,j,k in coords]);p=np.array([S*(1+j*.03125+k*.0625+(0 if i!=1 else .25)) for i,j,k in coords])
    bc={q:0. for q,(i,j,k) in enumerate(coords) if i!=1}
    sim.set_permittivity(eps);sim.set_doping(dop);sim.set_mobility(np.full(N,.125),np.full(N,.0625))
    sim.set_effective_dos(np.full(N,S),np.full(N,S));sim.set_bandgap(np.zeros(N));sim.set_recombination(np.full(N,1e100),np.full(N,1e100))
    sim.set_thermal_voltage(.03125);sim.set_newton_use_log_space(logarithmic)
    sim.set_dirichlet_potential(bc);sim.set_electron_bc({q:n[q] for q in bc});sim.set_hole_bc({q:p[q] for q in bc});sim.set_initial_guess(np.zeros(N),n,p)
    sim.set_gummel_max_iter(100);sim.set_tolerance(1e-11);sim.set_transient_dt(.5*T/2**level);sim.set_transient_t_final(4*T);sim.set_nonlinear_history_enabled(True)
    sim.set_ferroelectric_enabled(True);sim.set_ferroelectric_params(np.ones(N,dtype=np.int8),1e8,1e12);sim.set_ferroelectric_model(2);sim.set_ferroelectric_polar_axis(0)
    sim.set_ferroelectric_preisach(PS,1e5,0.);sim.set_ferroelectric_nls(2.**-36,2048.,2.**-50);sim.set_ferroelectric_builtin_field(-512.);sim.set_ferroelectric_gamma(0.);sim.set_transient_lk_coupled(False)
    times=[i*T/4 for i in range(17)]+[2.875*T]
    if manual:
        w=WIDTHS[family]
        times+=([T-w,1.5*T+w,2.875*T-w,2.875*T+w] if protocol else [.25*T-w,.25*T+w,2.875*T-w,2.875*T+w])
    times=np.array(sorted(set(times)));volts=np.array([voltage(t,protocol) for t in times])
    sim.set_transient_voltage_waveforms(times,{q:volts for q in bc if q%3==2})
    if enable is not None:sim.set_transient_nls_event_control(False if manual else enable,WIDTHS[family])
    return sim,dict(axes=axes,coords=coords,eps=eps,doping=dop,times=times,volts=volts)

def trace_view(groups):
    return [[g['start_time_s'],g['attempted_time_s'],g['dt_s'],int(g['accepted']),g['retry_index'],[
        [t['role'],t['solver'],t['start_time_s'],t['attempted_time_s'],t['dt_s'],int(t['converged']),int(t['retained']),int(t['exception'])] for t in g['trials']]] for g in groups]

def check_timeline(history,groups):
    assert all(s['valid'] and not s['phi_frozen'] and not s['majority_frozen'] for s in history)
    assert history[0]['initial_state'] and history[0]['dt_s']==0 and history[-1]['time_s']==4*T
    retained=[t for g in groups for t in g['trials'] if t['retained']]
    assert len(retained)==len(history)-1
    for old,s,t in zip(history,history[1:],retained):
        assert s['time_s']==s['attempted_time_s']==t['attempted_time_s'] and s['dt_s']==t['dt_s']>0
        assert abs(s['time_s']-old['time_s']-s['dt_s'])<2e-27
        assert t['role']=='fixed' and not t['exception']
    assert math.isclose(math.fsum(s['dt_s'] for s in history),history[-1]['time_s']-history[0]['time_s'],rel_tol=2e-15)

def compare(left,right):
    assert len(left)==len(right)
    for a,b in zip(left,right):
        assert math.isclose(a['time_s'],b['time_s'],rel_tol=2e-15,abs_tol=1e-28)
        for name,scale in (('phi',2.**-10),('n',S),('p',S),('P',PS),('electrode_charges_C',1e-18)):
            assert np.max(np.abs(a[name]-b[name]))/scale<1e-8

def independent(history,meta):
    """Dense Gauss predictor and independent conservative FV/SG/BE rows.

    Keep the 475/482 local equation/Merz gates. Float64 output is not used
    to qualify tiny-interval net-charge subtraction or quad restart equality.
    """
    axes,coords,eps,dop=meta['axes'],meta['coords'],meta['eps'],meta['doping'];shape=[len(x) for x in axes];N=len(coords);strides=(1,3,9)
    widths=[np.r_[np.diff(x)[0],np.diff(x).mean(),np.diff(x)[-1]] if len(x)>1 else np.array([B]) for x in axes]
    q=float(native_constants()['elementary_charge_C']);maxima=dict(gauss=0.,BE=0.,current=0.,NLS=0.)
    def bern(x):return x/math.expm1(x) if abs(x)>1e-6 else 1-x/2+x*x/12-x**4/720
    for k,state in enumerate(history):
        phi,n,p,P=(state[f] for f in ('phi','n','p','P'));polar=P.reshape(N,3);dt=state['dt_s'];old=history[k-1] if k else state
        oldP=old['P'].reshape(N,3);matrix=np.zeros((N,N));rhs=np.zeros(N)
        for i,xyz in enumerate(coords):
            if xyz[0]!=1:matrix[i,i]=1;rhs[i]=phi[i]
            else:rhs[i]=q*(old['p'][i]-old['n'][i]+dop[i])
            gauss=divp=0.;rn=(n[i]-old['n'][i])/dt if dt else 0.;rp=(p[i]-old['p'][i])/dt if dt else 0.
            for axis,pos in enumerate(xyz):
                for sign in (-1,1):
                    if not 0<=pos+sign<shape[axis]:continue
                    j=i+sign*strides[axis];edge=abs(axes[axis][pos+sign]-axes[axis][pos]);geom=1/(edge*widths[axis][pos]);face=2*eps[i]*eps[j]/(eps[i]+eps[j]);delta=(phi[j]-phi[i])/.03125
                    gauss+=face*geom*(phi[i]-phi[j]);divp+=sign*face*.5*(polar[i,axis]/eps[i]+polar[j,axis]/eps[j])/widths[axis][pos]
                    rn+=.125*.03125*geom*(n[i]*bern(-delta)-n[j]*bern(delta));rp+=.0625*.03125*geom*(p[i]*bern(delta)-p[j]*bern(-delta))
                    if xyz[0]==1:
                        matrix[i,i]+=face*geom;matrix[i,j]-=face*geom;rhs[i]-=sign*face*.5*(oldP[i,axis]/eps[i]+oldP[j,axis]/eps[j])/widths[axis][pos]
                    if sign==1:
                        for label,density,mu,signj in (('Jn_',n,.125,1),('Jp_',p,.0625,-1)):
                            force=density[j]*bern(delta)-density[i]*bern(-delta) if label=='Jn_' else density[j]*bern(-delta)-density[i]*bern(delta)
                            expected=signj*q*mu*.03125/edge*force
                            defect=abs(state[label+'xyz'[axis]][i]-expected)/(q*mu*.03125/edge*max(density[i],density[j]));assert defect<5e-13
                            maxima['current']=max(maxima['current'],defect)
            if xyz[0]==1:
                defect=abs(gauss+divp-q*(p[i]-n[i]+dop[i]))/(q*S);assert defect<2e-8;maxima['gauss']=max(maxima['gauss'],defect)
                if dt:
                    defect=max(abs(rn),abs(rp))*dt/S;assert defect<1e-8;maxima['BE']=max(maxima['BE'],defect)
        if dt:
            predicted=np.linalg.solve(matrix,rhs);fields=[]
            for i,xyz in enumerate(coords):
                lo=max(0,xyz[0]-1);hi=min(2,xyz[0]+1);fields.append(-(predicted[i+hi-xyz[0]]-predicted[i+lo-xyz[0]])/(axes[0][hi]-axes[0][lo])+512.)
            mean=-(phi[2]-phi[0])/(8*B)+512.;peak=max(abs(mean),max(map(abs,fields)));prior=oldP[0,0]
            target=prior if abs(mean)<=1e-24*max(peak,1.) else PS if mean>0 else -PS
            fraction=-math.expm1(-dt/(2.**-36)*math.exp(-2048/peak)) if peak else 0.
            expected=np.zeros((N,3));expected[:,0]=prior+fraction*(target-prior)
            defect=np.max(abs(polar-expected))/PS;assert defect<2e-8;maxima['NLS']=max(maxima['NLS'],defect)
    return maxima

@lru_cache(None)
def native_rows(path):
    return {tuple(r[k] for k in KEYS):r for r in (json.loads(l) for l in Path(path).open())}

@pytest.mark.parametrize('dimension,logarithmic,family,protocol,level',itertools.product((2,3),(False,True),(0,1),(0,1),(0,1)))
def test_public_event_trajectory_restart_manual_and_native_bridge(dimension,logarithmic,family,protocol,level):
    args=(dimension,logarithmic,family,protocol,level);sim,meta=configured(*args);full=sim.solve_transient();ft=sim.get_transient_attempt_history()
    check_timeline(full,ft);expected_times=([T-WIDTHS[family],T,1.5*T,1.5*T+WIDTHS[family]] if protocol else [.25*T-WIDTHS[family],.25*T,.25*T+WIDTHS[family]])+[2.875*T-WIDTHS[family],2.875*T,2.875*T+WIDTHS[family]]
    for wanted in expected_times:assert sum(abs(s['time_s']-wanted)<1e-28 for s in full)==1
    for s in full:
        np.testing.assert_allclose(s['phi'][2::3],voltage(s['time_s'],protocol),rtol=0.,atol=1e-18)
    if protocol:
        plateau=[s for s in full if T<=s['time_s']<=1.5*T];assert len(plateau)>=3
        for state in plateau:np.testing.assert_array_equal(state['P'],plateau[0]['P'])
        assert any(np.any(plateau[0][f]!=plateau[-1][f]) for f in ('n','p'))
    cut=(1.25 if protocol else .25)*T;index=next(i for i,s in enumerate(full) if s['time_s']==cut);accepted=full[index]
    tail_sim,_=configured(*args);tail_sim.set_initial_guess(accepted['phi'],accepted['n'],accepted['p']);memory=tail_sim.get_ferroelectric_ensemble_history();memory['polarization']=accepted['P'].reshape(-1,3);tail_sim.set_ferroelectric_ensemble_history(memory);tail_sim.set_transient_start_time(cut)
    tail=tail_sim.solve_transient();tt=tail_sim.get_transient_attempt_history();check_timeline(tail,tt);compare(tail,full[index:])
    manual_sim,manual_meta=configured(*args,manual=True);manual=manual_sim.solve_transient();mt=manual_sim.get_transient_attempt_history();check_timeline(manual,mt);compare(full,manual)
    metrics={label:independent(h,m) for label,h,m in (('full',full,meta),('tail',tail,meta),('manual',manual,manual_meta))}
    native_path=os.environ.get('TCAD_NLS_NATIVE_BRIDGE_JSON')
    if native_path:
        native=native_rows(native_path)[args];views={}
        for name,h,tr in (('full',full,ft),('tail',tail,tt),('manual',manual,mt)):
            # Native interval values are exported only when their availability
            # flag is true, matching the public Python result contract.
            views[name]=[{k:(s[k].tolist() if isinstance(s[k],np.ndarray) else s[k]) for k in wanted} for s,wanted in zip(h,native[name])]
            availability={'charge_ledger_available':('stored_charge_C','terminal_currents_A'),
                'electrostatic_flux_available':('D_x','D_y','D_z'),
                'displacement_current_available':tuple(prefix+axis for prefix in ('Jdisp_','Jdielectric_','Jpolarization_') for axis in 'xyz'),
                'electrode_charge_available':('electrode_charges_C','electrode_voltages_V'),
                'total_terminal_current_available':('electrode_total_currents_A','electrode_displacement_currents_A','electrode_conduction_currents_A','electrode_dielectric_currents_A','electrode_polarization_currents_A','electrode_charge_increments_C')}
            for state in h:
                for flag,fields in availability.items():
                    for field in fields:assert (field in state)==state[flag]
            assert len(h)==len(native[name]);assert_exact(views[name],native[name]);assert_exact(trace_view(tr),native[name+'_trace'])
        output=os.environ.get('TCAD_NLS_BRIDGE_RECORDS')
        if output:
            row=dict(zip(KEYS,args));row.update(views,metrics=metrics)
            with Path(output).open('a') as f:f.write(json.dumps(row)+'\n')

BAD_WIDTHS=[0.,-1.,True,False,float('nan'),float('inf'),-float('inf'),1j,'1e-18',None,[1e-18],np.array([1e-18]),np.array(True),np.array('1e-18'),np.longdouble('1e4000'),np.longdouble('1e-4000')]
@pytest.mark.parametrize('bad',BAD_WIDTHS)
@pytest.mark.parametrize('enable',[True,False])
def test_rejected_width_does_not_change_existing_control(bad,enable):
    sim,_=configured();reference,_=configured();before=deepcopy(sim.get_ferroelectric_ensemble_history())
    with pytest.raises(ValueError,match='half width'):sim.set_transient_nls_event_control(enable,bad)
    assert_exact(sim.get_ferroelectric_ensemble_history(),before);assert_exact(sim.solve_transient(),reference.solve_transient())

@pytest.mark.parametrize('bad',[0,1,1.,None,'yes',np.array(True),[],np.array([True])])
def test_boolean_enable_contract(bad):
    sim,_=configured()
    with pytest.raises(ValueError,match='boolean'):sim.set_transient_nls_event_control(bad)

def test_default_off_toggle_numpy_scalars_and_owned_high_level_configuration():
    never,_=configured(enable=None);disabled,_=configured(enable=np.bool_(False));toggled,_=configured();toggled.set_transient_nls_event_control(np.bool_(False),np.array(2.**-60))
    expected=never.solve_transient();assert_exact(disabled.solve_transient(),expected);assert_exact(toggled.solve_transient(),expected)
    mesh=StructuredGrid(((0.,8*B),(0.,11*B),(0.,B)),3,3,1);high=Simulator(mesh);high._sim.set_dirichlet_potential({0:0.});high.set_transient_nls_event_control(np.bool_(True),np.float64(WIDTHS[0]));before=high.configuration_snapshot()
    with pytest.raises(ValueError):high.set_transient_nls_event_control(False,0.)
    assert_exact(high.configuration_snapshot(),before)
    cloned=clone_on_mesh(high,mesh,include_initial_guess=False);assert_exact(cloned.configuration_snapshot(),before)
    for backend in (high,cloned):
        with pytest.raises(ValueError,match='NLS event'):backend._sim.solve_transient()

GUARDS=('depol','partial','no_wave','nls_error','coupled','substep','model','contact','freeze_n','freeze_p','wide','resolution')
def invalid_scope(sim,kind,on):
    if kind=='depol':sim.set_ferroelectric_depol(25. if on else 0.)
    elif kind=='partial':
        mask=np.ones(9,dtype=np.int8);mask[4]=0 if on else 1;sim.set_ferroelectric_params(mask,1e8,1e12)
    elif kind=='no_wave':
        if on:sim.clear_transient_voltage_waveforms()
        else:
            times=np.array(sorted(set([i*T/4 for i in range(17)]+[2.875*T])));sim.set_transient_voltage_waveforms(times,{i:np.array([voltage(t,0) for t in times]) for i in (2,5,8)})
    elif kind=='nls_error':sim.set_transient_nls_error_control(on)
    elif kind=='coupled':sim.set_transient_lk_coupled(on)
    elif kind=='substep':sim.set_transient_lk_substepping(on)
    elif kind=='model':sim.set_ferroelectric_model(1 if on else 2)
    elif kind=='contact':sim.set_dirichlet_potential({4:0.} if on else {4:0.})
    elif kind=='freeze_n':sim.set_newton_freeze_n(on)
    elif kind=='freeze_p':sim.set_newton_freeze_p(on)
    else:sim.set_transient_nls_event_control(True,(2*T if kind=='wide' else 1e-60) if on else WIDTHS[0])

@pytest.mark.parametrize('kind',GUARDS)
def test_scope_errors_clear_trace_and_preserve_memory(kind):
    sim,_=configured();reference,_=configured();assert all(s['valid'] for s in sim.solve_transient());reference.solve_transient()
    owned=sim.get_transient_attempt_history();saved=deepcopy(owned)
    for backend in (sim,reference):invalid_scope(backend,kind,True)
    before=deepcopy(sim.get_ferroelectric_ensemble_history())
    with pytest.raises(ValueError):sim.solve_transient()
    assert sim.get_transient_attempt_history()==[];assert_exact(sim.get_ferroelectric_ensemble_history(),before);assert_exact(owned,saved)
    if kind=='contact':
        # Boundary setters merge; the unsupported contact cannot be removed.
        for backend in (sim,reference):backend.set_transient_nls_event_control(False)
    else:
        for backend in (sim,reference):invalid_scope(backend,kind,False)
    assert_exact(sim.solve_transient(),reference.solve_transient())

def test_public_transaction_and_solver_failure_restore_state():
    sim,_=configured(protocol=1);before=deepcopy(sim.get_ferroelectric_ensemble_history());sim.begin_reliability_transaction();inside=sim.solve_transient();sim.rollback_reliability_transaction();assert_exact(sim.get_ferroelectric_ensemble_history(),before)
    reference,_=configured(protocol=1);assert_exact(sim.solve_transient(),reference.solve_transient());assert all(s['valid'] for s in inside)
    failed,_=configured();memory=deepcopy(failed.get_ferroelectric_ensemble_history());failed.set_gummel_max_iter(1);history=failed.solve_transient()
    assert history[0]['initial_state'] and history[0]['valid'] and not history[-1]['valid'] and history[-1]['dt_s']==0.
    # A failed first attempt retains the accepted initial polarization. Before
    # the first solve, that same zero state has an unallocated memory vector.
    memory['polarization']=history[0]['P'].reshape(-1,3)
    assert_exact(failed.get_ferroelectric_ensemble_history(),memory)
    failed.set_gummel_max_iter(100);fresh,_=configured();assert_exact(failed.solve_transient(),fresh.solve_transient())
