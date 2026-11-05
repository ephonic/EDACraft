"""Python solver selection must match the compiled solver's public ABI."""
from pathlib import Path
import re
import numpy as np
import pytest
from tcad.core import SolverType
from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator


def test_public_solver_names_and_values_match_cpp_abi():
    source=Path(__file__).resolve().parents[1]/'src/linear_solver.h'
    # The candidate test is retained under validation; the source header is
    # the input ABI, not an independently hand-maintained duplicate list.
    text=source.read_text()
    body=re.search(r'enum class SolverType\s*\{(.*?)\}',text,re.S).group(1)
    names=[part.strip() for part in re.sub(r'//[^\n]*','',body).split(',')]
    assert {member.name:int(member) for member in SolverType}=={name:index for index,name in enumerate(names) if name}


def test_public_petsc_selection_reaches_native_backend(monkeypatch,capfd):
    monkeypatch.setenv('TCAD_PETSC_DEBUG','1')
    def make(solver):
        length=40e-9
        device=Device.pnjunction(L=length,W=length,H=length,x_junction=length/2,Na=1e22,Nd=1e22)
        sim=Simulator(structured_mesh_from_device(device,nx=11,ny=1,nz=1))
        sim.set_material_from_mesh();sim.set_contact('p_contact',voltage=.01);sim.set_contact('n_contact',voltage=0.)
        sim.set_solver_type(solver,solver)
        return sim
    capfd.readouterr()
    try:
        actual=make(SolverType.PETSC).run(max_iter=100,tol=1e-8)
    except RuntimeError as error:
        # Portable builds must report unsupported PETSc, rather than silently
        # selecting the iterative-refinement backend as the old enum did.
        assert 'PETSc' in str(error) and ('unavailable' in str(error) or 'not available' in str(error))
        return
    captured=capfd.readouterr()
    assert '[petsc n=' in captured.err,'Public PETSC selection did not enter the native PETSc backend'
    expected=make(SolverType.DENSE_DIRECT).run(max_iter=100,tol=1e-8)
    assert actual['converged'] and expected['converged']
    np.testing.assert_allclose(actual['phi'],expected['phi'],rtol=1e-7,atol=1e-9)
    for key in ('n','p'):np.testing.assert_allclose(actual[key],expected[key],rtol=1e-5,atol=1.)
