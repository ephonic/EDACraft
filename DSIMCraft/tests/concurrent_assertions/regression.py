"""Single-clock concurrent properties, sampled evaluation and rollback."""
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
  if name in ['implication','sampling','disable','clones','reset_nba','actions','glitch','reactive']:
   cutoff=(1000 if name in ['glitch','reactive'] else 6000)
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
  print('PASS concurrent properties',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(1,0),port
 negatives={
  'unknown':('reg clk;assert property(missing);','unknown local property'),
  'duplicate':('reg clk;property p;@(posedge clk) 1;endproperty property p;@(posedge clk) 0;endproperty','duplicate property'),
  'collision':('reg clk,p;property p;@(posedge clk) 1;endproperty','conflicts with a local declaration'),
  'alias':('reg clk;property p;@(posedge clk) 1;endproperty property q;p;endproperty','property aliases'),
  'formals':('reg clk;property p(int x);@(posedge clk) x;endproperty','syntax error'),
  'clockless':('reg x;assert property(x);','unknown local property'),
  'anyclock':('reg clk;assert property(@(clk) 1);','explicit posedge or negedge'),
  'starclock':('reg clk;assert property(@* 1);','single edge clock'),
  'expression_clock':('reg clk,x;assert property(@(posedge(clk&&x)) 1);','static integral signal'),
  'multiclock':('reg clk,rst;assert property(@(posedge clk or negedge rst) 1);','single edge clock'),
  'clock_iff':('reg clk,x;assert property(@(posedge clk iff x) 1);','clock qualifier'),
  'sequence_delay':('reg clk,x;assert property(@(posedge clk) x ##[1:2] x);','syntax error'),
  'repetition_range':('reg clk,x;assert property(@(posedge clk) x[*1:2]);','syntax error'),
  'mutation':('reg clk;integer x;assert property(@(posedge clk) x++);','pure integral expression'),
  'random':('reg clk;assert property(@(posedge clk) $urandom());','pure integral expression'),
  'function':('reg clk;function integer f();return 1;endfunction assert property(@(posedge clk) f());','pure integral expression'),
  'text':('reg clk;string x;assert property(@(posedge clk) x);','pure integral expression'),
  'memory':('reg clk,x[2];integer i=0;assert property(@(posedge clk) x[i]);','property expression'),
  'cover_else':('reg clk;cover property(@(posedge clk) 1) begin end else begin end','cover property'),
  'action_delay':('reg clk;assert property(@(posedge clk) 1) #1 $display("bad");','timing and suspension'),
  'action_wait':('reg clk;assert property(@(posedge clk) 1) @(clk) $display("bad");','timing and suspension'),
  'action_fork':('reg clk;assert property(@(posedge clk) 1) fork $display("bad");join_none','timing and suspension'),
  'procedural':('reg clk;initial assert property(@(posedge clk) 1);','syntax error'),
 }

 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+text+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 source=out/'keywords.v';source.write_text('module top;integer property=7,endproperty=8;initial $display("TRACE keyword %0d %0d",property,endproperty);endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'keywords'],out,'keywords-compile');assert run([out/'keywords'],out,'keywords-run')=='TRACE keyword 7 8\n'
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS concurrent properties:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
