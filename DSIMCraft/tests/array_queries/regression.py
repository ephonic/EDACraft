"""Static array queries and multi-control four-state bit counting."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/array_queries'
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
 if name in ['effects']:
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
native=out/'native-constants';native.mkdir(exist_ok=True)
run([compiler,fixtures/'native_constants.sv','--wave-support','--emit-cpp',native/'model.cpp','-o',native/'sim'],native,'compile')
assert run([native/'sim'],native,'run').splitlines()==expected['constants']

boundary=out/'native-boundaries';boundary.mkdir(exist_ok=True)
run([compiler,fixtures/'native_boundaries.sv','--wave-support','--emit-cpp',boundary/'model.cpp','-o',boundary/'sim'],boundary,'compile')
assert run([boundary/'sim'],boundary,'run').splitlines()==['TRACE native scalar and wide boundary pass']

negative={
 'countbits_none':('int q;initial q=$countbits();',''),
 'countbits_value_only':('int q;initial q=$countbits(1);','at least one control bit'),
 'countbits_type':('typedef logic[7:0] t;int q;initial q=$countbits(t,1);','type name is not a value'),
 'countbits_array':('int a[0:2];int q;initial q=$countbits(a,1);','unpacked array requires'),
 'countbits_array_control':('int a[0:2];int q;initial q=$countbits(1,a);','unpacked array requires'),
 'countbits_runtime_parameter':('int a;localparam C=$countbits(a,1);',''),
 'query_runtime_parameter':('int a[0:2];int d;localparam C=$size(a,d);',''),
 'dimension_type':('typedef logic[7:0] t;int a[0:2];int q;initial q=$size(a,t);','type name is not a value'),
 'query_real':('int q;initial q=$size(1.5);',''),
 'query_string':('int q;initial q=$size("abc");','unsupported array query operand'),
 'query_real_dimension':('int a[0:2];int q;initial q=$size(a,1.5);',''),
 'type_packed_atom':('int q;initial q=$size(int[2:0]);','packed dimensions require'),
 'type_runtime_bound':('int n;int q;initial q=$size(logic[n:0]);','unsupported array query operand'),
 'type_unknown_bound':("int q;initial q=$left(logic[4'bx:0]);",'unsupported array query operand'),
 'type_truncated_bound':("int q;initial q=$left(logic[64'h100000001:0]);",'unsupported array query operand'),
 'type_oversized_range':('int q;initial q=$size(bit[1048576:0]);','unsupported array query operand'),
}
for func in ['dimensions','unpacked_dimensions','left','right','low','high','increment','size']:
 negative[func+'_none']=(f'int q;initial q=${func}();','')
 args='a,1' if func in ['dimensions','unpacked_dimensions'] else 'a,1,2'
 negative[func+'_many']=(f'int a[0:2];int q;initial q=${func}({args});','requires')
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)

lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,delay in [('a',2000),('b',3000)]:
 wanted=[(0,(0,0))]+[(i*delay,(152 if i%2 else 157,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
ir=json.loads((out/'constants/serial.json').read_text())
assert not any(k in scope['signals'] for scope in ir['scopes'] for k in ['word_t','scalar_t','singleton_t','state_t','packet_t','item_t'])
code=(out/'effects/serial.cpp').read_text()
assert 'count_bits(count_arg0,selected)' in code and 'auto dimension=' in code
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=1,negative_cases=len(negative),four_state_vectors=256,independent_parallel_lanes=2,native_constant_countbits=True),indent=2)+'\n')
print('PASS array queries/countbits:',captures,'captures, 1 rollback,',len(negative),'rejections, 256 exhaustive vectors and two parallel lanes')
