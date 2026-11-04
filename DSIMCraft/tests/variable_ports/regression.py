"""Module output connections to variables and static prefix ownership."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/variable_ports'
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
 'blocking':('logic[7:0]v;c a(v);initial v=0;','variable port driver conflicts'),
 'nba':('logic[7:0]v;c a(v);initial v<=0;','variable port driver conflicts'),
 'initialization':('logic[7:0]v=0;c a(v);','declaration initialization'),
 'two_ports':('logic[7:0]v;c a(v),b(v);','variable port driver conflicts'),
 'overlap':('logic[11:0]v;c a(v[7:0]),b(v[11:4]);','variable port driver conflicts'),
 'dynamic_write':('logic[7:0]v;integer i;c a(v);initial begin i=0;v[i]=0;end','variable port driver conflicts'),
 'compound':('logic[7:0]v;c a(v);initial v+=1;','variable port driver conflicts'),
 'task_writeback':('logic[7:0]v;c a(v);task t(output logic[7:0]q);begin q=0;end endtask initial t(v);','variable port driver conflicts'),
 'function_effect':('logic[7:0]v;integer x;c a(v);function integer f();begin v=0;f=1;end endfunction initial x=f();','variable port driver conflicts'),
 'array_word':('logic[7:0]v[0:1];c a(v[1]);initial v[1]=0;','variable port driver conflicts'),
 'array_dynamic_write':('logic[7:0]v[0:1];integer i;c a(v[1]);initial begin i=0;v[i]=0;end','variable port driver conflicts'),
 'dynamic_output':('logic[15:0]v;integer i;c a(v[i+:8]);','variable selects in'),
 'out_of_range':('logic[7:0]v;c a(v[10+:8]);','variable selects in'),
 'input_variable_write':('logic v;bad a(v);','variable port driver conflicts'),
 'variable_inout':('logic v;io a(v);','equal-width net lvalues'),
 'array_inout':('arr a();','array inout ports are not supported'),
 'explicit_continuous_variable_conflict':('logic v;assign v=1;initial v=0;','variable port driver conflicts'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module c(output[7:0]y);assign y=8\'ha5;endmodule module bad(input bit d);initial d=0;endmodule module io(inout d);endmodule module arr(inout logic a[0:1]);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text()
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
state=timeline(*read(out/'parallel/serial-settled.vcd'))
for flag in ['ea','eb']:assert state[('top',flag)][2]==[(0,(0,0))]
for signal,step,delay in [('a',3,2000),('b',7,3000)]:
 assert state[('top',signal)][2]==[(i*delay,((i+1)*step,0)) for i in range(9)],(signal,state[('top',signal)])
# Keep the compact gate frontend separate: only its RTL port stub connects to
# the variables in these testbenches. Reuse independent four-state/FF oracles.
for name in ['four_state','seq_pipeline']:
 gate=ROOT/'tests/gate';work=out/('gate-'+name);work.mkdir(exist_ok=True)
 text=(gate/(name+'.tb.v')).read_text()
 if name=='four_state':text=text.replace('wire [7:0] y,y2','logic [7:0] y,y2')
 else:text=text.replace('wire [15:0] q,n; wire t,nt;','logic [15:0] q,n; logic t,nt;')
 source=work/'input.sv';source.write_text(text)
 library='sequential.lib' if name.startswith('seq_') else 'cells.lib'
 run([compiler,'--gate-netlist',gate/(name+'.net.v'),'--gate-top','dut','--liberty',gate/library,source,'--wave-support','--emit-cpp',work/'model.cpp','-o',work/'simv'],work,'compile')
 wave=work/'native.vcd';wave.unlink(missing_ok=True)
 result=run([work/'simv','--waveform',wave,'--wave-mode','settled'],work,'run')
 assert [line for line in result.splitlines() if line.startswith('TRACE')]==json.loads((gate/(name+'.expected.json')).read_text()),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),hybrid_gate_models=2,captures=captures,rollback_models=2,negative_cases=len(negative),real_parallel_partitions=2),indent=2)+'\n')
print('PASS variable ports:',captures,'captures, 2 rollbacks,',len(negative),'rejections and two actual partitions')
