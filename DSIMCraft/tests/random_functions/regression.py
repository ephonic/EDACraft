"""Stateful random calls: seeds, ranges, frames, scheduler and rollback."""
import hashlib,json,subprocess,sys
from pathlib import Path
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
expected=json.loads((fixtures/'expected.json').read_text());report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert [x for x in text.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,text,wanted)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   assert run([work/backend],work,backend+'-repeat')==text,(name,'run reproducibility')
   report['captures']+=1
  if name in ['timing','forks','overlap','replay']:
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(100000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS random functions',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for signal in ['one','two']:
  assert timeline(*read(out/'parallel/parallel.vcd'))[('top',signal)][2][-1][1]==(0x7903,0)
 negatives={
  'direct_call':('initial $urandom();','result must be consumed'),
  'urandom_arity':('integer x;initial x=$urandom(1,2);','accepts at most one'),
  'range_missing':('integer x;initial x=$urandom_range();','requires one or two'),
  'range_extra':('integer x;initial x=$urandom_range(1,2,3);','requires one or two'),
  'seed_constant':('integer x;initial x=$random(42);','assignment target must be a variable'),
  'seed_short':('logic[15:0]s;integer x;initial x=$random(s);','whole integral variable'),
  'seed_select':('logic[63:0]s;integer x;initial x=$random(s[31:0]);','whole integral variable'),
  'seed_readonly':('function automatic integer f(const ref integer s);return $random(s);endfunction integer x;initial x=f(x);','const ref'),
  'continuous':('wire[31:0]x;assign x=$urandom();','requires a procedural expression'),
  'reduction_mapper':('integer a[2],x;initial x=a.sum with($urandom()+item);','requires no user calls or side effects'),
  'event':('integer x;initial @($urandom())x=1;','event'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+text+'endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 source=out/'legacy.v';source.write_text('module top;integer seed=1,r;initial begin r=$random(seed);$display("TRACE legacy_v %0h",r);end endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'legacy_v'],out,'legacy_v-compile');assert run([out/'legacy_v'],out,'legacy_v-run')=='TRACE legacy_v 80010e00\n'
 source=out/'sv_only.v';source.write_text('module top;integer x;initial x=$urandom;endmodule\n')
 run([compiler,source,'--language','verilog','--emit-only','--emit-cpp',out/'sv_only.cpp'],out,'sv_only',False);assert 'requires SystemVerilog mode' in (out/'sv_only.stderr').read_text()
 report.update(status='PASS',negative_cases=len(negatives)+1,real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS random functions:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
