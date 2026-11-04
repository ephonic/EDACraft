"""Modport prototype signatures, view defaults and ordinary execution semantics."""
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
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0)
try:
 for name in (sys.argv[4:] or expected):
  wanted=expected[name]
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
  for accept in [False,True]:
   label='commit' if accept else 'rollback';cpp=work/(label+'.cpp')
   patch='''
s.run_until(500);
bool accepted=s.predict_until(95000,[](Sim&){},[](const Sim&){return ACCEPT;},[](Sim&){});
if(accepted!=ACCEPT||s.prediction_stats.COUNTER!=1)throw std::runtime_error("interface subroutine transaction mismatch");
s.run();
'''.replace('ACCEPT',str(accept).lower()).replace('COUNTER','commits' if accept else 'rollbacks')
   cpp.write_text(code.replace('\ns.run();\n',patch))
   flags=['-fp-model=strict'] if Path(cxx).name in ['icpx','icpc'] else []
   run([cxx,'-std=c++17','-O2','-pthread',*flags,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/label],work,label+'-compile')
   wave=work/(label+'.vcd');wave.unlink(missing_ok=True)
   text=run([work/label,'--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,label+'-run')
   assert (text,stream(wave))==reference,(name,label,'transaction state or wave')
   report['captures']+=1;report['commits' if accept else 'rollbacks']+=1
  ir=json.loads((work/'parallel.json').read_text())
  if name=='parallel':
   assert ir['parallel']['partitions']==2,ir['parallel']
   run([work/'parallel','--parallel-stats'],work,'parallel-stats')
   assert '"partitions":2' in (work/'parallel-stats.stderr').read_text()
   values=timeline(*read(work/'parallel.vcd'))
   for port,value in [('one',18),('two',26),('error_one',0),('error_two',0)]:assert values[('top',port)][2][-1][1]==(value,0),port
  if name=='basic':
   # No active waveform sink: snapshot/restore is tested directly, including
   # repeated restore, completed PC state and all declared final signal values.
   ids=sorted({row['id'] for scope in ir['scopes'] for row in scope['signals'].values()})
   values='std::vector<V>{'+','.join('s.get('+str(i)+')' for i in ids)+'}'
   probe='s.run_until(500);auto cp=s.checkpoint();s.run();auto final='+values+';auto steps=s.executed_steps();s.restore(cp);s.restore(cp);s.run();auto again='+values+';if(s.executed_steps()!=steps)throw std::runtime_error("checkpoint steps");for(size_t i=0;i<final.size();++i)if(!final[i].same(again[i]))throw std::runtime_error("checkpoint final state");'
   cpp=work/'checkpoint.cpp';cpp.write_text(code.replace('\ns.run();\n',probe))
   run([cxx,'-std=c++17','-O2','-pthread',*flags,'-I'+cache['DSIM_ZSTD_INCLUDE'],cpp,cache['DSIM_ZSTD_LIBRARY'],'-o',work/'checkpoint'],work,'checkpoint-compile')
   text=run([work/'checkpoint'],work,'checkpoint-run')
   assert text.splitlines()==wanted+wanted,text
   report.update(checkpoint_restores=2)
  report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),trace=wanted,parallel_partitions=ir['parallel']['partitions'])
  print('PASS modport prototypes',name,flush=True)
 api='interface bus;integer value=0;task automatic put(input integer x);#1;value=x;endtask function automatic integer get(input integer n=2);return value+n;endfunction modport client(import put,get,input value);modport ro(input value);endinterface '
 negatives={
  'hidden':(api+'module c(bus.ro b);initial b.put(1);endmodule module top;bus x();c u(x);endmodule','not visible via modport'),
  'signal_call':(api+'module top;bus x();initial x.value();endmodule','not a subroutine'),
  'import_signal':('interface bus;integer value;modport bad(import value);endinterface module top;bus x();endmodule','unknown subroutine'),
  'import_unknown':('interface bus;modport bad(import missing);endinterface module top;bus x();endmodule','unknown subroutine'),
  'direction_subroutine':('interface bus;function integer get();return 1;endfunction modport bad(input get);endinterface module top;bus x();endmodule','unknown signal'),
  'duplicate':('interface bus;task t();begin end endtask modport bad(import t,t);endinterface module top;bus x();endmodule','duplicate modport member'),
  'missing_argument':(api+'module top;bus x();initial x.put();endmodule','missing subroutine argument'),
  'unknown_argument':(api+'module top;bus x();initial x.put(.z(1));endmodule','unknown subroutine argument'),
  'duplicate_argument':(api+'module top;bus x();initial x.put(.x(1),.x(2));endmodule','duplicate subroutine argument'),
  'too_many':(api+'module top;bus x();initial x.put(1,2);endmodule','too many subroutine arguments'),
  'task_expression':(api+'module top;bus x();integer q;initial q=x.put(1);endmodule','expression requires a function'),
  'module_call':('module leaf;function integer f();return 1;endfunction endmodule module top;leaf u();integer q;initial q=u.f();endmodule','hierarchical module task/function'),
  'function_timing':('interface bus;function integer f();#1;return 1;endfunction endinterface module top;bus x();integer q;initial q=x.f();endmodule','zero-time'),
  'function_task':(api+'module top;bus x();function integer f();x.put(1);return 1;endfunction integer q;initial q=f();endmodule','zero-time'),
  'void_expression':('interface bus;function void f();begin end endfunction endinterface module top;bus x();integer q;initial q=x.f();endmodule','void function has no value'),
  'output_constant':('interface bus;task t(output integer n);n=1;endtask endinterface module top;bus x();initial x.t(1);endmodule','assignment target'),
  'ref_constant':('interface bus;function automatic integer f(ref integer n);return n;endfunction endinterface module top;bus x();integer q;initial q=x.f(1);endmodule','ref requires a whole variable'),
  'readonly_copyout':('interface bus;integer value;task t(output integer n);n=1;endtask modport ro(import t,input value);endinterface module c(bus.ro b);initial b.t(b.value);endmodule module top;bus x();c u(x);endmodule','cannot write input'),
  'recursive_task':('interface bus;task t();t();endtask endinterface module top;bus x();initial x.t();endmodule',''),
  'prototype_missing_body':('interface bus;modport c(import task t(input integer n));endinterface module user(bus.c b);initial b.t(1);endmodule module top;bus x();user u(x);endmodule','not a subroutine'),
  'export':('interface bus;task t();begin end endtask modport c(export t);endinterface module top;bus x();endmodule','syntax error'),
 }
 # Signature mismatches must fail even when the imported method is unused.
 def declaration(actual,prototype,extra=''):
  return 'interface bus;'+extra+actual+' modport c(import '+prototype+');endinterface module top;bus x();endmodule'
 signatures={
  'kind':('task t(input integer n);begin end endtask','function integer t(input integer n)'),
  'return_width':('function integer t();return 1;endfunction','function byte t()'),
  'return_signed':('function logic signed[7:0] t();return 1;endfunction','function logic[7:0] t()'),
  'return_void':('function void t();begin end endfunction','function integer t()'),
  'return_state':('function bit[7:0] t();return 1;endfunction','function logic[7:0] t()'),
  'count':('task t(input integer n);begin end endtask','task t()'),
  'direction':('task t(output integer n);n=1;endtask','task t(input integer n)'),
  'ref':('task automatic t(ref integer n);n=1;endtask','task t(input integer n)'),
  'width':('task t(input integer n);begin end endtask','task t(input byte n)'),
  'signed':('task t(input logic signed[7:0] n);begin end endtask','task t(input logic[7:0] n)'),
  'state':('task t(input bit[7:0] n);begin end endtask','task t(input logic[7:0] n)'),
  'string':('task t(input string n);begin end endtask','task t(input integer n)'),
  'bounds':('task t(input integer n[0:1]);begin end endtask','task t(input integer n[1:3])'),
  'rank':('task t(input integer n[0:1][0:1]);begin end endtask','task t(input integer n[0:3])'),
  'dynamic':('task t(input integer n[]);begin end endtask','task t(input integer n[0:1])'),
  'default':('function integer t(input integer n=2);return n;endfunction','function integer t(input integer n)'),
 }
 for name,(actual,prototype) in signatures.items():negatives['signature_'+name]=(declaration(actual,prototype),'modport prototype mismatch')
 for name,types in [('enum','typedef enum logic[1:0]{A=0} T;typedef enum logic[1:0]{B=0} U;'),('struct','typedef struct packed{logic[3:0] v;} T;typedef struct packed{bit[3:0] v;} U;')]:
  negatives['signature_'+name]=(declaration('function T t();return 0;endfunction','function U t()',types),'modport prototype mismatch')
 negatives['prototype_duplicate']=(declaration('task t();begin end endtask','task t(),task t()'),'duplicate modport member')
 negatives['prototype_hidden']=(api.replace('modport client(import put,get,input value);','modport client(import task put(input integer x),input value);')+'module user(bus.client b);integer n;initial n=b.get();endmodule module top;bus x();user u(x);endmodule','not visible via modport')
 negatives['prototype_named_formal']=(declaration('function integer t(input integer original);return original;endfunction','function integer t(input integer renamed)').replace('module top;bus x();endmodule','module user(bus.c b);integer n;initial n=b.t(.renamed(1));endmodule module top;bus x();user u(x);endmodule'),'unknown subroutine argument')
 negatives['prototype_no_import']=('interface bus;task t();begin end endtask modport c(input value,task t());integer value;endinterface module top;bus x();endmodule','requires import')
 negatives['prototype_lifetime']=(declaration('function automatic integer t();return 1;endfunction','function automatic integer t()'),'cannot declare a lifetime')
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.write_text('keep original output')
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  error=(out/(name+'.stderr')).read_text();assert 'dsim:' in error and diagnostic in error,(name,error)
  assert dest.read_text()=='keep original output',name
 report.update(status='PASS',negative_cases=len(negatives),independent_oracle='explicit fixture numeric/string/timing checks; parallel final values and zero errors')
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
