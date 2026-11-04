"""Inheritance, polymorphic functions/tasks, constructors and transactions."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/class_inheritance';expected=json.loads((fixtures/'expected.json').read_text())
if '--negative-only' in sys.argv[4:]:expected={}
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','180')))
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,'crash',p.returncode,p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,kind,value in events:
  if kind=='value':values[value[0]].append((t,value[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
def native(source,exe,work,label,flags=()):
 strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,*flags,'-I'+str(ROOT/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],work,label)
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 backends=[('serial',[])]
 if name!='q01':
  backends.extend([('wheel',['--time-wheel']),('parallel',['--threads','2'])])
 for backend,flags in backends:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  stdout=run([work/backend],work,backend+'-run')
  trace=[s for s in stdout.splitlines() if s.startswith(('TRACE','PROBE_CLASS'))];assert trace==wanted,(name,backend,trace,wanted)
  if name=='q01':continue
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt)==stdout
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats');assert '"partitions":2' in (work/'stats.stderr').read_text()
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  replacement='''
s.run_until(1);
if(s.predict_until(5,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction unexpectedly committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
if(!s.predict_until(7,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
s.run();
'''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replacement));native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
 report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),backends=[s[0] for s in backends])
 if name=='parallel':
  lanes=timeline(*read(work/'serial-settled.vcd'))
  for signal,wanted_values in [('one',[(0,(0,0)),(2,(5,0)),(4,(7,0))]),('two',[(0,(0,0)),(2,(7,0)),(4,(11,0))]),('three',[(0,(0,0)),(1,(11,0)),(3,(23,0))])]:
   assert lanes[('top',signal)][2]==wanted_values,(signal,lanes[('top',signal)],wanted_values)
negative={
 'unknown_base':('class D extends Missing;endclass','extends requires a previously declared class'),
 'nonclass_base':('int N;class D extends N;endclass','extends requires a previously declared class'),
 'downcast':('class B;endclass class D extends B;endclass B b;D d;initial d=b;','compatible object handle'),
 'unrelated':('class B;endclass class D;endclass B b;D d;initial b=d;','compatible object handle'),
 'ref_covariance':('class B;endclass class D extends B;endclass D d;task automatic t(ref B b);endtask initial t(d);','matching class handle types'),
 'virtual_outside':('virtual function int f();return 1;endfunction','virtual methods require a class'),
 'virtual_constructor':('class B;virtual function new();endfunction endclass','constructors cannot be virtual'),
 'override_width':('class B;virtual function int f(int n);return n;endfunction endclass class D extends B;function int f(bit n);return n;endfunction endclass','override signature mismatch'),
 'override_result':('class B;virtual function int f();return 1;endfunction endclass class D extends B;function string f();return "x";endfunction endclass','override signature mismatch'),
 'missing_base_actual':('class B;function new(int n);endfunction endclass class D extends B;endclass D d;initial d=new;','missing subroutine argument'),
 'late_super':('class B;endclass class D extends B;int n;function new();n=1;super.new();endfunction endclass D d;initial d=new;','super.new must be the first statement'),
 'virtual_wait':('class B;virtual function int f();return 1;endfunction endclass B b;initial begin b=new;wait(b.f());end','virtual function is not allowed in event/wait controls'),
 'virtual_event':('class B;virtual function int f();return 1;endfunction endclass B b;initial begin b=new;@(b.f());end','virtual function is not allowed in event/wait controls'),
}
for name,(body,diagnostic) in negative.items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1
for name,body in [('null_virtual','class B;virtual function int f();return 1;endfunction endclass B b;initial $display("%0d",b.f());'),('null_task','class B;virtual task run();#1;endtask endclass B b;initial b.run();')]:
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n')
 run([compiler,source,'--emit-cpp',out/(name+'.cpp'),'-o',out/name],out,name+'-compile')
 run([out/name],out,name+'-run',False);assert 'null or invalid class object access' in (out/(name+'-run.stderr')).read_text();report['runtime_rejections']+=1
for name,flags in [('wide',[]),('narrow',['-DDSIM_TEST_NARROW=1'])]:
 native(fixtures/'kernel.cpp',out/('kernel-'+name),out,'kernel-'+name+'-compile',flags);run([out/('kernel-'+name)],out,'kernel-'+name+'-run')
report['status']='PASS';(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS class inheritance:',report['captures'],'captures,',report['rollbacks'],'rollback,',report['commits'],'commit,',report['negative_cases'],'compile rejections,',report['runtime_rejections'],'runtime rejections')
