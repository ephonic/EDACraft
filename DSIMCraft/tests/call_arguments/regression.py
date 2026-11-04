"""Default, named and empty static subroutine arguments."""
from pathlib import Path
import os,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/call_arguments'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=float(os.environ.get("DSIM_TEST_COMMAND_TIMEOUT","180")))
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
  trace=run([work/backend],work,backend+'-run');assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name in ['parallel']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name=='parallel' else 1)) in (work/'stats.stderr').read_text()
 if name in ['effects','startup']:
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
 'mixed_module_ports':('integer a;child u(a,.x(a));','analysis failed'),
 'duplicate_module_ports':('integer a;child u(.x(a),.x(a));','analysis failed'),
 'unknown_name':('function integer f(input integer x=1);begin return x;end endfunction integer q;initial q=f(.y(2));','unknown subroutine argument'),
 'duplicate_name':('function integer f(input integer x=1);begin return x;end endfunction integer q;initial q=f(.x(2),.x(3));','duplicate subroutine argument'),
 'position_then_same_name':('function integer f(input integer x=1);begin return x;end endfunction integer q;initial q=f(2,.x(3));','duplicate subroutine argument'),
 'name_then_position':('function integer f(input integer x=1,input integer y=2);begin return x+y;end endfunction integer q;initial q=f(.x(3),4);','positional argument follows'),
 'too_many':('function integer f(input integer x=1);begin return x;end endfunction integer q;initial q=f(1,2);','too many subroutine arguments'),
 'required_omitted':('function integer f(input integer x,input integer y=2);begin return x+y;end endfunction integer q;initial q=f();','missing subroutine argument'),
 'required_empty':('function integer f(input integer x,input integer y=2);begin return x+y;end endfunction integer q;initial q=f(,2);','missing subroutine argument'),
 'required_named_empty':('function integer f(input integer x);begin return x;end endfunction integer q;initial q=f(.x());','missing subroutine argument'),
 'implicit_name':('integer x;function integer f(input integer x=1);begin return x;end endfunction integer q;initial q=f(.x);','require parentheses'),
 'classic_default':('function integer f;input integer x=1;begin return x;end endfunction integer q;initial q=f();','ANSI'),
 'output_default_constant':('function integer f(output integer x=1);begin x=2;return x;end endfunction integer q;initial q=f();','assignment target'),
 'inout_default_constant':('function integer f(inout integer x=1);begin x=2;return x;end endfunction integer q;initial q=f();','assignment target'),
 'output_default_expression':('integer a;function integer f(output integer x=a+1);begin x=2;return x;end endfunction integer q;initial q=f();','assignment target'),
 'continuous_default_output':('integer a;function integer f(output integer x=a);begin x=2;return x;end endfunction wire[31:0]q=f();','requires a procedural expression'),
 'enum_default':('typedef enum logic[1:0]{A,B} t;function t f(input t x=1);begin return x;end endfunction t q;initial q=f();','enum assignment'),
 'enum_named':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;function t f(input t x=A);begin return x;end endfunction t q;u x;initial q=f(.x(x));','enum assignment'),
 'task_missing':('task f(input integer x);begin end endtask initial f();','missing subroutine argument'),
 'task_unknown':('task f(input integer x=1);begin end endtask initial f(.y(2));','unknown subroutine argument'),
 'task_duplicate':('task f(input integer x=1);begin end endtask initial f(.x(2),.x(3));','duplicate subroutine argument'),
 'task_order':('task f(input integer x=1,input integer y=2);begin end endtask initial f(.x(2),3);','positional argument follows'),
 'task_output_default':('task f(output integer x=1);begin x=2;end endtask initial f();','assignment target'),
 'malformed_default':('function integer f(input integer x=);begin return x;end endfunction integer q;initial q=f();','syntax error'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module child(input wire[31:0] x);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,step,base in [('a',3000,3),('b',4000,17)]:
 wanted=[(0,(0,0))]+[(i*step,(base+i*3,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS call arguments:',captures,'captures, 2 rollbacks,',len(negative),'rejections and 2 independent partitions')
