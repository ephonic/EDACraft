"""Replay frozen memory cases without changing their input or 180 second budget."""
import hashlib,json,os,signal,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,work,label,timeout=180,env=None,expected=0):
 started=time.monotonic()
 if '--waveform' in args:
  wave=Path(args[args.index('--waveform')+1]);(wave if wave.is_absolute() else work/wave).unlink(missing_ok=True)
 with (work/(label+'.stdout')).open('w') as a,(work/(label+'.stderr')).open('w') as b:
  p=subprocess.Popen(list(map(str,args)),cwd=work,stdout=a,stderr=b,env=env,start_new_session=True)
  try:code=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM);p.wait();raise AssertionError((label,'original compile/run budget exceeded',timeout))
 text=(work/(label+'.stdout')).read_text();error=(work/(label+'.stderr')).read_text()
 assert code==expected,(label,code,text[-2000:],error[-2000:])
 return text,error,time.monotonic()-started

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {k:(w,r,values[i]) for k,(i,w,r) in declarations(meta).items()}
report=dict(status='RUNNING',binary_sha256=sha(compiler),original_cases={},captures=0,budget_resumes=0,checkpoint_resumes=0)
try:
 for name,row in json.loads((fixtures/'origins.json').read_text()).items():
  work=out/name;work.mkdir(exist_ok=True)
  for file,digest in row['files'].items():
   assert sha(fixtures/name/file)==digest
   shutil.copy2(fixtures/name/file,work/file)
  _,_,seconds=run([compiler,'--timescale','1ns/1ps','--top','tb','dut.sv','tb.sv','--emit-cpp','model.cpp','-o','simv'],work,'compile')
  text,_,runtime=run([work/'simv'],work,'run',60);assert text==row['expected_stdout'],(name,text)
  code=(work/'model.cpp').read_text()
  if name=='unrolled':assert 'Bounded compilation of a large acyclic initial process.' in code
  report['original_cases'][name]=dict(status='PASS',source_sha256=row['files'],compile_seconds=round(seconds,3),run_seconds=round(runtime,3),budget_seconds=180,phases=row['phases'],port_comparisons=row['port_comparisons'],stdout=text,cpp_sha256=sha(work/'model.cpp'))
  print('PASS unchanged memory case',name,flush=True)
 expected=(fixtures/'scalars.expected.txt').read_text()
 reference=None
 for label,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  work=out/('scalars-'+label);work.mkdir(exist_ok=True)
  run([compiler,fixtures/'scalars.sv',*flags,'--wave-support','--emit-cpp','model.cpp','-o','model'],work,'compile')
  text,_,_=run([work/'model','--waveform','wave.vcd','--wave-format','vcd','--wave-mode','ordered'],work,'run',60)
  assert text==expected,(label,text,expected)
  current=stream(work/'wave.vcd')
  if reference is None:reference=current
  else:assert reference==current,label
  report['captures']+=1
 # A large forward-only process, forward branches and suspension PCs; one
 # independent small process keeps a genuine two-partition configuration.
 work=out/'large';work.mkdir(exist_ok=True);source=work/'large.sv'
 body=[]
 for i in range(17000):
  body.append('value='+str(i+1)+';')
  if i%257==0:body.append('#1;')
  if i%251==0:body.append('if(value==0)value=17;else value='+str(i+1)+';')
 source.write_text('`timescale 1ns/1ps\nmodule bulk_lane(output integer value=0);initial begin\n'+'\n'.join(body)+'\nend endmodule\nmodule peer_lane(output integer value=0);initial begin value=5;#1;value=9;#2;value=11;end endmodule\nmodule top;wire[31:0] one,two;bulk_lane a(one);peer_lane b(two);endmodule\n')
 reference=None
 for label,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,source,*flags,'--wave-support','--emit-cpp',label+'.cpp','--emit-ir',label+'.json','-o',label],work,label+'-compile')
  text,_,_=run([work/label,'--waveform',label+'.vcd','--wave-format','vcd','--wave-mode','ordered'],work,label+'-run',60);assert not text
  current=stream(work/(label+'.vcd'))
  if reference is None:reference=current
  else:assert reference==current,label
  values=timeline(*read(work/(label+'.vcd')))
  for port,value in [('one',17000),('two',11)]:assert values[('top',port)][2][-1][1]==(value,0)
  report['captures']+=1
 ir=json.loads((work/'parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
 ports=json.loads((work/'serial.json').read_text())['scopes'][0]['signals']
 checks=''.join('if(s.get('+str(ports[name]['id'])+').a!='+str(value)+'ULL||s.get('+str(ports[name]['id'])+').b)throw std::runtime_error("large process final state");' for name,value in [('one',17000),('two',11)])
 probe='''
if(const char* prediction=std::getenv("DSIM_TEST_PREDICTION")){
 bool accept=std::string(prediction)=="commit";s.run_until(2000);
 if(s.predict_until(60000,[](Sim&){},[&](const Sim&){return accept;},[](Sim&){})!=accept)throw std::runtime_error("prediction outcome");
 if((accept?s.prediction_stats.commits:s.prediction_stats.rollbacks)!=1)throw std::runtime_error("prediction count");}
uint64_t cuts=0;const char* text=std::getenv("DSIM_TEST_BUDGET_CHUNK");uint64_t chunk=text?std::stoull(text):0;
for(;;){try{s.run();break;}catch(const InstructionBudgetExhausted&){
 if(++cuts>100000)throw std::runtime_error("no budget progress");
 if(std::getenv("DSIM_TEST_BUDGET_CHECKPOINT")){auto cp=s.checkpoint();s.restore(cp);s.restore(cp);}
 s.limit=chunk?s.limit+chunk:100000000;}}
FINAL_CHECKS
std::cerr<<"BUDGET "<<s.executed_steps()<<" "<<cuts<<"\\n";
'''
 probe=probe.replace('FINAL_CHECKS',checks)
 cpp=work/'resume.cpp';cpp.write_text('#include <cstdlib>\n'+code.replace('\ns.run();\n',probe))
 cxx=cache.get('DSIM_MODEL_CXX',cache['CMAKE_CXX_COMPILER'])
 if Path(cxx).name=='clang++' and sys.platform=='darwin':cxx='c++'
 strict=['-fp-model=strict'] if Path(cxx).name in ['icpx','icpc'] else []
 run([cxx,'-std=c++17','-O2','-pthread',*strict,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/'resume'],work,'resume-compile')
 _,error,_=run([work/'resume'],work,'unlimited',60)
 total,cuts=map(int,next(x for x in error.splitlines() if x.startswith('BUDGET ')).split()[1:]);assert cuts==0
 limits=[0,1,254,255,256,257,258,510,511,512,513,1023,1024,16383,16384,16385,total-1,total]
 for checkpoint in [False,True]:
  for limit in limits:
   label=('checkpoint-' if checkpoint else 'resume-')+str(limit);env=dict(os.environ)
   if checkpoint:env['DSIM_TEST_BUDGET_CHECKPOINT']='1'
   args=[work/'resume','--max-events',limit]+([] if checkpoint else ['--waveform',label+'.vcd','--wave-format','vcd','--wave-mode','ordered'])
   text,error,_=run(args,work,label,60,env)
   assert not text
   if not checkpoint:assert stream(work/(label+'.vcd'))==reference,label
   steps,cuts=map(int,next(x for x in error.splitlines() if x.startswith('BUDGET ')).split()[1:]);assert steps==total+cuts,(label,steps,total,cuts)
   report['checkpoint_resumes' if checkpoint else 'budget_resumes']+=1
   if not checkpoint:report['captures']+=1
 for amount in [17,255,256,257]:
  label='chunks-'+str(amount);env=dict(os.environ,DSIM_TEST_BUDGET_CHUNK=str(amount),DSIM_TEST_BUDGET_CHECKPOINT='1')
  text,error,_=run([work/'resume','--max-events','0'],work,label,60,env)
  assert not text
  steps,cuts=map(int,next(x for x in error.splitlines() if x.startswith('BUDGET ')).split()[1:]);assert steps==total+cuts and cuts>1
  report['checkpoint_resumes']+=1
 for outcome in ['commit','rollback']:
  label='prediction-'+outcome;env=dict(os.environ,DSIM_TEST_PREDICTION=outcome)
  text,_,_=run([work/'resume','--waveform',label+'.vcd','--wave-format','vcd','--wave-mode','ordered'],work,label,60,env)
  assert not text and stream(work/(label+'.vcd'))==reference,label
  report['captures']+=1
 report['prediction_commits']=1;report['prediction_rollbacks']=1
 # Conservatively keep loops and recurring RTL on their previous code path.
 for name,prefix,suffix in [('loop','initial begin','forever #1;end'),('always','always begin','end')]:
  test=work/(name+'.sv');test.write_text('module top;integer value;'+prefix+'\n'+'\n'.join('value='+str(i)+';' for i in range(16500))+suffix+' endmodule\n')
  run([compiler,test,'--emit-only','--emit-cpp',name+'.cpp'],work,name)
  assert 'Bounded compilation of a large acyclic initial process.' not in (work/(name+'.cpp')).read_text(),name
 negatives=['a[1]','a[i]','a[0:1]','a[0+:2]','a[0][0]']
 for i,expression in enumerate(negatives):
  test=out/('negative-'+str(i)+'.sv');test.write_text('module top;reg a;integer i=0;initial $display("%b",'+expression+');endmodule\n')
  dest=out/('negative-'+str(i)+'.cpp');dest.write_text('keep original output')
  _,error,_=run([compiler,test,'--emit-only','--emit-cpp',dest],out,'negative-'+str(i),expected=1)
  assert error and dest.read_text()=='keep original output'
 report.update(status='PASS',negative_cases=len(negatives),large_process_partitions=2,uninterrupted_steps=total,large_source_sha256=sha(source))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
