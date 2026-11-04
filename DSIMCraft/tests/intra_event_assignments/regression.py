"""Blocking intra-assignment event controls, saved RHS and repeated suspension."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/intra_event_assignments'
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
 if name in ['sample','targets','repetition']:
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
 'array':('module top;logic clk;integer a[0:1],b[0:1];initial a=@(posedge clk)b;endmodule','event controls on unpacked arrays'),
 'implicit':('module top;logic q,d;initial q=@*d;endmodule','implicit sensitivity'),
 'function':('module top;logic clk;function integer f();f=repeat(0)@(posedge clk)1;endfunction initial f();endmodule','timing controls'),
 'comb':('module top;logic clk,q,d;always_comb q=@(posedge clk)d;endmodule','intra-assignment timing'),
 'mutation':('module top;logic q;integer n;initial q=@(n++)1;endmodule','side effects'),
 'missing':('module top;logic q,clk;initial q=repeat()@(posedge clk)1;endmodule',''),
 'nested':('module top;logic q,clk;initial q=repeat(1)repeat(2)@(posedge clk)1;endmodule',''),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 if diagnostic:assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,period in [('a',1000),('b',2000)]:
 assert state[('top',signal)][2]==[(0,(0,0)),(2*period,(1,0)),(4*period,(3,0))],(signal,state[('top',signal)])
state=timeline(*read(out/'sample/serial-settled.vcd'))
assert state[('top','q')][2]==[(0,(0,0)),(3000,((1<<129)|5,0))]
assert state[('top','signed_q')][2]==[(0,(0,0)),(5000,((1<<130)-3,0))]
assert state[('top','clean')][2]==[(0,(0,0)),(6000,(145,0))]
assert state[('top','state')][2]==[(0,(0,0)),(7000,(1,0))]
state=timeline(*read(out/'targets/serial-settled.vcd'))
assert state[('top','q')][2]==[(0,(0,0)),(2000,(0xef00,0))]
for name,values in [('calls',[(2000,1),(4000,2),(6000,3)]),('stage',[(2000,1),(4000,2),(6000,3)]),('a',[(4000,3)]),('b',[(4000,64)])]:
 assert state[('top',name)][2]==[(0,(0,0))]+[(t,(v,0)) for t,v in values],name
state=timeline(*read(out/'repetition/serial-settled.vcd'))
assert state[('top','q')][2]==[(0,(0,0)),(3000,(77,0)),(7000,(88,0))]
assert state[('top','order')][2]==[(0,(12,0)),(3000,(122222,0)),(5000,(1222222,0))]
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),real_parallel_partitions=2),indent=2)+'\n')
print('PASS intra-assignment events:',captures,'captures, 3 actual rollbacks,',len(negative),'rejections and two actual partitions')
