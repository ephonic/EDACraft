"""Classify accepted VCS extensions separately from actual compiler rejections."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
fixtures,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
report=dict(status='RUNNING',compile={},runtime={})
def run(cmd,w,label):
 p=subprocess.run(['bash','-c',cmd],cwd=w,capture_output=True,text=True,timeout=240)
 (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr);assert p.returncode>=0
 return p
try:
 for group,filename in [('compile','negative.json'),('runtime','runtime_errors.json')]:
  if not (fixtures/filename).exists():continue
  for name,data in json.loads((fixtures/filename).read_text()).items():
   if len(sys.argv)>3 and name not in sys.argv[3:]:continue
   w=out/name;w.mkdir();source=data['source'].encode();(w/'tb.sv').write_bytes(source)
   p=run('source /apps/EDAs/syn.bash; vcs -full64 -sverilog tb.sv -o native',w,'compile')
   if group=='compile':
    assert (p.returncode==0)==(w/'native').exists(),name
    if p.returncode:assert 'Error-[' in p.stdout,(name,p.stdout[-3000:])
    result=dict(status='ACCEPTED' if not p.returncode else 'REJECTED',exit_code=p.returncode)
   else:
    assert not p.returncode,(name,p.stdout[-3000:]);p=run('./native',w,'run')
    has_error=bool(re.search(r'Error(?:-\[|:)',p.stdout));assert (not p.returncode and not has_error) or (p.returncode and has_error),(name,p.returncode,p.stdout[-3000:])
    result=dict(status='RUNTIME_REJECTED' if p.returncode else 'PASS',exit_code=p.returncode)
   result['source_sha256']=hashlib.sha256(source).hexdigest();report[group][name]=result;print(group,name,result['status'],flush=True)
 report['status']='PASS'
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
