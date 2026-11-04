"""Unpacked aggregate storage state across assignments, calls and schedulers."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/unpacked_state'
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
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
  trace=run([work/backend],work,backend+'-run');assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt in ['vcd','dwf']:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format',fmt],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);captures+=1
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
 checkpoint=1000 if name in ['timing','parallel'] else 0
 (work/'replay.cpp').write_text(code.replace('\ns.run();\n',f'''
s.run_until({checkpoint});
if(s.predict_until(30000,[](Sim&){{}},[](const Sim&){{return false;}},[](Sim&){{}}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
 run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
 dest=work/'replay.dwf';dest.unlink(missing_ok=True)
 assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
 assert streams(dest)==references['ordered'];captures+=1
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for name,wanted in [('ea',0),('eb',0),('a',2),('b',0x21)]:
 assert state[('top',name)][2][-1][1]==(wanted,0),(name,state[('top',name)])
for lane in ['u','v']:
 assert state[('top',lane,'count')][2][-1][1]==(3,0),lane
# Ordinary packed designs do not include the mixed-state runtime path.
plain=out/'packed-control.sv'
plain.write_text("module top;typedef struct packed{bit[3:0]b;logic[3:0]l;}t;t q;initial begin q.b=4'bxz10;if(q!==8'bxz10xxxx)$fatal(1,\"packed storage\");$finish;end endmodule\n")
run([compiler,plain,'--emit-cpp',out/'packed-control.cpp','-o',out/'packed-control'],out,'packed-control-compile')
run([out/'packed-control'],out,'packed-control-run')
assert '#define DSIM_MIXED_STATE_ENABLED' not in (out/'packed-control.cpp').read_text()
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=len(expected),real_parallel_partitions=2,packed_fast_path_unchanged=True),indent=2)+'\n')
print('PASS unpacked state:',captures,'captures,',len(expected),'rollback models, 2 partitions and packed control')
