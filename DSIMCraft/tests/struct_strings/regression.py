"""Heterogeneous unpacked values across copying, events, checkpoints and workers."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
fixtures=ROOT/'tests/struct_strings'
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
report=dict(status='RUNNING',models={},captures=0,rollback_models=0,negative_cases=0)
for name,wanted in json.loads((fixtures/'expected.json').read_text()).items():
 work=out/name;work.mkdir(exist_ok=True);references={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  trace=run([work/backend],work,backend+'-run');assert trace.splitlines()==wanted,(name,backend,trace)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    dest=work/(backend+'-'+mode+'.'+fmt);dest.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',dest,'--wave-mode',mode,'--wave-format','vcd' if fmt=='vcd' else 'dwf',*extra],work,backend+'-'+mode+'-'+fmt)==trace
    state=streams(dest);report['captures']+=1
    assert not any(key[-1] in ('a','b','r','s','x','y') or key[-1].startswith('items[') for key in state),state
    if backend=='serial' and fmt=='vcd':references[mode]=state
    assert state==references[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert dest.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
  if backend=='parallel' and name=='parallel':
   run([work/backend,'--parallel-stats'],work,'stats')
   assert '"partitions":2' in (work/'stats.stderr').read_text()
 code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
 replay='''
s.run_until(0);
if(s.predict_until(20,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''
 if name=='timing':
  declaration='s.signal(85,false); // "top.a"';assert code.count(declaration)==1
  code=code.replace(declaration,'int replay_struct='+declaration)
  replay='''
s.run_until(0);auto original=s.get(replay_struct);bool changed=false,restored=false;
if(s.predict_until(4,[](Sim&){},[&](const Sim& trial){changed=!trial.get(replay_struct).same(original);return false;},[&](Sim& retry){restored=retry.get(replay_struct).same(original);}))throw std::runtime_error("unexpected commit");
if(!changed||!restored||s.get(replay_struct).same(original))throw std::runtime_error("struct string rollback lost value isolation");
if(!s.predict_until(20,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("prediction counters");
s.run();
'''
 (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replay))
 strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,'-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
 dest=work/'replay.dwf';dest.unlink(missing_ok=True)
 assert run([work/'replay','--waveform',dest,'--wave-mode','ordered'],work,'replay-run')==(work/'serial-run.stdout').read_text()
 assert streams(dest)==references['ordered'];report['captures']+=1;report['rollback_models']+=1
 report['models'][name]=dict(status='PASS',captures=19)
 if name=='parallel':
  state=timeline(*read(dest))
  for signal,wanted in [('ca',3),('cb',3),('ea',0),('eb',0)]:
   key=('top',signal);assert state[key][2][-1][1]==(wanted,0),(key,state[key])
for name,source in json.loads((fixtures/'negative.json').read_text()).items():
 path=out/(name+'.sv');path.write_text(source+'\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,path,'--emit-only','--emit-cpp',target],out,name,False)
 assert not target.exists();report['negative_cases']+=1
report.update(status='PASS',real_parallel_partitions=2,commits=1)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS struct strings:',report['captures'],'captures,',report['negative_cases'],'diagnostics, 4 rollbacks and 2 partitions')
