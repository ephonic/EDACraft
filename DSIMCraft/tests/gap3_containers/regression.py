from pathlib import Path
import json,runpy,subprocess,sys
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[2]).resolve()
sys.argv.append('gap3_containers')
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
