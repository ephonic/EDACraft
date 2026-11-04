"""Explicit continuous variable assignments, delayed delivery and ownership."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/variable_assign'
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
 if name in ['delay','types']:
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
 'blocking':("logic[7:0]v;assign v=8'ha5;initial v=0;",'variable port driver conflicts'),
 'nba':('logic[7:0]v;assign v=1;initial v<=0;','variable port driver conflicts'),
 'initialization':('logic[7:0]v=0;assign #2 v=1;','declaration initialization'),
 'two_assigns':('logic[7:0]v;assign v=1;assign v=2;','variable port driver conflicts'),
 'port':('logic[7:0]v;assign v=1;c a(v);','variable port driver conflicts'),
 'overlap':('logic[15:0]v;assign v[7:0]=1;assign #1 v[11:4]=2;','variable port driver conflicts'),
 'dynamic_write':('logic[7:0]v;integer i;assign v[7:4]=1;initial begin i=0;v[i]=0;end','variable port driver conflicts'),
 'function_effect':('logic[7:0]v;integer x;assign v=1;function integer f();begin v=0;f=1;end endfunction initial x=f();','variable port driver conflicts'),
 'array_word':('logic[7:0]v[0:1];assign v[1]=1;initial v[1]=0;','variable port driver conflicts'),
 'array_dynamic_write':('logic[7:0]v[0:1];integer i;assign v[1]=1;initial begin i=0;v[i]=0;end','variable port driver conflicts'),
 'dynamic_target':('logic[15:0]v;integer i;assign v[i+:8]=1;','variable selects in'),
 'array_dynamic_target':('logic[7:0]v[0:1];integer i;assign #2 v[i]=1;','variable selects in'),
 'two_delays':('logic v;assign #(1,2) v=1;','require a single delay'),
 'three_delays':('logic v;assign #(1,2,3) v=1;','require a single delay'),
 'zero_two_delays':('logic v;assign #(0,0) v=1;','require a single delay'),
 'mixed_two_delays':('logic v;wire n;assign #(1,2) {n,v}=1;','require a single delay'),
 'enum_type':('typedef enum logic[1:0]{A=1,B=2} T;T v;assign v=1;','enum'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module c(output[7:0]y);assign y=8\'ha5;endmodule module bad(input bit d);initial d=0;endmodule module io(inout d);endmodule module arr(input logic a[0:1]);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text()
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for flag in ['ea','eb']:assert state[('top',flag)][2]==[(0,(0,0))]
for signal,step,delay in [('a',3,2000),('b',7,3000)]:
 assert state[('top',signal)][2]==[(0,(255,255))]+[(i*delay+1000,((i+1)*step,0)) for i in range(9)],(signal,state[('top',signal)])

# Independent interval oracle: all pairs of four-bit static ranges and mixed
# procedural/continuous writers. Same-statement repeated parts are legal.
oracle_cases=0
for procedural in [False,True]:
 for lo in range(8):
  for other in range(8):
   valid=lo+4<=other or other+4<=lo
   source=f"module top;logic[15:0]v;assign v[{lo}+:4]=1;"+(f"initial v[{other}+:4]=2;" if procedural else f"assign v[{other}+:4]=2;")+"endmodule\n"
   path=out/'ownership.sv';path.write_text(source)
   run([compiler,path,'--emit-only','--emit-cpp',out/'ownership.cpp'],out,'ownership',valid);oracle_cases+=1
path=out/'many-parts.sv';path.write_text("module top;logic[4095:0]v;"+''.join(f"assign v[{i}]=1'b0;" for i in range(4096))+"endmodule\n")
run([compiler,path,'--emit-only','--emit-cpp',out/'many-parts.cpp'],out,'many-parts')
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),ownership_oracle_cases=oracle_cases,disjoint_assignments=4096,real_parallel_partitions=2),indent=2)+'\n')
print('PASS variable assign:',captures,'captures, 2 rollbacks,',len(negative),'rejections,',oracle_cases,'ownership cases and two actual partitions')
