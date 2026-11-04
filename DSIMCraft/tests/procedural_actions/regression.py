"""Compound assignment and subroutine return through the actual compiled simulator."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/procedural_actions'
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
  trace=run([work/backend],work,backend+'-run');assert trace.splitlines()==wanted,(name,backend,trace)
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
  for signal,base in [('a',3),('b',17)]:
   expected_values=[(0,(0,0))]+[((i+2)*1000,(base+i*3,0)) for i in range(5)]
   assert values[('top',signal)][2]==expected_values,(signal,values[('top',signal)],expected_values)
 if name=='targets':
  values=timeline(*read(work/'serial-settled.vcd'))
  assert values[('top','words[0]')][2]==[(0,(255,0)),(1000,(256,0))]
  assert values[('top','words[1]')][2]==[(0,(0x1234,0)),(1000,(0x1235,0)),(2000,(0x1355,0))]
  assert values[('top','words[2]')][2]==[(0,(0xffff,0))]
 if name in ['targets','returns']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run').splitlines()==wanted
  assert streams(dest)==references['ordered'];captures+=1
# Compile-time boundaries and lexical visibility must fail explicitly.
negative={
 'return_initial':('module top;initial return;endmodule','return requires'),
 'return_loop':('module top;initial for(int i=0;i<3;i+=1)return i;endmodule','return requires'),
 'task_return_value':('module top;task t;begin return 3;end endtask initial t();endmodule','tasks cannot return a value'),
 'compound_net':('module top;wire [7:0] a;initial a+=1;endmodule','procedural assignment to a net'),
 'compound_constant':('module top;initial 1+=2;endmodule','assignment target'),
 'compound_expression':('module top;integer a=1,b;initial b=(a+=1);endmodule',''),
 'compound_delay':('module top;integer a=1;initial a+=#1 2;endmodule',''),
 'compound_dynamic_width':('module top;reg[15:0]a;integer w=4;initial a[0+:w]+=1;endmodule','width must be'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
print('PASS',len(negative),'unsupported or invalid procedural action diagnostics')

(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_updated_words=3,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS procedural actions:',captures,'captures, 2 rollback models,',len(negative),'diagnostics')
