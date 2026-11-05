"""Steady mixed-material FV equations, independently assembled in physical volumes."""
import numpy as np
import pytest
from scipy.optimize import root
from test_transient_mixed_volumes import CASES, SCALE, VT, EPS, QE, mixed_device, face_rates


def reference(spec):
    size=len(spec['n']); i,j=spec['i'],spec['j']; volume=spec['volume']
    contacts=spec['contacts']; fixed=contacts | spec['blocked']
    lap=np.zeros((size,size)); weight=EPS*spec['area']/spec['distance']
    for row,col,sign in [(i,i,1),(j,j,1),(i,j,-1),(j,i,-1)]:
        np.add.at(lap,(row,col),sign*weight)
    lap/=QE*SCALE*volume[:,None]
    def residual(x):
        phi,n,p=x.reshape(3,size)
        fp=lap@phi-(p-n) if spec['coupled'] else phi/VT
        fp[contacts]=phi[contacts]/VT
        rates=face_rates(spec,phi,n,p); blocks=[]
        source=spec['generation']-(n*p-1)/(spec['tau']*(n+p+2))
        for density,rate,key in [(n,rates[0],'n'),(p,rates[1],'p')]:
            f=-source.copy()
            np.add.at(f,i,rate/volume[i]);np.add.at(f,j,-rate/volume[j])
            f*=1e-10
            f[fixed]=density[fixed]-spec[key][fixed]
            blocks.append(f)
        return np.r_[fp,*blocks]
    solved=root(residual,np.r_[np.zeros(size),spec['n'],spec['p']],tol=1e-10)
    assert max(abs(residual(solved.x)))<1e-9,solved.message
    return solved.x.reshape(3,size)


@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('stretched',[False,True])
@pytest.mark.parametrize('coupled',[False,True])
@pytest.mark.parametrize('newton',[False,True])
def test_steady_mixed_geometry_matches_independent_fv(case,stretched,coupled,newton):
    sim,spec=mixed_device(case,stretched,False,coupled)
    # Gummel always evolves Poisson. Compare both solvers on that same system;
    # the coupled parameter selects generation/SRH rather than freezing phi.
    sim.set_newton_freeze_phi(False)
    spec['coupled']=True
    sim.set_use_newton(newton)
    sim.set_newton_primary(newton)
    sim.set_gummel_max_iter(300)
    actual=sim.solve()
    assert actual['converged']
    expected=reference(spec)
    np.testing.assert_allclose(actual['phi'],expected[0],rtol=2e-6,atol=1e-10)
    for key,row in [('n',1),('p',2)]:
        np.testing.assert_allclose(actual[key]/SCALE,expected[row],rtol=2e-6,atol=1e-12)
    # Independently integrate both contact currents. Each internal SG face
    # must occur with equal magnitude and opposite orientation in adjacent rows.
    rn,rp=face_rates(spec,actual['phi'],actual['n']/SCALE,actual['p']/SCALE)
    current=QE*SCALE*(-rn+rp);i,j=spec['i'],spec['j'];c=spec['contacts']
    left=c[i]&~c[j];right=~c[i]&c[j]
    terminals=np.array([current[left].sum(),-current[right].sum()])
    assert abs(terminals.sum())<2e-7*max(abs(terminals))+1e-28
