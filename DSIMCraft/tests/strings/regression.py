"""Owned dynamic strings, enum names, automatic frames and rollback."""
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
   assert [x for x in text.splitlines() if x.startswith(('TRACE','T11_ENUM_NAME'))]==wanted,(name,backend,text,wanted)
   assert 'FAIL' not in text,(name,backend,text)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name in ['methods','timing','automatic','implicit']:
   cutoff={'methods':100,'timing':750,'automatic':500,'implicit':750}[name]
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({cutoff});
if(s.predict_until(10000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS strings',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(49,0),port
 timing=json.loads((out/'timing/serial.json').read_text())['scopes'][0]['signals'];assert timing['source']['string'] and timing['source']['width'] is None
 assert ('top','source') not in stream(out/'timing/serial.vcd'),'dynamic string is not an integral waveform'
 negatives={
  'real_lhs':('string s;real q;initial q=s;','real conversion requires a numeric value'),
  'mixed_compare':('string s;integer q;initial q=s==1;','mixed string'),
  'mixed_concat':('string s;initial s={s,1};','mixed string'),
  'mixed_mux':('string s;initial s=1?s:1;','mixed string'),
  'arithmetic':('string s;initial s=s+s;','unsupported string operator'),
  'boolean':('string s;initial if(s)$finish;','boolean condition'),
  'not':('string s;integer q;initial q=!s;','string operand'),
  'repeat':('string s;initial repeat(s)$finish;','repeat count'),
  'wait':('string s;initial wait(s)$finish;','boolean condition'),
  'delay':('string s;initial #(s)$finish;','string cannot be used as a delay'),
  'method_count':('string s;integer n;initial n=s.len(1);','argument count'),
  'method_type':('string s;integer n;initial n=s.getc("a");','argument type'),
  'compare_type':('string s;integer n;initial n=s.compare(1);','argument type'),
  'enum_count':('typedef enum{A,B} t;t e;string s;initial s=e.name(1);','too many arguments'),
  'packed':('string[3:0] s;','syntax error'),
  'port':('input string s;','string packed'),
  'nba':('string s;initial s<="text";','string nonblocking'),
  'continuous':('string s;assign s="text";','continuous string'),
  'compound':('string s;initial s+="text";','string compound'),
  'real_formal':('task f(input real s);begin end endtask string x;initial f(x);','real conversion requires a numeric value'),
  'edge':('string s;initial @(posedge s)$finish;','string event'),
  'function_boolean':('function automatic integer f();string s;if(s)return 1;return 0;endfunction integer n;initial n=f();','boolean condition'),
  'literal_method':('integer n;initial n="abc".len();','string method receiver'),
  'numeric_format':('string s;initial $display("%d",s);','require %s'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text('module top;'+text+' endmodule\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 source=out/'keywords.v';source.write_text('module top;integer string=7;initial $display("TRACE keyword %0d",string);endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'keywords'],out,'keywords-compile');assert run([out/'keywords'],out,'keywords-run')=='TRACE keyword 7\n'
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS strings:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
