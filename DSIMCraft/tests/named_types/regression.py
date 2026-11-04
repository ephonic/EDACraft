"""Named integral types, scope binding and runtime semantics."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/named_types'
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
negative={
 'unknown_base':('typedef missing_t alias_t;','unknown integral type'),
 'unknown_variable':('missing_t q;','unknown integral type'),
 'duplicate':('typedef int t;typedef byte t;','duplicate type or symbol'),
 'value_collision':('int t;typedef byte t;','duplicate type or symbol'),
 'value_use':('typedef int t;initial $display(t);','type name is not a value'),
 'value_dimension':('typedef int t;logic [t:0] q;','type name is not a value'),
 'type_lvalue':('typedef int t;initial t=1;','type name is not a value'),
 'cycle':('typedef t t;','unknown integral type'),
 'overwide':('typedef logic [1048576:0] t;','typedef packed range'),
 'runtime_bound':('int n=7;typedef logic[n:0] t;','typedef bounds'),
 'unknown_bound':("typedef logic[8'hx:0] t;",'typedef bounds'),
 'high_bound':("typedef logic[64'h100000007:0] t;",'typedef bounds'),
 'real_bound':('typedef logic[2.5:0] t;','typedef bounds'),
 'single_bound':('typedef logic[7] t;','typedef packed range requires'),
 'unpacked_alias':('typedef byte t[0:1];',''),
 'extra_packed':('typedef bit [7:0] a;typedef a [1:0] b;',''),
 'type_parameter':('parameter type t=byte;',''),
 'out_of_scope':('initial begin: local_scope typedef byte t;t x;end t q;','unknown integral type'),
 'enum_member_range':('typedef enum {A[2]} t;',''),
 'dynamic_cast':('int q;initial $cast(q,1);','unsupported system task'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+'endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
params=json.loads((out/'values/serial.json').read_text())['scopes'][0]['parameters']
expected_params={'A':(8,True,255),'B':(64,True,1<<32),'C':(13,False,0x501),
 'D':(130,False,1<<129),'E':(8,True,128),'G':(64,False,1<<32),'H':(1,False,0)}
for name,(width,sign,value) in expected_params.items():
 p=params[name];assert (p['width'],p['signed'],p['bits'])==(width,sign,format(value,'0'+str(width)+'b')),(name,p)
assert params['I']['bits']=='z' and params['I']['width']==1
assert params['F']['bits']=='xxxxzzzz00000000xxxxzzzz00000001' and params['F']['signed']
signals=json.loads((out/'values/serial.json').read_text())['scopes'][0]['signals']
for name,width,sign,two in [('a',8,True,False),('c',8,True,False),('u',13,False,True),('w',130,False,False),('by',8,True,True),('sh',16,True,True),('iv',32,True,True),('lv',64,True,True),('tv',64,False,False)]:
 p=signals[name];assert (p['width'],p['signed'],p['two_state'])==(width,sign,two),(name,p)
assert not any(name.endswith('_t') for name in signals),'type definitions allocated runtime storage'
hier=timeline(*read(out/'hierarchy/serial-settled.vcd'))
for instance,width in [('u',8),('v',13)]:
 for g in range(2):
  bits=width+g
  assert hier[('top',instance,'gen['+str(g)+']','x')][2]==[(0,((1<<bits)-1,0)),(1000,(0x501&((1<<bits)-1),0))]
values=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal in ['ea','eb']:assert values[('top',signal)][2]==[(0,(0,0))],signal
for name in ['values','effects','scopes']:
 assert 'DSIM error:' not in (out/name/'serial-run.stdout').read_text(),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parameters=9,independent_signal_types=9,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS named types:',captures,'captures, 2 rollback models,',len(negative),'rejections and independent type/value/parallel oracles')
