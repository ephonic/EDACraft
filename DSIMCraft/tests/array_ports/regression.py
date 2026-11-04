"""Static unpacked variable array ports and declaration-order mapping."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/array_ports'
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
  if backend=='parallel' and name in ['parallel']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name=='parallel' else 1)) in (work/'stats.stderr').read_text()
 if name in ['timing','types']:
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
 'width':('module c(input logic[3:0]a[0:1]);endmodule module top;logic[7:0]a[0:1];c u(a);endmodule','element width mismatch'),
 'size':('module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:2];c u(a);endmodule','dimension size mismatch'),
 'rank':('module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1];c u(a);endmodule','semantic analysis failed'),
 'subarray_rank':('module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1][0:1];c u(a[0]);endmodule','semantic analysis failed'),
 'dynamic':('module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1];integer i;c u(a[i]);endmodule','indices must be constant'),
 'unknown':("module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1];c u(a[1'bx]);endmodule",'indices must be constant'),
 'outside':('module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1];c u(a[3]);endmodule','indices must be constant'),
 'inout':('module top(inout logic[7:0]a[0:1]);endmodule','array inout ports'),
 'net_inout_variable':('module c(inout wire[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1];c u(a);endmodule','requires net array actual'),
 'initializer':("module top(input logic[7:0]a[0:1]='0);endmodule",'whole-array declaration initializers'),
 'output_procedure':('module c(output logic[7:0]a[0:1]);assign a[0]=1,a[1]=2;endmodule module top;logic[7:0]a[0:1];c u(a);initial a[1]=0;endmodule','variable port driver conflicts'),
 'two_outputs':('module c(output logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1];c u(a),v(a);endmodule','variable port driver conflicts'),
 'input_procedure':('module c(input logic[7:0]a[0:1]);initial a[1]=0;endmodule module top;logic[7:0]a[0:1];c u(a);endmodule','variable port driver conflicts'),
 'input_function':('module c(input logic[7:0]a[0:1]);integer x;function integer f();begin a[1]=0;return 1;end endfunction initial x=f();endmodule module top;logic[7:0]a[0:1];c u(a);endmodule','variable port driver conflicts'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for flag in ['ea','eb']:assert state[('top',flag)][2]==[(0,(0,0))]
for signal,step,delay,extra in [('a[0]',3,2000,0),('a[1]',3,2000,1),('b[3]',7,3000,0),('b[2]',7,3000,1)]:
 assert state[('top',signal)][2]==[(0,(255,255))]+[(i*delay+1000,((i+1)*step+extra,0)) for i in range(9)],(signal,state[('top',signal)])
# Two output subarrays and an unrelated procedural word remain independent.
path=out/'output-subarrays.sv';path.write_text("module c(output logic[7:0]a[0:1]);assign a[0]=1,a[1]=2;endmodule module top;logic[7:0]a[0:2][3:2];c u(a[0]),v(a[1]);initial begin a[2][2]=3;a[2][3]=4;#1;if(a[0][2]!==2||a[0][3]!==1||a[1][2]!==2||a[1][3]!==1||a[2][2]!==3||a[2][3]!==4)$fatal(1,\"subarrays\");$finish;end endmodule\n")
run([compiler,path,'--emit-cpp',out/'output-subarrays.cpp','-o',out/'output-subarrays'],out,'output-subarrays-compile')
assert 'DSIM fatal' not in run([out/'output-subarrays'],out,'output-subarrays-run')
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),output_subarray_models=1,real_parallel_partitions=2),indent=2)+'\n')
print('PASS array ports:',captures,'captures, 2 rollbacks,',len(negative),'rejections and two actual partitions')
