"""Replay unchanged reported cases against independently frozen full-bit histories."""
from pathlib import Path
import hashlib,json,os,signal,shutil,subprocess,sys,time
fixtures=Path(__file__).resolve().parent
compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
report=dict(status='RUNNING',binary_sha256=sha(compiler.read_bytes()),models={})
def run(args,work,label):
 start=time.monotonic()
 with (work/(label+'.stdout')).open('w') as stdout,(work/(label+'.stderr')).open('w') as stderr:
  p=subprocess.Popen(list(map(str,args)),cwd=work,stdout=stdout,stderr=stderr,start_new_session=True)
  try:code=p.wait(timeout=180)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);p.wait();raise AssertionError((label,'original 180 second budget exceeded'))
 assert code==0,(label,code,(work/(label+'.stderr')).read_text()[-2500:])
 return (work/(label+'.stdout')).read_text(),time.monotonic()-start
try:
 for name,row in json.loads((fixtures/'inventory.json').read_text()).items():
  work=out/name;work.mkdir(exist_ok=True)
  for f in row['files']:
   assert sha((fixtures/name/f).read_bytes())==row['input_sha256'][f],(name,f)
   (work/f).parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(fixtures/name/f,work/f)
  _,seconds=run([compiler,'--timescale','1ns/1ps','--top','tb_compare',*[f for f in row['files'] if f.endswith('.sv')],'--emit-cpp','model.cpp','-o','simv'],work,'compile')
  text,runtime=run([work/'simv'],work,'run');lines=[s for s in text.splitlines() if s.startswith(('RTL_DUAL_TRACE ','RTL_DUAL_DONE '))]
  assert len(lines)==row['events']+1,(name,'complete ordered history required')
  for i,line in enumerate(lines[:-1]):
   fields=line.split();assert fields[:2]==['RTL_DUAL_TRACE',str(i)],(name,i,'order')
   assert len(fields)==len(row['outputs'])+2,(name,i,'inventory')
   for token,(key,width) in zip(fields[2:],row['outputs']):
    assert token.startswith(key+'=') and len(token)==len(key)+1+width and set(token[len(key)+1:])<=set('01xz'),(name,i,key,'full four-state width')
  assert lines[-1]=='RTL_DUAL_DONE events='+str(row['events'])+' outputs='+str(len(row['outputs'])),name
  digest=sha(('\n'.join(lines)+'\n').encode())
  assert digest==row['expected_trace_sha256']==row['vcs_trace_sha256'],(name,'independent oracle/VCS complete history mismatch')
  report['models'][name]=dict(status='PASS',events=row['events'],outputs=len(row['outputs']),compile_seconds=round(seconds,3),run_seconds=round(runtime,3),trace_sha256=digest,input_sha256=row['input_sha256'])
  print('PASS unchanged reported case',name,row['events'],'events',flush=True)
 report.update(status='PASS',events=sum(r['events'] for r in report['models'].values()))
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
