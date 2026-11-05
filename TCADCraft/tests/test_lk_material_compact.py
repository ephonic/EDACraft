"""Exact compact derivative support, independent differences and storage size."""
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.fixture(scope='module')
def probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('quad C++ derivative probe requires GCC')
    project=Path(__file__).resolve().parents[1]
    exe=tmp_path_factory.mktemp('compact_lk')/'probe'
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals',
        '-I'+str(project/'src'),str(project/'tests/cpp/lk_material_compact_probe.cpp'),
        '-lquadmath','-o',str(exe)],check=True,capture_output=True,text=True)
    return exe


@pytest.mark.parametrize('shape',[(7,1,1),(1,7,1),(1,1,7),(7,4,1),(7,1,4),(1,7,4),(4,3,2),(1,1,1)])
@pytest.mark.parametrize('polar',[0,1,2])
@pytest.mark.parametrize('partial',[0,1])
def test_line_storage_preserves_quad_derivative(probe,shape,polar,partial):
    text=subprocess.check_output([str(probe),*map(str,shape),str(polar),str(partial)],text=True)
    bits,n,packed,dense=map(int,text.split())
    assert bits==113 and n==shape[0]*shape[1]*shape[2]
    assert packed==n*sum(s for s in shape if s>1)
    assert dense==3*n*n
    if sum(s>1 for s in shape)>1:assert packed<dense
