"""Known-equation regressions for portable quad GMRES termination."""
from pathlib import Path
import json,shutil,subprocess
import pytest
@pytest.fixture(scope='module')
def probe(tmp_path_factory):
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('GMRES probe requires GCC/libquadmath')
    root=Path(__file__).resolve().parents[1];out=tmp_path_factory.mktemp('gmres_probe')/'probe'
    sources=['linear_solver.cpp','sparse_matrix.cpp','ilu_preconditioner.cpp','ic_preconditioner.cpp']
    subprocess.run([compiler,'-std=c++17','-O2','-fext-numeric-literals','-I'+str(root/'src'),str(root/'tests/cpp/gmres_contract_probe.cpp'),*[str(root/'src'/n) for n in sources],'-lquadmath','-o',str(out)],check=True,capture_output=True,text=True)
    return out
def run(probe,case,budget):
    r=subprocess.run([str(probe),case,str(budget)],check=True,capture_output=True,text=True,timeout=20)
    d=json.loads(r.stdout);assert d['mantissa_bits']==113 and d['finite'];return d
@pytest.mark.parametrize('budget',[0,1,2,3,7,30,31])
def test_exact_arnoldi_budget(probe,budget):
    d=run(probe,'restart',budget);assert 0<=d['steps']<=budget
    if budget==0:assert d['change']==0
def test_happy_breakdown_applies_all_givens_rotations(probe):
    d=run(probe,'happy',2);assert d['steps']==2 and d['error']<1e-28 and d['residual']<1e-28
def test_exact_initial_guess_needs_no_arnoldi_step(probe):
    d=run(probe,'warm',0);assert d['steps']==0 and d['change']==0 and d['residual']==0
def test_restart_accumulates_accurate_solution(probe):
    d=run(probe,'restart',120);assert d['steps']<=120 and d['error']<1e-24 and d['residual']<1e-24
def test_inconsistent_breakdown_does_not_divide_by_zero(probe):
    d=run(probe,'singular',2);assert 0<d['steps']<=2 and d['change']==0 and d['residual']==1
