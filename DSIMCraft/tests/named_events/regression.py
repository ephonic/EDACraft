"""Named event occurrences, persistent queries, NBA triggers and process suspension."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/named_events'
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
 if name in ['handshake','nba_delay']:
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

negative={
 'array':('module top;event e[0:1];endmodule','event arrays'),
 'packed':('module top;event [1:0]e;endmodule',''),
 'alias':('module top;event a,b=a;endmodule','aliases/initializers'),
 'automatic_array':('module top;task automatic t();event e[2];endtask initial t();endmodule','event arrays'),
 'trigger_variable':('module top;logic e;initial ->e;endmodule','static scalar event'),
 'edge':('module top;event e;initial @(posedge e);endmodule','edge qualifiers'),
 'value':('module top;event e;integer q;initial q=e;endmodule','event handles'),
 'assign':('module top;event e;initial e=1;endmodule','event handles'),
 'select':('module top;event e;logic q;initial q=e[0];endmodule','event handles'),
 'method':('module top;event e;initial wait(e.unknown);endmodule','only triggered'),
 'arguments':('module top;event e;initial wait(e.triggered(1));endmodule','without arguments'),
 'parentheses':('module top;event e;initial wait(e.triggered());endmodule','without arguments'),
 'query_select':('module top;event e;logic q;initial q=e.triggered[0];endmodule','select of triggered query'),
 'query_assign':('module top;event e;initial e.triggered=1;endmodule','event handles'),
 'event_control_trigger':('module top;event a,b;initial ->> @a b;endmodule',''),
 'wait_order':('module top;event a,b;initial wait_order();endmodule',''),
 'syntax':('module top;event e;initial ->> #(;endmodule',''),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 if diagnostic:assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for flag in ['ea','eb']:assert state[('top',flag)][2]==[(0,(0,0))]
for signal,step,period in [('a',3,3000),('b',7,4000)]:
 assert state[('top',signal)][2]==[(k*period,(k*step,0)) for k in range(5)],(signal,state[('top',signal)])
state=timeline(*read(out/'triggered/serial-settled.vcd'))
assert state[('top','instant')][2]==[(0,(0,0)),(1000,(2,0)),(2000,(3,0))]
for signal in ['changes','rises']:assert state[('top',signal)][2]==[(0,(0,0)),(1000,(1,0))]
state=timeline(*read(out/'nba_delay/serial-settled.vcd'))
assert state[('top','seen')][2]==[(0,(0,0)),(2000,(1,0)),(5000,(2,0))]
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),real_parallel_partitions=2),indent=2)+'\n')
print('PASS named events:',captures,'captures, 2 actual rollbacks,',len(negative),'rejections and two actual partitions')
