"""String repetition, operand conversion and complete waveform identity."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=Path(__file__).resolve().parent;root=fixtures.parents[1]
sys.path.insert(0,str(root/'tests/waveform'));from reader import read
expected=json.loads((fixtures/'expected.json').read_text());report=dict(status='RUNNING',models={},captures=0)
def run(args,w,label,ok=True):
 p=subprocess.run(list(map(str,args)),cwd=w,capture_output=True,text=True,timeout=float(os.getenv('DSIM_TEST_COMMAND_TIMEOUT','600')))
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stderr[-4000:]);return p
try:
 for name,wanted in expected.items():
  source=fixtures/(name+'.sv');w=out/name;w.mkdir(exist_ok=True);reference=None
  for backend,flags in [('serial',[]),('shared',['--shared-functions']),('wheel',['--shared-functions','--time-wheel']),('parallel',['--threads','2'])]:
   run([compiler,*flags,source,'--wave-support','--emit-ir',w/(backend+'.json'),'--emit-cpp',w/(backend+'.cpp'),'-o',w/backend],w,backend+'-compile')
   p=run([w/backend,'--waveform',w/(backend+'.vcd'),'--wave-format','vcd','--wave-mode','ordered'],w,backend+'-run')
   assert p.stdout.splitlines()==wanted,(name,backend,p.stdout,wanted)
   current=read(w/(backend+'.vcd'));report['captures']+=1
   if reference is None:reference=current
   else:assert current==reference,(name,backend,'complete waveform')
  report['models'][name]=dict(trace=wanted,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
  print('PASS string replication',name,flush=True)
 negatives=json.loads((fixtures/'negative.json').read_text())
 for name,data in negatives.items():
  w=out/('reject-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text(data['source']);(w/'model.cpp').write_text('protected\n')
  p=run([compiler,w/'tb.sv','--emit-only','--emit-cpp',w/'model.cpp'],w,'compile',False)
  assert data['diagnostic'] in p.stderr,(name,p.stderr)
  assert (w/'model.cpp').read_text()=='protected\n'
 runtime={
  'limit':('int count=600000;string word="ab",result;initial result={count{word}};', 'string replication result exceeds 1048576 bytes'),
 }
 for name,(source,message) in runtime.items():
  w=out/('runtime-'+name);w.mkdir(exist_ok=True);(w/'tb.sv').write_text('module top;'+source+' endmodule\n')
  run([compiler,w/'tb.sv','-o',w/'native'],w,'compile');p=run([w/'native'],w,'run',False)
  assert message in p.stderr,(name,p.stderr)
 report.update(status='PASS',negative_cases=len(negatives),runtime_rejections=len(runtime))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
