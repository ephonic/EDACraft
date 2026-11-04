"""Automatic function event expressions and guards, dependencies and rollback."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/function_events'
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
  trace=run([work/backend],work,backend+'-run');assert 'DSIM fatal:' not in trace,(name,trace);assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    assert all('$activation' not in '.'.join(key) for key in state),(name,'automatic state exported')
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2)) in (work/'stats.stderr').read_text()
 if name in ['value','guard']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.now!=1000)throw std::runtime_error("activation checkpoint time missing");
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(dest)==references['ordered'];captures+=1

# More requested workers than domains: guard-only writers must still join
# their consumers, while the two lanes remain independent.
joined=out/'guard-dependencies.json'
run([compiler,fixtures/'parallel.sv','--threads','8','--emit-only','--emit-ir',joined,'--emit-cpp',out/'guard-dependencies.cpp'],out,'guard-dependencies')
assert json.loads(joined.read_text())['parallel']['partitions']==2
negative={
 'static':('module top;logic a;function logic f(input logic x);return x;endfunction initial @(f(a));endmodule','user function calls'),
 'external':('module top;logic a;integer count;function automatic logic f(input logic x);count++;return x;endfunction initial @(f(a));endmodule','side effects'),
 'output':('module top;logic a,b;function automatic logic f(input logic x,output logic y);y=x;return x;endfunction initial @(f(a,b));endmodule','side effects'),
 'nested':('module top;logic a;function logic inner(input logic x);return x;endfunction function automatic logic outer(input logic x);return inner(x);endfunction initial @(outer(a));endmodule','user function calls'),
 'argument':('module top;integer a;function automatic integer f(input integer x);return x;endfunction initial @(f(a++));endmodule','side effects'),
 'diagnostic':('module top;logic a;function automatic logic f(input logic x);assert(x);return x;endfunction initial @(f(a));endmodule','side effects'),
 'guard':('module top;logic a,g;integer count;function automatic logic f();count++;return g;endfunction initial @(posedge a iff f());endmodule','iff conditions with user function calls'),
 'void':('module top;logic a;function automatic void f(input logic x);return;endfunction initial @(f(a));endmodule','void function has no value'),
 'recursive':('module top;logic a;function automatic logic f(input logic x);return f(x);endfunction initial @(f(a));endmodule','effect-free automatic function activation'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,period in [('a',1000),('b',2000)]:
 assert state[('top',signal)][2]==[(0,(0,0)),(2*period,(1,0)),(4*period,(3,0))],(signal,state[('top',signal)])
state=timeline(*read(out/'value/serial-settled.vcd'))
assert state[('top','changes')][2]==[(0,(0,0)),(1000,(1,0)),(2000,(2,0)),(3000,(3,0)),(4000,(4,0)),(6000,(5,0)),(7000,(6,0)),(8000,(7,0))]
assert state[('top','rises')][2]==[(0,(0,0)),(1000,(1,0)),(6000,(2,0))]
state=timeline(*read(out/'guard/serial-settled.vcd'))
for n in ['clocks','edges']:assert state[('top',n)][2]==[(0,(0,0)),(2000,(1,0)),(8000,(2,0))]
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),real_parallel_partitions=2),indent=2)+'\n')
print('PASS function events:',captures,'captures, 2 actual rollbacks,',len(negative),'rejections and two actual partitions')
