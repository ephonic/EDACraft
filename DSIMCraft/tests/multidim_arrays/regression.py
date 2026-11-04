"""Static multidimensional arrays, indexed effects and activation storage."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/multidim_arrays'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in (compiler.parent/'CMakeCache.txt').read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0,(label,"process crashed",p.returncode,p.stderr)
 assert (p.returncode==0)==ok,(label,p.stdout,p.stderr)
 if ok:assert 'DSIM fatal:' not in p.stdout,(label,p.stdout)
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
 if name in ['effects','automatic']:
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
 'partial': 'logic[7:0] a[1:2][3:4];logic[7:0] q;initial q=a[1];',
 'slice': 'logic[7:0] a[1:2][3:4];logic[7:0] q;initial q=a[1:2][3];',
 'whole_value': 'logic[7:0] a[1:2][3:4];logic[7:0] q;initial q=a;',
 'net_write': 'wire[7:0] a[1:2][3:4];initial a[1][3]=0;',
 'negative_bound': 'logic[7:0] a[1:2][-1:1];',
 'total_limit': 'logic a[0:1024][0:1024];',
 'readmem': 'logic[7:0] a[1:2][3:4];initial $readmemh("x.hex",a);',
 'automatic_nba': 'task automatic t;logic[7:0] a[1:2][3:4];a[1][3]<=1;endtask initial t();',
 'array_port': 'endmodule module invalid(input logic[7:0] a[1:2][3:4]);',
}
for name,source in negative.items():
 path=out/(name+'.sv');path.write_text('module top(inout logic[7:0] a[1:2][3:4]);endmodule\n' if name=='array_port' else 'module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text()
for flag in ['ea','eb']:
 assert timeline(*read(out/'parallel/serial-settled.vcd'))[('top',flag)][2]==[(0,(0,0))]
# Every exported array word is checked against an independently visible packed
# observer; the same observer's whole timeline is also compared with VCS.
observers=json.loads((fixtures/'observers.json').read_text())
for model,words in observers.items():
 state=timeline(*read(out/model/'serial-settled.vcd'))
 actual_words={'.'.join(k) for k in state if '[' in k[-1]}
 assert actual_words==set(words),(model,actual_words,set(words))
 for word,(observer,shift,width) in words.items():
  wanted=[];mask=(1<<width)-1
  for t,(a,b) in state[tuple(observer.split('.'))][2]:
   value=((a>>shift)&mask,(b>>shift)&mask)
   if not wanted or wanted[-1][1]!=value:wanted.append((t,value))
  actual=state[tuple(word.split('.'))]
  assert actual[0]==width and actual[2]==wanted,(model,word,actual,wanted)
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative)),indent=2)+'\n')
print('PASS multidimensional arrays:',captures,'captures, 2 rollbacks,',len(negative),'rejections')
