"""Same-byte fixtures on the VCS oracle; preserve failures and source hashes."""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,sys,time
root,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
fixtures=root/'tests/stream_enum_casts';names=sorted(p.stem for p in fixtures.glob('*.sv') if not p.name.startswith('.'))
if len(sys.argv)>3:names=sys.argv[3:]
def one(name):
 w=out/name;w.mkdir(exist_ok=True);source=(fixtures/(name+'.sv')).read_bytes();(w/'tb.sv').write_bytes(source);t=time.monotonic()
 for label,command in [('compile','source /apps/EDAs/syn.bash; vcs -full64 -sverilog -top '+('tb' if name=='original' else 'top')+' tb.sv -o native'),('run','./native')]:
  p=subprocess.run(['bash','-c',command],cwd=w,capture_output=True,text=True,timeout=240)
  (w/(label+'.stdout')).write_text(p.stdout);(w/(label+'.stderr')).write_text(p.stderr)
  assert not p.returncode,(name,label,p.stdout[-3000:],p.stderr[-1000:])
 trace=[l for l in p.stdout.splitlines() if l.startswith(('TRACE','FORKFN:'))]
 print('PASS VCS',name,flush=True)
 return name,dict(status='PASS',trace=trace,source_sha256=hashlib.sha256(source).hexdigest(),seconds=time.monotonic()-t)
report=dict(status='RUNNING',performance_comparison=False,models={})
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for name,data in pool.map(one,names):report['models'][name]=data
 report['status']='PASS';(out/'expected.json').write_text(json.dumps({n:r['trace'] for n,r in report['models'].items()},indent=2)+'\n')
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
