"""String-key and class-owned associative arrays, ordering and transaction isolation."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/string_associative';expected=json.loads((fixtures/'expected.json').read_text())
if '--negative-only' in sys.argv[4:]:expected={}
for arg in sys.argv[4:]:
 if arg.startswith('--model='):expected={arg.split('=',1)[1]:expected[arg.split('=',1)[1]]}
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0,negative_cases=0,runtime_rejections=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
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
def native(source,exe,work,label,flags=()):
 strict=['-fp-model=strict'] if Path(config['DSIM_MODEL_CXX']).name in ('icpx','icpc') else []
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread',*strict,*flags,'-I'+str(ROOT/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],work,label)
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  stdout=run([work/backend],work,backend+'-run')
  assert [s for s in stdout.splitlines() if s.startswith('TRACE')]==wanted,(name,backend,stdout,wanted)
  for mode in ([] if name=='copy' else ['ordered','settled']):
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt)==stdout
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
 if name=='parallel':
  run([work/'parallel','--parallel-stats'],work,'stats')
  assert '"partitions":2' in (work/'stats.stderr').read_text()
  lanes=timeline(*read(work/'serial-settled.vcd'))
  assert lanes[('top','one')][2]==[(0,(0,0)),(1,(8,0)),(3,(1,0))]
  assert lanes[('top','two')][2]==[(0,(0,0)),(1,(20,0)),(3,(1,0))]
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  replacement='''
s.run_until(1);
if(s.predict_until(5,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("missing rollback");
if(!s.predict_until(6,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
s.run();
'''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replacement));native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'serial','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','2','--wave-end','3'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')} and lanes[('top','observed')][2]==[(2,(12,0))],lanes;report['captures']+=1
 report['models'][name]=dict(status='PASS',source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest())
 lanes=timeline(*read(work/'serial-settled.vcd')) if name!='copy' else {}
 if name=='rollback':assert lanes[('top','observed')][2]==[(0,(3,0)),(2,(12,0)),(4,(5,0)),(6,(24,0))],lanes
 if name=='enums':assert lanes[('top','current')][2][-1][1]==((1<<68)-1,(1<<68)-1)
 save()
for name,(body,diagnostic) in json.loads((fixtures/'negative.json').read_text()).items():
 source=out/(name+'.sv');source.write_text('module top;'+body+'\nendmodule\n');target=out/(name+'.cpp');target.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',target],out,name,False)
 assert diagnostic in (out/(name+'.stderr')).read_text(),name
 assert not target.exists(),(name,'partial generated output');report['negative_cases']+=1
 save()
native(fixtures/'kernel.cpp',out/'kernel',out,'kernel-compile')
assert run([out/'kernel'],out,'kernel-run')=='PASS string associative heap and checkpoint isolation\n'
report['checkpoints']=2
report['status']='PASS';(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS string associative:',report['captures'],'captures,',report['rollbacks'],'rollback,',report['commits'],'commit,',report['negative_cases'],'compile rejections')
