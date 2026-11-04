from pathlib import Path
import json,runpy,subprocess,sys
root=Path(__file__).resolve().parents[2]
compiler,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
sys.argv.append('process_handles')
runpy.run_path(str(root/'tests/typed_execution.py'),run_name='__main__')
errors=json.loads((root/'tests/process_handles/runtime_errors.json').read_text())
for name,case in errors.items():
 work=out/('runtime-'+name);work.mkdir(exist_ok=True);source=work/'bad.sv';source.write_text(case['source']+'\n')
 for label,args in [('compile',[compiler,source,'--emit-cpp',work/'bad.cpp','-o',work/'bad']),('run',[work/'bad'])]:
  p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180)
  (work/(label+'.stdout')).write_text(p.stdout);(work/(label+'.stderr')).write_text(p.stderr)
  assert p.returncode==0 if label=='compile' else p.returncode==1 and case['diagnostic'] in p.stderr,(name,label,p.returncode,p.stderr)
report=json.loads((out/'results.json').read_text());report['runtime_errors']=len(errors)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',len(errors),'runtime diagnostics',flush=True)
