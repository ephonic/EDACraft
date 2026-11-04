"""Writable ref aliases, live events, element selection, cancellation and rollback."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/ref_arguments'
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
 if name in ['events','elements','control']:
  checkpoint_time=1000
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(CHECKPOINT_TICKS);
if(s.now!=CHECKPOINT_TICKS)throw std::runtime_error("activation checkpoint time missing");
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''.replace('CHECKPOINT_TICKS',str(checkpoint_time))))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(dest)==references['ordered'];captures+=1


# Repeated calls reuse variable storage after cancellation/return and scope exits.
code=(out/'control/serial.cpp').read_text()
(out/'control/bounded.cpp').write_text(code.replace('\ns.run();\n','\ns.run();\nif(s.processes.size()>20||s.signals.size()>100)throw std::runtime_error("unbounded activation storage");\n'))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],out/'control/bounded.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',out/'control/bounded'],out/'control','bounded-compile')
assert run([out/'control/bounded'],out/'control','bounded-run')==(out/'control/serial-run.stdout').read_text()
# A checkpoint before allocation must discard and regenerate runtime storage.
code=(out/'control/serial.cpp').read_text()
(out/'control/before.cpp').write_text(code.replace('\ns.run();\n','''\nif(s.predict_until(1000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],out/'control/before.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',out/'control/before'],out/'control','before-compile')
dest=out/'control/before.dwf';dest.unlink(missing_ok=True)
assert run([out/'control/before','--waveform',dest,'--wave-mode','ordered'],out/'control','before-run')==(out/'control/serial-run.stdout').read_text()
assert streams(dest)==streams(out/'control/serial-ordered.dwf');captures+=1
# Independent expected final values also guard the two partition outputs.
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for name in ['a','b']:
 assert state[('top',name)][2][-1][1]==(6,0),(name,state[('top',name)])
negative={
 'static':('integer x;task t(ref integer a);a++;endtask initial t(x);','ref formals require an automatic subroutine'),
 'literal':('task automatic t(ref integer a);a++;endtask initial t(3);','ref requires a whole variable'),
 'net':('wire [7:0] x;task automatic t(ref logic [7:0] a);a++;endtask initial t(x);','ref actual must be a variable'),
 'width':('logic [6:0] x;task automatic t(ref logic [7:0] a);a++;endtask initial t(x);','ref requires equivalent argument types'),
 'signed':('logic signed [7:0] x;task automatic t(ref logic [7:0] a);a++;endtask initial t(x);','ref requires equivalent argument types'),
 'state':('bit [7:0] x;task automatic t(ref logic [7:0] a);a++;endtask initial t(x);','ref requires equivalent argument types'),
 'atom':('logic signed [31:0] x;task automatic t(ref integer a);a++;endtask initial t(x);','ref requires equivalent argument types'),
 'part':('logic [7:0] x;task automatic t(ref logic [3:0] a);a++;endtask initial t(x[3:0]);','ref does not support packed bit/part selections'),
 'array':('integer x[2];task automatic t(ref integer a);a++;endtask initial t(x);','ref requires a whole variable'),
 'nba':('integer x;task automatic t(ref integer a);a<=1;endtask initial t(x);','automatic'),
 'const':('integer x;task automatic t(const ref integer a);a++;endtask initial t(x);','cannot modify const ref'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
# A failed prediction spanning all function aliases must release every guard.
work=out/'functions';code=(work/'serial.cpp').read_text()
(work/'before.cpp').write_text(code.replace('\ns.run();\n','\nif(s.predict_until(1000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");\ns.run();\n'))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'before.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'before'],work,'before-compile')
dest=work/'before.dwf';dest.unlink(missing_ok=True)
assert run([work/'before','--waveform',dest,'--wave-mode','ordered'],work,'before-run')==(work/'serial-run.stdout').read_text()
assert streams(dest)==streams(work/'serial-ordered.dwf');captures+=1
# Invalid dynamic element references are diagnosed before entering the task.
for name,index in [('unknown',"'x"),('outside','7')]:
 path=out/(name+'.sv');path.write_text('module top;integer words[2],index='+index+';task automatic t(ref integer a);a++;endtask initial t(words[index]);endmodule\n')
 run([compiler,path,'-o',out/name],out,name+'-compile')
 run([out/name],out,name+'-run',False)
 assert 'ref array index is unknown or out of range' in (out/(name+'-run.stderr')).read_text()
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,failed_predictions=5,restore_before_allocation=['control','functions'],bounded_calls=24,negative_cases=len(negative),invalid_runtime_indices=2,real_parallel_partitions=2),indent=2)+'\n')
print('PASS ref arguments:',captures,'captures, 5 failed predictions, bounded storage and two partitions')
