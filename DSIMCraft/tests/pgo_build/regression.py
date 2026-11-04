"""Exercise the real GCC workflow with generated four-state RTL and input files."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
repo=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('dsim',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--cxx',default='g++');args=parser.parse_args()
compiler=args.dsim.resolve();result_dir=args.output.resolve();result_dir.mkdir(parents=True,exist_ok=True)
out=Path(tempfile.mkdtemp(prefix='run-',dir=result_dir))
fixture=out/'training inputs';fixture.mkdir();shutil.copy2(repo/'tests/pgo_build/input.mem',fixture/'input.mem')
report={'status':'RUNNING','execution_directory':str(out),'checks':{}}
def run(command,label,success=True):
    p=subprocess.run(list(map(str,command)),cwd=out,capture_output=True,text=True,timeout=600)
    (out/(label+'.stdout')).write_text(p.stdout);(out/(label+'.stderr')).write_text(p.stderr)
    assert (p.returncode==0)==success,(label,p.returncode,p.stdout,p.stderr[-3000:])
    return p
try:
    cpp=out/'generated model.cpp'
    run([compiler,repo/'tests/pgo_build/loops.sv','--emit-only','--emit-cpp',cpp],'lower')
    cpp.write_text('static_assert(DSIM_PGO_LITERAL==17,"literal compiler argument");\n'+cpp.read_text())
    baseline=out/'reference'
    run([args.cxx,'-std=c++17','-O2','-pthread','-DDSIM_PGO_LITERAL=17',cpp,'-o',baseline],'reference-compile')
    p=subprocess.run([baseline,'--max-events','100000000'],cwd=fixture,capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stderr;expected=p.stdout;(out/'reference.stdout').write_text(expected)
    assert len([x for x in expected.splitlines() if x.startswith('TRACE ')])==9
    work=out/'profile build'
    command=[sys.executable,repo/'scripts/build_pgo.py',cpp,'--work',work,'--run-dir',fixture,'--cxx',args.cxx,'--cxx-flag=-DDSIM_PGO_LITERAL=17','--train-arg=--max-events','--train-arg=100000000','--verify']
    run(command,'pipeline')
    data=json.loads((work/'pgo.json').read_text());assert data['status']=='PASS' and data['verify']
    assert data['input_sha256']==hashlib.sha256(cpp.read_bytes()).hexdigest()
    assert (work/'training.stdout').read_text()==(work/'verify.stdout').read_text()==expected
    for name,digest in data['profiles'].items():assert hashlib.sha256((work/name).read_bytes()).hexdigest()==digest
    assert '-DDSIM_PGO_LITERAL=17' in data['commands']['compile-optimized']
    assert '-Werror=missing-profile' in data['commands']['compile-optimized'] and '-Werror=coverage-mismatch' in data['commands']['compile-optimized']
    assert hashlib.sha256((work/'simv').read_bytes()).hexdigest()==data['binary_sha256']
    report['checks']['generated_model_training_and_verification']='PASS'
    before=(work/'pgo.json').read_bytes();binary=(work/'simv').read_bytes()
    run(command,'existing-work',False)
    assert (work/'pgo.json').read_bytes()==before and (work/'simv').read_bytes()==binary
    report['checks']['existing_work_preserved']='PASS'
    missing=out/'missing-argument-build'
    bad=[sys.executable,repo/'scripts/build_pgo.py',cpp,'--work',missing,'--cxx',args.cxx]
    run(bad,'compile-failure',False)
    failure=json.loads((missing/'pgo.json').read_text());assert failure['status']=='FAIL' and not (missing/'simv').exists()
    report['checks']['compile_failure_recorded']='PASS'
    report['status']='PASS'
finally:(result_dir/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
