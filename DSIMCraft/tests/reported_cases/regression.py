"""Preserve user-reported sources, independent expected bits and corrected race fixtures."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
root=Path(__file__).resolve().parent;compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','models':{}}
try:
 for name in json.loads((root/'cases.json').read_text()):
  source=root/name;work=out/name;work.mkdir(exist_ok=True)
  if (source/'stimulus.hex').exists():__import__('shutil').copy2(source/'stimulus.hex',work/'stimulus.hex')
  origin=json.loads((source/'origin.json').read_text())
  assert hashlib.sha256((source/'rtl.sv').read_bytes()).hexdigest()==origin['original_rtl_sha256']
  if origin['change'].startswith('none;'):assert hashlib.sha256((source/'tb.sv').read_bytes()).hexdigest()==origin['original_tb_sha256']
  if (source/'stimulus.hex').exists():assert hashlib.sha256((source/'stimulus.hex').read_bytes()).hexdigest()==origin['original_stimulus_sha256']
  durations={}
  for label,command in [('compile',[compiler,'--timescale','1ns/1ps','--top','tb_compare',source/'rtl.sv',source/'tb.sv','--emit-cpp',work/'model.cpp','-o',work/'simv']),('run',[work/'simv'])]:
   started=time.monotonic();p=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=180)
   (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr);durations[label]=time.monotonic()-started
   assert p.returncode==0,(name,label,p.returncode,p.stdout,p.stderr)
  trace=[x for x in p.stdout.splitlines() if x.startswith('RTL_DUAL_TRACE ')];expected=json.loads((source/'expected.json').read_text());assert trace==expected,(name,'independent expected bits')
  assert len([x for x in p.stdout.splitlines() if x.startswith('RTL_DUAL_DONE ')])==1
  assert 'RTL_DUAL_DONE events='+str(len(expected))+' outputs='+str(len(expected[0].split())-2) in p.stdout
  report['models'][name]={'status':'PASS','events':len(trace),'seconds':durations};print('PASS reported case',name,len(trace),flush=True)
 report['status']='PASS'
except Exception as e:report.update(status='FAIL',failure=repr(e));raise
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
