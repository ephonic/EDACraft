#!/usr/bin/env python3
"""Run the unchanged complete UVM library through emit, native build and hello_test."""
from pathlib import Path
import argparse,hashlib,json,os,re,signal,subprocess,time
parser=argparse.ArgumentParser()
parser.add_argument('--simulator',choices=['dsim','vcs'],default='dsim')
parser.add_argument('--compiler',type=Path,required=True)
parser.add_argument('--uvm-dir',type=Path,required=True)
parser.add_argument('--test',type=Path,help='UVM test with the REAL_UVM_SMOKE marker (default: repository hello_test)')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--compile-timeout',type=int,default=1800)
parser.add_argument('--run-timeout',type=int,default=60)
parser.add_argument('--model-optimization',choices=['-O0','-O1','-O2','-O3'],help='Override native model optimization for dsim verification; recorded in results')
args=parser.parse_args()
if args.model_optimization and args.simulator!='dsim':parser.error('--model-optimization applies to dsim only')
root=Path(__file__).resolve().parents[1];compiler=args.compiler.resolve();library=args.uvm_dir.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
pkg=library/'src/uvm_pkg.sv';smoke=args.test.resolve() if args.test else root/'tests/uvm_preprocess/smoke.sv'
if not compiler.is_file() or not os.access(compiler,os.X_OK):parser.error('--compiler must be an executable file')
if not pkg.is_file():parser.error('--uvm-dir must contain src/uvm_pkg.sv')
if not smoke.is_file():parser.error('--test must be an existing SystemVerilog file')
if min(args.compile_timeout,args.run_timeout)<=0:parser.error('timeouts must be positive')
if any((out/name).exists() for name in ['native','model.cpp','results.json']):parser.error('--out must not contain previous results.json/model.cpp/native')
sources={str(p.relative_to(library)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((library/'src').rglob('*')) if p.is_file()}
(out/'uvm-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
report=dict(status='RUNNING',simulator=args.simulator,complete_uvm_source=True,uvm_source_tree_sha256=hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(),uvm_source_files=len(sources),uvm_pkg_sha256=hashlib.sha256(pkg.read_bytes()).hexdigest(),smoke_sha256=hashlib.sha256(smoke.read_bytes()).hexdigest(),stages={},model_generated=False,native_generated=False,hello_pass=False,defines=['UVM_NO_DPI'])
if args.model_optimization:report['native_optimization_override']=args.model_optimization
def save():
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(label,command,timeout):
 start=time.monotonic()
 report['stages'][label]=dict(status='RUNNING',command=list(map(str,command)));save()
 print('START',label,flush=True)
 timed_out=False
 with (out/(label+'.stdout')).open('w') as stdout,(out/(label+'.stderr')).open('w') as stderr:
  p=subprocess.Popen(['/bin/bash','-c','ulimit -s 65520; exec "$@"','dsim-uvm',*map(str,command)],cwd=out,stdout=stdout,stderr=stderr,start_new_session=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:symbolize=0'))
  try:p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 report['stages'][label].update(status='TIMEOUT' if timed_out else 'PASS' if not p.returncode else 'FAIL',exit_code=p.returncode,seconds=time.monotonic()-start)
 save();diagnostic=(out/(label+'.stderr')).read_text(errors='replace')[-1500:]
 print(label,p.returncode,diagnostic,flush=True)
 return p.returncode
try:
 command=[compiler,*(['--shared-functions'] if args.simulator=='dsim' else ['-full64','-sverilog','-top','top']),'+incdir+'+str(library/'src'),'+define+UVM_NO_DPI',pkg,smoke]
 if args.simulator=='dsim':
  command+=['--emit-cpp',out/'model.cpp']
  if args.model_optimization:command+=['--cxx-flag',args.model_optimization]
 code=run('compile',[*command,'-o',out/'native'],args.compile_timeout)
 report['model_generated']=(out/'model.cpp').exists()
 report['native_generated']=(out/'native').exists()
 if report['stages']['compile']['status']=='TIMEOUT':report['status']='COMPILE_TIMEOUT'
 elif code:report['status']='COMPILE_BLOCKED' if args.simulator=='vcs' else 'NATIVE_COMPILE_BLOCKED' if report['model_generated'] else 'FRONTEND_BLOCKED'
 else:
  code=run('run',[out/'native'],args.run_timeout);stdout=(out/'run.stdout').read_text(errors='replace')
  report['hello_pass']=not code and 'TRACE REAL_UVM_SMOKE' in stdout and all(re.search(r'\b'+severity+r'\s*:\s*0\b',stdout) for severity in ['UVM_FATAL','UVM_ERROR'])
  report['status']='RUN_TIMEOUT' if report['stages']['run']['status']=='TIMEOUT' else 'PASS' if report['hello_pass'] else 'RUN_BLOCKED'
except Exception as error:
 report.update(status='HARNESS_ERROR',error=str(error));raise
finally:save()
raise SystemExit(0 if report['status']=='PASS' else 1)
