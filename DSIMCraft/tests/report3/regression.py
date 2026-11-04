"""REPORT3 packed literal contexts, assertion actions and signedness controls."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];fixtures=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations,timeline
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
config={x.split('=',1)[0].split(':',1)[0]:x.split('=',1)[1] for x in cache.read_text().splitlines() if '=' in x and not x.startswith('//')}
def run(cmd,work,label):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for t,k,p in events:
  if k=='value':values[p[0]].append((t,p[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);references={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,fixtures/(name+'.sv'),'--wave-support',*flags,'--emit-ir',work/(backend+'.json'),'--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   trace=run([work/backend],work,backend+'-run');assert trace.splitlines()==wanted,(name,backend,trace,wanted)
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    assert run([work/backend,'--waveform',wave,'--wave-mode',mode,'--wave-format','vcd'],work,backend+'-'+mode)==trace
    state=streams(wave);report['captures']+=1
    if backend=='serial':references[mode]=state
    assert state==references[mode],(name,backend,mode,'complete signal streams')
   if backend=='parallel' and name=='parallel':
    run([work/backend,'--parallel-stats'],work,'stats')
    assert '"partitions":2' in (work/'stats.stderr').read_text()
  code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
  checkpoint='s.run_until(1000);\n' if name in ['actions','parallel'] else ''
  (work/'replay.cpp').write_text(code.replace('\ns.run();\n','\n'+checkpoint+'''
if(s.predict_until(30000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
  run(['c++','-std=c++17','-O2','-pthread','-I'+config['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',config['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
  wave=work/'replay.vcd';wave.unlink(missing_ok=True)
  assert run([work/'replay','--waveform',wave,'--wave-mode','ordered','--wave-format','vcd'],work,'replay-run')==(work/'serial-run.stdout').read_text()
  assert streams(wave)==references['ordered'],(name,'rollback complete signal streams')
  report['captures']+=1;report['rollbacks']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),'trace':wanted}
  print('PASS REPORT3',name,flush=True)
 state=timeline(*read(out/'parallel/serial-settled.vcd'))
 for name,wanted in [('ea',0),('eb',0),('a',0x4144),('b',0x4144)]:assert state[('top',name)][2][-1][1]==(wanted,0),(name,state[('top',name)])
 for lane in ['u','v']:assert state[('top',lane,'count')][2][-1][1]==(3,0),lane
 # Preserve the original report probe verbatim: its own BUG labels also occur in VCS.
 wanted=['sra  in ternary: BUG got=7fffffff want=ffffffff','div  in ternary: BUG got=55555554 want=00000000','mod  in ternary: BUG got=00000002 want=fffffffe','cmp  in ternary: ok','mul  in ternary: ok','sra both-branch ternary: ok']
 work=out/'p27';work.mkdir(exist_ok=True)
 for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
  run([compiler,fixtures/'p27_signed_ternary.sv','--top','tb',*flags,'--wave-support','--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
  wave=work/(backend+'.vcd');wave.unlink(missing_ok=True)
  assert run([work/backend,'--waveform',wave,'--wave-format','vcd'],work,backend+'-run').splitlines()==wanted
  if backend=='serial':reference=streams(wave)
  else:assert streams(wave)==reference,('p27',backend)
  report['captures']+=1
 report.update(status='PASS',signedness_probe='same six lines as VCS',real_parallel_partitions=2)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS REPORT3:',report['captures'],'VCD captures,',report['rollbacks'],'rollbacks and signedness control')
