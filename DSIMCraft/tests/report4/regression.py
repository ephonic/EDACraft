"""REPORT4 same-source signed-context and packed-string behavioral regressions."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
fixtures=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests/waveform'))
from reader import read,declarations

compiler=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
cache_path=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else compiler.parent/'CMakeCache.txt'
cache={line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
       for line in cache_path.read_text().splitlines() if '=' in line and not line.startswith('//')}

def run(command,work,label):
 p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=240)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout,p.stderr)
 return p.stdout

def streams(path):
 meta,events=read(path);values=[[] for _ in meta['signals']]
 for time,kind,payload in events:
  if kind=='value':values[payload[0]].append((time,payload[1]))
 return {key:(width,ranges,values[ident]) for key,(ident,width,ranges) in declarations(meta).items()}

models=json.loads((fixtures/'models.json').read_text())
expected=json.loads((fixtures/'expected.json').read_text())
report={'status':'RUNNING','models':{},'captures':0,'rollbacks':0}
try:
 for name,model in models.items():
  source=ROOT/model['source'];work=out/name;work.mkdir(exist_ok=True);references={}
  for backend,flags in [('serial',[]),('wheel',['--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,source,'--top',model['top'],*flags,'--wave-support',
        '--emit-cpp',work/(backend+'.cpp'),'-o',work/backend],work,backend+'-compile')
   for mode in ['ordered','settled']:
    wave=work/(backend+'-'+mode+'.vcd');wave.unlink(missing_ok=True)
    text=run([work/backend,'--waveform',wave,'--wave-mode',mode,'--wave-format','vcd'],work,backend+'-'+mode)
    assert text.splitlines()==expected[name],(name,backend,mode,text,expected[name])
    current=streams(wave)
    if backend=='serial':references[mode]=current
    else:assert current==references[mode],(name,backend,mode,'complete signal stream')
    report['captures']+=1
  if name in ['signed_contexts','contexts']:
   code=(work/'serial.cpp').read_text();assert code.count('\ns.run();\n')==1
   (work/'replay.cpp').write_text(code.replace('\ns.run();\n','''
s.run_until(1000);
if(s.predict_until(30000,[](Sim&){},[](const Sim&){return false;},[](Sim&){}))throw std::runtime_error("prediction committed");
if(s.prediction_stats.rollbacks!=1)throw std::runtime_error("rollback missing");
s.run();
'''))
   run(['c++','-std=c++17','-O2','-pthread','-I'+cache['DSIM_ZSTD_INCLUDE'],work/'replay.cpp',cache['DSIM_ZSTD_LIBRARY'],'-o',work/'replay'],work,'replay-compile')
   wave=work/'replay.vcd';wave.unlink(missing_ok=True)
   assert run([work/'replay','--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'],work,'replay-run').splitlines()==expected[name]
   assert streams(wave)==references['ordered'],(name,'rollback complete signal stream')
   report['captures']+=1;report['rollbacks']+=1
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output':expected[name]}
  print('PASS REPORT4',name,flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS REPORT4:',len(report['models']),'models,',report['captures'],'VCD captures,',report['rollbacks'],'rollbacks')
