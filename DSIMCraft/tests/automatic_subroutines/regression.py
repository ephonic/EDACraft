"""Automatic activation, initialization, suspension and output copying."""
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/automatic_subroutines'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=float(os.environ.get('DSIM_TEST_COMMAND_TIMEOUT','180')))
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
    assert all('$activation' not in '.'.join(key) for key in state),(name,'automatic state exported')
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name in ['parallel']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name=='parallel' else 1)) in (work/'stats.stderr').read_text()
 if name in ['overlap','events','blocks']:
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.now!=1000)throw std::runtime_error("activation checkpoint time missing");
if(s.predict_until(300000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  dest=work/'replay.dwf';dest.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(dest)==references['ordered'];captures+=1

negative={
 'function_local_nba': ('function automatic integer f();integer a;begin a<=1;return a;end endfunction integer q;initial q=f();', 'zero-time'),
 'function_return_nba': ('function automatic integer f();begin f<=1;end endfunction integer q;initial q=f();', 'zero-time'),
 'function_output_nba': ('function automatic integer f(output integer x);begin x<=1;return x;end endfunction integer q,x;initial q=f(x);', 'zero-time'),
 'function_input_nba': ('function automatic integer f(input integer x);begin x<=1;return x;end endfunction integer q;initial q=f(2);', 'zero-time'),
 'task_local_nba': ('task automatic t();integer a;begin a<=1;end endtask initial t();', 'nonblocking assignment'),
 'task_array_nba': ('task automatic t();integer a[0:1];begin a[1]<=1;end endtask initial t();', 'nonblocking assignment'),
 'task_dynamic_array_nba': ('task automatic t(input integer i);integer a[0:1];begin a[i]<=1;end endtask initial t(1);', 'nonblocking assignment'),
 'task_part_nba': ('task automatic t();logic[7:0] a;begin a[2+:3]<=1;end endtask initial t();', 'nonblocking assignment'),
 'task_delayed_nba': ('task automatic t();integer a;begin a<=#1 1;end endtask initial t();', 'nonblocking assignment'),
 'task_inout_nba': ('task automatic t(inout integer a);begin a<=1;end endtask integer q;initial t(q);', 'nonblocking assignment'),
 'task_block_nba': ('task automatic t();begin: blk integer a;a<=1;end endtask initial t();', 'nonblocking assignment'),
 'recursive_output': ('function automatic integer f(input integer x,output integer y);begin return f(x,y);end endfunction integer q,r;initial q=f(1,r);', 'input/ref formals and scalar results'),
 'recursive_task': ('task automatic t();begin t();end endtask initial t();', ''),
 'function_delay': ('function automatic integer f();begin #1;return 2;end endfunction integer q;initial q=f();', 'zero-time'),
 'function_event': ('logic x;function automatic integer f();begin @(x);return 2;end endfunction integer q;initial q=f();', 'zero-time'),
 'function_task': ('task automatic t();begin end endtask function automatic integer f();begin t();return 2;end endfunction integer q;initial q=f();', 'zero-time'),
 'function_ref_static': ('function integer f(ref integer x);begin return x;end endfunction integer q;initial q=f(q);', ''),
 'task_ref_static': ('task t(ref integer x);begin end endtask integer q;initial t(q);', ''),
 'duplicate_automatic': ('function automatic automatic integer f();begin return 1;end endfunction integer q;initial q=f();', 'duplicate automatic'),
 'enum_input': ('typedef enum logic[1:0]{A,B} t;function automatic t f(input t x);begin return x;end endfunction t q;initial q=f(1);', 'enum assignment'),
 'output_constant': ('task automatic t(output integer a);begin a=1;end endtask initial t(2);', 'assignment target'),
 'continuous_output': ('integer a;function automatic integer f(output integer x=a);begin x=1;return x;end endfunction wire[31:0] q=f();', 'requires a procedural expression'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module child(input wire[31:0] x);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,step,base in [('a',3000,5),('b',4000,19)]:
 wanted=[(0,(0,0))]+[(i*step,(base+i,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS automatic subroutines:',captures,'captures, 3 rollbacks,',len(negative),'rejections and 2 independent partitions')
