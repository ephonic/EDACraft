"""Compilation-unit imports, lexical scopes, canonical storage and replay."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache_path.read_text().splitlines() if '=' in x and not x.startswith('//')}
sys.path.insert(0,str(ROOT/'tests/waveform'));from reader import read,declarations,timeline

def run(command,work,label,ok=True):
 p=subprocess.run(list(map(str,command)),cwd=work,text=True,capture_output=True,timeout=300)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout[-2000:],p.stderr[-2000:])
 return p.stdout

def stream(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,commits=0,rollbacks=0,negative_cases=0)
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'--emit-ir',work/(backend+'.json'),'-o',work/backend],work,backend+'-compile')
   wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/backend,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,backend+'-run')
   assert [x for x in text.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,text,wanted)
   current=(text,stream(wave))
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete per-signal ordered streams')
   report['captures']+=1
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  cxx=cache.get('DSIM_MODEL_CXX',cache['CMAKE_CXX_COMPILER'])
  if Path(cxx).name=='clang++' and sys.platform=='darwin':cxx='c++'
  cflags=['-fp-model=strict'] if Path(cxx).name in ['icpx','icpc'] else []
  def native(cpp,label):
   run([cxx,'-std=c++17','-O2','-pthread',*cflags,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
  for accept in [False,True]:
   label='commit' if accept else 'rollback';cpp=work/(label+'.cpp')
   patch='''
s.run_until(500);
bool accepted=s.predict_until(95000,[](Sim&){},[](const Sim&){return ACCEPT;},[](Sim&){});
if(accepted!=ACCEPT||s.prediction_stats.COUNTER!=1)throw std::runtime_error("compilation-unit transaction mismatch");
s.run();
'''.replace('ACCEPT',str(accept).lower()).replace('COUNTER','commits' if accept else 'rollbacks')
   cpp.write_text(code.replace('\ns.run();\n',patch));native(cpp,label)
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/label,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run')
   assert (text,stream(wave))==reference,(name,label,'transaction state or wave')
   report['captures']+=1;report['commits' if accept else 'rollbacks']+=1
  ir=json.loads((work/'parallel.json').read_text())
  if name=='parallel':
   assert ir['parallel']['partitions']==2,ir['parallel']
   values=timeline(*read(work/'parallel.vcd'))
   for port,wanted_value in [('one',4),('two',22)]:assert values[('top',port)][2][-1][1]==(wanted_value,0),port
   run([work/'parallel','--parallel-stats'],work,'parallel-stats');assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
  if name=='shared':
   assert ir['parallel']['partitions']==1,'shared package must remain in one partition'
   ids=sorted({row['id'] for scope in ir['scopes'] for row in scope['signals'].values()})
   values='std::vector<V>{'+','.join('s.get('+str(i)+')' for i in ids)+'}'
   probe='s.run_until(1500);auto cp=s.checkpoint();s.run();auto final='+values+';auto steps=s.executed_steps();s.restore(cp);s.restore(cp);s.run();auto again='+values+';if(s.executed_steps()!=steps)throw std::runtime_error("checkpoint steps");for(size_t i=0;i<final.size();++i)if(!final[i].same(again[i]))throw std::runtime_error("checkpoint package state");'
   cpp=work/'checkpoint.cpp';cpp.write_text(code.replace('\ns.run();\n',probe));native(cpp,'checkpoint')
   assert run([work/'checkpoint'],work,'checkpoint-run').splitlines()==wanted+wanted
   report['checkpoint_restores']=2
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),trace=wanted,parallel_partitions=ir['parallel']['partitions'])
  print('PASS compilation imports',name,flush=True)
 # Imports are lexical; packages cannot capture $unit and later imports do
 # not retroactively affect earlier module definitions.
 p='package p;parameter int N=3;typedef logic[2:0] T;endpackage '
 q='package q;parameter int N=5;endpackage '
 negatives={
  'missing_package':('import absent::*;module top;endmodule','unknown or not yet declared package'),
  'forward_package':('import p::*;'+p+'module top;endmodule','unknown or not yet declared package'),
  'missing_member':(p+'import p::absent;module top;endmodule','package member not found'),
  'explicit_conflict':(p+q+'import p::N;import q::N;module top;endmodule','conflicting explicit'),
  'list_conflict':(p+q+'import p::N,q::N;module top;endmodule','conflicting explicit'),
  'ambiguous':(p+q+'import p::*;import q::*;module top;integer x;initial x=N;endmodule','ambiguous wildcard'),
  'bound_explicit_conflict':(p+q+'import p::*;module early #(parameter V=N)();endmodule import q::N;module top;early e();endmodule','conflicting explicit'),
  'shadow_does_not_bind':(p+q+'import p::*;module early;parameter N=7;integer x;initial x=N;endmodule import q::*;module top;early e();integer x;initial x=N;endmodule','ambiguous wildcard'),
  'local_import_does_not_bind_unit':(p+q+'import p::*;module early;import p::N;integer x;initial x=N;endmodule import q::*;module top;early e();integer x;initial x=N;endmodule','ambiguous wildcard'),
  'provisional_not_binding':(p+q+'import p::*,q::*;module early;integer x;initial x=N;endmodule import p::*;module top;early e();integer x;initial x=N;endmodule','ambiguous wildcard'),
  'ambiguous_header':(p+q+'import p::*,q::*;module top #(parameter W=N)();endmodule','ambiguous wildcard'),
  'module_before_import':(p+'module early;integer x;initial x=N;endmodule import p::*;module top;early e();endmodule','not visible'),
  'header_before_import':(p+'module top #(parameter W=N)();endmodule import p::*;','not visible'),
  'package_capture':(p+'import p::*;package q;parameter M=N;endpackage module top;endmodule','not visible'),
  'package_capture_explicit':(p+'import p::N;package q;parameter M=N;endpackage module top;endmodule','not visible'),
  'hierarchical_import':(p+'import p::*;module child;endmodule module top;child u();integer x;initial x=u.N;endmodule','unknown hierarchical member'),
  'explicit_unit_export':(p+'import p::*;export p::N;module top;endmodule',None),
 }
 for name,(body,diagnostic) in negatives.items():
  path=out/(name+'.sv');path.write_text(body+'\n');dest=out/(name+'.cpp');dest.unlink(missing_ok=True)
  run([compiler,path,'--emit-only','--emit-cpp',dest],out,name,False)
  if diagnostic:assert diagnostic in (out/(name+'.stderr')).read_text(),name
  assert not dest.exists(),name
  report['negative_cases']+=1
 # Local declarations shadow the outer import, including explicit imports.
 shadow=out/'explicit-shadow.sv';shadow.write_text(p+'import p::N,p::T;module top;parameter N=7;typedef bit[1:0] T;T x;initial begin x=N;$display("TRACE shadow %0d",x);end endmodule\n')
 run([compiler,shadow,'-o',out/'explicit-shadow'],out,'explicit-shadow-compile')
 assert run([out/'explicit-shadow'],out,'explicit-shadow-run').splitlines()==['TRACE shadow 3']
 # Source files in this invocation form one ordered compilation unit.
 a=out/'first.sv';b=out/'second.sv';a.write_text(p+'import p::N;\n');b.write_text('module top;initial $display("TRACE multifile %0d",N);endmodule\n')
 run([compiler,a,b,'-o',out/'multifile'],out,'multifile-compile')
 assert run([out/'multifile'],out,'multifile-run').splitlines()==['TRACE multifile 3']
 run([compiler,b,a,'--emit-only','--emit-cpp',out/'reversed.cpp'],out,'reversed',False)
 report['negative_cases']+=1
 # No new keyword is reserved by this extension in Verilog mode.
 legacy=out/'legacy.v';legacy.write_text('module import;integer x;initial x=1;endmodule\n')
 run([compiler,legacy,'--language','verilog','-o',out/'legacy'],out,'legacy-compile')
 report.update(status='PASS',real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS compilation imports:',report['captures'],'captures,',report['negative_cases'],'rejections')
