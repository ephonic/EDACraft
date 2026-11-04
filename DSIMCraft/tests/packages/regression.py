"""Package namespace identity, lexical binding, shared functions and time scopes."""
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
   assert [x for x in text.splitlines() if x.startswith(('TRACE','T03_PACKAGE'))]==wanted,(name,backend,text,wanted)
   current=stream(wave)
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete ordered stream')
   report['captures']+=1
  if name in ['timing','functions','timescales']:
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(100);
if(s.predict_until(10000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
   assert stream(wave)==reference,(name,'rollback full ordered stream');report['rollbacks']+=1;report['captures']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS packages',name,flush=True)
 ir=json.loads((out/'parallel/parallel.json').read_text());assert ir['parallel']['partitions']==2,ir['parallel']
 for port in ['one','two']:
  assert timeline(*read(out/'parallel/parallel.vcd'))[('top',port)][2][-1][1]==(0x8003,0),port
 assert json.loads((out/'functions/parallel.json').read_text())['parallel']['partitions']==1,'shared static package state must stay in one partition'
 assert any(t==125 and v==(123,0) for t,v in timeline(*read(out/'timescales/serial.vcd'))[('top','sampled')][2]),'125ps package delay'
 negatives={
  'missing_package':('module top;import absent::*;endmodule','unknown or not yet declared package'),
  'missing_member':('package p;parameter int X=1;endpackage module top;import p::Y;endmodule','package member not found'),
  'qualified_missing':('package p;endpackage module top;integer x;initial x=p::Y;endmodule','package member not found'),
  'ambiguous':('package p;parameter int X=1;endpackage package q;parameter int X=2;endpackage module top;import p::*;import q::*;integer x;initial x=X;endmodule','ambiguous wildcard'),
  'explicit_conflict':('package p;parameter int X=1;endpackage package q;parameter int X=2;endpackage module top;import p::X,q::X;endmodule','conflicting explicit'),
  'local_conflict':('package p;parameter int X=1;endpackage module top;import p::X;integer X;endmodule','redefined'),
  'duplicate_package':('package p;endpackage package p;endpackage module top;endmodule','duplicate package'),
  'end_label':('package p;endpackage:q module top;endmodule','endpackage name does not match'),
  'forward_dependency':('package p;import q::*;endpackage package q;endpackage module top;endmodule','not yet declared package'),
  'lexical_leak':('package p;function automatic integer f();return hidden;endfunction endpackage module top;integer hidden=1,x;initial x=p::f();endmodule','not visible'),
  'no_export':('package p;parameter int X=1;endpackage package q;import p::X;endpackage module top;integer x;initial x=q::X;endmodule','package member not found'),
  'qualified_declarator':('package p;endpackage module top;integer p::x;endmodule','qualified name cannot be declared'),
  'used_wildcard_conflict':('package p;parameter int X=1;endpackage module top;import p::*;integer y;initial y=X;integer X;endmodule','redefined'),
 }
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text());assert not dest.exists(),name
 work=out/'multifile';work.mkdir(exist_ok=True)
 package,module=(fixtures/'report.sv').read_text().split('module t03;',1)
 (work/'package.sv').write_text(package);(work/'top.sv').write_text('module t03;'+module)
 run([compiler,work/'package.sv',work/'top.sv','-o',work/'model'],work,'compile')
 assert run([work/'model'],work,'run')=='T03_PACKAGE PASS\n'
 source=out/'keywords.v';source.write_text('module top;integer package=1,import=2,endpackage=3;initial $display("TRACE keywords %0d",package+import+endpackage);endmodule\n')
 run([compiler,source,'--language','verilog','-o',out/'keywords'],out,'keywords-compile')
 assert run([out/'keywords'],out,'keywords-run')=='TRACE keywords 6\n'
 report.update(status='PASS',negative_cases=len(negatives),real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS packages:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['negative_cases'],'rejections')
