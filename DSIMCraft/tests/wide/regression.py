from pathlib import Path
import json,subprocess,sys,tempfile
from cases import make
root=Path(__file__).resolve().parents[2]
base=Path(sys.argv[2]).resolve();base.mkdir(parents=True,exist_ok=True)
work=Path(tempfile.mkdtemp(prefix='run-',dir=base));manifest=make(work/'inputs')
subprocess.run([sys.executable,str(root/'scripts/run_flow.py'),str(manifest),'--dsim',str(Path(sys.argv[1]).resolve()),'--output',str(work/'flow')],check=True)
report=json.loads(next((work/'flow').glob('run-*/results.json')).read_text());assert report['status']=='PASS'
record=dict(status='PASS',directory=str(work),cases=len(report['cases']))
(base/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS complete multiword compiler/ports/gates/SDF/VCD/DWF',work)
