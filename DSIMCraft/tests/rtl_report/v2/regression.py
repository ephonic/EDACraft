"""Exact v2 report probes, default named ANSI input and missing-top diagnostics."""
import hashlib,json,subprocess,sys
from pathlib import Path
fixtures=Path(__file__).resolve().parent;compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
for name,digest in json.loads((fixtures/'origin.json').read_text())['probes'].items():assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==digest,name
markers={'t05_random':'T05_RANDOM PASS','t06_urandom':'T06_URANDOM PASS','t08_struct_arg':'T08_STRUCT_ARG PASS','implicit_formals':'TRACE implicit named struct and enum formals pass'}
def run(cmd,work,label,ok=True):
 p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,timeout=180)
 (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
 assert p.returncode==(0 if ok else 1),(label,p.returncode,p.stdout,p.stderr)
 return p.stdout
report={'status':'RUNNING','models':{},'negative_cases':0}
try:
 for name,marker in markers.items():
  work=out/name;work.mkdir(exist_ok=True);source=fixtures/(name+'.sv')
  run([compiler,source,'--emit-cpp',work/'model.cpp','-o',work/'model'],work,'compile')
  text=run([work/'model'],work,'run');assert marker in text and 'FAIL' not in text and 'Fatal' not in text,(name,text)
  report['models'][name]={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stdout':text}
  print('PASS RTL report v2',name,flush=True)
 source=out/'missing_top.sv';source.write_text('module top;endmodule\n');dest=out/'missing_top.cpp';dest.unlink(missing_ok=True)
 run([compiler,source,'--top','nonexistent_top','--emit-only','--emit-cpp',dest],out,'missing_top',False)
 text=(out/'missing_top.stderr').read_text();assert 'top module not found' in text and 'nonexistent_top' in text and 'unknown err' not in text and not dest.exists(),text
 report.update(status='PASS',negative_cases=1)
finally:(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
