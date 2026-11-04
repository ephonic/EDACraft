"""Streaming assignment targets, allocation, bit order and complete wave identity."""
from pathlib import Path
import hashlib,json,subprocess,sys

compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((fixtures/'expected.json').read_text())
report=dict(status='RUNNING',captures=0,models={})
try:
 for name,wanted in expected.items():
  work=out/name;work.mkdir(exist_ok=True);reference=None;captures={}
  modes=[('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel'])]
  for mode,flags in modes:
   for label,cmd in [('compile',[compiler,*flags,fixtures/(name+'.sv'),'--wave-support','--emit-cpp',work/(mode+'.cpp'),'-o',work/mode]),('run',[work/mode,'--waveform',work/(mode+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'])]:
    p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=600)
    (work/(mode+'-'+label+'.stdout')).write_text(p.stdout);(work/(mode+'-'+label+'.stderr')).write_text(p.stderr)
    assert not p.returncode,(name,mode,label,p.stderr[-4000:])
   assert p.stdout.splitlines()==wanted,(name,mode,p.stdout,wanted)
   wave=read(work/(mode+'.vcd'))
   if reference is None:reference=wave
   else:assert reference==wave,(name,'complete ordered waveform')
   captures[mode]=dict(cpp_sha256=hashlib.sha256((work/(mode+'.cpp')).read_bytes()).hexdigest())
   report['captures']+=1
  report['models'][name]=dict(trace=wanted,source_sha256=hashlib.sha256((fixtures/(name+'.sv')).read_bytes()).hexdigest(),captures=captures)
  print('PASS stream targets',name,flush=True)
 negatives=json.loads((fixtures/'negative.json').read_text())
 for name,data in negatives.items():
  work=out/('reject-'+name);work.mkdir(exist_ok=True);(work/'tb.sv').write_text(data['source']);(work/'model.cpp').write_text('protected\n')
  p=subprocess.run(list(map(str,[compiler,work/'tb.sv','--emit-only','--emit-cpp',work/'model.cpp'])),cwd=work,capture_output=True,text=True,timeout=600)
  (work/'compile.stderr').write_text(p.stderr)
  assert p.returncode==1 and data['diagnostic'] in p.stderr,(name,p.stderr)
  assert (work/'model.cpp').read_text()=='protected\n'
 runtime=json.loads((fixtures/'runtime_errors.json').read_text())
 for name,data in runtime.items():
  work=out/('runtime-'+name);work.mkdir(exist_ok=True);(work/'tb.sv').write_text(data['source'])
  for label,cmd in [('compile',[compiler,'--shared-functions',work/'tb.sv','-o',work/'native']),('run',[work/'native'])]:
   p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=600)
   (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
   assert p.returncode==(1 if label=='run' else 0),(name,label,p.stderr)
  assert data['diagnostic'] in p.stderr,(name,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives),runtime_rejections=len(runtime))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
