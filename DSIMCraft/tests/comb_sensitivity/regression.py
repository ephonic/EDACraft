"""Static bit sensitivity for always_comb/always_latch, including hidden function reads."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,text=True,capture_output=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
expected=json.loads((fixtures/'expected.json').read_text());expected['reported']=json.loads((fixtures/'reported/expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  sources=[fixtures/'reported/rtl.sv',fixtures/'reported/tb.sv'] if name=='reported' else [fixtures/(name+'.sv')]
  top='tb_compare' if name=='reported' else 'top'
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,*sources,'--top',top,*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert text.splitlines()==wanted,(name,backend,text,wanted)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name!='parallel':
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(1000000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
  print('PASS static bit sensitivity',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 run([out/'parallel/parallel','--parallel-stats'],out/'parallel','stats');assert '"partitions":2' in (out/'parallel/stats.stderr').read_text()
 for port,value in [('one',1),('two',2)]:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(value,0),port
 # Static disjoint drivers are legal; overlapping writers remain illegal.
 negatives={
  'static_overlap':('logic[3:0]q;always_comb q[3:2]=q[1:0];initial q[3]=0;','another writer'),
  'whole_overlap':('logic[3:0]q;always_comb q[3:2]=q[1:0];initial q=0;','another writer'),
  'union_overlap':('logic[3:0]q,a;always_comb begin q[3:2]=a[3:2];q[1:0]=a[1:0];end initial q[1]=0;','another writer'),
  'dynamic_feedback':('logic[7:0]q;integer i;always_comb q[i]=q[0];','dynamic bit-select sensitivity'),
  'function_feedback':('logic[7:0]q,y;integer i;function automatic[7:0]f();q[i]=q[0];return q;endfunction always_comb y=f();','dynamic bit-select sensitivity'),
  'dynamic_view':('typedef struct packed{logic[3:0]hi;logic[3:0]lo;}pair_t;pair_t q;integer i;always_comb q.hi[i]=q.lo[0];','dynamic bit-select sensitivity'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+text+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2,reported_events=196)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS static bit sensitivity:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
