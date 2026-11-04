"""Budget interruptions must preserve PC/FIFO and reproduce uninterrupted waves."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations

def run(cmd,work,label,env=None):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=240,env=env)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout[-1000:],p.stderr[-2000:])
 return p.stdout,p.stderr

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 decl=declarations(meta);names={i:tuple(sorted(k for k,v in decl.items() if v[0]==i)) for i in range(len(values))};ordered=[]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]));ordered.append((t,names[p[0]],p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in decl.items()},ordered

probe='''
uint64_t budget_cuts=0;
const char* chunk_text=std::getenv("DSIM_TEST_BUDGET_CHUNK");
uint64_t chunk=chunk_text?std::stoull(chunk_text):0;
for(;;){
 try{s.run();break;}
 catch(const InstructionBudgetExhausted&){
  if(++budget_cuts>100000)throw std::runtime_error("budget resume made no progress");
  if(std::getenv("DSIM_TEST_BUDGET_CHECKPOINT")){auto interrupted=s.checkpoint();s.restore(interrupted);s.restore(interrupted);}
  s.limit=chunk?s.limit+chunk:100000000;
 }
}
std::cerr<<"BUDGET "<<s.executed_steps()<<" "<<budget_cuts<<"\\n";
'''
report=dict(status='RUNNING',models={},resumes=0,repeated_chunks=0,ordered_captures=0,checkpoint_resumes=0)
try:
 for name,path in [('edges','comb_leaves/edges.sv'),('controls','compiled_activation/controls.sv'),('property','sequence_delays/chain.sv'),('fork','automatic_fork/sharing.sv')]:
  work=out/name;work.mkdir(exist_ok=True);source=ROOT/'tests'/path
  run([compiler,source,'--wave-support','--emit-cpp',work/'model.cpp','-o',work/'normal'],work,'lower')
  code=(work/'model.cpp').read_text();assert code.count('\ns.run();\n')==1
  cpp=work/'resume.cpp';cpp.write_text('#include <cstdlib>\n'+code.replace('\ns.run();\n',probe))
  cxx=config.get('DSIM_MODEL_CXX',config['CMAKE_CXX_COMPILER'])
  if Path(cxx).name=='clang++' and sys.platform=='darwin':cxx='c++'
  run([cxx,'-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',work/'resume'],work,'resume-compile')
  wave=work/'normal.vcd';wave.unlink(missing_ok=True)
  expected,_=run([work/'normal','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'normal-run')
  reference=stream(wave);assert reference[0]
  base,err=run([work/'resume'],work,'unlimited')
  assert base==expected
  total,cuts=map(int,next(x for x in err.splitlines() if x.startswith('BUDGET ')).split()[1:]);assert cuts==0
  for label,limit,chunk in [(str(i),i,0) for i in [*range(129),255,256,257,511,512,1024]]+[('chunks-'+str(i),0,i) for i in [3,7,17]]:
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   env=dict(os.environ);env.pop('DSIM_TEST_BUDGET_CHUNK',None)
   if chunk:env['DSIM_TEST_BUDGET_CHUNK']=str(chunk)
   text,err=run([work/'resume','--max-events',limit,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label,env)
   assert text==expected,(name,label,'output')
   assert stream(wave)==reference,(name,label,'full ordered capture')
   steps,cuts=map(int,next(x for x in err.splitlines() if x.startswith('BUDGET ')).split()[1:])
   assert steps==total+cuts,(name,label,steps,total,cuts)
   assert cuts>0 or limit>=total
   report['resumes']+=1;report['ordered_captures']+=1
   if chunk:report['repeated_chunks']+=1
  for limit in [*range(33),63,64,65,127,128,255,256,511]:
   env=dict(os.environ);env.pop('DSIM_TEST_BUDGET_CHUNK',None);env['DSIM_TEST_BUDGET_CHECKPOINT']='1'
   text,err=run([work/'resume','--max-events',limit],work,'checkpoint-'+str(limit),env)
   assert text==expected,(name,limit,'checkpoint output')
   steps,cuts=map(int,next(x for x in err.splitlines() if x.startswith('BUDGET ')).split()[1:])
   assert steps==total+cuts
   report['checkpoint_resumes']+=1
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),uninterrupted_steps=total)
  print('PASS budget resume',name,flush=True)
 # Function-local C++ PCs are not restartable. A safe-boundary retry must
 # never catch their ordinary step() failures and rerun visible side effects.
 work=out/'functions';work.mkdir(exist_ok=True)
 source=Path(__file__).with_name('functions.sv')
 run([compiler,source,'--emit-cpp',work/'model.cpp','-o',work/'normal'],work,'lower')
 code=(work/'model.cpp').read_text();assert code.count('\ns.run();\n')==1
 cpp=work/'resume.cpp';cpp.write_text('#include <cstdlib>\n'+code.replace('\ns.run();\n',probe))
 run([cxx,'-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],cpp,config['DSIM_ZSTD_LIBRARY'],'-o',work/'resume'],work,'resume-compile')
 expected,_=run([work/'normal'],work,'normal-run')
 assert expected.strip()=='TRACE function boundary 16 16'
 rejected=0
 for limit in range(65):
  p=subprocess.run([str(work/'resume'),'--max-events',str(limit)],cwd=work,text=True,capture_output=True,timeout=60)
  (work/(str(limit)+'.stdout')).write_text(p.stdout);(work/(str(limit)+'.stderr')).write_text(p.stderr)
  assert p.returncode in [0,1]
  if p.returncode:
   assert 'execution budget exhausted' in p.stderr and not p.stdout
   rejected+=1
  else:assert p.stdout==expected
 assert rejected>0
 report['nonrestartable_function_cuts']=rejected
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
