"""Detached control with static call slots, cancellation and frame boundaries."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/fork_control'
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
 if name in ['any','cancel','scopes']:
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

# Control edges keep children with their parent even with no shared variables.
joined=out/'fork-dependencies.json'
run([compiler,fixtures/'parallel.sv','--threads','8','--emit-only','--emit-ir',joined,'--emit-cpp',out/'fork-dependencies.cpp'],out,'fork-dependencies')
assert json.loads(joined.read_text())['parallel']['partitions']==2
negative={
 'function_wait':('module top;function automatic integer f();wait fork;f=1;endfunction initial $display("%d",f());endmodule','fork control is not allowed in functions'),
 'function_disable':('module top;function automatic integer f();disable fork;f=1;endfunction initial $display("%d",f());endmodule','fork control is not allowed in functions'),
 'comb_wait':('module top;logic q;always_comb begin wait fork;q=1;end endmodule','fork control is not allowed in always_comb'),
 'comb_disable':('module top;logic q;always_comb begin disable fork;q=1;end endmodule','fork control is not allowed in always_comb'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 if diagnostic:assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,period in [('a',1000),('b',2000)]:
 assert state[('top',signal)][2]==[(0,(0,0)),(period,(1,0)),(2*period,(2,0)),(3*period,(3,0))],(signal,state[('top',signal)])
for lane in ['u','v']:assert state[('top',lane,'bad')][2]==[(0,(0,0))]
state=timeline(*read(out/'cancel/serial-settled.vcd'))
assert state[('top','q')][2]==[(0,(0,0)),(1000,(1,0)),(2000,(2,0)),(3000,(3,0))]
assert state[('top','n')][2]==[(0,(0,0)),(5000,(11,0)),(6000,(12,0)),(7000,(13,0))]
assert state[('top','bad')][2]==[(0,(0,0))]
# M54 supplies independent compiled activations for these static-storage cases.
overlap={
 'direct':'module top;integer k=0;initial begin for(k=0;k<3;k++)fork #3;join_none wait fork;end endmodule',
 'descendant':'module top;integer k=0;initial begin for(k=0;k<2;k++)begin fork begin fork #5;join_none end join wait fork;end end endmodule',
}
for name,source in overlap.items():
 path=out/('overlap-'+name+'.sv');path.write_text(source+'\n');exe=out/('overlap-'+name)
 run([compiler,path,'--emit-cpp',out/('overlap-'+name+'.cpp'),'-o',exe],out,'overlap-'+name+'-compile')
 run([exe],out,'overlap-'+name+'-run')
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),runtime_overlap_rejections=0,overlap_cases=len(overlap),real_parallel_partitions=2),indent=2)+'\n')
print('PASS fork control:',captures,'captures, 3 actual rollbacks,',len(negative),'rejections and two actual partitions')
