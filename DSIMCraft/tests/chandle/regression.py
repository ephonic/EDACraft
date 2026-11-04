"""Actual C ABI calls, callbacks, waves, input protection and prediction barriers."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/chandle';expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,kind,value in events:
  if kind=='value':values[value[0]].append((t,value[1]))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}
def native(source,exe,work,label):
 strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 export=['-Wl,-export_dynamic'] if sys.platform=='darwin' else ['-Wl,--export-dynamic','-ldl']
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],*export,'-o',exe],work,label)
cc=os.environ.get('CC','cc')
feature_flags=[] if sys.platform=='darwin' else ['-D_GNU_SOURCE']
shared_flags=['-shared','-fPIC',*feature_flags,*(['-Wl,-undefined,dynamic_lookup'] if sys.platform=='darwin' else [])]
library=out/('api.dylib' if sys.platform=='darwin' else 'api.so')
run([cc,*shared_flags,'-I'+str(ROOT/'include/dsim'),fixtures/'api.c','-o',library],out,'c-library')
save()
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support','--dpi-lib',library,'--dpi-header',work/(backend+'.h'),*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  run([cc,*feature_flags,'-fsyntax-only','-I'+str(ROOT/'include/dsim'),'-include',work/(backend+'.h'),fixtures/'api.c'],work,backend+'-c-prototypes')
  stdout=run([work/backend],work,backend+'-run')
  assert stdout.splitlines()==wanted,(name,backend,stdout,wanted)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt)==stdout
    state=streams(path);assert not any(key[-1] in ('h','k','a','b','c') or key[-1].startswith('arr[') for key in state),(name,state);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  handle_storage='s.signal_two_state(64); // "top.h"'
  assert code.count(handle_storage)==1
  code=code.replace(handle_storage,'int replay_handle='+handle_storage)
  replacement='''
s.run_until(0);
if(s.predict_until(3,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("impure call was speculated");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing foreign-call rollback");
auto old_handle=s.get(replay_handle);bool changed=false,restored=false;
if(s.predict_until(4,[](Sim&){},[&](const Sim& trial){changed=trial.get(replay_handle).a!=old_handle.a;return false;},[&](Sim& replay){restored=replay.get(replay_handle).a==old_handle.a&&!replay.get(replay_handle).b;}))throw std::runtime_error("unexpected pure commit");
if(!changed||!restored||s.get(replay_handle).a==old_handle.a||s.get(replay_handle).b)throw std::runtime_error("opaque pointer rollback failed");
if(!s.predict_until(6,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing pure commit");
if(s.get(replay_handle).a==old_handle.a||s.get(replay_handle).b)throw std::runtime_error("opaque pointer commit failed");
s.run();
'''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replacement));native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==stdout
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=2;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'serial','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','3','--wave-end','4'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')} and lanes[('top','observed')][2]==[(3,(41,0)),(4,(73,0))],lanes;report['captures']+=1
  run([work/'parallel','--parallel-stats'],work,'parallel-stats')
  assert '"partitions":1' in (work/'parallel-stats.stderr').read_text()
 report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest());save()
for name,(body,diagnostic) in json.loads((fixtures/'negative.json').read_text()).items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),(name,(out/(name+'.stderr')).read_text())
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1;save()
report['status']='PASS';save();print('PASS chandle:',report['captures'],'captures,',report['rollbacks'],'rollbacks,',report['commits'],'commit,',report['negative_cases'],'compile rejections')
