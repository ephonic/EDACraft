"""Immediate assertion actions, diagnostics and four-state execution in compiled simulations."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/immediate_assertions'
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
 if name=='parallel':
  values=timeline(*read(work/'serial-settled.vcd'))
  for signal,base,delay in [('a',3,2000),('b',7,3000)]:
   wanted_values=[(i*delay,((i+1)*base,0)) for i in range(5)]
   assert values[('top',signal)][2]==wanted_values,(signal,values[('top',signal)],wanted_values)
 if name in ['defaults','hierarchy']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(dest)==references['ordered'];captures+=1
# Unsupported deferred/concurrent verification constructs and invalid action grammar.
negative={
 'deferred_zero':('module top;initial assert #0(1);endmodule',''),
 'deferred_final':('module top;initial assert final(1);endmodule',''),
 'concurrent_assert':('module top;reg c;assert property(@(posedge c)1);endmodule',''),
 'concurrent_cover':('module top;reg c;cover property(@(posedge c)1);endmodule',''),
 'property_declaration':('module top;property p;1;endproperty endmodule',''),
 'clocking_block':('module top;reg c;clocking cb @(posedge c);endclocking endmodule',''),
 'cover_else':('module top;initial cover(1)begin end else;endmodule',''),
 'null_pass_else':('module top;initial assert(1);else;endmodule',''),
 'dynamic_fatal_number':('module top;int n=1;initial $fatal(n,"bad");endmodule','$fatal finish number'),
 'class_declaration':('module top;class C;int i;endclass endmodule',''),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
# Fatal diagnostics must terminate execution; the trailing display must not run.
fatal_sources={
 'fatal_number':'$fatal(1,"fatal value %0d",7);',
 'fatal_default':'$fatal;',
 'assert_fatal':'failed:assert(0)else $fatal(2,"assertion failed");',
}
for name,body in fatal_sources.items():
 work=out/name;work.mkdir(exist_ok=True);source=work/(name+'.sv')
 source.write_text('module top;initial begin $display("TRACE before");'+body+'$display("TRACE after");end endmodule\n')
 run([compiler,source,'--emit-cpp',work/'model.cpp','-o',work/'simv'],work,'compile')
 text=run([work/'simv'],work,'run',False)
 assert 'TRACE before' in text and 'TRACE after' not in text and 'DSIM fatal:' in text,(name,text)
 assert '$fatal terminated simulation' in (work/'run.stderr').read_text()
# Check independent outputs, including the invisible failure arms in true parallel domains.
values=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,delay in [('ha',2000),('hb',3000)]:
 assert values[('top',signal)][2]==[(i*delay,(i,0)) for i in range(5)],(signal,values[('top',signal)])
for signal in ['ea','eb']:assert values[('top',signal)][2]==[(0,(0,0))],signal
for mode in ['serial','wheel','parallel']:
 text=(out/'defaults'/(mode+'-run.stdout')).read_text()
 assert text.count('DSIM error:')==3 and text.count('DSIM warning:')==1 and text.count('DSIM info:')==1,text
 assert 'top.a_bad:5' in text and 'assume failed at top:6' in text,text
values=timeline(*read(out/'actions/serial-settled.vcd'))
for name,value in [('passes',3),('fails',6),('hits',2),('checks',2)]:assert values[('top',name)][2]==[(0,(value,0))],(name,values[('top',name)])
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),fatal_models=len(fatal_sources),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS immediate assertions:',captures,'captures, 2 rollback models,',len(negative),'diagnostics, 3 fatal terminations and independent condition/parallel oracles')
