"""Fixed-charge LK checked against a full edge-D/potential/vector-P block."""
import numpy as np
import pytest
from scipy.optimize import root
from tcad.postprocess import audit_transient_lk_energy
from test_transient_displacement import film, QE


def widths(x):
    h=np.diff(x)
    return (np.r_[h,0.]+np.r_[0.,h])/2


def charged_device(axis=0, stretched=True, pattern="positive"):
    sim,x,eps,mask,area=film(axis,0,stretched,True)
    c=np.zeros(len(x))
    if pattern=="positive": c[1:-1]=np.linspace(.3,1.4,len(x)-2)*1e23
    elif pattern=="negative": c[1:-1]=-np.linspace(1.4,.3,len(x)-2)*1e23
    else:
        c[1:-1]=np.array([1.,-2.,3.,-1.,2.,-3.,1.])*1e23
        c[-2]-=np.dot(widths(x),c)/widths(x)[-2]
    sim.set_doping(c)
    sim.set_transient_lk_coupled(True);sim.set_transient_lk_material_field(True)
    return sim,x,eps,mask,area,c


def block_step(x,eps,mask,old,c,dt,voltage,axis,polar_axis=None,imprint=0.,depol=0.):
    """Independent simultaneous equations: all edge D, node phi and 3N P.

    No prefix charge elimination or scalar displacement root is used here.
    Initial P is fixed; subsequent steps solve vector LK, Gauss, edge voltage
    drops and the two contact constraints together.
    """
    n=len(x);h=np.diff(x);w=widths(x)
    if polar_axis is None: polar_axis=axis
    def equations(y):
        p=y[:3*n].reshape(n,3);d=y[3*n:4*n-1];phi=y[4*n-1:]
        mean_d=(np.r_[h*d,0.]+np.r_[0.,h*d])/(2*w)
        field=np.zeros_like(p);field[:,axis]=(mean_d-p[:,axis])/eps
        if dt is None: lk=(p-old)
        else:
            lk=(-1e8*p+1e12*p**3+.1/dt*(p-old)-field)/1e10
            lk[:,polar_axis]+=imprint/1e10
            if depol: lk[:,polar_axis]+=p[:,polar_axis]/(depol*8.854187817e-12*1e10)
            lk[mask==0]=p[mask==0]
        gauss=(np.diff(d)-QE*c[1:-1]*w[1:-1])/1e-3
        edge_drop=phi[:-1]-phi[1:]-h/2*((d-p[:-1,axis])/eps[:-1]+(d-p[1:,axis])/eps[1:])
        return np.r_[lk.ravel(),gauss,edge_drop,phi[0],phi[-1]+voltage]
    guess=np.r_[old.ravel(),np.zeros(n-1),np.linspace(0.,-voltage,n)]
    result=root(equations,guess,tol=1e-11)
    assert np.max(np.abs(equations(result.x)))<2e-12
    return result.x[:3*n].reshape(n,3),result.x[3*n:4*n-1],result.x[4*n-1:]


def check_history(sim,x,eps,mask,area,c,axis,polar_axis=None,imprint=0.,depol=0.,voltage=.01):
    states=sim.solve_transient();old=np.zeros((len(x),3));prior=None
    for s in states:
        assert s['valid'] and s['lk_material_field']
        p,d,phi=block_step(x,eps,mask,old,c,s['dt_s'] or None,voltage,axis,polar_axis,imprint,depol)
        np.testing.assert_allclose(s['P'].reshape(-1,3),p,rtol=2e-9,atol=2e-13)
        np.testing.assert_allclose(s['phi'],phi,rtol=2e-10,atol=2e-13)
        np.testing.assert_allclose(s['D_'+'xyz'[axis]][:-1],d,rtol=2e-10,atol=2e-15)
        np.testing.assert_allclose(s['electrode_charges_C'],area*np.array([d[0],-d[-1]]),rtol=2e-10,atol=2e-27)
        np.testing.assert_allclose(sum(s['electrode_charges_C']),-QE*area*np.dot(widths(x),c),rtol=1e-11,atol=1e-28)
        if prior is not None:
            current=(s['electrode_charges_C']-prior['electrode_charges_C'])/s['dt_s']
            np.testing.assert_allclose(s['electrode_total_currents_A'],current,rtol=2e-9,atol=1e-18)
            assert abs(sum(s['electrode_total_currents_A']))<1e-22
        old=p;prior=s
    if np.any(mask): assert audit_transient_lk_energy(states)['valid']
    else: assert all(not s['lk_energy_available'] for s in states)
    return states


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('pattern',['positive','negative','neutral'])
@pytest.mark.parametrize('stretched',[False,True])
def test_charged_full_block_ports_and_gauss(axis,pattern,stretched):
    sim,x,eps,mask,area,c=charged_device(axis,stretched,pattern)
    states=check_history(sim,x,eps,mask,area,c,axis)
    assert np.ptp(states[-1]['D_'+'xyz'[axis]][:-1])>1e-5


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('polar_axis',[0,1,2])
@pytest.mark.parametrize('depol',[0.,30.])
def test_charged_vector_lk_and_depolarization(axis,polar_axis,depol):
    sim,x,eps,mask,area,c=charged_device(axis)
    sim.set_ferroelectric_polar_axis(polar_axis)
    sim.set_ferroelectric_builtin_field(2e5);sim.set_ferroelectric_depol(depol)
    check_history(sim,x,eps,mask,area,c,axis,polar_axis,2e5,depol)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('sign',[-1,1])
