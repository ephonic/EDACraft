"""Backend errors must propagate before state or replay configuration changes."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator,SolverType
from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator

def device():
    L=40e-9;d=Device.pnjunction(L=L,W=L,H=L,x_junction=L/2,Na=1e22,Nd=1e22)
    s=Simulator(structured_mesh_from_device(d,nx=11,ny=1,nz=1));s.set_material_from_mesh()
    s.set_contact('p_contact',voltage=.01);s.set_contact('n_contact',voltage=0.)
    return s

@pytest.mark.parametrize('kind',['poisson','continuity'])
@pytest.mark.parametrize('bad',[-1,9,2147483647])
def test_native_invalid_backend_does_not_poison_next_solve(kind,bad):
    s=device()
    with pytest.raises(ValueError,match='invalid linear solver type'):
        getattr(s._sim,'set_'+kind+'_solver_type')(bad)
    r=s.run(max_iter=100,tol=1e-8);expected=device().run(max_iter=100,tol=1e-8)
    assert r['converged'] and expected['converged']
    for k in ('phi','n','p'):np.testing.assert_array_equal(r[k],expected[k])

@pytest.mark.parametrize('slot',[0,1])
@pytest.mark.parametrize('bad',[-1,9,2147483647])
def test_invalid_public_pair_is_transactional(slot,bad):
    s=device();before=repr(s.configuration_snapshot())
    # A changed valid first selection must also roll back when the second fails.
    pair=[SolverType.BICGSTAB,SolverType.BICGSTAB];pair[slot]=bad
    with pytest.raises(ValueError,match='invalid linear solver type'):s.set_solver_type(*pair)
    assert repr(s.configuration_snapshot())==before
    r=s.run(max_iter=100,tol=1e-8);expected=device().run(max_iter=100,tol=1e-8)
    assert r['converged'] and expected['converged']
    for k in ('phi','n','p'):np.testing.assert_array_equal(r[k],expected[k])

@pytest.mark.parametrize('slot',[0,1])
def test_uncompiled_petsc_is_explicit_and_transactional(slot):
    s=device();before=repr(s.configuration_snapshot())
    try:s._sim.validate_linear_solver_type(int(SolverType.PETSC))
    except RuntimeError as e:
        assert 'PETSc' in str(e) and 'unavailable' in str(e)
        pair=[SolverType.BICGSTAB,SolverType.BICGSTAB];pair[slot]=SolverType.PETSC
        with pytest.raises(RuntimeError,match='PETSc.*unavailable'):s.set_solver_type(*pair)
        with pytest.raises(RuntimeError,match='PETSc.*unavailable'):
            getattr(s._sim,('set_poisson_solver_type','set_continuity_solver_type')[slot])(int(SolverType.PETSC))
        assert repr(s.configuration_snapshot())==before
        r=s.run(max_iter=100,tol=1e-8);assert r['converged']
    else:
        # PETSc-enabled builds retain the native backend, rather than disabling
        # the public ABI entry globally to make the portable tests pass.
        pair=[SolverType.DENSE_DIRECT,SolverType.DENSE_DIRECT];pair[slot]=SolverType.PETSC
        s.set_solver_type(*pair);assert s.run(max_iter=100,tol=1e-8)['converged']
