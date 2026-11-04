"""Integral/vector system functions, type widths and runtime semantics."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/system_functions'
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
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
negative={}
for func in ['bits','clog2','isunknown','countones','onehot','onehot0']:
 for suffix,args in [('none',''),('many','1,2')]:
  negative[func+'_'+suffix]=(f'int q;initial q=${func}({args});','requires exactly one argument' if args else '')
 if func!='bits':negative[func+'_type']=(f'typedef logic[7:0] t;int q;initial q=${func}(t);','type name is not a value')
negative.update({
 'parameter_runtime':('int q;localparam P=$clog2(q);',''),
 'whole_array':('int a[0:1];int q;initial q=$countones(a);',''),
 'packed_atom':('int q;initial q=$bits(int[1:0]);','packed dimensions require'),
 'type_nonbits':('int q;initial q=$onehot(int);','only $bits and array queries accept a data type'),
 'runtime_type_range':('int n;int q;initial q=$bits(logic[n:0]);',''),
 'unknown_type_range':("int q;initial q=$bits(logic[4'bx:0]);",''),
 'real_bits':('int q;initial q=$bits(1.5);',''),
 'truncated_type_bound':("int q;initial q=$bits(logic[64'h100000003:0]);",'bound exceeds supported int range'),
 'truncated_part_width':("logic[7:0] q;int n;initial n=$bits(q[0+:64'h100000001]);",''),
 'overwide_type_range':('int q;initial q=$bits(logic[1048576:0]);','exceeds supported width'),
})
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)

# Independent output expectations for two true parallel partitions.
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,delay in [('a',2000),('b',3000)]:
 wanted=[(0,(0,0))]+[(i*delay,(101+((i-1).bit_length())*10,0)) for i in range(1,6)]
 wanted=[event for index,event in enumerate(wanted) if index==0 or event[1]!=wanted[index-1][1]]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
# Type names are compile-time symbols rather than runtime signals.
ir=json.loads((out/'constants/serial.json').read_text())
assert not any(k in scope['signals'] for scope in ir['scopes'] for k in ['word_t','packet_t','state_t'])
assert 'DSIM_VECTOR_SYSTEM_FUNCTIONS' in (out/'effects/serial.cpp').read_text()
wide=out/'wide';wide.mkdir(exist_ok=True)
run([compiler,fixtures/'wide-clog2.sv','--emit-cpp',wide/'model.cpp','-o',wide/'sim'],wide,'compile')
assert run([wide/'sim'],wide,'run').splitlines()==['TRACE before wide clog2','TRACE wide unknown xxxxxxxx','TRACE wide clog2 pass']
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=1,negative_cases=len(negative),four_state_vectors=256,native_wide_clog2=True,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS system functions:',captures,'captures, 1 rollback model,',len(negative),'rejections, 256 exhaustive vectors and two parallel lanes')