def test_no_fe_limit_matches_analytic_quadratic_poisson(axis,sign):
    sim,x,_,mask,area,c=charged_device(axis)
    eps=np.full(len(x),20*8.854187817e-12);mask[:]=0;c[1:-1]=sign*1e23
    sim.set_permittivity(eps);sim.set_doping(c);sim.set_ferroelectric_params(mask,-1e8,1e12)
    states=check_history(sim,x,eps,mask,area,c,axis)
    expected=-.01*x/x[-1]+QE*sign*1e23*x*(x[-1]-x)/(2*eps[0])
    for s in states:np.testing.assert_allclose(s['phi'],expected,atol=1e-15,rtol=1e-12)


@pytest.mark.parametrize('endpoint',[0,-1])
def test_charged_endpoint_rejected(endpoint):
    sim,x,eps,mask,area,c=charged_device();c[endpoint]=1e23;sim.set_doping(c)
    with pytest.raises(ValueError,match='endpoint doping'):sim.solve_transient()


def test_charged_failure_rollback_and_retry():
    sim,*_=charged_device();sim.set_gummel_max_iter(0)
    states=sim.solve_transient();assert not states[-1]['valid']
    np.testing.assert_array_equal(states[-1]['P'],states[0]['P'])
    sim.set_gummel_max_iter(80);retry=sim.solve_transient()
    fresh,*_=charged_device()
    for a,b in zip(retry,fresh.solve_transient()):
        for key in ('P','phi','electrode_charges_C'):np.testing.assert_array_equal(a[key],b[key])


def test_charged_adaptive_rejections_keep_accepted_lk_history():
    sim,x,eps,mask,area,c=charged_device()
    sim.set_dirichlet_potential({0:0.,len(x)-1:-1.})
    sim.set_transient_lk_substepping(True)
    sim.set_transient_lk_error_control(True,rtol=1e-4,atol=1e-9,min_dt=1e-15,max_reject=30)
    sim.set_nonlinear_history_enabled(True)
    check_history(sim,x,eps,mask,area,c,0,voltage=1.)
    assert any(not g['accepted'] for g in sim.get_transient_attempt_history())


@pytest.fixture(scope='module')
def quad_charge_probe(tmp_path_factory):
    import shutil,subprocess
    from pathlib import Path
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('native C++ probe requires GCC')
    project=Path(__file__).resolve().parents[1]
    exe=tmp_path_factory.mktemp('fixed_charge')/'quad_probe'
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals',
        '-I'+str(project/'src'),str(project/'tests/cpp/lk_fixed_charge_probe.cpp'),
        '-lquadmath','-o',str(exe)],check=True,capture_output=True,text=True)
    return exe


@pytest.mark.parametrize('sign',[1,-1])
def test_fixed_charge_full_block_at_quad_precision(quad_charge_probe,sign):
    import subprocess
    import mpmath as mp
    lines=subprocess.check_output([str(quad_charge_probe),'positive' if sign==1 else 'negative'],text=True).splitlines()
    assert int(lines[0])==113
    with mp.workdps(90):
        v=list(map(mp.mpf,lines[1:]));x=v[:9];eps=v[9:18];old=v[18:45]
        c=v[45:54];actual=v[54:81];phi=v[81:90];samples=v[90:92]
        h=[x[i+1]-x[i] for i in range(8)]
        w=[((h[i-1] if i else 0)+(h[i] if i<8 else 0))/2 for i in range(9)]
        alpha=mp.mpf('-649519052.838329');beta=mp.mpf('331387271.85629034');rate=mp.mpf('2e9')
        def equations(*y):
            p=list(y[:7])+[mp.mpf(0)]*2;d=y[7:15];potential=y[15:]
            mean=[((h[i-1]*d[i-1] if i else 0)+(h[i]*d[i] if i<8 else 0))/(2*w[i]) for i in range(9)]
            lk=[(alpha*p[i]+beta*p[i]**3+rate*(p[i]-old[3*i])-(mean[i]-p[i])/eps[i])/mp.mpf('1e10') for i in range(7)]
            gauss=[(d[i]-d[i-1]-mp.mpf('1.602176634e-19')*c[i]*w[i])/mp.mpf('.001') for i in range(1,8)]
            drop=[potential[i]-potential[i+1]-h[i]/2*((d[i]-p[i])/eps[i]+(d[i]-p[i+1])/eps[i+1]) for i in range(8)]
            return tuple(lk+gauss+drop+[potential[0],potential[-1]+sign*mp.mpf('.25')])
        d_actual=[2*eps[i]*eps[i+1]/(eps[i]+eps[i+1])*((phi[i]-phi[i+1])/h[i]+(actual[3*i]/eps[i]+actual[3*(i+1)]/eps[i+1])/2) for i in range(8)]
        guess=tuple(actual[3*i] for i in range(7))+tuple(d_actual)+tuple(phi)
        expected=mp.findroot(equations,guess,tol=mp.mpf('1e-75'))
        assert max(abs(z) for z in equations(*expected))<mp.mpf('1e-70')
        assert max(abs(a-b) for a,b in zip(guess,expected))<mp.mpf('1e-28')
        assert abs(samples[0])<mp.mpf('1e-28')


@pytest.mark.parametrize('value',[np.nan,np.inf,-np.inf])
def test_nonfinite_fixed_charge_rejected_before_evolution(value):
    sim,x,eps,mask,area,c=charged_device();c[4]=value;sim.set_doping(c)
    with pytest.raises(ValueError,match='fixed doping must be finite'):sim.solve_transient()
    c[4]=0.;sim.set_doping(c);retry=sim.solve_transient()
    fresh,*rest=charged_device();fresh.set_doping(c)
    for a,b in zip(retry,fresh.solve_transient()):
        for key in ('P','phi'):np.testing.assert_array_equal(a[key],b[key])
