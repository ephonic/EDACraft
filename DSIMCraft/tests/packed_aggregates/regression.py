"""Packed aggregate layouts, bounded members and runtime semantics."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/packed_aggregates'
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
 if name=='parallel':
  values=timeline(*read(work/'serial-settled.vcd'))
  for signal,base,delay in [('a',3,2000),('b',7,3000)]:
   wanted_values=[(i*delay,((i+1)*base,0)) for i in range(5)]
   assert values[('top',signal)][2]==wanted_values,(signal,values[('top',signal)],wanted_values)
 if name in ['values','effects','storage_views']:
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
 'unknown_member':('typedef struct packed {bit a;} t;t q;initial q.missing=0;','unknown packed member'),
 'nonaggregate':('int q;initial q.a=0;','member base is not a packed aggregate'),
 'unequal_union':('typedef union packed {bit a;bit[1:0] b;} t;','packed union members must have equal widths'),
 'duplicate_field':('typedef struct packed {bit a;logic a;} t;',''),
 'initialized_field':('typedef struct packed {bit a=1;} t;','packed member must be a variable'),
 'unpacked_field':('typedef struct packed {bit a[0:1];} t;','packed member must be a variable'),
 'runtime_bound':('int n=7;typedef struct packed {bit[n:0] a;} t;','typedef bounds'),
 'unknown_bound':("typedef struct packed {bit[8'hx:0] a;} t;",'typedef bounds'),
 'single_bound':('typedef struct packed {bit[7] a;} t;','typedef packed range'),
 'overwide_total':('typedef struct packed {bit[524288:0] a,b;} t;','packed aggregate width'),
 'out_of_scope':('initial begin typedef struct packed {bit a;} t;end t q;','unknown integral type'),
 'enum_base':('typedef struct packed {bit a;} t;typedef enum t {A,B} e;','enum base must be'),
 'enum_integer':('typedef enum logic[1:0]{A,B} e;typedef struct packed {e a;} t;t q;initial q.a=0;','enum assignment requires'),
 'enum_other':('typedef enum logic[1:0]{A,B} e;typedef enum logic[1:0]{C,D} f;typedef struct packed {e a;} t;t q;initial q.a=C;','enum assignment requires'),
 'enum_delayed':('typedef enum logic[1:0]{A,B} e;typedef struct packed {e a;} t;t q;initial q.a<=#1 0;','enum assignment requires'),
 'enum_compound':('typedef enum logic[1:0]{A,B} e;typedef struct packed {e a;} t;t q;initial q.a+=1;','compound assignment to enum'),
 'untyped_parameter':('typedef struct packed {bit a;} t;localparam P=t\'(0);initial $display("%b",P.a);','member base is not a packed aggregate'),
 'inline_struct':('struct packed {bit a;} q;',''),
 'assignment_pattern':("typedef struct packed {bit a;} t;t q;initial q=t'{a:1};",''),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
# Native boundary checks are deliberately separate from the VCS-common cases.
native={
 'member-bounds':['TRACE wide select '+'x'*61+'0101','TRACE effects 1f3 456 354 99 4 1'],
 'enum-member-update':expected['values'],
 'implicit-ports':['TRACE implicit ports pass'],
}
for name,wanted in native.items():
 work=out/name;work.mkdir(exist_ok=True)
 source=fixtures/(name+'.sv')
 run([compiler,source,'-o',work/'sim','--emit-cpp',work/'model.cpp'],work,'compile')
 trace=run([work/'sim'],work,'run');assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,trace)
signals=json.loads((out/'values/serial.json').read_text())['scopes'][0]['signals']
for name,width,sign,two in [('s',8,False,False),('u',8,False,False),('w',130,False,True),('packet',8,False,False),('n',18,False,False),('signed_s',8,True,False)]:
 p=signals[name];assert (p['width'],p['signed'],p['two_state'])==(width,sign,two),(name,p)
assert not any(name in signals for name in ['mixed_t','view_t','b','l','state','data','tag'])
hier=timeline(*read(out/'hierarchy/serial-settled.vcd'))
for instance,width in [('u',3),('v',7)]:
 for g in range(2):
  bits=width+g
  assert hier[('top',instance,'gen['+str(g)+']','x')][2]==[(0,(((bits<<bits)|1),0)),(1000,((((bits+1)<<bits)|1),0))]
values=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal in ['ea','eb']:assert values[('top',signal)][2]==[(0,(0,0))],signal
for name in ['values','effects','hierarchy']:
 assert 'DSIM error:' not in (out/name/'serial-run.stdout').read_text(),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),native_boundary_models=2,implicit_port_regression=True,independent_signal_types=6,independent_generate_values=4,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS packed aggregates:',captures,'captures, 3 rollback models,',len(negative),'rejections, 2 native boundary checks and independent layout/parallel oracles')
