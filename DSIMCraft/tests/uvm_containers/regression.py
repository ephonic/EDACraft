"""UVM integral container foundations, scheduling, values and rollback."""
from pathlib import Path
import json, subprocess, sys, hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations
from compare_waveforms import compare
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/uvm_containers';expected=json.loads((fixtures/'expected.json').read_text())
if '--negative-only' in sys.argv[4:]:expected={}
report=dict(status='RUNNING',models={},captures=0,failed_predictions=0,negative_cases=0)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,'crash',p.returncode,p.stderr)
 assert (not p.returncode)==ok,(label,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,kind,value in events:
  if kind=='value':values[value[0]].append((t,value[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
def native(source,exe,work,label):
 flags=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*flags,'-I'+str(ROOT/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],work,label)
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  stdout=run([work/backend],work,backend+'-run')
  trace=[s for s in stdout.splitlines() if s.startswith(('TRACE','PROBE_'))];assert trace==wanted,(name,backend,trace,wanted)
  if name!='report_q05':
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
 if name!='report_q05':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  replay=code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(100000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction unexpectedly committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
s.run();
''')
  (work/'replay.cpp').write_text(replay);native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(path)==reference['ordered'];report['captures']+=1;report['failed_predictions']+=1
 report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest())
negative={
 'new_queue':('int q[$];initial q=new[2];','new[] requires a dynamic array'),
 'new_assoc':('int a[int];initial a=new[2];','associative array assignment'),
 'size_arg':('int q[$];initial $display("%0d",q.size(1));','argument count'),
 'push_arg':('int q[$];initial q.push_back();','argument count'),
 'push_value':('int q[$];int n;initial n=q.push_back(1);','void container method'),
 'delete_value':('int a[int];int n;initial n=a.delete();','void container method'),
 'wrong_method':('int a[int];initial a.push_back(1);','invalid associative array method'),
 'cursor_const':('int a[int];int n;initial n=a.first(1);','assignment target'),
 'cursor_width':('int a[int];bit[7:0] k;int n;initial n=a.first(k);','whole 32-bit'),
 'queue_actual':('int q[$];task automatic f(ref int a[]);begin end endtask initial f(q);','equivalent container types and bounds'),
 'assoc_actual':('int a[int];task automatic f(input int q[]);begin end endtask initial f(a);','associative arrays require matching key types'),
 'copy_kind':('int a[int],q[$];initial q=a;','associative array assignment'),
 'nba_queue':('int q[$];initial begin q.push_back(1);q[0]<=2;end','timed/NBA'),
 'nba_assoc':('int a[int];initial a[0]<=2;','timed/NBA'),
 'timed_queue':('int q[$];initial q[0]=#1 2;','timed/NBA'),
 'concat':("int q[$];int k;initial {q[0],k}=64'd0;",'concatenation targets'),
 'bound':('int q[$:-1];','queue upper bound'),
 'bound_unknown':("int q[$:32'bx];",'queue upper bound'),
 'nested':('int q[$][2];','mixed runtime container dimensions'),
 'wildcard_key':('int a[*];','syntax error'),
 'query':('int a[int];int n;initial n=$left(a);','system queries are not supported'),
}
for name,(body,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+body+'\nendmodule\n')
 target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not target.exists(),(name,'partial generated output')
 report['negative_cases']+=1
path=out/'unknown-write.sv';path.write_text("module top;int a[int];initial a[32'bx]=1;endmodule\n")
run([compiler,path,'--emit-cpp',out/'unknown-write.cpp','-o',out/'unknown-write'],out,'unknown-write-compile')
run([out/'unknown-write'],out,'unknown-write-run',False)
assert 'associative array write index contains X/Z' in (out/'unknown-write-run.stderr').read_text()
report['runtime_rejections']=1
native(fixtures/'kernel.cpp',out/'kernel',out,'kernel-compile');run([out/'kernel'],out,'kernel-run')
report['status']='PASS';(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS UVM integral containers:',report['captures'],'captures,',report['failed_predictions'],'rollbacks,',report['negative_cases'],'reject cases')
