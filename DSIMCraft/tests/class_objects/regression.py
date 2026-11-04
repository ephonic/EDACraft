"""Class handles, heap effects, method activations, events and transactions."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/class_objects';expected=json.loads((fixtures/'expected.json').read_text())
if '--negative-only' in sys.argv[4:]:expected={}
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
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
 if name in ('events','event_nba','tasks','rollback','clones','parallel'):
  backends.extend([('wheel',['--time-wheel']),('parallel',['--threads','2'])])
 for backend,flags in backends:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  stdout=run([work/backend],work,backend+'-run')
  trace=[s for s in stdout.splitlines() if s.startswith('TRACE')];assert trace==wanted,(name,backend,trace,wanted)
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
 'arithmetic':('class C;endclass C p;int n;initial n=p+1;','class handle'),
 'wrong_class':('class C;endclass class D;endclass C p;D q;initial p=q;','compatible object handle'),
 'integer_handle':('class C;endclass C p;initial p=0;','compatible object handle'),
 'integer_target':('class C;endclass C p;int n;initial n=p;','class handle cannot'),
 'wrong_compare':('class C;endclass class D;endclass C p;D q;initial $display("%0d",p==q);','class handle'),
 'integer_compare':('class C;endclass C p;initial $display("%0d",p==0);','class handle'),
 'ref_type':('class C;endclass class D;endclass C p;task automatic f(ref D a);begin end endtask initial f(p);','matching class handle types'),
 'new_integer':('int n;initial n=new;','class-typed assignment context'),
 'no_constructor':('class C;endclass C p;initial p=new(1);','accepts no arguments'),
 'constructor_outside':('function new();begin end endfunction','requires a class'),
 'missing_property':('class C;endclass C p;initial p.value=1;','class member'),
 'handle_packed_select':('class C;endclass C p;int n;initial n=p[0];','class handles cannot be selected'),
 'property_array':('class C;int a[2];endclass C p;initial p=new;','unpacked class properties'),
 'recursive_allocation':('class C;C p=new;endclass C p;initial p=new;','recursive class allocation'),
 'nba_property':('class C;int n;endclass C p;initial begin p=new;p.n<=1;end','class property'),
}
for name,(body,diagnostic) in negative.items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1
for name,body in [('null_field','class C;int n;endclass C p;initial $display("%0d",p.n);'),('null_method','class C;function int f();return 1;endfunction endclass C p;initial $display("%0d",p.f());')]:
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n')
 run([compiler,source,'--emit-cpp',out/(name+'.cpp'),'-o',out/name],out,name+'-compile')
 run([out/name],out,name+'-run',False);assert 'null or invalid class object access' in (out/(name+'-run.stderr')).read_text();report['runtime_rejections']+=1
for name,flags in [('wide',[]),('narrow',['-DDSIM_TEST_NARROW=1'])]:
 native(fixtures/'kernel.cpp',out/('kernel-'+name),out,'kernel-'+name+'-compile',flags);run([out/('kernel-'+name)],out,'kernel-'+name+'-run')
report['status']='PASS';(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS class objects:',report['captures'],'captures,',report['rollbacks'],'rollback,',report['commits'],'commit,',report['negative_cases'],'compile rejections,',report['runtime_rejections'],'runtime rejections')
