"""Manufactured divergence-free fields and implicit derivatives at natural faces."""
from pathlib import Path
import shutil
import subprocess
import numpy as np
import pytest


@pytest.fixture(scope='module')
def probes(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:
        pytest.skip('quad C++ probes require GCC')
    root=Path(__file__).resolve().parents[1]
    result={}
    for name in ('lk_natural_boundary','lk_material_compact'):
        exe=tmp_path_factory.mktemp(name)/'probe'
        subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals',
            '-I'+str(root/'src'),str(root/f'tests/cpp/{name}_probe.cpp'),
            '-lquadmath','-o',str(exe)],check=True,capture_output=True,text=True)
        result[name]=exe
    return result


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('side',[0,1])
@pytest.mark.parametrize('cells',[2,3,7,11])
def test_manufactured_nonzero_tangential_divergence(probes,axis,side,cells):
    text=subprocess.check_output([str(probes['lk_natural_boundary']),
        str(axis),str(side),str(cells)],text=True)
    bits,error,legacy=map(float,text.split())
    assert bits==113
    assert error<1e-30
    # The missing exterior D half produces a first-order bias h/(4 eps/2).
    assert legacy==pytest.approx(1/(4*cells),rel=1e-13)


@pytest.mark.parametrize('shape',[(7,4,1),(7,1,4),(1,7,4),(4,3,2)])
@pytest.mark.parametrize('faces',[1,2,4,8,16,32,21,42,63])
@pytest.mark.parametrize('partial',[0,1])
def test_natural_face_compact_jacobian(probes,shape,faces,partial):
    text=subprocess.check_output([str(probes['lk_material_compact']),
        *map(str,shape),'2',str(partial),str(faces)],text=True)
    bits,n,packed,dense=map(int,text.split())
    assert bits==113 and n==shape[0]*shape[1]*shape[2]
    assert packed==n*sum(s for s in shape if s>1)
    assert dense==3*n*n


@pytest.mark.parametrize('faces',[None,True,[],b'yY','yy','a','y Y'])
def test_invalid_face_declarations(faces):
    from tcad.core import PyDeviceSimulator
    sim=PyDeviceSimulator(4,3,1,1.,1.,1.)
    with pytest.raises(ValueError):sim.set_transient_lk_zero_d_faces(faces)


@pytest.mark.parametrize('shape,faces',[((4,1,1),'x'),((4,3,1),'z'),((1,1,1),'X')])
def test_inactive_or_one_dimensional_face_rejected(shape,faces):
    from tcad.core import PyDeviceSimulator
    sim=PyDeviceSimulator(*shape,1.,1.,1.)
    with pytest.raises(ValueError,match='active face axis'):
        sim.set_transient_lk_zero_d_faces(faces)


@pytest.mark.parametrize('shape',[(4,3,1),(4,1,3),(1,4,3),(3,3,3)])
@pytest.mark.parametrize('partial',[False,True])
@pytest.mark.parametrize('charged',[False,True])
@pytest.mark.parametrize('policy',['lower','both'])
def test_full_poisson_lk_block_and_physical_volumes(shape,partial,charged,policy):
    from test_lk_material_multidimensional import device,independent_step
    from tcad.postprocess.lk_energy import audit_transient_lk_energy
    drive=next(a for a,n in enumerate(shape) if n>1)
    faces=''.join('xXyYzZ'[2*a:2*a+(2 if policy=='both' else 1)]
        for a,n in enumerate(shape) if n>1 and a!=drive)
    sim,spec=device(shape,partial,2,charged,natural_faces=faces)
    states=sim.solve_transient();old=np.zeros((spec['count'],3));phi=states[0]['phi']
    for state in states[1:]:
        assert state['valid']
        phi,old=independent_step(spec,old,phi,state['dt_s'])
        np.testing.assert_allclose(state['phi'],phi,rtol=1e-8,atol=1e-11)
        np.testing.assert_allclose(state['P'].reshape(-1,3),old,rtol=1e-8,atol=1e-12)
        field,div,ports=spec['fields'](phi,old)
        np.testing.assert_allclose(np.column_stack([state['Ex'],state['Ey'],state['Ez']]),field,rtol=2e-8,atol=2e-4)
        np.testing.assert_allclose(state['electrode_charges_C'],ports,rtol=1e-8,atol=1e-28)
        assert max(abs((div-1.602176634e-19*spec['doping'])[~spec['contacts']]))<1e-7
    spacing=[1e-8,1.3e-8,1.7e-8];widths=[]
    for a,(n,h) in enumerate(zip(shape,spacing)):
        if n==1:widths.append(np.array([h]));continue
        edge=np.diff(np.arange(n,dtype=float)**1.3*h)
        w=(np.r_[0.,edge]+np.r_[edge,0.])/2
        if 'xXyYzZ'[2*a] in faces:w[0]+=edge[0]/2
        if 'xXyYzZ'[2*a+1] in faces:w[-1]+=edge[-1]/2
        widths.append(w)
    expected=np.array([widths[0][i]*widths[1][j]*widths[2][k]
        for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    expected[~spec['mask']]=0.
    for state in states:np.testing.assert_allclose(state['lk_node_volumes_m3'],expected,rtol=2e-14,atol=0.)
    assert audit_transient_lk_energy(states)['valid']


def test_face_contact_conflict_is_rejected_and_can_be_reset():
    from test_lk_material_multidimensional import device
    sim,_=device((4,3,1),False,0,natural_faces='x')
    with pytest.raises(ValueError,match='face interior contains a potential contact'):
        sim.solve_transient()
    sim.set_transient_lk_zero_d_faces('')
    assert all(s['valid'] for s in sim.solve_transient())


def test_steady_solve_cannot_silently_ignore_declaration():
    from tcad.core import PyDeviceSimulator
    sim=PyDeviceSimulator(4,3,1,1.,1.,1.)
    sim.set_transient_lk_zero_d_faces('yY')
    with pytest.raises(ValueError,match='only by transient'):sim.solve()


def test_requires_material_field_coupling():
    from test_lk_material_multidimensional import device
    sim,_=device((4,3,1),False,0,natural_faces='yY')
    sim.set_transient_lk_material_field(False)
    with pytest.raises(ValueError,match='multidimensional coupled material-field'):
        sim.solve_transient()


@pytest.mark.parametrize('native',[False,True])
def test_declaration_survives_configuration_inheritance(monkeypatch,native):
    import tcad.simulator as module
    from test_configuration_inheritance import setup,NativeCapture
    backend=module.PyDeviceSimulator
    monkeypatch.setattr(module,'PyDeviceSimulator',lambda *a:NativeCapture(backend(*a)))
    _,refiner,sim=setup(layout=(0,1),dielectric=True)
    target=sim._sim if native else sim
    target.set_transient_lk_zero_d_faces('yY')
    before=repr(sim.configuration_snapshot())
    mesh=refiner.generate_feature_refined_mesh(1)
    clone=sim.clone_on_mesh(mesh)
    calls=clone._sim.backend.calls
    assert any(name=='set_transient_lk_zero_d_faces' and args==('yY',) for name,args,kwargs in calls)
    assert repr(sim.configuration_snapshot())==before
    with pytest.raises(ValueError):target.set_transient_lk_zero_d_faces('bad')
    assert repr(sim.configuration_snapshot())==before
