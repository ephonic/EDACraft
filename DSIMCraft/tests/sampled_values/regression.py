"""Clock-sampled value functions, gated history and rollback."""
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
   assert [x for x in text.splitlines() if x.startswith(('TRACE','T04_CONC_ASSERT'))]==wanted,(name,backend,text,wanted)
   assert 'FAIL' not in text,(name,backend,text)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name in ['history','disabled','actions','nested','edges','initial']:
   cutoff=6000
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({cutoff});
if(s.predict_until(30000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS sampled values',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(1,0),port
 negatives={
  'outside':('reg x;initial $display("%b",$past(x));','concurrent property clock'),
  'zero_depth':('reg clk,x;assert property(@(posedge clk) $past(x,0));','positive constant'),
  'negative_depth':('reg clk,x;assert property(@(posedge clk) $past(x,-1));','positive constant'),
  'huge_depth':('reg clk,x;assert property(@(posedge clk) $past(x,65537));','positive constant'),
  'xz_depth':("reg clk,x;assert property(@(posedge clk) $past(x,32'bx));",'positive constant'),
  'dynamic_depth':('reg clk,x;integer n=2;assert property(@(posedge clk) $past(x,n));','positive constant'),
  'extra_past':('reg clk,x;assert property(@(posedge clk) $past(x,1,1,1));','one to three arguments'),
  'extra_rose':('reg clk,x;assert property(@(posedge clk) $rose(x,1));','exactly one argument'),
  'mutation':('reg clk;integer x;assert property(@(posedge clk) $past(x++));','pure integral expression'),
  'random':('reg clk;assert property(@(posedge clk) $past($urandom()));','pure integral expression'),
  'string':('reg clk;string x;assert property(@(posedge clk) $sampled(x));','pure integral expression'),
  'memory':('reg clk,x[2];integer i=0;assert property(@(posedge clk) $past(x[i]));','property expression'),
  'action_history':('reg clk,x;assert property(@(posedge clk) 1) $display("%b",$past(x));','history functions require a property expression'),
  'disable_history':('reg clk,x;assert property(@(posedge clk) disable iff($rose(x)) 1);','history functions require a property expression'),
 }

 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+text+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 source=out/'keywords.v';source.write_text('module top;integer property=7,endproperty=8;initial $display("TRACE keyword %0d %0d",property,endproperty);endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'keywords'],out,'keywords-compile');assert run([out/'keywords'],out,'keywords-run')=='TRACE keyword 7 8\n'
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS sampled values:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
