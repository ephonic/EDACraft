"""Known equations at seven amplitudes; no dimensionful absolute residual floor."""
from pathlib import Path
import json,shutil,subprocess
import pytest
AMPLITUDES=['1e-3000','1e-120','1e-60','1','1e60','1e120','1e3000']
@pytest.fixture(scope='module')
def probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('GMRES source probe requires GCC/libquadmath')
    root=Path(__file__).resolve().parents[1];out=tmp_path_factory.mktemp('gmres_scale')/'probe'
    sources=['linear_solver.cpp','sparse_matrix.cpp','ilu_preconditioner.cpp','ic_preconditioner.cpp']
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals','-I'+str(root/'src'),str(root/'tests/cpp/gmres_scale_probe.cpp'),*[str(root/'src'/n) for n in sources],'-lquadmath','-o',str(out)],check=True,capture_output=True,text=True)
    return out
@pytest.mark.parametrize('amplitude',AMPLITUDES)
@pytest.mark.parametrize('prec',['diagonal','ilu'])
@pytest.mark.parametrize('case',['happy','restart','homogeneous','warm'])
def test_solution_and_original_equation_across_amplitudes(probe,amplitude,prec,case):
    r=subprocess.run([str(probe),case,amplitude,prec],check=True,capture_output=True,text=True,timeout=20)
    d=json.loads(r.stdout)
    assert d['mantissa_bits']==113 and d['finite'],d
    assert d['scaled_error']<1e-24 and d['scaled_residual']<1e-24,d
    assert 0<=d['steps']<=d['budget'],d
    if case=='warm':assert d['steps']==0,d
    else:assert d['steps']>0,d
