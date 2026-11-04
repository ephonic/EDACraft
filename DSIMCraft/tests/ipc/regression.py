from pathlib import Path
import json,runpy,subprocess,sys
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[2]).resolve()
sys.argv.append('ipc')
runpy.run_path(str(root/'tests/typed_execution.py'),run_name='__main__')
p=subprocess.run([str(out/'parallel/parallel'),'--parallel-stats'],capture_output=True,text=True,timeout=60)
(out/'parallel/stats.stderr').write_text(p.stderr)
assert p.returncode==0 and '"partitions":2' in p.stderr,p.stderr
sys.path.insert(0,str(root/'tests/waveform'))
from reader import read,timeline
lanes=timeline(*read(out/'parallel/parallel-ordered.async.dwf'))
assert lanes[('top','one')][2]==[(0,(0,0)),(2,(7,0)),(4,(9,0))],lanes
assert lanes[('top','two')][2]==[(0,(0,0)),(1,(11,0)),(3,(23,0))],lanes
report=json.loads((out/'results.json').read_text());report['verified_parallel_partitions']=2
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS two independent runtime partitions',flush=True)

# These compile successfully and must report a language/runtime error, never a crash.
errors=json.loads((root/'tests/ipc/runtime_errors.json').read_text())
compiler=Path(sys.argv[1]).resolve()
for name,case in errors.items():
 work=out/('runtime-'+name);work.mkdir(exist_ok=True)
 source=work/'bad.sv';source.write_text(case['source']+'\n')
 p=subprocess.run([str(compiler),str(source),'--emit-cpp',str(work/'bad.cpp'),'-o',str(work/'bad')],capture_output=True,text=True,timeout=180)
 (work/'compile.stdout').write_text(p.stdout);(work/'compile.stderr').write_text(p.stderr)
 assert p.returncode==0,(name,p.stderr)
 p=subprocess.run([str(work/'bad')],capture_output=True,text=True,timeout=30)
 (work/'run.stdout').write_text(p.stdout);(work/'run.stderr').write_text(p.stderr)
 assert p.returncode>0 and case['diagnostic'] in p.stderr,(name,p.returncode,p.stdout,p.stderr)
report=json.loads((out/'results.json').read_text());report['runtime_errors']=len(errors)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',len(errors),'runtime diagnostics',flush=True)
