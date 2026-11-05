"""Known-solution quad systems exercise pivot fill, units and graph ordering."""
from pathlib import Path
import json,os,shutil,subprocess
import pytest

@pytest.fixture(scope='module')
def band_probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('quad direct solver probe needs GCC/libquadmath')
    root=Path(__file__).resolve().parents[1];out=tmp_path_factory.mktemp('quad_band')/'probe'
    sources=['linear_solver.cpp','sparse_matrix.cpp','ilu_preconditioner.cpp','ic_preconditioner.cpp']
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals','-I'+str(root/'src'),
        str(root/'tests/cpp/portable_band_probe.cpp'),*[str(root/'src'/n) for n in sources],
        '-lquadmath','-o',str(out)],check=True,capture_output=True,text=True)
    return out

@pytest.mark.parametrize('case',['ordinary','pivot','asymmetric','species','disconnected','dense'])
def test_quad_direct_known_solution_and_original_equations(band_probe,case):
    r=subprocess.run([str(band_probe),case],check=True,capture_output=True,text=True,
        env=dict(os.environ,TCAD_LIN_DEBUG='1'),timeout=30)
    d=json.loads(r.stdout)
    assert d['mantissa_bits']==113
    assert d['solution_relative']<1e-26
    assert d['backward_relative']<1e-28
    if case in ('pivot','asymmetric'):assert '[quad pivot band ' in r.stderr
    if case in ('species','disconnected'):assert '[reordered direct ' in r.stderr
