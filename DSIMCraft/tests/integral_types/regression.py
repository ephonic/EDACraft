"""Integral signedness, time, typed ports and subroutines through the actual compiled simulator."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/integral_types'
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
  for signal,base in [('a',3),('b',17)]:
   expected_values=[(0,(0,0))]+[((i+2)*1000,(0x100000000+base+i*3,0)) for i in range(5)]
   assert values[('top',signal)][2]==expected_values,(signal,values[('top',signal)],expected_values)
 if name=='memory':
  values=timeline(*read(work/'serial-settled.vcd'))
  wanted_words={
   'words[0]':[(0,(0x12345678ffffffff,0)),(1000,(0x1234567900000000,0))],
   'words[1]':[(0,(0x8000000000000000,0)),(1000,(0x8000000100000000,0))],
   'words[2]':[(0,(0xffffffffffffffff,0)),(3000,(0xfedcba9876543210,0))],
   'numbers[0]':[(0,(0xffffffff,0)),(1000,(0x55555555,0))],
   'numbers[1]':[(0,(0x80000000,0)),(2000,(0x40000000,0))],
  }
  for word,reference in wanted_words.items():assert values[('top',word)][2]==reference,(word,values[('top',word)],reference)
 if name in ['ports','memory','subroutines']:
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
# Compile-time boundaries and lexical visibility must fail explicitly.
negative={
 'integer_range':('module top(input integer[7:0]a);endmodule',''),
 'time_range':('module top(input time[7:0]a);endmodule',''),
 'integral_inout':('module top(inout integer a);endmodule',''),
 'time_signed':('module top;time signed a;endmodule',''),
 'formal_range':('module top;task t(input time[7:0]a);begin end endtask initial t(1);endmodule',''),
 'return_range':('module top;function time[7:0]f;begin f=1;end endfunction endmodule',''),
 'subarray_value':('module top;time a[0:1][0:1],q;initial q=a[0];endmodule',''),
}


for name,(source,diagnostic) in negative.items():
 path=out/(name+'.sv');path.write_text(source+'\n')
 run([compiler,path,'--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text(),name
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
print('PASS',len(negative),'unsupported or invalid integral type diagnostics')

(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=3,negative_cases=len(negative),independent_updated_words=5,independent_parallel_lanes=2),indent=2)+'\n')
print('PASS integral types:',captures,'captures, 3 rollback models,',len(negative),'diagnostics')
