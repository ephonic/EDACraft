"""Enumerated types, nominal identity and runtime semantics."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/enums'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=float(os.environ.get("DSIM_TEST_COMMAND_TIMEOUT","180")))
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
 if name in ['values','scopes']:
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
 'duplicate_value':('typedef enum {A=1,B=1} t;','enum duplicate member value'),
 'duplicate_x':("typedef enum logic[3:0] {A=4'bx001,B=4'bx001} t;",'enum duplicate member value'),
 'duplicate_name':('typedef enum {A,A} t;','enum duplicate member or symbol'),
 'name_collision':('int A;typedef enum {A,B} t;','enum duplicate member or symbol'),
 'auto_unsigned_overflow':("typedef enum logic[2:0] {A=3'd7,B} t;",'enum implicit member overflows'),
 'auto_signed_overflow':('typedef enum logic signed[2:0] {A=3,B} t;','enum implicit member overflows'),
 'positive_range':('typedef enum logic[2:0] {A=8} t;','enum member is outside'),
 'signed_range':('typedef enum logic signed[2:0] {A=7} t;','enum member is outside'),
 'negative_range':('typedef enum logic signed[2:0] {A=-5} t;','enum member is outside'),
 'unsigned_negative':('typedef enum logic[7:0] {A=-1} t;','enum member is outside'),
 'wide_sized':("typedef enum logic[3:0] {A=8'd2} t;",'enum sized member is wider'),
 'wide_sized_expr':("typedef enum logic[3:0] {A=8'd2+8'd1} t;",'enum sized member is wider'),
 'wide_cast':("typedef enum logic[3:0] {A=int'(2)} t;",'enum sized member is wider'),
 'two_state_x':("typedef enum bit[3:0] {A=4'bx001} t;",'enum two-state base'),
 'implicit_x':("typedef enum logic[3:0] {A=4'bx001,B} t;",'enum implicit member cannot follow'),
 'implicit_z':("typedef enum logic[3:0] {A=4'bz001,B} t;",'enum implicit member cannot follow'),
 'runtime_value':('int n=2;typedef enum {A=n} t;','enum member requires'),
 'real_value':('typedef enum {A=2.5} t;','enum member requires'),
 'future_value':('typedef enum {A=B,B=2} t;',''),
 'enum_base':('typedef enum {A,B} t;typedef enum t {C,D} u;','enum base must be'),
 'assign_integer':('typedef enum {A,B} t;t q;initial q=0;','enum assignment requires'),
 'assign_other_enum':('typedef enum {A,B} t;typedef enum {C,D} u;t q;initial q=C;','enum assignment requires'),
 'initializer_integer':('typedef enum {A,B} t;t q=0;','enum assignment requires'),
 'numeric_parameter':('typedef enum {A,B} t;parameter int P=A;t q;initial q=P;','enum assignment requires'),
 'integer_cast':("typedef enum {A,B} t;t q;initial q=int'(A);",'enum assignment requires'),
 'size_cast_label':("typedef enum {A=4,B} t;t q;initial q=A'(0);",'enum assignment requires'),
 'arithmetic_assignment':('typedef enum {A,B} t;t q;initial q=A+1;','enum assignment requires'),
 'mixed_ternary':('typedef enum {A,B} t;t q;initial q=1?A:0;','enum assignment requires'),
 'memory_integer':('typedef enum {A,B} t;t q[0:1];initial q[1]=0;','enum assignment requires'),
 'delayed_blocking':('typedef enum {A,B} t;t q;initial q=#1 0;','enum assignment requires'),
 'delayed_nba':('typedef enum {A,B} t;t q;initial q<=#1 0;','enum assignment requires'),
 'compound':('typedef enum {A,B} t;t q;initial begin q=A;q+=1;end','compound assignment to enum'),
 'member_write':('typedef enum {A,B} t;initial A=2;',''),
 'out_of_scope':('initial begin: x typedef enum {A,B} t;end initial $display(A);',''),
 'member_range':('typedef enum {A[2]} t;',''),
 'method_name_arguments':('typedef enum {A,B} t;t q;initial $display("%s",q.name(1));','too many arguments'),
}
for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
params=json.loads((out/'values/serial.json').read_text())['scopes'][0]['parameters']
for name,width,sign,value in [('CHOSEN',32,True,4),('WV',130,False,1<<64)]:
 p=params[name];assert (p['width'],p['signed'],p['bits'])==(width,sign,format(value,'0'+str(width)+'b')),(name,p)
signals=json.loads((out/'values/serial.json').read_text())['scopes'][0]['signals']
for name,width,sign,two in [('state',32,True,True),('copy',32,True,True),('sm',8,True,False),('four',4,False,False),('wide',130,False,True),('narrow',4,False,False)]:
 p=signals[name];assert (p['width'],p['signed'],p['two_state'])==(width,sign,two),(name,p)
assert not any(name in signals for name in ['state_t','IDLE','RUN','W0','W1']),'enum definitions allocated runtime storage'
hier=timeline(*read(out/'hierarchy/serial-settled.vcd'))
for instance,width in [('u',3),('v',7)]:
 for g in range(2):
  bits=width+g
  assert hier[('top',instance,'gen['+str(g)+']','x')][2]==[(0,(bits,0)),(1000,(bits+1,0)),(2000,((1<<bits)-1,0))]
values=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal in ['ea','eb']:assert values[('top',signal)][2]==[(0,(0,0))],signal
for name in ['values','scopes','hierarchy']:
 assert 'DSIM error:' not in (out/name/'serial-run.stdout').read_text(),name
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parameters=2,independent_signal_types=6,independent_generate_values=4,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS enums:',captures,'captures, 2 rollback models,',len(negative),'rejections and independent type/value/parallel oracles')
