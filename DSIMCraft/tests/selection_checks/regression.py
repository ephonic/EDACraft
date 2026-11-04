"""Qualified selection statements, deferred diagnostics and process-local report flushing."""
from pathlib import Path
import json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/selection_checks'
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
warnings=json.loads((fixtures/'warnings.json').read_text())
def reports(text):
 return sorted([[int(time),int(line),reason] for reason,line,time in re.findall(r'DSIM selection: .*? (overlap|no-match) at .*?:(\d+) time=(\d+)',text)])
captures=0
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert 'DSIM fatal:' not in trace and reports(trace)==warnings[name],(name,trace,warnings[name]);assert [x for x in trace.splitlines() if x.startswith('TRACE')]==wanted,(name,backend,trace)
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
 if name in ['events','functions']:
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
 'duplicate': 'logic a;integer q;initial unique priority if(a)q=1;',
 'after_else': 'logic a;integer q;initial if(a)q=1;else unique if(a)q=2;',
 'inner_qualifier': 'logic a;integer q;initial unique if(a)q=1;else priority if(a)q=2;',
 'casez_inside': 'logic a;integer q;initial unique casez(a)inside 0:q=1;endcase',
 'case_matches': 'logic a;integer q;initial unique case(a)matches 0:q=1;endcase',
 'assert_control': 'initial $assertoff;',
 'qualified_loop': 'initial priority repeat(2);',
 'qualified_assertion': 'logic a;initial unique assert(a);',
}
for name,source in negative.items():
 path=out/(name+'.sv');path.write_text('module top;'+source+' endmodule\n')
 run([compiler,path,'--emit-only','--emit-cpp',out/(name+'.cpp')],out,name,False)
 assert 'dsim:' in (out/(name+'.stderr')).read_text()
for flag in ['ea','eb']:
 assert timeline(*read(out/'parallel/serial-settled.vcd'))[('top',flag)][2]==[(0,(0,0))]
(out/'results.json').write_text(json.dumps(dict(status='PASS',models=len(expected),captures=captures,rollback_models=2,negative_cases=len(negative),diagnostic_reports=sum(map(len,warnings.values())),real_parallel_partitions=2),indent=2)+'\n')
print('PASS qualified selections:',captures,'captures, 2 rollbacks,',len(negative),'rejections and',sum(map(len,warnings.values())),'deferred reports')
