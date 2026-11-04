"""Nonlocal termination, final rules and resumable stops across native backends."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((fixtures/'expected.json').read_text());inputs=json.loads((fixtures/'modes.json').read_text())
wave_disabled=json.loads((fixtures/'wave_disabled.json').read_text())
report=dict(status='RUNNING',models={},captures=0,native_runs=0)
def run(args,w,label,ok=True,commands=''):
 p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,input=commands,timeout=float(os.getenv('DSIM_TEST_COMMAND_TIMEOUT','600')))
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stderr[-4000:]);return p
try:
 for name,modes in expected.items():
  source=fixtures/(name+'.sv');w=out/name;w.mkdir(exist_ok=True);references={};wave_enabled=name not in wave_disabled
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,*flags,source,'--wave-support','--emit-ir',w/(backend+'.json'),'--emit-cpp',w/(backend+'.cpp'),'-o',w/backend],w,backend+'-compile')
   for mode,wanted in modes.items():
    wave=w/(backend+'-'+mode+'.vcd')
    p=run([w/backend,*(['--waveform',wave,'--wave-format','vcd','--wave-mode','ordered'] if wave_enabled else [])],w,backend+'-'+mode,commands=inputs.get(name,{}).get(mode,''))
    assert p.stdout.splitlines()==wanted,(name,backend,mode,p.stdout,wanted)
    report['native_runs']+=1
    if wave_enabled:
     current=read(wave);report['captures']+=1
     if backend=='serial':references[mode]=current
     else:assert current==references[mode],(name,backend,mode,'complete waveform')
  assert json.loads((w/'parallel.json').read_text())['parallel']['partitions']==1,name
  report['models'][name]=dict(traces=modes,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
  print('PASS function termination',name,flush=True)
 negatives=json.loads((fixtures/'negative.json').read_text())
 for name,data in negatives.items():
  w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(data['source']);(w/'model.cpp').write_text('protected\n')
  p=run([compiler,w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'compile',False)
  assert data['diagnostic'] in p.stderr,(name,p.stderr)
  assert (w/'model.cpp').read_text()=='protected\n'
 report.update(status='PASS',negative_cases=len(negatives))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
