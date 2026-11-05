"""Independent prescribed-field/source references for the single-contact SG path."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator

VT=1.380649e-23*300/1.602176634e-19
Q=1.602176634e-19


def problem(axis,reverse=False):
    count=21;shape=[1,1,1];shape[axis]=count
    x=1e-8*np.linspace(0,1,count)**1.3
    core=PyDeviceSimulator(*shape,1e-9,1e-9,1e-9)
    getattr(core,'set_'+'xyz'[axis]+'_positions')(x)
    core.set_mobility(np.full(count,.1),np.full(count,.05))
    core.set_doping(np.zeros(count))
    core.set_effective_dos(np.full(count,1e22),np.full(count,1e22))
    core.set_bandgap(np.full(count,1.12));core.set_thermal_voltage(VT)
    core.set_recombination(np.full(count,1e100),np.full(count,1e100))
    core.set_electron_bc({count-1 if reverse else 0:1e8})
    core.set_hole_bc({count-1 if reverse else 0:1e8})
    core.set_use_newton(False);core.set_gummel_max_iter(120);core.set_tolerance(1e-10)
    return core,x


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('sign',[-1,1])
def test_thermal_population_ratio_survives_extreme_density_range(axis,reverse,sign):
    core,x=problem(axis,reverse)
    phi=sign*(x/x[-1])
    anchor=-1 if reverse else 0
    core.set_dirichlet_potential(dict(enumerate(phi)))
    core.set_initial_guess(phi.copy(),np.full(len(x),1e8),np.full(len(x),1e8))
    result=core.solve();assert result['converged']
    n=1e8*np.exp((phi-phi[anchor])/VT)
    p=1e8*np.exp(-(phi-phi[anchor])/VT)
    np.testing.assert_allclose(result['n'],n,rtol=2e-8,atol=0.)
    np.testing.assert_allclose(result['p'],p,rtol=2e-8,atol=0.)
    np.testing.assert_allclose(result['phi'],phi,rtol=0.,atol=1e-15)
    # Current cancellation is scored against each edge's own drift/diffusion
    # scale, not a global carrier maximum that hides depleted-row errors.
    for carrier,mobility,key in [(n,.1,'Jn_'),(p,.05,'Jp_')]:
        scale=Q*mobility*VT*(carrier[:-1]+carrier[1:])/np.diff(x)
        assert np.max(abs(result[key+'xyz'[axis]][:-1])/scale)<1e-8


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('reverse',[False,True])
def test_nonzero_generation_matches_existing_box_control_volumes(axis,reverse):
    core,x=problem(axis,reverse)
    count=len(x);generation=1e34
    core.set_electron_bc({count-1 if reverse else 0:1e16})
    core.set_hole_bc({count-1 if reverse else 0:1e16})
    core.set_optical_generation(np.full(count,generation))
    core.set_dirichlet_potential(dict(enumerate(np.zeros(count))))
    core.set_initial_guess(np.zeros(count),np.full(count,1e16),np.full(count,1e16))
    state=core.solve();assert state['converged']
    distance=x[-1]-x if reverse else x
    # Grid3D gives the endpoint a full edge-width box, so its reflecting
    # outer face is half an edge beyond the last node. Keep that declared
    # geometry in this reference; this patch does not change storage volumes.
    reflected_edge=x[1]-x[0] if reverse else x[-1]-x[-2]
    integral=(x[-1]+reflected_edge/2)*distance-distance**2/2
    for species,mobility in [('n',.1),('p',.05)]:
        expected=1e16+generation/(mobility*VT)*integral
        np.testing.assert_allclose(state[species],expected,rtol=2e-8,atol=0.)
    assert np.max(state['n'])>1e19 and np.max(state['p'])>1e19
