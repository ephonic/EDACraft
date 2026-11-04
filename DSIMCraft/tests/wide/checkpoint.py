"""Checkpoint and replay actual generated multiword RTL + timed-gate programs."""
from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[2]
record=json.loads((Path(sys.argv[2])/'results.json').read_text());assert record['status']=='PASS'
flow=next((Path(record['directory'])/'flow').glob('run-*/results.json')).parent
subprocess.run([sys.executable,str(root/'tests/sdf_runtime/checkpoint.py'),sys.argv[1],str(flow),'sdf-256','fourstate-ports','arithmetic'],check=True)
