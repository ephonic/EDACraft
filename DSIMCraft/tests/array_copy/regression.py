"""Static unpacked array procedural copy, sampling and declaration-order mapping."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/array_copy'
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

expected=json.loads((fixtures/'expected.json').read_text());expected.update(json.loads((fixtures/'native-expected.json').read_text()))
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
  if backend=='parallel' and name in ['parallel','intra_parallel']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name in ['parallel','intra_parallel'] else 1)) in (work/'stats.stderr').read_text()
 if name in ['timing','effects','intra_delay']:
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
 'width':('module top;logic[7:0]a[0:1];logic[15:0]b[0:1];initial b=a;endmodule','compatible element types'),
 'signed':('module top;logic signed[7:0]a[0:1];logic[7:0]b[0:1];initial b=a;endmodule','compatible element types'),
 'enum':('module top;typedef enum logic[1:0]{A=0,B=1} e1;typedef enum logic[1:0]{C=0,D=1} e2;e1 a[0:1];e2 b[0:1];initial b=a;endmodule','compatible element types'),
 'rank':('module top;logic[7:0]a[0:3],b[0:1][0:1];initial b=a;endmodule','rank mismatch'),
 'size':('module top;logic[7:0]a[0:2],b[0:1];initial b=a;endmodule','dimension size mismatch'),
 'inner_size':('module top;logic[7:0]a[0:1][0:2],b[0:1][0:1];initial b=a;endmodule','dimension size mismatch'),
 'slice':('module top;logic[7:0]a[0:3],b[0:1];initial b=a[1:2];endmodule','array copy slices'),
 'dynamic_net_target':('module top;wire[7:0]a[0:1][0:1];logic[7:0]b[0:1];integer i;initial a[i]=b;endmodule','procedural assignment to a net'),
 'dynamic_automatic_nba':('module top;task automatic t;logic[7:0]a[0:1][0:1],b[0:1];integer i;a[i]<=b;endtask initial t();endmodule','automatic variable'),
 'automatic_nba':('module top;task automatic t;logic[7:0]a[0:1],b[0:1];b<=a;endtask initial t();endmodule','automatic variable'),
 'net_target':('module top;wire[7:0]a[0:1];logic[7:0]b[0:1];initial a=b;endmodule','procedural assignment to a net'),
 'scalar_target':('module top;logic[7:0]a[0:1],b;initial b=a;endmodule','matching unpacked'),
 'scalar_source':('module top;logic[7:0]a[0:1],b;initial a=b;endmodule','matching unpacked'),
 'continuous':('module top;logic[7:0]a[0:1],b[0:1];assign b=a;endmodule','requires an element index'),
 'multiple_comb':('module top;logic[7:0]a[0:1],b[0:1];always_comb b=a;initial b[0]=1;endmodule','has another writer'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for flag in ['ea','eb']:assert state[('top',flag)][2]==[(0,(0,0))]
for signal,step,delay,extra in [('a[0]',3,2000,0),('a[1]',3,2000,1),('b[3]',7,3000,0),('b[2]',7,3000,1)]:
 assert state[('top',signal)][2]==[(0,(255,255))]+[(i*delay+1000,((i+1)*step+extra,0)) for i in range(8)],(signal,state[('top',signal)])
state=timeline(*read(out/'timing/serial-settled.vcd'))
for n in range(2):assert state[('top','pipe['+str(n)+']')][2]==[(0,(255,255))]+[(t*1000,(v+n,0)) for t,v in [(2,10),(3,20),(4,30)]]
assert timeline(*read(out/'intra_parallel/serial-settled.vcd'))==timeline(*read(out/'parallel/serial-settled.vcd'))
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),real_parallel_partitions=2),indent=2)+'\n')
print('PASS array copy:',captures,'captures, 3 rollbacks,',len(negative),'rejections and two actual partitions')
