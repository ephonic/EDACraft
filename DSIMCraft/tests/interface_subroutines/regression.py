"""Interface subroutine binding, copy/ref, lexical timing and transactions."""
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
  print('PASS interface subroutines',name,flush=True)
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
 for name,(text,diagnostic) in negatives.items():
  source=out/(name+'.sv');source.write_text(text+'\n');dest=out/(name+'.cpp');dest.write_text('keep original output')
  run([compiler,source,'--emit-only','--emit-cpp',dest],out,name,False)
  error=(out/(name+'.stderr')).read_text();assert 'dsim:' in error and diagnostic in error,(name,error)
  assert dest.read_text()=='keep original output',name
 report.update(status='PASS',negative_cases=len(negatives),independent_oracle='explicit fixture numeric/string/timing checks; parallel final values and zero errors')
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
