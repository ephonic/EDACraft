"""Unchanged reported sources; complete independent bit oracle and VCS transport log."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,shutil
fixtures=Path(__file__).resolve().parent;compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
inventory=json.loads((fixtures/'inventory.json').read_text());report={'status':'RUNNING','models':{}}
def run(cmd,cwd,label):
 started=time.monotonic();p=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,text=True,timeout=300)
 (cwd/(label+'.stdout')).write_text(p.stdout);(cwd/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==0,(label,p.returncode,p.stdout[-1000:],p.stderr[-2000:])
 return p.stdout,time.monotonic()-started
try:
 for name,c in inventory.items():
  source=fixtures/name;work=out/name;work.mkdir(exist_ok=True)
  for f,wanted in c['input_sha256'].items():assert hashlib.sha256((source/f).read_bytes()).hexdigest()==wanted,(name,f,'frozen input changed')
  for f in c['files']:shutil.copy2(source/f,work/f)
  _,seconds=run([compiler,'--timescale','1ns/1ps','--top','tb_compare',*[f for f in c['files'] if f.endswith('.sv')],'--emit-cpp','serial.cpp','--emit-ir','serial.json','-o','simv'],work,'compile')
  text,_=run([work/'simv'],work,'run');lines=text.splitlines()
  actual=[s for s in lines if s.startswith(('RTL_DUAL_TRACE ','RTL_DUAL_DONE '))]
  assert actual==(source/'expected-trace.txt').read_text().splitlines(),(name,'independent oracle: all events/outputs/bits/order/completion')
  assert [s for s in lines if s.startswith('RTL_TRANSPORT_V1 ')]==(source/'expected-transport.txt').read_text().splitlines(),(name,'complete transport history/start/reset/clock/end')
  assert [s for s in lines if s.startswith('RTL_')]==(source/'expected-all.txt').read_text().splitlines(),(name,'VCS complete ordered output')
  report['models'][name]=dict(status='PASS',events=c['events'],outputs=len(c['outputs']),archive_count=len(c['archives']),compile_seconds=round(seconds,3),stdout_sha256=hashlib.sha256(text.encode()).hexdigest(),cpp_sha256=hashlib.sha256((work/'serial.cpp').read_bytes()).hexdigest())
  print('PASS cases_archive',name,c['events'],'events',flush=True)
 report.update(status='PASS',unique_inputs=len(inventory),archives=sum(len(c['archives']) for c in inventory.values()),unique_events=sum(c['events'] for c in inventory.values()))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS original cases:',report['unique_inputs'],'unique inputs,',report['archives'],'archives')
