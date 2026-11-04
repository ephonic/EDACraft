"""Typed integral/enum key conversion, traversal, constraints and restored storage."""
from pathlib import Path
import os,json,subprocess,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,declarations,timeline
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=root/'tests/integral_keys';expected=json.loads((fixtures/'expected.json').read_text())
if not config.get('DSIM_Z3_LIBRARY') or config['DSIM_Z3_LIBRARY'].endswith('-NOTFOUND'):
 for name in ('constraints','wide_constraints'):expected.pop(name,None)
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
save()
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=float(os.environ.get("DSIM_TEST_COMMAND_TIMEOUT","180")))
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}
selected=[x.split('=',1)[1] for x in sys.argv[4:] if x.startswith('--model=')]
if selected:expected={k:v for k,v in expected.items() if k in selected}
if '--negative-only' in sys.argv[4:]:expected={}
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  assert run([work/backend],work,backend+'-run').splitlines()==wanted,(name,backend)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt).splitlines()==wanted
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
 if name in ('rollback','packed_rollback'):
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1);
if(s.predict_until(4,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");
if(!s.predict_until(4,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("prediction accounting");
s.run();
'''))
  run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*(['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []),'-I'+str(root/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run').splitlines()==wanted
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'replay','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','2','--wave-end','3'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')}
  assert lanes[('top','observed')][2]==[(2,(15,0)),(3,(18,0))],lanes
  report['captures']+=1
 report['models'][name]={'status':'PASS','backend_requests':3}
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS integral keys',name,flush=True)
for name,(body,diagnostic) in json.loads((fixtures/'negative.json').read_text()).items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1;save()
for name,operation in [('unknown','write'),('unknown_read','read')]:
 run([compiler,fixtures/(name+'.sv'),'-o',out/name],out,name+'-compile')
 run([out/name],out,name+'-run',False)
 assert 'associative array '+operation+' index contains X/Z' in (out/(name+'-run.stderr')).read_text()
 report['runtime_rejections']+=1
run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread','-I'+str(root/'include'),fixtures/'keys_runtime.cpp','-o',out/'keys_runtime'],out,'keys-runtime-compile')
assert 'PASS typed integral key limbs' in run([out/'keys_runtime'],out,'keys-runtime-run')
report.update(status='PASS',runtime_keys='PASS');save()
print('PASS integral keys:',report['captures'],'captures,',report['negative_cases'],'compile rejections')
