"""IEEE numeric execution, exact compressed real bits and selected async capture."""
from pathlib import Path
import json,math,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline,dwf
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]) if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={s.split('=',1)[0].split(':',1)[0]:s.split('=',1)[1] for s in cache.read_text().splitlines() if '=' in s and not s.startswith('//')}
fixtures=ROOT/'tests/real_values';expected=json.loads((fixtures/'expected.json').read_text())
for arg in sys.argv[4:]:
 if arg.startswith('--model='):expected={arg.split('=',1)[1]:expected[arg.split('=',1)[1]]}
report=dict(status='RUNNING',models={},captures=0,rollbacks=0,commits=0)
def save():(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,work,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=work,text=True,capture_output=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode>=0 and (p.returncode==0)==ok,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 real_codes={row[3] for row in meta['header'] if row[0]=='$var' and row[1]=='real'}
 for t,kind,value in events:
  if kind!='value':continue
  ident,(bits,unknown)=value;s=meta['signals'][ident]
  if s['code'] in real_codes:
   assert not unknown
   number=struct.unpack('<f' if s['width']==32 else '<d',bits.to_bytes(s['width']//8,'little'))[0]
   # Text VCD represents NaN but cannot preserve its payload. DWF bits are
   # checked independently below, including after a prediction rollback.
   value=('nan',) if math.isnan(number) else ('real',number,math.copysign(1,number))
  else:value=(bits,unknown)
  values[ident].append((t,value))
 return {key:(width,ranges,values[i]) for key,(i,width,ranges) in declarations(meta).items()}

def native(source,exe,work,label):
 return run([config['DSIM_MODEL_CXX'],'-std=c++17','-O2','-pthread','-I'+str(ROOT/'include'),'-I'+config['DSIM_ZSTD_INCLUDE'],source,config['DSIM_ZSTD_LIBRARY'],'-o',exe],work,label)
library=out/('api.dylib' if sys.platform=='darwin' else 'api.so')
run(['cc','-shared','-fPIC',fixtures/'api.c','-o',library],out,'c-library')
save()
for name,wanted in expected.items():
 work=out/name;work.mkdir(exist_ok=True);reference={}
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  extra=['--dpi-lib',library,'--dpi-header',work/(backend+'.h')] if name=='dpi' else []
  run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,*extra,'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  if name=='dpi':run(['cc','-fsyntax-only','-I'+str(ROOT/'include/dsim'),'-include',work/(backend+'.h'),fixtures/'api.c'],work,backend+'-abi')
  stdout=run([work/backend],work,backend+'-run');assert stdout.splitlines()==wanted,(name,backend,stdout,wanted)
  for mode in ['ordered','settled']:
   for fmt,extra in [('vcd',[]),('dwf',[]),('async.dwf',['--wave-async','--wave-buffer-bytes','4096'])]:
    path=work/(backend+'-'+mode+'.'+fmt);path.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',path,'--wave-format','vcd' if fmt=='vcd' else 'dwf','--wave-mode',mode,*extra],work,backend+'-'+mode+'-'+fmt)==stdout
    state=streams(path);report['captures']+=1
    if backend=='serial' and fmt=='vcd':reference[mode]=state
    assert state==reference[mode],(name,backend,mode,fmt)
    if fmt=='async.dwf':assert path.read_bytes()==(work/(backend+'-'+mode+'.dwf')).read_bytes()
  if name=='special':
   with (work/(backend+'-ordered.dwf')).open('rb') as f:
    reader=dwf.Reader(f);assert all(s.get('type')=='real' and s['width']==64 for s in reader.meta['signals'])
    raw=[(t,p[1]) for t,k,p in reader.events() if k=='value']
    assert [(t,bits) for t,bits in raw if bits!=(0,0)]==[
     (0,(0x7ff8000000000042,0)),(1,(0x7ff0000000000000,0)),
     (2,(0x8000000000000000,0))],raw
 if name=='parallel':
  run([work/'parallel','--parallel-stats'],work,'stats');assert '"partitions":2' in (work/'stats.stderr').read_text()
  for signal,expected_changes in [('one',[(0,0.5),(2,1.25),(4,2.5)]),('two',[(0,-1.5),(1,0.25),(3,0.5)])]:
   samples=reference['settled'][('top',signal)][2]
   assert [(t,v[1]) for t,v in samples]==expected_changes,(signal,samples)
 if name=='rollback':
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  replacement='''
s.run_until(1);
if(s.predict_until(4,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("unexpected commit");
if(!s.predict_until(5,[](Sim&){},[](const Sim&){return true;},[](Sim&){}))throw std::runtime_error("missing commit");
if(s.prediction_stats.rollbacks!=1||s.prediction_stats.commits!=1)throw std::runtime_error("missing prediction accounting");
s.run();
'''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n',replacement));native(work/'replay.cpp',work/'replay',work,'replay-compile')
  path=work/'replay.dwf';path.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',path,'--wave-mode','ordered','--wave-async'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(path)==reference['ordered'];report['captures']+=1;report['rollbacks']+=1;report['commits']+=1
  path=work/'selected.dwf';path.unlink(missing_ok=True)
  run([work/'replay','--waveform',path,'--wave-async','--wave-scope','top','--wave-include','*observed','--wave-start','2','--wave-end','3'],work,'selected-run')
  lanes=timeline(*read(path));assert set(lanes)=={('top','observed')}
  assert lanes[('top','observed')][2]==[(2,(0x3fe8000000000000,0)),(3,(0x3ff0000000000000,0))],lanes
  report['captures']+=1
 report['models'][name]={'status':'PASS'};save();print('PASS real',name,flush=True)
negative=json.loads((fixtures/'negative.json').read_text())
for name,body in negative.items():
 work=out/name;work.mkdir(exist_ok=True);source=work/'bad.sv';source.write_text('module top;\n'+body+'\nendmodule\n')
 cpp=work/'bad.cpp';cpp.unlink(missing_ok=True)
 run([compiler,source,'--emit-only','--emit-cpp',cpp],work,'reject',False)
 assert not cpp.exists(),name
report['negative_cases']=len(negative);save()
report['status']='PASS';save();print(json.dumps(report),flush=True)
