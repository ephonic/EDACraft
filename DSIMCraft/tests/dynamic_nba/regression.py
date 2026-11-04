"""Dynamic element NBA regions, captured allocations, frame lifetime and rollback."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/dynamic_nba'
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
 if name in ['sample','targets','events','lifetime','control']:
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
for name in ['one','two']:
 assert state[('top',name)][2][-1][1]==(42,0),(name,state[('top',name)])
negative={'whole': ('integer a[];initial a<=new[2];', 'blocking assignment without timing control'), 'concat_net': ('logic[7:0] a[];wire q;initial begin a=new[1];{a[0],q}<=3;end', 'procedural assignment to a net'), 'const': ('integer a[];task automatic t(const ref integer x[]);x[0]<=1;endtask initial t(a);', 'cannot modify const ref'), 'event_auto_source': ('integer a[];task automatic t(input logic x);a[0]<=@(x)1;endtask initial begin a=new[1];t(0);end', 'automatic variables in pending NBA event controls'), 'event_auto_guard': ('integer a[];event e;task automatic t(input logic x);a[0]<=@(e iff x)1;endtask initial begin a=new[1];t(0);end', 'automatic variables in pending NBA event controls'), 'event_mutation': ('integer a[],i=0;initial begin a=new[1];a[0]<=@(i++)1;end', 'side effects'), 'comb_timing': ('integer a[];logic d;always_comb a[0]<=#1 d;', 'intra-assignment timing'), 'function_nba': ('integer a[],q=0;function automatic integer f();integer x[];x=new[1];x[0]<=1;return 1;endfunction initial @(f())q=1;', 'functions require zero-time blocking statements')}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
# A failed prediction before automatic task frames must restore all pending updates.
work=out/'lifetime';code=(work/'serial.cpp').read_text()
(work/'before.cpp').write_text(code.replace('\ns.run();\n','\nif(s.predict_until(1000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");\nif(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");\ns.run();\n'))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'before.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'before'],work,'before-compile')
dest=work/'before.dwf';dest.unlink(missing_ok=True)
assert run([work/'before','--waveform',dest,'--wave-mode','ordered'],work,'before-run')==(work/'serial-run.stdout').read_text()
assert streams(dest)==streams(work/'serial-ordered.dwf');captures+=1

# VCS W-2024.09 reports NYI for ref-port NBA. Verify this native extension separately.
refwork=out/'ref-native';refwork.mkdir(exist_ok=True)
for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
 run([compiler,fixtures/'native-only/ref.sv',*flags,'--emit-cpp',refwork/(backend+'.cpp'),'-o',refwork/backend],refwork,backend+'-compile')
 trace=run([refwork/backend],refwork,backend+'-run')
 assert [x for x in trace.splitlines() if x.startswith('TRACE')]==['TRACE native ref 30 1']

for name in ['bounds','unknown','negative']:
 work=out/('runtime-'+name);work.mkdir(exist_ok=True)
 run([compiler,fixtures/'runtime-errors'/(name+'.sv'),'--emit-cpp',work/'model.cpp','-o',work/'model'],work,'compile')
 run([work/'model'],work,'runtime',False)
 assert 'nonblocking dynamic array index is unknown or out of range' in (work/'runtime.stderr').read_text()

# Preserve the measured index-function evaluation difference as a separate probe.
work=out/'function-index-native';work.mkdir(exist_ok=True)
run([compiler,fixtures/'native-only/function-index.sv','--emit-cpp',work/'model.cpp','-o',work/'model'],work,'compile')
trace=run([work/'model'],work,'runtime')
assert [x for x in trace.splitlines() if x.startswith('TRACE')]==['TRACE sample 7 20 1 0 9 9 99 fffffffffffffffffffffffd 73']
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,failed_predictions=7,restore_before_allocation=['control','lifetime'],bounded_calls=12,negative_cases=len(negative),real_parallel_partitions=2,native_only_ref_backends=3,runtime_errors=3),indent=2)+'\n')
print('PASS dynamic element NBA:',captures,'captures, 7 failed predictions, bounded storage and two partitions')
