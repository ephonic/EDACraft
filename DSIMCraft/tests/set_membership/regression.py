"""Integral set membership, wildcard equality and case-inside."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/set_membership'
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
    assert all('$activation' not in '.'.join(key) for key in state),(name,'automatic state exported')
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
  if backend=='parallel' and name in ['parallel']:
   run([work/backend,'--parallel-stats'],work,'stats')
   assert ('"partitions":'+str(2 if name=='parallel' else 1)) in (work/'stats.stderr').read_text()
 if name in ['effects','control']:
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
 'empty_set': ('logic q;initial q=1 inside {};', 'syntax error'),
 'trailing_comma': ('logic q;initial q=1 inside {1,};', 'syntax error'),
 'missing_comma': ('logic q;initial q=1 inside {1 2};', 'syntax error'),
 'missing_bound': ('logic q;initial q=1 inside {[1:]};', 'syntax error'),
 'indexed_range': ('logic q;initial q=1 inside {[1+:2]};', 'syntax error'),
 'open_low': ('logic q;initial q=1 inside {[$:4]};', ''),
 'open_high': ('logic q;initial q=1 inside {[0:$]};', ''),
 'string_member': ('logic q;initial q=1 inside {"a"};', ''),
 'string_selector': ('logic q;initial q="a" inside {1};', ''),
 'subarray_member': ('integer a[0:1][0:1];logic q;initial q=1 inside {a[0]};', ''),
 'array_selector': ('integer a[0:1];logic q;initial q=a inside {1};', ''),
 'array_bound': ('integer a[0:1];logic q;initial q=1 inside {[a:3]};', ''),
 'casez_inside': ('integer q;initial casez(q)inside 1:q=2;endcase', 'inside requires case'),
 'normal_case_range': ('integer q;initial case(q)[1:3]:q=2;endcase', 'syntax error'),
 'empty_case_set': ('integer q;initial case(q)inside :q=2;endcase', 'syntax error'),
 'case_matches': ('logic[3:0] a;integer q;initial case(a) matches 1:q=1;endcase', ''),
 'delayed_function': ('function automatic integer f();begin #1;return 2;end endfunction logic q;initial q=1 inside {f()};', 'zero-time'),
 'task_member': ('task t();begin end endtask logic q;initial q=1 inside {t()};', ''),
 'unknown_symbol': ('logic q;initial q=1 inside {missing};', ''),
 'wild_missing_rhs': ('logic q;initial q=1==?;', 'syntax error'),
}

for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text('module child(input wire[31:0] x);endmodule module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 text=(out/(name+'.stderr')).read_text();assert 'dsim:' in text and diagnostic in text,(name,text)
lanes=timeline(*read(out/'parallel/serial-settled.vcd'))
for signal,step,base in [('a',3000,0),('b',4000,9)]:
 wanted=[(0,(0,0))]+[(i*step,(base+i,0)) for i in range(1,6)]
 assert lanes[('top',signal)][2]==wanted,(signal,lanes[('top',signal)],wanted)
for signal in ['ea','eb']:assert lanes[('top',signal)][2]==[(0,(0,0))],signal
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),independent_parallel_lanes=2),indent=2)+'\n')
print('PASS set membership:',captures,'captures, 2 rollbacks,',len(negative),'rejections and 2 independent partitions')
