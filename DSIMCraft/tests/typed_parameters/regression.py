"""Typed parameter conversion and context sizing in actual compiled simulations."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/typed_parameters'
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
  for signal,base,delay in [('a',3,2000),('b',7,3000)]:
   wanted_values=[(i*delay,((i+1)*base,0)) for i in range(5)]
   assert values[('top',signal)][2]==wanted_values,(signal,values[('top',signal)],wanted_values)
 if name in ['overrides','generate']:
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
# Reject unsupported parameter categories and invalid override targets.
negative={
 'atom_range':('module top;parameter int[7:0]P=1;endmodule',''),
 'byte_range':('module top;localparam byte[7:0]P=1;endmodule',''),
 'time_range':('module top;parameter time[7:0]P=1;endmodule',''),
 'type_parameter':('module top #(parameter type T=int)();endmodule',''),
 'array_parameter':('module top;parameter int P[0:1]=1;endmodule',''),
 'local_override':('module child #(parameter int P=1)();localparam int Q=2;endmodule module top;child #(.Q(3))u();endmodule',''),
 'duplicate_override':('module child #(parameter int P=1)();endmodule module top;child #(.P(3),.P(4))u();endmodule',''),
 'runtime_parameter':('module top;int x;parameter int P=x;endmodule',''),
 'multiple_named_values':('module child #(parameter int P=1)();endmodule module top;child #(.P(3,4))u();endmodule',''),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
# Parameter IR must retain destination type semantics after cloning and overrides.
scopes={scope['path']:scope for scope in json.loads((out/'overrides/serial.json').read_text())['scopes']}
for path,pvalue,bvalue,lvalue in [('top.u',3,255,(1<<64)-1),('top.v',2,0,(1<<32)-1),('top.v2',(-7)&((1<<32)-1),128,(1<<64)-3)]:
 params=scopes[path]['parameters']
 for name,width,sign,value in [('P',32,True,pvalue),('B',8,True,bvalue),('L',64,False,lvalue)]:
  assert params[name]==dict(width=width,signed=sign,two_state=True,bits=format(value,'0'+str(width)+'b')),(path,name,params[name])
 assert params['MASK']['two_state'] and len(params['MASK']['bits'])==80
context=json.loads((out/'context/serial.json').read_text())['scopes']
assert int(context[2]['parameters']['P']['bits'],2)==(1<<32)+1
assert int(context[0]['parameters']['SUM']['bits'],2)==1<<32
assert int(context[0]['parameters']['SHIFT']['bits'],2)==1<<40
assert int(context[0]['parameters']['MIX']['bits'],2)==256
# Long division is independently checked using Python integers at 130 bits.
params=json.loads((out/'constant_ops/serial.json').read_text())['scopes'][0]['parameters']
big=int('3fedcba9876543210123456789abcdef01',16)&((1<<130)-1)
assert int(params['QUOT']['bits'],2)==big//257
assert int(params['REM']['bits'],2)==big%257
assert params['FOUR']['bits']=='x'*32 and params['ZERO']['bits']=='0'*64
assert params['ALL']['bits']=='0'*63+'1' and params['ANY']['bits']=='0'*64
assert params['ANDZ']['bits']==params['ORZ']['bits']=='0000000x'
assert params['NOTZ']['bits']=='1111111x' and params['MUXZ']['bits']=='1010010x'
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS typed parameters:',captures,'captures, 2 rollback models,',len(negative),'diagnostics and independent parameter/wide arithmetic oracles')
