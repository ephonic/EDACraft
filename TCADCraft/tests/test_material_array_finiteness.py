"""Reject nonfinite material/seed arrays without altering persistent inputs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from test_field_input_contract import ROUTES, fixture, observe
from test_transient_selfconsistent import EPS, QE, VT, bernoulli, central_cell
from test_zero_auger_transient import configured, digest, snapshot


FIELDS=[('permittivity',0),('doping',0),('mobility',0),('mobility',1),
        ('initial_guess',0),('initial_guess',1),('initial_guess',2)]
BAD={'nan':np.nan,'inf':np.inf,'ninf':-np.inf}


def reference(key,value):
    h=digest(value)
    print(json.dumps(dict(test='material_finite_reference',key=key,sha256=h)))
    oracle=os.environ.get('TCAD_MATERIAL_FINITE_ORACLE')
    if oracle:assert json.loads(Path(oracle).read_text(encoding='utf8'))[key]==h


def arrays(name):
    if name=='permittivity':return [np.full(3,EPS)]
    if name=='doping':return [np.array([0.,.15e16,0.])]
    if name=='mobility':return [np.full(3,.1),np.full(3,.05)]
    return [np.zeros(3),1e16*np.array([1.,1.6,1.]),1e16*np.array([1.,1.1,1.])]


def retry(sim):
    sim.set_permittivity(np.full(3,1.2*EPS))
    sim.set_doping(np.array([0.,-.3e16,0.]))
    sim.set_mobility(np.full(3,.13),np.full(3,.07))
    sim.set_initial_guess(np.array([0.,-.003,0.]),1e16*np.array([1.,1.4,1.]),1e16*np.array([1.,1.2,1.]))


def reference_step(nn,pp,dt,x,eps,doping,mu_n,mu_p):
    left,right=np.diff(x);rate=(1/left+1/right)/((left+right)/2)
    kappa=QE*1e16/(eps*rate)
    if not dt:return kappa*(pp-nn+doping),nn,pp
    an,ap=dt*mu_n*VT*rate,dt*mu_p*VT*rate
    def carriers(phi):
        u=phi/VT
        return ((nn+an*bernoulli(-u))/(1+an*bernoulli(u)),
                (pp+ap*bernoulli(u))/(1+ap*bernoulli(-u)))
    def residual(phi):
        n,p=carriers(phi)
        return phi-kappa*(p-n+doping)
    lo,hi=-10*VT,10*VT
    assert residual(lo)<0<residual(hi)
    for _ in range(100):
        mid=(lo+hi)/2
        if residual(mid)<0:lo=mid
        else:hi=mid
    phi=(lo+hi)/2
    return phi,*carriers(phi)


@pytest.mark.parametrize('name',['permittivity','doping','mobility','initial_guess'])
@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('log_space',[False,True])
def test_valid_material_and_signed_seed_matches_independent_poisson_sg_be(name,axis,log_space):
    sim,x,nn,pp=central_cell(1e16,log_space,axis,True)
    sim.set_quantum_enabled(False);sim.set_nonlinear_history_enabled(True)
    eps,doping,mu_n,mu_p=EPS,.15,.1,.05
    if name=='permittivity':
        eps*=1.4;sim.set_permittivity(np.full(3,eps))
    elif name=='doping':
        doping=-.3;sim.set_doping(np.array([0.,doping*1e16,0.]))
    elif name=='mobility':
        mu_n,mu_p=.13,.07;sim.set_mobility(np.full(3,mu_n),np.full(3,mu_p))
    else:
        nn,pp=1.4,1.2
        sim.set_initial_guess(np.array([.001,-.003,.002]),1e16*np.array([1.,nn,1.]),1e16*np.array([1.,pp,1.]))
    result=snapshot(sim);assert len(result[0])==4
    phi_error=carrier_error=0.
    for state in result[0]:
        assert state['valid']
        phi,nn,pp=reference_step(nn,pp,state['dt_s'],x,eps,doping,mu_n,mu_p)
        np.testing.assert_allclose(state['phi'],[0.,phi,0.],rtol=2e-8,atol=1e-12)
        np.testing.assert_allclose(state['n']/1e16,[1.,nn,1.],rtol=2e-8)
        np.testing.assert_allclose(state['p']/1e16,[1.,pp,1.],rtol=2e-8)
        phi_error=max(phi_error,abs(float(state['phi'][1])-phi))
        carrier_error=max(carrier_error,abs(float(state['n'][1])/1e16-nn),abs(float(state['p'][1])/1e16-pp))
    key=f'physical/{name}/{axis}/{log_space}';reference(key,result)
    print(json.dumps(dict(test='material_finite_physics',key=key,max_phi_error_V=phi_error,max_scaled_carrier_error=carrier_error)))


@pytest.mark.parametrize('name,field',FIELDS)
def test_finite_signed_zero_and_extreme_values_accept_then_restore(name,field):
    actual,expected=[configured('classical',0,True) for _ in range(2)]
    maximum=float(np.finfo(float).max);minimum=float(np.nextafter(0.,1.))
    for value in [-maximum,maximum,-minimum,minimum,-0.,0.]:
        values=arrays(name);values[field]=np.full(3,value)
        getattr(actual,'set_'+name)(*values)
        # Setter compatibility only: never solve with extreme or unphysical
        # finite material arrays. Restore the full normal configuration.
        for setting in ['permittivity','doping','mobility','initial_guess']:
            getattr(actual,'set_'+setting)(*arrays(setting))
    a,b=snapshot(actual),snapshot(expected)
    assert all(s['valid'] for s in a[0]) and digest(a)==digest(b)
    reference(f'finite/{name}/{field}',a)


@pytest.mark.parametrize('route',ROUTES)
def test_cleared_initial_guess_fixture_and_valid_retry_are_observable(route):
    a,b=fixture(route),fixture(route)
    a.clear_initial_guess();b.clear_initial_guess()
    before,control=observe(a),observe(b);assert digest(before)==digest(control)
    retry(a);retry(b)
    after,control=observe(a),observe(b)
    assert digest(after)==digest(control) and digest(after)!=digest(before)
    reference(f'cleared/{route}',[before,after])


def child(route,name,field,bad,position,cleared):
    actual,expected=fixture(route),fixture(route)
    if cleared:
        actual.clear_initial_guess();expected.clear_initial_guess()
    values=arrays(name)
    # Earlier valid fields are also changed, exposing partial assignment
    # when an invalid value occurs in a later field or array element.
    if name=='permittivity':values=[np.full(3,1.4*EPS)]
    elif name=='doping':values=[np.array([0.,-.3e16,0.])]
    elif name=='mobility':values=[np.full(3,.13),np.full(3,.07)]
    else:values=[np.array([0.,-.003,0.]),1e16*np.array([1.,1.4,1.]),1e16*np.array([1.,1.2,1.])]
    values[field][position]=BAD[bad]
    message={'permittivity':'permittivity values must be finite','doping':'doping values must be finite',
             'mobility':'mobility values must be finite','initial_guess':'initial guess values must be finite'}[name]
    with pytest.raises(ValueError,match='^'+message+'$'):
        getattr(actual,'set_'+name)(*values)
    before,control=observe(actual),observe(expected)
    assert digest(before)==digest(control)
    retry(actual);retry(expected)
    after,control=observe(actual),observe(expected)
    assert digest(after)==digest(control) and digest(after)!=digest(before)
    return dict(route=route,name=name,field=field,bad=bad,position=position,cleared=cleared,requests=1,sha256=digest([before,after]))


CASES=[(name,field,bad,pos,False) for name,field in FIELDS for bad in BAD for pos in range(3)]
CASES += [('initial_guess',field,bad,2,True) for field in range(3) for bad in BAD]


@pytest.mark.parametrize('route',ROUTES)
@pytest.mark.parametrize('name,field,bad,position,cleared',CASES)
def test_invalid_material_or_seed_preserves_state_and_allows_retry(route,name,field,bad,position,cleared):
    args=(route,name,field,bad,position,cleared)
    code=("import json,resource;resource.setrlimit(resource.RLIMIT_CORE,(0,0))\n"
          "from test_material_array_finiteness import child\n"
          f"print(json.dumps(dict(test='material_finite_atomic',**child(*{args!r}))))\n")
    env=dict(os.environ);env['PYTHONPATH']=str(Path(__file__).parent)+os.pathsep+env.get('PYTHONPATH','')
    r=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,encoding='utf8',timeout=60)
    print(json.dumps(dict(test='material_finite_child_exit',route=route,name=name,field=field,bad=bad,position=position,cleared=cleared,returncode=r.returncode)))
    assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
    rows=[line for line in r.stdout.splitlines() if line.startswith('{"test": "material_finite_atomic"')]
    assert len(rows)==1
    print(rows[0])
