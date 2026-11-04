"""Explicit integer and size casts, constant contexts and runtime side effects."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/explicit_casts'
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
 if name in ['values','effects']:
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
# Unsupported types and invalid widths must never turn into identity casts.
negative={
 'zero':("module top;initial $display(0'(1));endmodule",'cast width must be'),
 'negative':("module top;initial $display((-1)'(1));endmodule",'cast width must be'),
 'small_negative':("module top;initial $display(1'sb1'(1));endmodule",'cast width must be'),
 'unknown':("module top;initial $display(4'bx'(1));endmodule",'cast width must be'),
 'overwide':("module top;initial $display(1048577'(1));endmodule",'cast width must be'),
 'highword':("module top;initial $display(64'h100000001'(1));endmodule",'cast width must be'),
 'runtime':("module top;int n=8;initial $display(n'(1));endmodule",'cast width must be'),
 'real_width':("module top;initial $display(2.5'(1));endmodule",''),
 'unknown_type':("module top;initial $display(missing_type'(1));endmodule",''),
 'qualified_type':("module top;initial $display(int unsigned'(1));endmodule",''),
 'dynamic_cast':('module top;int n;initial $cast(n,1);endmodule','unsupported system task'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
# Independent width/value/sign expectations, not derived from the generated model.
params=json.loads((out/'constants/serial.json').read_text())['scopes'][0]['parameters']
expected_params={'A':(64,True,1<<32),'B':(8,False,255),'C':(14,True,(1<<14)-1),
 'D':(32,True,133),'F':(130,True,(1<<130)-128),'G':(4,False,1),
 'H':(8,True,255),'I':(32,False,(1<<32)-1),'J':(8,True,255),
 'K':(64,True,(1<<64)-1),'L':(1,False,1),'M':(1,False,0),'N':(8,False,255),'O':(16,False,255)}
for name,(width,sign,value) in expected_params.items():
 p=params[name];assert (p['width'],p['signed'],p['bits'])==(width,sign,format(value,'0'+str(width)+'b')),(name,p)
assert params['E']['bits']=='0'*24+'1xz001z1'
values=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal in ['ea','eb']:assert values[('top',signal)][2]==[(0,(0,0))],signal
for name in ['values','effects']:
 assert 'DSIM error:' not in (out/name/'serial-run.stdout').read_text(),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parameters=15,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS explicit casts:',captures,'captures, 2 rollback models,',len(negative),'rejections and independent constant/parallel oracles')
