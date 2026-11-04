"""Named types at parameter and static subroutine boundaries."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/type_signatures'
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

negative={
 'unknown_parameter':('parameter missing_t P=1;','unknown integral type'),
 'unknown_formal':('function integer f(input missing_t x);begin f=x;end endfunction integer q;initial q=f(1);','unknown integral type'),
 'unknown_return':('function missing_t f(input integer x);begin f=x;end endfunction integer q;initial q=f(1);','unknown integral type'),
 'value_as_type':('int t;parameter t P=1;','unknown integral type'),
 'uninitialized_parameter':('typedef logic[7:0] t;parameter t P;',''),
 'runtime_parameter':('typedef logic[7:0] t;t v;parameter t P=v;',''),
 'unpacked_parameter':('typedef logic[7:0] t;parameter t P[0:1]=0;',''),
 'unpacked_formal':('typedef logic[7:0] t;function t f(input t x[0:1]);begin f=x;end endfunction t q;initial q=f(1);',''),
 'parameter_signing':('typedef logic[7:0] t;parameter signed t P=1;','named parameter type'),
 'parameter_extra_type':('typedef logic[7:0] t;parameter int t P=1;','named parameter type'),
 'parameter_packed_suffix':('typedef logic[7:0] t;parameter t[1:0] P=0;',''),
 'enum_parameter_raw':('typedef enum logic[1:0]{A,B}t;parameter t P=1;','enum parameter'),
 'enum_parameter_other':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;parameter t P=D;','enum parameter'),
 'enum_formal_raw':('typedef enum logic[1:0]{A,B}t;function t f(input t x);begin f=x;end endfunction t q;initial q=f(1);','enum assignment'),
 'enum_formal_other':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;function t f(input t x);begin f=x;end endfunction t q;initial q=f(C);','enum assignment'),
 'enum_function_assignment':('typedef enum logic[1:0]{A,B}t;function t f(input t x);begin f=1;end endfunction t q;initial q=f(A);','enum assignment'),
 'enum_return_raw':('typedef enum logic[1:0]{A,B}t;function t f(input t x);begin return 1;end endfunction t q;initial q=f(A);','enum return'),
 'enum_return_other':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;function t f(input t x);begin return C;end endfunction t q;initial q=f(A);','enum return'),
 'enum_result_assignment':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;function t f(input t x);begin f=x;end endfunction u q;initial q=f(A);','enum assignment'),
 'enum_task_input':('typedef enum logic[1:0]{A,B}t;task go(input t x);begin end endtask initial go(1);','enum assignment'),
 'enum_task_inout':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;task go(inout t x);begin x=B;end endtask u q;initial go(q);','enum assignment'),
 'enum_task_output':('typedef enum logic[1:0]{A,B}t;typedef enum logic[1:0]{C,D}u;task go(output t x);begin x=B;end endtask u q;initial go(q);','enum assignment'),
 'scalar_formal_select':('typedef logic t;function t f(input t x);begin f=x[0];end endfunction t q;initial q=f(1);','scalar'),
 'scalar_result_select':('typedef logic t;function t f(input t x);begin f[0]=x;end endfunction t q;initial q=f(1);','scalar'),
 'type_invisible':('generate if(1)begin:g typedef logic[7:0] t;end endgenerate parameter t P=1;','unknown integral type'),
 'typed_parameter_readonly':('typedef logic[7:0]t;parameter t P=1;initial P=2;','assignment target'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,step,base in [('a',3000,3),('b',4000,17)]:
 wanted=[(0,(0,0))]+[(i*step,(base+i*3,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
ir=json.loads((out/'values/serial.json').read_text());params=ir['scopes'][0]['parameters']
assert params['NEG']==dict(width=8,signed=True,two_state=False,bits='11111110')
assert params['CLEAN']['width']==130 and params['CLEAN']['two_state']
assert params['PACK']['width']==12 and params['DATA']['bits']=='10111110'
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=1,negative_cases=len(negative),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS named type signatures:',captures,'captures, 1 rollback,',len(negative),'rejections and two parallel lanes')
