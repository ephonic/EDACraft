"""Overlapping compiled fork activations, waits, cancellation and slot recycling."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/dynamic_fork'
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
 if name in ['any','events','nested']:
  checkpoint_time=3000 if name=='any' else 1000
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


# The process-slot pool grows to peak live concurrency, then reuses closures.
code=(out/'recycle/serial.cpp').read_text()
(out/'recycle/bounded.cpp').write_text(code.replace('\ns.run();\n','\ns.run();\nif(s.processes.size()>5)throw std::runtime_error("unbounded fork process pool");\n'))
run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],out/'recycle/bounded.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',out/'recycle/bounded'],out/'recycle','bounded-compile')
assert run([out/'recycle/bounded'],out/'recycle','bounded-run')==(out/'recycle/serial-run.stdout').read_text()
# Former automatic-parent/child boundaries are now positive execution cases.
for name,source,wanted in [
 ('auto_parent','module top;integer q=0;task automatic t();integer n=7;fork begin #1;q=n;end join_none endtask initial begin t();wait fork;if(q!=7)$fatal(1,"escape");end endmodule',''),
 ('auto_child','module top;integer k=0,q=0;task automatic work();integer saved=7;#1;q+=saved;endtask initial begin for(k=0;k<3;k++)fork work();join_none wait fork;if(q!=21)$fatal(1,"alias");end endmodule',''),
]:
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'-o',out/name],out,name+'-compile')
 assert run([out/name],out,name+'-run')==wanted
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,compile_rejections=0,runtime_rejections=0,bounded_recycle_activations=150,real_parallel_partitions=2),indent=2)+'\n')
print('PASS dynamic fork:',captures,'captures, 3 actual rollbacks, automatic frame upgrades and bounded process recycling')
