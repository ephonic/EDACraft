"""Function outputs, external effects and statement calls."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/function_effects'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,"process crashed",p.returncode,p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

expected=json.loads((fixtures/'expected.json').read_text())
captures=0
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  if name=='copy':assert (work/(backend+'-compile.stderr')).read_text().count('function return value discarded')==1
  trace=run([work/backend],work,backend+'-run');assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name in ['parallel','shared']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name=='parallel' else 1)) in (work/'stats.stderr').read_text()
 if name in ['effects']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(dest)==references['ordered'];captures+=1

negative={
 'malformed_ports':('function void f(,);begin end endfunction','syntax error'),
 'void_value':('function void f();begin end endfunction integer q;initial q=f();','void function has no value'),
 'void_arithmetic':('function void f();begin end endfunction integer q;initial q=f()+1;','void function has no value'),
 'void_return_value':('function void f();begin return 1;end endfunction initial f();','void functions cannot return a value'),
 'void_return_assignment':('function void f();begin f=1;end endfunction initial f();','void function has no value'),
 'void_bits':('function void f();begin end endfunction integer q;initial q=$bits(f());','unsupported array query operand'),
 'void_dimensions':('function void f();begin end endfunction integer q;initial q=$dimensions(f());','unsupported array query operand'),
 'void_discard_value':("initial void'(1+2);",'void discard requires a function call'),
 'void_discard_task':("task t();begin end endtask initial void'(t());",'void discard requires a function call'),
 'output_constant':('function integer f(output integer x);begin x=1;return 2;end endfunction integer q;initial q=f(1);','assignment target'),
 'output_expression':('integer x;function integer f(output integer y);begin y=1;return 2;end endfunction integer q;initial q=f(x+1);','assignment target'),
 'continuous_output':('integer x;function integer f(output integer y);begin y=1;return 2;end endfunction wire[31:0] q=f(x);','requires a procedural expression'),
 'continuous_nested':('integer x;function integer f(output integer y);begin y=1;return 2;end endfunction wire[31:0] q=1+f(x);','requires a procedural expression'),
 'module_actual_output':('integer x;function integer f(output integer y);begin y=1;return 2;end endfunction child u(f(x));','requires a procedural expression'),
 'enum_input':('typedef enum logic[1:0]{A,B}t;function t f(inout t x);begin return x;end endfunction t q;integer a;initial q=f(a);','enum assignment'),
 'enum_output':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;function t f(output t x);begin x=B;return B;end endfunction t q;u a;initial q=f(a);','enum assignment'),
 'void_delay':('function void f();begin #1;end endfunction initial f();','zero-time'),
 'void_nba':('integer x;function void f();begin x<=1;end endfunction initial f();','zero-time'),
 'void_task_call':('task t();begin end endtask function void f();begin t();end endfunction initial f();','zero-time'),
 'void_recursive':('function void f();begin f();end endfunction initial f();',''),
 'multiple_writers':('logic x;function void f();begin x=1;end endfunction always_comb f();always_comb x=0;','another writer'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module child(input wire[31:0] x);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
words=timeline(*read(out/'copy/serial-settled.vcd'))
for i,want in enumerate([[(0,(11,0)),(2000,(10,0))],[(0,(202,0)),(2000,(402,0))],[(0,(15,0))],[(0,(4,0)),(2000,(10,0))]]):
 assert words[('top','data['+str(i)+']')][2]==want,(i,words)
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,step,base in [('a',3000,3),('b',4000,17)]:
 wanted=[(0,(0,0))]+[(i*step,(base+i*3,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=1,negative_cases=len(negative),independent_parallel_lanes=2,shared_function_partitions=1),indent=2)+'\n')
print('PASS function effects:',captures,'captures, 1 rollback,',len(negative),'rejections and shared/independent partitions')
